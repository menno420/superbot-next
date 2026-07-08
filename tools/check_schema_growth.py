#!/usr/bin/env python3
"""check_schema_growth — the A-2 schema-growth ledger gate (K2 CI, canonical plan §11).

Diffs the manifest grammar's registered field set (sb.spec.roles —
`snapshot_field_roles()` after importing the sb.spec grammar modules) against
`docs/planning/schema-growth-ledger.yml`:

  - a registered grammar field neither in `baseline` nor in `entries` => red
    (a field was added without minting its same-PR ledger entry);
  - an `entries` row with fewer than 2 `consumers` => red (the Q-0219
    second-consumer rule);
  - a ledger row naming a field that is NOT registered => red (stale ledger).

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LEDGER = REPO_ROOT / "docs" / "planning" / "schema-growth-ledger.yml"


def _registered_fields() -> set[str]:
    """Import every sb.spec module (registration side effects), read the map."""
    import sb.spec as spec_pkg
    for info in pkgutil.iter_modules(spec_pkg.__path__):
        importlib.import_module(f"sb.spec.{info.name}")
    from sb.spec.roles import snapshot_field_roles
    return set(snapshot_field_roles())


def check() -> list[str]:
    import yaml
    doc = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
    baseline = set(doc.get("baseline") or [])
    entries: dict = doc.get("entries") or {}
    registered = _registered_fields()

    problems: list[str] = []
    for field in sorted(registered - baseline - set(entries)):
        problems.append(
            f"{field}: registered grammar field with no schema-growth ledger entry "
            "(mint it in the same PR: field + >=2 consuming manifest paths + "
            "the rejected tier-3 alternative)")
    for field, row in sorted(entries.items()):
        consumers = (row or {}).get("consumers") or []
        if len(consumers) < 2:
            problems.append(f"{field}: ledger entry has {len(consumers)} consumer(s) "
                            "(the Q-0219 second-consumer rule requires >=2)")
        if field not in registered:
            problems.append(f"{field}: ledger entry for an unregistered field (stale ledger)")
    for field in sorted(baseline - registered):
        problems.append(f"{field}: baseline names an unregistered field (stale baseline)")
    return problems


def main() -> int:
    problems = check()
    for p in problems:
        print(p)
    if problems:
        print(f"check_schema_growth: {len(problems)} violation(s)", file=sys.stderr)
        return 1
    print("check_schema_growth: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
