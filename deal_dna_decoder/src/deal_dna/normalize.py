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


# --- WebVTT support (real transcript exports are often .vtt) ---
_VTT_TS = re.compile(r"(\d{2}:\d{2}:\d{2})[.,]\d{3}\s*-->")
_VTT_V = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>)?$", re.I)


def _speaker_role(name: str) -> tuple[str, str]:
    """'Buyer - VP Operations' -> ('Buyer', 'VP Operations'); else ('Speaker', name)."""
    if " - " in name:
        role, sp = name.split(" - ", 1)
        return role.strip(), sp.strip()
    return "Speaker", name.strip()


def _parse_vtt(text: str, source: str) -> list[Turn]:
    turns: list[Turn] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        cur_ts = ""
        content: list[str] = []
        for ln in lines:
            m = _VTT_TS.search(ln)
            if m:
                cur_ts = m.group(1)
                continue
            if ln.strip().upper() == "WEBVTT" or ln.strip().isdigit():
                continue
            content.append(ln.strip())
        for cl in content:
            vm = _VTT_V.match(cl)
            if vm:
                name, txt = vm.group(1), vm.group(2)
            elif ":" in cl:
                name, txt = cl.split(":", 1)
            else:
                name, txt = "Speaker", cl
            role, sp = _speaker_role(name.strip())
            turns.append(Turn(timestamp=cur_ts or "00:00:00", role=role, speaker=sp,
                              text=txt.strip(), source=source))
    return turns


# --- Clari/Gong-style blocks: ">>Speaker  MM:SS" then paragraph text until the next speaker ---
_SPK_RE = re.compile(r"^>>\s*(.+?)\s+(\d{1,2}:\d{2}(?::\d{2})?)\b\s*(.*)$")


def _norm_ts(ts: str) -> str:
    parts = [int(x) for x in ts.split(":")]
    h, m, s = ([0] + parts)[-3:] if len(parts) == 2 else parts
    return f"{h:02d}:{m:02d}:{s:02d}"


def _looks_like_blocks(text: str) -> bool:
    return any(_SPK_RE.match(ln.strip()) for ln in text.splitlines()[:120])


def _parse_speaker_blocks(text: str, source: str) -> list[Turn]:
    turns: list[Turn] = []
    speaker: str | None = None
    ts = "00:00:00"
    buf: list[str] = []

    def flush() -> None:
        if speaker is not None:
            txt = " ".join(x.strip() for x in buf if x.strip()).strip()
            if txt:
                turns.append(Turn(timestamp=ts, role="Speaker", speaker=speaker,
                                  text=txt, source=source))

    for line in text.splitlines():
        m = _SPK_RE.match(line.strip())
        if m:
            flush()
            speaker, ts = m.group(1).strip(), _norm_ts(m.group(2))
            buf = [m.group(3)] if m.group(3).strip() else []
        else:
            buf.append(line)
    flush()
    return turns


def load_call(path: Path) -> Call:
    meta_path = path.parent / (path.stem + ".metadata.json")
    metadata = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.exists() else {}
    source = _rel(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".vtt":
        turns = _parse_vtt(text, source)
    elif _looks_like_blocks(text):
        turns = _parse_speaker_blocks(text, source)
    else:
        turns = [t for raw in text.splitlines() if raw.strip()
                 and (t := parse_line(raw, source)) is not None]
    return Call(
        cycle_id=metadata.get("cycle_id", path.parent.name),
        call_id=metadata.get("call_id", path.stem),
        metadata=metadata,
        turns=turns,
    )


def load_cycle(cycle_id: str) -> Cycle:
    cdir = config.TRANSCRIPTS_DIR / cycle_id
    if not cdir.exists():
        raise FileNotFoundError(f"No transcripts for cycle '{cycle_id}' at {cdir}")
    files = sorted(p for p in cdir.iterdir() if p.suffix.lower() in (".txt", ".vtt"))
    return Cycle(cycle_id=cycle_id, calls=[load_call(p) for p in files])


def list_cycles() -> list[str]:
    if not config.TRANSCRIPTS_DIR.exists():
        return []
    return sorted(p.name for p in config.TRANSCRIPTS_DIR.iterdir() if p.is_dir())
