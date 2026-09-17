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
import shutil
from pathlib import Path

from . import config

APPROVED_DIR = config.DATA_DIR / "approved_exports"
APPROVED_TRANSCRIPTS = APPROVED_DIR / "transcripts"
APPROVED_SALESFORCE = APPROVED_DIR / "salesforce" / "opportunities.csv"


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


def ingest_approved() -> dict:
    """Copy an approved export into the working data layout and rebuild the manifest."""
    if not _has_approved():
        raise FileNotFoundError(
            f"No approved export found. Drop approved transcripts under {APPROVED_TRANSCRIPTS} "
            f"and a Salesforce CSV at {APPROVED_SALESFORCE}, then run --ingest.")

    if config.TRANSCRIPTS_DIR.exists():
        shutil.rmtree(config.TRANSCRIPTS_DIR)
    shutil.copytree(APPROVED_TRANSCRIPTS, config.TRANSCRIPTS_DIR)

    config.SALESFORCE_DIR.mkdir(parents=True, exist_ok=True)
    if APPROVED_SALESFORCE.exists():
        shutil.copy2(APPROVED_SALESFORCE, config.SALESFORCE_DIR / "opportunities.csv")

    rows = _build_manifest(source_system="SharePoint (approved export)")
    return {"mode": "approved-export", "cycles": len({r['cycle_id'] for r in rows}),
            "calls": len(rows)}


def _build_manifest(source_system: str) -> list[dict]:
    rows: list[dict] = []
    for cdir in sorted(p for p in config.TRANSCRIPTS_DIR.iterdir() if p.is_dir()):
        for f in sorted(p for p in cdir.iterdir() if p.suffix.lower() in (".txt", ".vtt")):
            meta_path = f.parent / (f.stem + ".metadata.json")
            meta = {}
            if meta_path.exists():
                import json
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
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
