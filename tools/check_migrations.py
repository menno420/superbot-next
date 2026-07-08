#!/usr/bin/env python3
"""check_migrations — numbering + immutability + checksum-manifest gate (K3 CI).

Frozen L0 spec 05 §3.6, the CI twin of the boot-time verify_applied_checksums:

  1. numbering — every migrations/*.sql matches NNNN_<snake_name>.sql, versions
     are unique AND contiguous from 0001 (fresh chain, design-spec §5.2);
  2. immutability — every NNNN_*.sql byte-matches its entry in the committed
     migrations/checksums.json manifest, so a changed applied file is CI-red
     BEFORE it can reach a deploy (today drift would only be caught at boot).
     New files append to the manifest in the same PR (a file missing from the
     manifest, or a manifest entry with no file, is red);
  3. forward-only is enforced structurally by (1)+(2): a version below the
     current max can only be *added* by editing the manifest, which review
     owns (spec 05 §3.6 item 3's "signed rebase" is a PR-review property).

Exit 0 = clean; exit 1 = violations (one per line).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"
MANIFEST = MIGRATIONS_DIR / "checksums.json"

_NAME_RE = re.compile(r"^(\d{4})_([a-z][a-z0-9_]*)\.sql$")


def check(migrations_dir: Path = MIGRATIONS_DIR, manifest_path: Path = MANIFEST) -> list[str]:
    violations: list[str] = []
    if not migrations_dir.is_dir():
        return [f"{migrations_dir}: migrations/ directory not found"]

    files = sorted(p for p in migrations_dir.iterdir() if p.suffix == ".sql")

    # 1. numbering: pattern + unique + contiguous from 0001
    seen: dict[int, str] = {}
    for path in files:
        match = _NAME_RE.match(path.name)
        if match is None:
            violations.append(f"{path.name}: does not match NNNN_<snake_name>.sql")
            continue
        version = int(match.group(1))
        if version in seen:
            violations.append(
                f"{path.name}: duplicate version {version:04d} (also {seen[version]}) "
                "— the second would never apply (forward-only; rename, do not duplicate)")
        seen[version] = path.name
    expected = set(range(1, len(seen) + 1))
    missing = expected - set(seen)
    beyond = set(seen) - expected
    for v in sorted(missing):
        violations.append(f"chain gap: no migration {v:04d} (chain must be contiguous from 0001)")
    for v in sorted(beyond):
        violations.append(f"{seen[v]}: version {v:04d} beyond the contiguous chain")

    # 2. immutability against the committed manifest
    if not manifest_path.exists():
        violations.append(f"{manifest_path.name}: checksum manifest missing")
        return violations
    try:
        manifest: dict[str, str] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, TypeError) as exc:
        violations.append(f"{manifest_path.name}: unparseable ({exc})")
        return violations

    on_disk = {p.name for p in files}
    for path in files:
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        recorded = manifest.get(path.name)
        if recorded is None:
            violations.append(
                f"{path.name}: not in checksums.json — append its entry in the SAME PR")
        elif recorded != digest:
            violations.append(
                f"{path.name}: checksum mismatch (manifest {recorded}, on disk {digest}) "
                "— an applied migration was edited; ship a NEW migration instead")
    for name in sorted(set(manifest) - on_disk):
        violations.append(f"{name}: in checksums.json but absent on disk (squashed/renamed applied file)")
    return violations


def main() -> int:
    violations = check()
    for line in violations:
        print(line)
    if violations:
        print(f"check_migrations: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    n = len(list(MIGRATIONS_DIR.glob("*.sql"))) if MIGRATIONS_DIR.is_dir() else 0
    print(f"check_migrations: clean ({n} migration(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
