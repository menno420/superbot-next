"""Concrete `SurfaceResponder` implementations (frozen L0 spec 02 §2) — the
ONLY modules that touch `discord.Interaction` / `discord.Message`.

Duck-typed against the discord.py API so the module imports cleanly without
the discord package (the objects arrive from the gateway at runtime).
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.request import ConfirmPrompt, Surface
from sb.spec.outcomes import ReplyVisibility

logger = logging.getLogger("sb.adapters.discord.responders")

__all__ = ["InteractionResponder", "MessageResponder"]


class InteractionResponder:
    """Wraps a `discord.Interaction` (slash / component / modal)."""

    def __init__(self, interaction: object, *, surface: Surface = Surface.SLASH):
        self._interaction = interaction
        self.surface = surface
        self._committed: ReplyVisibility | None = None

    def is_acked(self) -> bool:
        response = getattr(self._interaction, "response", None)
        return bool(response is not None and response.is_done())

    def committed_visibility(self) -> ReplyVisibility | None:
        return self._committed

    async def ack(self, *, ephemeral: bool) -> None:
        await self._interaction.response.defer(ephemeral=ephemeral)
        self._committed = (ReplyVisibility.EPHEMERAL if ephemeral
                           else ReplyVisibility.PUBLIC)

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        # pre-ack direct denial — the denial IS the ack
        await self._interaction.response.send_message(message, ephemeral=ephemeral)

    async def open_modal(self, modal_ref: object) -> None:
        await self._interaction.response.send_modal(modal_ref)

    async def open_confirm(self, prompt: ConfirmPrompt) -> None:
        # v1 confirm surface: an ephemeral prompt whose confirm control
        # custom_id encodes (target_key, confirm token, request_id) — the
        # component adapter re-enters resolve() with confirmed=True. The
        # kernel confirm VIEW (buttons/modal) is S9b panel-runtime work.
        custom_id = f"sb.confirm:{prompt.target_key}:{prompt.request_id}"
        await self._interaction.response.send_message(
            f"{prompt.prompt_text} (confirm id: `{custom_id}`)", ephemeral=True)

    async def render(self, result: object) -> None:
        message = getattr(result, "user_message", None)
        visibility = getattr(result, "reply_visibility", ReplyVisibility.EPHEMERAL)
        if message is None or visibility is ReplyVisibility.SILENT:
            return
        ephemeral = visibility is ReplyVisibility.EPHEMERAL
        response = getattr(self._interaction, "response", None)
        if response is not None and not response.is_done():
            await response.send_message(message, ephemeral=ephemeral)
        else:
            await self._interaction.followup.send(message, ephemeral=ephemeral)


class MessageResponder:
    """Wraps a `commands.Context` / `discord.Message` (prefix surface).
    `ack` is a no-op; nothing is ever committed (ephemerality does not exist
    on the message surface — EPHEMERAL renders as a normal reply)."""

    def __init__(self, ctx: object, *, surface: Surface = Surface.PREFIX):
        self._ctx = ctx
        self.surface = surface

    def is_acked(self) -> bool:
        return False

    def committed_visibility(self) -> ReplyVisibility | None:
        return None

    async def ack(self, *, ephemeral: bool) -> None:
        return None                                    # message surfaces: no-op

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        await self._ctx.reply(message)

    async def open_modal(self, modal_ref: object) -> None:
        await self._ctx.reply("This action needs the slash-command version.")

    async def open_confirm(self, prompt: ConfirmPrompt) -> None:
        await self._ctx.reply(prompt.prompt_text)

    async def render(self, result: object) -> None:
        message = getattr(result, "user_message", None)
        visibility = getattr(result, "reply_visibility", None)
        if message is None or visibility is ReplyVisibility.SILENT:
            return
        await self._ctx.reply(message)
