"""Portfolio / executive intelligence (aggregate across all cycles).

Turns per-deal DealDNA objects into org-level intelligence for leadership and the
cross-functional teams named in the brief:
- win rate overall and by product family
- top recurring win drivers and loss drivers (evidence-grounded)
- competitor battlecards (where/why we are exposed, with a sample quote)
- enablement coaching hotspots (recurring rep-facing friction to train on)

Deterministic and offline. A "winning feature": it converts individual reviews into
a repeatable feedback loop without inventing anything the drivers don't support.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html import escape

from .schema import DealDNA, Direction, Outcome

_CLOSED = (Outcome.WON, Outcome.LOST)


@dataclass
class Battlecard:
    competitor: str
    deals: int
    won: int
    lost: int
    top_loss_drivers: list[tuple[str, int]] = field(default_factory=list)
    sample_quote: str = ""

    @property
    def loss_rate(self) -> float:
        closed = self.won + self.lost
        return self.lost / closed if closed else 0.0


@dataclass
class PortfolioReport:
    total_cycles: int = 0
    won: int = 0
    lost: int = 0
    stalled: int = 0
    needs_review: int = 0
    win_rate: float = 0.0
    win_rate_by_product: list[tuple[str, float, int]] = field(default_factory=list)
    top_win_drivers: list[tuple[str, int]] = field(default_factory=list)
    top_loss_drivers: list[tuple[str, int]] = field(default_factory=list)
    battlecards: list[Battlecard] = field(default_factory=list)
    coaching_hotspots: list[tuple[str, int]] = field(default_factory=list)


def build_portfolio(deals: list[DealDNA]) -> PortfolioReport:
    r = PortfolioReport(total_cycles=len(deals))
    r.won = sum(d.outcome == Outcome.WON for d in deals)
    r.lost = sum(d.outcome == Outcome.LOST for d in deals)
    r.stalled = sum(d.outcome == Outcome.STALLED for d in deals)
    r.needs_review = sum(d.outcome == Outcome.NEEDS_REVIEW for d in deals)
    closed = r.won + r.lost
    r.win_rate = r.won / closed if closed else 0.0

    # Win rate by product family.
    by_prod: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [won, closed]
    for d in deals:
        if d.outcome not in _CLOSED:
            continue
        prod = d.product_families[0] if d.product_families else "(unknown)"
        by_prod[prod][1] += 1
        if d.outcome == Outcome.WON:
            by_prod[prod][0] += 1
    r.win_rate_by_product = sorted(
        [(p, w / c if c else 0.0, c) for p, (w, c) in by_prod.items()],
        key=lambda x: x[2], reverse=True,
    )

    # Top win / loss drivers (evidence-grounded, direction-aware).
    win_cat, loss_cat = Counter(), Counter()
    for d in deals:
        for drv in d.drivers:
            if d.outcome == Outcome.WON and drv.direction == Direction.POSITIVE:
                win_cat[drv.category.value] += 1
            if d.outcome == Outcome.LOST and drv.direction in (Direction.NEGATIVE, Direction.MIXED):
                loss_cat[drv.category.value] += 1
    r.top_win_drivers = win_cat.most_common(5)
    r.top_loss_drivers = loss_cat.most_common(5)

    # Competitor battlecards.
    comp_cycles: dict[str, list[DealDNA]] = defaultdict(list)
    for d in deals:
        for name in {m.name for m in d.competitor_mentions}:
            comp_cycles[name].append(d)
    for name, cyc in sorted(comp_cycles.items(), key=lambda x: len(x[1]), reverse=True):
        won = sum(c.outcome == Outcome.WON for c in cyc)
        lost = sum(c.outcome == Outcome.LOST for c in cyc)
        loss_drivers = Counter()
        sample = ""
        for c in cyc:
            if c.outcome == Outcome.LOST:
                for drv in c.drivers:
                    if drv.direction in (Direction.NEGATIVE, Direction.MIXED):
                        loss_drivers[drv.category.value] += 1
                        sample = sample or drv.quote
        r.battlecards.append(Battlecard(
            competitor=name, deals=len(cyc), won=won, lost=lost,
            top_loss_drivers=loss_drivers.most_common(3), sample_quote=sample,
        ))

    # Enablement coaching hotspots: recurring rep-facing friction across all cycles.
    hotspots = Counter()
    for d in deals:
        for drv in d.drivers:
            if drv.direction in (Direction.NEGATIVE, Direction.MIXED):
                hotspots[drv.category.value] += 1
    r.coaching_hotspots = hotspots.most_common(6)
    return r


def format_portfolio(r: PortfolioReport) -> str:
    lines = ["=== Deal DNA \u2014 Portfolio intelligence (synthetic) ==="]
    lines.append(f"Cycles: {r.total_cycles}  |  Won {r.won} / Lost {r.lost} / Stalled {r.stalled} "
                 f"/ Needs Review {r.needs_review}  |  Win rate: {r.win_rate:.0%}")
    lines.append("Win rate by product:")
    for p, wr, n in r.win_rate_by_product:
        lines.append(f"  - {p}: {wr:.0%} ({n} closed)")
    lines.append("Top win drivers:  " + ", ".join(f"{c}({n})" for c, n in r.top_win_drivers))
    lines.append("Top loss drivers: " + ", ".join(f"{c}({n})" for c, n in r.top_loss_drivers))
    lines.append("Competitor battlecards:")
    for b in r.battlecards:
        drivers = ", ".join(f"{c}({n})" for c, n in b.top_loss_drivers) or "\u2014"
        lines.append(f"  - {b.competitor}: {b.deals} deals, W{b.won}/L{b.lost} "
                     f"(loss rate {b.loss_rate:.0%}); loss drivers: {drivers}")
    lines.append("Coaching hotspots: " + ", ".join(f"{c}({n})" for c, n in r.coaching_hotspots))
    return "\n".join(lines)


def render_portfolio_html(r: PortfolioReport) -> str:
    def rows(pairs):
        return "".join(f"<tr><td>{escape(str(a))}</td><td>{b}</td></tr>" for a, b in pairs)

    prod_rows = "".join(
        f"<tr><td>{escape(p)}</td><td>{wr:.0%}</td><td>{n}</td></tr>"
        for p, wr, n in r.win_rate_by_product)
    bc_rows = "".join(
        f"<tr><td>{escape(b.competitor)}</td><td>{b.deals}</td><td>{b.won}</td><td>{b.lost}</td>"
        f"<td>{b.loss_rate:.0%}</td><td>{escape(', '.join(f'{c} ({n})' for c, n in b.top_loss_drivers) or '—')}</td>"
        f"<td><em>{escape((b.sample_quote or '')[:90])}</em></td></tr>"
        for b in r.battlecards)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Deal DNA — Portfolio Intelligence</title>
<style>
 body{{font-family:Calibri,Segoe UI,sans-serif;margin:0;color:#0A1420;background:#fff}}
 header{{background:#082649;color:#fff;padding:18px 28px}}
 header h1{{margin:0;font-size:22px}} header .note{{opacity:.8;font-size:13px}}
 main{{padding:20px 28px;max-width:1000px}}
 h2{{color:#082649;border-bottom:2px solid #AE6B29;padding-bottom:4px;margin-top:26px}}
 .kpis{{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0}}
 .kpi{{background:#F5F6FB;border:1px solid #D0D8EF;border-radius:8px;padding:12px 16px;min-width:120px}}
 .kpi .v{{font-size:24px;font-weight:700;color:#082649}} .kpi .l{{font-size:12px;color:#495E83}}
 table{{border-collapse:collapse;width:100%;margin-top:8px;font-size:14px}}
 th,td{{border:1px solid #D0D8EF;padding:6px 10px;text-align:left}} th{{background:#082649;color:#fff}}
 tr:nth-child(even){{background:#F5F6FB}}
</style></head><body>
<header><h1>Deal DNA — Portfolio Intelligence</h1>
<div class="note">SYNTHETIC sample data — not real customer data · advisory &amp; read-only</div></header>
<main>
 <div class="kpis">
  <div class="kpi"><div class="v">{r.win_rate:.0%}</div><div class="l">Win rate ({r.won+r.lost} closed)</div></div>
  <div class="kpi"><div class="v">{r.won}</div><div class="l">Won</div></div>
  <div class="kpi"><div class="v">{r.lost}</div><div class="l">Lost</div></div>
  <div class="kpi"><div class="v">{r.stalled}</div><div class="l">Stalled</div></div>
  <div class="kpi"><div class="v">{r.needs_review}</div><div class="l">Needs Review</div></div>
 </div>
 <h2>Win rate by product</h2>
 <table><tr><th>Product</th><th>Win rate</th><th>Closed deals</th></tr>{prod_rows}</table>
 <h2>Top win drivers</h2><table><tr><th>Driver</th><th>Count</th></tr>{rows(r.top_win_drivers)}</table>
 <h2>Top loss drivers</h2><table><tr><th>Driver</th><th>Count</th></tr>{rows(r.top_loss_drivers)}</table>
 <h2>Competitor battlecards</h2>
 <table><tr><th>Competitor</th><th>Deals</th><th>Won</th><th>Lost</th><th>Loss rate</th>
 <th>Top loss drivers</th><th>Sample evidence</th></tr>{bc_rows}</table>
 <h2>Enablement coaching hotspots</h2>
 <table><tr><th>Theme</th><th>Occurrences</th></tr>{rows(r.coaching_hotspots)}</table>
</main></body></html>"""
