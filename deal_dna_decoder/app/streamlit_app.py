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

import pandas as pd
import streamlit as st

from deal_dna import config
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


def _load(cycle_id: str) -> DealDNA:
    return enrich_crossfunctional(synthesize_cycle(cycle_id))


def _get_dna(cycle_id: str) -> DealDNA:
    store = st.session_state.setdefault("dna", {})
    if cycle_id not in store:
        store[cycle_id] = _load(cycle_id)
    return store[cycle_id]


def _save_reviewed(d: DealDNA) -> Path:
    out = config.OUTPUTS_DIR / "reviewed" / f"{d.cycle_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d.model_dump(mode="json"), indent=2, default=str), encoding="utf-8")
    return out


def _kpi(label: str, value, kind: str = "") -> str:
    return f'<div class="rp-kpi {kind}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def _badge(outcome: str) -> str:
    return f'<span class="rp-badge {_OUTCOME_CLASS.get(outcome, "review")}">{outcome}</span>'


def _status_chip(status: str) -> str:
    return f'<span class="rp-status {_STATUS_CLASS.get(status, "needs-review")}">Review: {status}</span>'


# ---------- Portfolio page ----------
def page_portfolio() -> None:
    report, radar = _portfolio()
    st.markdown(
        '<div class="rp-hero"><h1>Deal DNA — Executive Portfolio</h1>'
        '<div class="sub">Why we win and lose, decoded from sales conversations — '
        'evidence-backed, advisory, human-in-the-loop.</div>'
        '<div style="margin-top:8px"><span class="pill">SYNTHETIC data</span>'
        '<span class="pill">read-only</span><span class="pill">no CRM write-back</span></div></div>',
        unsafe_allow_html=True)

    st.markdown(
        '<div class="rp-kpis">'
        + _kpi(f"Win rate ({report.won + report.lost} closed)", f"{report.win_rate:.0%}", "good")
        + _kpi("Won", report.won, "good") + _kpi("Lost", report.lost, "bad")
        + _kpi("Stalled", report.stalled, "warn") + _kpi("Cycles", report.total_cycles)
        + "</div>", unsafe_allow_html=True)

    st.markdown('<div class="rp-section">Win rate by product</div>', unsafe_allow_html=True)
    prod_df = pd.DataFrame(
        [{"product": p, "win_rate": round(wr * 100), "closed": n}
         for p, wr, n in report.win_rate_by_product]).set_index("product")
    st.bar_chart(prod_df[["win_rate"]], color="#082649", height=240)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="rp-section">Top win drivers</div>', unsafe_allow_html=True)
        if report.top_win_drivers:
            st.bar_chart(pd.DataFrame(report.top_win_drivers, columns=["driver", "count"])
                         .set_index("driver"), color="#2E8B57", height=220)
    with c2:
        st.markdown('<div class="rp-section">Top loss drivers</div>', unsafe_allow_html=True)
        if report.top_loss_drivers:
            st.bar_chart(pd.DataFrame(report.top_loss_drivers, columns=["driver", "count"])
                         .set_index("driver"), color="#D2402A", height=220)

    st.markdown('<div class="rp-section">Competitor battlecards</div>', unsafe_allow_html=True)
    st.caption("Where we are exposed and why — each with evidence. A mention is not a loss reason.")
    for b in report.battlecards:
        klass = "hot" if b.loss_rate >= 0.75 else "mid" if b.loss_rate >= 0.4 else "cool"
        drivers = ", ".join(f"{c} ({n})" for c, n in b.top_loss_drivers) or "—"
        quote = f'<blockquote>“{b.sample_quote[:120]}”</blockquote>' if b.sample_quote else ""
        st.markdown(
            f'<div class="rp-bc {klass}"><h4>{b.competitor}</h4>'
            f'<div class="meta">{b.deals} deal(s) · Won {b.won} / Lost {b.lost} · '
            f'loss rate {b.loss_rate:.0%} · top loss drivers: {drivers}</div>{quote}</div>',
            unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="rp-section">Enablement coaching hotspots</div>', unsafe_allow_html=True)
        if report.coaching_hotspots:
            st.bar_chart(pd.DataFrame(report.coaching_hotspots, columns=["theme", "count"])
                         .set_index("theme"), color="#AE6B29", height=220)
    with c4:
        st.markdown('<div class="rp-section">Market-signal radar</div>', unsafe_allow_html=True)
        st.caption(radar.note)
        if radar.recurring_hesitations:
            st.write("**Recurring hesitations**")
            for s in radar.recurring_hesitations:
                st.write(f"- {s.label}: {s.count} cycles")
        if radar.alternative_software:
            st.write("**Alternative software mentioned**")
            for s in radar.alternative_software:
                st.write(f"- {s.label}: {s.count} cycles")

    html = (config.OUTPUTS_DIR / "portfolio.html")
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
                'review, and route cross-functional actions.</div></div>', unsafe_allow_html=True)

    if not filtered:
        st.warning("No deals match the current filters.")
        return

    labels = {f'{r["cycle_id"]} · {r["account"]} · {r["outcome"]}': r["cycle_id"] for r in filtered}
    with st.sidebar:
        rep_name = st.text_input("Rep name", value="Rep")
        manager_name = st.text_input("Manager name", value="Manager")
        if st.button("Reset this deal"):
            st.session_state.get("dna", {}).pop(st.session_state.get("cur_cycle"), None)
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
        _tab_review(d, cycle_id, rep_name, manager_name)
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


def _tab_review(d: DealDNA, cycle_id: str, rep_name: str, manager_name: str) -> None:
    done = sum(1 for c in d.review.corrections if c.actor == "rep")
    st.progress(min(done / max(len(d.drivers), 1), 1.0),
                text=f"Rep decisions recorded: {done}/{len(d.drivers)}")
    st.markdown("#### Rep review — one decision per driver")
    if not d.drivers:
        st.info("No drivers to review.")
    for i, drv in enumerate(d.drivers):
        with st.container(border=True):
            st.markdown(f"**{drv.category.value} · {drv.direction.value} · {drv.confidence}** — {drv.summary}")
            st.caption(f'“{drv.quote}” — {drv.speaker} · {drv.timestamp} · {drv.source}')
            note = st.text_input("Context / challenge note", key=f"note-{cycle_id}-{i}",
                                 placeholder="Required for Add context / Challenge")
            cols = st.columns(3)
            if cols[0].button("✔ Confirm", key=f"confirm-{cycle_id}-{i}", use_container_width=True):
                _record(d, rep_name, "confirmed", drv.category.value, "")
                st.rerun()
            if cols[1].button("＋ Add context", key=f"context-{cycle_id}-{i}", use_container_width=True):
                if note.strip():
                    _record(d, rep_name, "added_context", drv.category.value, note.strip())
                    st.rerun()
                else:
                    st.warning("Add a note before submitting context.")
            if cols[2].button("✎ Challenge", key=f"challenge-{cycle_id}-{i}", use_container_width=True):
                if note.strip():
                    _record(d, rep_name, "challenged", drv.category.value, note.strip())
                    st.rerun()
                else:
                    st.warning("Add a note explaining the challenge.")

    st.divider()
    st.markdown("#### Manager validation")
    can_validate = d.review.status == "Rep Reviewed"
    if not can_validate and d.review.status != "Manager Validated":
        st.info("Manager can validate once the rep has reviewed at least one driver.")
    if st.button("✅ Validate deal", disabled=not can_validate, type="primary"):
        d.review.corrections.append(ReviewCorrection(actor="manager", action="validated",
                                                     field="review", note=""))
        d.review.status = "Manager Validated"
        d.review.manager = manager_name
        d.review.reviewed_at = _now()
        st.success(f"Validated by {manager_name}. Saved to {_save_reviewed(d)}")
    if st.button("💾 Save review snapshot"):
        st.success(f"Saved to {_save_reviewed(d)}")


def _tab_audit(d: DealDNA) -> None:
    st.markdown(_status_chip(d.review.status), unsafe_allow_html=True)
    st.caption(f"rep: {d.review.rep or '—'} · manager: {d.review.manager or '—'} "
               f"· reviewed_at: {d.review.reviewed_at or '—'}")
    if d.review.corrections:
        st.dataframe(pd.DataFrame([{"at": c.at, "actor": c.actor, "action": c.action,
                                    "field": c.field, "note": c.note} for c in d.review.corrections]),
                     use_container_width=True, hide_index=True)
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


def main() -> None:
    st.set_page_config(page_title="Deal DNA", layout="wide", page_icon="🧬")
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

    if not list_cycles():
        st.error("No cycles found. Run:  python data/generate_data.py")
        return

    with st.sidebar:
        st.markdown("### 🧬 Deal DNA")
        page = st.radio("Workspace", ["📊 Executive Portfolio", "🔬 Deal Review"], label_visibility="collapsed")
        st.divider()

    if page.startswith("📊"):
        page_portfolio()
    else:
        page_review()

    st.markdown(f'<div class="rp-note" style="margin-top:18px">{config.DATA_NOTE} · '
                f'advisory &amp; read-only · no CRM write-back / outreach</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
