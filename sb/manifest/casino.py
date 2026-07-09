"""CASINO subsystem manifest (band 6) — the shipped hub + poker
declarations (parity key `casino`): !casino opens the hub; !poker
(alias holdem) is DECLARED with the multiplayer-ephemeral-table
orchestration riding the live adapter (the pure card model + hand
evaluator are aboard — D-0045)."""

from __future__ import annotations

from sb.domain.casino import panels as _panels
from sb.domain.casino import service as _service
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

MANIFEST = SubsystemManifest(
    key="casino",
    version=1,
    commands=(
        CommandSpec(name="casino", kind=CommandKind.PREFIX,
                    route=PanelRef("casino.hub"),
                    audience_tier="user", capability="casino",
                    summary="Open the Casino hub — group card games "
                            "like poker.",
                    usage="!casino"),
        CommandSpec(name="poker", kind=CommandKind.PREFIX,
                    aliases=("holdem",),
                    route=HandlerRef("casino.poker_pending"),
                    audience_tier="user", capability="casino",
                    summary="Open a multiplayer Texas Hold'em table in "
                            "this channel.",
                    usage="!poker"),
    ),
    panels=(_panels.casino_hub_spec(),),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
