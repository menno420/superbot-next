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

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord as _discord
except ImportError:
    _discord = None  # type: ignore[assignment]

__all__ = ["InteractionResponder", "MessageResponder"]

_CONTENT_LIMIT = 2000                       # Discord hard cap per message


def _mention_kwargs(result: object) -> dict:
    """The shipped ``allowed_mentions=AllowedMentions.none()`` send kwarg,
    carried as reply data (``Result.workflow`` is the handler's Reply; the
    ``!aireview preset add`` confirmation echoes member text — the shipped
    cog suppressed pings on it)."""
    if _discord is None:
        return {}
    if bool(getattr(getattr(result, "workflow", None),
                    "suppress_mentions", False)):
        return {"allowed_mentions": _discord.AllowedMentions.none()}
    return {}


def _content_chunks(text: str, limit: int = _CONTENT_LIMIT) -> list[str]:
    """Split success copy into <= limit chunks on line boundaries (a single
    over-long line hard-splits). Discord rejects >2000-char content with a
    400 — without this, a long reply dies in render and the invoker sees
    NOTHING (found live: `!coglist`'s manifest listing)."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:            # one pathological line
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current)
    return [c.rstrip("\n") for c in chunks if c.rstrip("\n")]


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
        # a declared ModalSpec materializes as the real discord.ui.Modal
        # (the modal-arming slice); an already-sendable modal object (the
        # hermetic/test contexts' fakes) passes through unchanged.
        if (_discord is not None and modal_ref is not None
                and hasattr(modal_ref, "modal_id")
                and hasattr(modal_ref, "fields")):
            from sb.adapters.discord.modal_view import build_modal

            modal_ref = build_modal(modal_ref)
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
        mention_kwargs = _mention_kwargs(result)
        response = getattr(self._interaction, "response", None)
        chunks = _content_chunks(str(message))
        if response is not None and not response.is_done():
            await response.send_message(chunks[0], ephemeral=ephemeral,
                                        **mention_kwargs)
            chunks = chunks[1:]
        for chunk in chunks:
            await self._interaction.followup.send(chunk, ephemeral=ephemeral,
                                                  **mention_kwargs)


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
        mention_kwargs = _mention_kwargs(result)
        for chunk in _content_chunks(str(message)):
            await self._ctx.reply(chunk, **mention_kwargs)
