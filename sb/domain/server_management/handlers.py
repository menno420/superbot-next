"""Server-management hub action terminals — the shipped specialised
managers (moderation / roles / cleanup — the manager panels the hub
routes into via ``build_help_menu_view``; the display-only Help Preview
surface and the Help editor — disbot/views/server_management/ +
views/help/editor.py) are their own port slices; every hub click on an
unported manager lands on the declared + honest refusal terminal (the
role/utility-band precedent), never a silent stub. The Channels, Setup
and Access Map buttons forward to real panels and live in panels.py /
access_map.py. Refs register at MODULE IMPORT (the composition-parity
invariant — the live root never runs ENSURE_REFS)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with its own manager slice."


def _register_pending() -> None:
    from sb.domain.operator_spine import pending_handler

    pending_handler("server_management.moderation_pending",
                    f"🛡️ The Moderation manager{_PENDING}")
    pending_handler("server_management.roles_pending",
                    f"🎭 The Roles manager{_PENDING}")
    pending_handler("server_management.cleanup_pending",
                    f"🧹 The Cleanup manager{_PENDING}")
    pending_handler("server_management.help_preview_pending",
                    f"👁 The Help Preview display{_PENDING}")
    pending_handler("server_management.help_editor_pending",
                    f"✏️ The Help editor{_PENDING}")


_register_pending()


def ensure_handler_refs() -> None:
    _register_pending()
