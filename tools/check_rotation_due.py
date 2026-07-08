#!/usr/bin/env python3
"""check_rotation_due — the scheduled cadence DETECTOR's CLI (S13, frozen L0
spec 12 §2.B(1); mirrors the reconciliation-due routine, NOT a repo CI gate).

Joins CREDENTIAL_REGISTRY's static `cadence_days` against the rotation
ledger's `last_rotated_at` and prints what is due. With a live DB
(`DATABASE_URL` + asyncpg + `--arm`) it arms the DURABLE one-shot per due
leaf / prompts per due root via `arm_due_rotations`. Without a DB it reports
the static cadence posture (every cadence row shows as never-rotated).

Exit 0 always in report mode — due-ness is an ops signal, not a build error.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sb.kernel.credentials.cadence import rotation_due  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--ledger", type=Path, default=None,
                        help="offline last-rotated map: JSON {name: iso8601}")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    last_rotated: dict[str, datetime] = {}
    if args.ledger and args.ledger.exists():
        raw = json.loads(args.ledger.read_text())
        last_rotated = {k: datetime.fromisoformat(v) for k, v in raw.items()}

    due = rotation_due(last_rotated, now)
    if args.json:
        print(json.dumps([{
            "name": d.cred.name, "horizon_epoch": d.horizon_epoch,
            "tier": "root" if d.is_root else "leaf",
            "cadence_days": d.cred.cadence_days,
            "revocation_ref": d.cred.revocation_ref.value,
        } for d in due], indent=2))
        return 0
    if not due:
        print("check_rotation_due: nothing due")
        return 0
    print(f"check_rotation_due: {len(due)} rotation(s) due")
    for d in due:
        tier = "ROOT (owner prompt)" if d.is_root else "leaf (auto-armable)"
        print(f"  - {d.cred.name}: {tier}, cadence {d.cred.cadence_days}d, "
              f"horizon {d.horizon_epoch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
