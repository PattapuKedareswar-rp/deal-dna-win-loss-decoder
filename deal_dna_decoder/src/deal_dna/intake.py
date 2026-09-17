"""Intake & provenance gate.

Validates that a cycle's evidence is safe to analyze: consent/approval, transcript
completeness, speaker attribution, and Salesforce opportunity mapping. Blocks or flags
`Needs Review` rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import salesforce
from .normalize import Cycle
from .schema import TranscriptStatus

_STATUS_BY_VALUE = {s.value: s for s in TranscriptStatus}


@dataclass
class IntakeResult:
    ok: bool
    transcript_status: TranscriptStatus
    opportunity_id: str = ""
    account: str = ""
    product: str = ""
    issues: list[str] = field(default_factory=list)


def gate(cycle: Cycle) -> IntakeResult:
    issues: list[str] = []
    if not cycle.calls:
        return IntakeResult(False, TranscriptStatus.NONE, issues=["No usable transcript found."])

    first_meta = cycle.calls[0].metadata
    opp_id = first_meta.get("opportunity_id", "")
    account = first_meta.get("account", "")
    product = first_meta.get("product", "")

    # Consent / approval must be explicit.
    if not all(c.metadata.get("consent") == "approved" for c in cycle.calls):
        issues.append("One or more calls lack approved consent status.")

    # Transcript completeness (take the weakest across calls).
    statuses = [_STATUS_BY_VALUE.get(c.metadata.get("transcript_status", ""),
                                     TranscriptStatus.NONE) for c in cycle.calls]
    order = list(TranscriptStatus)  # FULL is strongest, NONE weakest
    weakest = max(statuses, key=lambda s: order.index(s))
    if weakest not in (TranscriptStatus.FULL, TranscriptStatus.EXCERPTS):
        issues.append(f"Transcript completeness insufficient: {weakest.value}.")

    # Speaker attribution.
    if any(not t.speaker for c in cycle.calls for t in c.turns):
        issues.append("Speaker attribution incomplete on at least one turn.")

    # Salesforce mapping.
    row = salesforce.opportunity_for_cycle(first_meta)
    if row is None:
        issues.append(f"No Salesforce opportunity mapped for '{opp_id}'.")

    ok = not issues and weakest in (TranscriptStatus.FULL, TranscriptStatus.EXCERPTS)
    return IntakeResult(ok=ok, transcript_status=weakest, opportunity_id=opp_id,
                        account=account, product=product, issues=issues)
