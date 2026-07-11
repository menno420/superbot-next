"""STARBOARD subsystem manifest (the `_unmapped` starboard-family
re-home; NEW subsystem birth) — the shipped `!starboard` config command
group verbatim (cogs/starboard_cog.py: the invoke_without_command root +
ignore/unignore/off/selfstar/panel subcommands, every one
``perms_or_owner(manage_guild=True)`` ⇒ tier "staff") over the
starboard_settings/starboard_ignore_channels stores (migration 0033) and
the K7 config ops (sb/domain/starboard/ops.py).

Under-port boundary (sb/domain/starboard/service.py): the
reaction-listener pipeline (`on_raw_reaction_add/remove` →
handle_star_change → the `starboard_entries` table) lands with the
reaction-surfaces slice — no golden pins a reaction step.
"""

from __future__ import annotations

from sb.domain.starboard import handlers as _handlers
from sb.domain.starboard import panels as _panels
from sb.domain.starboard.ops import ensure_ops_refs, register_ops
from sb.domain.starboard.panels import install_starboard_panels
from sb.domain.starboard.store import (
    STARBOARD_IGNORE_STORE,
    STARBOARD_SETTINGS_STORE,
)
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, *, group: str = "",
         aliases: tuple[str, ...] = (), summary: str,
         usage: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=route, aliases=aliases, audience_tier="staff",
                       capability="starboard", summary=summary, usage=usage)


_COMMANDS = (
    # @commands.group(name="starboard", invoke_without_command=True): bare
    # shows the config, argful sets channel + threshold —
    # goldens/starboard/sweep_starboard pins the off-state status byte.
    _cmd("starboard", HandlerRef("starboard.root"),
         summary="Show or set the hall-of-fame channel + star threshold.",
         usage="!starboard [#channel] [threshold]"),
    _cmd("ignore", HandlerRef("starboard.ignore"), group="starboard",
         summary="Keep a channel's messages off the starboard.",
         usage="!starboard ignore #channel"),
    _cmd("unignore", HandlerRef("starboard.unignore"), group="starboard",
         summary="Let a channel's messages onto the starboard again.",
         usage="!starboard unignore #channel"),
    _cmd("off", HandlerRef("starboard.off"), group="starboard",
         summary="Disable the starboard.",
         usage="!starboard off"),
    _cmd("selfstar", HandlerRef("starboard.selfstar"), group="starboard",
         summary="Count the author's own ⭐ toward the threshold?",
         usage="!starboard selfstar on|off"),
    _cmd("panel", PanelRef("starboard.config"), group="starboard",
         summary="Open the interactive starboard config panel.",
         usage="!starboard panel"),
)

MANIFEST = SubsystemManifest(
    key="starboard",
    version=1,
    commands=_COMMANDS,
    panels=install_starboard_panels(),
    settings=(),
    stores=(STARBOARD_SETTINGS_STORE, STARBOARD_IGNORE_STORE),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.starboard import store as _store

    _handlers.ensure_handler_refs()
    _panels.ensure_panel_refs()
    install_starboard_panels()
    ensure_ops_refs()
    _store.ensure_refs()


ENSURE_REFS = _ensure_refs
