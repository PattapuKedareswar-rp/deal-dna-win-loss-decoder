"""Ask Deal DNA — a read-only intelligence agent over the deterministic analytics.

When a key is present, the agent uses OpenAI **tool-calling**: it plans, calls read-only analytics
tools (win rates, competitor battlecards, deal evidence, market radar, portfolio), then composes an
evidence-cited answer. Offline, it falls back to deterministic intent routing so it still works.

Governance: every tool is read-only. The agent never emails, writes to Salesforce, or contacts a
customer; such requests are refused with a human-review recommendation.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from . import config, llm
from .normalize import list_cycles
from .portfolio import build_portfolio
from .radar import build_radar
from .schema import DealDNA
from .synthesize import synthesize_cycle

_COMPETITORS = ["Entrata", "Yardi", "MRI Software", "ResMan", "AppFolio"]


@lru_cache(maxsize=1)
def _all_deals() -> tuple[DealDNA, ...]:
    return tuple(synthesize_cycle(c) for c in list_cycles())


def reset_cache() -> None:
    _all_deals.cache_clear()


# ---------------- read-only tools ----------------
def t_list_deals() -> list[dict]:
    return [{"cycle_id": d.cycle_id, "account": d.account, "outcome": d.outcome.value,
             "product": d.product_families[0] if d.product_families else ""} for d in _all_deals()]


def t_get_deal_evidence(cycle_id: str) -> dict:
    for d in _all_deals():
        if d.cycle_id == cycle_id:
            return {
                "cycle_id": d.cycle_id, "account": d.account, "outcome": d.outcome.value,
                "drivers": [{"category": x.category.value, "direction": x.direction.value,
                             "quote": x.quote, "speaker": x.speaker, "timestamp": x.timestamp,
                             "source": x.source, "confidence": x.confidence} for x in d.drivers],
                "competitor_mentions": [{"name": m.name, "is_loss_reason": m.is_loss_reason}
                                        for m in d.competitor_mentions],
                "unknowns": d.unknowns,
            }
    return {"error": f"cycle {cycle_id} not found"}


def t_win_rates(group_by: str = "overall") -> dict:
    r = build_portfolio(list(_all_deals()))
    if group_by == "product":
        return {"by_product": [{"product": p, "win_rate": round(wr, 3), "closed": n}
                               for p, wr, n in r.win_rate_by_product]}
    return {"win_rate": round(r.win_rate, 3), "won": r.won, "lost": r.lost, "stalled": r.stalled}


def t_competitor_battlecards() -> list[dict]:
    r = build_portfolio(list(_all_deals()))
    return [{"competitor": b.competitor, "deals": b.deals, "won": b.won, "lost": b.lost,
             "loss_rate": round(b.loss_rate, 3), "top_loss_drivers": b.top_loss_drivers,
             "sample_quote": b.sample_quote} for b in r.battlecards]


def t_market_radar() -> dict:
    r = build_radar(list(_all_deals()))
    return {"recurring_hesitations": [{"label": s.label, "cycles": s.count}
                                      for s in r.recurring_hesitations],
            "alternative_software": [{"label": s.label, "cycles": s.count}
                                     for s in r.alternative_software]}


def t_portfolio_summary() -> dict:
    r = build_portfolio(list(_all_deals()))
    return {"win_rate": round(r.win_rate, 3), "won": r.won, "lost": r.lost, "stalled": r.stalled,
            "top_win_drivers": r.top_win_drivers, "top_loss_drivers": r.top_loss_drivers,
            "coaching_hotspots": r.coaching_hotspots}


_DISPATCH = {
    "list_deals": lambda a: t_list_deals(),
    "get_deal_evidence": lambda a: t_get_deal_evidence(a.get("cycle_id", "")),
    "win_rates": lambda a: t_win_rates(a.get("group_by", "overall")),
    "competitor_battlecards": lambda a: t_competitor_battlecards(),
    "market_radar": lambda a: t_market_radar(),
    "portfolio_summary": lambda a: t_portfolio_summary(),
}

TOOLS = [
    {"type": "function", "function": {
        "name": "list_deals", "description": "List all deals with cycle_id, account, outcome, product.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_deal_evidence",
        "description": "Get the citation-locked drivers, competitor mentions, and unknowns for one deal.",
        "parameters": {"type": "object", "properties": {
            "cycle_id": {"type": "string", "description": "e.g. cyc-001"}}, "required": ["cycle_id"]}}},
    {"type": "function", "function": {
        "name": "win_rates", "description": "Win rate overall or grouped by product.",
        "parameters": {"type": "object", "properties": {
            "group_by": {"type": "string", "enum": ["overall", "product"]}}}}},
    {"type": "function", "function": {
        "name": "competitor_battlecards",
        "description": "Per-competitor deals, win/loss, loss rate, top loss drivers, sample evidence quote.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "market_radar", "description": "Recurring hesitations and alternative-software mentions.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "portfolio_summary",
        "description": "KPIs, top win/loss drivers, and enablement coaching hotspots.",
        "parameters": {"type": "object", "properties": {}}}},
]

_SYSTEM = (
    "You are Deal DNA, a read-only sales win/loss intelligence agent. Answer the user's question by "
    "calling the provided analytics tools and grounding EVERY claim in their results. Cite specific "
    "numbers and verbatim quotes (with speaker + timestamp) from tool outputs. Never invent data. A "
    "competitor mention is NOT a loss reason. You are advisory only: never propose sending email, "
    "writing to Salesforce, or contacting a customer. If asked to take such an action, refuse and give "
    "a human-review recommendation instead. Note the data is synthetic/demo unless told otherwise. Keep "
    "answers concise and well-structured."
)

_ACTION_RE = re.compile(r"\b(email|send|contact|update (salesforce|crm)|write ?back|publish|notify)\b", re.I)


@dataclass
class ToolCall:
    name: str
    args: dict
    result: object


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    engine: str = "offline"


def ask(question: str) -> AgentResult:
    if llm.is_offline():
        return _offline(question)
    try:
        return _agentic(question)
    except Exception as e:  # any API/parse failure -> deterministic fallback
        res = _offline(question)
        res.answer = f"_(Live model unavailable: {e}. Answered with offline reasoning.)_\n\n" + res.answer
        return res


def _agentic(question: str) -> AgentResult:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    messages = [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": question}]
    calls: list[ToolCall] = []
    for _ in range(6):
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL, messages=messages, tools=TOOLS, temperature=0)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return AgentResult(answer=msg.content or "", tool_calls=calls, engine="openai")
        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _DISPATCH.get(tc.function.name, lambda a: {"error": "unknown tool"})(args)
            calls.append(ToolCall(tc.function.name, args, result))
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)[:6000]})
    resp = client.chat.completions.create(model=config.OPENAI_MODEL, messages=messages, temperature=0)
    return AgentResult(answer=resp.choices[0].message.content or "", tool_calls=calls, engine="openai")


def _offline(question: str) -> AgentResult:
    q = question.lower()
    calls: list[ToolCall] = []

    def _use(name, args, fn):
        r = fn()
        calls.append(ToolCall(name, args, r))
        return r

    named = [c for c in _COMPETITORS if c.lower() in q]
    if named or "competitor" in q or "alternative" in q:
        bc = _use("competitor_battlecards", {}, t_competitor_battlecards)
        rows = [b for b in bc if not named or b["competitor"] in named] or bc
        lines = ["**Competitive exposure** (synthetic demo data):"]
        for b in rows:
            drivers = ", ".join(f"{c} ({n})" for c, n in b["top_loss_drivers"]) or "—"
            lines.append(f"- **{b['competitor']}** — {b['deals']} deal(s), Won {b['won']} / Lost "
                         f"{b['lost']}, loss rate {b['loss_rate']:.0%}; top loss drivers: {drivers}")
            if b["sample_quote"]:
                lines.append(f"  - evidence: “{b['sample_quote'][:130]}”")
        answer = "\n".join(lines)
    elif re.search(r"cyc-\d+", q):
        cid = re.search(r"cyc-\d+", q).group(0)
        ev = _use("get_deal_evidence", {"cycle_id": cid}, lambda: t_get_deal_evidence(cid))
        if "error" in ev:
            answer = ev["error"]
        else:
            lines = [f"**{ev['account']} ({ev['cycle_id']}) — {ev['outcome']}**"]
            for d in ev["drivers"][:5]:
                lines.append(f"- {d['category']} ({d['direction']}, {d['confidence']}): "
                             f"“{d['quote'][:120]}” — {d['speaker']} @ {d['timestamp']}")
            if ev["unknowns"]:
                lines.append("Unknowns: " + "; ".join(ev["unknowns"]))
            answer = "\n".join(lines)
    elif "win rate" in q or "by product" in q or "product" in q:
        wr = _use("win_rates", {"group_by": "product"}, lambda: t_win_rates("product"))
        lines = ["**Win rate by product** (synthetic demo data):"]
        for r in wr["by_product"]:
            lines.append(f"- {r['product']}: {r['win_rate']:.0%} ({r['closed']} closed)")
        answer = "\n".join(lines)
    elif any(w in q for w in ("coach", "train", "enablement", "skill")):
        ps = _use("portfolio_summary", {}, t_portfolio_summary)
        hot = ", ".join(f"{c} ({n})" for c, n in ps["coaching_hotspots"])
        answer = f"**Coaching hotspots** (recurring rep-facing friction): {hot}."
    elif "radar" in q or "trend" in q or "hesitation" in q:
        rad = _use("market_radar", {}, t_market_radar)
        h = ", ".join(f"{s['label']} ({s['cycles']})" for s in rad["recurring_hesitations"])
        a = ", ".join(f"{s['label']} ({s['cycles']})" for s in rad["alternative_software"])
        answer = f"**Recurring hesitations:** {h}.\n**Alternative software mentioned:** {a}."
    else:
        ps = _use("portfolio_summary", {}, t_portfolio_summary)
        win = ", ".join(f"{c} ({n})" for c, n in ps["top_win_drivers"])
        loss = ", ".join(f"{c} ({n})" for c, n in ps["top_loss_drivers"])
        answer = (f"**Portfolio** (synthetic demo): win rate {ps['win_rate']:.0%} "
                  f"({ps['won']}W / {ps['lost']}L / {ps['stalled']} stalled).\n"
                  f"Top win drivers: {win}.\nTop loss drivers: {loss}.")

    if _ACTION_RE.search(q):
        answer = ("**Refused — advisory only.** Deal DNA will not email, write to Salesforce, or contact "
                  "customers. Here is a human-review recommendation instead:\n\n" + answer)
    return AgentResult(answer=answer, tool_calls=calls, engine="offline")
