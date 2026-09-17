# Deal DNA (channel DD) — current status

**Last updated:** 2026-09-17, PT
**Active editor:** Person A
**Artifact:** `deal_dna_decoder/` — evidence-first Win/Loss Decoder (Person A core complete)
**Repo:** https://github.com/PattapuKedareswar-rp/deal-dna-win-loss-decoder (branch `main`)

**Event timeline:** Build began Wed Sep 16, 2026. Final submission due 11:59 PM PT Thu Sep 17, 2026.
Judging Sep 18–25, 2026; winners announced at the Sep 30, 2026 Town Hall.

## Current goal
Integrated prototype COMPLETE (Person A core + Person B cross-functional feeds, genome UI, and
rep→manager review loop). Remaining: reviewer walkthrough + post final package to the team channel.

## Completed
- Evidence pipeline: `normalize → intake → evidence → synthesize` producing a citation-locked
  `DealDNA` per cycle (rolled up by cycle, not by call).
- `audit` (traceability + advisory-only guardrail), `radar` (recurring-signal, false-alarm guard),
  `evaluate` (vs human gold set), `run` CLI incl. `--demo`.
- 18 synthetic cycles / 22 calls; OpenAI (gpt-4o) path validated + offline fallback.
- **Person B merged (PR #1):** `crossfunction.py` (5 feeds + seller card + handoff), `render.py`
  (genome HTML), `app/streamlit_app.py` (rep→manager review + audit trail). Integrated via the
  `synthesize_cycle → enrich_crossfunctional → render_briefing` seam — hooks in `run.py` auto-wire it.
- **19/19 tests pass** (11 core + 8 enrichment/render). Evaluation: **100% top-driver agreement (7/7) ·
  100% citation coverage · 0% competitor false-alarm.** `run --all` emits enriched JSON + genome HTML.
- **Portfolio intelligence (`--portfolio`):** win-rate analytics (overall + by product), top win/loss
  drivers, **competitor battlecards**, enablement coaching hotspots + a styled HTML dashboard.
  Win rate 56% (9W/7L); Entrata loss rate 100% (pricing+risk). **22/22 tests pass.**
- Streamlit review app verified live (Genome / Rep-Manager review / Cross-functional / Audit / Guardrail).

## In progress
- Final reviewer walkthrough + submission package post to the team Teams channel.

## Next best action
- Run the MVP demo for a non-author reviewer; finalize `03_Final_Submission/README.md`; post to Teams.

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
