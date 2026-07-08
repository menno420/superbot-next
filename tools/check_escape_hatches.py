#!/usr/bin/env python3
"""check_escape_hatches — the A-19 escape-hatch ratchet (canonical plan §11).

A named deliverable INSIDE the manifest-validate gate (snapshot-derived
validator family; no 7th gate), required CI from the first kernel PR through
post-cutover, NO EXPIRY. Invariant: every compiled surface unit is tier-1/2
(declarative manifest / registered refs) or a tier-3 registration with a
non-empty `justification`.

Tier-3 units counted from the compiled snapshot:
  - every `{"$ref": "view:..."}` occurrence (a ViewRef IS the §2.9 tier-3
    re-homed-legacy-view escape hatch) — its carrying node must declare a
    non-empty `justification`;
  - every node carrying `tier: 3` or a truthy `escape_hatch` marker.
Also red: `sb/domain/<x>/ui/` modules unreachable from any registered ref.

Ratchet semantics (the proven A-2 ledger pattern): the generated report is
diffed against the committed pinned baseline (per-subsystem tier-3 COUNT +
repo total). Any RISE fails CI unless the same PR updates the baseline with a
ledger entry. Reductions tighten one-way: `--tighten` rewrites the baseline
down. At CUT-3 the baseline stamps as the permanent year-two ceiling.

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BASELINE = REPO_ROOT / "docs" / "planning" / "escape-hatch-baseline.json"
SNAPSHOT = REPO_ROOT / "manifest.snapshot.json"


def _count_tier3(snapshot: dict) -> tuple[dict[str, int], list[str]]:
    """(per-subsystem tier-3 counts, justification violations)."""
    counts: dict[str, int] = {}
    problems: list[str] = []

    def walk(node: object, subsystem: str, carrier: dict | None) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            is_tier3 = (isinstance(ref, str) and ref.startswith("view:")) or \
                node.get("tier") == 3 or bool(node.get("escape_hatch"))
            if is_tier3:
                counts[subsystem] = counts.get(subsystem, 0) + 1
                holder = carrier if isinstance(ref, str) else node
                justification = (holder or {}).get("justification") or node.get("justification")
                if not justification:
                    what = ref or node.get("id") or node.get("panel_id") or "tier-3 unit"
                    problems.append(
                        f"{subsystem}: {what} is tier-3 with no non-empty justification")
            for v in node.values():
                walk(v, subsystem, node)
        elif isinstance(node, list):
            for v in node:
                walk(v, subsystem, carrier)

    for subsystem, body in (snapshot.get("subsystems") or {}).items():
        walk(body, subsystem, None)
    return counts, problems


def _unreachable_ui_modules(snapshot: dict) -> list[str]:
    """`sb/domain/<x>/ui/` modules not referenced by any registered ref."""
    domain_root = REPO_ROOT / "sb" / "domain"
    if not domain_root.is_dir():
        return []
    referenced_modules = {
        meta.get("module") for meta in (snapshot.get("projections") or {}).get("refs", {}).values()
    }
    problems = []
    for ui_file in sorted(domain_root.glob("*/ui/*.py")):
        if ui_file.name == "__init__.py":
            continue
        module = ".".join(ui_file.relative_to(REPO_ROOT).with_suffix("").parts)
        if module not in referenced_modules:
            problems.append(
                f"{ui_file.relative_to(REPO_ROOT)}: domain ui module unreachable "
                "from any registered ref")
    return problems


def check(snapshot: dict, baseline: dict, *, tighten: bool = False) -> tuple[list[str], dict]:
    counts, problems = _count_tier3(snapshot)
    problems += _unreachable_ui_modules(snapshot)
    total = sum(counts.values())

    base_counts: dict[str, int] = baseline.get("per_subsystem") or {}
    base_total = int(baseline.get("total") or 0)

    for subsystem, n in sorted(counts.items()):
        allowed = int(base_counts.get(subsystem, 0))
        if n > allowed:
            problems.append(
                f"{subsystem}: tier-3 count rose to {n} (baseline {allowed}) — "
                "update the baseline in this PR with a ledger entry "
                "(what grew, why, the rejected tier-2 alternative)")
    if total > base_total:
        problems.append(f"repo total tier-3 count rose to {total} (baseline {base_total})")

    new_baseline = dict(baseline)
    if tighten and total <= base_total:
        new_baseline["per_subsystem"] = {k: v for k, v in sorted(counts.items())}
        new_baseline["total"] = total
    return problems, new_baseline


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="A-19 escape-hatch ratchet.")
    parser.add_argument("--snapshot", default=str(SNAPSHOT))
    parser.add_argument("--tighten", action="store_true",
                        help="rewrite the baseline down after a reduction (one-way)")
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"check_escape_hatches: {snapshot_path} absent — dormant until the "
              "committed snapshot exists (rides the manifest-validate gate).")
        return 0
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems, new_baseline = check(snapshot, baseline, tighten=args.tighten)
    if args.tighten and new_baseline != baseline:
        BASELINE.write_text(json.dumps(new_baseline, indent=2, sort_keys=False) + "\n",
                            encoding="utf-8")
        print(f"check_escape_hatches: baseline tightened to total={new_baseline['total']}")
    for p in problems:
        print(p)
    if problems:
        print(f"check_escape_hatches: {len(problems)} violation(s)", file=sys.stderr)
        return 1
    print("check_escape_hatches: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
