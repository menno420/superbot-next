#!/usr/bin/env python3
"""check_orphan_pendings — the PR #412 bug-class guard: `*_pending`
handler refs whose handler (or whose referencing panel) no longer exists.

PROVENANCE: PR #412 ("role: retire the three orphan _pending refs") found
`role.roleinfo_pending` / `role.assignroles_pending` / `role.debug_pending`
registered in sb/domain/role/handlers.py but UNREACHABLE — their live
handlers had landed via #358 and nothing routed to the pendings anymore.
That cleanup was a manual audit (snapshot projections + grep); this checker
mechanizes it so the class cannot silently regrow, in either direction:

  O1 dangling — a handler ref REFERENCED by a registered panel's actions/
     selectors or by a live manifest, with NO ``_REF_TABLE`` entry: the
     click/command dies in a RefUnresolved BUG envelope on first live use.
     Always RED, no baseline. This is deliberately checked over the PANEL
     REGISTRY as well as the manifest walk, because some panel refs are
     minted DYNAMICALLY at spec-construction time (e.g.
     sb/domain/settings/panels.py's ``HandlerRef(f"settings.{action_id}
     _pending")``) — a static grep cannot resolve those; a runtime walk
     after the full composition boot can. (The manifest-side overlap with
     check_runtime_smoke's W1 is accepted: both point at the same bug.)
  O2 orphan — a REGISTERED handler whose name ends ``_pending`` that is
     referenced by NO registered panel and NO manifest ref: the exact #412
     class (registered but unreachable — dead declared surface that rots
     into confusion). RED against ``_KNOWN_ORPHANS``, the burn-down
     baseline captured at this checker's landing (the
     tests/unit/invariants/test_composition_parity.py
     ``_KNOWN_ENSURE_ONLY`` prior art): entries may only be REMOVED (prune
     in the PR that retires the pending), never added — there is no
     legitimate new member. A stale baseline row (an entry that is no
     longer an orphan) is ALSO red, so a pruned defect cannot hide a
     same-name regression.

SCOPE FENCES (the false-positive traps this check is built to dodge): only
``_REF_TABLE`` handler-kind names and walked ``*Ref`` objects are read —
never a raw string grep — so the kernel lifecycle ``_pending`` module
globals (sb/kernel/lifecycle), the ``rps_pvp_pending`` subsystem string,
and ``xp_pending``-style op keys never enter the population.

HONEST COVERAGE BOUNDARY: O2's reference universe is SPEC references
(manifest ref walk + registered-panel ref walk). A handler that dispatches
a pending dynamically at click time (``resolve(HandlerRef(f"..."))``)
would be invisible to it — no such site exists today (verified at
landing); if one lands, exempt its prefix here with a comment, mirroring
check_runtime_smoke's W6 dynamic-name boundary.

Boot pattern: the check_runtime_smoke headless composition boot — boot-gate
leg A (``gate_recompile`` imports every ``sb.manifest`` module + runs the
ENSURE_REFS re-arm hooks), ``load_live_manifests()``,
``register_manifest_panels()``. No token, no guild, no DB, no network —
runs green with only ``pyyaml`` installed (ci.yml's checkers job).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_SNAPSHOT = "manifest.snapshot.json"
PENDING_SUFFIX = "_pending"

# The burn-down baseline: every registered-but-unreferenced `*_pending`
# handler alive on main when this checker landed (2026-07-13, main @
# 5dac6ce — the post-#412 state). Each is a standing #412-class defect,
# NOT an exemption policy. PRUNE the row in the PR that retires the
# pending; never add one.
#   EMPTY as of settings epic S0 (2026-07-19): the last row
#   ("settings.group_pending") was pruned when open_group's non-hub arm
#   re-pointed to the ported settings.group_edit page — no registered-but-
#   unreferenced `*_pending` handler remains. Additions are still illegal;
#   this floor is now zero.
_KNOWN_ORPHANS: frozenset[str] = frozenset()


# --- the pure rules (unit-testable against synthetic populations) ----------------


def dangling_handler_refs(
        referenced: dict[tuple[str, str], set[str]],
        registered: set[tuple[str, str]]) -> list[str]:
    """O1: every referenced handler-kind ref has a registered callable."""
    problems: list[str] = []
    for (kind, name), owners in sorted(referenced.items()):
        if kind != "handler" or (kind, name) in registered:
            continue
        via = ", ".join(sorted(owners)[:3])
        problems.append(
            f"O1 handler:{name} is referenced ({via}) but has NO registered "
            "callable — a RefUnresolved BUG envelope on first live dispatch")
    return problems


def orphan_pending_registrations(
        registered: set[tuple[str, str]],
        referenced: dict[tuple[str, str], set[str]],
        baseline: frozenset[str] = _KNOWN_ORPHANS) -> list[str]:
    """O2: every registered `*_pending` handler is referenced somewhere
    (or sits on the burn-down baseline); every baseline row is still real."""
    pendings = {name for (kind, name) in registered
                if kind == "handler" and name.endswith(PENDING_SUFFIX)}
    referenced_names = {name for (kind, name) in referenced
                        if kind == "handler"}
    orphans = pendings - referenced_names
    problems: list[str] = []
    for name in sorted(orphans - baseline):
        problems.append(
            f"O2 handler:{name} is registered but referenced by NO manifest "
            "ref and NO registered panel — the PR #412 orphan class; retire "
            "the pending_handler(...) call (or wire its route) instead of "
            "growing _KNOWN_ORPHANS")
    for name in sorted(baseline - orphans):
        problems.append(
            f"O2 stale baseline row: handler:{name} is no longer an orphan "
            "(fixed, retired, or now referenced) — prune it from "
            "_KNOWN_ORPHANS so a same-name regression cannot hide")
    return problems


# --- the headless boot (the I/O shell) --------------------------------------------


def collect_populations(snapshot_path: Path) -> tuple[
        dict[tuple[str, str], set[str]], set[tuple[str, str]]]:
    """(referenced ref -> owning loci, registered (kind, name) set) after
    the full composition boot."""
    import json

    from sb.app.boot_gate import gate_recompile

    committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    violations = gate_recompile(committed)
    if violations:
        raise SystemExit(
            "check_orphan_pendings: boot-gate leg A failed (not this "
            "checker's finding — manifest_compile owns it):\n"
            + "\n".join(str(v) for v in violations[:10]))

    from sb.app.main import load_live_manifests
    from sb.app.panel_host import register_manifest_panels
    from sb.kernel.panels.registry import panel_inventory
    from sb.spec.refs import _REF_TABLE
    from tools.manifest_compile import _walk_refs

    manifests = load_live_manifests()
    register_manifest_panels(manifests)

    referenced: dict[tuple[str, str], set[str]] = {}
    for m in manifests:
        key = getattr(m, "key", "?")
        for ref, _owner in _walk_refs(m):
            referenced.setdefault((ref.kind, ref.name), set()).add(
                f"manifest:{key}")
    for panel_id, spec in sorted(panel_inventory().items()):
        for ref, _owner in _walk_refs(spec):
            referenced.setdefault((ref.kind, ref.name), set()).add(
                f"panel:{panel_id}")
    return referenced, set(_REF_TABLE)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="check_orphan_pendings")
    parser.add_argument(
        "snapshot", nargs="?", default=str(REPO_ROOT / DEFAULT_SNAPSHOT),
        help="committed manifest snapshot (default: repo-root "
             f"{DEFAULT_SNAPSHOT})")
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"check_orphan_pendings: {snapshot_path} absent — dormant "
              "until the compiler emits the committed snapshot.")
        return 0

    referenced, registered = collect_populations(snapshot_path)
    problems = dangling_handler_refs(referenced, registered)
    problems += orphan_pending_registrations(registered, referenced)

    if problems:
        for p in problems:
            print(f"RED {p}")
        print(f"check_orphan_pendings: {len(problems)} problem(s)",
              file=sys.stderr)
        return 1

    pendings = sorted(name for (kind, name) in registered
                      if kind == "handler" and name.endswith(PENDING_SUFFIX))
    referenced_pendings = [
        name for name in pendings
        if ("handler", name) in referenced]
    walked_handlers = sum(1 for k in referenced if k[0] == "handler")
    print(f"check_orphan_pendings: OK — {len(pendings)} registered "
          f"*_pending handler(s) ({len(referenced_pendings)} referenced, "
          f"{len(_KNOWN_ORPHANS)} on the burn-down baseline); "
          f"{walked_handlers} handler ref(s) walked from manifests + "
          "registered panels, 0 dangling, 0 new orphans")
    return 0


if __name__ == "__main__":
    sys.exit(main())
