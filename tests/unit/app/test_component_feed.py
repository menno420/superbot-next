"""The live component feed (sb/adapters/discord/component_feed.py) — the
interaction-band twin of the message feed: gateway ``on_interaction`` →
``dispatch_component`` → ``resolve()``. Hermetic + roster-free (see
TestManifestPanelRegistration's docstring in test_main_wiring.py): every
interaction here is a duck-typed SimpleNamespace — no discord import, no
sb.manifest import; the adapter is duck-typed by design and tests
everywhere (the ci.yml `tests` job runs without runtime deps)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.adapters.discord import component_feed
from sb.kernel.interaction.request import Surface
from sb.kernel.panels.engine import PanelSession


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


class _FakeResponse:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bool]] = []
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, message: str, *, ephemeral: bool = False):
        self.sent.append((message, ephemeral))
        self._done = True


def _interaction(custom_id: str = "nav:help", *, type_value: object = 3,
                 user_id: int = 42, message_id: int = 1001):
    itype = SimpleNamespace(value=type_value)   # duck InteractionType
    return SimpleNamespace(
        id=555,
        type=itype,
        data={"custom_id": custom_id, "component_type": 2},
        user=SimpleNamespace(id=user_id),
        guild=SimpleNamespace(id=7, owner_id=42),
        channel_id=9,
        message=SimpleNamespace(id=message_id),
        response=_FakeResponse(),
    )


class TestIsComponentInteraction:
    def test_component_wire_type_3_is_consumed(self):
        assert component_feed.is_component_interaction(_interaction())

    def test_raw_int_type_also_matches(self):
        interaction = _interaction()
        interaction.type = 3
        assert component_feed.is_component_interaction(interaction)

    def test_slash_autocomplete_and_modal_types_are_not(self):
        for other in (1, 2, 4, 5, None):
            assert not component_feed.is_component_interaction(
                _interaction(type_value=other))


class TestHandleComponentInteraction:
    def test_non_component_interactions_are_left_alone(self, monkeypatch):
        called = []
        monkeypatch.setattr(component_feed, "dispatch_component",
                            lambda *a, **k: called.append(1))
        interaction = _interaction(type_value=2)     # an application command
        assert run(component_feed.handle_component_interaction(interaction)) is None
        assert not called and not interaction.response.sent

    def test_component_dispatches_through_the_kernel_adapter(self, monkeypatch):
        seen: dict[str, object] = {}

        async def fake_dispatch(interaction, *, responder):
            seen["interaction"] = interaction
            seen["responder"] = responder
            return "RESULT"

        monkeypatch.setattr(component_feed, "dispatch_component", fake_dispatch)
        interaction = _interaction("settings.hub.subsystem_select")
        assert run(component_feed.handle_component_interaction(
            interaction)) == "RESULT"
        assert seen["interaction"] is interaction
        assert seen["responder"].surface is Surface.COMPONENT

    def test_invoker_locked_clicks_are_skipped_not_double_answered(self, monkeypatch):
        # the live PanelRuntimeView.interaction_check owns the denial copy —
        # the feed must not race a second response for the same click.
        called = []
        monkeypatch.setattr(component_feed, "dispatch_component",
                            lambda *a, **k: called.append(1))
        session = PanelSession(panel_id="admin.hub", invoker_id=1,
                               audience="invoker")
        monkeypatch.setattr(component_feed, "session_for",
                            lambda key: session if key == "1001" else None)
        interaction = _interaction(user_id=42)       # not the invoker (1)
        assert run(component_feed.handle_component_interaction(interaction)) is None
        assert not called and not interaction.response.sent

    def test_the_invoker_still_dispatches_on_a_locked_panel(self, monkeypatch):
        async def fake_dispatch(interaction, *, responder):
            return "RESULT"

        monkeypatch.setattr(component_feed, "dispatch_component", fake_dispatch)
        session = PanelSession(panel_id="admin.hub", invoker_id=42,
                               audience="invoker")
        monkeypatch.setattr(component_feed, "session_for",
                            lambda key: session if key == "1001" else None)
        assert run(component_feed.handle_component_interaction(
            _interaction(user_id=42))) == "RESULT"

    def test_dispatch_fault_renders_the_error_envelope(self, monkeypatch):
        async def boom(interaction, *, responder):
            raise RuntimeError("wiring fault")

        monkeypatch.setattr(component_feed, "dispatch_component", boom)
        interaction = _interaction()
        assert run(component_feed.handle_component_interaction(interaction)) is None
        assert len(interaction.response.sent) == 1   # the K8 envelope, ephemeral
        assert interaction.response.sent[0][1] is True

    def test_fault_after_ack_never_double_responds(self, monkeypatch):
        async def boom(interaction, *, responder):
            await responder.ack(ephemeral=True)      # already acked pre-fault
            raise RuntimeError("late fault")

        monkeypatch.setattr(component_feed, "dispatch_component", boom)
        interaction = _interaction()
        acked = []

        async def defer(*, ephemeral: bool) -> None:
            acked.append(ephemeral)
            interaction.response._done = True

        interaction.response.defer = defer
        assert run(component_feed.handle_component_interaction(interaction)) is None
        assert acked == [True] and not interaction.response.sent


class TestArmComponentFeed:
    def test_registers_an_additive_on_interaction_listener(self):
        listeners: list[tuple[object, str]] = []
        bot = SimpleNamespace(
            add_listener=lambda coro, name: listeners.append((coro, name)))
        component_feed.arm_component_feed(bot)
        assert len(listeners) == 1
        assert listeners[0][1] == "on_interaction"
        assert asyncio.iscoroutinefunction(listeners[0][0])
