"""The moderation hub panel — the shipped ``!modmenu`` / ``/moderation``
Moderation Panel at byte parity (disbot views/moderation/main_panel.py
``ModPanelView`` + services/moderation_helpers.py ``_build_mod_panel_embed``
@7f7628e1; goldens/moderation/sweep_modmenu + sweep_slash_moderation pin
every byte).

Shipped shape carried verbatim:

* the seven action buttons with their PERSISTENT custom_ids (``mod:warn``
  … ``mod:clearwarn`` — static ids, so the panel anchors and the ids ride
  ``custom_id_override``, the economy:* precedent), glyph-IN-label
  (``discord.ui.Button(label="⚠️ Warn")`` — no wire emoji field), the
  shipped styles (warn/timeout PRIMARY, kick/ban DANGER, unban SUCCESS,
  logs/clearwarn SECONDARY) and the shipped 3/3/1 row layout;
* every button opened a MODAL prompting for the user and reason
  (views/moderation/modals.py) — ported as G-10 ModalSpecs whose submits
  run the audited K7 ops;
* the orange embed (title ``🔨 Moderation Panel``, the two-line
  description, seven INLINE button-glossary fields, the dynamic
  ``🤖 Bot readiness`` field, the staff footer) — state-dependent copy the
  grammar cannot express, so a renderer_override composes it
  (economy.render_hub precedent).
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    DeferMode,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, WorkflowRef, handler, panel

__all__ = ["ensure_panel_refs", "moderation_hub_spec"]

#: shipped footer literal (moderation_helpers._build_mod_panel_embed;
#: goldens/moderation/sweep_modmenu pins the byte)
_FOOTER = ("Any staff member with Moderate Members permission may use "
           "this panel.")

#: the shipped button glossary — seven INLINE fields, name/value verbatim
#: (goldens/moderation/sweep_modmenu + sweep_slash_moderation pin every
#: byte; the shipped "auto-timeout at 3" literal bakes the DEFAULT warn
#: ladder into copy exactly like the oracle did).
_GLOSSARY: tuple[tuple[str, str], ...] = (
    ("⚠️ Warn", "Issue a warning (auto-timeout at 3)"),
    ("⏳ Timeout", "Temporarily mute for N minutes"),
    ("👢 Kick", "Remove from server"),
    ("🚫 Ban", "Permanently ban"),
    ("✅ Unban", "Lift a ban by user ID"),
    ("📋 Mod Logs", "View moderation history"),
    ("⬛ Clear Warnings", "Reset warning count"),
)

# --- the shipped prompt modals (views/moderation/modals.py) ----------------------
# Titles "Warn Member"/"Timeout Member" are oracle-verbatim; the remaining
# titles follow the same shipped family. Field ids feed
# service.parse_target_and_reason ("user"/"reason") and the timeout record
# leg ("minutes") directly.

_USER_FIELD = ModalFieldSpec(
    field_id="user", label="User (mention, ID, or name)",
    placeholder="@member or 123456789", required=True, max_length=40)
_REASON_FIELD = ModalFieldSpec(
    field_id="reason", label="Reason", required=False, max_length=200)

WARN_MODAL = ModalSpec(
    modal_id="moderation.warn_form", title="Warn Member",
    fields=(_USER_FIELD, _REASON_FIELD),
    on_submit=WorkflowRef("moderation.warn"))
TIMEOUT_MODAL = ModalSpec(
    modal_id="moderation.timeout_form", title="Timeout Member",
    fields=(_USER_FIELD,
            ModalFieldSpec(field_id="minutes", label="Duration (minutes)",
                           placeholder="e.g. 30", required=True,
                           max_length=10),
            _REASON_FIELD),
    on_submit=HandlerRef("moderation.timeout_command"))
KICK_MODAL = ModalSpec(
    modal_id="moderation.kick_form", title="Kick Member",
    fields=(_USER_FIELD, _REASON_FIELD),
    on_submit=WorkflowRef("moderation.kick"))
BAN_MODAL = ModalSpec(
    modal_id="moderation.ban_form", title="Ban Member",
    fields=(_USER_FIELD, _REASON_FIELD),
    on_submit=WorkflowRef("moderation.ban"))
UNBAN_MODAL = ModalSpec(
    modal_id="moderation.unban_form", title="Unban User",
    fields=(ModalFieldSpec(field_id="user", label="User ID",
                           placeholder="123456789", required=True,
                           max_length=40),
            _REASON_FIELD),
    on_submit=WorkflowRef("moderation.unban"))
LOGS_MODAL = ModalSpec(
    modal_id="moderation.modlogs_form", title="Mod Logs",
    fields=(_USER_FIELD,),
    on_submit=HandlerRef("moderation.modlogs_view"))
CLEARWARN_MODAL = ModalSpec(
    modal_id="moderation.clearwarnings_form", title="Clear Warnings",
    fields=(_USER_FIELD,),
    on_submit=WorkflowRef("moderation.clearwarnings"))


def moderation_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="moderation.hub",
        subsystem="moderation",
        title="🔨 Moderation Panel",           # shipped verbatim
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="orange",   # discord.Color.orange()
                             footer_mode=FooterMode.NONE),
        body=(
            # shipped description, verbatim — the override reuses this
            # grammar byte (base.embed.description).
            TextBlock("Click a button to take a moderation action.\n"
                      "You'll be prompted to enter the user and reason."),
        ),
        actions=(
            # Row 0 — shipped ids/labels/styles verbatim (main_panel.py).
            PanelActionSpec(
                action_id="warn", label="⚠️ Warn",
                style=ActionStyle.PRIMARY,
                defer_mode=DeferMode.MODAL, modal=WARN_MODAL,
                handler=WorkflowRef("moderation.warn"),
                audit="moderation.action_taken",
                custom_id_override="mod:warn"),
            PanelActionSpec(
                action_id="timeout", label="⏳ Timeout",
                style=ActionStyle.PRIMARY,
                defer_mode=DeferMode.MODAL, modal=TIMEOUT_MODAL,
                handler=HandlerRef("moderation.timeout_command"),
                audit="moderation.action_taken",
                custom_id_override="mod:timeout"),
            PanelActionSpec(
                action_id="kick", label="👢 Kick",
                style=ActionStyle.DANGER,
                defer_mode=DeferMode.MODAL, modal=KICK_MODAL,
                handler=WorkflowRef("moderation.kick"),
                audit="moderation.action_taken",
                custom_id_override="mod:kick"),
            # Row 1.
            PanelActionSpec(
                action_id="ban", label="🚫 Ban",
                style=ActionStyle.DANGER,
                defer_mode=DeferMode.MODAL, modal=BAN_MODAL,
                handler=WorkflowRef("moderation.ban"),
                audit="moderation.action_taken",
                custom_id_override="mod:ban"),
            PanelActionSpec(
                action_id="unban", label="✅ Unban",
                style=ActionStyle.SUCCESS,
                defer_mode=DeferMode.MODAL, modal=UNBAN_MODAL,
                handler=WorkflowRef("moderation.unban"),
                audit="moderation.action_taken",
                custom_id_override="mod:unban"),
            PanelActionSpec(
                action_id="logs", label="📋 Mod Logs",
                defer_mode=DeferMode.MODAL, modal=LOGS_MODAL,
                handler=HandlerRef("moderation.modlogs_view"),
                custom_id_override="mod:logs"),
            # Row 2.
            PanelActionSpec(
                action_id="clearwarn", label="⬛ Clear Warnings",
                defer_mode=DeferMode.MODAL, modal=CLEARWARN_MODAL,
                handler=WorkflowRef("moderation.clearwarnings"),
                audit="moderation.action_taken",
                custom_id_override="mod:clearwarn"),
        ),
        navigation=NavigationSpec(),   # nav:help only — moderation IS a hub
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("warn", "timeout", "kick"),
            ("ban", "unban", "logs"),
            ("clearwarn",),
        )),)),
        renderer_override=HandlerRef("moderation.render_hub"),
        justification=(
            "the shipped Moderation Panel embed (services/"
            "moderation_helpers.py _build_mod_panel_embed) carries "
            "state-dependent copy the grammar cannot express; the override "
            "delegates the COMPONENTS to render_panel (declared actions/"
            "nav untouched, the pinned mod:* ids come from the spec) and "
            "composes the EMBED surfaces only: the seven INLINE "
            "button-glossary fields (shipped literals), the dynamic "
            "non-inline '🤖 Bot readiness' field (render_readiness_line "
            "over the guild.me read port; dropped when no guild view is "
            "available — the shipped no-guild posture), and the footer "
            "literal ('Any staff member with Moderate Members permission "
            "may use this panel.'). Title, orange accent, and the two-line "
            "description stay the grammar's own bytes."),
    )


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — see the spec's justification."""
    import dataclasses

    from sb.domain.moderation.service import (
        read_moderation_readiness,
        render_readiness_line,
    )
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    fields: list[tuple[str, str, bool]] = [
        (name, value, True) for name, value in _GLOSSARY]
    readiness = await read_moderation_readiness(int(ctx.guild_id or 0))
    if readiness is not None:
        fields.append(("🤖 Bot readiness",
                       render_readiness_line(readiness), False))
    embed = RenderedEmbed(
        title=spec.title,
        description=base.embed.description,
        fields=tuple(fields),
        footer=_FOOTER,
        style_token=spec.frame.style_token)
    return dataclasses.replace(base, embed=embed)


@panel("moderation.hub")
def _hub_factory() -> PanelSpec:
    return moderation_hub_spec()


handler("moderation.render_hub")(_render_hub)


def install_moderation_panels() -> PanelSpec:
    spec = moderation_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    if not _is(PanelRef("moderation.hub")):
        _panel("moderation.hub")(_hub_factory)
    if not _is(HandlerRef("moderation.render_hub")):
        handler("moderation.render_hub")(_render_hub)
