# Deal DNA: The Win/Loss Decoder — Master Build Prompt (v2, transcript-intelligence)

> **How to use:** Paste this whole file into a capable coding agent (Copilot / ChatGPT-Codex /
> Claude). It is self-sufficient — it specifies the vision, constraints, data, evidence contract,
> agent pipeline, output schema, UI, tests, and definition of done needed to build the full prototype.
> **This v2 supersedes any earlier "structured-stats" version.** The problem is **sales-call
> conversation intelligence**, not tabular deal statistics.

---

## 0) Role and mandate

You are a **senior AI application engineer** building a competition-grade prototype for the RealPage
Q3 AI Hackathon, use case **"Deal DNA: The Win/Loss Decoder for Sales"** (Sales Enablement sponsor).

Build an **agentic, evidence-first system** that reads approved **sales-call transcripts**, connects
them to **read-only Salesforce deal outcomes**, and decodes **why deals win or lose** — producing
**citation-locked** findings, a **human review loop** (rep → manager), and **five role-specific
cross-functional feeds**. Nothing is asserted without evidence; the system abstains when evidence is
missing. It never writes to CRM and never contacts customers.

**Company question:** Why did this deal win/lose/stall, and what should Enablement, Product, Pricing,
Product Marketing, and Implementations change?
**Seller question:** Given this cycle's evidence, what should the rep emphasize, verify, demo, or avoid next?

---

## 1) Hard constraints (do not violate)

1. **Model:** OpenAI via official `openai` Python SDK with **structured outputs / function calling**.
   Default `gpt-4o` (env override `OPENAI_MODEL`).
2. **No MCP server.** In-process Python only; no custom MCP server created/installed/configured.
3. **No secrets in files.** `OPENAI_API_KEY` from env via git-ignored `.env`; ship `.env.example`
   placeholder only. Never hard-code/log/commit a key.
4. **Read-only Salesforce. No CRM write-back, no auto-outreach, no auto-publishing.** Human review is
   required before any finding is "shared."
5. **Evidence-first + abstention.** Every material finding cites `quote + speaker + timestamp + source`.
   Separate **Observed** vs **Inferred**. When evidence is missing, return **Not observed / Unknown /
   Needs Review** — never guess. **A competitor mention is NOT proof of a loss or a loss reason.**
6. **Cycle-level, not call-level.** Aggregate by `cycle_id`; a multi-call deal is ONE observation.
7. **Data safety:** For the public/demo build use **synthetic, clearly-labeled transcripts** only —
   never real customer data in the repo. Document the real SharePoint/Salesforce/Clari connector path
   separately so it stays production-credible.

---

## 2) Domain & data contract

**Outcome model** (Salesforce is the authority for outcome):

| Outcome | Meaning | In win/loss denominator? |
|---|---|---|
| `Won` | Closed-won opportunity | Yes |
| `Lost` | Closed-lost opportunity | Yes |
| `Stalled / No Decision` | Open new-sale, substantive pre-contract evidence, independent stall signal | No |
| `Needs Review` | Mapping/eligibility/outcome/consent/evidence unreliable | No |

Do **not** infer `Lost` from a competitor name, silence, attendance, or an old close date.

**Synthetic data to generate** (label as synthetic in headers/README):
```
data/
  transcripts/<cycle_id>/<call_id>.txt        # speaker-attributed lines with [HH:MM:SS] timestamps
  transcripts/<cycle_id>/<call_id>.metadata.json  # cycle_id, call_id, date, source_system, product, stage, consent
  salesforce/opportunities.csv                # opportunity_id, account, product_family, stage, IsWon, outcome, owner, close_date
  reference/competitor-taxonomy.yaml          # Yardi, Entrata, MRI, ResMan, AppFolio, ...
  reference/product-taxonomy.yaml             # AI Revenue Mgmt, Screening, Payments, PMP, Leasing & Mktg
  reference/theme-taxonomy.yaml               # need, pricing, demo friction, ROI, integration, trust, timing, authority, risk
  manifest.csv                                # one row per call: source, cycle, outcome, completeness, consent
  gold/human-reviewed-labels.csv              # a few cycles with human labels for the eval harness
```
Generate ~10–15 cycles (mix of Won/Lost/Stalled, multi-call cycles included), realistic RealPage
multifamily context, with **injected but plausible signals** so drivers are discoverable. Seed the RNG.

---

## 3) Evidence contract (the shared seam between components)

Every material finding carries:
```
cycle_id, opportunity_id, account, call_id, call_date, source_system, source_url_or_path,
transcript_status, speaker, speaker_role, timestamp_start, timestamp_end,
exact_quote, observation, interpretation, category, direction, confidence, review_status
```
**Evidence labels:** `Observed` · `Inferred` · `Not observed` · `Unknown` · `Needs Review` · `Mixed`.
**Transcript completeness:** `Full transcript available` · `Full transcript remote only` ·
`Reviewed excerpts only` · `Speaker attribution incomplete` · `No usable transcript`.
Never call a reviewed excerpt a full transcript.

**Canonical output — `DealDNA` JSON per cycle** (this schema is the contract both people build to):
```json
{
  "cycle_id": "cyc-004",
  "opportunity_id": "006XX[…]",
  "account": "Example Account",
  "product_families": ["AI Revenue Management"],
  "outcome": "Lost",
  "outcome_source": "Salesforce IsWon",
  "transcript_status": "Full transcript available",
  "drivers": [
    {
      "category": "pricing", "direction": "negative", "label": "Observed",
      "summary": "Buyer flagged TCO once implementation fees were added.",
      "quote": "Once you add setup, you're 20% over the other bid.",
      "speaker": "Buyer - VP Ops", "timestamp": "00:24:11",
      "source": "data/transcripts/cyc-004/call-2.txt", "confidence": "high"
    }
  ],
  "unknowns": ["Decision authority not observed"],
  "competitor_mentions": [{"name": "Entrata", "quote": "…", "timestamp": "00:12:03", "is_loss_reason": false}],
  "cross_function_actions": {"enablement": [], "product": [], "pricing": [], "product_marketing": [], "implementations": []},
  "seller_coaching": {},
  "implementation_handoff": {},
  "review": {"status": "Needs Review", "rep": null, "manager": null, "reviewed_at": null, "corrections": []}
}
```

---

## 4) Agentic architecture (OpenAI-driven skills/pipeline)

Implement as an orchestrated pipeline of skills (each a module; LLM calls use structured outputs).
**No skill invents numbers or facts; each cites evidence or abstains.**

1. **Intake & provenance gate** — validate source, consent, date, transcript completeness, speaker
   attribution, opportunity mapping. Block or `Needs Review` on failure.
2. **Transcript normalizer** — normalize TXT/VTT/notes into a turn format preserving speaker, role,
   timestamp, source, exact wording. Never invent speaker identities.
3. **Evidence coder (LLM)** — extract findings per turn: category (need/pricing/demo/ROI/competitor/
   integration/trust/timing/authority/risk), direction, `Observed`/`Inferred`, quote, speaker,
   timestamp, confidence. Abstain when unsupported.
4. **Cycle synthesizer (LLM)** — roll all calls of a `cycle_id` into one win/loss decode: outcome vs
   interpretation, top win signals, top risk/loss signals, mixed/unknowns, themes, review hypotheses.
5. **Cross-functional translator (LLM)** — produce **five** distinct feeds (Enablement, Product,
   Pricing, Product Marketing, Implementations), each with owner suggestion, evidence, recurrence, review state.
6. **Seller coach (LLM)** — next-conversation card: stress / verify / avoid / biggest unanswered
   question / 3 buyer-centered questions / one proof to show. No personality judgments.
7. **Implementation handoff (LLM, Won deals)** — expected value, commitments, risks; separate buyer
   expectation from seller promise; flag items needing confirmation.
8. **Review & safety auditor** — traceability, unsupported causality, false certainty, competitor
   false-alarms, outcome leakage, cycle duplication, CRM-writeback attempts → PASS / PASS WITH REVIEW / BLOCKED.
9. **Market-signal radar (aggregate)** — recurring hesitations + alternative-software mentions across
   cycles with precision guardrails (recurrence ≥ N, low false-alarm).

---

## 5) Interfaces & experience

1. **CLI (required):** `python -m deal_dna.run --cycle cyc-004` → runs the pipeline → writes the
   `DealDNA` JSON + a rendered HTML/Markdown briefing to `outputs/`.
2. **Review web app (required):** shows the **Deal DNA genome** for a cycle — a strand of color-coded
   markers (win / risk / hesitation / competitor / unmet-need), each clickable to its evidence
   (quote+speaker+timestamp). Rep can **confirm / add context / challenge** each finding; manager can
   **validate**; every change lands in the `review.corrections` audit trail. Styled with RP Colorway.
3. **Five cross-functional feed views** + **seller coaching card** + **implementation handoff** views.
4. **Static HTML export** of one reviewed cycle as the offline reviewer fallback.

---

## 6) RP Colorway (presentation only — never changes evidence/outcome/governance)

Anchors: navy `#082649`, ink `#0A1420`, amber `#AE6B29`, UI/link blue `#2E6FB0`. Use sequential for
ordered values, diverging for variance, categorical (`#082649,#AE6B29,#E69F00,#009E73,#CC79A7,#56B4E9`)
for series, semantic (success `#2E8B57`, warning `#E8A21A`, error `#D2402A`) for status. Never signal
Won/Lost/risk/review-state by color alone — pair with text/icon. Default font Calibri. Keep **evidence,
interpretation, confidence, reviewer status, and recommended action visually distinct.**

---

## 7) Unique differentiators to implement (why we win)

- **Citation-locked genome** — no claim without `quote+speaker+timestamp+source`.
- **Calibrated abstention** — returns `Not observed`/`Needs Review`; competitor mention ≠ loss reason.
- **Cycle-level rollup** — dedupe multi-call deals by `cycle_id`.
- **Closed-loop review** — rep confirm/challenge → manager validate → audit trail.
- **Five role-specific feeds** — one analysis → five actionable audiences.
- **Genome visualization** — the memorable, brand-styled demo artifact.
- **Market-signal radar** — emerging trends with low false-alarm.
- **Implementation handoff** for Won deals — expected value, commitments, risks.

---

## 8) Governance & safety (implement, not just document)

Env-only key; read-only Salesforce; no CRM write-back / outreach / auto-publish; human review before
"shared"; synthetic data only in repo; every finding traceable; abstain over guess; keep source /
interpretation / reviewer-correction / final-approved states distinguishable; report sample size,
retrieval date, transcript completeness, and coverage gaps.

---

## 9) Project structure

```
deal_dna_decoder/
├─ README.md
├─ requirements.txt            # openai, pydantic, python-dotenv, pyyaml, jinja2, (ui) streamlit or flask
├─ .env.example                # OPENAI_API_KEY=your-key-here
├─ .gitignore                  # .env, __pycache__/, outputs/, .venv/
├─ data/                       # synthetic transcripts + salesforce map + reference + manifest + gold (see §2)
├─ src/deal_dna/
│  ├─ config.py                # env, model, thresholds
│  ├─ schema.py                # pydantic models for the evidence contract + DealDNA JSON (§3)
│  ├─ intake.py                # provenance gate
│  ├─ normalize.py             # transcript normalizer
│  ├─ evidence.py              # evidence coder (LLM)
│  ├─ synthesize.py            # cycle synthesizer (LLM)
│  ├─ crossfunction.py         # five feeds + seller coach + implementation handoff (LLM)
│  ├─ audit.py                 # review & safety auditor
│  ├─ radar.py                 # market-signal radar (aggregate)
│  ├─ render.py                # HTML/Markdown briefing + genome markup
│  └─ run.py                   # CLI orchestrator
├─ app/                        # review web app (genome UI, rep/manager review, feed views)
├─ outputs/                    # generated DealDNA JSON + briefings (git-ignored)
└─ tests/                      # schema + abstention + cycle-rollup + governance tests
```

---

## 10) MVP demo (build to this, end-to-end)

Take **1 Won + 1 Lost + 1 Stalled** cycle and show: Salesforce outcome + eligibility → call evidence
with exact excerpts + timestamps → cycle-level driver summary with uncertainty → **one** cross-functional
feed → **one** seller coaching card → **one** implementation handoff (Won) → **one reviewer correction
in the audit trail**. The demo answers: *what did we learn, where's the proof, who uses it, what's uncertain.*

---

## 11) Build sequence

1. Scaffold + `schema.py` (evidence contract + DealDNA JSON) + `config.py` + `.env.example` + `.gitignore`.
2. Synthetic data generator (§2) + manifest + gold labels.
3. Intake gate + normalizer + `tests`.
4. Evidence coder → cycle synthesizer → produce `DealDNA` JSON for the 3 demo cycles.
5. Cross-functional translator + seller coach + implementation handoff.
6. Audit + market-signal radar.
7. Genome review web app (rep/manager review + audit trail) + RP Colorway styling.
8. HTML export + README + eval harness.

---

## 12) Tests & evidence

- **T-01 Typical:** a Lost cycle → grounded, citation-locked drivers + one feed.
- **T-02 Abstention:** a cycle with a competitor mention but no loss evidence → does NOT label it a loss
  reason; returns `Needs Review`/`Not observed`.
- **T-03 Guardrail:** "update Salesforce / email the customer" → refuses, returns human-review recommendation.
- **Cycle-rollup test:** a 3-call cycle counts as ONE observation.

---

## 13) Definition of done

End-to-end run on synthetic data yields, for the 3 demo cycles: a `DealDNA` JSON with citation-locked
drivers, five feeds, seller card, Won-deal handoff; a genome review UI with working rep→manager review
+ audit trail; a static HTML fallback; passing tests (incl. abstention + rollup + no-writeback); key is
env-only and uncommitted; README lets a new reviewer set up, run, and understand scope, sources, limits,
and the human-review boundary.
