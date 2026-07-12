"""Composition parity — the BUG A class-killer (band-5 live-drive ledger
bug 1, fixed for role in #111): the LIVE root (``sb.app.main.
load_live_manifests``) imports every ``sb.manifest`` module and dispatches —
it NEVER runs the ``ENSURE_REFS`` hooks when zero plugins are admitted
(those hooks are the compiler/plugin-host re-arm seam, not a boot step). So
any ref that a manifest's ENSURE_REFS registers but module import does NOT
is invisible to the live bot: the routed command/panel dies in a
RefUnresolved BUG envelope on first live use, while every unit suite that
politely calls ``ensure_handler_refs()`` stays green.

This test diffs the two roots' ref sets generically — a NEW plugin whose
pending terminals (or any refs) live only inside its ensure hook fails CI
here, before band-6 trips on it live. Blackjack and rps were the two known
carriers when this landed; both were fixed in the same PR (register at
module import, the sb/domain/role/handlers.py pattern from #111).

_KNOWN_ENSURE_ONLY is a BURN-DOWN list, not an exemption policy: every
entry is a standing live defect of exactly this class, captured at the time
this invariant landed (docs/ideas/ensure-only-registration-gaps-2026-07-10
.md). Entries may only be REMOVED (prune on fix); adding one requires the
same standard as fixing it — there is no legitimate new member of this set.
"""

from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# Standing ensure-only refs at the time this invariant landed — each one is
# a live RefUnresolved waiting to fire (see the ideas ledger). Burn down to
# empty; never grow.
_KNOWN_ENSURE_ONLY: frozenset[str] = frozenset({
    "handler:fishing.bait_pending",
    "handler:fishing.boathouse_pending",
    "handler:fishing.craftbait_pending",
    "handler:fishing.craftcharm_pending",
    "handler:fishing.craftcurio_pending",
    "handler:fishing.craftpearl_pending",
    "handler:fishing.craftrod_pending",
    "handler:fishing.curios_pending",
    "handler:fishing.dock_pending",
    "handler:fishing.fishery_pending",
    "handler:fishing.forecast_pending",
    "handler:fishing.rod_pending",
    "handler:fishing.rodrecipes_pending",
    "handler:fishing.sail_pending",
    "handler:fishing.tidepool_pending",
    "handler:mining.build_pending",
    "handler:mining.buildable_pending",
    "handler:mining.buildlist_pending",
    # equip/unequip/gear/loadout/character pruned by the slice-1 port —
    # their real *_route / *_view handlers register at module import.
    # descend/ascend/mineworld pruned by the slice-2 port — their real
    # descend_route / ascend_route / mineworld_route register at import.
    "handler:mining.cook_pending",
    "handler:mining.forge_pending",
    "handler:mining.home_pending",
    "handler:mining.quickcraft_pending",
    "handler:mining.repair_pending",
    "handler:mining.skill_pending",
    "handler:mining.skills_pending",
    "handler:mining.titles_pending",
    "handler:mining.use_pending",
    "handler:mining.workshop_pending",
    "panel:role.hub",
})


# The probe runs in a CLEAN interpreter (subprocess): re-importing domain
# modules in-process trips kernel registries that are deliberately
# non-idempotent across module identities (e.g. sb.kernel.ai.router route
# probes raise on a same-name/different-fn re-register), and would also
# leak fresh module objects into a suite that cached the old ones. A fresh
# process IS the live root's posture — cold import, nothing pre-armed.
_PROBE = r"""
import importlib, json, pkgutil, sys
import sb.manifest as manifest_pkg
from sb.spec.refs import ref_inventory

# the exact roster + order the live root walks (sb.app.main.
# load_live_manifests: pkgutil over sb.manifest, sorted by name)
names = [f"sb.manifest.{i.name}"
         for i in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                         key=lambda i: i.name)]
for n in names:
    importlib.import_module(n)
import_root = sorted(ref_inventory())          # what the LIVE root registers
for n in names:
    hook = getattr(sys.modules[n], "ENSURE_REFS", None)
    if callable(hook):
        hook()
inventory = ref_inventory()                    # the compiler/plugin-host view
ensure_only = {ref: meta["module"] for ref, meta in inventory.items()
               if ref not in set(import_root)}
print(json.dumps({"import_root": import_root, "ensure_only": ensure_only}))
"""


@lru_cache(maxsize=1)
def _both_roots() -> tuple[frozenset[str], dict[str, str]]:
    """(import_root_set, ensure_only_ref -> registering module).

    Import root: cold import of every manifest module — what
    ``load_live_manifests`` produces live. Ensure root: the same plus
    every ENSURE_REFS hook — what the compiler (P1) and the polite unit
    suites see. The diff is exactly the live-invisible surface.
    """
    repo_root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE], cwd=repo_root,
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        f"composition probe failed:\n{proc.stderr[-2000:]}")
    data = json.loads(proc.stdout)
    return frozenset(data["import_root"]), data["ensure_only"]


def test_no_new_ensure_only_refs():
    """ANY ref visible only after ENSURE_REFS is a live RefUnresolved —
    register at module import (declaring IS reserving; the
    sb/domain/role/handlers.py `_register_pending()` pattern)."""
    _, ensure_only = _both_roots()
    new = {ref: module for ref, module in ensure_only.items()
           if ref not in _KNOWN_ENSURE_ONLY}
    assert new == {}, (
        "ref(s) registered ONLY by ENSURE_REFS — the live root never runs "
        "those hooks, so these die in RefUnresolved BUG envelopes on first "
        "live dispatch. Register at module import instead "
        f"(role/handlers.py pattern): {new}")


def test_burn_down_entries_are_still_real():
    """A pruned defect must leave the list — a stale row hides a regression
    of the same name (and blackjack/rps must never reappear)."""
    _, ensure_only = _both_roots()
    stale = sorted(_KNOWN_ENSURE_ONLY - set(ensure_only))
    assert stale == [], (
        f"fixed (or vanished) refs still on the burn-down list — prune: {stale}")
    fixed_this_pr = [r for r in _KNOWN_ENSURE_ONLY
                     if r.startswith(("handler:blackjack.", "handler:rps."))]
    assert fixed_this_pr == []


def test_the_sweep_sees_the_live_roster():
    """The diff is only meaningful if the walk actually covered the tree."""
    import_root, _ = _both_roots()
    # 563 import-root refs when this invariant landed; the roster only grows
    assert len(import_root) >= 550
    for ref in ("handler:blackjack.tournament_open_pending",
                "handler:rps.register_pending",
                "handler:role.create_pending"):
        assert ref in import_root, ref
