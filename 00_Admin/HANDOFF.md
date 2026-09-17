# Deal DNA — Handoff & Completion Note

## Handoff note
- **Handoff date/time:** 2026-09-18, PT
- **Team / channel ID:** DD (Deal DNA: The Win/Loss Decoder for Sales)
- **Current status:** Demo ready
- **Completed:** Evidence-first pipeline (normalize → intake → evidence → synthesize), audit + advisory
  guardrail, market-signal radar, evaluation harness, agent (OpenAI tool-calling "Ask Deal DNA"),
  Streamlit app (Executive Portfolio · Ask Deal DNA · Deal Review), rep→manager review loop with
  persistence + roles, five cross-functional feeds, seller card, implementation handoff. 36/36 tests.
  Ingested the 27 approved SharePoint transcripts (→26 cycles) and validated end-to-end on real data.
- **Decisions made:** Advisory/read-only (no CRM write-back). Outcomes come from Salesforce only; with
  no Salesforce access, real cycles stay `Needs Review` (never guessed from filenames). Public repo
  ships code + synthetic demo data only; real transcripts are git-ignored and local.
- **Evidence / files added:** `03_Final_Submission/README.md`, `FINAL_SUBMISSION_CHECKLIST.md`,
  `DEMO_SCRIPT.md`, `00_Admin/STATUS.md` (T-01/T-02/T-03 log), repo on GitHub.
- **Open questions / blockers:** Salesforce access to map Won/Lost and prove `Sale_Type__c='New'`
  eligibility; approved cycle grouping (some files are the same account across calls).
- **Next recommended action:** Add Salesforce outcomes to `data/approved_exports/index.csv`, re-run
  `--ingest` → win-rate, battlecard loss rates, and win/loss drivers populate.
- **Reviewer / SME needed:** Deal DNA SMEs (Jon.Barker, Kerri.Haltom, Michael.Davis1, yoric.dedeken).
- **Known limitations:** Win/loss rate empty until Salesforce outcomes added; small synthetic gold set
  (directional, not production accuracy); offline extraction is heuristic (OpenAI path is primary).

## Teams completion message (copy-paste)
> **Final submission — DD (Deal DNA: The Win/Loss Decoder for Sales).**
> Start with `03_Final_Submission/README.md`. The package includes the working prototype (Python
> pipeline + Streamlit app: Executive Portfolio, Ask Deal DNA agent, Deal Review with rep→manager
> review), a demo path (`DEMO_SCRIPT.md` / `python -m deal_dna.run --demo`), source & permissions
> notes, and the final checklist + handoff. Repo: https://github.com/PattapuKedareswar-rp/deal-dna-win-loss-decoder
> Validated on the 27 approved SharePoint transcripts (26 cycles) locally; outcomes remain Needs Review
> pending Salesforce (never guessed). Runs offline with no key, or on OpenAI gpt-4o. No CRM write-back;
> human review in the loop. Reviewer access checked by [name] at [time] PT. Artifact version: [commit].
