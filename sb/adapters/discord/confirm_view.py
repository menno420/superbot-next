"""The S9b CONFIRM VIEW — the kernel-owned confirm surface, materialized
(frozen L0 spec 02 §3.2 ConfirmationSpec round-trip):

* ``challenge=button`` → a **Confirm** (danger) / **Cancel** (secondary)
  button pair; the Confirm control's custom_id IS the fixed re-entry handle
  ``sb.confirm:<target_key>:<request_id>`` (the component adapter parses it
  and re-enters ``resolve()`` with ``confirmed=True``).
* ``challenge=typed_phrase``/``typed_hash`` → a one-field **ModalSpec-style
  capture** (the Gate-0 L-24 rider: typed challenges render a modal, never
  an ad-hoc prompt). Where no modal can open directly (the prefix surface
  has no interaction; a deferred slash response can no longer modal), the
  Confirm button carries ``sb.confirm.open:…`` and the live component feed
  answers that click WITH the modal — the click is presentation mechanics,
  never the confirmed re-entry.
* Cancel carries ``sb.confirm.cancel:…`` — the kernel component adapter's
  §2.7 DECLINED terminal.
* The view times out at ``ConfirmationSpec.timeout_s`` and disables its
  controls (the spec's decline-by-timeout render); the kernel stash is
  dropped via ``cancel_pending_confirm`` so a stale click declines.

No per-item callbacks — every click dispatches through the live component
feed (the PanelRuntimeView doctrine). Import-guarded: pure helpers work
without the discord package; ``build_confirm_view``/``build_confirm_modal``
require it at CALL time.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.request import ConfirmPrompt
from sb.kernel.interaction.resolve import cancel_pending_confirm
from sb.kernel.panels.engine import may_interact, session_for
from sb.spec.confirmation import Challenge

logger = logging.getLogger("sb.adapters.discord.confirm_view")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
    from discord import ui as discord_ui
except ImportError:  # noqa: SIM105
    discord = None          # type: ignore[assignment]
    discord_ui = None       # type: ignore[assignment]

__all__ = [
    "CONFIRM_OPEN_PREFIX",
    "build_confirm_modal",
    "build_confirm_view",
    "cancel_custom_id",
    "confirm_custom_id",
    "expected_phrase",
    "is_typed_challenge",
    "open_custom_id",
    "phrase_matches",
]

#: the typed-challenge Confirm button: the click OPENS the capture modal
#: (presentation mechanics — the modal's submit is the confirmed re-entry).
CONFIRM_OPEN_PREFIX = "sb.confirm.open:"
_CANCEL_PREFIX = "sb.confirm.cancel:"   # kept in lockstep with the kernel adapter
_PHRASE_FIELD_ID = "typed_value"


def confirm_custom_id(target_key: str, request_id: str) -> str:
    return f"sb.confirm:{target_key}:{request_id}"


def open_custom_id(target_key: str, request_id: str) -> str:
    return f"{CONFIRM_OPEN_PREFIX}{target_key}:{request_id}"


def cancel_custom_id(target_key: str, request_id: str) -> str:
    return f"{_CANCEL_PREFIX}{target_key}:{request_id}"


def is_typed_challenge(challenge: object) -> bool:
    return challenge in (Challenge.TYPED_PHRASE, Challenge.TYPED_HASH)


def expected_phrase(target_key: str) -> str:
    """The typed-challenge phrase: the target's own final name segment
    (``moderation.kick``/``kick`` ⇒ type ``kick``) — context-derived like
    the draft lane's ``apply <id>``; ConfirmationSpec carries no
    expected_phrase field (ledgered choice, this rework)."""
    return target_key.rsplit(".", 1)[-1] or target_key


def phrase_matches(target_key: str, submitted: object) -> bool:
    return str(submitted or "").strip().casefold() == expected_phrase(
        target_key).casefold()


def build_confirm_modal(target_key: str, request_id: str):
    """The typed-challenge capture (L-24: a one-field ModalSpec-style form).
    The modal's custom_id is the FIXED confirm re-entry handle — its submit
    dispatches through the modal adapter with ``confirmed=True`` after the
    feed checks the typed phrase."""
    if discord_ui is None:
        raise RuntimeError("discord is not installed")
    phrase = expected_phrase(target_key)

    class ConfirmCaptureModal(discord_ui.Modal):
        def __init__(self) -> None:
            super().__init__(title="Confirm", timeout=None,
                             custom_id=confirm_custom_id(target_key, request_id))
            self.typed_value = discord_ui.TextInput(
                label=f'Type "{phrase}" to confirm',
                custom_id=_PHRASE_FIELD_ID, required=True,
                max_length=100)
            self.add_item(self.typed_value)

        async def on_submit(self, interaction) -> None:  # pragma: no cover
            # the live component feed's on_interaction listener owns the
            # submit (phrase check + modal adapter re-entry) — this default
            # exists only so discord.py does not warn about an unhandled
            # modal; it must never respond (one writer per interaction).
            return None

    return ConfirmCaptureModal()


def build_confirm_view(prompt: ConfirmPrompt):
    """ConfirmPrompt → the one confirm view (no callbacks; the component
    feed dispatches). Confirm is danger-styled per the destructive-control
    convention; typed challenges route the click through the modal capture."""
    if discord_ui is None:
        raise RuntimeError("discord is not installed")
    typed = is_typed_challenge(prompt.challenge)
    confirm_id = (open_custom_id(prompt.target_key, prompt.request_id) if typed
                  else confirm_custom_id(prompt.target_key, prompt.request_id))

    class ConfirmView(discord_ui.View):
        def __init__(self) -> None:
            super().__init__(timeout=prompt.timeout_s)
            self.message = None      # set by the responder after send
            self.add_item(discord_ui.Button(
                custom_id=confirm_id, label="Confirm",
                style=discord.ButtonStyle.danger))
            self.add_item(discord_ui.Button(
                custom_id=cancel_custom_id(prompt.target_key, prompt.request_id),
                label="Cancel", style=discord.ButtonStyle.secondary))

        async def interaction_check(self, interaction) -> bool:
            # invoker lock, mirrored from the same kernel session the live
            # feed reads (register_confirm_session at open_confirm time).
            key = str(getattr(getattr(interaction, "message", None), "id", ""))
            session = session_for(key)
            user_id = getattr(getattr(interaction, "user", None), "id", None)
            if not may_interact(session, user_id):
                try:
                    await interaction.response.send_message(
                        "This confirmation belongs to someone else.",
                        ephemeral=True)
                except Exception:  # noqa: BLE001
                    logger.debug("confirm invoker-lock notice failed",
                                 exc_info=True)
                return False
            return True

        async def on_timeout(self) -> None:
            # the §3.2 step-3 timeout terminal: disable the controls and
            # drop the kernel stash so a stale click declines.
            cancel_pending_confirm(prompt.request_id)
            for child in self.children:
                child.disabled = True
            if self.message is not None:
                try:
                    await self.message.edit(view=self)
                except Exception:  # noqa: BLE001 — timeout-disable is best-effort
                    logger.debug("confirm timeout-disable edit failed",
                                 exc_info=True)

    return ConfirmView()
