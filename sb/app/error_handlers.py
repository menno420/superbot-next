"""Composition-root error-handler registration (frozen L0 spec 02 §2/§6):
`tree.error` + `on_app_command_error` + the prefix `on_command_error`, each a
3-line shim into `from_exception`. Registered during host construction,
BEFORE gateway connect — the envelope is armed the instant the first
interaction arrives (closes the "31 slash commands, zero handler" gap).
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.errors import from_exception
from sb.kernel.interaction.request import Surface

logger = logging.getLogger("sb.app.error_handlers")

__all__ = ["register_error_handlers"]


def register_error_handlers(bot: object) -> None:
    """Wire the three shims onto the bot/tree (duck-typed; discord.py API)."""

    async def on_app_command_error(interaction: object, error: BaseException) -> None:
        envelope = from_exception(error, surface=Surface.SLASH, target=None)
        try:
            response = getattr(interaction, "response", None)
            if response is not None and not response.is_done():
                await response.send_message(envelope.user_message, ephemeral=True)
            else:
                await interaction.followup.send(envelope.user_message, ephemeral=True)
        except Exception:  # noqa: BLE001 — the handler never raises
            logger.warning("app-command error render failed", exc_info=True)

    async def on_command_error(ctx: object, error: BaseException) -> None:
        # CommandNotFound is the fuzzy adapter's input, not an error surface.
        if type(error).__name__ == "CommandNotFound":
            return
        envelope = from_exception(error, surface=Surface.PREFIX, target=None)
        try:
            await ctx.reply(envelope.user_message)
        except Exception:  # noqa: BLE001
            logger.warning("prefix error render failed", exc_info=True)

    tree = getattr(bot, "tree", None)
    if tree is not None:
        tree.error(on_app_command_error)        # tree.error registration
    adder = getattr(bot, "add_listener", None)
    if callable(adder):
        adder(on_command_error, "on_command_error")
