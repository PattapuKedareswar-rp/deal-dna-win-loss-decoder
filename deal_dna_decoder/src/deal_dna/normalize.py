"""Transcript normalizer.

Parse synthetic speaker-attributed, timestamped `.txt` calls into structured turns,
preserving speaker, role, timestamp, exact wording, and source path. Never invents speakers.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config

# Matches:  [HH:MM:SS] Role - Name: text
_LINE_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+([^-]+?)\s+-\s+([^:]+?):\s+(.*)$")


@dataclass
class Turn:
    timestamp: str
    role: str
    speaker: str
    text: str
    source: str


@dataclass
class Call:
    cycle_id: str
    call_id: str
    metadata: dict
    turns: list[Turn] = field(default_factory=list)


@dataclass
class Cycle:
    cycle_id: str
    calls: list[Call] = field(default_factory=list)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(config.PROJECT_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def parse_line(raw: str, source: str) -> Turn | None:
    m = _LINE_RE.match(raw.strip())
    if not m:
        return None
    ts, role, speaker, text = m.groups()
    return Turn(timestamp=ts, role=role.strip(), speaker=speaker.strip(),
                text=text.strip(), source=source)


def load_call(txt_path: Path) -> Call:
    meta_path = txt_path.parent / (txt_path.stem + ".metadata.json")
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    source = _rel(txt_path)
    turns: list[Turn] = []
    for raw in txt_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        t = parse_line(raw, source)
        if t is not None:
            turns.append(t)
    return Call(
        cycle_id=metadata.get("cycle_id", txt_path.parent.name),
        call_id=metadata.get("call_id", txt_path.stem),
        metadata=metadata,
        turns=turns,
    )


def load_cycle(cycle_id: str) -> Cycle:
    cdir = config.TRANSCRIPTS_DIR / cycle_id
    if not cdir.exists():
        raise FileNotFoundError(f"No transcripts for cycle '{cycle_id}' at {cdir}")
    calls = [load_call(p) for p in sorted(cdir.glob("*.txt"))]
    return Cycle(cycle_id=cycle_id, calls=calls)


def list_cycles() -> list[str]:
    if not config.TRANSCRIPTS_DIR.exists():
        return []
    return sorted(p.name for p in config.TRANSCRIPTS_DIR.iterdir() if p.is_dir())
