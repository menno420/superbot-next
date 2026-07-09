"""FISHING subsystem manifest (band 6, checkpoint family) — the FULL
shipped command surface verbatim (20 commands): the core cast + dex/
trophy/leaderboard reads are live; gear/venue/craft/structure surfaces
are honest pending terminals riding the D-0043 named successor port."""

from __future__ import annotations

from sb.domain.fishing import service as _service
from sb.domain.fishing.ops import register_ops
from sb.domain.fishing.store import FISHING_CATCH_LOG_STORE
from sb.kernel.panels.registry import register_panel
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel


def fishing_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="fishing.hub",
        subsystem="fishing",
        title="🎣 Fishing",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock("Cast a line — 21 species across 7 size bands; "
                        "level up to unlock bigger fish. Caught fish "
                        "land in your pack (sell or cook them); the "
                        "biggest of each species is your trophy."),),
        actions=(
            PanelActionSpec(action_id="fishing_cast", label="Cast",
                            emoji="🎣", style=ActionStyle.SUCCESS,
                            audience_tier="user",
                            handler=HandlerRef("fishing.fish_route"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="fishing_log", label="Fish Dex",
                            emoji="📖", audience_tier="user",
                            handler=HandlerRef("fishing.log_view"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="fishing_trophies",
                            label="Trophies", emoji="🏆",
                            audience_tier="user",
                            handler=HandlerRef("fishing.trophies_view"),
                            result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.world")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("fishing_cast", "fishing_log", "fishing_trophies"),)),)),
    )


@panel("fishing.hub")
def _hub_factory() -> PanelSpec:
    return fishing_hub_spec()


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
    _cmd("fish", HandlerRef("fishing.fish_route"),
         "Cast a line — one instant catch roll."),
    _cmd("fishing", PanelRef("fishing.hub"), "Open the fishing hub.",
         ("fishmenu",)),
    _cmd("fishlog", HandlerRef("fishing.log_view"),
         "Your fish dex — every species you've caught.", ("fishdex",)),
    _cmd("fishtop", HandlerRef("fishing.top_view"),
         "Top anglers by total catches.", ("topfishers",)),
    _cmd("trophies", HandlerRef("fishing.trophies_view"),
         "Trophy records — the biggest catches.",
         ("bigfish", "fishtrophy")),
    # --- gear/venue/craft systems (the D-0043 named successor port) -------
    _pending("forecast", "Today's fishing weather.",
             ("fishforecast", "fishingweather")),
    _pending("sail", "Set sail to the deepwater venue.", ("setsail",)),
    _pending("rod", "The rod shop.", ("rodshop", "buyrod")),
    _pending("bait", "The bait shop.", ("baitshop", "buybait")),
    _pending("craftbait", "Craft bait from fish.", ("baitcraft",)),
    _pending("craftcharm", "Craft a fishing charm.", ("charmcraft",)),
    _pending("craftrod", "Craft a rod.", ("rodcraft",)),
    _pending("rodrecipes", "Rod crafting recipes.",
             ("rodrecipe", "rrecipes")),
    _pending("craftpearl", "Craft pearl bait.", ("pearlcraft",)),
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
    panels=(fishing_hub_spec(),),
    settings=(),
    stores=(FISHING_CATCH_LOG_STORE,),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.fishing import ops as _ops
    from sb.domain.fishing import store as _store
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    if not is_registered(_P("fishing.hub")):
        _panel("fishing.hub")(_hub_factory)
    register_ops()


ENSURE_REFS = _ensure_refs
