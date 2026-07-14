"""Game sections slice 3 (D-0082, docs/design/game-sections.md §6): the
games hub renders the per-guild ENABLED set — the ``games.hub_fields``
provider filters through the slice-1 ``enabled_games`` seam, the hub /
world buttons carry ``games.enabled_<key>`` visible_when predicates
(render-time drop + resolve.py dispatch-time stale-click deny), sections
with zero enabled games drop, and fully-default guilds render
BYTE-IDENTICAL to the static roster (the ported games goldens' bytes)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1 = 1, 42

_CASINO = ("blackjack", "casino")
_ARCADE = ("deathmatch", "rps_tournament", "counting", "chain")
_WORLD = ("mining", "fishing", "creature", "farm")
_ALL = _CASINO + _ARCADE + _WORLD


@pytest.fixture(autouse=True)
def _default_sections():
    """Deterministic registry: exactly the manifest's DEFAULT sections
    (the slice-1 fixture shape), restored after."""
    from sb.manifest import games as manifest
    from sb.spec import sections as mod

    saved = dict(mod._SECTIONS)
    mod.clear_sections_for_tests()
    manifest._register_sections()
    yield
    mod.clear_sections_for_tests()
    mod._SECTIONS.update(saved)


def _install_enabled(monkeypatch, enabled: set[str]):
    """Stub the ONE governance read every lane lazily imports (the
    slice-1/2 test shape); returns the call log."""
    from sb.domain.governance import service

    calls: list[tuple[int, str]] = []

    async def fake_subsystem_enabled(guild_id: int, subsystem: str) -> bool:
        calls.append((guild_id, subsystem))
        return subsystem in enabled

    monkeypatch.setattr(service, "subsystem_enabled", fake_subsystem_enabled)
    return calls


def _install_broken_read(monkeypatch):
    from sb.domain.governance import service

    async def broken(guild_id: int, subsystem: str) -> bool:
        raise RuntimeError("governance store unreachable")

    monkeypatch.setattr(service, "subsystem_enabled", broken)


def _ctx(guild_id: int = GID):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id, actor=SimpleNamespace(user_id=P1),
        channel_id=900, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


def _render_hub(guild_id: int = GID):
    from sb.domain.games.panels import _render_hub as render, games_hub_spec

    return run(render(games_hub_spec(), _ctx(guild_id)))


def _render_world(guild_id: int = GID):
    from sb.domain.games.panels import _render_hub as render, world_hub_spec

    return run(render(world_hub_spec(), _ctx(guild_id)))


def _game_button_ids(rendered) -> set[str]:
    return {c.custom_id for c in rendered.components
            if c.custom_id.startswith(("games:open:", "explore:open:"))}


# --- the byte-identity property (the ported goldens' contract) -----------------


def test_all_enabled_renders_byte_identical_to_the_static_roster(monkeypatch):
    # Fully-default guild (no overrides ⇒ every read True): the provider
    # path must reproduce the static roster BYTE-FOR-BYTE — the property
    # that keeps parity/goldens/games/sweep_games + sweep_slash_games
    # replaying unchanged.
    from sb.domain.games.panels import _STATIC_HUB_FIELDS

    _install_enabled(monkeypatch, set(_ALL))
    rendered = _render_hub()
    assert rendered.embed.fields == _STATIC_HUB_FIELDS
    assert rendered.embed.fields[0][0] == "🎰 Casino"
    assert rendered.embed.fields[1][0] == "🕹️ Arcade"
    assert rendered.embed.fields[2][0] == "🌍 World"
    assert _game_button_ids(rendered) == {
        f"games:open:{k}" for k in _ALL}
    assert rendered.embed.footer == "Only you can interact with this panel."


def test_world_all_enabled_renders_byte_identical(monkeypatch):
    from sb.domain.games.panels import _WORLD_PLACES

    _install_enabled(monkeypatch, set(_ALL))
    rendered = _render_world()
    assert rendered.embed.fields == (("Where to go", _WORLD_PLACES),)
    assert _game_button_ids(rendered) == {
        "explore:open:mining", "explore:open:fishing", "explore:open:farm"}


def test_hub_has_no_selectors_so_no_options_to_filter():
    # D-0082 §6 names "the hub select" — at HEAD the shipped hub carries
    # ONLY buttons (the goldens pin zero selects); the enablement filter
    # therefore rides visible_when on the buttons. The slice-2 settings
    # panel's selects intentionally SHOW disabled games (its job is
    # toggling them) — no hub-side options provider exists to filter.
    from sb.domain.games.panels import games_hub_spec, world_hub_spec

    assert games_hub_spec().selectors == ()
    assert world_hub_spec().selectors == ()


# --- filtering: pick-a-few / section drop / empty ------------------------------


def test_pick_a_few_filters_fields_and_buttons(monkeypatch):
    _install_enabled(monkeypatch, {"blackjack", "fishing", "counting"})
    rendered = _render_hub()
    assert rendered.embed.fields == (
        ("🎰 Casino",
         "🃏 **Blackjack** — Blackjack card game"),
        ("🕹️ Arcade",
         "🔢 **Counting** — Collaborative counting game"),
        ("🌍 World",
         "🎣 **Fishing** — Fishing minigame — cast a line, build your "
         "collection"),
    )
    assert _game_button_ids(rendered) == {
        "games:open:blackjack", "games:open:fishing", "games:open:counting"}


def test_fully_disabled_section_drops(monkeypatch):
    _install_enabled(monkeypatch, set(_ARCADE + _WORLD))
    rendered = _render_hub()
    assert [name for name, _v in rendered.embed.fields] == \
        ["🕹️ Arcade", "🌍 World"]
    assert _game_button_ids(rendered) == {
        f"games:open:{k}" for k in _ARCADE + _WORLD}


def test_nothing_enabled_renders_no_catalog(monkeypatch):
    # slice-1 "empty = empty": all games disabled ⇒ zero catalog fields,
    # zero game buttons — only the description + the nav:help slot remain.
    _install_enabled(monkeypatch, set())
    rendered = _render_hub()
    assert rendered.embed.fields == ()
    assert _game_button_ids(rendered) == set()
    assert {c.custom_id for c in rendered.components} == {"nav:help"}


def test_world_filters_lines_and_buttons(monkeypatch):
    _install_enabled(monkeypatch, set(_ALL) - {"mining"})
    rendered = _render_world()
    (name, value), = rendered.embed.fields
    assert name == "Where to go"
    assert "**Mine**" not in value
    assert "**Fish**" in value and "**Farm**" in value
    ids = {c.custom_id for c in rendered.components}
    assert "explore:open:mining" not in ids
    assert {"explore:open:fishing", "explore:open:farm",
            "explore:world_card", "nav:help"} <= ids


def test_world_all_games_disabled_drops_the_field_keeps_the_card(monkeypatch):
    _install_enabled(monkeypatch, set())
    rendered = _render_world()
    assert rendered.embed.fields == ()
    assert {c.custom_id for c in rendered.components} == {
        "explore:world_card", "nav:help"}   # the card is NOT a game


# --- fail-open degradation (the goldens' safety net) ---------------------------


def test_broken_enablement_read_fails_open_to_the_static_bytes(monkeypatch):
    # A read outage renders TODAY'S full hub (never a blank one) —
    # enforcement stays at dispatch. This is also why the ported goldens
    # can never blank: any seam failure degrades to the pinned bytes.
    from sb.domain.games.panels import _STATIC_HUB_FIELDS, _WORLD_PLACES

    _install_broken_read(monkeypatch)
    hub = _render_hub()
    assert hub.embed.fields == _STATIC_HUB_FIELDS
    assert _game_button_ids(hub) == {f"games:open:{k}" for k in _ALL}
    world = _render_world()
    assert world.embed.fields == (("Where to go", _WORLD_PLACES),)


def test_empty_sections_registry_fails_open_to_the_static_fields(monkeypatch):
    # An unpopulated registry means boot never declared the inventory —
    # NOT "everything disabled"; the hub renders the static roster.
    from sb.domain.games.panels import _STATIC_HUB_FIELDS
    from sb.spec import sections as mod

    _install_enabled(monkeypatch, set(_ALL))
    mod.clear_sections_for_tests()
    rendered = _render_hub()
    assert rendered.embed.fields == _STATIC_HUB_FIELDS


# --- the update contract: next-interaction consistency (§6.1) ------------------


def test_fresh_render_reflects_a_mutation_next_interaction(monkeypatch):
    # The engine has no pub/sub — the contract is that EVERY fresh render
    # (open / nav click / refresh_session_view) re-resolves the enabled
    # set at click time. Flip enablement between two renders and the
    # second render is already honest; an ALREADY-RENDERED message is
    # covered by the dispatch-time deny below.
    enabled = set(_ALL)
    from sb.domain.governance import service

    async def fake(guild_id: int, subsystem: str) -> bool:
        return subsystem in enabled

    monkeypatch.setattr(service, "subsystem_enabled", fake)

    before = _render_hub()
    assert "games:open:mining" in _game_button_ids(before)
    enabled -= {"mining"}                      # the slice-2 settings write
    after = _render_hub()
    assert "games:open:mining" not in _game_button_ids(after)
    assert "**Mining**" not in dict(after.embed.fields)["🌍 World"]


# --- the stale-click deny path (no strand) --------------------------------------


class _Responder:
    def __init__(self):
        self.acks: list[bool] = []
        self.denials: list[tuple[str, bool]] = []

    def is_acked(self) -> bool:
        return bool(self.acks)

    def committed_visibility(self):
        return None

    async def ack(self, *, ephemeral: bool) -> None:
        self.acks.append(ephemeral)

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        self.denials.append((message, ephemeral))

    async def open_modal(self, modal_ref) -> None:  # pragma: no cover
        pass

    async def open_confirm(self, prompt) -> None:  # pragma: no cover
        pass

    async def render(self, result) -> None:  # pragma: no cover
        pass


@pytest.fixture()
def _clean_resolver():
    import sb.kernel.lifecycle as lifecycle
    from sb.kernel.interaction import cooldown as cooldown_mod
    from sb.kernel.interaction.predicates import (
        reset_predicate_ports_for_tests,
    )
    from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests

    lifecycle.reset_for_tests()
    lifecycle.set_phase(lifecycle.Phase.RUNNING)
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()
    yield
    lifecycle.reset_for_tests()
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()


def _component_request(action_spec, responder):
    from sb.kernel.interaction.request import (
        ActorRef,
        ResolveRequest,
        Surface,
        TargetRef,
    )

    return ResolveRequest(
        surface=Surface.COMPONENT,
        target=TargetRef(key="games.hub.ga_blackjack", spec=action_spec),
        actor=ActorRef(user_id=P1, is_guild_operator=False,
                       is_bot_owner=False, is_dm=False,
                       member_tier="administrator"),
        guild_id=GID, channel_id=900, args={}, responder=responder,
        origin=object())


def test_stale_click_on_a_disabled_games_button_is_denied(
        monkeypatch, _clean_resolver):
    # An ALREADY-RENDERED hub message still shows the disabled game's
    # button — the dispatch-time re-evaluation of the SAME visible_when
    # predicate (resolve.py 02 §3.0 stale/replayed-custom_id guard)
    # denies the click before any panel opens. No strand.
    from sb.domain.games.panels import games_hub_spec
    from sb.kernel.interaction.resolve import resolve
    from sb.spec.outcomes import BLOCKED, DenialReason

    _install_enabled(monkeypatch, set(_ALL) - {"blackjack"})
    action = {a.action_id: a for a in games_hub_spec().actions}["ga_blackjack"]
    assert action.visible_when == "games.enabled_blackjack"

    responder = _Responder()
    result = run(resolve(_component_request(action, responder)))
    assert result.outcome == BLOCKED
    assert result.reason is DenialReason.DISABLED
    assert responder.denials == [
        ("This control is no longer available.", True)]


def test_click_on_an_enabled_games_button_opens_the_child(
        monkeypatch, _clean_resolver):
    from sb.domain.games.panels import games_hub_spec
    from sb.kernel.interaction.resolve import install_panel_engine, resolve
    from sb.spec.outcomes import SUCCESS

    _install_enabled(monkeypatch, set(_ALL))
    opened: list[str] = []

    async def engine(ref, req):
        opened.append(ref.name)

    install_panel_engine(engine)
    action = {a.action_id: a for a in games_hub_spec().actions}["ga_blackjack"]
    result = run(resolve(_component_request(action, _Responder())))
    assert result.outcome == SUCCESS
    assert opened == ["blackjack.hub"]
