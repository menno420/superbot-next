"""The PR #412 orphan-pendings rules (tools/check_orphan_pendings.py) —
exercised against IN-MEMORY synthetic populations so both red directions
stay covered without CI theatrics (the test_runtime_smoke.py pattern).

Hermetic on purpose: NO full manifest roster import here — importing it
mid-suite front-runs the band tests' import-time registrations. Every
population is synthetic; the real composition boot is exercised by the
checker itself in ci.yml's checkers job."""

from __future__ import annotations

from tools.check_orphan_pendings import (
    _KNOWN_ORPHANS,
    dangling_handler_refs,
    orphan_pending_registrations,
)


def _refd(*pairs: tuple[str, str, str]) -> dict[tuple[str, str], set[str]]:
    """(kind, name, owner) triples -> the referenced-population mapping."""
    out: dict[tuple[str, str], set[str]] = {}
    for kind, name, owner in pairs:
        out.setdefault((kind, name), set()).add(owner)
    return out


class TestO1Dangling:
    def test_referenced_but_unregistered_handler_is_red(self):
        referenced = _refd(
            ("handler", "fix.gone_pending", "panel:fix.hub"))
        problems = dangling_handler_refs(referenced, registered=set())
        assert len(problems) == 1
        assert "O1 handler:fix.gone_pending" in problems[0]
        assert "panel:fix.hub" in problems[0]

    def test_non_pending_dangling_handler_is_red_too(self):
        # O1 is the RefUnresolved class — the suffix is irrelevant to it.
        referenced = _refd(("handler", "fix.route", "manifest:fix"))
        problems = dangling_handler_refs(referenced, registered=set())
        assert len(problems) == 1 and "handler:fix.route" in problems[0]

    def test_registered_reference_is_green(self):
        referenced = _refd(("handler", "fix.ok_pending", "panel:fix.hub"))
        assert dangling_handler_refs(
            referenced, registered={("handler", "fix.ok_pending")}) == []

    def test_non_handler_kinds_are_out_of_scope(self):
        # panel/provider refs are W2/W1's remit, never O1's.
        referenced = _refd(("panel", "fix.gone", "manifest:fix"),
                           ("provider", "fix.gone", "manifest:fix"))
        assert dangling_handler_refs(referenced, registered=set()) == []


class TestO2Orphans:
    def test_registered_unreferenced_pending_is_red(self):
        problems = orphan_pending_registrations(
            registered={("handler", "fix.dead_pending")},
            referenced={},
            baseline=frozenset())
        assert len(problems) == 1
        assert "O2 handler:fix.dead_pending" in problems[0]
        assert "#412" in problems[0]

    def test_referenced_pending_is_green(self):
        problems = orphan_pending_registrations(
            registered={("handler", "fix.live_pending")},
            referenced=_refd(("handler", "fix.live_pending", "panel:fix.hub")),
            baseline=frozenset())
        assert problems == []

    def test_baseline_entry_stays_green_while_still_real(self):
        problems = orphan_pending_registrations(
            registered={("handler", "fix.known_pending")},
            referenced={},
            baseline=frozenset({"fix.known_pending"}))
        assert problems == []

    def test_stale_baseline_row_is_red(self):
        # the pending was retired (or wired) but the row was not pruned —
        # a same-name regression would hide behind it.
        problems = orphan_pending_registrations(
            registered=set(),
            referenced={},
            baseline=frozenset({"fix.fixed_pending"}))
        assert len(problems) == 1 and "stale baseline row" in problems[0]

    def test_non_pending_registrations_are_out_of_scope(self):
        # an unreferenced NON-pending handler is not this rule's finding
        # (plenty of handlers are dispatched dynamically by design).
        problems = orphan_pending_registrations(
            registered={("handler", "fix.dynamic_route")},
            referenced={},
            baseline=frozenset())
        assert problems == []

    def test_lifecycle_style_names_never_enter(self):
        # the scope fence: raw `_pending` strings (kernel lifecycle
        # globals, rps_pvp_pending subsystem keys) are not handler-kind
        # refs, so they never join either population.
        problems = orphan_pending_registrations(
            registered={("engine", "kernel.shutdown_pending"),
                        ("provider", "rps_pvp_pending")},
            referenced={},
            baseline=frozenset())
        assert problems == []


class TestBaselineHygiene:
    def test_baseline_is_the_landing_snapshot_and_only_shrinks(self):
        # the burn-down list captured on main @ 5dac6ce (post-#412),
        # pruned to the single LIVE row 2026-07-13 (the 8 dead rows'
        # pendings retired — blackjack/rps tournament + btd6 ingestion
        # features landed under *_route / cmd_* refs). REMOVING an entry
        # (with its pending retired) is the only legal edit; this pin
        # makes an ADDITION a reviewed, deliberate act.
        assert _KNOWN_ORPHANS <= {
            "settings.group_pending",
        }
        assert all(name.endswith("_pending") for name in _KNOWN_ORPHANS)
