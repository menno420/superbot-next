#!/usr/bin/env python3
"""check_parity_depth — the A-16 parity-depth floor, INSIDE the golden-parity
named gate (canonical plan §11b A-16; no 7th gate).

DB-free by construction: reads golden JSON (`parity/goldens/`), the committed
`manifest.snapshot.json`, and `parity/parity.yml`. Never boots anything.

Enforced invariants (red = exit 1):

  R1  schema — every subsystem status is `pending | ported`; every
      `parity/goldens/<dir>` has exactly one `subsystems` row and vice versa;
      exemption reasons begin with a declared reason class; ratchet counts are
      non-negative ints.
  R2  floor at the flip — every `ported` subsystem has 100% declared-surface
      touch coverage: each manifest-declared event name / store table /
      setting key is exercised by >=1 golden OR carries an `exempt` row.
  R3  count-ratchet — for every subsystem with a `depth.ratchet` row, the
      covered-surface counts computed from the goldens are >= the committed
      counts (never decrease). Every `ported` subsystem MUST have a row.
  R4  one-way door — this checker cannot see git history, so the ported->
      pending direction is guarded structurally: a subsystem listed in
      `depth.ratchet` may not be `pending` unless it never flipped (ratchet
      rows are minted at the flip, so ratchet-row + pending = a reverted flip).

The KERNEL coverage home (A-16 clause 3, parity.yml `kernel:` section) rides
the same four rules as a pseudo-subsystem (D-0075): `parity/goldens/kernel/`
is ITS golden dir (never a `subsystems` row — kernel is owned by no port
band's manifest), its declared surfaces are the kernel section's own
`events`/`tables` lists (data, not the manifest snapshot — the checker stays
DB-free), exemptions/ratchet live under the ordinary `depth.*` keys with the
`kernel` key, and `kernel.status` is the same one-way pending|ported door.

`--write-ratchet` regenerates `depth.ratchet` rows for ported subsystems
(upward only) — run it in the same PR that adds coverage. The write is a
TEXT SPLICE: only the machine-minted `depth.ratchet` block is rewritten;
every other byte of parity.yml — the comment header, the exemption
prose, key order — is preserved (the original `yaml.safe_dump` full
rewrite destroyed all comments and forced a run-learn-restore-hand-apply
workaround on every flip PR).

Coverage extraction mirrors parity/coverage.py (the imported oracle-side
measurer): events from step["events"][*]["event"]; tables from db_delta keys;
setting keys from key-ish columns of rows added/removed in settings-family
tables.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PARITY_YML = REPO_ROOT / "parity" / "parity.yml"
GOLDENS_ROOT = REPO_ROOT / "parity" / "goldens"
SNAPSHOT = REPO_ROOT / "manifest.snapshot.json"

STATUSES = ("pending", "ported")
SETTINGS_TABLES = ("settings", "guild_settings", "global_settings")
SETTING_KEY_COLUMNS = ("key", "setting_key", "name")


# --------------------------------------------------------------------- loads
def load_parity_yml(path: Path = PARITY_YML) -> dict:
    return yaml.safe_load(path.read_text())


def golden_docs(goldens_root: Path = GOLDENS_ROOT) -> dict[str, list[dict]]:
    """subsystem dir name -> list of parsed golden documents."""
    by_subsystem: dict[str, list[dict]] = {}
    for path in sorted(goldens_root.glob("*/*.json")):
        by_subsystem.setdefault(path.parent.name, []).append(
            json.loads(path.read_text())
        )
    return by_subsystem


# ------------------------------------------------------------------ coverage
def covered_surfaces(docs: list[dict]) -> dict[str, set[str]]:
    """The surfaces a golden corpus touches: events / tables / settings."""
    events: set[str] = set()
    tables: set[str] = set()
    settings: set[str] = set()
    for doc in docs:
        for step in doc.get("steps", []):
            for event in step.get("events", []):
                name = event.get("event")
                if isinstance(name, str):
                    events.add(name)
        for table, delta in (doc.get("db_delta") or {}).items():
            tables.add(table)
            if table not in SETTINGS_TABLES:
                continue
            rows = list(delta.get("added", [])) + list(delta.get("removed", []))
            for row in rows:
                for column in SETTING_KEY_COLUMNS:
                    value = row.get(column)
                    if isinstance(value, str):
                        settings.add(value)
    return {"events": events, "tables": tables, "settings": settings}


def declared_surfaces(snapshot: dict, subsystem: str) -> dict[str, set[str]]:
    """Manifest-declared surfaces for one subsystem, from the snapshot.

    Duck-typed over the serialized manifest (the compiler serializes facet
    dataclasses to plain dicts): events carry `name`, stores `table`,
    settings `key`.
    """
    manifest = (snapshot.get("subsystems") or {}).get(subsystem) or {}
    events = {
        e["name"]
        for e in manifest.get("events") or []
        if isinstance(e, dict) and isinstance(e.get("name"), str)
    }
    tables = {
        s["table"]
        for s in manifest.get("stores") or []
        if isinstance(s, dict) and isinstance(s.get("table"), str)
    }
    settings = {
        s["key"]
        for s in manifest.get("settings") or []
        if isinstance(s, dict) and isinstance(s.get("key"), str)
    }
    return {"events": events, "tables": tables, "settings": settings}


def _exempt_surfaces(depth: dict, subsystem: str) -> set[str]:
    rows = (depth.get("exemptions") or {}).get(subsystem) or []
    return {row["surface"] for row in rows if isinstance(row, dict)}


# -------------------------------------------------------------------- checks
def check(
    parity: dict,
    docs_by_subsystem: dict[str, list[dict]],
    snapshot: dict,
) -> list[str]:
    problems: list[str] = []
    subsystems: dict[str, str] = parity.get("subsystems") or {}
    kernel: dict = parity.get("kernel") or {}
    kernel_status = kernel.get("status")
    depth: dict = parity.get("depth") or {}
    reason_classes: list[str] = depth.get("reason_classes") or []
    ratchet: dict = depth.get("ratchet") or {}

    # R1 — schema + both-direction roster match
    for name, status in subsystems.items():
        if status not in STATUSES:
            problems.append(
                f"R1 {name}: status {status!r} not in {STATUSES}"
            )
    if kernel and kernel_status not in STATUSES:
        problems.append(
            f"R1 kernel: status {kernel_status!r} not in {STATUSES}"
        )
    golden_dirs = set(docs_by_subsystem)
    listed = set(subsystems)
    # parity/goldens/kernel/ is the KERNEL coverage home's dir (D-0075) —
    # legal iff the `kernel:` section exists, never a `subsystems` row.
    if "kernel" in golden_dirs and not kernel:
        problems.append(
            "R1 parity/goldens/kernel/ exists but parity.yml has no "
            "`kernel:` coverage-home section"
        )
    for missing in sorted(golden_dirs - listed - {"kernel"}):
        problems.append(
            f"R1 parity/goldens/{missing}/ exists but has no subsystems row"
        )
    for orphan in sorted(listed - golden_dirs):
        problems.append(
            f"R1 subsystems row {orphan!r} has no parity/goldens/{orphan}/ dir"
        )
    for subsystem, rows in (depth.get("exemptions") or {}).items():
        if subsystem not in listed and subsystem != "kernel":
            problems.append(f"R1 exemption for unknown subsystem {subsystem!r}")
        for row in rows or []:
            if not isinstance(row, dict) or "surface" not in row or "reason" not in row:
                problems.append(
                    f"R1 {subsystem}: exemption rows need surface + reason: {row!r}"
                )
                continue
            reason = str(row["reason"])
            if not any(
                reason == cls or reason.startswith(cls + ":") for cls in reason_classes
            ):
                problems.append(
                    f"R1 {subsystem}: exemption reason {reason!r} does not begin "
                    f"with a declared reason class (never a bare 'flaky')"
                )
    for subsystem, counts in ratchet.items():
        if subsystem not in listed and subsystem != "kernel":
            problems.append(f"R1 ratchet row for unknown subsystem {subsystem!r}")
            continue
        for dim in ("events", "tables", "settings"):
            v = (counts or {}).get(dim)
            if not isinstance(v, int) or v < 0:
                problems.append(
                    f"R1 {subsystem}: ratchet.{dim} must be a non-negative int, got {v!r}"
                )

    # R2 — floor at the flip (declared-surface-or-exempt, 100%)
    for subsystem in sorted(listed):
        if subsystems[subsystem] != "ported":
            continue
        covered = covered_surfaces(docs_by_subsystem.get(subsystem, []))
        declared = declared_surfaces(snapshot, subsystem)
        exempt = _exempt_surfaces(depth, subsystem)
        for dim, prefix in (("events", "event"), ("tables", "table"), ("settings", "setting")):
            for surface in sorted(declared[dim]):
                token = f"{prefix}:{surface}"
                if surface not in covered[dim] and token not in exempt:
                    problems.append(
                        f"R2 {subsystem} is ported but declared {token} is "
                        f"neither exercised by a golden nor exempt"
                    )

    # R2 (kernel) — floor at the kernel flip: the declared surfaces are the
    # kernel section's OWN events/tables lists (A-16 clause 3 — the coverage
    # obligation lives in the kernel home, per the flag-13 disposition
    # ruling), measured over parity/goldens/kernel/ only.
    if kernel_status == "ported":
        covered = covered_surfaces(docs_by_subsystem.get("kernel", []))
        exempt = _exempt_surfaces(depth, "kernel")
        kernel_declared = {
            "events": {e for e in kernel.get("events") or []
                       if isinstance(e, str)},
            "tables": {t for t in kernel.get("tables") or []
                       if isinstance(t, str)},
            "settings": set(),
        }
        for dim, prefix in (("events", "event"), ("tables", "table"),
                            ("settings", "setting")):
            for surface in sorted(kernel_declared[dim]):
                token = f"{prefix}:{surface}"
                if surface not in covered[dim] and token not in exempt:
                    problems.append(
                        f"R2 kernel is ported but declared {token} is "
                        f"neither exercised by a kernel-band golden nor exempt"
                    )

    # R3 — ratchet: counts never decrease; ported rows mandatory
    for subsystem in sorted(listed):
        status = subsystems[subsystem]
        row = ratchet.get(subsystem)
        if status == "ported" and row is None:
            problems.append(
                f"R3 {subsystem} is ported but has no depth.ratchet row "
                f"(mint it in the flip PR: --write-ratchet)"
            )
        if row is None:
            continue
        covered = covered_surfaces(docs_by_subsystem.get(subsystem, []))
        for dim in ("events", "tables", "settings"):
            committed = row.get(dim, 0)
            current = len(covered[dim])
            if isinstance(committed, int) and current < committed:
                problems.append(
                    f"R3 {subsystem}: covered {dim} count fell {committed} -> "
                    f"{current} (the ratchet is one-way)"
                )
        # R4 — a ratchet row on a pending subsystem = a reverted flip
        if status == "pending":
            problems.append(
                f"R4 {subsystem}: has a depth.ratchet row but status is "
                f"pending — ported is a one-way door (design-spec §6 gate 5)"
            )

    # R3/R4 (kernel) — the kernel home's ratchet rides the same rules.
    if kernel:
        row = ratchet.get("kernel")
        if kernel_status == "ported" and row is None:
            problems.append(
                "R3 kernel is ported but has no depth.ratchet row "
                "(mint it in the flip PR: --write-ratchet)"
            )
        if row is not None:
            covered = covered_surfaces(docs_by_subsystem.get("kernel", []))
            for dim in ("events", "tables", "settings"):
                committed = row.get(dim, 0)
                current = len(covered[dim])
                if isinstance(committed, int) and current < committed:
                    problems.append(
                        f"R3 kernel: covered {dim} count fell {committed} -> "
                        f"{current} (the ratchet is one-way)"
                    )
            if kernel_status == "pending":
                problems.append(
                    "R4 kernel: has a depth.ratchet row but status is "
                    "pending — ported is a one-way door (design-spec §6 gate 5)"
                )

    return problems


def write_ratchet(parity: dict, docs_by_subsystem: dict[str, list[dict]]) -> dict:
    """Regenerate ratchet rows (upward only) for ported subsystems —
    including the kernel coverage home when its status is ported."""
    subsystems: dict[str, str] = parity.get("subsystems") or {}
    depth = parity.setdefault("depth", {})
    ratchet = depth.setdefault("ratchet", {}) or {}
    rows = dict(subsystems)
    kernel_status = (parity.get("kernel") or {}).get("status")
    if kernel_status:
        rows["kernel"] = kernel_status
    for subsystem, status in rows.items():
        if status != "ported":
            continue
        covered = covered_surfaces(docs_by_subsystem.get(subsystem, []))
        row = ratchet.get(subsystem) or {}
        ratchet[subsystem] = {
            dim: max(len(covered[dim]), int(row.get(dim, 0)))
            for dim in ("events", "tables", "settings")
        }
    depth["ratchet"] = ratchet
    return parity


def render_ratchet_block(ratchet: dict[str, dict[str, int]]) -> list[str]:
    """The `depth.ratchet` block at the committed parity.yml formatting
    (two-space `ratchet:` key, four-space flow-mapping rows, sorted)."""
    if not ratchet:
        return ["  ratchet: {}"]
    lines = ["  ratchet:"]
    for name in sorted(ratchet):
        row = ratchet[name] or {}
        lines.append(
            f"    {name}: {{events: {int(row.get('events', 0))}, "
            f"tables: {int(row.get('tables', 0))}, "
            f"settings: {int(row.get('settings', 0))}}}"
        )
    return lines


def splice_ratchet_text(text: str, ratchet: dict[str, dict[str, int]]) -> str:
    """Rewrite ONLY the `depth.ratchet` block inside parity.yml's raw text.

    Every byte outside the block — the ~130-line comment header, the
    exemption prose, key order, even the `# ratchet:` schema comment right
    above the block — survives untouched, and the file's own line ending
    (LF or CRLF) is kept. Only the machine-minted block itself is
    regenerated: a comment INTERSTITIAL to the block (one followed by
    more block rows, at any indent) is consumed with it, while a TRAILING
    blank/comment run belongs to whatever follows the block and is
    preserved. Raises SystemExit if the `depth:` section carries no
    `ratchet:` key to splice over.
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    start = None
    in_depth = False
    for i, line in enumerate(lines):
        if re.match(r"^depth:\s*(#.*)?$", line):
            in_depth = True
            continue
        if in_depth and re.match(r"^\S", line):
            in_depth = False
        if in_depth and re.match(r"^  ratchet:(?=\s|$)", line):
            start = i
            break
    if start is None:
        raise SystemExit(
            "splice_ratchet_text: no `ratchet:` key found under `depth:` — "
            "add an empty `ratchet: {}` row to parity.yml first"
        )

    # block extent: every following deeper-indented non-comment line;
    # blank/comment runs are consumed only when a deeper NON-comment line
    # resumes after them (interstitial) — a trailing run is preserved for
    # whatever follows the block
    end = start + 1
    j = start + 1
    while j < len(lines):
        stripped = lines[j].strip()
        if stripped == "" or stripped.startswith("#"):
            k = j + 1
            while k < len(lines) and (
                lines[k].strip() == "" or lines[k].strip().startswith("#")
            ):
                k += 1
            if k < len(lines) and re.match(r"^\s{3,}\S", lines[k]):
                j = k + 1
                end = j
                continue
            break
        if re.match(r"^\s{3,}", lines[j]):
            j += 1
            end = j
            continue
        break

    new_lines = lines[:start] + render_ratchet_block(ratchet) + lines[end:]
    out = newline.join(new_lines)
    if text.endswith(("\n", "\r\n")):
        out += newline
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_parity_depth")
    parser.add_argument(
        "--write-ratchet",
        action="store_true",
        help="regenerate depth.ratchet rows for ported subsystems (upward only)",
    )
    args = parser.parse_args(argv)

    parity = load_parity_yml()
    docs = golden_docs()
    snapshot = json.loads(SNAPSHOT.read_text())

    if args.write_ratchet:
        updated = write_ratchet(parity, docs)
        PARITY_YML.write_text(
            splice_ratchet_text(
                PARITY_YML.read_text(), updated["depth"]["ratchet"],
            )
        )
        print("parity.yml depth.ratchet regenerated in place — only the "
              "machine-minted ratchet block is rewritten; the comment "
              "header and every other byte are preserved")
        return 0

    problems = check(parity, docs, snapshot)
    if problems:
        for p in problems:
            print(f"RED {p}")
        print(f"check_parity_depth: {len(problems)} problem(s)")
        return 1
    ported = [s for s, st in (parity.get("subsystems") or {}).items() if st == "ported"]
    kernel_status = (parity.get("kernel") or {}).get("status", "absent")
    print(
        f"check_parity_depth: OK — {len(parity.get('subsystems') or {})} subsystems "
        f"({len(ported)} ported), kernel {kernel_status}, "
        f"{sum(len(d) for d in docs.values())} goldens"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
