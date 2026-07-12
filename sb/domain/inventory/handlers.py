"""Inventory read handlers (band 3) — `!inventory [@user]` opens the
shipped unified inventory hub (disbot/cogs/inventory_cog.py: ``target =
member or ctx.author`` → ``UnifiedInventoryView`` + ``build_hub_embed``),
presented through the declarative panel engine (the economy wallet-card
open_panel pattern); parity/goldens/inventory/sweep_inventory.json pins
the empty-state bytes."""

from __future__ import annotations


from sb.spec.outcomes import SUCCESS
from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _target_id(req) -> int:
    """Optional member arg (mention/id) else the invoker — the shipped
    ``member: discord.Member = None`` converter parameter. Snowflake-length
    guard: the shipped MemberConverter never resolved short numerics as
    member ids (`!inventory 1` raised MemberNotFound), so a sub-snowflake
    token falls back to the invoker rather than inventing a target."""
    argv = tuple(req.args.get("argv", ()) or ())
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit() and len(stripped) >= 15:
            return int(stripped)
    return int(getattr(req.actor, "user_id", 0) or 0)


def _author_display(req) -> tuple[str, str]:
    """(display name, avatar url) for the invoking member — the shipped
    ``target.display_name`` / ``target.display_avatar.url`` pair, duck-typed
    over the surface origin (the economy !balance precedent). Members
    without a custom avatar get discord's default-avatar URL (index
    ``(id >> 22) % 6``)."""
    origin = getattr(req, "origin", None)
    member = (getattr(origin, "author", None)
              or getattr(origin, "user", None))
    uid = int(getattr(member, "id", 0) or getattr(req.actor, "user_id", 0)
              or 0)
    name = (str(getattr(member, "display_name", "") or "")
            or str(getattr(member, "name", "") or "") or f"<@{uid}>")
    icon = str(getattr(getattr(member, "display_avatar", None), "url", "")
               or "")
    if not icon:
        icon = f"https://cdn.discordapp.com/embed/avatars/{(uid >> 22) % 6}.png"
    return name, icon


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("inventory.view")):
        return

    @handler("inventory.view")
    async def inventory_view(req) -> Reply:
        """!inventory [@user] — the shipped hub open: build the combined
        inventory for the target and present the hub panel (title, gold
        accent, avatar thumbnail, footer literal and the per-non-empty-
        category buttons live in the panel's renderer_override)."""
        import dataclasses

        from sb.domain.inventory.panels import _member_display
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        gid = int(req.guild_id or 0)
        invoker = int(getattr(req.actor, "user_id", 0) or 0)
        target = _target_id(req)
        if target == invoker:
            name, icon = _author_display(req)
        else:
            name, icon = await _member_display(target, gid)
            if not name:
                name = f"<@{target}>"
        hub_req = dataclasses.replace(
            req, args={**dict(req.args), "inv_target": target,
                       "inv_name": name, "inv_icon": icon})
        await open_panel(PanelRef("inventory.hub"), hub_req)
        return Reply(SUCCESS, None)


_register()


def ensure_handler_refs() -> None:
    _register()
