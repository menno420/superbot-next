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
        token = str(argv[0]).upper()
        if token not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return Reply(BLOCKED, "Level must be DEBUG/INFO/WARNING/ERROR/CRITICAL.")
        _logging.getLogger("sb").setLevel(token)
        return Reply(SUCCESS, f"sb log level → {token}.")

    @handler("admin.restart")
    async def restart(req) -> Reply:
        from sb.kernel import lifecycle

        lifecycle.request_restart(
            reason="admin command", actor=str(req.actor.user_id or "?"))
        return Reply(SUCCESS, "Restart requested — draining, then the "
                              "supervisor relaunches.")

    @handler("admin.serverstats_view")
    async def serverstats_view(req) -> Reply:
        # guild-census stats need the gateway cache — the guild-info port
        # arms with the composition root (declared, honest refusal).
        return Reply(BLOCKED, "Server stats need the live gateway cache — "
                              "not armed in this build yet.")

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
