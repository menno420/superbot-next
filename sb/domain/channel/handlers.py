"""Channel hub action terminals — the shipped sub-panels
(disbot/views/channels/: create/delete/restrict/move/visibility) are the
channel-ops Discord-mutation slice (D-0030, the named successor); every
hub click lands on the declared + honest refusal terminal (the
role/utility-band precedent), never a silent stub. Refs register at
MODULE IMPORT (the composition-parity invariant — the live root never
runs ENSURE_REFS)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with the channel-ops slice (D-0030)."


def _register_pending() -> None:
    from sb.domain.operator_spine import pending_handler

    pending_handler("channel.create_pending",
                    f"➕ The interactive channel creator{_PENDING}")
    pending_handler("channel.delete_pending",
                    f"🗑️ The channel delete picker{_PENDING}")
    pending_handler("channel.restrict_pending",
                    f"🔒 The lock/unlock restriction panel{_PENDING}")
    pending_handler("channel.move_pending",
                    f"↔️ The move/reorder panel{_PENDING}")
    pending_handler("channel.visibility_pending",
                    f"🔍 The subsystem-visibility panel{_PENDING}")


_register_pending()


def ensure_handler_refs() -> None:
    _register_pending()
