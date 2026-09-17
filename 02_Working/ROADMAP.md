# Deal DNA: The Win-Loss Decoder for Sales — Build Roadmap (Draft for Review)

> Status: **DRAFT — awaiting approval.** Nothing is built yet beyond workspace scaffolding.
> Use case channel prefix: `DD` · Deadline: 11:59 PM PT, Thu Sep 17, 2026.

---

## 1. What the package told us (facts, not guesses)

- The **Participant Package is process only** (rules, collaboration, evidence, submission). The
  **detailed Deal DNA brief lives in your Teams channel** — we do not have its exact text yet, so
  Section 3 is our *inferred* problem definition and must be confirmed against the real brief.
- **Judging criteria:** business value, practicality, clarity of the prototype, adoption potential,
  follow-through, workflow quality, and safety & governance.
- **Hard constraints:**
  - Allowed AI tools: Copilot, RPGPT, ChatGPT/Codex, Claude (whatever the team is licensed for).
  - Managed connectors only — **no custom MCP server**, no installing/configuring servers.
  - **Never** put credentials/keys/secrets in any prompt, file, or repo.
  - **No automated customer/employee/employment/compensation/performance/legal/production decisions.**
    Keep a **human reviewer in the loop** and document the review point.
  - Use only **approved/owned data**. Sponsor data needs confirmed access + tool-use + package permission.
  - Format is flexible, but it must satisfy the brief + evidence requirements.

## 2. The judge's lens — what a winning Deal DNA feature looks like

If I were judging, the top submission would:
- Tie to **one high-value sales decision** (not "solve all of sales"). Example: *"Which loss reasons
  are costing us the most, and what should reps change on the next deal against Competitor X?"*
- Produce **actionable output** (recommendations, at-risk deal alerts, coaching prompts) — not just charts.
- Be **grounded** in real/representative data with visible evidence; label estimates vs measured.
- Be a **repeatable workflow** a sales manager could actually run each week.
- Show **governance**: no PII misuse, insights *advise* while humans decide, clear limits.

## 3. Proposed solution concept (MVP) — *to confirm against the real brief*

**"Deal DNA Decoder"** — an AI-assisted win-loss analysis tool that turns raw closed-deal data into a
decoded "DNA profile" of why deals are won and lost, plus forward-looking coaching and risk signals.

Core capabilities (MVP scope):
1. **Ingest** a win-loss dataset (CSV export of closed deals + optional free-text win/loss notes).
2. **Decode the DNA** — compute the factors most associated with wins vs losses (price, competitor,
   product fit, deal size, sales cycle, champion strength, industry/segment, etc.).
3. **Loss-reason taxonomy** — cluster qualitative notes into a clean, ranked set of loss/win themes.
4. **Competitor threat view** — where we lose, to whom, and the recurring reasons.
5. **Deal-health / early-warning score** — apply the learned pattern to *open* deals to flag at-risk ones.
6. **Actionable recommendations** — coaching prompts and playbook adjustments per segment/competitor.
7. **Human-in-the-loop** — every recommendation is advisory with a clear "reviewed by" step.

Stretch (only if time allows): trend-over-time view, exportable manager briefing, "ask the data" chat.

## 4. Artifact form & architecture (respecting constraints)

Recommended primary artifact: a **self-contained, no-backend web app / HTML dashboard** (Claude-artifact
style) plus a short **AI-assistant prompt/agent spec** and a **document package** with evidence.

Why this shape:
- **No server / no MCP / no credentials** — runs locally in a browser, satisfies all guardrails.
- **Reviewer-friendly fallback** — works offline; screenshots/video are easy evidence.
- **Demonstrable** — reviewer loads sample CSV → sees the decoded DNA + recommendations immediately.

Data plan:
- Use **synthetic/representative sample data** we generate (clearly labeled) so we never touch
  unapproved sponsor data. If the team has an *approved* real export, we swap it in behind the same schema.

Proposed pieces:
- `Deal_DNA_Decoder.html` — single-file dashboard (upload/paste CSV → analysis + recommendations + export).
- `sample_data/deals_sample.csv` — labeled synthetic win-loss dataset.
- `AI_Assistant_Spec.md` — prompt/instructions for a Copilot/Claude/GPT "Win-Loss Decoder" assistant
  (grounded, advisory, human-in-the-loop) as the AI-tool component the brief expects.
- Evidence in `STATUS.md` (typical case, ambiguous-input case, guardrail case).
- Final `03_Final_Submission/README.md` tying it all together.

## 5. Phased plan (mapped to the ~48h window)

| Phase | Goal | Output | Owner |
| --- | --- | --- | --- |
| 0. Setup ✅ | Folders, templates, roadmap | Workspace scaffold + this file | — |
| 1. Confirm brief & scope | Lock problem, user, decision, data source | Filled TEAM_CHARTER.md | Team + SME |
| 2. Data schema + sample | Define columns; generate labeled synthetic data | `deals_sample.csv` | Build |
| 3. Core decoder | Win/loss driver analysis + loss-reason taxonomy | Working analysis in HTML | Build |
| 4. Insights + risk score | Competitor view, early-warning score, recommendations | Dashboard sections | Build |
| 5. AI assistant spec | Grounded advisory assistant instructions | `AI_Assistant_Spec.md` | Domain |
| 6. Test + evidence | 3 test cases logged (typical/ambiguous/guardrail) | STATUS.md log + screenshots | Test |
| 7. Package + review | Final README, reviewer-access check, fallback | 03_Final_Submission ready | Demo |

## 6. Evidence & submission alignment (built in from the start)

- Log tests in `00_Admin/STATUS.md`: typical case, missing/ambiguous input, guardrail case.
- Keep `DECISIONS.md` + `HANDOFF.md` current.
- Final README states: problem, user, result, review path, sources, reused-vs-created, limits, next step.
- Reviewer-access check by a non-author teammate; include static screenshots/video fallback.

## 7. Decisions I need from you before building

1. **Real brief:** Can you paste the actual Deal DNA brief text from the Teams channel? (validates Section 3)
2. **Data:** Do we have an approved real CRM/win-loss export, or should we build on **synthetic sample data**?
3. **Artifact form:** OK with **HTML dashboard + AI-assistant spec + doc package**, or do you prefer a
   pure AI agent/GPT, or a video-led package?
4. **AI tool:** Which is your team licensed for — Copilot, RPGPT, ChatGPT/Codex, or Claude?
5. **Team:** Size and who owns build / test / demo?

---

**Next step once you approve:** lock scope in `TEAM_CHARTER.md`, then build Phase 2–3 (sample data +
core decoder) as the first working version.
