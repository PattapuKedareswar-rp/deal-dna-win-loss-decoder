"""Runtime configuration. Key is read from the environment only — never hard-coded."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project paths
PKG_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PKG_DIR.parent.parent          # .../deal_dna_decoder
DATA_DIR = PROJECT_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
SALESFORCE_DIR = DATA_DIR / "salesforce"
REFERENCE_DIR = DATA_DIR / "reference"
GOLD_DIR = DATA_DIR / "gold"
FIXTURES_DIR = DATA_DIR / "fixtures"
OUTPUTS_DIR = PROJECT_DIR / "outputs"

# Model / mode
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
FORCE_OFFLINE = os.getenv("DEAL_DNA_OFFLINE", "0") == "1"

DATA_NOTE = "SYNTHETIC sample data — not real customer data."


def is_offline() -> bool:
    """Offline (deterministic) mode when no key is configured or offline is forced."""
    return FORCE_OFFLINE or not OPENAI_API_KEY
