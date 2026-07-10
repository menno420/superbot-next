"""BLACKJACK subsystem manifest (band 6, wager-workflow family) — the
shipped commands verbatim (blackjack/bj, bjtournament/bjtourn, bjstart,
bjstatus), the solo/PvP K7 lanes over the games-substrate checkpoint
store, the D1 escrow flow, and the g1: dynamic-session action table.
Checkpoint rows live in the GAMES manifest's game_state store."""

from __future__ import annotations

from sb.domain.blackjack import handlers as _handlers
from sb.domain.blackjack import panels as _panels
from sb.domain.blackjack.ops import register_ops
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import SettingSpec

_SETTINGS = (
    SettingSpec(
        name="default_entry_fee", value_type=int, default=0,
        settings_key="blackjack_default_entry_fee",
        capability_required="blackjack.tournament.manage",
        hint="Default entry fee (🪙 coins) applied when an admin runs "
             "`!bjtournament` without an explicit entry_fee argument.",
        input_hint="numeric_presets", presets=(0, 10, 25, 50, 100)),
)

MANIFEST = SubsystemManifest(
    key="blackjack",
    version=1,
    commands=(
        CommandSpec(name="blackjack", kind=CommandKind.PREFIX,
                    aliases=("bj",), route=HandlerRef("blackjack.play"),
                    audience_tier="user", capability="blackjack",
                    summary="Play blackjack — solo vs the dealer, or "
                            "challenge a player (stakes escrowed).",
                    usage="!blackjack [bet] | !blackjack @player [bet]"),
        CommandSpec(name="bjtournament", kind=CommandKind.PREFIX,
                    aliases=("bjtourn",),
                    route=HandlerRef("blackjack.tournament_open_pending"),
                    audience_tier="staff", capability="blackjack",
                    summary="Start a Blackjack tournament "
                            "(registration + private round channels).",
                    usage="!bjtournament [entry_fee] [rounds] [mins]"),
        CommandSpec(name="bjstart", kind=CommandKind.PREFIX,
                    route=HandlerRef("blackjack.tournament_start_pending"),
                    audience_tier="staff", capability="blackjack",
                    summary="Manually start a pending Blackjack "
                            "tournament early.",
                    usage="!bjstart"),
        CommandSpec(name="bjstatus", kind=CommandKind.PREFIX,
                    route=HandlerRef("blackjack.status_view"),
                    audience_tier="user", capability="blackjack",
                    summary="Show the current tournament status.",
                    usage="!bjstatus"),
    ),
    panels=(_panels.blackjack_hub_spec(), _panels.blackjack_table_spec()),
    settings=_SETTINGS,
    stores=(),          # checkpoint rows ride the games manifest's stores
    events=(),          # emits economy.balance_changed (owner: economy)
    capabilities=(),
)

register_ops()
_panels.register_blackjack_sessions()


def _ensure_refs() -> None:
    from sb.domain.blackjack import ops as _ops

    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
