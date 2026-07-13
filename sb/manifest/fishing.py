"""FISHING subsystem manifest (band 6, checkpoint family) — the FULL
shipped command surface verbatim (20 commands): the core cast + dex/
trophy/leaderboard reads, the slice-1 weather/venue surfaces, the
slice-2 rod ladder and the slice-3 bait shelf are live; curio/structure
surfaces are honest pending terminals riding the D-0043 named successor
port."""

from __future__ import annotations

from sb.domain.fishing import panels as _panels
from sb.domain.fishing import service as _service
from sb.domain.fishing.ops import register_ops
from sb.domain.fishing.panels import fishing_hub_spec
from sb.domain.fishing.store import (
    FISHING_BAIT_STORE,
    FISHING_CATCH_LOG_STORE,
    FISHING_ENERGY_STORE,
    FISHING_ROD_STORE,
    FISHING_VENUE_STORE,
)
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, summary: str,
         aliases: tuple[str, ...] = ()) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       aliases=aliases, route=route, audience_tier="user",
                       capability="fishing", summary=summary,
                       usage=f"!{name}")


def _pending(name: str, summary: str,
             aliases: tuple[str, ...] = ()) -> CommandSpec:
    return _cmd(name, HandlerRef(f"fishing.{name}_pending"), summary,
                aliases)


_COMMANDS = (
    _cmd("fish", HandlerRef("fishing.cast_open"),
         "Cast a line — wait for the bite, then reel."),
    _cmd("fishing", PanelRef("fishing.hub"), "Open the fishing hub.",
         ("fishmenu",)),
    _cmd("fishlog", PanelRef("fishing.log"),
         "Your fish dex — every species you've caught.", ("fishdex",)),
    _cmd("fishtop", HandlerRef("fishing.top_view"),
         "Top anglers by total catches.", ("topfishers",)),
    _cmd("trophies", HandlerRef("fishing.trophies_view"),
         "Trophy records — the biggest catches.",
         ("bigfish", "fishtrophy")),
    # --- weather + venue (fishing depth slice 1 — LIVE) -------------------
    _cmd("forecast", HandlerRef("fishing.forecast_view"),
         "Today's fishing weather.",
         ("fishforecast", "fishingweather")),
    _cmd("sail", HandlerRef("fishing.sail_route"),
         "Set sail to the deepwater venue.", ("setsail",)),
    # --- the rod ladder (fishing depth slice 2 — LIVE) ---------------------
    _cmd("rod", HandlerRef("fishing.rod_shop"),
         "The rod shop.", ("rodshop", "buyrod")),
    _cmd("craftrod", HandlerRef("fishing.craftrod_route"),
         "Craft a rod.", ("rodcraft",)),
    _cmd("rodrecipes", HandlerRef("fishing.rodrecipes_view"),
         "Rod crafting recipes.", ("rodrecipe", "rrecipes")),
    # --- the bait shelf (fishing depth slice 3 — LIVE) ---------------------
    _cmd("bait", HandlerRef("fishing.bait_shop"),
         "The bait shop.", ("baitshop", "buybait")),
    _cmd("craftbait", HandlerRef("fishing.craftbait_route"),
         "Craft bait from fish.", ("baitcraft",)),
    _cmd("craftcharm", HandlerRef("fishing.craftcharm_route"),
         "Craft a fishing charm.", ("charmcraft",)),
    _cmd("craftpearl", HandlerRef("fishing.craftpearl_route"),
         "Craft pearl bait.", ("pearlcraft",)),
    # --- curio/structure systems (the D-0043 named successor port) --------
    _pending("curios", "Your curio collection.", ("curio", "carvings")),
    _pending("craftcurio", "Carve a curio from coral.",
             ("carve", "curiocraft")),
    _pending("tidepool", "The tide pool structure.",
             ("reef", "tidepools")),
    _pending("dock", "The dock structure.", ("pier", "fishingdock")),
    _pending("boathouse", "The boathouse structure.",
             ("moorings", "boat")),
    _pending("fishery", "The fishery structure.",
             ("hatchery", "fishfarm")),
)

MANIFEST = SubsystemManifest(
    key="fishing",
    version=1,
    commands=_COMMANDS,
    panels=(fishing_hub_spec(), _panels.cast_spec(), _panels.log_spec(),
            _panels.fishing_card_spec(), _panels.rod_shop_spec(),
            _panels.rod_recipes_spec(), _panels.bait_shop_spec()),
    settings=(),
    stores=(FISHING_CATCH_LOG_STORE, FISHING_ENERGY_STORE,
            FISHING_VENUE_STORE, FISHING_ROD_STORE, FISHING_BAIT_STORE),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.fishing import ops as _ops
    from sb.domain.fishing import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    _panels.ensure_panel_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
