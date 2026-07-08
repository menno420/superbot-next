#!/usr/bin/env python3
"""check_slash_cap — the Q-0237(e) 100/25/1-nest slash budget as a CI gate
(S15, frozen L0 spec 14 §2.A companion; the budget is already baked into
K1's validate — this asserts it over the registered GLOBAL slash tree so
`survivability set ⊆ under-cap slash set` composes: the essential surface
both fits the cap and survives denial).

Exit 0 = clean.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sb.spec.governance import slash_cap_violations  # noqa: E402


def _all_commands():
    import sb.manifest as manifest_pkg
    commands = []
    n = 0
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        manifests = [getattr(module, "MANIFEST", None)]
        manifests.extend(getattr(module, "MANIFESTS", ()))
        for manifest in manifests:
            if manifest is None:
                continue
            n += 1
            commands.extend(tuple(getattr(manifest, "commands", ()) or ()))
    return commands, n


def main() -> int:
    commands, n = _all_commands()
    problems = slash_cap_violations(commands)
    if problems:
        print("check_slash_cap: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"check_slash_cap: OK ({n} manifest(s), {len(commands)} command(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
