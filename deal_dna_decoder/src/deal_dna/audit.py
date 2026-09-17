"""Review & safety auditor.

Two jobs:
1. `audit_dealdna` — verify a DealDNA is traceable and governance-safe before it is shared.
2. `screen_action_request` — the guardrail: refuse any request to take an external action
   (CRM write-back, emailing customers, publishing) and route to human review instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import DealDNA, EvidenceLabel

# Verdicts
PASS = "PASS"
PASS_WITH_REVIEW = "PASS WITH REVIEW"
BLOCKED = "BLOCKED"

_ACTION_RE = re.compile(
    r"\b(email|e-mail|send|contact|call the customer|update (salesforce|crm)|write ?back|"
    r"push to (salesforce|crm)|publish|post|notify the (customer|client)|"
    r"close the deal|apply (a )?discount)\b",
    re.I,
)


@dataclass
class AuditResult:
    verdict: str
    issues: list[str] = field(default_factory=list)


def audit_dealdna(d: DealDNA) -> AuditResult:
    issues: list[str] = []

    # Traceability: every driver needs a quote + source.
    for i, drv in enumerate(d.drivers):
        if not drv.quote.strip() or not drv.source.strip():
            issues.append(f"Driver #{i} ({drv.category.value}) missing quote or source.")

    # Competitor mention must not be an unsupported loss reason.
    for m in d.competitor_mentions:
        if m.is_loss_reason and "chose" not in m.quote.lower() and "went with" not in m.quote.lower():
            issues.append(f"Competitor '{m.name}' marked as loss reason without explicit causal evidence.")

    # Outcome authority must come from Salesforce.
    if d.outcome_source and "salesforce" not in d.outcome_source.lower():
        issues.append("Outcome is not sourced from Salesforce.")

    # Honesty: an outcome with zero drivers and no unknowns is suspicious.
    if not d.drivers and not d.unknowns:
        issues.append("No evidence and no unknowns recorded; likely under-analyzed.")

    if any("missing quote" in x or "not sourced" in x for x in issues):
        return AuditResult(BLOCKED, issues)
    if issues:
        return AuditResult(PASS_WITH_REVIEW, issues)
    if d.review.status == "Manager Validated":
        return AuditResult(PASS, [])
    reason = {
        "Needs Review": "Pending human review — no rep decisions recorded yet.",
        "Rep Reviewed": "Rep reviewed; awaiting manager validation.",
        "Blocked": "Blocked by the intake gate (consent / completeness / mapping).",
    }.get(d.review.status, f"Pending review (status: {d.review.status}).")
    return AuditResult(PASS_WITH_REVIEW, [reason])


@dataclass
class ActionScreen:
    allowed: bool
    reason: str


def screen_action_request(instruction: str) -> ActionScreen:
    """Guardrail: Deal DNA is advisory. Refuse external/production actions."""
    if _ACTION_RE.search(instruction or ""):
        return ActionScreen(
            allowed=False,
            reason=("Deal DNA is advisory and read-only. It does not write to Salesforce, contact "
                    "customers, or publish. This is a human-review recommendation only."),
        )
    return ActionScreen(allowed=True, reason="Analytical request; no external action requested.")
