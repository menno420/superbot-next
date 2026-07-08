"""Test bootstrap: put the repo root (where ``sb/`` lives) on sys.path."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
