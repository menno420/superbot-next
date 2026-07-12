"""FOUR_TWENTY subsystem manifest (band 6, easter-egg family) — the shipped
🍃 420 surface verbatim (disbot/cogs/four_twenty_cog.py): ``!420`` (aliases
``fourtwenty`` / ``fourtwenty420``, shipped ``@commands.cooldown(rate=3,
per=10, user)``) opens the ``_FourTwentyPanelView`` overview; the passive
``FourTwentyStage`` per-message rule is
``sb.domain.four_twenty.service.handle_message`` (the MESSAGE FEED arms it
after the XP chat award — shipped pipeline order 50, the passive tier).

stores/events/settings are honestly EMPTY: the subsystem never wrote a row
or emitted a domain event (the golden's db_delta rows are the kernel
resolver's ai_decision_audit trace + the XP chat award — both other
subsystems' surfaces), so A-16 R2 is vacuous with zero exemptions (trap
15b: no dead tables).
"""

from __future__ import annotations

from sb.domain.four_twenty import handlers as _handlers
from sb.domain.four_twenty import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="four_twenty",
    version=1,
    commands=(
        CommandSpec(name="420", kind=CommandKind.PREFIX,
                    route=HandlerRef("four_twenty.panel_view"),
                    aliases=("fourtwenty", "fourtwenty420"),
                    audience_tier="user", capability="four_twenty",
                    cooldown=CooldownSpec(rate=3, per_s=10),
                    summary="Open the 🍃 420 panel — rotating wisdom and "
                            "number trivia.",
                    usage="!420"),
    ),
    panels=(_panels.four_twenty_overview_spec(),),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
