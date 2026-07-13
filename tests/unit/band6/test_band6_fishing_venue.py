"""Fishing depth slice 1 — weather + venue: the ported venue module
(shipped ``utils/fishing/venue.py`` verbatim), the ``!forecast`` embed
bytes and the ``!sail`` toggle lane (goldens/fishing/sweep_forecast +
sweep_sail pin the user-facing bytes), the new ``fishing_venue`` store
spec + erasure ref, and the manifest/hub route flips."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42


@dataclass(frozen=True)
class _FakeReq:
    """The ResolveRequest subset these handlers touch — a dataclass so
    the ``_card`` lane's ``dataclasses.replace(req, args=…)`` works."""

    actor: object = field(
        default_factory=lambda: SimpleNamespace(user_id=P1,
                                                actor_type="user"))
    guild_id: int = GID
    channel_id: int = 2
    args: dict = field(default_factory=dict)
    origin: object = None
    request_id: str = "r1"
    surface: object = None


def _req(uid: int = P1, gid: int = GID, argv: tuple = ()):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"),
                    guild_id=gid, args={"argv": argv})


class FakeVenueStore:
    """In-memory fishing_venue over the sole-writer store module."""

    def __init__(self):
        self.rows: dict[tuple, str] = {}

    def install(self, monkeypatch):
        from sb.domain.fishing import store as fs

        async def get_fishing_venue(user_id, guild_id, conn=None):
            return self.rows.get((user_id, guild_id), "shore")

        async def set_fishing_venue(user_id, guild_id, venue, conn=None):
            self.rows[(user_id, guild_id)] = venue

        monkeypatch.setattr(fs, "get_fishing_venue", get_fishing_venue)
        monkeypatch.setattr(fs, "set_fishing_venue", set_fishing_venue)
        return self


# --- the pure venue module (shipped verbatim) ------------------------------------


def test_venue_keys_profiles_and_toggle():
    from sb.domain.fishing import venue

    assert (venue.SHORE, venue.DEEPWATER) == ("shore", "deepwater")
    # normalize: None / unknown / case+space slop → shore
    assert venue.normalize(None) == "shore"
    assert venue.normalize("atlantis") == "shore"
    assert venue.normalize(" DEEPWATER ") == "deepwater"
    # the toggle is the shipped shore ↔ deepwater flip
    assert venue.toggle(None) == "deepwater"
    assert venue.toggle("shore") == "deepwater"
    assert venue.toggle("deepwater") == "shore"
    assert venue.toggle("junk") == "deepwater"     # unknown reads shore
    # profile identity bytes (the hub field / cast footer interpolate
    # emoji + name + blurb — sweep_fishing pins the shore bytes)
    shore = venue.profile_for(None)
    assert (shore.emoji, shore.name) == ("🏖️", "Shore")
    assert shore.blurb == "Relaxed casting from the shoreline."
    deep = venue.profile_for("deepwater")
    assert (deep.emoji, deep.name) == ("⛵", "Deepwater")
    # the shipped tuning numbers ride as data (shore = the tuned
    # minigame constants; deepwater = the sim §5 tunables)
    assert (shore.bite_delay_min, shore.bite_delay_max,
            shore.bite_delay_floor) == (3.0, 6.0, 1.5)
    assert (shore.reaction_window, shore.base_escape) == (2.5, 0.06)
    assert (deep.bite_delay_min, deep.bite_delay_max,
            deep.bite_delay_floor) == (6.0, 12.0, 3.0)
    assert (deep.reaction_window, deep.base_escape) == (2.0, 0.22)
    assert deep.species_venue == "deepwater"


# --- !sail — the venue toggle lane (sweep_sail bytes) ------------------------------


def test_sail_route_sets_sail_then_docks(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.sail_route"))
    store = FakeVenueStore().install(monkeypatch)

    # fresh player (no row → shore) sails to deepwater — the
    # golden-pinned message byte + the minted row
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    assert reply.user_message == (
        "⛵ **You set sail for deepwater.** Rare boat-only fish lurk "
        "here — they bite slower and fight harder to break free, so a "
        "rod with good escape-resist pays off. Cast with `!fish`.")
    assert store.rows[(P1, GID)] == "deepwater"

    # the second toggle docks back on the shore (oracle set_venue's
    # other branch — not golden-pinned, source-verbatim)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    assert reply.user_message == (
        "🏖️ **You docked back on the shore.** Relaxed casting for the "
        "everyday catch. Cast with `!fish`.")
    assert store.rows[(P1, GID)] == "shore"


# --- !forecast — the date-seeded forecast embed (sweep_forecast bytes) -------------


def test_forecast_view_renders_the_rain_embed(monkeypatch):
    from sb.domain.fishing import service, weather
    from sb.kernel.panels import engine as panels_engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.forecast_view"))

    opened: list = []

    async def _open_panel(ref, req):
        opened.append((ref, req))

    monkeypatch.setattr(panels_engine, "open_panel", _open_panel)
    try:
        weather.seed_weather_for_replay("rain")
        reply = run(route(_req()))
    finally:
        weather.seed_weather_for_replay(None)
    assert reply.outcome is SUCCESS
    (ref, req), = opened
    assert "fishing.card" in str(ref)
    embed = req.args["_card"]
    # goldens/fishing/sweep_forecast, byte-for-byte
    assert embed.title == "🌧️ Today's fishing forecast: Rain"
    assert embed.description == (
        "Rain stirs the surface — the fish are biting fast today.\n\n"
        "**Effect on every cast:** faster bites")
    assert embed.footer == "Same for everyone today · 🎣 !fish to cast"
    assert embed.style_token == "blue"      # _FISHING_COLOR 3447003


# --- the store spec + refs ---------------------------------------------------------


def test_venue_store_spec_and_erasure_ref():
    from sb.domain.fishing import ops, store
    from sb.spec.refs import WorkflowRef, is_registered
    from sb.spec.versioning import DataClass

    spec = store.FISHING_VENUE_STORE
    assert spec.table == "fishing_venue"
    assert spec.data_class is DataClass.MEMBER_ID
    assert spec.erasure_ref == WorkflowRef("fishing.erase_subject_venue")
    ops.ensure_ops_refs()
    assert is_registered(WorkflowRef("fishing.erase_subject_venue"))


# --- manifest + hub routes ----------------------------------------------------------


def test_manifest_and_hub_route_the_live_lanes():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import fishing_hub_spec
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["forecast"].route == HandlerRef("fishing.forecast_view")
    assert by_name["forecast"].aliases == ("fishforecast", "fishingweather")
    assert by_name["sail"].route == HandlerRef("fishing.sail_route")
    assert by_name["sail"].aliases == ("setsail",)
    # the new store is a declared fishing surface (covered by
    # sweep_sail's own db_delta row — no depth exemption)
    assert "fishing_venue" in {s.table for s in MANIFEST.stores}
    # the hub ⛵ Set sail / Dock button repointed to the live lane
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_sail"].handler == HandlerRef("fishing.sail_route")
    # forecast/sail left PENDING; their *_pending refs no longer register
    service.ensure_handler_refs()
    assert "forecast" not in service.PENDING
    assert "sail" not in service.PENDING
    assert not is_registered(HandlerRef("fishing.forecast_pending"))
    assert not is_registered(HandlerRef("fishing.sail_pending"))
