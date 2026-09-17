"""Cycle synthesizer — the seam Person A provides: `synthesize_cycle(cycle_id) -> DealDNA`.

Rolls all calls of a cycle into ONE observation (never counts calls as deals), takes the
outcome from Salesforce (the authority), aggregates evidence-backed drivers and competitor
mentions, and records honest unknowns.
"""
from __future__ import annotations

from collections import Counter

from . import salesforce
from .evidence import extract_call
from .intake import gate
from .normalize import load_cycle
from .schema import (Category, CompetitorMention, DealDNA, Driver, Outcome,
                     Review, TranscriptStatus)


def _collect(cycle) -> tuple[list[Driver], list[CompetitorMention]]:
    drivers: list[Driver] = []
    mentions: list[CompetitorMention] = []
    for call in cycle.calls:
        d, m = extract_call(call)
        drivers.extend(d)
        mentions.extend(m)
    return drivers, mentions


def _calibrate_confidence(drivers: list[Driver]) -> None:
    """A category seen only once in the cycle is weaker evidence: medium -> low."""
    counts = Counter(d.category for d in drivers)
    for d in drivers:
        if counts[d.category] == 1 and d.confidence == "medium":
            d.confidence = "low"


def _unknowns(drivers: list[Driver], outcome: Outcome) -> list[str]:
    cats = {d.category for d in drivers}
    unknowns: list[str] = []
    if Category.AUTHORITY not in cats:
        unknowns.append("Decision authority not observed.")
    if outcome == Outcome.WON and Category.ROI not in cats:
        unknowns.append("ROI / value evidence not observed on a Won deal.")
    if outcome == Outcome.LOST and Category.PRICING not in cats:
        unknowns.append("Pricing sentiment not observed on a Lost deal.")
    if outcome == Outcome.LOST and not (
        {Category.PRICING, Category.PRODUCT, Category.INTEGRATION, Category.DEMO} & cats
    ):
        unknowns.append("Primary loss driver not clearly evidenced; needs review.")
    return unknowns


def synthesize_cycle(cycle_id: str) -> DealDNA:
    cycle = load_cycle(cycle_id)
    intake = gate(cycle)

    first_meta = cycle.calls[0].metadata if cycle.calls else {}
    row = salesforce.opportunity_for_cycle(first_meta)
    outcome = salesforce.outcome_from_row(row)
    account = intake.account or (row or {}).get("account", "")
    product = intake.product or (row or {}).get("product_family", "")

    drivers, mentions = _collect(cycle)
    _calibrate_confidence(drivers)

    # A competitor mention can only be a loss reason on a Lost deal (abstention guard).
    if outcome != Outcome.LOST:
        for m in mentions:
            m.is_loss_reason = False
            m.note = "Mention only; not established as a loss reason."

    review = Review(status="Needs Review")
    if not intake.ok:
        review.status = "Blocked" if intake.transcript_status == TranscriptStatus.NONE else "Needs Review"

    return DealDNA(
        cycle_id=cycle_id,
        opportunity_id=intake.opportunity_id or (row or {}).get("opportunity_id", ""),
        account=account,
        product_families=[product] if product else [],
        outcome=outcome,
        outcome_source="Salesforce IsWon",
        transcript_status=intake.transcript_status,
        call_count=len(cycle.calls),
        drivers=drivers,
        competitor_mentions=mentions,
        unknowns=_unknowns(drivers, outcome) + intake.issues,
        review=review,
    )
