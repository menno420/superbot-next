"""DEATHMATCH subsystem manifest (band 6, PvP family) — the shipped
duel game on the blackjack-PvP g1 recipe: dm_challenge (+ the three
shipped fluency aliases) and dm_help (the hub rides the games.world
nav — shipped reached it via the Games hub hook, no typed command); deathmatch_stats (PvP only);
the turn_timeout SettingSpec (shipped schemas.py verbatim);
DeathmatchProvider + RpsProvider register here (their stat stores land
in this slice)."""

from __future__ import annotations

from sb.domain.deathmatch import panels as _panels
from sb.domain.deathmatch import service as _service
from sb.domain.deathmatch.ops import register_ops
from sb.domain.deathmatch.store import DEATHMATCH_STATS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef
from sb.spec.settings import SettingSpec

_SETTINGS = (
    SettingSpec(
        name="turn_timeout", value_type=int, default=60,
        settings_key="deathmatch_turn_timeout",
        capability_required="deathmatch.game.challenge",
        hint="Seconds each player has to respond on their turn before "
             "the duel times out and the opponent wins by default.",
        input_hint="numeric_presets", presets=(30, 60, 120, 300)),
)

MANIFEST = SubsystemManifest(
    key="deathmatch",
    version=1,
    commands=(
        CommandSpec(name="dm_challenge", kind=CommandKind.PREFIX,
                    aliases=("deathmatch", "challenge", "dm"),
                    route=HandlerRef("deathmatch.challenge_route"),
                    audience_tier="user", capability="deathmatch",
                    summary="Challenge another user to a deathmatch "
                            "duel.",
                    usage="!deathmatch @user"),
        CommandSpec(name="dm_help", kind=CommandKind.PREFIX,
                    aliases=("deathmatch_help",),
                    route=HandlerRef("deathmatch.help_view"),
                    audience_tier="user", capability="deathmatch",
                    summary="Deathmatch commands + how duels work.",
                    usage="!dm_help"),
    ),
    panels=(_panels.deathmatch_hub_spec(),),
    settings=_SETTINGS,
    stores=(DEATHMATCH_STATS_STORE,),
    events=(),
    capabilities=(),
)

register_ops()
_panels.register_deathmatch_sessions()
_service.register_provider_rows()


def _ensure_refs() -> None:
    from sb.domain.deathmatch import ops as _ops
    from sb.domain.deathmatch import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    _service.register_provider_rows()
    register_ops()


ENSURE_REFS = _ensure_refs
