#!/usr/bin/env python3
"""permission_census — the CUT-2 Discord-side permission-override census +
rename→preservation partition + carry-verify (S15, frozen L0 spec 14 §2.D).

Guild admins' per-command Server-Settings overrides are a SECOND security
config DB living in Discord — bot-token-READABLE
(`GET /applications/{app}/guilds/{g}/commands/permissions`, one GET per
guild) but bot-token-UN-WRITABLE (the PUT needs an admin OAuth2 Bearer with
`applications.commands.permissions.update`), so there is NO automated
replay. Preservation = id-stability (the SAME application id keeps
un-renamed commands' ids ⇒ Discord keeps their overrides through
re-registration, zero action — PG-5 recommends same-app-id) + an
admin-notice for the RENAMED/DROPPED remainder.

Partition (per censused override, given the enumerable Q-0224 rename map):
  PRESERVED  command un-renamed  -> same id survives; carry-VERIFIED post-swap
  RENAMED    id changes          -> override LOST; admin-notice (only remediation)
  DROPPED    no successor        -> admin-notice

The census SCOPE is every command with an override in any guild — NOT the
25 code-declared default_permissions surfaces (admins can override ANY
command).

Modes (the live GET wiring is CUT-2 ops build — same tier as the importer):
  --census FILE                partition a captured census JSON
  --census FILE --verify FILE  carry-verify: assert every PRESERVED override
                               survived re-registration (FJ §4 #7 copy-
                               fidelity; any loss = cutover failure, exit 1)
Census JSON schema: {guild_id: [{"command_id": str, "command_name": str,
"permissions": [{"id": str, "type": "role|user|channel",
"permission": bool}]}]}. Rename map JSON: {old_name: new_name|null}.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class Disposition(str, Enum):
    PRESERVED = "preserved"
    RENAMED = "renamed"
    DROPPED = "dropped"


@dataclass(frozen=True)
class OverrideRecord:
    guild_id: int
    command_id: str
    command_name: str
    permissions: tuple[dict, ...]
    disposition: Disposition
    successor: str | None = None   # the new name (RENAMED) / same name (PRESERVED)


def partition(census: dict, rename_map: dict[str, str | None],
              *, same_application_id: bool = True) -> list[OverrideRecord]:
    """Bucket every censused override. With a NEW application id (PG-5
    option b) EVERY id changes, so nothing is PRESERVED — the admin-notice
    covers the entire census (why same-app-id is strongly recommended)."""
    records: list[OverrideRecord] = []
    for guild_id, entries in census.items():
        for entry in entries:
            name = entry["command_name"]
            top = name.split()[0] if name else name
            if top in rename_map:
                successor = rename_map[top]
                if successor is None:
                    dispo, succ = Disposition.DROPPED, None
                else:
                    dispo, succ = Disposition.RENAMED, successor
            elif not same_application_id:
                dispo, succ = Disposition.RENAMED, name  # id changes anyway
            else:
                dispo, succ = Disposition.PRESERVED, name
            records.append(OverrideRecord(
                guild_id=int(guild_id), command_id=str(entry["command_id"]),
                command_name=name,
                permissions=tuple(entry.get("permissions", ())),
                disposition=dispo, successor=succ))
    return records


def carry_verify(preserved: list[OverrideRecord], post: dict) -> list[str]:
    """Post-swap read-back (bot-token GET): every PRESERVED override must
    still be present — a copy-FIDELITY check on the un-renamed set. Any
    missing override is a cutover failure (blocking)."""
    problems: list[str] = []
    post_index: dict[tuple[int, str], list] = {}
    for guild_id, entries in post.items():
        for entry in entries:
            post_index[(int(guild_id), entry["command_name"])] = list(
                entry.get("permissions", ()))
    for rec in preserved:
        found = post_index.get((rec.guild_id, rec.command_name))
        if found is None:
            problems.append(f"guild {rec.guild_id} / {rec.command_name}: PRESERVED "
                            f"override VANISHED after re-registration")
            continue
        want = {(p["id"], p["type"], p["permission"]) for p in rec.permissions}
        got = {(p["id"], p["type"], p["permission"]) for p in found}
        if not want <= got:
            problems.append(f"guild {rec.guild_id} / {rec.command_name}: override "
                            f"overlay changed ({len(want - got)} entries lost)")
    return problems


def admin_notice_lines(records: list[OverrideRecord]) -> list[str]:
    """The CUT-3 comms-plan remainder: one per-guild line per RENAMED/
    DROPPED override, with the captured overlay so the admin can reproduce
    it exactly in Server Settings → Integrations (the ONLY remediation —
    the write is admin-only, PG-4)."""
    lines: list[str] = []
    for rec in records:
        if rec.disposition is Disposition.PRESERVED:
            continue
        what = (f"renamed to '{rec.successor}'" if rec.disposition is
                Disposition.RENAMED else "removed")
        overlay = "; ".join(
            f"{p['type']} {p['id']}: {'allow' if p['permission'] else 'deny'}"
            for p in rec.permissions)
        lines.append(f"guild {rec.guild_id}: permission customizations on "
                     f"'{rec.command_name}' were reset ({what}) — re-apply in "
                     f"Server Settings → Integrations: [{overlay}]")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, required=True,
                        help="captured census JSON (bot-token GET sweep, CUT-2)")
    parser.add_argument("--rename-map", type=Path, default=None,
                        help="Q-0224 rename map JSON {old: new|null}")
    parser.add_argument("--verify", type=Path, default=None,
                        help="post-swap census JSON — carry-verify mode")
    parser.add_argument("--new-application-id", action="store_true",
                        help="PG-5 option (b): nothing is PRESERVED")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    census = json.loads(args.census.read_text())
    rename_map = (json.loads(args.rename_map.read_text())
                  if args.rename_map else {})
    records = partition(census, rename_map,
                        same_application_id=not args.new_application_id)
    by = {d: [r for r in records if r.disposition is d] for d in Disposition}

    if args.verify:
        post = json.loads(args.verify.read_text())
        problems = carry_verify(by[Disposition.PRESERVED], post)
        if problems:
            print("permission_census carry-verify: FAILURES (cutover-blocking)")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"permission_census carry-verify: OK "
              f"({len(by[Disposition.PRESERVED])} preserved override(s) intact)")
        return 0

    if args.json:
        print(json.dumps({
            "preserved": len(by[Disposition.PRESERVED]),
            "renamed": len(by[Disposition.RENAMED]),
            "dropped": len(by[Disposition.DROPPED]),
            "admin_notice": admin_notice_lines(records),
        }, indent=2))
        return 0
    print(f"permission_census: {len(records)} override(s) — "
          f"{len(by[Disposition.PRESERVED])} preserved, "
          f"{len(by[Disposition.RENAMED])} renamed, "
          f"{len(by[Disposition.DROPPED])} dropped")
    for line in admin_notice_lines(records):
        print(f"  NOTICE {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
