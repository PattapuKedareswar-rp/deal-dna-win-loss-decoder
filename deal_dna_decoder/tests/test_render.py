"""Genome renderer tests — all run OFFLINE (no OpenAI key needed)."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"  # force deterministic path for reproducible tests

from markupsafe import escape

from deal_dna.crossfunction import enrich_crossfunctional
from deal_dna.render import render_briefing
from deal_dna.synthesize import synthesize_cycle


def test_render_contains_every_driver_quote_and_timestamp():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))
    html = render_briefing(d)
    assert "<html" in html.lower()
    for drv in d.drivers:
        assert str(escape(drv.quote)) in html, f"missing quote for {drv.category.value}"
        assert drv.timestamp in html, f"missing timestamp {drv.timestamp}"


def test_render_shows_outcome_and_source():
    d = enrich_crossfunctional(synthesize_cycle("cyc-001"))
    html = render_briefing(d)
    assert d.outcome.value in html
    assert str(escape(d.outcome_source)) in html


def test_render_writes_html_file():
    from deal_dna import config

    d = enrich_crossfunctional(synthesize_cycle("cyc-002"))
    render_briefing(d)
    assert (config.OUTPUTS_DIR / f"{d.cycle_id}.html").exists()
