"""Robustness tests: LLM path (mocked), graceful fallback, and messy-input abstention."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"

import deal_dna.llm as llm_mod
from deal_dna import evidence
from deal_dna.normalize import Call, Turn
from deal_dna.schema import Category, Direction, Driver, EvidenceLabel


def _call(text: str, role: str = "Buyer", speaker: str = "VP", ts: str = "00:00:10") -> Call:
    return Call(cycle_id="t", call_id="c1", metadata={},
                turns=[Turn(timestamp=ts, role=role, speaker=speaker, text=text, source="data/t.txt")])


def test_llm_path_used_when_online(monkeypatch):
    monkeypatch.setattr(llm_mod, "is_offline", lambda: False)
    stub = Driver(category=Category.PRICING, direction=Direction.NEGATIVE,
                  label=EvidenceLabel.OBSERVED, summary="LLM driver", quote="too expensive",
                  speaker="Buyer - VP", speaker_role="VP", timestamp="00:00:10",
                  source="data/t.txt", confidence="high")

    def fake(system, user, model_cls):
        return model_cls(drivers=[stub], competitor_mentions=[])

    monkeypatch.setattr(llm_mod, "structured_json", fake)
    drivers, _ = evidence.extract_call(_call("anything at all"))
    assert any(d.summary == "LLM driver" for d in drivers)


def test_llm_failure_falls_back_offline(monkeypatch):
    monkeypatch.setattr(llm_mod, "is_offline", lambda: False)

    def boom(system, user, model_cls):
        raise RuntimeError("api down")

    monkeypatch.setattr(llm_mod, "structured_json", boom)
    drivers, _ = evidence.extract_call(_call("your list price is too high for us"))
    assert any(d.category == Category.PRICING for d in drivers)


def test_messy_transcript_abstains():
    # No supported signal -> no drivers (abstention), no fabrication.
    drivers, mentions = evidence.extract_call(_call("Hi, thanks for the time, talk soon."))
    assert drivers == []
    assert mentions == []


def test_competitor_mention_without_causal_language_is_not_loss_reason():
    _, mentions = evidence.extract_call(_call("We also looked at Yardi briefly."))
    assert mentions and all(not m.is_loss_reason for m in mentions)
