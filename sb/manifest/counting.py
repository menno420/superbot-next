"""COUNTING subsystem manifest (band 6, message-game family) — the
shipped 10-command surface verbatim over the counting_state blob;
the on_message hot path is the ``counting.record_count`` lane (the
MESSAGE FEED arms with the live adapter). CountingProvider registers
here (alias countlb / counting_leaderboard)."""

from __future__ import annotations

from sb.domain.counting import panels as _panels
from sb.domain.counting import service as _service
from sb.domain.counting.ops import register_ops
from sb.domain.counting.store import COUNTING_STATE_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, summary: str, aliases: tuple[str, ...] = (),
         tier: str = "user") -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       aliases=aliases, route=route, audience_tier=tier,
                       capability="counting", summary=summary,
                       usage=f"!{name}")


_COMMANDS = (
    _cmd("countingmenu", PanelRef("counting.hub"),
         "Open the counting management panel.", ("cm",)),
    _cmd("start_match", HandlerRef("counting.start_match_route"),
         "Start a counting match: !start_match <mode> [args].",
         ("sm",), tier="staff"),
    _cmd("end_match", HandlerRef("counting.end_match_route"),
         "End the counting match in a channel.", ("em",), tier="staff"),
    _cmd("reset_count", HandlerRef("counting.reset_route"),
         "Reset a counting channel to its starting state.", ("rc",),
         tier="staff"),
    _cmd("toggle_turns", HandlerRef("counting.toggle_turns_route"),
         "Toggle the no-counting-twice-in-a-row rule.", ("tt",),
         tier="staff"),
    _cmd("count_info", HandlerRef("counting.info_view"),
         "Show a counting channel's mode + state.", ("ci",)),
    _cmd("counttop", HandlerRef("counting.top_view"),
         "This channel's top counters.", ("ct", "counting_top")),
    # the shipped count_rules sent the static rules EMBED
    # (cogs/counting_cog.py — goldens/counting/sweep_count_rules pins the
    # bytes); counting.rules_view stays a registered text read surface.
    _cmd("count_rules", PanelRef("counting.rules_card"),
         "The counting rules.", ("cr",)),
    _cmd("set_skip_numbers", HandlerRef("counting.set_skip_route"),
         "Set the skip step for a 'skip' match.", ("ssn",),
         tier="staff"),
    _cmd("toggle_reset_on_wrong_count",
         HandlerRef("counting.toggle_reset_route"),
         "Toggle reset-to-start on a wrong count.", ("trwc",),
         tier="staff"),
)

MANIFEST = SubsystemManifest(
    key="counting",
    version=1,
    commands=_COMMANDS,
    panels=(_panels.counting_hub_spec(), _panels.rules_card_spec()),
    settings=(),
    stores=(COUNTING_STATE_STORE,),
    events=(),
    capabilities=(),
)

register_ops()
_service.register_provider_rows()


def _ensure_refs() -> None:
    from sb.domain.counting import ops as _ops

    from sb.domain.counting import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    _service.register_provider_rows()
    register_ops()


ENSURE_REFS = _ensure_refs
