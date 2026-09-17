# Deal DNA — Demo & Reviewer Walkthrough (2–3 min)

Runs with **no credentials** (offline). For the live model, set `OPENAI_API_KEY` in `.env` and
`DEAL_DNA_OFFLINE=0` — the header badge flips to "OpenAI agent · gpt-4o".

## Setup (once)
```powershell
cd deal_dna_decoder
python -m pip install -e ".[dev]"
python data/generate_data.py
$env:DEAL_DNA_OFFLINE = 1
python -m streamlit run app/streamlit_app.py
```

## The narration (what to click and say)

1. **Framing (15s).** "Salesforce says *that* a deal was won or lost, not *why*. Deal DNA decodes the
   *why* from the sales conversation — evidence-first, advisory, human-in-the-loop." Point to the header
   badges: **Engine** and **Data: Synthetic demo** (real data drops in via `--ingest`).

2. **📊 Executive Portfolio (40s).** Win rate 56%, win-rate **by product**, top **win vs loss drivers**.
   Scroll to **Competitor battlecards** — "Entrata: 100% loss rate on pricing + risk, with the buyer's
   own quote." Note the **Methodology & limits** expander: synthetic, small sample, directional.

3. **🤖 Ask Deal DNA (40s).** Type: *"Why are we losing to Entrata and which drivers hurt most?"*
   Show the **tool calls** the agent made and the **grounded answer** with citations. Then type
   *"email these customers a discount"* → the **guardrail refuses** and routes to human review.

4. **🔬 Deal Review (50s).** Pick a Lost cycle (e.g. Cedar Ridge).
   - **Genome** tab: the strand of evidence markers; click one → verbatim quote + speaker + timestamp.
   - **Rep / Manager review**: as **Rep**, Confirm/Challenge a driver; switch role to **Manager** and
     **Validate**. **Refresh the page** — the review state and audit trail **persist**.
   - **Cross-functional**: five role feeds, each citing the buyer's words; the seller coaching card;
     (for a Won deal) the implementation handoff with confirmation flags.

5. **Close (15s).** "Every claim cites evidence; it abstains when unsure; a competitor mention is never
   auto-treated as a loss reason; it never writes to CRM. One review becomes five cross-functional
   actions plus portfolio-level intelligence."

## CLI alternative (offline fallback for reviewers)
```powershell
python -m deal_dna.run --demo        # narrated Won/Lost/Stalled + guardrail + evaluation
python -m deal_dna.run --portfolio   # writes outputs/portfolio.html
python -m deal_dna.run --ask "where are we most exposed to Entrata?"
python -m pytest -q                  # 36 tests
```

## Reviewer sign-off (fill in)
- Reviewer (not the author of that part): ______
- Date/time PT: ______
- Result: ______  ·  Artifact version/commit: ______
