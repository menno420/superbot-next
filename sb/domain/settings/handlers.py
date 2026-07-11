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
