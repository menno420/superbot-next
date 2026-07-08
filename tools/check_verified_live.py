#!/usr/bin/env python3
"""check_verified_live — the V-5 registry gate (verification-review §3.3;
A-18 tiering; Q-0244 verification requirement).

Enforced (red = exit 1):
  V1  schema — every record parses against the §3.3 schema; statuses /
      tiers / evidence kinds from the closed vocabularies; record_ids
      unique; every record's subsystem exists on the dashboard.
  V2  the VERIFIED transition is a signed fact — signer + signed_at +
      build_sha + linked evidence, with the tier's evidence rule (Q-0244:
      slash/component = prefix-twin live + pipeline-true replay; prefix =
      lane-A live test; human tier = human-walk/owner-judgment).
  V3  dashboard honesty — a subsystem marked `verified` needs >=1 record
      and ZERO unverified AUTOMATED-tier records. Unverified HUMAN-tier
      rows NEVER red anything (the debt-list model — nothing in the human
      lane blocks CUT-3); they surface via --debt-list.
  V4  roster spine — the dashboard carries every parity.yml subsystem
      (+ `kernel`), both directions: one port dashboard, two lenses.

`--debt-list` prints the CUT-2/CUT-3 coverage-debt publication (exit 0 —
debt is published, never blocking).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PARITY_YML = REPO_ROOT / "parity" / "parity.yml"

DASHBOARD_STATUSES = ("unverified", "verified")


def check() -> list[str]:
    from verification.verified_live import (
        Status,
        Tier,
        load_registry,
        validate_record,
    )

    problems: list[str] = []
    try:
        subsystems, records = load_registry()
    except Exception as exc:  # noqa: BLE001 - a broken registry is one problem
        return [f"V1 registry does not load: {type(exc).__name__}: {exc}"]

    # V1 — schema + uniqueness + dashboard membership
    seen_ids: set[str] = set()
    for record in records:
        if record.record_id in seen_ids:
            problems.append(f"V1 duplicate record_id {record.record_id!r}")
        seen_ids.add(record.record_id)
        if record.subsystem not in subsystems:
            problems.append(
                f"V1 {record.record_id}: subsystem {record.subsystem!r} not on the dashboard"
            )
        problems.extend(f"V2 {p}" for p in validate_record(record))

    for name, status in subsystems.items():
        if status not in DASHBOARD_STATUSES:
            problems.append(f"V1 {name}: dashboard status {status!r} not in {DASHBOARD_STATUSES}")

    # V3 — dashboard honesty (human-tier debt never blocks)
    by_subsystem: dict[str, list] = {}
    for record in records:
        by_subsystem.setdefault(record.subsystem, []).append(record)
    for name, status in subsystems.items():
        if status != "verified":
            continue
        rows = by_subsystem.get(name, [])
        if not rows:
            problems.append(f"V3 {name}: marked verified with zero records")
            continue
        for record in rows:
            if record.tier is Tier.AUTOMATED and record.status is not Status.VERIFIED:
                problems.append(
                    f"V3 {name}: marked verified but automated-tier "
                    f"{record.record_id} is {record.status.value}"
                )

    # V4 — one dashboard spine with parity.yml
    parity = yaml.safe_load(PARITY_YML.read_text())
    parity_roster = set(parity.get("subsystems") or {}) | {"kernel"}
    dashboard = set(subsystems)
    for missing in sorted(parity_roster - dashboard):
        problems.append(f"V4 parity.yml subsystem {missing!r} missing from verified_live.yml")
    for orphan in sorted(dashboard - parity_roster):
        problems.append(f"V4 verified_live.yml subsystem {orphan!r} unknown to parity.yml")

    return problems


def print_debt_list() -> int:
    from verification.verified_live import debt_list, load_registry

    _, records = load_registry()
    debt = debt_list(records)
    print(f"verified_live coverage-debt list ({len(debt)} row(s)) — published "
          f"per A-18(3)/Q-0244, NEVER a CUT-3 blocker:")
    for record in debt:
        print(f"  {record.record_id} [{record.tier.value}] {record.surface_kind.value} "
              f"{record.surface_id} — {record.status.value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_verified_live")
    parser.add_argument("--debt-list", action="store_true",
                        help="print the CUT-2/CUT-3 coverage-debt publication")
    args = parser.parse_args(argv)
    if args.debt_list:
        return print_debt_list()
    problems = check()
    if problems:
        for p in problems:
            print(f"RED {p}")
        print(f"check_verified_live: {len(problems)} problem(s)")
        return 1
    from verification.verified_live import load_registry

    subsystems, records = load_registry()
    verified = sum(1 for s in subsystems.values() if s == "verified")
    print(f"check_verified_live: OK — {len(subsystems)} subsystems "
          f"({verified} verified), {len(records)} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
