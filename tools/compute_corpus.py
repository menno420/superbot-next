#!/usr/bin/env python3
"""compute_corpus — the one-time Stage-2 corpus-computation procedure (K1).

Frozen L0 spec 03 §3.6, the load-bearing order:

  1. enumerate the nav-node deep-link commands INTO the corpus FIRST
     (Q-0231/Q-0237f hub openers — canonical names + shipped `-menu` hidden
     aliases);
  2. walk the LIVE EXPANDED corpus (every subcommand a distinct node) —
     NEVER the flat `command-surface.json` (the L-14 root: 1 vs 11 shared
     verbs);
  3. compute the shared-verb set (verb -> owning subsystems; shared iff >=2);
  4. apply the cap budget (§3.5): group shared verbs; only if still >100
     top-level, prefix-demote the long tail by the deterministic
     `(usage_weight=0, namespace_id asc)` rule minus `slash_pins.json`;
  5. write the resulting reservations + the per-subsystem naming list.

Input: because this repo never imports the old bot, the expanded corpus is
supplied as JSON (`--corpus`): a list of nodes
  {"name": str, "kind": "prefix"|"slash"|"both", "parent_group": str|null,
   "subsystem": str, "source": str}
produced at Stage-2 by walking shipped `bot.commands` in the superbot repo
(the walker lives with the old bot; this tool owns the ALGORITHM). Nav nodes
ride `--nav-nodes` with the same shape plus optional {"alias_of": str}.

Output: `legacy_reservations.json` reservations + `slash_pins.json` seed +
a per-subsystem naming list (stdout JSON). Run ONCE at Stage-2 (spec 03 §11).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sb.namespace.kinds import CommandScope, NamespaceKind, Surface, namespace_id, normalize  # noqa: E402

CAP_TOP_LEVEL = 100


def _surfaces(kind: str) -> list[Surface]:
    if kind == "both":
        return [Surface.PREFIX, Surface.SLASH]
    return [Surface(kind)]


def compute(corpus: list[dict], nav_nodes: list[dict], pins: set[str]) -> dict:
    # Step 1: nav nodes FIRST (they are real commands outside the harvested 271).
    nodes = list(nav_nodes) + list(corpus)

    # Step 2 is the caller's (the walk produced `corpus` expanded). Step 3:
    verb_owners: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        verb_owners[normalize(node["name"], NamespaceKind.COMMAND)].add(node["subsystem"])
    shared_verbs = {v for v, owners in verb_owners.items() if len(owners) >= 2}

    # Step 4a: group shared verbs — a shared verb becomes `/subsystem verb`.
    assigned: list[dict] = []
    for node in nodes:
        name = normalize(node["name"], NamespaceKind.COMMAND)
        parent = node.get("parent_group")
        if name in shared_verbs and parent is None:
            parent = node["subsystem"]  # grouped form: /area verb (Q-0224)
        for surface in _surfaces(node["kind"]):
            assigned.append({
                "value": name,
                "kind": "command",
                "surface": surface.value,
                "parent_group": parent,
                "subsystem": node["subsystem"],
                "source": node.get("source", "stage-2 walk"),
                "alias_of": node.get("alias_of"),
            })

    # Step 4b: deterministic prefix-demotion (dormant when corpus fits).
    top_level: dict[str, list[dict]] = defaultdict(list)
    for row in assigned:
        if row["surface"] == "slash":
            head = (row["parent_group"] or row["value"]).split(".")[0]
            top_level[head].append(row)
    overflow = len(top_level) - CAP_TOP_LEVEL
    demoted: list[str] = []
    if overflow > 0:
        def sort_key(head: str) -> tuple[int, str]:
            # usage_weight is a manifest [O] field absent at Stage-2 => 0 for all;
            # the order degenerates to namespace_id asc (total, reproducible).
            return (0, namespace_id(head, CommandScope(Surface.SLASH, None)))

        candidates = sorted((h for h in top_level if h not in pins), key=sort_key)
        for head in candidates[:overflow]:
            demoted.append(head)
            for row in top_level[head]:
                row["surface"] = "prefix"

    # Step 5: the reservation rows + naming list.
    naming: dict[str, list[str]] = defaultdict(list)
    for row in assigned:
        qualified = f"{row['parent_group'] + ' ' if row['parent_group'] else ''}{row['value']}"
        entry = f"{row['surface']}:{qualified}"
        if entry not in naming[row["subsystem"]]:
            naming[row["subsystem"]].append(entry)

    return {
        "shared_verbs": sorted(shared_verbs),
        "demoted_to_prefix": demoted,
        "reservations": assigned,
        "naming_list": {k: sorted(v) for k, v in sorted(naming.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, help="expanded-corpus JSON (live walk export)")
    parser.add_argument("--nav-nodes", default=None, help="nav-node deep-link commands JSON")
    parser.add_argument("--slash-pins", default="sb/namespace/slash_pins.json")
    parser.add_argument("--out", default=None, help="write result JSON here (default stdout)")
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    nav = json.loads(Path(args.nav_nodes).read_text(encoding="utf-8")) if args.nav_nodes else []
    pins_doc = json.loads(Path(args.slash_pins).read_text(encoding="utf-8"))
    result = compute(corpus, nav, set(pins_doc.get("pins", [])))
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
