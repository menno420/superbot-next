"""Server-management hub action terminals — the display-only Access
Map / Help Preview surfaces and the Help editor
(disbot/views/server_management/) are their own port slices; every hub
click on an unported surface lands on the declared + honest refusal
terminal (the role/utility-band precedent), never a silent stub. The
manager trio (Moderation / Roles / Cleanup — retired here by the
2026-07-13 curation rework) plus Channels and Setup forward to their
PORTED hub panels and live in panels.py. Refs register at MODULE
IMPORT (the composition-parity invariant — the live root never runs
ENSURE_REFS)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with its own manager slice."


def _register_pending() -> None:
    from sb.domain.operator_spine import pending_handler

    pending_handler("server_management.access_map_pending",
                    f"🔓 The Access Map display{_PENDING}")
    pending_handler("server_management.help_preview_pending",
                    f"👁 The Help Preview display{_PENDING}")
    pending_handler("server_management.help_editor_pending",
                    f"✏️ The Help editor{_PENDING}")


_register_pending()


def ensure_handler_refs() -> None:
    _register_pending()
