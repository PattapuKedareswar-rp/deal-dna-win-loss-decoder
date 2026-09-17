"""Market-signal radar (aggregate across cycles).

Surfaces recurring hesitations and alternative-software mentions, but only when they recur
often enough to reduce false alarms. Aggregates deterministically from DealDNA objects.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .schema import DealDNA, Direction

MIN_RECURRENCE = 2  # precision guard: don't surface one-off signals as trends


@dataclass
class RadarSignal:
    label: str
    count: int
    cycles: list[str] = field(default_factory=list)


@dataclass
class RadarReport:
    recurring_hesitations: list[RadarSignal] = field(default_factory=list)
    alternative_software: list[RadarSignal] = field(default_factory=list)
    note: str = f"Only signals recurring in >= {MIN_RECURRENCE} cycles are shown (false-alarm guard)."


def build_radar(deals: list[DealDNA]) -> RadarReport:
    hes_cycles: dict[str, set[str]] = defaultdict(set)
    comp_cycles: dict[str, set[str]] = defaultdict(set)

    for d in deals:
        for drv in d.drivers:
            if drv.direction in (Direction.NEGATIVE, Direction.MIXED):
                hes_cycles[drv.category.value].add(d.cycle_id)
        for m in d.competitor_mentions:
            comp_cycles[m.name].add(d.cycle_id)

    def _signals(mapping: dict[str, set[str]]) -> list[RadarSignal]:
        out = [RadarSignal(label=k, count=len(v), cycles=sorted(v))
               for k, v in mapping.items() if len(v) >= MIN_RECURRENCE]
        return sorted(out, key=lambda s: s.count, reverse=True)

    return RadarReport(
        recurring_hesitations=_signals(hes_cycles),
        alternative_software=_signals(comp_cycles),
    )
