#!/usr/bin/env python3
"""check_lockfile_fresh — the deterministic-install gate (S13, frozen L0
spec 12 §2.C; Q-D18). Closes S-1/S-2: merge=deploy installs the exact
reviewed set, and an adopted dep's lock diff IS the reviewable artifact.

Static legs (always, offline):
  (1) requirements.lock exists and EVERY requirement entry is hash-pinned
      (`--hash=sha256:`) and exactly `==`-pinned;
  (2) every requirement named in requirements.txt appears `==`-pinned in the
      lock (a constraint with no resolved entry = a drifted lock).

Regeneration leg (`--regen`, network; the CI job runs it):
  (3) `pip-compile --generate-hashes --strip-extras` from requirements.txt
      reproduces requirements.lock byte-for-byte (modulo the autogen header)
      — a hand-edited or stale lock is CI-red. pip-compile reuses existing
      satisfying pins, so an upstream release alone never reds this.

Exit 0 = clean.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQ = REPO_ROOT / "requirements.txt"
LOCK = REPO_ROOT / "requirements.lock"

_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _norm(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def _lock_entries(text: str) -> dict[str, list[str]]:
    """{normalized name: [hash lines]} for every `pkg==ver` entry."""
    entries: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", stripped)
            current = _norm(m.group(1)) if m else None
            if m:
                entries[current] = []
            continue
        if current and "--hash=sha256:" in stripped:
            entries[current].append(stripped)
    return entries


def _static_check() -> list[str]:
    problems: list[str] = []
    if not LOCK.exists():
        return ["requirements.lock missing (pip-compile --generate-hashes "
                "-o requirements.lock requirements.txt)"]
    lock_text = LOCK.read_text()
    entries = _lock_entries(lock_text)
    # (1) every entry hash-pinned
    for name, hashes in entries.items():
        if not hashes:
            problems.append(f"lock entry {name}: no --hash=sha256 pin")
    # non-== requirement lines in the lock body are drift
    for line in lock_text.splitlines():
        if line.startswith((" ", "\t", "#")) or not line.strip():
            continue
        body = line.split("#", 1)[0].strip().rstrip("\\").strip()
        if body and "==" not in body:
            problems.append(f"lock line not ==-pinned: {body!r}")
    # (2) every requirements.txt constraint resolved in the lock
    for line in REQ.read_text().splitlines():
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        m = _NAME_RE.match(body)
        if m and _norm(m.group(1)) not in entries:
            problems.append(f"requirements.txt {m.group(1)}: no resolved entry "
                            f"in requirements.lock (regenerate the lock)")
    return problems


def _strip_header(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.startswith("#"))


def _regen_check() -> list[str]:
    if shutil.which("pip-compile") is None:
        return ["--regen requested but pip-compile is not installed "
                "(pip install pip-tools)"]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "requirements.lock"
        shutil.copy(LOCK, out)  # seed so pip-compile reuses satisfying pins
        res = subprocess.run(
            ["pip-compile", "--generate-hashes", "--strip-extras", "--quiet",
             "-o", str(out), "requirements.txt"],  # relative: the `via -r`
            capture_output=True, text=True, cwd=REPO_ROOT)  # annotations match
        if res.returncode != 0:
            return [f"pip-compile failed: {res.stderr.strip()[:500]}"]
        if _strip_header(out.read_text()) != _strip_header(LOCK.read_text()):
            return ["requirements.lock is NOT fresh: regenerating from "
                    "requirements.txt yields a diff — run pip-compile "
                    "--generate-hashes -o requirements.lock requirements.txt "
                    "and commit the result"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regen", action="store_true",
                        help="also regenerate and diff (network; the CI leg)")
    args = parser.parse_args()
    problems = _static_check()
    if not problems and args.regen:
        problems = _regen_check()
    if problems:
        print("check_lockfile_fresh: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    entries = _lock_entries(LOCK.read_text())
    hashes = sum(len(v) for v in entries.values())
    print(f"check_lockfile_fresh: OK ({len(entries)} pinned dists, "
          f"{hashes} hashes{', regen-verified' if args.regen else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
