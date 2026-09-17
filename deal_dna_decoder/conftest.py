"""Test bootstrap: ensure `src/` is importable and synthetic data exists."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Generate synthetic data once if it is missing.
if not (ROOT / "data" / "transcripts").exists():
    subprocess.run([sys.executable, str(ROOT / "data" / "generate_data.py")], check=True)
