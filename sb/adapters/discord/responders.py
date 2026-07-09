"""Concrete `SurfaceResponder` implementations (frozen L0 spec 02 §2) — the
ONLY modules that touch `discord.Interaction` / `discord.Message`.

Duck-typed against the discord.py API so the module imports cleanly without
the discord package (the objects arrive from the gateway at runtime).
"""

from __future__ import annotations

import logging

from sb.adapters.discord import confirm_view as confirm_view_mod
from sb.kernel.interaction.request import ConfirmPrompt, Surface
from sb.kernel.panels.engine import register_confirm_session
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
        # the S9b confirm surface (02 §3.2): a typed challenge opens the
        # capture modal DIRECTLY while the interaction is still un-acked
        # (the modal must be the first response); otherwise the Confirm/
        # Cancel button view goes out (ephemeral), invoker-locked through
        # the kernel confirm session the component feed mirrors.
        response = getattr(self._interaction, "response", None)
        if confirm_view_mod.discord_ui is None:
            # text fallback: no discord package (hermetic/test contexts) —
            # the raw confirm id stays the manual re-entry handle.
            custom_id = f"sb.confirm:{prompt.target_key}:{prompt.request_id}"
            await self._interaction.response.send_message(
                f"{prompt.prompt_text} (confirm id: `{custom_id}`)",
                ephemeral=True)
            return
        if (confirm_view_mod.is_typed_challenge(prompt.challenge)
                and response is not None and not response.is_done()):
            await response.send_modal(confirm_view_mod.build_confirm_modal(
                prompt.target_key, prompt.request_id))
            return
        view = confirm_view_mod.build_confirm_view(prompt)
        message = None
        if response is not None and not response.is_done():
            await response.send_message(prompt.prompt_text, view=view,
                                        ephemeral=True)
            try:
                message = await self._interaction.original_response()
            except Exception:  # noqa: BLE001 — lock registration is best-effort
                logger.debug("confirm original_response fetch failed",
                             exc_info=True)
        else:
            # a followup send returns the message (interaction webhooks
            # carry a token) — the lock/timeout handle comes back directly.
            message = await self._interaction.followup.send(
                prompt.prompt_text, view=view, ephemeral=True)
        view.message = message
        invoker = getattr(getattr(self._interaction, "user", None), "id", None)
        if message is not None:
            register_confirm_session(str(getattr(message, "id", "")),
                                     invoker_id=invoker,
                                     timeout_s=prompt.timeout_s)

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
        # the S9b confirm surface on the message band: the Confirm/Cancel
        # button view (a prefix message has no interaction, so a typed
        # challenge's capture modal opens from the Confirm CLICK — the live
        # component feed answers sb.confirm.open: with the modal).
        if confirm_view_mod.discord_ui is None:
            # text fallback: no discord package (hermetic/test contexts).
            custom_id = f"sb.confirm:{prompt.target_key}:{prompt.request_id}"
            await self._ctx.reply(
                f"{prompt.prompt_text} (confirm id: `{custom_id}`)")
            return
        view = confirm_view_mod.build_confirm_view(prompt)
        message = await self._ctx.reply(prompt.prompt_text, view=view)
        view.message = message
        invoker = getattr(getattr(self._ctx, "author", None), "id", None)
        if message is not None:
            register_confirm_session(str(getattr(message, "id", "")),
                                     invoker_id=invoker,
                                     timeout_s=prompt.timeout_s)

    async def render(self, result: object) -> None:
        message = getattr(result, "user_message", None)
        visibility = getattr(result, "reply_visibility", None)
        if message is None or visibility is ReplyVisibility.SILENT:
            return
        await self._ctx.reply(message)
