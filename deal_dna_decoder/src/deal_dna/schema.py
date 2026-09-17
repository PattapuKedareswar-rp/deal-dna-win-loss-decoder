"""Shared contract: the evidence model and the canonical `DealDNA` JSON.

This is the seam between Person A (produces DealDNA) and Person B (consumes it).
Co-authored in Step 0; owned by Person A thereafter.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Outcome(str, Enum):
    WON = "Won"
    LOST = "Lost"
    STALLED = "Stalled / No Decision"
    NEEDS_REVIEW = "Needs Review"


class EvidenceLabel(str, Enum):
    OBSERVED = "Observed"
    INFERRED = "Inferred"
    NOT_OBSERVED = "Not observed"
    UNKNOWN = "Unknown"
    NEEDS_REVIEW = "Needs Review"
    MIXED = "Mixed"


class TranscriptStatus(str, Enum):
    FULL = "Full transcript available"
    REMOTE = "Full transcript remote only"
    EXCERPTS = "Reviewed excerpts only"
    ATTR_INCOMPLETE = "Speaker attribution incomplete"
    NONE = "No usable transcript"


class Direction(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class Category(str, Enum):
    NEED = "need"
    PRICING = "pricing"
    DEMO = "demo"
    ROI = "roi"
    COMPETITOR = "competitor"
    INTEGRATION = "integration"
    TRUST = "trust"
    TIMING = "timing"
    AUTHORITY = "authority"
    RISK = "risk"
    IMPLEMENTATION = "implementation"
    PRODUCT = "product"


class Driver(BaseModel):
    """One evidence-backed finding. Every driver must cite a quote and a source."""
    category: Category
    direction: Direction
    label: EvidenceLabel = EvidenceLabel.OBSERVED
    summary: str
    quote: str
    speaker: str
    speaker_role: str
    timestamp: str
    source: str
    confidence: str = "medium"  # low | medium | high


class CompetitorMention(BaseModel):
    name: str
    quote: str
    speaker: str
    timestamp: str
    source: str
    # A competitor mention is NOT a loss reason unless explicit loss evidence is present.
    is_loss_reason: bool = False
    note: str = ""


class CrossFunctionAction(BaseModel):
    audience: str
    insight: str
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    owner_suggestion: str = ""
    recurrence: str = "single cycle"
    review_status: EvidenceLabel = EvidenceLabel.NEEDS_REVIEW


class CrossFunctionActions(BaseModel):
    enablement: list[CrossFunctionAction] = Field(default_factory=list)
    product: list[CrossFunctionAction] = Field(default_factory=list)
    pricing: list[CrossFunctionAction] = Field(default_factory=list)
    product_marketing: list[CrossFunctionAction] = Field(default_factory=list)
    implementations: list[CrossFunctionAction] = Field(default_factory=list)


class SellerCoaching(BaseModel):
    situation: str = ""
    stress_next: list[str] = Field(default_factory=list)
    verify_before: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    biggest_unanswered_question: str = ""
    buyer_questions: list[str] = Field(default_factory=list)
    proof_to_show: str = ""
    next_step_owner: str = ""
    confidence: str = "medium"
    review_status: EvidenceLabel = EvidenceLabel.NEEDS_REVIEW


class HandoffItem(BaseModel):
    # requested | promised | inferred_expectation | dependency | unresolved | out_of_scope | not_observed
    kind: str
    summary: str
    quote: str = ""
    speaker: str = ""
    timestamp: str = ""
    source: str = ""
    responsible: str = ""
    risk_if_unresolved: str = ""


class ImplementationHandoff(BaseModel):
    applicable: bool = False
    expected_value: list[str] = Field(default_factory=list)
    items: list[HandoffItem] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ReviewCorrection(BaseModel):
    at: str = Field(default_factory=_now)
    actor: str = ""          # rep | manager
    action: str = ""         # confirmed | added_context | challenged | rejected | validated
    field: str = ""
    note: str = ""


class Review(BaseModel):
    # Needs Review | Rep Reviewed | Manager Validated | Blocked
    status: str = "Needs Review"
    rep: Optional[str] = None
    manager: Optional[str] = None
    reviewed_at: Optional[str] = None
    corrections: list[ReviewCorrection] = Field(default_factory=list)


class DealDNA(BaseModel):
    """Canonical per-cycle output. Base fields filled by Person A; enrichment by Person B."""
    cycle_id: str
    opportunity_id: str
    account: str
    product_families: list[str] = Field(default_factory=list)
    outcome: Outcome
    outcome_source: str = "Salesforce IsWon"
    transcript_status: TranscriptStatus = TranscriptStatus.FULL
    call_count: int = 0

    # --- Person A (evidence core) ---
    drivers: list[Driver] = Field(default_factory=list)
    competitor_mentions: list[CompetitorMention] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    # --- Person B (enrichment) ---
    cross_function_actions: CrossFunctionActions = Field(default_factory=CrossFunctionActions)
    seller_coaching: Optional[SellerCoaching] = None
    implementation_handoff: Optional[ImplementationHandoff] = None

    review: Review = Field(default_factory=Review)
    generated_at: str = Field(default_factory=_now)
    data_note: str = "SYNTHETIC sample data — not real customer data."
