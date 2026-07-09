"""Inventory read handlers (band 3) — the `!inventory` unified browser as a
projection-first text view; the category detail views (paging, type filter,
sort cycle) ride the panel-action slice with the shipped pure helpers
already in sb/domain/inventory/service.py."""

from __future__ import annotations


from sb.spec.outcomes import SUCCESS
from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("inventory.view")):
        return

    @handler("inventory.view")
    async def inventory_view(req) -> Reply:
        from sb.domain.inventory import service

        argv = tuple(req.args.get("argv", ()) or ())
        target = int(getattr(req.actor, "user_id", 0) or 0)
        for token in argv:                      # shipped: optional member arg
            stripped = str(token).strip("<@!>")
            if stripped.isdigit() and len(stripped) >= 15:
                target = int(stripped)
                break
        grouped = await service.build_combined_inventory(
            target, int(req.guild_id or 0))
        lines = [f"🎒 **<@{target}>'s Inventory**"]
        lines.extend(service.render_hub_lines(grouped))
        return Reply(SUCCESS, "\n".join(lines))


_register()


def ensure_handler_refs() -> None:
    _register()
