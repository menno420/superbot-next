"""Settings-surface handlers — the ``!settings access`` front door plus
the declared + honest pending terminals for every hub/explorer click
whose target is its own port slice (the role/utility/channel-band
precedent, never a silent stub): the per-group settings pages
(``settings_subsystem.*``), the four diagnostic sub-panels
(``settings_needs_setup.back`` family), the Command Access panel
(``settings_command_access.*``, PR-6), and the explorer's live legs
(``governance.resolve_subsystem_state`` reads, scope/paging state).
Refs register at MODULE IMPORT (the composition-parity invariant — the
live root never runs ENSURE_REFS)."""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with the settings-mutation panel slice."

#: settings groups whose page is a REAL dedicated panel that is NOT the
#: operator-spine ``<group>.hub`` shape — ``games.hub`` is the PLAYER games
#: hub (band 6 parity flip), so the D-0082 §5 sections settings surface
#: lives at its own id and the group select routes here first.
_GROUP_PANELS: dict[str, str] = {
    "games": "games.sections",
}


def _display_name(req) -> str:
    """The invoking member's display name (the shipped ``ctx.author``
    read — the economy author-display / rps precedent)."""
    user = getattr(req.origin, "author", None) or getattr(req.origin, "user", None)
    name = (getattr(user, "display_name", None)
            or getattr(user, "name", None))
    return str(name) if name else "unknown"


def _register() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.spec.refs import HandlerRef, handler, is_registered

    pending_handler("settings.group_pending",
                    f"⚙️ The per-group settings page{_PENDING}")
    pending_handler("settings.needs_setup_pending",
                    f"📋 The Needs-setup diagnostic{_PENDING}")
    pending_handler("settings.invalid_pending",
                    f"⚠️ The Invalid-settings diagnostic{_PENDING}")
    pending_handler("settings.missing_bindings_pending",
                    f"🔗 The Missing-bindings diagnostic{_PENDING}")
    pending_handler("settings.audit_pending",
                    f"🕒 The Recent-changes audit view{_PENDING}")
    pending_handler("settings.command_access_pending",
                    f"🚪 The Command Access panel{_PENDING}")
    pending_handler("settings.access_subsystem_pending",
                    "🔍 The explorer's subsystem selection ports with the "
                    "governance-diagnostic slice.")
    pending_handler("settings.access_scope_pending",
                    "🔍 The explorer's scope selection ports with the "
                    "governance-diagnostic slice.")
    pending_handler("settings.access_explain_pending",
                    "🔬 Explain Access ports with the governance-diagnostic "
                    "slice (governance.resolve_subsystem_state).")
    pending_handler("settings.access_reset_pending",
                    "🔄 The explorer reset ports with the "
                    "governance-diagnostic slice.")
    pending_handler("settings.access_page_pending",
                    "🔍 The explorer's subsystem paging ports with the "
                    "governance-diagnostic slice.")

    if is_registered(HandlerRef("settings.access_view")):
        return

    @handler("settings.open_group")
    async def open_group(req):
        """The Settings-hub "Open a settings group…" select — the shipped
        ``SettingsHubView`` group select NAVIGATED (read-only, never a
        mutation) to each group's page. Restore that navigation as a
        faithful READ SUBSET: open the group's read-only operator-spine hub
        when one is ensured (welcome/counters/security/automod/
        image_moderation) or the group's dedicated settings panel
        (``_GROUP_PANELS`` — the D-0082 games sections surface); every
        other group keeps the honest pending terminal until the
        settings-mutation panel slice ports the full edit page. This
        handler only NAVIGATES — open_panel or BLOCKED, never a write
        seam (mirrors ``help.open_category``); the games sections panel's
        own components carry the mutations."""
        from sb.domain.operator_spine import has_operator_hub
        from sb.kernel.panels.engine import open_panel
        from sb.spec.outcomes import BLOCKED
        from sb.spec.refs import PanelRef

        values = tuple(req.args.get("values", ()) or ())
        group = str(values[0]) if values else ""
        if group in _GROUP_PANELS:
            await open_panel(PanelRef(_GROUP_PANELS[group]), req)
            return None
        if group and has_operator_hub(group):
            await open_panel(PanelRef(f"{group}.hub"), req)
            return None
        # the per-group scalar edit + reset is the settings-mutation slice's
        # port (write-seam-gated) — read-only nav lands here until then.
        return Reply(BLOCKED, f"⚙️ The per-group settings page{_PENDING}")

    @handler("settings.access_view")
    async def access_view(req):
        """``!settings access`` — open the shipped Access Policy Explorer
        (goldens/settings/sweep_settings_access). The invoker's display
        name rides the request args so the renderer override can stamp
        the shipped author-lock footer (the economy author-display
        precedent)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(
            PanelRef("settings.access"),
            dataclasses.replace(req, args={**dict(req.args),
                                           "invoker_name": _display_name(req)}))
        return None


_register()


def ensure_handler_refs() -> None:
    _register()
