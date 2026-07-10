"""HERMES subsystem manifest — the Discord→Claude-Code dispatch bridge
(shipped home disbot/cogs/hermes_cog.py: `/bugreport` + `/dispatch`, both
admin-gated slash-only commands, always deferred-ephemeral).

Owner ruling (rebuild walk 2026-07-05): the bridge is dropped from the new
bot's product roadmap — but the parity corpus pins its unconfigured-bridge
reply, so the surface exists here at parity fidelity: the config family
stays DORMANT (inert unless keyed) and the transmit lane is an honest
pending terminal (sb/domain/hermes/handlers.py)."""

from __future__ import annotations

from sb.domain.hermes import handlers as _handlers
from sb.domain.hermes import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import ReplyVisibility
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="hermes",
    version=1,
    commands=(
        CommandSpec(
            name="bugreport",
            kind=CommandKind.SLASH,          # shipped: app_commands only
            route=HandlerRef("hermes.bugreport"),
            summary="Report a bug — Hermes dispatches a Claude Code "
                    "session to fix it automatically.",
            usage="/bugreport <title> <description> [notes]",
            capability="hermes",
            # shipped: @app_commands.default_permissions(administrator=True)
            # + app_admin_or_owner() — the empty authority_ref ADMIN floor.
            reply_visibility=ReplyVisibility.EPHEMERAL,  # always ephemeral
        ),
        CommandSpec(
            name="dispatch",
            kind=CommandKind.SLASH,
            route=HandlerRef("hermes.dispatch"),
            summary="Send a raw Hermes work order to the Claude Code "
                    "Routine (owner only).",
            usage="/dispatch <work_order>",
            capability="hermes",
            reply_visibility=ReplyVisibility.EPHEMERAL,
        ),
    ),
    panels=(_panels.bridge_unconfigured_spec(),),
)


def _ensure_refs() -> None:
    _panels.ensure_hermes_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
