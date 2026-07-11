"""The G-10 MODAL VIEW — a declared ``ModalSpec`` materialized as the real
``discord.ui.Modal`` (the modal-arming slice; the confirm capture's
``build_confirm_modal`` generalized to the declarative form grammar).

The form is DATA (spec 02 §3.7 / L-24 rider 4): the modal's ``custom_id``
IS the spec's ``modal_id`` — the §3.4 static table routes the SUBMIT back
to the declaring ``PanelActionSpec`` and the live component feed dispatches
it through the frozen MODAL adapter. No per-form callbacks: ``on_submit``
is the deliberate no-op the confirm capture modal established (discord.py
must not warn about an unhandled modal, and it must never respond — one
writer per interaction; the feed owns the dispatch).

Import-guarded like confirm_view: the module imports without the discord
package; ``build_modal`` requires it at CALL time.
"""

from __future__ import annotations

import logging

from sb.spec.panels import ModalFieldStyle, ModalSpec

logger = logging.getLogger("sb.adapters.discord.modal_view")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
    from discord import ui as discord_ui
except ImportError:  # noqa: SIM105
    discord = None          # type: ignore[assignment]
    discord_ui = None       # type: ignore[assignment]

__all__ = ["build_modal"]

#: Discord's hard caps (modal title / text-input label / placeholder).
_TITLE_CAP = 45
_LABEL_CAP = 45
_PLACEHOLDER_CAP = 100


def build_modal(spec: ModalSpec):
    """One declared ``ModalSpec`` → the sendable ``discord.ui.Modal``.
    ``timeout=None`` — the form's lifecycle is the submit dispatch through
    the live feed, never a client-side callback (the confirm-capture
    posture); a stale submit falls to the handler's own guards."""
    if discord_ui is None:
        raise RuntimeError("discord is not installed")

    class PanelModal(discord_ui.Modal):
        def __init__(self) -> None:
            super().__init__(title=(spec.title or "Form")[:_TITLE_CAP],
                             timeout=None, custom_id=spec.modal_id)
            for field in spec.fields:
                self.add_item(discord_ui.TextInput(
                    label=field.label[:_LABEL_CAP],
                    custom_id=field.field_id,
                    style=(discord.TextStyle.paragraph
                           if field.style is ModalFieldStyle.PARAGRAPH
                           else discord.TextStyle.short),
                    required=field.required,
                    min_length=field.min_length,
                    max_length=field.max_length,
                    placeholder=(field.placeholder[:_PLACEHOLDER_CAP]
                                 or None),
                    default=field.default or None,
                ))

        async def on_submit(self, interaction) -> None:  # pragma: no cover
            # the live component feed's on_interaction listener owns the
            # submit (custom_id → modal adapter → resolve()); this default
            # exists only so discord.py does not warn — it must never
            # respond (one writer per interaction).
            return None

    return PanelModal()
