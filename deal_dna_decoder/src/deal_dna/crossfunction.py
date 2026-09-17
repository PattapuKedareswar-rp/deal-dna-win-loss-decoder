"""Cross-functional enrichment.

Turn an evidence-locked `DealDNA` into decisions for other teams, a seller coaching
card, and (for Won deals) an implementation handoff. Every recommendation is anchored to
the drivers that justify it — no action without evidence. Two paths mirror `evidence.py`:

- Offline (default / no key): deterministic mapping from `d.drivers`. Keeps tests and the
  demo reproducible.
- LLM (key present): structured output constrained to the same schema, falling back to the
  offline result on any error or if the model returns an action with no evidence.

Governance: this module never decides a price change or any external action. Pricing items
are phrased as review items; every action carries `review_status = Needs Review`.
"""
from __future__ import annotations

from . import llm
from .schema import (
    Category,
    CrossFunctionAction,
    CrossFunctionActions,
    DealDNA,
    Direction,
    Driver,
    EvidenceLabel,
    HandoffItem,
    ImplementationHandoff,
    Outcome,
    SellerCoaching,
)

# audience -> (driver categories that feed it, owner suggestion)
_FEED_MAP: dict[str, tuple[set[Category], str]] = {
    "enablement": ({Category.DEMO, Category.TRUST, Category.AUTHORITY}, "Sales Enablement"),
    "product": ({Category.PRODUCT, Category.INTEGRATION, Category.DEMO}, "Product Management"),
    "pricing": ({Category.PRICING, Category.ROI}, "Pricing / Deal Desk"),
    "product_marketing": ({Category.ROI, Category.RISK, Category.COMPETITOR}, "Product Marketing"),
    "implementations": ({Category.IMPLEMENTATION, Category.RISK}, "Implementation / Customer Success"),
}


def _ref(d: Driver) -> str:
    """A single evidence reference: timestamp, source, verbatim quote."""
    return f'{d.timestamp} {d.source} — "{d.quote}"'


def _short(text: str, n: int = 90) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = x.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _insight(audience: str, drivers: list[Driver]) -> str:
    if not drivers:
        return f"Alternative-software mentions relevant to {audience.replace('_', ' ')}."
    top = drivers[0]
    cats = sorted({d.category.value for d in drivers})
    neg = sum(1 for d in drivers if d.direction == Direction.NEGATIVE)
    pos = sum(1 for d in drivers if d.direction == Direction.POSITIVE)
    tone = "hesitation" if neg > pos else "strength" if pos > neg else "signal"
    return (f"{len(drivers)} {tone}(s) across {', '.join(cats)}. "
            f"Lead example: “{_short(top.quote)}” ({top.category.value}).")


def _recommended_action(audience: str, drivers: list[Driver],
                        competitors: list[str] | None = None) -> str:
    q = _short(drivers[0].quote) if drivers else ""
    if audience == "pricing":
        return (f"Deal Desk: review packaging / TCO against the buyer's words — “{q}”. "
                f"Review item, NOT an approved price change.")
    if audience == "product_marketing":
        comp = ", ".join(sorted(set(competitors or []))) or "no named alternative"
        return f"Sharpen messaging / proof against “{q}”; competitive context: {comp}."
    verbs = {
        "enablement": f"Coach reps on this moment — “{q}”; build a play from the cited quotes.",
        "product": f"Log the capability / roadmap gap evidenced by “{q}” for triage.",
        "implementations": f"Set post-sale expectations from “{q}” before kickoff.",
    }
    return verbs.get(audience, "Route to the owning team for review.")


def _build_feeds(d: DealDNA) -> CrossFunctionActions:
    feeds = CrossFunctionActions()
    comp_names = [m.name for m in d.competitor_mentions]
    for audience, (cats, owner) in _FEED_MAP.items():
        supporting = [drv for drv in d.drivers if drv.category in cats]
        refs = [_ref(drv) for drv in supporting]
        # product_marketing also carries competitor mentions as evidence.
        if audience == "product_marketing":
            for m in d.competitor_mentions:
                refs.append(f'{m.timestamp} {m.source} — "{m.quote}"')
        if not refs:
            continue  # no action without evidence
        action = CrossFunctionAction(
            audience=audience,
            insight=_insight(audience, supporting),
            evidence_refs=refs,
            recommended_action=_recommended_action(audience, supporting, comp_names),
            owner_suggestion=owner,
            recurrence="single cycle",
            review_status=EvidenceLabel.NEEDS_REVIEW,
        )
        getattr(feeds, audience).append(action)
    return feeds


def _build_coaching(d: DealDNA) -> SellerCoaching:
    pos = [drv for drv in d.drivers if drv.direction == Direction.POSITIVE]
    neg = [drv for drv in d.drivers if drv.direction == Direction.NEGATIVE]
    won = d.outcome == Outcome.WON

    situation = (f"{d.account}: {d.outcome.value} ({d.outcome_source}). "
                 f"{len(d.drivers)} evidence-backed drivers across {d.call_count} call(s).")

    stress_next = _dedupe([f"Reinforce: {drv.summary}" for drv in pos])[:3] or \
        ["No positive drivers observed — do not assume strengths."]
    verify_before = _dedupe([f"Verify: {u}" for u in d.unknowns])[:3] or \
        ["No open unknowns recorded — confirm decision criteria anyway."]
    avoid = _dedupe([f"Do not repeat: {drv.summary}" for drv in neg])[:3] or \
        ["No negative drivers observed."]

    biggest = d.unknowns[0] if d.unknowns else "No unknowns recorded in evidence."
    buyer_questions = _dedupe(
        [f"What would resolve “{_short(drv.quote)}” for your team?" for drv in neg])[:3]
    while len(buyer_questions) < 3:
        extra = "What would make this an easy yes for your team?"
        if extra in buyer_questions:
            break
        buyer_questions.append(extra)
    proof = next((f'Show: "{drv.quote}" ({drv.category.value})' for drv in pos
                  if drv.category in (Category.ROI, Category.TRUST)),
                 "No ROI/trust proof captured in evidence.")

    return SellerCoaching(
        situation=situation, stress_next=stress_next, verify_before=verify_before, avoid=avoid,
        biggest_unanswered_question=biggest, buyer_questions=buyer_questions[:3],
        proof_to_show=proof, next_step_owner="Account team",
        confidence="high" if won else "medium", review_status=EvidenceLabel.NEEDS_REVIEW,
    )


# driver category -> (handoff kind, responsible party)
_HANDOFF_KIND: dict[Category, tuple[str, str]] = {
    Category.NEED: ("requested", "Account team"),
    Category.ROI: ("inferred_expectation", "Account team"),
    Category.IMPLEMENTATION: ("promised", "Seller / Implementation"),
    Category.RISK: ("dependency", "Implementation"),
    Category.INTEGRATION: ("dependency", "Implementation"),
    Category.PRODUCT: ("unresolved", "Product"),
    Category.PRICING: ("dependency", "Deal Desk"),
}
# Categories whose commitments need explicit confirmation before delivery.
_CONFIRM_CATS = {Category.PRICING, Category.PRODUCT, Category.INTEGRATION}


def _build_handoff(d: DealDNA) -> ImplementationHandoff:
    applicable = d.outcome == Outcome.WON
    handoff = ImplementationHandoff(applicable=applicable)
    if not applicable:
        return handoff
    seen: set[tuple] = set()
    for drv in d.drivers:
        key = (drv.category, drv.quote)
        if key in seen:
            continue
        seen.add(key)
        kind, responsible = _HANDOFF_KIND.get(drv.category, ("inferred_expectation", "Account team"))
        summary = drv.summary
        if drv.category in _CONFIRM_CATS:
            summary += " [requires Product/Legal/Deal-Desk confirmation]"
        handoff.items.append(HandoffItem(
            kind=kind, summary=summary, quote=drv.quote, speaker=drv.speaker,
            timestamp=drv.timestamp, source=drv.source, responsible=responsible,
            risk_if_unresolved=("Unmet risk carried into onboarding." if drv.direction == Direction.NEGATIVE
                                else "Expectation gap at kickoff."),
        ))
    handoff.expected_value = _dedupe(
        [f'{drv.summary} — "{_short(drv.quote)}"' for drv in d.drivers
         if drv.direction == Direction.POSITIVE
         and drv.category in (Category.ROI, Category.NEED, Category.TRUST)])
    handoff.risks = _dedupe(
        [f'{drv.summary} — "{_short(drv.quote)}"' for drv in d.drivers
         if drv.direction == Direction.NEGATIVE])
    return handoff


def _enrich_offline(d: DealDNA) -> DealDNA:
    d.cross_function_actions = _build_feeds(d)
    d.seller_coaching = _build_coaching(d)
    d.implementation_handoff = _build_handoff(d)
    return d


_LLM_SYSTEM = (
    "You are Deal DNA's cross-functional analyst. You are given an evidence-locked deal with "
    "drivers (each a verbatim buyer quote). Produce cross-functional actions, a seller coaching "
    "card, and — only for Won deals — an implementation handoff. EVERY action MUST set "
    "evidence_refs to the supporting driver quotes/timestamps; never emit an action with no "
    "evidence. NEVER recommend a price change as a decision — phrase pricing as a review item. "
    "Make no personality judgments; if evidence is missing, say so. Return JSON with keys "
    "'cross_function_actions', 'seller_coaching', 'implementation_handoff' matching the schema."
)


def enrich_crossfunctional(d: DealDNA) -> DealDNA:
    """Fill the enrichment fields on `d` and return it. Pure: input DealDNA, output DealDNA."""
    if llm.is_offline():
        return _enrich_offline(d)
    try:
        from pydantic import BaseModel

        class _Enrichment(BaseModel):
            cross_function_actions: CrossFunctionActions = CrossFunctionActions()
            seller_coaching: SellerCoaching | None = None
            implementation_handoff: ImplementationHandoff | None = None

        drivers = "\n".join(
            f"[{drv.timestamp}] ({drv.category.value}/{drv.direction.value}) "
            f"{drv.speaker}: {drv.quote} (source={drv.source})" for drv in d.drivers
        )
        user = (f"Account: {d.account}\nOutcome: {d.outcome.value}\n"
                f"Unknowns: {d.unknowns}\nDrivers:\n{drivers}")
        out = llm.structured_json(_LLM_SYSTEM, user, _Enrichment)
        feeds = out.cross_function_actions
        all_actions = (feeds.enablement + feeds.product + feeds.pricing
                       + feeds.product_marketing + feeds.implementations)
        if all_actions and all(a.evidence_refs for a in all_actions):
            d.cross_function_actions = feeds
            d.seller_coaching = out.seller_coaching or _build_coaching(d)
            handoff = out.implementation_handoff or _build_handoff(d)
            handoff.applicable = d.outcome == Outcome.WON  # authority stays deterministic
            d.implementation_handoff = handoff
            return d
    except Exception:
        pass
    return _enrich_offline(d)
