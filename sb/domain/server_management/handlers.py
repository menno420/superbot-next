"""Server-management hub action terminals — every shipped hub surface
is PORTED now: the manager trio (Moderation / Roles / Cleanup — retired
by the 2026-07-13 curation rework) plus Channels and Setup forward to
their hub panels in panels.py, and the display-only Access Map / Help
Preview surfaces and the Help editor forward to real panels
(access_map.py / help_preview.py / sb/domain/help/editor.py). No
pending terminals remain — a re-registration means a regression
re-parked a live surface (the nav-wiring retirement sweep pins their
absence). Refs register at MODULE IMPORT (the composition-parity
invariant — the live root never runs ENSURE_REFS)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def ensure_handler_refs() -> None:
    """Every hub surface forwards to a ported panel — nothing pending
    left to register (kept for the composition-parity call sites)."""
