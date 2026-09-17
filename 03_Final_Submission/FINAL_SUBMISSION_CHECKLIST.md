# Deal DNA — Final Submission Checklist

**Team/channel:** DD · **Use case:** Deal DNA: The Win/Loss Decoder for Sales
**Artifact:** `deal_dna_decoder/` (Python pipeline + Streamlit app) · **Repo:** https://github.com/PattapuKedareswar-rp/deal-dna-win-loss-decoder
**Completed:** 2026-09-18 PT · **Owner:** Kedareswar (PattapuKedareswar-rp)

## Required package items (per Demo & Submission guide)
- [x] **1. README** — `03_Final_Submission/README.md` (problem, user, result, review path, evidence, sources, reuse, limits, next step).
- [x] **2. Final artifact** — code + Streamlit app in the repo; runs offline or on OpenAI gpt-4o.
- [x] **3. Demonstration path** — `DEMO_SCRIPT.md` (2–3 min walkthrough) + `python -m deal_dna.run --demo`.
- [x] **4. Source & permissions note** — in the README (approved SharePoint transcripts used locally; git-ignored; read-only Salesforce authority; env-only key).
- [x] **5. Handoff & checklist** — this file + `00_Admin/STATUS.md` (evidence log) + `00_Admin/HANDOFF.md`.

## Brief completion checklist
- [x] Read the official PDF brief; kept separate from implementation assumptions.
- [~] Confirm the Salesforce environment / describe objects — **not connected** (no access); outcomes = `Needs Review` (not guessed).
- [x] Configure the SharePoint transcript source — 27 approved `.txt` ingested via `--ingest` (Clari/Gong parser) → 26 cycles.
- [~] Prove new-sale eligibility at the opportunity-line level — **pending Salesforce** (`Sale_Type__c='New'`).
- [x] Build a cycle-level index with source + transcript-status fields (`data/approved_exports/index.csv`, git-ignored).
- [x] Preserve exact evidence citations (quote + speaker + timestamp + source on every driver).
- [x] Separate Won / Lost / Stalled / Needs Review (all real cycles currently `Needs Review` pending Salesforce).
- [x] Demonstrate at least one reviewer correction (rep→manager review loop + audit trail, persists across refresh).
- [x] Produce the five cross-functional views (Enablement, Product, Pricing, Product Marketing, Implementations).
- [x] Produce a seller coaching card.
- [x] Produce an implementation handoff summary (Won deals; confirmation flags).
- [x] Show at least one explicit unknown / evidence gap (`unknowns` + abstention).
- [x] Verify no CRM write-back or automatic outreach (advisory guardrail refuses external actions).
- [x] Apply RP Colorway rules; verify visual review (navy/white theme; color always paired with text/icon).
- [x] Report sample size, retrieval date, transcript completeness, and limits (README "Methodology & limits").

## Reviewer-access check
- [ ] Non-author teammate opens the app from Teams/SharePoint, runs a rep→manager review, refreshes to confirm persistence.
- [ ] Record: reviewer name, date/time PT, result, artifact commit — in `00_Admin/STATUS.md`.

## Freeze & post
- [ ] Place this package in the team Teams channel's connected SharePoint `Final Submissions` folder (team/ID folder).
- [ ] Post the completion note (see `00_Admin/HANDOFF.md`) with the start-here link + completion time PT.
- [ ] Stop modifying after posting. If an access/outage issue occurs, record time + item and contact Austin.braham@realpage.com.

## Known limitations (stated plainly)
- Win/loss **rate** is empty until Salesforce outcomes are added (tool refuses to guess from filenames).
- Public repo ships **code + synthetic demo data only** — no customer transcripts, outcomes, or keys.
- Small, author-labeled gold set → metrics are directional, not production accuracy.
