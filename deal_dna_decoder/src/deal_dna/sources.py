"""Data source layer — ingest APPROVED evidence; synthetic is a labeled demo fallback.

Per the hackathon brief, Deal DNA must analyze *approved* sales-call evidence connected to
read-only Salesforce outcomes — not fabricated data. We cannot reach RealPage's live SharePoint
or Salesforce connectors from this environment, so the supported real path is a **drop-in export**:

    data/approved_exports/
      transcripts/<cycle_id>/<call_id>.vtt|.txt   + <call_id>.metadata.json
      salesforce/opportunities.csv

A participant connects the approved SharePoint/Salesforce in their own environment, exports the
approved `.txt`/`.vtt` transcripts + a Salesforce outcome CSV into that folder, and runs `--ingest`.
When no approved export is present, a clearly-labeled SYNTHETIC demo set is used so the app still runs.

Nothing here fetches from a live connector or fabricates 'real' evidence. Provenance is preserved
(source_system, source_url, consent, transcript_status) so every finding remains traceable.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

from . import config

APPROVED_DIR = config.DATA_DIR / "approved_exports"
APPROVED_TRANSCRIPTS = APPROVED_DIR / "transcripts"
APPROVED_SALESFORCE = APPROVED_DIR / "salesforce" / "opportunities.csv"
APPROVED_INDEX = APPROVED_DIR / "index.csv"


def _has_approved() -> bool:
    t = APPROVED_TRANSCRIPTS
    return t.exists() and (any(t.rglob("*.txt")) or any(t.rglob("*.vtt")))


def data_mode() -> str:
    """'approved-export' when a real approved drop-in exists, else 'synthetic-demo'."""
    return "approved-export" if _has_approved() else "synthetic-demo"


def provenance_note() -> str:
    if data_mode() == "approved-export":
        return "APPROVED EXPORT — SharePoint .txt/.vtt transcripts + read-only Salesforce outcomes."
    return "SYNTHETIC demo data (fallback) — NOT real customer data."


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", (s or "").strip()).strip("-") or "cycle"


def _read_index() -> dict[str, dict]:
    """Optional index.csv mapping a transcript file -> cycle/opportunity/outcome, etc."""
    rows: dict[str, dict] = {}
    if not APPROVED_INDEX.exists():
        return rows
    with APPROVED_INDEX.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = (r.get("file") or r.get("call_id") or r.get("filename") or "").strip()
            if key:
                rows[key] = r
                rows[Path(key).stem] = r
    return rows


def ingest_approved() -> dict:
    """Ingest an approved export (nested OR flat folder + optional index.csv) into the working layout.

    Supported drop-in shapes under data/approved_exports/transcripts/:
      - nested:  <cycle_id>/<call_id>.txt|.vtt  (+ optional <call_id>.metadata.json)
      - flat:    <anything>.txt|.vtt            (each file = one cycle; map via index.csv if present)
    Salesforce outcomes come from salesforce/opportunities.csv if provided, else are derived from the
    index/metadata (outcome defaults to 'Needs Review' when unknown — never guessed).
    """
    if not _has_approved():
        raise FileNotFoundError(
            f"No approved export found. Drop approved .txt/.vtt transcripts under "
            f"{APPROVED_TRANSCRIPTS} (flat or per-cycle), optionally add {APPROVED_INDEX} and "
            f"{APPROVED_SALESFORCE}, then run --ingest.")

    index = _read_index()
    if config.TRANSCRIPTS_DIR.exists():
        shutil.rmtree(config.TRANSCRIPTS_DIR)
    config.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in APPROVED_TRANSCRIPTS.rglob("*")
                   if p.suffix.lower() in (".txt", ".vtt"))
    cycle_meta: dict[str, dict] = {}
    for p in files:
        row = index.get(p.name, index.get(p.stem, {}))
        nested = p.parent != APPROVED_TRANSCRIPTS
        cycle_id = _slug(p.parent.name if nested else (row.get("cycle_id") or p.stem))
        call_id = _slug(p.stem)
        dest = config.TRANSCRIPTS_DIR / cycle_id
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest / (call_id + p.suffix.lower()))

        sib = p.parent / (p.stem + ".metadata.json")
        if sib.exists():
            meta = json.loads(sib.read_text(encoding="utf-8-sig"))
        else:
            meta = {
                "cycle_id": cycle_id, "call_id": call_id,
                "opportunity_id": row.get("opportunity_id", ""),
                "account": row.get("account", cycle_id),
                "call_date": row.get("call_date", ""),
                "source_system": "SharePoint (approved export)",
                "source_url": row.get("source_url", ""),
                "product": row.get("product", row.get("product_family", "")),
                "stage": row.get("stage", ""),
                "consent": row.get("consent", "approved"),
                "transcript_status": row.get("transcript_status", "Full transcript available"),
                "outcome": row.get("outcome", "Needs Review"),  # never guessed
            }
        (dest / (call_id + ".metadata.json")).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        cycle_meta.setdefault(cycle_id, meta)

    config.SALESFORCE_DIR.mkdir(parents=True, exist_ok=True)
    if APPROVED_SALESFORCE.exists():
        shutil.copy2(APPROVED_SALESFORCE, config.SALESFORCE_DIR / "opportunities.csv")
    else:
        _write_salesforce_from_meta(cycle_meta)

    rows = _build_manifest(source_system="SharePoint (approved export)")
    return {"mode": "approved-export", "cycles": len({r['cycle_id'] for r in rows}),
            "calls": len(rows)}


def _write_salesforce_from_meta(cycle_meta: dict[str, dict]) -> None:
    """Build a minimal read-only Salesforce outcome map from ingested metadata."""
    with (config.SALESFORCE_DIR / "opportunities.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["opportunity_id", "account", "product_family", "stage", "IsWon",
                    "outcome", "owner", "close_date", "sale_type"])
        for cycle_id, m in cycle_meta.items():
            outcome = m.get("outcome", "Needs Review")
            w.writerow([m.get("opportunity_id", cycle_id), m.get("account", cycle_id),
                        m.get("product", ""), m.get("stage", ""),
                        "true" if outcome == "Won" else "false", outcome,
                        m.get("owner", ""), m.get("call_date", ""), "New"])


def _build_manifest(source_system: str) -> list[dict]:
    rows: list[dict] = []
    for cdir in sorted(p for p in config.TRANSCRIPTS_DIR.iterdir() if p.is_dir()):
        for f in sorted(p for p in cdir.iterdir() if p.suffix.lower() in (".txt", ".vtt")):
            meta_path = f.parent / (f.stem + ".metadata.json")
            meta = {}
            if meta_path.exists():
                import json
                meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            rows.append({
                "cycle_id": cdir.name, "call_id": f.stem,
                "source": str(f.relative_to(config.DATA_DIR.parent)).replace("\\", "/"),
                "source_system": meta.get("source_system", source_system),
                "source_url": meta.get("source_url", ""),
                "outcome": meta.get("outcome", ""),
                "completeness": meta.get("transcript_status", "Full transcript available"),
                "consent": meta.get("consent", "approved"),
            })
    (config.DATA_DIR / "manifest.csv").write_text("", encoding="utf-8")
    with (config.DATA_DIR / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cycle_id", "call_id", "source", "source_system",
                                           "source_url", "outcome", "completeness", "consent"])
        w.writeheader()
        w.writerows(rows)
    return rows
