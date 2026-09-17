"""Person A core tests — all run OFFLINE (no OpenAI key needed)."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"  # force deterministic path for reproducible tests

from deal_dna.audit import BLOCKED, PASS, PASS_WITH_REVIEW, audit_dealdna, screen_action_request
from deal_dna.radar import build_radar
from deal_dna.schema import Category, DealDNA, Outcome
from deal_dna.synthesize import synthesize_cycle
from deal_dna.normalize import list_cycles


def test_every_driver_is_citation_locked():
    dna = synthesize_cycle("cyc-001")
    assert dna.drivers, "expected drivers for a rich Lost cycle"
    for d in dna.drivers:
        assert d.quote.strip(), "driver must include a verbatim quote"
        assert d.source.strip(), "driver must include a source path"
        assert d.timestamp.strip(), "driver must include a timestamp"


def test_outcome_comes_from_salesforce():
    dna = synthesize_cycle("cyc-002")
    assert dna.outcome == Outcome.WON
    assert "salesforce" in dna.outcome_source.lower()


def test_cycle_rollup_counts_deal_once():
    # cyc-001 has 2 calls but must be ONE observation.
    dna = synthesize_cycle("cyc-001")
    assert dna.call_count == 2
    assert isinstance(dna, DealDNA)


def test_competitor_mention_is_not_a_loss_reason():
    dna = synthesize_cycle("cyc-001")  # mentions Entrata but no "we chose" language
    assert dna.competitor_mentions, "expected a competitor mention"
    assert all(not m.is_loss_reason for m in dna.competitor_mentions)
    verdict = audit_dealdna(dna)
    assert verdict.verdict in (PASS, PASS_WITH_REVIEW)


def test_guardrail_refuses_external_actions():
    assert screen_action_request("email the customer a discount").allowed is False
    assert screen_action_request("update Salesforce with the loss reason").allowed is False
    assert screen_action_request("summarize why we lost this deal").allowed is True


def test_audit_blocks_untraceable_driver():
    dna = synthesize_cycle("cyc-001")
    dna.drivers[0].source = ""  # break traceability
    assert audit_dealdna(dna).verdict == BLOCKED


def test_radar_only_surfaces_recurring_signals():
    deals = [synthesize_cycle(c) for c in list_cycles()]
    report = build_radar(deals)
    for s in report.recurring_hesitations:
        assert s.count >= 2
    for s in report.alternative_software:
        assert s.count >= 2
