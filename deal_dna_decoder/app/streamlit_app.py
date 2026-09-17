"""Deal DNA — review web app (Person B).

A rep -> manager approval loop over an evidence-locked DealDNA. The app is advisory and
read-only toward the outside world: it never emails, writes to Salesforce, or publishes.
Any such request is routed to the guardrail and refused, with the refusal shown in-app.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from deal_dna import config
from deal_dna.audit import audit_dealdna, screen_action_request
from deal_dna.crossfunction import enrich_crossfunctional
from deal_dna.normalize import list_cycles
from deal_dna.render import render_briefing
from deal_dna.schema import DealDNA, ReviewCorrection
from deal_dna.synthesize import synthesize_cycle

_CSS = (Path(__file__).parent / "static" / "colorway.css").read_text(encoding="utf-8")
_STATUS_CLASS = {
    "Needs Review": "needs-review",
    "Rep Reviewed": "rep-reviewed",
    "Manager Validated": "manager-validated",
    "Blocked": "blocked",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(cycle_id: str) -> DealDNA:
    """Build a fresh, enriched DealDNA for a cycle (offline-safe)."""
    return enrich_crossfunctional(synthesize_cycle(cycle_id))


def _get_dna(cycle_id: str) -> DealDNA:
    store = st.session_state.setdefault("dna", {})
    if cycle_id not in store:
        store[cycle_id] = _load(cycle_id)
    return store[cycle_id]


def _status_chip(status: str) -> str:
    cls = _STATUS_CLASS.get(status, "needs-review")
    return f'<span class="rp-status {cls}">Review: {status}</span>'


def _save_reviewed(d: DealDNA) -> Path:
    out = config.OUTPUTS_DIR / "reviewed" / f"{d.cycle_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d.model_dump(mode="json"), indent=2, default=str), encoding="utf-8")
    return out


def main() -> None:
    st.set_page_config(page_title="Deal DNA — Review", layout="wide")
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

    st.markdown('<h1 class="rp-title">Deal DNA — Win/Loss Review</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="rp-note">{config.DATA_NOTE} · advisory & read-only</div>',
                unsafe_allow_html=True)

    cycles = list_cycles()
    if not cycles:
        st.error("No cycles found. Run:  python data/generate_data.py")
        return

    with st.sidebar:
        cycle_id = st.selectbox("Deal cycle", cycles)
        rep_name = st.text_input("Rep name", value="Rep")
        manager_name = st.text_input("Manager name", value="Manager")
        if st.button("Reset this deal"):
            st.session_state.get("dna", {}).pop(cycle_id, None)
            st.rerun()

    d = _get_dna(cycle_id)
    verdict = audit_dealdna(d)

    top = st.columns([3, 2])
    with top[0]:
        st.subheader(f"{d.account} — {d.outcome.value}")
        st.caption(f"{d.cycle_id} · opp {d.opportunity_id} · {d.call_count} call(s) "
                   f"· outcome source: {d.outcome_source}")
    with top[1]:
        st.markdown(_status_chip(d.review.status), unsafe_allow_html=True)
        st.caption(f"Audit: {verdict.verdict}")

    tab_genome, tab_review, tab_feeds, tab_audit, tab_guard = st.tabs(
        ["Genome", "Rep / Manager review", "Cross-functional", "Audit trail", "Guardrail"])

    with tab_genome:
        st.components.v1.html(render_briefing(d), height=900, scrolling=True)

    with tab_review:
        st.markdown("#### Rep review — one decision per driver")
        if not d.drivers:
            st.info("No drivers to review.")
        for i, drv in enumerate(d.drivers):
            with st.container(border=True):
                st.markdown(f"**{drv.category.value} · {drv.direction.value}** — {drv.summary}")
                st.caption(f'“{drv.quote}” — {drv.speaker} · {drv.timestamp} · {drv.source}')
                note = st.text_input("Context / challenge note", key=f"note-{cycle_id}-{i}",
                                     placeholder="Required for Add context / Challenge")
                cols = st.columns(3)
                if cols[0].button("Confirm", key=f"confirm-{cycle_id}-{i}"):
                    _record(d, rep_name, "confirmed", drv.category.value, "")
                    st.rerun()
                if cols[1].button("Add context", key=f"context-{cycle_id}-{i}"):
                    if note.strip():
                        _record(d, rep_name, "added_context", drv.category.value, note.strip())
                        st.rerun()
                    else:
                        st.warning("Add a note before submitting context.")
                if cols[2].button("Challenge", key=f"challenge-{cycle_id}-{i}"):
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
        if st.button("Validate deal", disabled=not can_validate):
            d.review.corrections.append(ReviewCorrection(
                actor="manager", action="validated", field="review", note=""))
            d.review.status = "Manager Validated"
            d.review.manager = manager_name
            d.review.reviewed_at = _now()
            path = _save_reviewed(d)
            st.success(f"Validated by {manager_name}. Saved to {path}")

        if st.button("Save review snapshot"):
            path = _save_reviewed(d)
            st.success(f"Saved to {path}")

    with tab_feeds:
        _render_feeds(d)

    with tab_audit:
        st.markdown(_status_chip(d.review.status), unsafe_allow_html=True)
        st.caption(f"rep: {d.review.rep or '—'} · manager: {d.review.manager or '—'} "
                   f"· reviewed_at: {d.review.reviewed_at or '—'}")
        if d.review.corrections:
            st.table([{"at": c.at, "actor": c.actor, "action": c.action,
                       "field": c.field, "note": c.note} for c in d.review.corrections])
        else:
            st.info("No corrections yet.")

    with tab_guard:
        st.markdown("#### Guardrail — Deal DNA is advisory and read-only")
        instruction = st.text_input(
            "Request an action", placeholder="e.g. email the customer a discount")
        if instruction:
            screen = screen_action_request(instruction)
            if screen.allowed:
                st.success(f"ALLOWED — {screen.reason}")
            else:
                st.markdown(f'<div class="rp-refuse"><b>REFUSED</b> — {screen.reason}</div>',
                            unsafe_allow_html=True)


def _record(d: DealDNA, rep: str, action: str, field: str, note: str) -> None:
    d.review.corrections.append(ReviewCorrection(
        actor="rep", action=action, field=field, note=note))
    d.review.rep = rep
    if d.review.status == "Needs Review":
        d.review.status = "Rep Reviewed"


def _render_feeds(d: DealDNA) -> None:
    feeds = d.cross_function_actions
    for name in ["enablement", "product", "pricing", "product_marketing", "implementations"]:
        actions = getattr(feeds, name)
        if not actions:
            continue
        st.markdown(f"#### {name.replace('_', ' ').title()}")
        for a in actions:
            with st.container(border=True):
                st.write(a.insight)
                st.caption(f"Recommended: {a.recommended_action}")
                st.caption(f"Owner: {a.owner_suggestion} · Recurrence: {a.recurrence} "
                           f"· {a.review_status.value}")
                with st.expander(f"{len(a.evidence_refs)} evidence refs"):
                    for r in a.evidence_refs:
                        st.caption(r)

    if d.seller_coaching:
        c = d.seller_coaching
        st.markdown("#### Seller coaching card")
        with st.container(border=True):
            st.write(c.situation)
            st.markdown("**Stress next:** " + "; ".join(c.stress_next))
            st.markdown("**Verify before:** " + "; ".join(c.verify_before))
            st.markdown("**Avoid:** " + "; ".join(c.avoid))
            st.markdown(f"**Biggest unanswered question:** {c.biggest_unanswered_question}")
            st.markdown("**Likely buyer questions:** " + "; ".join(c.buyer_questions))
            st.markdown(f"**Proof to show:** {c.proof_to_show}")

    if d.implementation_handoff and d.implementation_handoff.applicable:
        h = d.implementation_handoff
        st.markdown("#### Implementation handoff (Won deal)")
        with st.container(border=True):
            if h.expected_value:
                st.markdown("**Expected value:** " + "; ".join(h.expected_value))
            for it in h.items:
                st.caption(f"[{it.kind}] {it.summary} — responsible: {it.responsible}")
            if h.risks:
                st.markdown("**Risks:** " + "; ".join(h.risks))
    elif d.implementation_handoff:
        st.caption("Implementation handoff: not applicable (deal not Won).")


if __name__ == "__main__":
    main()
