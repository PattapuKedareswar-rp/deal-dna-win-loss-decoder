# Deal DNA — The Win/Loss Decoder for Sales

Evidence-first sales-conversation intelligence. Deal DNA reads approved **sales-call transcripts**,
connects them to **read-only Salesforce outcomes**, and decodes **why deals win or lose** — with
every finding **citation-locked** to a quote, speaker, timestamp, and source. It is **advisory and
read-only**: it never writes to CRM, never contacts customers, and keeps a human in the loop.

> All data in this repo is **SYNTHETIC** — not real customer data.

## What's built (Person A — Evidence & Intelligence Core)

- `data/generate_data.py` — synthetic, speaker-attributed, timestamped transcripts + a Salesforce
  outcome map + reference taxonomies + a small human-labeled gold set.
- `src/deal_dna/schema.py` — the shared **`DealDNA`** contract (the seam with Person B).
- `normalize.py` → `intake.py` → `evidence.py` → `synthesize.py` — the pipeline that turns
  transcripts into a citation-locked `DealDNA` per cycle (rolled up **by cycle, not by call**).
- `audit.py` — traceability + governance checks and the **guardrail** that refuses external actions.
- `radar.py` — market-signal radar (recurring hesitations + alternative-software mentions, with a
  false-alarm guard).
- `run.py` — the CLI orchestrator.

It runs fully **offline** (deterministic) with no API key, and uses **OpenAI** when a key is present.

## Quick start

```powershell
cd deal_dna_decoder
python -m pip install -e ".[dev]"
python data/generate_data.py           # create synthetic transcripts + Salesforce map

# Offline mode needs no key:
$env:DEAL_DNA_OFFLINE = 1
python -m deal_dna.run --all            # analyze every cycle -> outputs/*.json
python -m deal_dna.run --radar          # market-signal radar
python -m deal_dna.run --evaluate       # score decoded drivers vs the human gold set
python -m deal_dna.run --portfolio      # executive intelligence + outputs/portfolio.html
python -m deal_dna.run --demo           # narrated Won/Lost/Stalled walkthrough
python -m deal_dna.run --check "email the customer a discount"   # guardrail demo
python -m deal_dna.run --write-fixture  # emit data/fixtures/sample_dealdna.json for Person B
python -m pytest -q                     # offline test suite
```

To use OpenAI instead of the offline path, copy `.env.example` to `.env`, set `OPENAI_API_KEY`
(never commit it), and leave `DEAL_DNA_OFFLINE=0`.

## The seam (how Person B plugs in)

Person A produces the base `DealDNA` JSON (`outcome`, `drivers`, `competitor_mentions`, `unknowns`).
Person B consumes it and fills the enrichment fields:

- `synthesize_cycle(cycle_id) -> DealDNA`  — provided by Person A (`src/deal_dna/synthesize.py`).
- `enrich_crossfunctional(d) -> DealDNA`   — to be built by Person B (`crossfunction.py`): the five
  cross-functional feeds, the seller coaching card, and the implementation handoff.
- `render_briefing(d) -> str`              — to be built by Person B (`render.py`) + the genome
  review web app in `app/`.

Person B can start immediately against `data/fixtures/sample_dealdna.json` without waiting.

## Governance

Read-only Salesforce · no CRM write-back / outreach / auto-publish · human review before sharing ·
synthetic data only · every finding traceable · abstains (`Needs Review` / `Not observed`) instead
of guessing · a competitor mention is never auto-treated as a loss reason · API key is env-only.
