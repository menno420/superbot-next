"""App-command registration (CUT-1, completion-report flag 30): populate
``bot.tree`` from the LIVE manifests and offer the GUILD-scoped sync leg.

The tree is built from the same truth dispatch resolves on (D-0050: the
live manifest ``CommandSpec`` objects, kind-partitioned per §2.2 — every
``kind in ("slash", "both")`` spec becomes one app command, groups via the
spec's ``group`` path exactly like ``qualified_name``/the snapshot's
``parent_group``). Every callback funnels through
``sb.kernel.interaction.adapters.slash.dispatch_interaction`` — the no-skip
fence (spec 02 §7) stays intact; ``CommandSpec`` declares no option facet,
so commands register parameterless (typed slash options are a named
successor; the handlers read ``argv``-style args today).

Sync posture (boot-gate leg C, spec 01 §3.3-§3.4): GLOBAL sync stays
compare-only in the test-mode root — the remote app still carries the OLD
bot's global commands and a global ``tree.sync()`` would replace them ahead
of the CUT-3 cutover. The safe leg is :func:`sync_guild_commands`:
``copy_global_to`` + ``sync(guild=...)`` writes GUILD-scoped commands to
the TEST guild only and never touches the global set. The composition root
gates it on ``SB_DATA_PLANE=test`` + the explicit ``SB_APPCMD_SYNC_GUILD_ID``
opt-in.

Import-guarded like every discord adapter (discord absent in CI containers
by design).
"""

from __future__ import annotations

import logging

logger = logging.getLogger("sb.adapters.discord.command_tree")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
    from discord import app_commands

    DISCORD_AVAILABLE = True
except ImportError:
    discord = None        # type: ignore[assignment]
    app_commands = None   # type: ignore[assignment]
    DISCORD_AVAILABLE = False

__all__ = [
    "DISCORD_AVAILABLE",
    "register_app_commands",
    "slash_description",
    "sync_guild_commands",
]

#: Discord's hard cap on an app-command description.
_DESCRIPTION_MAX = 100


def slash_description(spec: object) -> str:
    """The spec's ``summary`` clipped to Discord's 1..100 bound (empty
    summaries fall back to the command name — description is required)."""
    text = str(getattr(spec, "summary", "") or "").strip()
    if not text:
        text = str(getattr(spec, "name", "") or "command")
    if len(text) > _DESCRIPTION_MAX:
        text = text[: _DESCRIPTION_MAX - 1] + "…"
    return text


def _make_callback():
    """One dispatch funnel per command: interaction → InteractionResponder →
    dispatch_interaction → resolve() (the ONLY path, spec 02 §7)."""
    from sb.adapters.discord.responders import InteractionResponder
    from sb.kernel.interaction.adapters.slash import dispatch_interaction
    from sb.kernel.interaction.request import Surface

    async def callback(interaction) -> None:  # noqa: ANN001 — discord.Interaction
        responder = InteractionResponder(interaction, surface=Surface.SLASH)
        await dispatch_interaction(interaction, responder=responder)

    return callback


def register_app_commands(bot: object, manifests: list) -> int:
    """Populate ``bot.tree`` with one app command per slash-surface
    CommandSpec across the LIVE manifests (kind in ("slash", "both")).
    Groups follow the spec's ``group`` path (dots nest, mirroring
    ``qualified_name``). Returns the number of leaf commands added."""
    if not DISCORD_AVAILABLE:
        raise RuntimeError("discord is not installed — no app commands in this container")
    tree = bot.tree
    groups: dict[str, object] = {}

    def _group_for(path: str) -> object:
        node = groups.get(path)
        if node is not None:
            return node
        parts = path.split(".")
        name = parts[-1]
        node = app_commands.Group(
            name=name, description=f"{name} commands")
        groups[path] = node
        if len(parts) > 1:
            _group_for(".".join(parts[:-1])).add_command(node)
        else:
            tree.add_command(node)
        return node

    count = 0
    for manifest in manifests:
        for cmd in getattr(manifest, "commands", ()) or ():
            name = str(getattr(cmd, "name", "") or "")
            kind = str(getattr(cmd, "kind", "") or "")
            if not name or kind not in ("slash", "both"):
                continue
            command = app_commands.Command(
                name=name,
                description=slash_description(cmd),
                callback=_make_callback(),
            )
            group_path = str(getattr(cmd, "group", "") or "")
            if group_path:
                _group_for(group_path).add_command(command)
            else:
                tree.add_command(command)
            count += 1
    return count


async def sync_guild_commands(bot: object, guild_id: int) -> tuple[str, ...]:
    """The SAFE sync leg: copy the local tree's global commands into the
    guild's scope and sync THAT guild only — the remote GLOBAL command set
    (the old bot's, until CUT-3) is never written. Returns the synced
    command names (sorted) for the boot log/evidence."""
    if not DISCORD_AVAILABLE:
        raise RuntimeError("discord is not installed — no app commands in this container")
    guild = discord.Object(id=int(guild_id))
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    return tuple(sorted(str(c.name) for c in synced))
