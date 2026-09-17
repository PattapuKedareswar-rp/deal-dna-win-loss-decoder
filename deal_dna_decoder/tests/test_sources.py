"""Data-source layer tests — VTT parsing + provenance mode (offline)."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"

from deal_dna.normalize import _parse_vtt
from deal_dna.sources import data_mode

_VTT = """WEBVTT

1
00:00:05.000 --> 00:00:12.000
<v Buyer - VP Operations>We still set renewals manually and it is painful.

2
00:00:20.000 --> 00:00:26.000
Rep - A. Morgan: Our AI revenue management automates that.
"""


def test_vtt_parsing_preserves_speaker_and_timestamp():
    turns = _parse_vtt(_VTT, "data/x.vtt")
    assert len(turns) == 2
    assert turns[0].role == "Buyer" and turns[0].speaker == "VP Operations"
    assert turns[0].timestamp == "00:00:05"
    assert "renewals manually" in turns[0].text
    assert turns[1].role == "Rep" and turns[1].speaker == "A. Morgan"


def test_data_mode_defaults_to_synthetic_demo():
    # No approved export present in the test workspace.
    assert data_mode() == "synthetic-demo"
