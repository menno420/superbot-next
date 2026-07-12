"""The ORDER 016 runtime-smoke W-rules (tools/check_runtime_smoke.py) —
exercised against IN-MEMORY broken fixtures so the red path stays covered
without CI theatrics (the deliberate-break proof run is one-shot; these
pins are permanent).

Hermetic on purpose (the test_main_wiring.py lesson): NO full manifest
roster import here — importing it mid-suite front-runs the band tests'
import-time registrations. Every fixture is synthetic."""

from __future__ import annotations

from types import SimpleNamespace

from tools.check_runtime_smoke import (
    GraphBus,
    orphan_subscriptions,
    scan_emit_sites,
    undelivered_durable_events,
    unknown_emit_names,
    unmet_expected_subscribers,
    unregistered_panel_refs,
    unresolved_manifest_refs,
)


def _ref(kind: str, name: str):
    return SimpleNamespace(kind=kind, name=name)


def _walk(pairs):
    """A walk_refs stand-in: manifest.refs is the pre-walked list."""
    def walk_refs(manifest):
        return list(getattr(manifest, "refs", ()))
    return walk_refs


def _spec(name: str, *, delivery: str = "best_effort",
          expected=()) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        delivery=SimpleNamespace(value=delivery),
        expected_subscribers=tuple(expected),
    )


class TestW1RefGraph:
    def test_unresolved_ref_is_red(self):
        m = SimpleNamespace(key="fix", refs=[(_ref("handler", "fix.gone"), None)])

        def resolver(ref):
            raise LookupError(f"{ref.kind}:{ref.name} has no registered callable")

        problems = unresolved_manifest_refs(
            [m], resolver=resolver, walk_refs=_walk(None),
            skip_predicate=lambda r: False)
        assert len(problems) == 1 and "handler:fix.gone" in problems[0]

    def test_non_callable_resolution_is_red(self):
        m = SimpleNamespace(key="fix", refs=[(_ref("handler", "fix.data"), None)])
        problems = unresolved_manifest_refs(
            [m], resolver=lambda ref: 42, walk_refs=_walk(None),
            skip_predicate=lambda r: False)
        assert len(problems) == 1 and "non-callable" in problems[0]

    def test_resolvable_callable_is_green_and_skip_respected(self):
        m = SimpleNamespace(key="fix", refs=[
            (_ref("handler", "fix.ok"), None),
            (_ref("predicate", "setting:x=1"), None),
        ])
        problems = unresolved_manifest_refs(
            [m], resolver=lambda ref: (lambda: None), walk_refs=_walk(None),
            skip_predicate=lambda r: r.kind == "predicate")
        assert problems == []


class TestW2PanelGraph:
    def test_unregistered_panel_ref_is_red(self):
        m = SimpleNamespace(key="fix", refs=[(_ref("panel", "fix.hub"), None)])

        def get_panel(panel_id):
            raise LookupError(panel_id)

        problems = unregistered_panel_refs([m], get_panel=get_panel,
                                           walk_refs=_walk(None))
        assert len(problems) == 1 and "panel:fix.hub" in problems[0]

    def test_registered_panel_ref_is_green(self):
        m = SimpleNamespace(key="fix", refs=[(_ref("panel", "fix.hub"), None)])
        problems = unregistered_panel_refs(
            [m], get_panel=lambda pid: object(), walk_refs=_walk(None))
        assert problems == []


class TestW3OrphanSubscribers:
    def test_subscription_on_unknown_event_is_red(self):
        bus = GraphBus()
        bus.on("order016.broken.event", lambda **kw: None)
        problems = orphan_subscriptions(bus, {"xp.level_up": _spec("xp.level_up")})
        assert len(problems) == 1 and "order016.broken.event" in problems[0]

    def test_non_callable_subscriber_is_red(self):
        bus = GraphBus()
        bus.on("xp.level_up", "not-a-callable")
        problems = orphan_subscriptions(bus, {"xp.level_up": _spec("xp.level_up")})
        assert len(problems) == 1 and "non-callable" in problems[0]

    def test_known_event_with_callable_is_green(self):
        bus = GraphBus()
        bus.on("xp.level_up", lambda **kw: None)
        assert orphan_subscriptions(bus, {"xp.level_up": _spec("xp.level_up")}) == []


class TestW4DurableDelivery:
    def test_at_least_once_with_no_subscriber_is_red(self):
        bus = GraphBus()
        known = {"audit.action_recorded": _spec("audit.action_recorded",
                                                delivery="at_least_once")}
        problems = undelivered_durable_events(bus, known)
        assert len(problems) == 1 and "ZERO live subscribers" in problems[0]

    def test_best_effort_with_no_subscriber_is_green(self):
        # the honest boundary: zero-subscriber BEST_EFFORT is legal (§2.8).
        bus = GraphBus()
        known = {"xp.awarded": _spec("xp.awarded")}
        assert undelivered_durable_events(bus, known) == []

    def test_subscribed_durable_event_is_green(self):
        bus = GraphBus()
        bus.on("audit.action_recorded", lambda **kw: None)
        known = {"audit.action_recorded": _spec("audit.action_recorded",
                                                delivery="at_least_once")}
        assert undelivered_durable_events(bus, known) == []


class TestW5ExpectedSubscribers:
    def test_unresolvable_expected_subscriber_is_red(self):
        bus = GraphBus()
        bus.on("economy.balance_changed", lambda **kw: None)
        known = {"economy.balance_changed": _spec(
            "economy.balance_changed",
            expected=[_ref("handler", "economy.gone")])}

        def resolver(ref):
            raise LookupError("no registered callable")

        problems = unmet_expected_subscribers(bus, known, resolver=resolver)
        assert len(problems) == 1 and "economy.gone" in problems[0]

    def test_declared_expectation_with_no_live_subscriber_is_red(self):
        bus = GraphBus()  # nobody armed
        known = {"economy.balance_changed": _spec(
            "economy.balance_changed",
            expected=[_ref("handler", "economy.route")])}
        problems = unmet_expected_subscribers(
            bus, known, resolver=lambda ref: (lambda: None))
        assert len(problems) == 1 and "ZERO live subscribers" in problems[0]

    def test_met_expectation_is_green(self):
        bus = GraphBus()
        bus.on("economy.balance_changed", lambda **kw: None)
        known = {"economy.balance_changed": _spec(
            "economy.balance_changed",
            expected=[_ref("handler", "economy.route")])}
        assert unmet_expected_subscribers(
            bus, known, resolver=lambda ref: (lambda: None)) == []


class TestW6EmitSites:
    def test_unknown_emitted_name_is_red(self):
        sites = [("sb/domain/fix/service.py", 10, "order016.smoke_break")]
        problems = unknown_emit_names(sites, {"xp.level_up": _spec("xp.level_up")})
        assert len(problems) == 1
        assert "order016.smoke_break" in problems[0]
        assert "sb/domain/fix/service.py:10" in problems[0]

    def test_known_emitted_name_is_green(self):
        sites = [("sb/x.py", 3, "xp.level_up")]
        assert unknown_emit_names(sites, {"xp.level_up": _spec("xp.level_up")}) == []


class TestEmitSiteScan:
    def test_scan_finds_literals_and_module_constants_skips_dynamic(self, tmp_path):
        pkg = tmp_path / "sb"
        pkg.mkdir()
        (pkg / "svc.py").write_text(
            'EVT = "role.lifecycle_changed"\n'
            "async def go(bus, name, audit):\n"
            '    await bus.emit("audit.action_recorded", a=1)\n'
            "    await bus.emit(EVT, b=2)\n"
            "    await bus.emit(name, c=3)\n"      # dynamic — skipped (boundary)
            "    await sink.emit(audit)\n",        # non-string arg — skipped
            encoding="utf-8")
        sites = scan_emit_sites(pkg)
        names = sorted(name for _f, _l, name in sites)
        assert names == ["audit.action_recorded", "role.lifecycle_changed"]

    def test_scan_survives_syntax_errors(self, tmp_path):
        pkg = tmp_path / "sb"
        pkg.mkdir()
        (pkg / "broken.py").write_text("def (", encoding="utf-8")
        assert scan_emit_sites(pkg) == []


class TestGraphBus:
    def test_bus_shape_matches_eventbus_contract(self):
        bus = GraphBus()
        fn = lambda **kw: None  # noqa: E731
        bus.on("a.b", fn)
        assert bus.subscribers("a.b") == (fn,)
        assert bus.subscribers("missing") == ()
        assert bus.subscribed_names() == ("a.b",)
