# Person B — Start Guide (Experience, Review Loop & Cross-Functional Outputs)

Welcome. Person A built the **evidence core** that turns transcripts into a citation-locked
`DealDNA` per deal. **Your job:** turn that `DealDNA` into (1) five cross-functional feeds + a seller
coaching card + an implementation handoff, (2) a **Deal DNA genome** view, and (3) a **review web app**
with a rep → manager approval loop and audit trail.

You are **never blocked** by Person A: you build against `data/fixtures/sample_dealdna.json`.

---

## 0) Get running in 10 minutes

```powershell
git clone https://github.com/PattapuKedareswar-rp/deal-dna-win-loss-decoder.git
cd deal-dna-win-loss-decoder/deal_dna_decoder
python -m pip install -e ".[dev]"
python data/generate_data.py            # synthetic transcripts + Salesforce map
$env:DEAL_DNA_OFFLINE = 1
python -m deal_dna.run --all            # writes outputs/cyc-*.json (base DealDNA)
python -m deal_dna.run --write-fixture  # refreshes data/fixtures/sample_dealdna.json
python -m pytest -q                     # 7 tests should pass
```

Open `data/fixtures/sample_dealdna.json` and `src/deal_dna/schema.py` — that JSON **is your input
contract**. Also read `deal_dna_decoder/README.md`.

To use OpenAI instead of offline: copy `.env.example` → `.env`, set `OPENAI_API_KEY`, set
`DEAL_DNA_OFFLINE=0`. **Never commit `.env`.**

---

## 1) The contract you consume (already built)

Person A fills these fields on `DealDNA` (`schema.py`):
`cycle_id, opportunity_id, account, product_families, outcome, transcript_status, call_count,`
`drivers[] (category, direction, label, summary, quote, speaker, speaker_role, timestamp, source,`
`confidence), competitor_mentions[], unknowns[]`.

**You fill the enrichment fields** (they exist in the schema, empty):
`cross_function_actions, seller_coaching, implementation_handoff, review`.

Do **not** change `schema.py` except in a joint "schema-drift" sync with Person A.

---

## 2) Files you own (no one else edits these)

```
src/deal_dna/crossfunction.py     # enrich_crossfunctional(d) -> DealDNA
src/deal_dna/render.py            # render_briefing(d) -> str   (HTML genome + briefing)
app/                              # review web app (Streamlit recommended)
app/static/colorway.css          # RP Colorway tokens
tests/test_crossfunction.py
tests/test_render.py
```

---

## 3) Deliverable 1 — `crossfunction.py`

Signature (this is the seam `run.py` will call):

```python
from .schema import DealDNA
def enrich_crossfunctional(d: DealDNA) -> DealDNA: ...
```

Fill three things on `d`, then return `d`:

**A. Five feeds** → `d.cross_function_actions` (each item is a `CrossFunctionAction` with
`audience, insight, evidence_refs, recommended_action, owner_suggestion, recurrence, review_status`).
Map drivers to audiences (a driver can feed more than one):

| Feed | Driven by these driver categories |
|---|---|
| `enablement` | `demo`, `trust`, `authority` (rep skill/stage gaps) |
| `product` | `product`, `integration`, `demo` (capability/roadmap) |
| `pricing` | `pricing`, `roi` (packaging / value / TCO) |
| `product_marketing` | `roi`, `risk`, `competitor` (messaging / hesitations) |
| `implementations` | `implementation`, `risk` (post-sale expectations) |

Each action must set `evidence_refs` to the supporting driver quotes/timestamps — **no action without
evidence**. Set `review_status = Needs Review`. Never recommend a price change as a decision — phrase it
as a review item.

**B. Seller coaching card** → `d.seller_coaching` (`SellerCoaching`): situation, `stress_next`,
`verify_before`, `avoid`, `biggest_unanswered_question` (pull from `d.unknowns`), 3 `buyer_questions`,
`proof_to_show`. No personality judgments; if evidence is missing say so.

**C. Implementation handoff** → `d.implementation_handoff` (`ImplementationHandoff`). Set
`applicable = (d.outcome == Outcome.WON)`. For Won deals extract expected value + commitments + risks
from the drivers, classifying each `HandoffItem.kind` as requested / promised / inferred_expectation /
dependency / unresolved / out_of_scope / not_observed. Separate buyer expectation from seller promise.

**Build two paths** (mirror `evidence.py`):
- Offline: deterministic mapping from `d.drivers` (works with no key — keeps tests + demo reproducible).
- LLM: `from . import llm; llm.structured_json(system, user, SomeModel)` when `not llm.is_offline()`,
  falling back to the offline result on any error.

---

## 4) Deliverable 2 — `render.py` (the genome)

```python
def render_briefing(d: DealDNA) -> str: ...   # returns a self-contained HTML string
```

Render the deal as a **genome strand**: one marker per driver, positioned by timestamp, **colored by
direction** (win = success green, risk = error red, neutral = navy) and shaped/iconed by category.
Each marker is **click-to-evidence** (shows quote + speaker + timestamp + source). Below the strand,
render: outcome + source, the five feeds, the seller card, the handoff, and the `unknowns`.
Keep **evidence / interpretation / confidence / review-state visually distinct** (never color alone —
pair with text/icon). Use `jinja2` (already a dependency). Write a copy to `outputs/<cycle_id>.html`.

---

## 5) Deliverable 3 — `app/` (review web app)

Use **Streamlit** (fastest): add `streamlit` to `requirements.txt`, `app/streamlit_app.py`.

Flow:
1. Pick a cycle → load its `DealDNA` (call `synthesize_cycle` then `enrich_crossfunctional`, or load
   `outputs/<cycle>.json`).
2. Show the genome (from `render.py`) + the five feeds + seller card + handoff.
3. **Rep review:** for each driver, buttons **Confirm / Add context / Challenge** → append a
   `ReviewCorrection(actor="rep", action=..., field=..., note=...)` to `d.review.corrections`; set
   `d.review.status = "Rep Reviewed"`, `d.review.rep = <name>`.
4. **Manager review:** **Validate** → `d.review.status = "Manager Validated"`, `d.review.manager=<name>`,
   `d.review.reviewed_at = now`.
5. Save to `outputs/reviewed/<cycle>.json`. Show the audit trail.

**Guardrail:** the app must never send email / write to Salesforce / publish. Route any such intent to
`audit.screen_action_request` and display the refusal.

---

## 6) RP Colorway (presentation only)

Anchors: navy `#082649`, ink `#0A1420`, amber `#AE6B29`, link blue `#2E6FB0`. Semantic: success
`#2E8B57`, warning `#E8A21A`, error `#D2402A`. Categorical series:
`#082649,#AE6B29,#E69F00,#009E73,#CC79A7,#56B4E9`. Default font Calibri. Never signal Won/Lost/risk/
review-state by color alone — pair with text or icon. Styling must never change evidence or outcome.

---

## 7) Wire into the CLI (agree with Person A at Sync 3)

`run.py` will call: `synthesize_cycle → enrich_crossfunctional → audit_dealdna → render_briefing → write`.
Keep your functions pure (input `DealDNA`, output `DealDNA`/`str`) so this composition just works.

---

## 8) Tests to add

- `test_crossfunction.py`: every `CrossFunctionAction` has non-empty `evidence_refs`; a Won cycle yields
  `implementation_handoff.applicable == True`; a Lost cycle yields `False`.
- `test_render.py`: `render_briefing(fixture)` returns HTML containing each driver's quote/timestamp.
- Force offline in tests: `os.environ["DEAL_DNA_OFFLINE"] = "1"` at the top (see `tests/test_core.py`).

---

## 9) Suggested order & definition of done

**Order:** (B1) offline `enrich_crossfunctional` from the fixture → (B2) `render_briefing` genome →
(B3) Streamlit app + rep/manager review + audit trail → (B4) RP Colorway polish → (B5) static HTML
fallback + demo path.

**Done when:** from any `DealDNA` JSON the app shows the genome, five feeds, seller card, and (Won-deal)
handoff; a rep→manager review lands in the audit trail; a static HTML fallback exists; your tests pass
offline; and you never write to CRM / contact customers.

**Collision rule:** only `schema.py` is ever co-edited (with Person A). Commit only the files in §2.
Keep your key in a local `.env` (never committed).
