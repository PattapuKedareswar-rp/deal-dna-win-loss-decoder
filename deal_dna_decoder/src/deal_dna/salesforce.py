"""Salesforce outcome map access (read-only) — the authority for deal outcome.

Loads the synthetic `salesforce/opportunities.csv`. Never writes back to Salesforce.
"""
from __future__ import annotations

import csv
from functools import lru_cache

from . import config
from .schema import Outcome

_OUTCOME_BY_VALUE = {o.value: o for o in Outcome}


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    path = config.SALESFORCE_DIR / "opportunities.csv"
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["opportunity_id"]] = row
    return rows


def opportunity_for_cycle(cycle_meta: dict) -> dict | None:
    """Resolve the Salesforce opportunity row from a call's metadata."""
    opp_id = cycle_meta.get("opportunity_id")
    if not opp_id:
        return None
    return _load().get(opp_id)


def outcome_from_row(row: dict | None) -> Outcome:
    if not row:
        return Outcome.NEEDS_REVIEW
    return _OUTCOME_BY_VALUE.get(row.get("outcome", ""), Outcome.NEEDS_REVIEW)
