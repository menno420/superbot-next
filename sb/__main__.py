"""``python3 -m sb`` — the live composition root (sb/app/main.py)."""

from __future__ import annotations

import sys

from sb.app.main import cli

if __name__ == "__main__":
    sys.exit(cli())
