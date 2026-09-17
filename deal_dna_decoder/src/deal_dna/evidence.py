"""Evidence coder.

Extract evidence-backed drivers from transcript turns. Every driver cites the exact quote,
speaker, timestamp, and source. Two paths:

- Offline (default / no key): deterministic phrase matching over real buyer statements. The
  quote is always a verbatim turn, so findings stay grounded.
- LLM (key present): OpenAI structured output constrained to the same evidence contract.

Governance built in: a competitor mention is captured but never auto-marked as a loss reason.
"""
from __future__ import annotations

import re

from . import config, llm
from .normalize import Call, Turn
from .schema import Category, CompetitorMention, Direction, Driver, EvidenceLabel

COMPETITORS = ["Yardi", "Entrata", "MRI Software", "ResMan", "AppFolio"]

# (pattern, category, direction, confidence, short summary)
_SIGNALS: list[tuple[re.Pattern, Category, Direction, str, str]] = [
    (re.compile(r"too high|20% above|total cost|cost of ownership|won'?t approve|implementation fees", re.I),
     Category.PRICING, Direction.NEGATIVE, "high", "Price / total cost of ownership concern."),
    (re.compile(r"revenue lift|rent-optimization lift|\bROI\b|\bNOI\b|payback|quantified", re.I),
     Category.ROI, Direction.POSITIVE, "high", "Positive ROI / revenue-lift signal."),
    (re.compile(r"clunky|felt clunky|weren'?t obvious|switched screens|switching screens", re.I),
     Category.DEMO, Direction.NEGATIVE, "medium", "Demo friction observed."),
    (re.compile(r"demo really showed|demo was smooth|demo.*showed how", re.I),
     Category.DEMO, Direction.POSITIVE, "medium", "Positive demo reaction."),
    (re.compile(r"open API|data warehouse|roadmap still|integration", re.I),
     Category.INTEGRATION, Direction.NEGATIVE, "high", "Integration / API gap."),
    (re.compile(r"references|peer references|\btrust\b", re.I),
     Category.TRUST, Direction.POSITIVE, "medium", "Trust / references strength."),
    (re.compile(r"budget froze|next fiscal year|timing|budget approval is uncertain|budget reopen", re.I),
     Category.TIMING, Direction.NEGATIVE, "medium", "Timing / budget constraint."),
    (re.compile(r"CFO.*approve|need.*approve|will need to approve", re.I),
     Category.AUTHORITY, Direction.NEUTRAL, "medium", "Decision authority / approval gate."),
    (re.compile(r"switching cost|migration|onboarding|risk concerns|hesitant|risk", re.I),
     Category.RISK, Direction.NEGATIVE, "medium", "Perceived risk / switching cost."),
    (re.compile(r"consolidate|manual steps|manual|point tools|pain", re.I),
     Category.NEED, Direction.POSITIVE, "medium", "Consolidation / efficiency need."),
    (re.compile(r"implementation plan de-?risked|implementation and support|support plan", re.I),
     Category.IMPLEMENTATION, Direction.POSITIVE, "medium", "Implementation plan de-risked the deal."),
    (re.compile(r"missing feature|feature gap|automated renewals", re.I),
     Category.PRODUCT, Direction.NEGATIVE, "high", "Missing feature / product gap."),
]

_LOSS_CAUSAL = re.compile(r"we (chose|went with|selected)\b", re.I)
# Risk language that is explicitly mitigated should not read as a negative signal.
_MITIGATION = re.compile(r"de-?risk|reduced|addressed|mitigat|resolved|eased|reassured", re.I)


def _extract_offline(turns: list[Turn]) -> tuple[list[Driver], list[CompetitorMention]]:
    drivers: list[Driver] = []
    mentions: list[CompetitorMention] = []
    # Synthetic data labels roles (Buyer/Rep); real transcripts don't. When no buyer role
    # exists, analyze all speakers so extraction still works on real evidence.
    has_roles = any(("buyer" in t.role.lower() or "customer" in t.role.lower()) for t in turns)
    for t in turns:
        role = t.role.lower()
        # Competitor mentions (from anyone) — captured, not judged.
        for comp in COMPETITORS:
            if re.search(rf"\b{re.escape(comp)}\b", t.text, re.I):
                mentions.append(CompetitorMention(
                    name=comp, quote=t.text, speaker=f"{t.role} - {t.speaker}",
                    timestamp=t.timestamp, source=t.source,
                    is_loss_reason=bool(_LOSS_CAUSAL.search(t.text)),
                    note="" if _LOSS_CAUSAL.search(t.text) else "Mention only; not established as a loss reason.",
                ))
        # Drivers anchor on buyer statements when roles are known; else on any speaker.
        if has_roles and "buyer" not in role and "customer" not in role:
            continue
        for pat, cat, direction, conf, summary in _SIGNALS:
            if not pat.search(t.text):
                continue
            # Risk that the seller explicitly mitigated is not a negative signal.
            if cat == Category.RISK and direction == Direction.NEGATIVE and _MITIGATION.search(t.text):
                continue
            drivers.append(Driver(
                category=cat, direction=direction, label=EvidenceLabel.OBSERVED,
                summary=summary, quote=t.text, speaker=f"{t.role} - {t.speaker}",
                speaker_role=t.speaker, timestamp=t.timestamp, source=t.source,
                confidence=conf,
            ))
    return _dedupe(drivers), mentions


def _dedupe(drivers: list[Driver]) -> list[Driver]:
    seen: set[tuple] = set()
    out: list[Driver] = []
    for d in drivers:
        key = (d.category, d.quote)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


_LLM_SYSTEM = (
    "You are Deal DNA's evidence coder. Extract ONLY findings supported by an attributed BUYER "
    "statement. Every driver MUST copy a VERBATIM buyer quote (never paraphrase, never invent) plus "
    "the speaker, timestamp, and source exactly as given. Separate observation from interpretation: "
    "use label 'Observed' only for direct buyer statements. A competitor mention is NOT a loss reason "
    "unless the buyer explicitly says they chose/selected the competitor. When a statement is not "
    "clearly supported, DO NOT emit a driver (abstain). Do not turn missing evidence into a negative "
    "finding. Return JSON with a 'drivers' list and a 'competitor_mentions' list matching the schema."
)


class _EvidenceBundle:  # lightweight container for LLM parsing
    pass


def extract_call(call: Call) -> tuple[list[Driver], list[CompetitorMention]]:
    """Extract drivers + competitor mentions for one call."""
    if llm.is_offline():
        return _extract_offline(call.turns)
    # LLM path: keep the deterministic result as a grounded fallback if parsing fails.
    try:
        from pydantic import BaseModel

        class _Bundle(BaseModel):
            drivers: list[Driver] = []
            competitor_mentions: list[CompetitorMention] = []

        transcript = "\n".join(
            f"[{t.timestamp}] {t.role} - {t.speaker}: {t.text}" for t in call.turns
        )
        user = f"Source: {call.turns[0].source if call.turns else ''}\nTranscript:\n{transcript}"
        bundle = llm.structured_json(_LLM_SYSTEM, user, _Bundle)
        if bundle.drivers or bundle.competitor_mentions:
            return bundle.drivers, bundle.competitor_mentions
    except Exception:
        pass
    return _extract_offline(call.turns)
