"""Portfolio intelligence tests — offline, deterministic."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"

from deal_dna.normalize import list_cycles
from deal_dna.portfolio import build_portfolio, render_portfolio_html
from deal_dna.synthesize import synthesize_cycle


def _all():
    return [synthesize_cycle(c) for c in list_cycles()]


def test_portfolio_win_rate_and_counts():
    r = build_portfolio(_all())
    assert r.total_cycles >= 12
    assert r.won > 0 and r.lost > 0
    assert 0.0 <= r.win_rate <= 1.0


def test_portfolio_has_competitor_battlecards():
    r = build_portfolio(_all())
    names = {b.competitor for b in r.battlecards}
    assert {"Entrata", "Yardi"} & names, "expected known competitors in battlecards"
    for b in r.battlecards:
        assert b.deals == b.won + b.lost or b.deals >= b.won + b.lost  # stalled allowed


def test_portfolio_html_renders():
    html = render_portfolio_html(build_portfolio(_all()))
    assert "Portfolio Intelligence" in html
    assert "Competitor battlecards" in html
