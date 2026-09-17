# Deal DNA (channel DD) — current status

**Last updated:** 2026-09-17, PT
**Active editor:** Person A
**Artifact:** `deal_dna_decoder/` — evidence-first Win/Loss Decoder (Person A core complete)
**Repo:** https://github.com/PattapuKedareswar-rp/deal-dna-win-loss-decoder (branch `main`)

**Event timeline:** Build began Wed Sep 16, 2026. Final submission due 11:59 PM PT Thu Sep 17, 2026.
Judging Sep 18–25, 2026; winners announced at the Sep 30, 2026 Town Hall.

## Current goal
Finish integrated prototype: Person A evidence core (done) + Person B cross-functional feeds, genome
UI, and rep→manager review loop (in progress), then final package.

## Completed
- Evidence pipeline: `normalize → intake → evidence → synthesize` producing a citation-locked
  `DealDNA` per cycle (rolled up by cycle, not by call).
- `audit` (traceability + advisory-only guardrail), `radar` (recurring-signal, false-alarm guard),
  `evaluate` (vs human gold set), `run` CLI incl. `--demo`.
- 18 synthetic cycles / 22 calls; OpenAI (gpt-4o) path validated + offline fallback.
- **11/11 tests pass.** Evaluation: **100% top-driver agreement (7/7) · 100% citation coverage ·
  0% competitor false-alarm.**

## In progress
- Person B — `crossfunction.py` (5 feeds + seller card + handoff), `render.py` (genome), `app/`
  (review UI). Integrates via the `synthesize_cycle → enrich_crossfunctional → render_briefing` seam
  (hooks already wired in `run.py`).

## Next best action
- Person A: support Person B integration (Sync 2/3); finalize `03_Final_Submission/README.md`.

## Test and evidence log

| Test ID | Approved input / scenario | Expected behavior | Actual result | Pass/fail | Evidence |
| --- | --- | --- | --- | --- | --- |
| T-01 | Typical Lost cycle: `run --cycle cyc-001` | Grounded, citation-locked drivers tied to Salesforce outcome | 5 drivers, each with verbatim quote + speaker + timestamp + source; outcome `Lost` from Salesforce; audit `PASS WITH REVIEW` | Pass | `outputs/cyc-001.json`; `--demo` |
| T-02 | Abstention: competitor mention with no loss evidence (cyc-014, Won) + missing consent/attribution (cyc-015/016) | Do not treat competitor mention as loss reason; flag `Needs Review` instead of guessing | cyc-014 competitor `Yardi` → `is_loss_reason=False`; cyc-015 → unknowns cite consent; cyc-016 → transcript status downgraded + completeness flagged; competitor false-alarm rate **0%** | Pass | `--evaluate`; `outputs/cyc-014/015/016.json` |
| T-03 | Guardrail: `run --check "email the customer a discount"` | Refuse external action; return human-review recommendation | `REFUSED: Deal DNA is advisory and read-only…` | Pass | `--demo`; `audit.screen_action_request` |

## How to reproduce
```powershell
cd deal_dna_decoder
python -m pip install -e ".[dev]"
python data/generate_data.py
$env:DEAL_DNA_OFFLINE = 1
python -m deal_dna.run --demo      # narrated walkthrough (Won/Lost/Stalled + guardrail + eval)
python -m pytest -q                # 11 tests
```

## Safety reminder
Advisory & read-only: no CRM write-back, no customer outreach, no auto-publish. Human review before
sharing. Synthetic data only. API key is environment-only and git-ignored.
