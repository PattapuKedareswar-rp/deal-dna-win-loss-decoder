# Person A — Roadmap (Evidence & Intelligence Core)

You've shipped the core (commit `b9d4703`). This is what's left to make it demo-winning, integrate
with Person B, and be submission-ready. Ordered by priority.

---

## Done ✅
- `DealDNA` contract (`schema.py`), config, OpenAI+offline `llm` wrapper.
- Pipeline: `normalize → intake → evidence → synthesize` (rollup by cycle).
- `audit` (traceability + action guardrail), `radar` (recurring-signal, false-alarm guard), `run` CLI.
- 12 synthetic cycles, 7 offline tests passing, fixture for Person B, README. Pushed to `main`.
- **A1 ✅** risk-mitigation heuristic fixed (Won cycles no longer flagged as risk), confidence
  calibration (single-mention → low), stronger `unknowns` (missing ROI on Won / pricing on Lost).
- **A3 ✅** evaluation harness (`--evaluate`): **100% top-driver agreement (7/7)**, **100% citation
  coverage**, **0% competitor false-alarm** + 3 tests. Commit `8d3023c`.
- **A2 ✅** live OpenAI (gpt-4o) path validated on cyc-001; clean offline fallback; key git-ignored.
- **A4 ✅** grew to 18 cycles/22 calls (multi-call Won, competitor-mention-no-loss, two Needs-Review
  cycles); intake gate surfaces completeness issues. Commit `f8fc8f4`.
- **A6 ✅** narrated `--demo` walkthrough + Person B integration hooks in `run.py`; recreated
  `00_Admin/STATUS.md` (3-test evidence log) + `03_Final_Submission/README.md`. Commit `b3ca4be`.
- **A5 (hooks) ✅** `run.py` auto-calls `enrich_crossfunctional`/`render_briefing` if Person B's
  modules exist — zero-touch integration when they land.

---

## Phase A1 — Sharpen the evidence core (do first)
1. **Fix an offline heuristic false-positive:** "reduced our risk concerns" (Won cycles cyc-002,
   cyc-005) is tagged `risk / negative`. Make the `risk` pattern direction-aware — if the quote
   contains `de-risked | reduced | plan reduced | addressed`, emit `direction=positive` (or drop it).
   Re-run `--radar` and confirm the risk trend no longer includes Won cycles by mistake.
2. **Confidence + label calibration:** downgrade single-mention drivers to `confidence=low`; mark a
   driver `Inferred` when it comes from a rep statement rather than a buyer statement.
3. **Strengthen `unknowns`:** add checks for missing ROI evidence on Won deals and missing pricing
   evidence on Lost deals, so abstention is visible.

## Phase A2 — Validate the OpenAI path (needs the provided key)
4. Put the key in a **local `.env`** (never commit), set `DEAL_DNA_OFFLINE=0`, and run
   `python -m deal_dna.run --cycle cyc-001`. Confirm the LLM returns schema-valid drivers with real
   quotes; verify it **falls back to offline** cleanly on any parse error.
5. Tighten `_LLM_SYSTEM` in `evidence.py`: forbid inventing quotes, require verbatim buyer quotes,
   enforce "competitor mention ≠ loss reason", and demand abstention when unsupported.
6. Add a `--model` note in the README and confirm cost is reasonable (consider `gpt-4o-mini` fallback).

## Phase A3 — Evaluation harness (big judging win: "win/loss insight quality" + "traceability")
7. Build `src/deal_dna/evaluate.py` that compares each cycle's top driver category against
   `data/gold/human-reviewed-labels.csv` and reports **agreement %**, **% of claims with a citation**,
   and **competitor false-alarm rate**. Add `python -m deal_dna.run --evaluate`.
8. Add `tests/test_evaluate.py` (offline). This is your evidence for the submission's test log.

## Phase A4 — Grow + realism of the data
9. Expand to ~15–18 cycles including: a **multi-call Won** deal, a cycle with a competitor mention but
   **no loss** (reinforces abstention), and a `Needs Review` cycle (missing consent / attribution) so
   the intake gate is demonstrably exercised.
10. Add one `Speaker attribution incomplete` transcript to prove the gate downgrades it.

## Phase A5 — Integration with Person B (Sync 2 & 3)
11. **Sync 2:** once Person B has `enrich_crossfunctional`, import it in `run.py` and chain
    `synthesize_cycle → enrich_crossfunctional → audit_dealdna → render_briefing → write`. Resolve any
    schema drift **together** in `schema.py` only.
12. Keep `synthesize_cycle` pure and stable — it's Person B's dependency. Version any breaking change.

## Phase A6 — Submission readiness
13. Recreate the admin/submission folders (they were deleted): `00_Admin/STATUS.md` with the **3-test
    evidence log** (typical / abstention / guardrail) and `03_Final_Submission/README.md`.
14. Map each judging criterion to concrete evidence (insight quality → eval harness; traceability →
    citation-locked drivers + review loop; cross-functional → B's feeds; theme/market → radar;
    governance → guardrail + read-only + synthetic data).
15. Prep the MVP demo script: **1 Won + 1 Lost + 1 Stalled** cycle end-to-end (evidence → genome →
    one feed → seller card → Won handoff → one reviewer correction in the audit trail).

---

## Your immediate next 3 tasks
1. ~~Phase A1.1 (fix the `risk` direction heuristic)~~ ✅ done.
2. ~~Phase A3.7 (evaluation harness)~~ ✅ done — 100% agreement / 100% citations / 0% false-alarm.
3. ~~Phase A2.4 (validate the OpenAI key path)~~ ✅ done. ~~A4~~ ✅ done. ~~A6 scaffolding~~ ✅ done.

**Remaining:** A5 Sync 3 — when Person B pushes `crossfunction.py` + `render.py` + `app/`, pull, run
`python -m deal_dna.run --all` (hooks auto-enrich + render), then run the MVP demo for reviewers and
post the final package to the team Teams channel.

Push after each so Person B always sees a stable `main`.
