"""Cross-functional enrichment tests — all run OFFLINE (no OpenAI key needed)."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"  # force deterministic path for reproducible tests

from deal_dna.crossfunction import enrich_crossfunctional
from deal_dna.schema import Outcome
from deal_dna.synthesize import synthesize_cycle


def _all_actions(d):
    f = d.cross_function_actions
    return f.enablement + f.product + f.pricing + f.product_marketing + f.implementations


def test_every_action_has_evidence():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))
    actions = _all_actions(d)
    assert actions, "expected cross-functional actions for a rich cycle"
    for a in actions:
        assert a.evidence_refs, f"action for {a.audience} has no evidence_refs"


def test_pricing_action_is_a_review_item_not_a_price_change():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))
    for a in d.cross_function_actions.pricing:
        assert "review item" in a.recommended_action.lower()


def test_won_cycle_handoff_applicable():
    d = enrich_crossfunctional(synthesize_cycle("cyc-002"))  # Won
    assert d.outcome == Outcome.WON
    assert d.implementation_handoff.applicable is True


def test_lost_cycle_handoff_not_applicable():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))  # Lost
    assert d.outcome != Outcome.WON
    assert d.implementation_handoff.applicable is False


def test_seller_coaching_pulls_biggest_unknown():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))
    assert d.seller_coaching is not None
    assert d.seller_coaching.biggest_unanswered_question.strip()
    assert len(d.seller_coaching.buyer_questions) == 3
