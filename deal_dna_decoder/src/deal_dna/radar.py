"""Market-signal radar (aggregate across cycles).

Surfaces recurring hesitations and alternative-software mentions, but only when they recur
often enough to reduce false alarms. Aggregates deterministically from DealDNA objects.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .schema import DealDNA, Direction

MIN_RECURRENCE = 2  # precision guard: a trend needs >= 2 distinct ACCOUNTS, not one noisy deal


@dataclass
class RadarSignal:
    label: str
    count: int
    cycles: list[str] = field(default_factory=list)
    accounts: int = 0


@dataclass
class RadarReport:
    recurring_hesitations: list[RadarSignal] = field(default_factory=list)
    alternative_software: list[RadarSignal] = field(default_factory=list)
    note: str = (f"Only signals recurring across >= {MIN_RECURRENCE} distinct accounts are shown "
                 f"(false-alarm guard).")


def build_radar(deals: list[DealDNA]) -> RadarReport:
    hes_cycles: dict[str, set[str]] = defaultdict(set)
    hes_accounts: dict[str, set[str]] = defaultdict(set)
    comp_cycles: dict[str, set[str]] = defaultdict(set)
    comp_accounts: dict[str, set[str]] = defaultdict(set)

    for d in deals:
        for drv in d.drivers:
            if drv.direction in (Direction.NEGATIVE, Direction.MIXED):
                hes_cycles[drv.category.value].add(d.cycle_id)
                hes_accounts[drv.category.value].add(d.account)
        for m in d.competitor_mentions:
            comp_cycles[m.name].add(d.cycle_id)
            comp_accounts[m.name].add(d.account)

    def _signals(cyc: dict[str, set[str]], acct: dict[str, set[str]]) -> list[RadarSignal]:
        out = [RadarSignal(label=k, count=len(cyc[k]), cycles=sorted(cyc[k]), accounts=len(acct[k]))
               for k in cyc if len(acct[k]) >= MIN_RECURRENCE]
        return sorted(out, key=lambda s: s.count, reverse=True)

    return RadarReport(
        recurring_hesitations=_signals(hes_cycles, hes_accounts),
        alternative_software=_signals(comp_cycles, comp_accounts),
    )
