#!/usr/bin/env python3
"""check_namespace — the required CI check over the committed snapshot (K1).

Frozen L0 spec 03 §3.2: loads the committed `manifest.snapshot.json`, calls
THE one oracle `sb.namespace.validate` (the same function boot leg-A and the
`git merge-tree` re-validation call), prints every Collision / CapViolation /
FormatError, exits nonzero if `not report.ok`.

Armed-later note: until the K2 compiler lands and emits a committed snapshot,
a missing snapshot file exits 0 with a warning (the "armed at K2" pattern,
spec 03 §11) — the oracle itself is fully built and fixture-tested at K1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sb.namespace import validate  # noqa: E402

DEFAULT_SNAPSHOT = "manifest.snapshot.json"


def main(argv: list[str]) -> int:
    snapshot_path = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_SNAPSHOT)
    if not snapshot_path.exists():
        print(f"check_namespace: {snapshot_path} absent — dormant until the K2 "
              "compiler emits the committed snapshot (spec 03 §11).")
        return 0
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    report = validate(snapshot)
    for c in report.collisions:
        scope = ""
        if c.scope is not None:
            scope = f" [{c.scope.surface.value}/{c.scope.parent_group or ''}]"
        detail = f" ({c.detail})" if c.detail else ""
        print(f"COLLISION {c.kind.value}:{c.value}{scope}{detail} — "
              f"{c.claimant_a} vs {c.claimant_b}")
    for v in report.cap_violations:
        print(f"CAP_VIOLATION {v.cap} at {v.locus or '<global>'}: "
              f"{v.count} > {v.limit} ({', '.join(v.members[:10])}...)")
    for f in report.format_errors:
        print(f"FORMAT_ERROR {f.kind.value}:{f.value} — {f.detail}")
    if not report.ok:
        total = len(report.collisions) + len(report.cap_violations) + len(report.format_errors)
        print(f"check_namespace: {total} violation(s)", file=sys.stderr)
        return 1
    print("check_namespace: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
