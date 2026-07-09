#!/usr/bin/env python3
"""check_compat_frozen — design-spec §6 gate 6.

Diffs the PINNED compat artifacts against the manifest export (the
committed ``manifest.snapshot.json`` + the frozen AI task-id literals):

  - subsystem keys;
  - command names / aliases / groups (per subsystem);
  - event literals + their payload field sets (the audit-payload freeze);
  - the legacy custom_id list (every ``custom_id_override`` pin + every
    G-10 ``modal_id`` custom-id root);
  - the frozen ``AITask`` value strings (``LEGACY_TASK_IDS``).

The pin lives at ``compat/compat-frozen.json``. ANY drift is red until the
pin is regenerated (``--write``) in the same PR — and the pin file is
CODEOWNERS-routed, so amending the §5.3 contract structurally carries the
owner-sign-off requirement (the ruleset makes this a required check; this
tool only reports).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SNAPSHOT = REPO_ROOT / "manifest.snapshot.json"
PIN = REPO_ROOT / "compat" / "compat-frozen.json"


def _walk(node: Any, key: str, out: list[str]) -> None:
    if isinstance(node, dict):
        value = node.get(key)
        if isinstance(value, str) and value:
            out.append(value)
        for child in node.values():
            _walk(child, key, out)
    elif isinstance(node, list):
        for child in node:
            _walk(child, key, out)


def derive() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT.read_text())
    subsystems = snapshot.get("subsystems") or {}

    commands: dict[str, list[dict[str, Any]]] = {}
    events: dict[str, list[str]] = {}
    for key in sorted(subsystems):
        body = subsystems[key]
        rows = []
        for cmd in (body.get("commands") or []):
            if not isinstance(cmd, dict):
                continue
            rows.append({
                "name": str(cmd.get("name", "")),
                "aliases": sorted(str(a) for a in (cmd.get("aliases") or [])),
                "group": str(cmd.get("group", "") or ""),
            })
        if rows:
            commands[key] = sorted(rows, key=lambda r: r["name"])
        for event in (body.get("events") or []):
            if not isinstance(event, dict):
                continue
            name = str(event.get("name", ""))
            if not name:
                continue
            fields = [str(f.get("name", "")) for f in
                      (event.get("payload_schema") or []) if isinstance(f, dict)]
            events[name] = sorted(fields)

    custom_ids: list[str] = []
    _walk(subsystems, "custom_id_override", custom_ids)
    _walk(subsystems, "modal_id", custom_ids)

    try:
        from sb.kernel.ai.tasks import LEGACY_TASK_IDS
        task_ids = sorted(LEGACY_TASK_IDS)
    except Exception:  # noqa: BLE001 — guarded import (container discipline)
        task_ids = []

    return {
        "schema_version": 1,
        "subsystem_keys": sorted(subsystems),
        "commands": commands,
        "event_payloads": dict(sorted(events.items())),
        "legacy_custom_ids": sorted(set(custom_ids)),
        "legacy_ai_task_ids": task_ids,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_compat_frozen")
    parser.add_argument("--write", action="store_true",
                        help="(re)generate the pin — owner-reviewed via CODEOWNERS")
    args = parser.parse_args(argv)

    current = derive()
    if args.write:
        PIN.parent.mkdir(parents=True, exist_ok=True)
        PIN.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n")
        print(f"check_compat_frozen: pin written -> {PIN}")
        return 0

    if not PIN.exists():
        print("RED compat/compat-frozen.json missing — run "
              "check_compat_frozen --write and commit the pin")
        return 1
    pinned = json.loads(PIN.read_text())
    if pinned == current:
        print("check_compat_frozen: OK — compat artifacts match the pin")
        return 0
    for section in sorted(set(pinned) | set(current)):
        if pinned.get(section) != current.get(section):
            print(f"RED compat drift in {section!r} — the §5.3 contract "
                  f"changed; amend the pin (--write) in this PR (CODEOWNERS "
                  f"routes it to owner review)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
