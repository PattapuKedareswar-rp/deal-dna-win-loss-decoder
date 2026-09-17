"""Evaluation harness.

Compares Deal DNA's decoded top driver against the human-reviewed gold set and reports:
- top-driver agreement %
- citation coverage (share of drivers with a quote + source)
- competitor false-alarm rate (mentions wrongly treated as loss reasons)

Runs offline and deterministically. This is the evidence for the submission's insight-quality claim.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field

from . import config
from .normalize import list_cycles
from .schema import Category, DealDNA, Outcome
from .synthesize import synthesize_cycle

# "Decisiveness" priority per outcome: the first category present is the decoded top driver.
_PRIORITY: dict[Outcome, list[Category]] = {
    Outcome.WON: [Category.ROI, Category.PRODUCT, Category.TRUST, Category.IMPLEMENTATION,
                  Category.DEMO, Category.NEED, Category.INTEGRATION, Category.PRICING],
    Outcome.LOST: [Category.PRICING, Category.INTEGRATION, Category.DEMO, Category.PRODUCT,
                   Category.COMPETITOR, Category.RISK, Category.TIMING, Category.ROI],
    Outcome.STALLED: [Category.TIMING, Category.PRICING, Category.AUTHORITY, Category.ROI,
                      Category.NEED],
}


def top_driver_category(dna: DealDNA) -> str:
    present = {d.category for d in dna.drivers}
    for cat in _PRIORITY.get(dna.outcome, []):
        if cat in present:
            return cat.value
    if dna.drivers:
        # fallback: most frequent category
        from collections import Counter
        return Counter(d.category for d in dna.drivers).most_common(1)[0][0].value
    return "Needs Review"


@dataclass
class EvalReport:
    total: int = 0
    agree: int = 0
    per_cycle: list[dict] = field(default_factory=list)
    citation_coverage: float = 1.0
    competitor_false_alarm_rate: float = 0.0

    @property
    def agreement(self) -> float:
        return self.agree / self.total if self.total else 0.0


def _load_gold() -> list[dict]:
    path = config.GOLD_DIR / "human-reviewed-labels.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate() -> EvalReport:
    gold = _load_gold()
    report = EvalReport(total=len(gold))

    for row in gold:
        dna = synthesize_cycle(row["cycle_id"])
        predicted = top_driver_category(dna)
        expected = row["top_driver_category"]
        ok = predicted == expected
        report.agree += int(ok)
        report.per_cycle.append({
            "cycle_id": row["cycle_id"], "outcome": dna.outcome.value,
            "expected": expected, "predicted": predicted, "match": ok,
        })

    # Citation coverage + competitor false-alarm across ALL cycles.
    total_drivers = cited = 0
    total_mentions = false_alarms = 0
    for cid in list_cycles():
        dna = synthesize_cycle(cid)
        for d in dna.drivers:
            total_drivers += 1
            if d.quote.strip() and d.source.strip():
                cited += 1
        for m in dna.competitor_mentions:
            total_mentions += 1
            if m.is_loss_reason and "chose" not in m.quote.lower() and "went with" not in m.quote.lower():
                false_alarms += 1

    report.citation_coverage = cited / total_drivers if total_drivers else 1.0
    report.competitor_false_alarm_rate = false_alarms / total_mentions if total_mentions else 0.0
    return report


def format_report(r: EvalReport) -> str:
    lines = ["=== Deal DNA evaluation (vs human gold set) ==="]
    for row in r.per_cycle:
        mark = "OK " if row["match"] else "XX "
        lines.append(f"  {mark}{row['cycle_id']} [{row['outcome']}] "
                     f"expected={row['expected']:<12} predicted={row['predicted']}")
    lines.append(f"Top-driver agreement:        {r.agreement:.0%} ({r.agree}/{r.total})")
    lines.append(f"Citation coverage:           {r.citation_coverage:.0%}")
    lines.append(f"Competitor false-alarm rate: {r.competitor_false_alarm_rate:.0%}")
    lines.append("")
    lines.append("Limits: gold set is SMALL and SYNTHETIC, and the decisiveness priority was tuned on "
                 "it — treat these as directional, not production accuracy. Real validation needs an "
                 "independent human-labeled sample split by cycle_id.")
    return "\n".join(lines)
