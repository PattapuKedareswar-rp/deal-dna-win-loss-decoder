# Deal DNA: The Win-Loss Decoder — Master Build Prompt

> **How to use this file:** Paste everything below into a capable coding agent (GitHub Copilot,
> ChatGPT/Codex, or Claude) as a single instruction. It is written to be **self-sufficient**: one
> prompt that fully specifies the vision, constraints, data, architecture, file layout, component
> behavior, tests, and definition of done needed to build the complete project end to end.

---

## 0) Your role and mandate

You are a **senior AI application engineer** building a competition-grade prototype for the RealPage
Q3 AI Hackathon, use case **"Deal DNA: The Win-Loss Decoder for Sales"** (channel prefix `DD`).

Your mandate: build an **agentic, OpenAI-powered win-loss intelligence analyst** that turns a sales
team's closed-deal history and open-pipeline data into a **decoded "Deal DNA" briefing** — the
factors that drive wins and losses, the competitive threat picture, at-risk open deals, and specific,
evidence-cited coaching actions. The system is **advisory only**, with a **human-review gate** on
every recommendation.

Build for the judging criteria: **business value, practicality, clarity of the prototype, adoption
potential, follow-through, workflow quality, and safety & governance.** Favor a clear, trustworthy,
demonstrable prototype over breadth.

---

## 1) Hard constraints (do not violate)

1. **Model:** Use **OpenAI** as the main model via the official `openai` Python SDK
   (Responses/Chat Completions with **function/tool calling**). Default model `gpt-4o` (allow an env
   override, e.g. `gpt-4o-mini` for cost).
2. **No MCP server.** Do **not** create, install, or configure any custom MCP server. The agent uses
   in-process Python functions exposed as OpenAI tools — nothing else.
3. **No secrets in files.** The OpenAI API key is read **only** from the environment variable
   `OPENAI_API_KEY` (loaded via `python-dotenv` from a **git-ignored** `.env`). Never hard-code,
   print, log, or commit a key. Ship a `.env.example` with a placeholder only.
4. **Advisory + human-in-the-loop.** The system must **never** automate or execute a customer,
   employee, employment, compensation, performance, legal, or production action (no sending email, no
   CRM writes). Every recommendation is labeled **"PENDING HUMAN REVIEW"** with a `reviewed_by` slot.
5. **Grounded numbers.** All statistics are computed **deterministically in Python (pandas)**. The LLM
   **explains and recommends** but must **not invent numbers**. Every recommendation cites the
   underlying stat/segment it came from, and labels findings as **measured** vs **estimated**.
6. **Data:** Use the provided **synthetic sample data** (clearly labeled synthetic). Keep the schema
   stable so a real, approved CRM export can be swapped in later behind the same columns.

---

## 2) Domain context (RealPage / multifamily B2B SaaS)

RealPage sells software to property-management companies. Deals are B2B SaaS. Ground the vocabulary in
this reality so the output feels credible to a sales leader:

- **Products:** AI Revenue Management, Resident Screening, Payments & Billing, Property Management
  Platform, Leasing & Marketing.
- **Segments:** SMB, Mid-Market, Enterprise.
- **Regions:** Northeast, Southeast, Central, West.
- **Industries:** Conventional Multifamily, Student Housing, Affordable, Single-Family Rental.
- **Competitors:** Yardi, Entrata, MRI Software, ResMan, AppFolio, None.
- **Win/Loss reasons (taxonomy seed):** Strong ROI / revenue lift · Product fit / platform
  consolidation · Superior support / implementation · Trusted relationship / references · Price too
  high · Missing feature / product gap · Lost to competitor incumbent · Implementation / risk
  concerns · Timing / budget frozen.

---

## 3) Data contract (build to these exact schemas)

Two CSV files under `data/`. Treat these columns as the canonical contract.

**`closed_deals_sample.csv`** (historical, labeled outcomes):
```
deal_id, account, segment, region, product, industry, deal_size_usd, sales_cycle_days,
rep, competitor, discount_pct, num_stakeholders, champion_strength, outcome, primary_reason, notes
```
- `outcome` ∈ {Won, Lost}; `champion_strength` ∈ {Low, Medium, High}; `discount_pct` integer 0–40;
  `deal_size_usd` integer; `sales_cycle_days` integer; `notes` = free-text call/deal summary.

**`open_deals_sample.csv`** (live pipeline, no outcome yet):
```
deal_id, account, segment, region, product, industry, deal_size_usd, days_in_stage, stage,
rep, competitor, discount_pct, num_stakeholders, champion_strength, notes
```
- `stage` ∈ {Discovery, Demo, Proposal, Negotiation} (or similar); no `outcome`, no `primary_reason`.

If a sample generator is needed, provide `data/generate_sample_data.py` that emits ~120 closed and
~30 open rows with realistic distributions drawn from the enums in §2 (Won/Lost roughly balanced;
correlated signals so patterns are discoverable — e.g., high discount + Low champion + incumbent
competitor skews Lost). Seed the RNG for reproducibility. **Label the data as synthetic in a header
comment / README.**

---

## 4) The trust principle (design center)

> **Deterministic math + LLM narration.** Pandas computes every number; the LLM only interprets,
> clusters qualitative text, and writes recommendations. This eliminates hallucinated statistics and
> is the project's core credibility argument to judges. Enforce it in code: analytics tools return
> structured numeric results; agent prompts forbid inventing figures and require citing tool outputs.

---

## 5) Agentic architecture

Implement a **planner/orchestrator + specialist tools + governance** pattern using OpenAI function
calling. The orchestrator receives a plain-English question, autonomously decides which tools to call,
loops until it has enough evidence, then synthesizes a briefing that passes a governance check.

```
User question
   -> Orchestrator/Planner agent (OpenAI, tool-calling loop)
        -> Data Analyst tools (deterministic pandas)
             - compute_win_rates(group_by)
             - driver_analysis()
             - competitor_breakdown()
             - segment_slice(filters)
        -> Theme Miner (LLM over notes) -> reason taxonomy + competitor objections
        -> Risk Scorer (deterministic score + LLM explanation) -> score_open_deals()
        -> Coach (LLM) -> evidence-cited recommendations per segment/competitor
   -> Governance/Guardrail agent (LLM+rules)
        - verify each claim maps to a tool result (grounding)
        - label measured vs estimated
        - insert "PENDING HUMAN REVIEW" + reviewed_by
        - refuse/redirect any action request (email, CRM write, etc.)
   -> Briefing (Markdown + optional HTML export)
```

**Agent/specialist responsibilities**

- **Orchestrator:** plans the investigation, calls tools, decides when to stop, assembles the briefing.
  System prompt forbids inventing numbers; requires citing tool outputs; keeps scope to win-loss.
- **Data Analyst tools (deterministic):** the numeric backbone (see §6).
- **Theme Miner (LLM):** clusters `notes` + `primary_reason` into a ranked win/loss taxonomy and
  extracts recurring competitor objections. Returns structured JSON (theme, count, example deal_ids).
- **Risk Scorer:** deterministic health score for each open deal from learned signals (discount,
  champion strength, stakeholder count, days-in-stage, competitor presence, segment/product win-rate
  priors), plus an LLM one-line rationale. Flags at-risk deals (score below threshold).
- **Coach (LLM):** converts findings into concrete rep-facing actions per segment/competitor, each
  citing the evidence it came from.
- **Governance/Guardrail (LLM + rules):** grounding check, measured/estimated labels, human-review
  gate, and hard refusal of any request to take an external action.

---

## 6) Deterministic analytics tools (exact behavior)

Implement in `src/deal_dna/analytics.py`; expose typed wrappers as OpenAI tools.

- `load_closed()` / `load_open()` -> pandas DataFrames with dtype coercion and validation.
- `compute_win_rates(group_by: str | list[str]) -> list[dict]`: win rate = Won / (Won+Lost) per
  group; include counts. Support group_by any categorical column(s).
- `driver_analysis() -> dict`: for each factor, quantify association with Won vs Lost. For categoricals
  (competitor, champion_strength, segment, product, industry, region) report win-rate deltas vs
  baseline. For numerics (deal_size_usd, sales_cycle_days, discount_pct, num_stakeholders) report
  mean/median for Won vs Lost and the gap. Return a ranked list of the strongest signals.
- `competitor_breakdown() -> list[dict]`: per competitor — deal count, win rate, avg discount, top
  loss reasons, avg deal size.
- `segment_slice(filters: dict) -> dict`: summary stats for an arbitrary filtered subset.
- `score_open_deals() -> list[dict]`: per open deal — 0–100 health score, top 2 contributing factors,
  risk band (Healthy / Watch / At-Risk). Scoring is a transparent weighted function of the drivers
  learned from closed deals; document the weights. Deterministic and explainable.

Return plain JSON-serializable structures. No LLM calls inside these functions.

---

## 7) Project structure

```
deal_dna_decoder/
├─ README.md                     # what it is, setup, run, safety, sample commands
├─ requirements.txt              # openai, pandas, pydantic, python-dotenv, (optional) streamlit
├─ .env.example                  # OPENAI_API_KEY=your-key-here  (placeholder only)
├─ .gitignore                    # .env, __pycache__/, *.pyc, exports/, .venv/
├─ data/
│  ├─ generate_sample_data.py
│  ├─ closed_deals_sample.csv
│  └─ open_deals_sample.csv
├─ src/deal_dna/
│  ├─ __init__.py
│  ├─ config.py                  # loads env, model name, thresholds, weights
│  ├─ analytics.py               # deterministic pandas tools (§6)
│  ├─ tools.py                   # pydantic tool schemas + OpenAI tool definitions -> analytics
│  ├─ agents.py                  # orchestrator + specialist prompts + tool-calling loop
│  ├─ governance.py              # grounding check, human-review gate, action-refusal rules
│  ├─ briefing.py                # assemble Markdown briefing + HTML export
│  └─ agent.py                   # CLI entrypoint: python -m deal_dna.agent "question"
├─ app/streamlit_app.py          # OPTIONAL interactive demo UI (local, not MCP)
├─ exports/                      # generated briefings (git-ignored)
└─ tests/
   └─ test_analytics.py          # deterministic unit checks on sample data
```

---

## 8) Interfaces

1. **CLI (required):** `python -m deal_dna.agent "Why are we losing Enterprise deals to Entrata, and
   which open deals are most at risk?"` -> runs the agent loop, prints the briefing, writes
   `exports/briefing_<timestamp>.md` and `.html`.
2. **Streamlit (optional, recommended for live demo):** upload/select CSVs, type a question, view the
   briefing with tables and the at-risk deal list. Local app only; still reads the key from env.
3. **Static HTML briefing (required as offline fallback):** a self-contained HTML export so a reviewer
   without a key can still see a real result via screenshots/file.

---

## 9) Output: the briefing format

Every run returns a structured briefing with these sections:

1. **Question & scope** — restated question, data window, "synthetic sample data" label.
2. **Deal DNA summary** — the 3–5 strongest win drivers and loss drivers (measured), each with the
   stat and sample size.
3. **Competitive picture** — per-competitor win rate and top loss reasons; where we are most exposed.
4. **At-risk open deals** — table of At-Risk/Watch deals with score, top factors, and one-line reason.
5. **Recommended actions (PENDING HUMAN REVIEW)** — 3–6 specific coaching/playbook actions, each
   citing the evidence, with owner + `reviewed_by:` blank.
6. **Limits & governance** — synthetic data, advisory-only, measured vs estimated, human-review note.

---

## 10) Safety & governance (must implement, not just document)

- Load key from env only; fail with a clear message if missing; never echo it.
- Governance agent rejects any instruction to take an external action and responds with a
  human-review recommendation instead.
- Grounding check: if the draft contains a number not present in a tool result, flag/repair it.
- All recommendations carry the review gate; nothing is presented as an executed decision.

---

## 11) Build sequence (follow in order)

1. Scaffold structure, `requirements.txt`, `.env.example`, `.gitignore`, `config.py`.
2. `data/generate_sample_data.py` + regenerate the two CSVs (synthetic, seeded, correlated signals).
3. `analytics.py` deterministic tools (§6) + `tests/test_analytics.py`; verify on sample data.
4. `tools.py`: pydantic schemas + OpenAI tool definitions bound to analytics functions.
5. `agents.py`: orchestrator tool-calling loop + specialist prompts (Theme Miner, Risk Scorer, Coach).
6. `governance.py`: grounding, review gate, action refusal.
7. `briefing.py`: Markdown + HTML assembly.
8. `agent.py`: CLI entrypoint wiring it together.
9. Optional `app/streamlit_app.py` demo.
10. `README.md`: setup (venv, install, set `OPENAI_API_KEY`), run commands, safety, sample Q&A.

---

## 12) Testing & evidence (produce this for the submission)

Provide three logged tests:

- **T-01 Typical:** a normal question -> useful, source-grounded briefing.
- **T-02 Ambiguous/missing input:** vague question or a data gap -> the agent asks a safe clarifying
  question or states the limitation instead of inventing facts.
- **T-03 Guardrail:** "email these at-risk customers a discount" -> the agent refuses to act and
  returns a human-review recommendation only.

Capture input, expected behavior, observed result, pass/fail, and evidence (export file/screenshot).

---

## 13) Definition of done

- One command runs the full agentic loop on synthetic data and produces a complete, grounded briefing
  with an at-risk list and review-gated recommendations.
- Numbers are all traceable to deterministic tools; no invented figures.
- Key is env-only; no secret in any file; `.env` git-ignored; `.env.example` present.
- The three tests pass; a static HTML briefing exists as an offline fallback.
- `README.md` lets a new reviewer set up and run it, and states scope, sources, limits, and the
  human-review boundary.

---

### Appendix — example interaction

**Input:** `"Where are we most exposed to Entrata, and which open deals should a manager coach first?"`

**Expected shape of output:** a briefing that (a) shows Entrata win rate and top loss reasons from
`competitor_breakdown()`, (b) names the 2–3 segments/products with the worst Entrata win rate from
`compute_win_rates`, (c) lists At-Risk open deals facing Entrata from `score_open_deals()`, and (d)
gives review-gated coaching actions (e.g., "lead with implementation de-risking where champion is
Low"), each citing the stat it came from — all labeled synthetic/advisory.
