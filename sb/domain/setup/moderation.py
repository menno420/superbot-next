"""The MODERATION section flow (the settings-write slice), ported from
the oracle (menno420/superbot, read from the LOCAL oracle clone:
views/setup/sections/moderation.py):

* the FOUR KNOBS (the high-impact subset the wizard surfaces —
  everything else stays in ``!settings → Moderation``): **DM on
  action** (``dm_on_action``), **Require a reason**
  (``require_reason``), **Warn escalation**
  (``warn_escalation_action`` over the shipped
  ``WARN_ESCALATION_ACTIONS`` vocabulary), **Moderator role** (the
  ADR-008 capability-native tier grant);
* the DETAIL VIEW (``ModerationSectionView``, rows 0–3 verbatim — row
  4 stays reserved for wizard_nav's ↩ Back to step injection): four
  single-purpose pickers, each pick STAGING one ``set_setting`` row
  into the guild's K9 draft (the registered ``settings.set_scalar``
  op kind — preset_select._register_set_setting_op_kind) and
  answering the shipped staged/pending confirmation;
* the EMBED (``build_moderation_embed``, bytes verbatim): the
  four-bullet "What you can set here" field plus the **Detected**
  field when current values are readable
  (moderation.service.load_policy — the oracle
  services/moderation_config twin);
* APPLY RECOMMENDED (``_recommended_moderation_ops``, semantics
  verbatim): DM-on-action + require-a-reason — "transparency /
  accountability wins and behaviour-preserving otherwise".

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the MODERATOR-ROLE write lands on ``governance.
  moderator_tier_role_id`` (the essential_steps moderators-step
  precedent; keys.py maps the oracle ``MODERATOR_TIER_ROLE_ID``
  settings key there) — the oracle's ``moderation.moderator_role``
  spec name has no declared twin here; the LABEL keeps the oracle's
  ``moderation.moderator_role = @{role}`` bytes (cosmetic tail);
* the Detected field's role render: the oracle's ``role.mention``
  resolution rode a perms-bearing guild handle no handler-side seam
  carries — the ```{role_id}``` fallback branch (the oracle's own)
  answers;
* the pick staging is GATED on the ported can-apply ladder (the
  channels-flow additive fence — the oracle's ``_stage_setting``
  predates the per-button re-check);
* staged K9 rows carry no oracle metadata dict (source/confidence/
  risk/rollback_note) — the final_review.py ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "MODERATION_DETAIL_PANEL_ID",
    "SETTING_DM_ON_ACTION",
    "SETTING_MODERATOR_ROLE",
    "SETTING_REQUIRE_REASON",
    "SETTING_WARN_ESCALATION",
    "build_moderation_embed",
    "ensure_setup_moderation_refs",
    "moderation_detail_spec",
    "read_current_state",
    "recommended_moderation_ops",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "moderation"
SUBSYSTEM = "moderation"

MODERATION_DETAIL_PANEL_ID = "setup.moderation_detail"

# Spec names (``SettingSpec.name``) — NOT the legacy settings_keys
# (oracle cogs/moderation/schemas.py; here sb/manifest/moderation.py).
SETTING_DM_ON_ACTION = "dm_on_action"
SETTING_REQUIRE_REASON = "require_reason"
SETTING_WARN_ESCALATION = "warn_escalation_action"
#: the ADR-008 tier grant's declared home (module docstring ledger).
SETTING_MODERATOR_ROLE = "moderator_tier_role_id"

#: shipped copy, verbatim (moderation._ESCALATION_DESCRIPTIONS).
_ESCALATION_DESCRIPTIONS: dict[str, str] = {
    "timeout": "Auto-timeout, then reset the count (today's default).",
    "kick": "Kick the member when they hit the warn threshold.",
    "ban": "Ban the member when they hit the warn threshold.",
    "none": "Disable automatic escalation — warnings only accumulate.",
}

#: the shipped card copy, verbatim (moderation.run's ``detected``).
_DETECTED_STATE = (
    "Moderation behaviour (DM-on-action, required reason, warn escalation, "
    "moderator role) stays at its current values until you change it. "
    "Apply Recommended enables DM-on-action + require-a-reason; Customize "
    "tunes each knob.")

_DM_OPTIONS_PROVIDER = "setup.moderation_dm_options"
_REASON_OPTIONS_PROVIDER = "setup.moderation_reason_options"
_ESCALATION_OPTIONS_PROVIDER = "setup.moderation_escalation_options"


# --- the embed (build_moderation_embed, bytes verbatim) ------------------------------------

def _on_off(value: bool | None) -> str:
    if value is None:
        return "default"
    return "on" if value else "off"


def build_moderation_embed(*, dm_on_action: bool | None = None,
                           require_reason: bool | None = None,
                           warn_escalation_action: str | None = None,
                           moderator_role_id: int | None = None):
    from sb.kernel.panels.render import RenderedEmbed

    fields: list[tuple] = [
        ("What you can set here",
         ("• **DM on action** — notify the member when they're actioned\n"
          "• **Require a reason** — warn / kick / ban need a reason\n"
          "• **Warn escalation** — what happens at the warn threshold\n"
          "• **Moderator role** — moderate without Discord perms (ADR-008)"),
         False),
    ]
    if any(v is not None for v in (dm_on_action, require_reason,
                                   warn_escalation_action,
                                   moderator_role_id)):
        role_text = "_(none)_"
        if moderator_role_id:
            # the oracle's unresolvable-role fallback branch (module
            # docstring ledger).
            role_text = f"`{moderator_role_id}`"
        fields.append((
            "Detected",
            (f"• DM on action: **{_on_off(dm_on_action)}**\n"
             f"• Require a reason: **{_on_off(require_reason)}**\n"
             f"• Warn escalation: "
             f"**{warn_escalation_action or 'timeout'}**\n"
             f"• Moderator role: {role_text}"),
            False))
    return RenderedEmbed(
        title="🛡️ Moderation",
        description=(
            "Configure how warns, timeouts, kicks, and bans behave.  Each "
            "pick stages a `set_setting` operation — **Final review** "
            "applies them all through the audited settings pipeline.  "
            "Everything else (DM template, ban message-purge, public log, "
            "…) lives in `!settings → Moderation`."),
        fields=tuple(fields),
        footer=("Recommended: DM on action + require a reason "
                "(safe, transparent)."),
        style_token="blurple")


async def read_current_state(guild_id: int) -> tuple[
        bool | None, bool | None, str | None, int | None]:
    """moderation._read_current_state, ported: best-effort read of the
    four surfaced values (any failure degrades to ``None`` — the
    snapshot is informational and must never block the render)."""
    dm_on = require_reason = None
    escalation = None
    moderator_role_id = None
    try:
        from sb.domain.moderation.service import load_policy

        policy = await load_policy(int(guild_id))
        dm_on = policy.dm_on_action
        require_reason = policy.require_reason
        escalation = policy.warn_escalation_action
    except Exception:  # noqa: BLE001 — the shipped soft-fail
        logger.exception("moderation: load_policy failed")
    try:
        from sb.kernel.settings import resolve

        raw = await resolve(int(guild_id), "governance",
                            SETTING_MODERATOR_ROLE)
        if raw not in (None, "", 0, "0"):
            moderator_role_id = int(raw)
    except Exception:  # noqa: BLE001 — the shipped soft-fail
        logger.exception("moderation: moderator-role read failed")
    return dm_on, require_reason, escalation, moderator_role_id


# --- staging (moderation._stage_setting over the K9 spine) ----------------------------------

def _setting_op(subsystem: str, name: str, value: object, label_body: str):
    """One ``set_setting`` StagedSectionOp — the registered
    ``settings.set_scalar`` op-kind payload (subsystem/name/key/value;
    bools serialize "true"/"false", the wizard._write_setting twin)."""
    from sb.domain.setup.section_card import StagedSectionOp
    from sb.kernel import settings as ksettings

    serialized = (("true" if value else "false") if isinstance(value, bool)
                  else str(value))
    return StagedSectionOp(
        op_kind="set_setting", subsystem=subsystem,
        payload={"subsystem": subsystem, "name": name,
                 "key": ksettings.persisted_key(subsystem, name),
                 "value": serialized},
        label_body=label_body)


async def _stage_setting(req, *, subsystem: str, name: str, value: object,
                         label: str) -> Reply:
    """Stage one moderation ``set_setting`` op into the guild's draft
    (the shipped append's replace-on-conflict slot semantics —
    section_card.stage_custom), gated on the ported can-apply ladder
    (the channels-flow additive fence)."""
    from sb.domain.setup import preset_select, section_card, wizard
    from sb.domain.setup.wizard import _refresh_own_panel

    guild_id = int(req.guild_id or 0)
    if not guild_id:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This can only be used in a server.")
    if not await section_card._gated_card(req):
        return Reply(BLOCKED, section_card.GATE_MSG_CARD)
    preset_select._register_set_setting_op_kind()
    try:
        await section_card.stage_custom(
            guild_id, SLUG, _setting_op(subsystem, name, value, label))
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception("moderation: setup_draft.append failed")
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "Could not stage the moderation setting — see logs.")
    await section_card.mark_step_in_progress(req, SLUG)
    try:
        pending = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped count soft-fail
        logger.exception("moderation: setup_draft.count failed")
        pending = 0
    await _refresh_own_panel(req, {})
    # shipped confirmation, verbatim (moderation._stage_setting).
    return Reply(SUCCESS,
                 f"✅ Staged for Final review: `{label}`.  "
                 f"Pending operations: **{pending}**.")


async def recommended_moderation_ops(guild_id: int) -> list:
    """Safe moderation baseline: DM on action + require a reason
    (moderation._recommended_moderation_ops — "transparency /
    accountability wins and behaviour-preserving otherwise")."""
    del guild_id
    return [
        _setting_op(SUBSYSTEM, SETTING_DM_ON_ACTION, True,
                    f"{SUBSYSTEM}.{SETTING_DM_ON_ACTION} = True"),
        _setting_op(SUBSYSTEM, SETTING_REQUIRE_REASON, True,
                    f"{SUBSYSTEM}.{SETTING_REQUIRE_REASON} = True"),
    ]


# --- the detail panel -------------------------------------------------------------------------

def moderation_detail_spec():
    """ModerationSectionView folded onto one panel: the four
    single-purpose pickers on rows 0–3 (placeholders/options verbatim)
    plus the wizard-origin ↩ Back to step button on row 4 (the row the
    oracle reserved for exactly this injection)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=MODERATION_DETAIL_PANEL_ID,
        subsystem="setup",
        title="🛡️ Moderation",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="mod_dm", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.moderation_dm_pick"),
                options_source=ProviderRef(_DM_OPTIONS_PROVIDER),
                placeholder="DM the member on action…"),
            SelectorSpec(
                selector_id="mod_reason", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.moderation_reason_pick"),
                options_source=ProviderRef(_REASON_OPTIONS_PROVIDER),
                placeholder="Require a reason for warn / kick / ban…"),
            SelectorSpec(
                selector_id="mod_escalation", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.moderation_escalation_pick"),
                options_source=ProviderRef(_ESCALATION_OPTIONS_PROVIDER),
                placeholder="Warn escalation action…"),
            SelectorSpec(
                selector_id="mod_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.moderation_role_pick"),
                placeholder=("Moderator role (optional — grants moderation "
                             "access)…")),
        ),
        actions=(
            PanelActionSpec(
                action_id="mod_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("mod_dm",), ("mod_reason",), ("mod_escalation",),
            ("mod_role",), ("mod_back_step",))),)),
        renderer_override=HandlerRef("setup.moderation_detail_render"),
        justification=(
            "the shipped moderation detail renders a live Detected field "
            "(the four current values off the audited settings read — "
            "moderation.build_moderation_embed's current-state arguments) "
            "and its ↩ Back to step button rides only the wizard-native "
            "path (wizard_nav.render_step_detail's row-4 injection) — "
            "outside the static grammar vocabulary; the override composes "
            "the embed and filters the components (no golden pins it — "
            "the oracle source does)."),
        session_lifecycle=True,
    )


def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_DM_OPTIONS_PROVIDER)):
        return

    @provider(_DM_OPTIONS_PROVIDER)
    async def dm_options(ctx):
        """_DmOnActionSelect's options, verbatim."""
        del ctx
        return (
            {"label": "DM on action: ON", "value": "true",
             "description": "Tell the member why they were actioned.",
             "emoji": "✅"},
            {"label": "DM on action: OFF", "value": "false",
             "description": "Don't DM the member (today's default).",
             "emoji": "🚫"},
        )

    @provider(_REASON_OPTIONS_PROVIDER)
    async def reason_options(ctx):
        """_RequireReasonSelect's options, verbatim."""
        del ctx
        return (
            {"label": "Require a reason: ON", "value": "true",
             "description": "Reject warn / kick / ban with no reason.",
             "emoji": "✅"},
            {"label": "Require a reason: OFF", "value": "false",
             "description": "Reasons stay optional (today's default).",
             "emoji": "🚫"},
        )

    @provider(_ESCALATION_OPTIONS_PROVIDER)
    async def escalation_options(ctx):
        """_WarnEscalationSelect's options over the shipped
        WARN_ESCALATION_ACTIONS vocabulary, verbatim caps."""
        del ctx
        from sb.domain.moderation.service import WARN_ESCALATION_ACTIONS

        return tuple(
            {"label": action, "value": action,
             "description": _ESCALATION_DESCRIPTIONS.get(action, "")[:100]}
            for action in WARN_ESCALATION_ACTIONS)


async def _render_moderation_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    dm_on, require_reason, escalation, role_id = await read_current_state(
        guild_id)
    embed = build_moderation_embed(
        dm_on_action=dm_on, require_reason=require_reason,
        warn_escalation_action=escalation, moderator_role_id=role_id)

    base = await render_panel(spec, ctx)
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        if c.custom_id.endswith(".mod_back_step") and not from_wizard:
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ----------------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.moderation_dm_pick")):
        return

    @handler("setup.open_section_moderation")
    async def open_section_moderation(req) -> Reply | None:
        """The hub's Moderation section button — gate exactly like the
        shipped hub button, land on the section card (moderation.run →
        section_card.show), record the step marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    def _bool_pick(setting_name: str, reason_word: str):
        async def _pick(req) -> Reply:
            values = tuple(req.args.get("values", ()) or ())
            enabled = bool(values) and str(values[0]) == "true"
            # the shipped label bytes (moderation's f"... = {enabled}").
            return await _stage_setting(
                req, subsystem=SUBSYSTEM, name=setting_name, value=enabled,
                label=f"{SUBSYSTEM}.{setting_name} = {enabled}")
        del reason_word
        return _pick

    handler("setup.moderation_dm_pick")(
        _bool_pick(SETTING_DM_ON_ACTION, "DM-on-action"))
    handler("setup.moderation_reason_pick")(
        _bool_pick(SETTING_REQUIRE_REASON, "require-reason"))

    @handler("setup.moderation_escalation_pick")
    async def moderation_escalation_pick(req) -> Reply:
        from sb.domain.moderation.service import WARN_ESCALATION_ACTIONS

        values = tuple(req.args.get("values", ()) or ())
        action = str(values[0]) if values else ""
        if action not in WARN_ESCALATION_ACTIONS:
            # defensive twin of the picker's known-keys contract.
            return Reply(BLOCKED, f"Unknown escalation action `{action}`.")
        return await _stage_setting(
            req, subsystem=SUBSYSTEM, name=SETTING_WARN_ESCALATION,
            value=action,
            label=f"{SUBSYSTEM}.{SETTING_WARN_ESCALATION} = {action}")

    @handler("setup.moderation_role_pick")
    async def moderation_role_pick(req) -> Reply:
        """_ModeratorRoleSelect.callback, ported: the numeric role id
        (string) lands on the declared governance tier-grant setting
        (module docstring ledger); the LABEL keeps the oracle bytes'
        shape — the role name resolution rode the native picker's
        resolved role, the id spelling answers here."""
        values = tuple(req.args.get("values", ()) or ())
        raw = str(values[0]) if values else ""
        if not raw.lstrip("-").isdigit():
            return Reply(BLOCKED, "No role picked.")
        role_id = int(raw)
        return await _stage_setting(
            req, subsystem="governance", name=SETTING_MODERATOR_ROLE,
            value=str(role_id),
            label=f"{SUBSYSTEM}.moderator_role = @{role_id}")


# --- registration --------------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.moderation_detail_render")):
        handler("setup.moderation_detail_render")(_render_moderation_detail)
    if not is_registered(PanelRef(MODERATION_DETAIL_PANEL_ID)):
        panel(MODERATION_DETAIL_PANEL_ID)(moderation_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    section_card.register_recommended_builder(SLUG,
                                              recommended_moderation_ops)
    section_card.register_customize_panel(SLUG, MODERATION_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_ensure_providers()
_register()
_register_panels()
_register_section()


def ensure_setup_moderation_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_section()
