"""Deal DNA — review & intelligence web app.

Two workspaces:
- Executive Portfolio: win-rate analytics, competitor battlecards, coaching hotspots, market radar.
- Deal Review: per-deal genome, rep -> manager review loop, cross-functional feeds, guardrail.

Advisory and read-only toward the outside world: it never emails, writes to Salesforce, or
publishes. Any such request is routed to the guardrail and refused, with the refusal shown in-app.

Run:  python -m streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from deal_dna import config, sources
from deal_dna.audit import audit_dealdna, screen_action_request
from deal_dna.crossfunction import enrich_crossfunctional
from deal_dna.normalize import list_cycles
from deal_dna.portfolio import build_portfolio
from deal_dna.radar import build_radar
from deal_dna.render import render_briefing
from deal_dna.schema import DealDNA, Outcome, ReviewCorrection
from deal_dna.synthesize import synthesize_cycle

_CSS = (Path(__file__).parent / "static" / "colorway.css").read_text(encoding="utf-8")
_STATUS_CLASS = {
    "Needs Review": "needs-review", "Rep Reviewed": "rep-reviewed",
    "Manager Validated": "manager-validated", "Blocked": "blocked",
}
_OUTCOME_CLASS = {
    "Won": "won", "Lost": "lost", "Stalled / No Decision": "stalled", "Needs Review": "review",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- data helpers (cached; offline & deterministic) ----------
@st.cache_data(show_spinner=False)
def _index() -> list[dict]:
    rows = []
    for c in list_cycles():
        d = synthesize_cycle(c)
        rows.append({
            "cycle_id": c, "account": d.account, "outcome": d.outcome.value,
            "product": d.product_families[0] if d.product_families else "(unknown)",
            "competitors": sorted({m.name for m in d.competitor_mentions}),
            "drivers": len(d.drivers), "calls": d.call_count,
        })
    return rows


@st.cache_data(show_spinner=False)
def _portfolio():
    deals = [synthesize_cycle(c) for c in list_cycles()]
    return build_portfolio(deals), build_radar(deals)


def _reviewed_path(cycle_id: str) -> Path:
    return config.OUTPUTS_DIR / "reviewed" / f"{cycle_id}.json"


def _load(cycle_id: str) -> DealDNA:
    # Reload a persisted review if present (survives refresh); else build fresh.
    p = _reviewed_path(cycle_id)
    if p.exists():
        try:
            return DealDNA.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return enrich_crossfunctional(synthesize_cycle(cycle_id))


def _get_dna(cycle_id: str) -> DealDNA:
    store = st.session_state.setdefault("dna", {})
    if cycle_id not in store:
        store[cycle_id] = _load(cycle_id)
    return store[cycle_id]


def _save_reviewed(d: DealDNA) -> Path:
    out = _reviewed_path(d.cycle_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d.model_dump(mode="json"), indent=2, default=str), encoding="utf-8")
    return out


def _kpi(label: str, value, kind: str = "") -> str:
    return f'<div class="rp-kpi {kind}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def _badge(outcome: str) -> str:
    return f'<span class="rp-badge {_OUTCOME_CLASS.get(outcome, "review")}">{outcome}</span>'


def _status_chip(status: str) -> str:
    return f'<span class="rp-status {_STATUS_CLASS.get(status, "needs-review")}">Review: {status}</span>'


def _engine_label() -> str:
    return "Offline heuristics" if config.is_offline() else f"OpenAI agent · {config.OPENAI_MODEL}"


def _data_pill() -> str:
    label = "Approved export" if sources.data_mode() == "approved-export" else "Synthetic demo"
    return f'<span class="pill">📁 Data: {label}</span>'


def _h(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="rp-section">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.caption(sub)


def _hbar(pairs, color: str, pct: bool = False):
    """Readable horizontal bar chart with value labels (no truncated x-axis text)."""
    if not pairs:
        return None
    df = pd.DataFrame(list(pairs), columns=["label", "value"])
    vmax = max(v for _, v in pairs) or 1
    domain = [0, (1.0 if pct else vmax) * 1.18]
    base = alt.Chart(df).encode(
        y=alt.Y("label:N", sort="-x", title=None,
                axis=alt.Axis(labelFontSize=13, labelLimit=260, labelColor="#0A1420")),
        x=alt.X("value:Q", title=None, axis=None, scale=alt.Scale(domain=domain)),
    )
    bars = base.mark_bar(color=color, cornerRadiusEnd=4, size=24)
    text = base.mark_text(align="left", dx=6, fontSize=13, color="#0A1420").encode(
        text=alt.Text("value:Q", format=".0%" if pct else "d"))
    return ((bars + text).properties(height=len(df) * 42 + 12)
            .configure_view(strokeWidth=0).configure_axis(grid=False))


def _bar(pairs, color: str, pct: bool = False) -> None:
    chart = _hbar(pairs, color, pct)
    if chart is not None:
        st.altair_chart(chart, width="stretch")


# ---------- Portfolio page ----------
def page_portfolio() -> None:
    report, radar = _portfolio()
    st.markdown(
        f'<div class="rp-hero"><h1>Deal DNA — Executive Portfolio</h1>'
        f'<div class="sub">Why we win and lose, decoded from sales conversations — '
        f'evidence-backed, advisory, human-in-the-loop.</div>'
        f'<div style="margin-top:10px"><span class="pill">🧠 Engine: {_engine_label()}</span>'
        f'{_data_pill()}<span class="pill">read-only</span>'
        f'<span class="pill">no CRM write-back</span></div></div>',
        unsafe_allow_html=True)
    st.write("")

    k = st.columns(5)
    k[0].markdown(_kpi(f"Win rate · {report.won + report.lost} closed", f"{report.win_rate:.0%}", "good"),
                  unsafe_allow_html=True)
    k[1].markdown(_kpi("Won", report.won, "good"), unsafe_allow_html=True)
    k[2].markdown(_kpi("Lost", report.lost, "bad"), unsafe_allow_html=True)
    k[3].markdown(_kpi("Stalled", report.stalled, "warn"), unsafe_allow_html=True)
    k[4].markdown(_kpi("Cycles", report.total_cycles), unsafe_allow_html=True)
    st.caption("⚠ Synthetic demo data, small sample — metrics are directional, not production accuracy. "
               "Product bars show closed-deal count (n).")

    _h("Win rate by product")
    _bar([(f"{p} (n={n})", wr) for p, wr, n in report.win_rate_by_product], "#082649", pct=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        _h("Top win drivers", "Positive signals on Won deals")
        _bar(report.top_win_drivers, "#2E8B57")
    with c2:
        _h("Top loss drivers", "Negative signals on Lost deals")
        _bar(report.top_loss_drivers, "#D2402A")

    _h("Competitor battlecards",
       "Where we are exposed and why — each with evidence. A mention is not a loss reason.")
    for b in report.battlecards:
        klass = "hot" if b.loss_rate >= 0.75 else "mid" if b.loss_rate >= 0.4 else "cool"
        drivers = ", ".join(f"{c} ({n})" for c, n in b.top_loss_drivers) or "—"
        quote = f'<blockquote>“{b.sample_quote[:140]}”</blockquote>' if b.sample_quote else ""
        st.markdown(
            f'<div class="rp-bc {klass}"><h4>{b.competitor} &nbsp;'
            f'<span style="font-weight:400;font-size:12px;color:#495E83">loss rate {b.loss_rate:.0%}</span></h4>'
            f'<div class="meta">{b.deals} deal(s) · Won {b.won} / Lost {b.lost} '
            f'· top loss drivers: {drivers}</div>{quote}</div>',
            unsafe_allow_html=True)

    c3, c4 = st.columns(2, gap="large")
    with c3:
        _h("Enablement coaching hotspots", "Recurring rep-facing friction to train on")
        _bar(report.coaching_hotspots, "#AE6B29")
    with c4:
        _h("Market-signal radar", radar.note)
        for s in radar.recurring_hesitations:
            st.markdown(f'<div class="rp-card">🔁 <b>{s.label}</b> — recurring in {s.count} cycles</div>',
                        unsafe_allow_html=True)
        for s in radar.alternative_software:
            st.markdown(f'<div class="rp-card">🏷 <b>{s.label}</b> — mentioned in {s.count} cycles</div>',
                        unsafe_allow_html=True)

    with st.expander("Methodology & limits"):
        st.markdown(
            "- Data is **synthetic demo** unless an approved export is ingested (`--ingest`).\n"
            "- Drivers are evidence-cited; a competitor mention is **never** auto-treated as a loss reason.\n"
            "- Aggregates are **directional on a small sample** — not a production predictive model.\n"
            "- The evaluation gold set is author-labeled and the priority logic is tuned on it; "
            "real validation needs an independent human-labeled sample split by cycle.")

    st.write("")
    st.download_button("⬇ Download portfolio dashboard (HTML)",
                       data=_portfolio_html(report), file_name="portfolio.html", mime="text/html")


def _portfolio_html(report) -> str:
    from deal_dna.portfolio import render_portfolio_html
    return render_portfolio_html(report)


# ---------- Deal Review page ----------
def page_review() -> None:
    idx = _index()
    all_products = sorted({r["product"] for r in idx})
    all_comps = sorted({c for r in idx for c in r["competitors"]})
    all_outcomes = ["Won", "Lost", "Stalled / No Decision", "Needs Review"]

    with st.sidebar:
        st.markdown("**Filter deals**")
        f_out = st.multiselect("Outcome", all_outcomes, default=all_outcomes)
        f_prod = st.selectbox("Product", ["All"] + all_products)
        f_comp = st.selectbox("Competitor", ["All"] + all_comps)

    def _match(r: dict) -> bool:
        if r["outcome"] not in f_out:
            return False
        if f_prod != "All" and r["product"] != f_prod:
            return False
        if f_comp != "All" and f_comp not in r["competitors"]:
            return False
        return True

    filtered = [r for r in idx if _match(r)]
    st.markdown('<div class="rp-hero"><h1>Deal DNA — Win/Loss Review</h1>'
                '<div class="sub">Open a deal to see its evidence genome, run the rep → manager '
                'review, and route cross-functional actions.</div>'
                f'<div style="margin-top:10px"><span class="pill">🧠 Engine: {_engine_label()}</span>{_data_pill()}'
                '<span class="pill">advisory</span><span class="pill">human-in-the-loop</span>'
                '</div></div>', unsafe_allow_html=True)

    if not filtered:
        st.warning("No deals match the current filters.")
        return

    labels = {f'{r["cycle_id"]} · {r["account"]} · {r["outcome"]}': r["cycle_id"] for r in filtered}
    with st.sidebar:
        role = st.radio("Your role", ["Rep", "Manager"], horizontal=True)
        actor_name = st.text_input(f"{role} name", value=role)
        if st.button("Reset this deal"):
            cid = st.session_state.get("cur_cycle")
            st.session_state.get("dna", {}).pop(cid, None)
            p = _reviewed_path(cid) if cid else None
            if p and p.exists():
                p.unlink()
            st.rerun()

    choice = st.selectbox(f"Deal ({len(filtered)} match)", list(labels.keys()))
    cycle_id = labels[choice]
    st.session_state["cur_cycle"] = cycle_id
    d = _get_dna(cycle_id)
    verdict = audit_dealdna(d)

    st.markdown(
        '<div class="rp-kpis">'
        + _kpi("Outcome", _badge(d.outcome.value))
        + _kpi("Calls", d.call_count) + _kpi("Drivers", len(d.drivers))
        + _kpi("Competitors", len(d.competitor_mentions))
        + _kpi("Audit", verdict.verdict)
        + "</div>", unsafe_allow_html=True)
    st.caption(f"{d.cycle_id} · opp {d.opportunity_id} · account {d.account} "
               f"· outcome source: {d.outcome_source} · transcript: {d.transcript_status.value}")
    _review_stepper(d.review.status)

    tabs = st.tabs(["🧬 Genome", "✅ Rep / Manager review", "🔀 Cross-functional",
                    "📜 Audit trail", "🛡 Guardrail"])
    with tabs[0]:
        st.components.v1.html(render_briefing(d), height=900, scrolling=True)
    with tabs[1]:
        _tab_review(d, cycle_id, role, actor_name)
    with tabs[2]:
        _render_feeds(d)
    with tabs[3]:
        _tab_audit(d)
    with tabs[4]:
        _tab_guard()


def _review_stepper(status: str) -> None:
    order = ["Needs Review", "Rep Reviewed", "Manager Validated"]
    cur = order.index(status) if status in order else 0
    parts = []
    for i, s in enumerate(order):
        parts.append(f'<span class="rp-step {"on" if i <= cur else ""}">{s}</span>')
        if i < len(order) - 1:
            parts.append('<span class="rp-arrow">→</span>')
    st.markdown('<div class="rp-steps">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def _tab_review(d: DealDNA, cycle_id: str, role: str, actor_name: str) -> None:
    is_rep = role == "Rep"
    is_mgr = role == "Manager"
    done = sum(1 for c in d.review.corrections if c.actor == "rep")
    st.progress(min(done / max(len(d.drivers), 1), 1.0),
                text=f"Rep decisions recorded: {done}/{len(d.drivers)}")
    st.caption(f"Acting as **{role}**. Review state is saved to disk and survives refresh.")
    st.markdown("#### Rep review — one decision per driver")
    if not d.drivers:
        st.info("No drivers to review.")
    for i, drv in enumerate(d.drivers):
        with st.container(border=True):
            st.markdown(f"**{drv.category.value} · {drv.direction.value} · {drv.confidence}** — {drv.summary}")
            st.caption(f'“{drv.quote}” — {drv.speaker} · {drv.timestamp} · {drv.source}')
            note = st.text_input("Context / challenge note", key=f"note-{cycle_id}-{i}",
                                 placeholder="Required for Add context / Challenge", disabled=not is_rep)
            cols = st.columns(3)
            if cols[0].button("✔ Confirm", key=f"confirm-{cycle_id}-{i}",
                              width="stretch", disabled=not is_rep):
                _record(d, actor_name, "confirmed", drv.category.value, "")
                st.rerun()
            if cols[1].button("＋ Add context", key=f"context-{cycle_id}-{i}",
                              width="stretch", disabled=not is_rep):
                if note.strip():
                    _record(d, actor_name, "added_context", drv.category.value, note.strip())
                    st.rerun()
                else:
                    st.warning("Add a note before submitting context.")
            if cols[2].button("✎ Challenge", key=f"challenge-{cycle_id}-{i}",
                              width="stretch", disabled=not is_rep):
                if note.strip():
                    _record(d, actor_name, "challenged", drv.category.value, note.strip())
                    st.rerun()
                else:
                    st.warning("Add a note explaining the challenge.")

    st.divider()
    st.markdown("#### Manager validation")
    can_validate = d.review.status == "Rep Reviewed" and is_mgr
    if d.review.status != "Manager Validated":
        if not is_mgr:
            st.info("Switch to the **Manager** role (sidebar) to validate.")
        elif d.review.status != "Rep Reviewed":
            st.info("Manager can validate once the rep has reviewed at least one driver.")
    if st.button("✅ Validate deal", disabled=not can_validate, type="primary"):
        d.review.corrections.append(ReviewCorrection(actor="manager", action="validated",
                                                     field="review", note=""))
        d.review.status = "Manager Validated"
        d.review.manager = actor_name
        d.review.reviewed_at = _now()
        _save_reviewed(d)
        st.success(f"Validated by {actor_name}. Saved (persists across refresh).")
    if st.button("💾 Save review snapshot"):
        st.success(f"Saved to {_save_reviewed(d)}")


def _tab_audit(d: DealDNA) -> None:
    st.markdown(_status_chip(d.review.status), unsafe_allow_html=True)
    st.caption(f"rep: {d.review.rep or '—'} · manager: {d.review.manager or '—'} "
               f"· reviewed_at: {d.review.reviewed_at or '—'}")
    if d.review.corrections:
        st.dataframe(pd.DataFrame([{"at": c.at, "actor": c.actor, "action": c.action,
                                    "field": c.field, "note": c.note} for c in d.review.corrections]),
                     width="stretch", hide_index=True)
    else:
        st.info("No corrections yet. Use the review tab to build the audit trail.")
    if d.unknowns:
        st.markdown("**Honest unknowns (abstention):**")
        for u in d.unknowns:
            st.write(f"- {u}")


def _tab_guard() -> None:
    st.markdown("#### Guardrail — Deal DNA is advisory and read-only")
    st.caption("Try asking it to take an action. It will refuse and route to human review.")
    instruction = st.text_input("Request an action",
                                placeholder="e.g. email the customer a discount")
    if instruction:
        screen = screen_action_request(instruction)
        if screen.allowed:
            st.markdown(f'<div class="rp-ok"><b>ALLOWED</b> — {screen.reason}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="rp-refuse"><b>REFUSED</b> — {screen.reason}</div>',
                        unsafe_allow_html=True)


def _record(d: DealDNA, rep: str, action: str, field: str, note: str) -> None:
    d.review.corrections.append(ReviewCorrection(actor="rep", action=action, field=field, note=note))
    d.review.rep = rep
    if d.review.status == "Needs Review":
        d.review.status = "Rep Reviewed"
    _save_reviewed(d)  # persist immediately so it survives refresh


def _render_feeds(d: DealDNA) -> None:
    feeds = d.cross_function_actions
    any_feed = False
    for name in ["enablement", "product", "pricing", "product_marketing", "implementations"]:
        actions = getattr(feeds, name)
        if not actions:
            continue
        any_feed = True
        st.markdown(f'<div class="rp-section">{name.replace("_", " ").title()}</div>',
                    unsafe_allow_html=True)
        for a in actions:
            with st.container(border=True):
                st.write(a.insight)
                st.caption(f"Recommended: {a.recommended_action}")
                st.caption(f"Owner: {a.owner_suggestion} · Recurrence: {a.recurrence} "
                           f"· {a.review_status.value}")
                with st.expander(f"{len(a.evidence_refs)} evidence refs"):
                    for r in a.evidence_refs:
                        st.caption(r)
    if not any_feed:
        st.info("No cross-functional actions for this deal.")

    if d.seller_coaching:
        c = d.seller_coaching
        st.markdown('<div class="rp-section">Seller coaching card</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write(c.situation)
            if c.stress_next:
                st.markdown("**Stress next:** " + "; ".join(c.stress_next))
            if c.verify_before:
                st.markdown("**Verify before:** " + "; ".join(c.verify_before))
            if c.avoid:
                st.markdown("**Avoid:** " + "; ".join(c.avoid))
            st.markdown(f"**Biggest unanswered question:** {c.biggest_unanswered_question}")
            if c.buyer_questions:
                st.markdown("**Likely buyer questions:** " + "; ".join(c.buyer_questions))
            st.markdown(f"**Proof to show:** {c.proof_to_show}")

    if d.implementation_handoff and d.implementation_handoff.applicable:
        h = d.implementation_handoff
        st.markdown('<div class="rp-section">Implementation handoff (Won deal)</div>',
                    unsafe_allow_html=True)
        with st.container(border=True):
            if h.expected_value:
                st.markdown("**Expected value:** " + "; ".join(h.expected_value))
            for it in h.items:
                st.caption(f"[{it.kind}] {it.summary} — responsible: {it.responsible}")
            if h.risks:
                st.markdown("**Risks:** " + "; ".join(h.risks))
    elif d.implementation_handoff:
        st.caption("Implementation handoff: not applicable (deal not Won).")


def page_ask() -> None:
    from deal_dna.agent import ask

    st.markdown(
        f'<div class="rp-hero"><h1>Ask Deal DNA</h1>'
        f'<div class="sub">A read-only agent that plans, calls analytics tools, and answers with '
        f'evidence. It never emails, writes to Salesforce, or contacts customers.</div>'
        f'<div style="margin-top:10px"><span class="pill">🧠 Engine: {_engine_label()}</span>'
        f'{_data_pill()}<span class="pill">tool-calling</span></div></div>',
        unsafe_allow_html=True)
    st.write("")

    examples = ["Where are we most exposed to Entrata?", "What is our win rate by product?",
                "Why did we lose cyc-004?", "What should enablement coach on?"]
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ask-ex-{i}", use_container_width=True):
            st.session_state["ask_q"] = ex

    q = st.text_input("Your question", key="ask_q",
                      placeholder="e.g. Where are we most exposed to Entrata?")
    if st.button("Ask Deal DNA", type="primary") and q.strip():
        with st.spinner("The agent is calling analytics tools…"):
            res = ask(q.strip())
        st.markdown(f'<span class="rp-status rep-reviewed">engine: {res.engine}</span>',
                    unsafe_allow_html=True)
        if res.tool_calls:
            with st.expander(f"🔧 Tools the agent called ({len(res.tool_calls)})", expanded=True):
                for tc in res.tool_calls:
                    arglist = ", ".join(f"{k}={v}" for k, v in tc.args.items())
                    st.markdown(f"- **{tc.name}**({arglist})")
        st.markdown("#### Answer")
        st.markdown(res.answer)
        st.caption("Grounded in read-only analytics · " + sources.provenance_note())


def main() -> None:
    st.set_page_config(page_title="Deal DNA", layout="wide", page_icon="🧬")
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

    if not list_cycles():
        st.error("No cycles found. Run:  python data/generate_data.py")
        return

    with st.sidebar:
        st.markdown("### 🧬 Deal DNA")
        page = st.radio("Workspace",
                        ["📊 Executive Portfolio", "🤖 Ask Deal DNA", "🔬 Deal Review"],
                        label_visibility="collapsed")
        st.divider()

    if page.startswith("📊"):
        page_portfolio()
    elif page.startswith("🤖"):
        page_ask()
    else:
        page_review()

    st.markdown(f'<div class="rp-note" style="margin-top:18px">{sources.provenance_note()} · '
                f'advisory &amp; read-only · no CRM write-back / outreach</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
