"""Evaluation harness tests — offline, deterministic."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"

from deal_dna.evaluate import evaluate


def test_top_driver_agreement_is_strong():
    r = evaluate()
    assert r.total >= 5
    assert r.agreement >= 0.8, f"top-driver agreement too low: {r.agreement:.0%}"


def test_every_driver_is_cited():
    assert evaluate().citation_coverage == 1.0


def test_no_competitor_false_alarms():
    assert evaluate().competitor_false_alarm_rate == 0.0
