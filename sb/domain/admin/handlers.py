"""Admin command handlers (band 2) — reads over the kernel truth sources;
restart through the K5 lifecycle seam."""

from __future__ import annotations

from sb.domain.operator_spine import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["ensure_handler_refs"]


def _manifests():
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg

    out = []
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda m: m.name):
        if info.ispkg or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"sb.manifest.{info.name}")
        manifest = getattr(module, "MANIFEST", None)
        if manifest is not None:
            out.append(manifest)
    return out


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("admin.subsystems_view")):
        return

    @handler("admin.subsystems_view")
    async def subsystems_view(req) -> Reply:
        # the `!coglist` truth source is now the manifest registry
        lines = []
        for m in _manifests():
            commands = len(getattr(m, "commands", ()) or ())
            panels = len(getattr(m, "panels", ()) or ())
            stores = len(getattr(m, "stores", ()) or ())
            lines.append(f"• **{m.key}** v{getattr(m, 'version', 1)} — "
                         f"{commands} command(s), {panels} panel(s), "
                         f"{stores} store(s)")
        return Reply(SUCCESS, "Loaded subsystems (manifest registry):\n"
                              + "\n".join(lines))

    @handler("admin.slash_inventory")
    async def slash_inventory(req) -> Reply:
        # `!slashes [scope]` — the shipped default scope is "guild"
        # (admin_cog.py `slashes`): the capture guild NEVER carried
        # guild-local registrations, so the shipped empty-branch copy is
        # the pinned reply (goldens/admin/sweep_slashes). The compiled
        # architecture registers slash commands in the GLOBAL tree only —
        # the guild-local registry is structurally empty forever, so the
        # shipped copy is the honest permanent read, not a stub. An
        # explicit non-guild scope falls through to the global-tree
        # inventory (the manifest registry — the honest analog of the
        # shipped global branch; no golden pins it).
        argv = tuple(req.args.get("argv", ()) or ())
        scope = str(argv[0]).lower() if argv else "guild"
        if scope == "guild":
            return Reply(SUCCESS,
                         "_No guild-local slash commands registered._ "
                         "Most slash commands may be in the global tree. "
                         "Use `!syncslash guild` to copy global commands "
                         "into this guild and sync them immediately.")
        names = []
        for m in _manifests():
            for cmd in getattr(m, "commands", ()) or ():
                if str(getattr(cmd, "kind", "")) in ("slash", "both"):
                    names.append(getattr(cmd, "qualified_name", cmd.name))
        names.sort()
        return Reply(SUCCESS, f"Slash surface ({len(names)}): "
                              + ", ".join(f"`/{n}`" for n in names))

    @handler("admin.loglevel")
    async def loglevel(req) -> Reply:
        import logging as _logging

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            level = _logging.getLogger("sb").getEffectiveLevel()
            return Reply(SUCCESS,
                         f"Current sb log level: {_logging.getLevelName(level)}")
        token = str(argv[0])
        # the shipped guard (admin_cog.py `loglevel`): getattr(logging,
        # level.upper()) — case-insensitive check, RAW token in the copy
        # (goldens/admin/sweep_loglevel pins "❌ Unknown level `test`. …").
        if token.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR",
                                 "CRITICAL"):
            return Reply(BLOCKED,
                         f"❌ Unknown level `{token}`. Choose from: DEBUG, "
                         "INFO, WARNING, ERROR, CRITICAL")
        _logging.getLogger("sb").setLevel(token.upper())
        return Reply(SUCCESS, f"sb log level → {token.upper()}.")

    @handler("admin.restart")
    async def restart(req) -> Reply:
        from sb.kernel import lifecycle

        lifecycle.request_restart(
            reason="admin command", actor=str(req.actor.user_id or "?"))
        return Reply(SUCCESS, "Restart requested — draining, then the "
                              "supervisor relaunches.")

    @handler("admin.serverstats_view")
    async def serverstats_view(req) -> Reply | None:
        # `!serverstats` — the shipped guild-census embed (admin_cog.py
        # `server_stats`: Total Members / Online Members / Text Channels /
        # Voice Channels / Roles over the gateway guild cache). The same
        # reads arrive through the utility guild-directory port (the
        # !serverinfo seam); uninstalled ⇒ the honest refusal.
        # goldens/admin/sweep_serverstats pins the bytes.
        import dataclasses as _dc

        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        try:
            info = await guild_directory().guild_info(int(req.guild_id or 0))
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, "ℹ️ Server stats need the live guild "
                                  "view (arms with the live adapter).")
        await open_panel(
            PanelRef("admin.server_stats"),
            _dc.replace(req, args={**dict(req.args), "stats": {
                "name": info.name,
                "member_count": info.member_count,
                "online_members": info.online_members,
                "text_channels": info.text_channels,
                "voice_channels": info.voice_channels,
                "roles": info.roles,
            }}))
        return None

    # the shipped Reload All button reloaded every discord.py extension
    # in-process — deploy-ops (the _sweep_skips unloadall class), so the
    # hub click lands on the declared + honest pending terminal (the
    # server_management precedent; no golden drives the click).
    from sb.domain.operator_spine import pending_handler

    pending_handler("admin.reload_all_pending",
                    "🔄 Reload All is deploy-ops in the compiled "
                    "architecture — subsystems recompile at boot, not "
                    "in-process.")


_register()


def ensure_handler_refs() -> None:
    _register()
