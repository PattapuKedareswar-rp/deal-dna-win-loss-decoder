# Deal DNA — Judge Review & Fix Plan

> Written as an adversarial hackathon judge. The tone is deliberately critical: the goal is to
> expose every weakness so you can fix it. Each item has: **what I see**, **why it loses points**,
> **exact fix** (files/functions), and **effort**. Work top-down — items are ordered by impact on
> the official judging criteria (business value, practicality, clarity, adoption, follow-through,
> workflow quality, safety & governance).

**Repo state reviewed:** commit `9a95152`. Stack: Python pipeline + Streamlit app, OpenAI optional,
18 synthetic transcript cycles.

---

## Scorecard (harsh, current state)

| Criterion | Score | Ceiling blocker |
|---|---|---|
| Win/loss insight quality | 6/10 | Heuristic extraction; metrics on self-authored synthetic gold |
| Traceability & human review | 8/10 | Strong — citations + review loop. Loses points: no persistence/roles |
| Cross-functional usefulness | 6/10 | Feeds are templated, not specific; shallow handoff |
| Theme detection & market signal | 6/10 | Works, but small synthetic set; no real-transcript validation |
| Safety, privacy & governance | 7/10 | Guardrail good; but no real consent/retention enforcement in practice |
| **"Agentic" claim** | **3/10** | **No autonomous planner/tool-calling loop — this is the headline gap** |

---

## P0 — Critical (fix first; these are what a judge will call out loudly)

### P0.1 — It is not actually "agentic"
**What I see:** `synthesize.py` runs a fixed sequence (normalize → intake → evidence → synthesize).
The LLM (`evidence.py`, `crossfunction.py`) is a single structured-output call, not an agent. There
is no planner, no tool selection, no reasoning loop, no ability to answer a free-form question.
**Why it loses points:** the use case and your own pitch say "agent." A judge will test it by asking
a question and finding there is nothing to ask. Biggest credibility gap.
**Fix (concrete):**
- Add `src/deal_dna/agent.py` with an OpenAI **function/tool-calling loop**. Register the existing
  deterministic analytics as tools: `compute_win_rates`, `competitor_breakdown`, `score/evidence for a
  cycle`, `build_radar`, `build_portfolio`, `get_cycle_drivers(cycle_id)`.
- The loop: system prompt (grounding rules) → model picks tools → execute → feed results back →
  model composes an evidence-cited answer. Cap at ~5 tool calls.
- Add a Streamlit page **"Ask Deal DNA"**: text box → show the tool calls the agent made (transparency)
  → show the grounded answer with citations. Offline fallback: canned intent-routed answers.
**Effort:** M (½ day). **Highest leverage single change.**

### P0.2 — No real data source; 100% synthetic
**What I see:** `data/generate_data.py` fabricates transcripts. No SharePoint pull, no read-only
Salesforce query — the brief's actual sources.
**Why it loses points:** judges discount results that never touched real evidence. Adoption story is
hypothetical.
**Fix:**
- Implement one **real, approved** path behind the existing schema: a `sources/` module that can read
  a local approved `.txt` transcript export (drop-in folder) mapped to a Salesforce-outcome CSV.
- Document the connector plan explicitly and show at least one non-synthetic cycle end-to-end (even a
  manually approved sample), clearly labeled and consented.
**Effort:** M. If real data is unavailable, at minimum add a **loader abstraction** so swapping is trivial
and say so in the README.

### P0.3 — Evaluation credibility is weak
**What I see:** `evaluate.py` scores against `data/gold/human-reviewed-labels.csv` — which **you wrote**,
on synthetic data, and the "decisiveness priority" in `evaluate.py` is tuned to match it. 100%/100%/0%
is circular.
**Why it loses points:** a judge reads this as "graded your own homework."
**Fix:**
- Separate the **label author** from the **algorithm author** conceptually; add a second independent
  labeler column and report inter-rater agreement.
- Report metrics with **confidence caveats** and small-sample warnings in the UI and README.
- Add a **held-out** set the priority logic was NOT tuned on, and report that score separately.
**Effort:** S–M.

---

## P1 — High (materially weakens core criteria)

### P1.1 — Offline extraction is brittle keyword matching
**What I see:** `evidence.py` `_SIGNALS` is a regex list. Real transcripts (paraphrase, overlapping
speakers, typos, ASR errors) will break it. It also only reads lines whose role contains "buyer".
**Why it loses points:** insight quality collapses outside the synthetic sandbox.
**Fix:**
- Make the **LLM path the default** when a key exists; treat regex as an explicit "offline demo mode."
- Add negative tests: feed a messy/paraphrased transcript and show graceful abstention.
- Speaker role detection should not depend on the literal word "buyer."
**Effort:** M.

### P1.2 — Cross-functional feeds are templated, not insightful
**What I see:** `crossfunction.py` `_recommended_action` returns near-identical canned strings per
audience; `_insight` is a count sentence. The seller card recycles driver summaries.
**Why it loses points:** "cross-functional usefulness" is a scored criterion; generic output reads as
filler.
**Fix:**
- In the LLM path, generate **specific** actions tied to the exact quotes (e.g., "Entrata bundled
  payments free in 2 deals — Pricing should model a competitive bundling response").
- Deduplicate the seller card (currently repeats the same driver in stress/avoid/questions).
- Add **recurrence across cycles** (not just single-cycle) so Product/Pricing see patterns.
**Effort:** M.

### P1.3 — Implementation handoff is shallow
**What I see:** `schema.py` supports rich handoff, but generation fills little; only for Won deals.
**Why it loses points:** the brief explicitly calls out post-sale expectations for Implementations.
**Fix:** extract explicit **buyer expectations vs seller promises**, dependencies, and risks with
quotes; classify each `HandoffItem.kind`; flag items needing Legal/Product confirmation.
**Effort:** S–M.

### P1.4 — No persistence, roles, or auth in the review loop
**What I see:** `app/streamlit_app.py` stores review state in `st.session_state`; rep/manager are free
-text boxes; refresh loses everything except the `outputs/reviewed/*.json` snapshot.
**Why it loses points:** "human review" is a top criterion; a judge will refresh and see it reset.
**Fix:**
- Persist review state to disk (`outputs/reviewed/`) and **reload on open**.
- Add a simple role selector (Rep / Manager) that gates the Validate button; record identity in the
  audit trail.
**Effort:** S–M.

### P1.5 — Metrics presented as fact without caveats
**What I see:** portfolio shows "Win rate 56%" etc. with no "synthetic / small-sample" qualifier on the
numbers themselves (only a small banner).
**Why it loses points:** overstating is explicitly warned against in the brief.
**Fix:** label every aggregate with n and a "synthetic" tag; grey out any metric with n < 5.
**Effort:** S.

---

## P2 — Medium (polish, robustness, correctness edges)

### P2.1 — Deprecation warnings in the app
`use_container_width` and `st.components.v1.html` are deprecated. **Fix:** switch to
`width='stretch'` and `st.html`/`st.components.v1.iframe` as appropriate. **Effort:** S.

### P2.2 — Accessibility not verified
No contrast/keyboard audit; genome markers use color+icon (good) but charts rely on color. **Fix:**
run a contrast check; ensure every color has a text/label pair; keyboard-navigable controls. **Effort:** S.

### P2.3 — Radar false-positive risk
`radar.py` counts any negative/mixed driver; a mislabeled driver inflates a "trend." **Fix:** require
≥2 distinct cycles AND ≥2 distinct accounts; show the contributing quotes on hover. **Effort:** S.

### P2.4 — Competitor abstention is coarse
`evidence.py` sets `is_loss_reason` only on "we chose/went with/selected." Real buyers phrase this many
ways; also risk of a Won-deal competitor mention being mislabeled. **Fix:** gate `is_loss_reason` on
outcome==Lost AND explicit causal language; add tests for won-deal mentions. **Effort:** S.

### P2.5 — Audit verdict is always "PASS WITH REVIEW"
Because `review.status` starts "Needs Review," every deal shows the same verdict — a judge may read it
as the check doing nothing. **Fix:** differentiate: PASS once manager-validated; show WHY review is
required (specific issue), not a blanket string. **Effort:** S.

### P2.6 — Tests don't cover the LLM path or messy input
All 22 tests run offline on clean synthetic data. **Fix:** add a mocked-LLM test and a
malformed-transcript abstention test. **Effort:** S–M.

---

## P3 — Submission & story (cheap points teams forget)

- **P3.1** No demo video / narrated script in the package. Add a 2–3 min walkthrough. (`--demo` exists;
  record it.) 
- **P3.2** README lacks a crisp "limits & what's real vs simulated" section stated plainly.
- **P3.3** No architecture diagram in the repo (only prose). Add one image/mermaid.
- **P3.4** Reviewer-access check not documented (who, when, result) — required by the brief.
- **P3.5** `DEAL_DNA_MASTER_PROMPT.md` still describes an agent that isn't fully built — align claims to
  reality or build P0.1 so the claim is true.

---

## Suggested fix order (fastest path to a higher score)
1. **P0.1** Ask Deal DNA agent page (makes "agentic" true + demos well).
2. **P1.4** Persist + role-gate the review loop.
3. **P1.2 / P1.3** Make feeds + handoff specific (LLM path).
4. **P0.3 / P1.5** Honest evaluation + caveated metrics.
5. **P2.x** deprecations, radar/abstention hardening, audit verdict nuance.
6. **P0.2** one real/approved data path (or a clean loader abstraction + honest README).
7. **P3.x** demo video, diagram, README limits, reviewer-access note.

## What is already strong (do not regress)
Citation-locked evidence; cycle-level rollup; the rep→manager review + audit trail; the advisory
guardrail (read-only, no CRM write-back); calibrated abstention framing; and the executive/battlecard
intelligence layer. Keep these front-and-center in the demo.
