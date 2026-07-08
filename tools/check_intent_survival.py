#!/usr/bin/env python3
"""check_intent_survival — the slash-first survivability gate (S15, frozen
L0 spec 14 §2.A; mirrors check_cost_posture / check_metric_cardinality).

Walks every sb.manifest declaration: for each capability whose D-5
`slash_common` (essential) tag is set, asserts >=1 entry-point registration
delivered via INTERACTION_CREATE — a CommandSpec whose K1 Surface == SLASH
(reads the frozen {PREFIX, SLASH} enum, invents no COMPONENT value, RC-11)
or any PanelActionSpec/SelectorSpec (inherently interaction-delivered, so
presence is the survivable signal). An essential capability whose only
registrations are PREFIX CommandSpecs is CI-red: intent denial must never
dark an essential capability.

Every input is already in the manifest — no AST. Exit 0 = clean.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sb.spec.governance import check_manifest_survival  # noqa: E402


def _manifests():
    import sb.manifest as manifest_pkg
    found = []
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        manifest = getattr(module, "MANIFEST", None)
        if manifest is not None:
            found.append(manifest)
        found.extend(getattr(module, "MANIFESTS", ()))
    return found


def check(manifests=None) -> list[str]:
    if manifests is None:
        manifests = _manifests()
    problems: list[str] = []
    for manifest in manifests:
        problems.extend(check_manifest_survival(manifest))
    return problems


def main() -> int:
    manifests = _manifests()
    problems = check(manifests)
    if problems:
        print("check_intent_survival: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"check_intent_survival: OK ({len(manifests)} manifest(s) walked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
