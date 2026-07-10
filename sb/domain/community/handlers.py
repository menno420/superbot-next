"""Community/leaderboard/spotlight read handlers (band 4) — thin
HandlerRef routes; everything reads the provider registry + spotlight
core. All read-only: no ops, no writes.
"""

from __future__ import annotations


from sb.spec.outcomes import SUCCESS
from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _category_from(req) -> str | None:
    """invoked-alias first (the shipped ctx.invoked_with rule), then the
    typed category argument."""
    from sb.domain.community.rank_providers import get_provider

    invoked = str(req.args.get("invoked_with", "") or
                  req.args.get("command", "") or "").lower()
    if invoked and invoked != "leaderboard" and get_provider(invoked):
        return invoked
    for token in tuple(req.args.get("argv", ()) or ()):
        if get_provider(str(token).lower()):
            return str(token).lower()
    return None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("leaderboard.board_view")):
        return

    @handler("leaderboard.board_view")
    async def board_view(req):
        """!leaderboard [category] (+ the shipped per-game aliases).

        No category → the shipped overview panel (embed + category
        selector — cogs/leaderboard_cog.py `_build_overview_embed` +
        `LeaderboardView`); a category argument or per-game alias
        pre-renders that board directly (the shipped route)."""
        from sb.domain.community.spotlight import provider_board_text
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        gid = int(req.guild_id or 0)
        category = _category_from(req)
        if category is None:
            await open_panel(PanelRef("leaderboard.board"), req)
            return None
        return Reply(SUCCESS, await provider_board_text(category, gid))

    @handler("leaderboard.category_view")
    async def category_view(req) -> Reply:
        """The board panel's category selector (args['values'])."""
        from sb.domain.community.spotlight import provider_board_text

        gid = int(req.guild_id or 0)
        values = tuple(req.args.get("values", ()) or ())
        category = str(values[0]) if values else "xp"
        return Reply(SUCCESS, await provider_board_text(category, gid))

    @handler("spotlight.xp_leaders")
    async def spotlight_xp_leaders(req) -> Reply:
        from sb.domain.community.spotlight import provider_board_text

        return Reply(SUCCESS,
                     await provider_board_text("xp", int(req.guild_id or 0)))

    @handler("spotlight.richest")
    async def spotlight_richest(req) -> Reply:
        from sb.domain.community.spotlight import provider_board_text

        return Reply(SUCCESS,
                     await provider_board_text("coins",
                                               int(req.guild_id or 0)))


_register()


def ensure_handler_refs() -> None:
    _register()
