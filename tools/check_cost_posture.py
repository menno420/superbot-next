#!/usr/bin/env python3
"""check_cost_posture — the class-11 declaration-presence gate (S11, frozen
L0 spec 10 §2.A, Phase 1).

Walks every command facet of every compiled manifest (duck-typed on
`effect` / `cost_posture` / `quota_ref`): an `effect="external"` ref with
`cost_posture=FREE` is red; a quota posture with no `quota_ref` is red; the
only valid posture with no counter is FAIL_CLOSED (a paid feature with no
counter is OFF, never unbounded — the L-16 media default-OFF rule).

Phase 2 (live-binding: quota_ref resolves to a REGISTERED counter) sequences
after the T2-15 spend-counter build. The cardinality leg is already
tools/check_metric_cardinality.py.

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sb.spec.cost import check_command_cost_posture  # noqa: E402


def _manifests() -> list[object]:
    import sb.manifest as manifest_pkg
    manifests = []
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        m = getattr(module, "MANIFEST", None)
        if m is not None:
            manifests.append(m)
    return manifests


def check(manifests: list[object] | None = None) -> list[str]:
    if manifests is None:
        manifests = _manifests()
    problems: list[str] = []
    for manifest in manifests:
        for command in getattr(manifest, "commands", ()) or ():
            for p in check_command_cost_posture(command):
                problems.append(f"{getattr(manifest, 'key', '?')}: {p}")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_cost_posture: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("check_cost_posture: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
