"""Deal DNA CLI — Person A orchestrator.

Examples:
  python -m deal_dna.run --all                 # analyze every cycle -> outputs/*.json
  python -m deal_dna.run --cycle cyc-001        # analyze one cycle, print summary
  python -m deal_dna.run --radar                # market-signal radar across all cycles
  python -m deal_dna.run --write-fixture        # emit data/fixtures/sample_dealdna.json (for Person B)
  python -m deal_dna.run --check "email the customer a discount"   # guardrail demo
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config
from .audit import audit_dealdna, screen_action_request
from .normalize import list_cycles
from .radar import build_radar
from .schema import DealDNA
from .synthesize import synthesize_cycle


def _write_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _maybe_enrich(dna: DealDNA) -> DealDNA:
    """If Person B's crossfunction module is present, enrich; else return the base DealDNA."""
    try:
        from .crossfunction import enrich_crossfunctional
    except ImportError:
        return dna
    try:
        return enrich_crossfunctional(dna)
    except Exception:
        return dna


def _maybe_render(dna: DealDNA, outdir: Path) -> None:
    """If Person B's render module is present, also write an HTML briefing."""
    try:
        from .render import render_briefing
    except ImportError:
        return
    try:
        (outdir / f"{dna.cycle_id}.html").write_text(render_briefing(dna), encoding="utf-8")
    except Exception:
        pass


def _analyze(cycle_id: str, outdir: Path) -> DealDNA:
    dna = synthesize_cycle(cycle_id)
    dna = _maybe_enrich(dna)
    verdict = audit_dealdna(dna)
    out = outdir / f"{cycle_id}.json"
    _write_json(dna.model_dump(mode="json"), out)
    _maybe_render(dna, outdir)
    print(f"[{cycle_id}] outcome={dna.outcome.value:22} "
          f"calls={dna.call_count} drivers={len(dna.drivers)} "
          f"competitors={len(dna.competitor_mentions)} audit={verdict.verdict}")
    for issue in verdict.issues:
        print(f"    - {issue}")
    return dna


def _demo(outdir: Path) -> None:
    """Narrated MVP walkthrough over one Won, one Lost, and one Stalled cycle."""
    from .evaluate import evaluate, format_report
    print("=" * 72)
    print("DEAL DNA — MVP WALKTHROUGH (synthetic data, advisory & read-only)")
    print("=" * 72)
    for cid, label in (("cyc-002", "WON"), ("cyc-001", "LOST"), ("cyc-003", "STALLED")):
        dna = synthesize_cycle(cid)
        verdict = audit_dealdna(dna)
        print(f"\n### {label}: {dna.account} ({dna.cycle_id}) — outcome {dna.outcome.value} "
              f"[{dna.outcome_source}], {dna.call_count} call(s)")
        print("  Evidence-backed drivers (each cites a verbatim quote):")
        for d in dna.drivers[:4]:
            print(f"    - [{d.direction.value}/{d.confidence}] {d.category.value}: "
                  f"\"{d.quote[:70]}\" @ {d.timestamp} ({d.source})")
        if dna.competitor_mentions:
            for m in dna.competitor_mentions:
                print(f"  Competitor mention: {m.name} — loss_reason={m.is_loss_reason} "
                      f"(abstains unless explicit).")
        if dna.unknowns:
            print("  Honest unknowns (abstention):")
            for u in dna.unknowns:
                print(f"    - {u}")
        print(f"  Audit: {verdict.verdict}  |  Review gate: {dna.review.status}")
    print("\n### Guardrail (advisory-only):")
    screen = screen_action_request("email the customer a discount and update Salesforce")
    print(f"  Request to act -> {'ALLOWED' if screen.allowed else 'REFUSED'}: {screen.reason}")
    print("\n### Evaluation vs human gold set:")
    print(format_report(evaluate()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deal_dna.run", description="Deal DNA — Win/Loss Decoder (Person A core)")
    ap.add_argument("--cycle", help="Analyze a single cycle id (e.g. cyc-001)")
    ap.add_argument("--all", action="store_true", help="Analyze all cycles")
    ap.add_argument("--radar", action="store_true", help="Print the market-signal radar")
    ap.add_argument("--evaluate", action="store_true", help="Score decoded drivers against the gold set")
    ap.add_argument("--demo", action="store_true",
                    help="Narrated MVP walkthrough: one Won, one Lost, one Stalled cycle")
    ap.add_argument("--write-fixture", action="store_true",
                    help="Write data/fixtures/sample_dealdna.json for Person B")
    ap.add_argument("--check", metavar="INSTRUCTION", help="Screen an instruction against the guardrail")
    ap.add_argument("--outdir", default=str(config.OUTPUTS_DIR), help="Output directory")
    args = ap.parse_args(argv)

    outdir = Path(args.outdir)
    mode = "OFFLINE (deterministic)" if config.is_offline() else f"OpenAI ({config.OPENAI_MODEL})"
    print(f"Deal DNA — mode: {mode}\n{config.DATA_NOTE}\n")

    if args.check is not None:
        screen = screen_action_request(args.check)
        print(f"Guardrail: {'ALLOWED' if screen.allowed else 'REFUSED'} — {screen.reason}")
        return 0

    cycles = list_cycles()
    if not cycles:
        print("No cycles found. Run:  python data/generate_data.py")
        return 1

    if args.evaluate:
        from .evaluate import evaluate, format_report
        print(format_report(evaluate()))
        return 0

    if args.demo:
        _demo(outdir)
        return 0

    deals: list[DealDNA] = []
    if args.all or (not args.cycle and not args.radar and not args.write_fixture):
        deals = [_analyze(c, outdir) for c in cycles]
    elif args.cycle:
        deals = [_analyze(args.cycle, outdir)]

    if args.write_fixture:
        source_cycle = args.cycle or "cyc-001"
        dna = synthesize_cycle(source_cycle)
        fixture = config.FIXTURES_DIR / "sample_dealdna.json"
        _write_json(dna.model_dump(mode="json"), fixture)
        print(f"Wrote fixture for Person B: {fixture}")

    if args.radar:
        if not deals:
            deals = [synthesize_cycle(c) for c in cycles]
        report = build_radar(deals)
        print("\n=== Market-signal radar ===")
        print(report.note)
        print("Recurring hesitations:")
        for s in report.recurring_hesitations:
            print(f"  - {s.label}: {s.count} cycles {s.cycles}")
        print("Alternative software mentioned:")
        for s in report.alternative_software:
            print(f"  - {s.label}: {s.count} cycles {s.cycles}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
