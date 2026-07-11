"""RPS subsystem manifest (band 6, wager-workflow family) — canonical key
``rps_tournament`` (shipped PR-3 display-rename strategy: user-facing
display is "Rock Paper Scissors"), the seven shipped commands verbatim,
the quick-play/PvP K7 lanes, the g1: session table, and the settings
slice (default_entry_fee persisted key + the shipped in-memory
default_mode/default_best_of made durable declarations)."""

from __future__ import annotations

from sb.domain.rps import handlers as _handlers
from sb.domain.rps import panels as _panels
from sb.domain.rps import tournament as _tournament
from sb.domain.rps.ops import register_ops
from sb.domain.rps.stats import RPS_PLAYERS_STORE
from sb.domain.rps.rules import GAME_MODES
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import SettingSpec


def _validate_mode(value: object) -> None:
    if value not in GAME_MODES:
        raise ValueError(f"invalid game mode {value!r}")


def _validate_best_of(value: object) -> None:
    if not isinstance(value, int) or value < 1 or value % 2 == 0:
        raise ValueError("default_best_of must be an odd positive integer")


_SETTINGS = (
    SettingSpec(
        name="default_entry_fee", value_type=int, default=0,
        settings_key="rps_default_entry_fee",
        capability_required="rps_tournament.tournament.manage",
        hint="Default entry fee (🪙 coins) applied when an admin runs "
             "`!rpsregister` without an explicit entry_fee argument.",
        input_hint="numeric_presets", presets=(0, 10, 25, 50, 100)),
    SettingSpec(
        name="default_mode", value_type=str, default="classic",
        settings_key="rps_default_mode",
        capability_required="rps_tournament.tournament.manage",
        hint="Tournament game mode when `!rpsstart` gets none "
             "(classic, lizard_spock, chess, elemental)."),
    SettingSpec(
        name="default_best_of", value_type=int, default=3,
        settings_key="rps_default_best_of",
        capability_required="rps_tournament.tournament.manage",
        hint="Best-of rounds when `!rpsstart` gets none "
             "(odd positive integer)."),
)

MANIFEST = SubsystemManifest(
    key="rps_tournament",
    version=1,
    commands=(
        CommandSpec(name="rps", kind=CommandKind.PREFIX,
                    route=HandlerRef("rps.play"),
                    audience_tier="user", capability="rps_tournament",
                    summary="Quick RPS — vs the bot, or challenge a "
                            "player (stakes escrowed at accept).",
                    usage="!rps [move] [bet] | !rps @player [bet]"),
        CommandSpec(name="rpsregister", kind=CommandKind.PREFIX,
                    aliases=("rpsreg",),
                    route=HandlerRef("rps.register_route"),
                    audience_tier="staff", capability="rps_tournament",
                    summary="Start tournament registration (button + "
                            "reaction sign-up).",
                    usage="!rpsregister [@role] [entry_fee]"),
        CommandSpec(name="rpsstart", kind=CommandKind.PREFIX,
                    aliases=("rpsbegin",),
                    route=HandlerRef("rps.start_route"),
                    audience_tier="staff", capability="rps_tournament",
                    summary="Start the registered RPS tournament.",
                    usage="!rpsstart [mode] [best_of]"),
        CommandSpec(name="rpsbot", kind=CommandKind.PREFIX,
                    route=HandlerRef("rps.bot_route"),
                    audience_tier="user", capability="rps_tournament",
                    summary="Start matches against the bot.",
                    usage="!rpsbot [mode] [best_of] [@members/@roles]"),
        CommandSpec(name="rpsmatchup", kind=CommandKind.PREFIX,
                    route=HandlerRef("rps.matchup_route"),
                    audience_tier="staff", capability="rps_tournament",
                    summary="Manually create a tournament match between "
                            "two members.",
                    usage="!rpsmatchup @player1 @player2"),
        CommandSpec(name="rpshelp", kind=CommandKind.PREFIX,
                    route=HandlerRef("rps.help_view"),
                    audience_tier="user", capability="rps_tournament",
                    summary="Show RPS command help.",
                    usage="!rpshelp"),
        CommandSpec(name="rpssettings", kind=CommandKind.PREFIX,
                    route=HandlerRef("rps.settings_view"),
                    audience_tier="staff", capability="rps_tournament",
                    summary="Update RPS settings (bare shows the current "
                            "values).",
                    usage="!rpssettings [setting] [value]"),
    ),
    panels=(_panels.rps_hub_spec(), _panels.rps_quickplay_spec(),
            _panels.rps_pvp_spec(), _panels.rps_registration_spec(),
            _panels.rps_match_spec()),
    settings=_SETTINGS,
    stores=(RPS_PLAYERS_STORE,),  # + checkpoint rows on the games manifest
    events=(),          # emits economy.balance_changed (owner: economy)
    capabilities=(),
)

register_ops()
_panels.register_rps_sessions()


def _ensure_refs() -> None:
    from sb.domain.rps import ops as _ops
    from sb.domain.rps import stats as _stats

    _stats.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _tournament.register_reaction_signup()
    register_ops()


ENSURE_REFS = _ensure_refs
