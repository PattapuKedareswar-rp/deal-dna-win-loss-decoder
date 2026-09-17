"""Deal DNA genome renderer.

`render_briefing(d)` returns a self-contained HTML string: the deal as a **genome strand**
(one marker per driver, positioned by timestamp, colored by direction and iconed by
category, click-to-evidence), followed by the outcome, the five cross-functional feeds, the
seller coaching card, the implementation handoff, and the unknowns.

Accessibility / governance: nothing is signaled by color alone — every marker and status
pairs color with a text label and an icon. Styling never changes evidence or outcome.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, select_autoescape

from . import config
from .schema import DealDNA, Direction

# RP Colorway (presentation only)
_DIRECTION = {
    Direction.POSITIVE: ("#2E8B57", "▲", "WIN"),
    Direction.NEGATIVE: ("#D2402A", "▼", "RISK"),
    Direction.NEUTRAL: ("#1A1A1A", "●", "NEUTRAL"),
    Direction.MIXED: ("#E8A21A", "◆", "MIXED"),
}
_CATEGORY_ICON = {
    "need": "◇", "pricing": "$", "demo": "▶", "roi": "%", "competitor": "⚔",
    "integration": "⛓", "trust": "✓", "timing": "⏱", "authority": "★",
    "risk": "!", "implementation": "⚙", "product": "▣",
}


def _seconds(ts: str) -> int:
    parts = [p for p in ts.strip().split(":") if p != ""]
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    while len(nums) < 3:
        nums.insert(0, 0)
    h, m, s = nums[-3], nums[-2], nums[-1]
    return h * 3600 + m * 60 + s


def _markers(d: DealDNA) -> list[dict]:
    secs = [_seconds(drv.timestamp) for drv in d.drivers]
    span = max(secs) if secs else 0
    out = []
    for i, drv in enumerate(d.drivers):
        color, icon, dlabel = _DIRECTION.get(drv.direction, _DIRECTION[Direction.NEUTRAL])
        left = 6 + (88 * (secs[i] / span) if span else (88 * i / max(len(d.drivers) - 1, 1)))
        out.append({
            "idx": i, "left": round(left, 2), "color": color, "dir_icon": icon,
            "dir_label": dlabel, "cat_icon": _CATEGORY_ICON.get(drv.category.value, "•"),
            "category": drv.category.value, "summary": drv.summary, "quote": drv.quote,
            "speaker": drv.speaker, "timestamp": drv.timestamp, "source": drv.source,
            "confidence": drv.confidence, "label": drv.label.value,
        })
    return out


_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deal DNA — {{ d.cycle_id }} {{ d.account }}</title>
<style>
 :root{--navy:#E8730C;--ink:#0A1420;--amber:#AE6B29;--link:#2E6FB0;
  --success:#2E8B57;--warning:#E8A21A;--error:#D2402A;}
 body{font-family:Calibri,'Segoe UI',sans-serif;color:var(--ink);margin:0;background:#fff;}
 header{background:var(--navy);color:#fff;padding:18px 24px;}
 header h1{margin:0;font-size:20px;} header .note{opacity:.8;font-size:12px;margin-top:4px;}
 main{padding:20px 24px;max-width:1000px;margin:0 auto;}
 .tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:bold;
  border:2px solid var(--navy);}
 .outcome{font-size:15px;margin:8px 0 20px;}
 .strand-wrap{position:relative;height:96px;margin:28px 0 8px;}
 .strand{position:absolute;top:46px;left:0;right:0;height:6px;border-radius:3px;
  background:linear-gradient(90deg,#d7dee6,#b9c4d0);}
 .marker{position:absolute;top:30px;transform:translateX(-50%);width:34px;text-align:center;
  cursor:pointer;background:none;border:none;font:inherit;}
 .dot{display:block;width:26px;height:26px;line-height:26px;margin:0 auto;border-radius:50%;
  color:#fff;font-weight:bold;font-size:14px;border:2px solid #fff;box-shadow:0 0 0 2px #0003;}
 .marker small{display:block;font-size:10px;color:var(--ink);margin-top:2px;}
 .axis{display:flex;justify-content:space-between;font-size:11px;color:#5a6572;margin-top:6px;}
 .legend{font-size:12px;margin:6px 0 18px;color:#3a4552;}
 .legend b{border-bottom:2px solid;}
 .card{border:1px solid #d7dee6;border-left:5px solid var(--navy);border-radius:6px;
  padding:12px 14px;margin:10px 0;}
 .card.win{border-left-color:var(--success);} .card.risk{border-left-color:var(--error);}
 .card.neutral{border-left-color:#1A1A1A;} .card.mixed{border-left-color:var(--warning);}
 .card:target{box-shadow:0 0 0 3px var(--amber);}
 .meta{font-size:12px;color:#5a6572;} blockquote{margin:6px 0;padding-left:10px;
  border-left:3px solid var(--amber);font-style:italic;}
 h2{color:var(--navy);border-bottom:2px solid #e3e8ee;padding-bottom:4px;margin-top:28px;}
 h3{color:var(--navy);margin:14px 0 4px;font-size:15px;}
 .pill{font-size:11px;font-weight:bold;padding:1px 8px;border-radius:10px;border:1px solid;}
 .review{color:var(--amber);border-color:var(--amber);}
 ul{margin:6px 0 6px 18px;padding:0;} li{margin:2px 0;}
 .refs{font-size:11px;color:#5a6572;} .foot{font-size:11px;color:#7a8592;margin-top:24px;}
</style></head><body>
<header>
 <h1>Deal DNA Genome — {{ d.account }} <span class="tag">{{ d.outcome.value }}</span></h1>
 <div class="note">{{ d.cycle_id }} · opp {{ d.opportunity_id }} · {{ d.call_count }} call(s)
  · {{ d.transcript_status.value }} · {{ d.data_note }}</div>
</header>
<main>
 <div class="outcome"><b>Outcome:</b> {{ d.outcome.value }}
  <span class="meta">(source: {{ d.outcome_source }})</span></div>

 <h2>Genome strand</h2>
 <div class="strand-wrap">
  <div class="strand"></div>
  {% for m in markers %}
  <a class="marker" style="left:{{ m.left }}%" href="#ev-{{ m.idx }}" title="{{ m.category }} · {{ m.dir_label }} · {{ m.timestamp }}">
   <span class="dot" style="background:{{ m.color }}">{{ m.cat_icon }}</span>
   <small>{{ m.dir_icon }} {{ m.timestamp }}</small>
  </a>
  {% endfor %}
 </div>
 <div class="axis"><span>00:00</span><span>call timeline →</span></div>
 <div class="legend">
  Direction (color + icon + text): <b style="border-color:#2E8B57;color:#2E8B57">▲ WIN</b>
  · <b style="border-color:#D2402A;color:#D2402A">▼ RISK</b>
  · <b style="border-color:#1A1A1A;color:#1A1A1A">● NEUTRAL</b>
  · <b style="border-color:#E8A21A;color:#E8A21A">◆ MIXED</b>
 </div>

 <h2>Evidence ({{ markers|length }} drivers)</h2>
 {% for m in markers %}
 <div class="card {{ m.dir_label|lower if m.dir_label != 'NEUTRAL' else 'neutral' }}" id="ev-{{ m.idx }}">
  <div><b>{{ m.cat_icon }} {{ m.category }}</b> · {{ m.dir_icon }} {{ m.dir_label }}
   · <span class="pill review">{{ m.label }}</span>
   · <span class="meta">confidence: {{ m.confidence }}</span></div>
  <div>{{ m.summary }}</div>
  <blockquote>“{{ m.quote }}”</blockquote>
  <div class="meta">— {{ m.speaker }} · {{ m.timestamp }} · {{ m.source }}</div>
 </div>
 {% endfor %}

 <h2>Cross-functional feeds</h2>
 {% set feeds = d.cross_function_actions %}
 {% for name in ["enablement","product","pricing","product_marketing","implementations"] %}
  {% set actions = feeds[name] %}
  {% if actions %}<h3>{{ name.replace('_',' ')|title }}</h3>
   {% for a in actions %}
   <div class="card">
    <div>{{ a.insight }} <span class="pill review">{{ a.review_status.value }}</span></div>
    <div class="meta">Recommended: {{ a.recommended_action }}</div>
    <div class="meta">Owner: {{ a.owner_suggestion }} · Recurrence: {{ a.recurrence }}</div>
    <details class="refs"><summary>{{ a.evidence_refs|length }} evidence refs</summary>
     <ul>{% for r in a.evidence_refs %}<li>{{ r }}</li>{% endfor %}</ul></details>
   </div>
   {% endfor %}
  {% endif %}
 {% endfor %}

 {% if d.seller_coaching %}{% set c = d.seller_coaching %}
 <h2>Seller coaching card <span class="pill review">{{ c.review_status.value }}</span></h2>
 <div class="card">
  <div>{{ c.situation }}</div>
  <h3>Stress next</h3><ul>{% for x in c.stress_next %}<li>{{ x }}</li>{% endfor %}</ul>
  <h3>Verify before</h3><ul>{% for x in c.verify_before %}<li>{{ x }}</li>{% endfor %}</ul>
  <h3>Avoid</h3><ul>{% for x in c.avoid %}<li>{{ x }}</li>{% endfor %}</ul>
  <h3>Biggest unanswered question</h3><div>{{ c.biggest_unanswered_question }}</div>
  <h3>Likely buyer questions</h3><ul>{% for q in c.buyer_questions %}<li>{{ q }}</li>{% endfor %}</ul>
  <h3>Proof to show</h3><div>{{ c.proof_to_show }}</div>
 </div>
 {% endif %}

 {% if d.implementation_handoff %}{% set h = d.implementation_handoff %}
 <h2>Implementation handoff
  <span class="pill review">{{ 'applicable' if h.applicable else 'not applicable (deal not Won)' }}</span></h2>
 {% if h.applicable %}
 <div class="card">
  {% if h.expected_value %}<h3>Expected value</h3>
   <ul>{% for v in h.expected_value %}<li>{{ v }}</li>{% endfor %}</ul>{% endif %}
  <h3>Items</h3>
  {% for it in h.items %}
  <div class="meta">· <b>[{{ it.kind }}]</b> {{ it.summary }}
   {% if it.quote %}<blockquote>“{{ it.quote }}”</blockquote>
   <span class="meta">— {{ it.speaker }} · {{ it.timestamp }} · responsible: {{ it.responsible }}</span>{% endif %}
  </div>
  {% endfor %}
  {% if h.risks %}<h3>Risks</h3><ul>{% for r in h.risks %}<li>{{ r }}</li>{% endfor %}</ul>{% endif %}
 </div>
 {% endif %}
 {% endif %}

 <h2>Unknowns</h2>
 {% if d.unknowns %}<ul>{% for u in d.unknowns %}<li>{{ u }}</li>{% endfor %}</ul>
 {% else %}<div class="meta">None recorded.</div>{% endif %}

 <div class="foot">Review status: {{ d.review.status }}
  {% if d.review.rep %}· rep: {{ d.review.rep }}{% endif %}
  {% if d.review.manager %}· manager: {{ d.review.manager }}{% endif %}
  · generated {{ d.generated_at }}</div>
</main></body></html>"""


def render_briefing(d: DealDNA) -> str:
    """Return a self-contained HTML genome briefing and write a copy to outputs/<cycle_id>.html."""
    env = Environment(autoescape=select_autoescape(["html", "xml"]))
    html = env.from_string(_TEMPLATE).render(d=d, markers=_markers(d))
    out = config.OUTPUTS_DIR / f"{d.cycle_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return html
