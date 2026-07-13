"""The ROLES section flow (the roles-family slice), ported from the
oracle (menno420/superbot, read from the LOCAL oracle clone:
views/setup/sections/roles.py):

* the TIME/XP TIER DETAIL (``RolesSectionView``, flow verbatim): a
  time-tier role picker (row 0) and an XP-tier role picker (row 1);
  picking a role opens the matching threshold form (``_TimeDaysModal``
  / ``_XpLevelModal`` — labels/placeholders/bounds verbatim:
  1..3650 days, 1..1000 levels); every submission stages ONE
  ``set_role_threshold`` op and answers the shipped staged/pending
  confirmation;
* the EMBED (``build_roles_embed``, bytes verbatim): the explainer +
  "How it works" field, the **Detected** field listing today's
  configured tiers when readable, the Final-Review footer;
* NO auto-recommended path (roles.run: "which role maps to which
  threshold is server-specific, so there is no safe default to
  stage") — ``recommended_ops_builder=None`` keeps the hub sweep from
  silently staging tiers; the section configures thresholds for
  **existing** roles only (role *creation* stays owned by resource
  provisioning — the wizard never opens a second creation path);
* the K9→K7 REGISTRATION: the ``set_role_threshold`` op kind binds
  onto the audited K7 ``role.set_threshold`` op (the
  ``role_thresholds`` full-row upsert + central audit row — the
  oracle dispatcher's ``services.role_automation.set_{time,xp}_
  threshold`` seam pair, folded).

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the K7 ``role.set_threshold`` leg is a FULL-ROW upsert keyed
  ``(guild_id, role_name)`` — applying the oracle's two per-kind rows
  for the same role would clobber each other (the second zeroes the
  first's column). The stage lane therefore FOLDS time + XP for the
  same role into ONE staged row (the essential_steps reward-step
  fold: "ONE full-row threshold upsert carrying both triggers"): the
  slot key is per-ROLE (``tier:{role_id}``, the oracle's
  ``binding_name`` discriminator without the per-kind
  ``setting_name`` half), and a submission merges the other kind's
  already-staged value forward before replacing the slot;
* a G-10 modal must be the interaction's FIRST response and rides a
  declared ``defer_mode=MODAL`` action (the review_item_edit_rename
  precedent) — a native role pick cannot open it. The pick therefore
  stashes the role and REVEALS the matching "Set …" modal button
  (the cleanup detail's stepwise-reveal precedent); the modal wire
  bytes stay static (the panels.py review_item ledger note);
* the native role pick carries only the ID on this seam — the
  staged ``role_name``/``display_name`` ride the id spelling (the
  essential_steps ``reward_existing`` precedent) and labels render
  ``@{role_id}`` (the moderation moderator-role ledger); the
  ``role_id`` column still captures the id so a later rename does
  not orphan the tier (PR6 id-groundwork, verbatim intent);
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
    "KIND_TIME",
    "KIND_XP",
    "ROLES_DETAIL_PANEL_ID",
    "build_roles_embed",
    "ensure_setup_roles_refs",
    "read_current_summary",
    "reset_roles_state_for_tests",
    "roles_detail_spec",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "roles"
SUBSYSTEM = "roles"

ROLES_DETAIL_PANEL_ID = "setup.roles_detail"

# Threshold sub-kinds — the oracle carried them on
# ``SetupOperation.setting_name``; here they pick the merge arm and the
# label bytes (the payload carries both columns, module docstring).
KIND_TIME = "time"
KIND_XP = "xp"

_MAX_DAYS = 3650  # ~10 years — a generous sanity ceiling
_MAX_LEVEL = 1000

#: the shipped card copy, verbatim (roles.run's ``detected``).
_DETECTED_STATE = (
    "Time / XP auto-role tiers stay at their current values until you "
    "change them. Click Customize to grant a role after N days in the "
    "server or at an XP level; manage existing tiers in `!roles`.")


# --- the embed (build_roles_embed, bytes verbatim) ----------------------------------

def build_roles_embed(*, current_summary: str | None = None):
    """roles.build_roles_embed: ``current_summary`` (when supplied)
    renders a **Detected** field listing today's configured tiers;
    ``None`` renders the static explainer used on the section card."""
    from sb.kernel.panels.render import RenderedEmbed

    fields: list[tuple] = [
        ("How it works",
         ("• **Time tier** — granted after N days in the server\n"
          "• **XP tier** — granted at XP level N (auto-assigned)\n"
          "• Configure each tier for an **existing** role; create roles "
          "first in Discord or via the role manager."),
         False),
    ]
    if current_summary is not None:
        fields.append((
            "Detected",
            current_summary or "_(no auto-role tiers configured yet)_",
            False))
    return RenderedEmbed(
        title="🎖️ Auto roles (time & XP)",
        description=(
            "Automatically grant a role when a member has been in the server "
            "long enough (**time tier**) or reaches an **XP level** (XP tier). "
            "Pick a role below, then enter the threshold — each submission "
            "stages a `set_role_threshold` operation that **Final review** "
            "applies through the audited role-automation seam."),
        fields=tuple(fields),
        footer=("Final Review applies all staged tiers · clear/edit tiers "
                "in !roles."),
        style_token="blurple")


async def read_current_summary(guild_id: int) -> str | None:
    """roles._read_current_summary, ported: best-effort one-line summary
    of configured auto-role tiers off the ``role_thresholds`` store read
    (the oracle ``roles_db.get_role_thresholds`` twin). ``None`` on
    failure (the snapshot is informational and must never block the
    render)."""
    try:
        from sb.domain.role import store as role_store

        rows = await role_store.get_thresholds(int(guild_id))
    except Exception:  # noqa: BLE001 — the shipped soft-fail
        logger.exception("roles: get_role_thresholds failed")
        return None
    lines: list[str] = []
    for row in rows:
        name = row.get("display_name") or row.get("role_name") or "?"
        days = row.get("days_required") or 0
        level = row.get("level_required")
        if days:
            lines.append(f"• @{name} — after **{days}d**")
        if level is not None and row.get("xp_auto_assign"):
            lines.append(f"• @{name} — at **XP level {level}**")
    if not lines:
        return ""
    return "\n".join(lines[:10])


# --- input validation (roles._parse_positive_int, verbatim) --------------------------

def _parse_positive_int(raw: str, ceiling: int) -> int | None:
    """Return a positive int within ``[1, ceiling]`` or ``None``."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 1 or value > ceiling:
        return None
    return value


# --- the op-kind registration (the cleanup set_cleanup_policy precedent) -------------

_SET_ROLE_THRESHOLD_OP_KIND = "set_role_threshold"


def _register_set_role_threshold_op_kind() -> None:
    """Bind the ``set_role_threshold`` op kind onto the audited K7
    ``role.set_threshold`` op (threshold row upsert + central audit row
    — the oracle Final-Review dispatcher's
    ``services.role_automation.set_{time,xp}_threshold`` route,
    folded onto the full-row leg)."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_SET_ROLE_THRESHOLD_OP_KIND,
        workflow_ref=WorkflowRef("role.set_threshold"),
        payload_schema=(FieldSpec("role_name", "str"),
                        FieldSpec("role_id", "int"),
                        FieldSpec("days_required", "int"),
                        FieldSpec("xp_auto_assign", "bool")),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


# --- staged-op builder (the per-role fold, module docstring) --------------------------

def _slot_name(role_id: int) -> str:
    """The oracle ``binding_name=f"tier:{role_id}"`` discriminator —
    per-ROLE here (not per-kind): the K7 full-row upsert forces the
    time+XP fold (module docstring ledger)."""
    return f"tier:{role_id}"


async def _prior_slot_payload(guild_id: int, role_id: int) -> dict:
    """The already-staged row at this role's slot (empty when none) —
    the merge-forward read (the fold's other-kind carry)."""
    from sb.domain.setup import section_card

    slot = (_SET_ROLE_THRESHOLD_OP_KIND, SUBSYSTEM, _slot_name(role_id))
    try:
        for _draft, op in await section_card.guild_ops(int(guild_id)):
            if section_card._op_slot(op) == slot:
                return dict(getattr(op, "payload", {}) or {})
    except Exception:  # noqa: BLE001 — a fresh row still stages
        logger.exception("roles: prior-slot read failed")
    return {}


def _threshold_op(*, role_id: int, role_name: str, days_required: int,
                  level_required: int | None, xp_auto_assign: bool,
                  label_body: str):
    """One ``set_role_threshold`` StagedSectionOp: the K7
    ``role.set_threshold`` params (the full-row upsert's columns) plus
    the review-renderer ride-along (``target_name``; the extra keys
    ride ABOVE the op's declared minimum — the stage_accepted
    precedent). ``name`` keys the replace-on-conflict slot per role."""
    from sb.domain.setup.section_card import StagedSectionOp

    return StagedSectionOp(
        op_kind=_SET_ROLE_THRESHOLD_OP_KIND, subsystem=SUBSYSTEM,
        payload={"name": _slot_name(role_id),
                 "role_name": role_name,
                 "display_name": role_name,
                 "role_id": int(role_id),
                 "days_required": int(days_required),
                 "level_required": (int(level_required)
                                    if level_required is not None else None),
                 "xp_auto_assign": bool(xp_auto_assign),
                 "target_name": role_name},
        label_body=label_body)


async def _stage_threshold(req, *, kind: str, role_id: int, role_name: str,
                           value: int, label: str) -> Reply:
    """roles._stage_threshold, ported onto the K9 spine (gated on the
    ported can-apply ladder — the channels-flow additive fence): merge
    the other kind's staged value forward (the full-row fold), replace
    the role's slot, answer the shipped staged/pending confirmation."""
    from sb.domain.setup import section_card, wizard
    from sb.domain.setup.wizard import _refresh_own_panel

    guild_id = int(req.guild_id or 0)
    if not guild_id:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This can only be used in a server.")
    if not await section_card._gated_card(req):
        return Reply(BLOCKED, section_card.GATE_MSG_CARD)
    _register_set_role_threshold_op_kind()
    prior = await _prior_slot_payload(guild_id, role_id)
    if kind == KIND_TIME:
        days = int(value)
        level = prior.get("level_required")
        level = int(level) if level is not None else None
        auto = bool(prior.get("xp_auto_assign", False))
    else:
        days = int(prior.get("days_required", 0) or 0)
        level = int(value)
        auto = True
    op = _threshold_op(role_id=role_id, role_name=role_name,
                       days_required=days, level_required=level,
                       xp_auto_assign=auto, label_body=label)
    try:
        await section_card.stage_custom(guild_id, SLUG, op)
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception("roles: setup_draft.append failed")
        # shipped copy, verbatim.
        return Reply(BLOCKED, "Could not stage the role tier — see logs.")
    await section_card.mark_step_in_progress(req, SLUG)
    try:
        pending = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped count soft-fail
        logger.exception("roles: setup_draft.count failed")
        pending = 0
    await _refresh_own_panel(req, {})
    # shipped confirmation, verbatim.
    return Reply(SUCCESS,
                 f"✅ Staged for Final review: `{label}`.  "
                 f"Pending operations: **{pending}**.")


# --- flow state -----------------------------------------------------------------------

#: guild:user → the picked TIME-tier role id.
_PICKED_TIME_ROLE: dict[str, int] = {}
#: guild:user → the picked XP-tier role id.
_PICKED_XP_ROLE: dict[str, int] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def reset_roles_state_for_tests() -> None:
    _PICKED_TIME_ROLE.clear()
    _PICKED_XP_ROLE.clear()


# --- the detail panel -------------------------------------------------------------------

def roles_detail_spec():
    """RolesSectionView folded onto one panel: the time-tier role picker
    (row 0, placeholder verbatim), the XP-tier role picker (row 1,
    placeholder verbatim), the two state-revealed modal buttons (row 2
    — the oracle's pick-opens-modal, split; titles ride the button
    labels), and the wizard-origin ↩ Back to step button (the row the
    oracle reserved for exactly this injection)."""
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        ModalFieldSpec, ModalSpec, NavigationSpec, PageSpec,
        PanelActionSpec, PanelSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef

    # the oracle modal forms, verbatim labels/placeholders/caps
    # (_TimeDaysModal / _XpLevelModal).
    time_modal = ModalSpec(
        modal_id="setup.roles_time_form",
        title="Set time tier (days)",
        fields=(
            ModalFieldSpec(field_id="days",
                           label="Days in server before the role is granted",
                           placeholder="7", required=True,
                           min_length=1, max_length=4),
        ),
        on_submit=HandlerRef("setup.roles_time_submit"))
    xp_modal = ModalSpec(
        modal_id="setup.roles_xp_form",
        title="Set XP tier (level)",
        fields=(
            ModalFieldSpec(field_id="level",
                           label="XP level at which the role is granted",
                           placeholder="10", required=True,
                           min_length=1, max_length=4),
        ),
        on_submit=HandlerRef("setup.roles_xp_submit"))

    return PanelSpec(
        panel_id=ROLES_DETAIL_PANEL_ID,
        subsystem="setup",
        title="🎖️ Auto roles (time & XP)",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="roles_time_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.roles_time_role_pick"),
                placeholder="Time tier: pick a role to grant after N days…"),
            SelectorSpec(
                selector_id="roles_xp_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.roles_xp_role_pick"),
                placeholder="XP tier: pick a role to grant at a level…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="roles_time_days", label="Set time tier (days)",
                style=ActionStyle.PRIMARY,
                defer_mode=DeferMode.MODAL, modal=time_modal,
                handler=HandlerRef("setup.roles_time_submit")),
            PanelActionSpec(
                action_id="roles_xp_level", label="Set XP tier (level)",
                style=ActionStyle.PRIMARY,
                defer_mode=DeferMode.MODAL, modal=xp_modal,
                handler=HandlerRef("setup.roles_xp_submit")),
            PanelActionSpec(
                action_id="roles_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("roles_time_role",), ("roles_xp_role",),
            ("roles_time_days", "roles_xp_level"),
            ("roles_back_step",))),)),
        renderer_override=HandlerRef("setup.roles_detail_render"),
        justification=(
            "the shipped roles detail renders a live Detected field (the "
            "configured-tiers summary — roles._read_current_summary) and "
            "its threshold forms open off a role pick "
            "(_TimeRoleSelect/_XpRoleSelect.callback → send_modal) — a "
            "G-10 modal must be the interaction's FIRST response, so each "
            "pick reveals its declared defer_mode=MODAL button instead "
            "(the cleanup stepwise-reveal precedent), and the ↩ Back to "
            "step button rides only the wizard-native path — all outside "
            "the static grammar vocabulary; the override composes the "
            "embed and filters the components (no golden pins it — the "
            "oracle source does)."),
        session_lifecycle=True,
    )


async def _render_roles_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    summary = await read_current_summary(guild_id)
    embed = build_roles_embed(current_summary=summary)

    base = await render_panel(spec, ctx)
    key = f"{guild_id}:{user_id}"
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        leaf = c.custom_id.removeprefix(f"{spec.panel_id}.")
        if leaf == "roles_time_days" and key not in _PICKED_TIME_ROLE:
            continue    # the form opens after its role pick
        if leaf == "roles_xp_level" and key not in _PICKED_XP_ROLE:
            continue    # the form opens after its role pick
        if leaf == "roles_back_step" and not from_wizard:
            continue    # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers -----------------------------------------------------------------------------

def _picked_role_id(req) -> int | None:
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return None
    raw = str(values[0])
    return int(raw) if raw.lstrip("-").isdigit() else None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.roles_time_role_pick")):
        return

    @handler("setup.open_section_roles")
    async def open_section_roles(req) -> Reply | None:
        """The hub's Roles section button — gate exactly like the
        shipped hub button, land on the section card (roles.run →
        section_card.show), record the step marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    def _role_pick(store: dict, tier_word: str):
        async def _pick(req) -> Reply | None:
            """_TimeRoleSelect / _XpRoleSelect.callback, split: stash
            the picked role; the matching threshold form reveals on the
            refreshed card (module docstring ledger — the oracle opened
            the modal directly off the pick)."""
            from sb.domain.setup.wizard import _open, _refresh_own_panel

            role_id = _picked_role_id(req)
            if role_id is None:
                return Reply(BLOCKED, "No role picked.")
            store[_key(req)] = role_id
            if not await _refresh_own_panel(req, {}):
                await _open(req, ROLES_DETAIL_PANEL_ID)
            return None
        del tier_word
        return _pick

    handler("setup.roles_time_role_pick")(
        _role_pick(_PICKED_TIME_ROLE, "time"))
    handler("setup.roles_xp_role_pick")(
        _role_pick(_PICKED_XP_ROLE, "xp"))

    @handler("setup.roles_time_submit")
    async def roles_time_submit(req) -> Reply:
        """_TimeDaysModal.on_submit, ported (refusal copy verbatim);
        the staged label keeps the oracle bytes' shape over the id
        spelling (module docstring ledger)."""
        role_id = _PICKED_TIME_ROLE.get(_key(req))
        if role_id is None:
            # a stale form (state lost between reveal and submit) —
            # the picker instruction answers.
            return Reply(BLOCKED,
                         "Time tier: pick a role to grant after N days "
                         "first.")
        value = _parse_positive_int(
            str(req.args.get("days") or "").strip(), _MAX_DAYS)
        if value is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         f"⚠️ Enter a whole number of days between 1 and "
                         f"{_MAX_DAYS}.")
        role_name = str(role_id)
        return await _stage_threshold(
            req, kind=KIND_TIME, role_id=role_id, role_name=role_name,
            value=value,
            label=f"role tier: @{role_name} after {value}d")

    @handler("setup.roles_xp_submit")
    async def roles_xp_submit(req) -> Reply:
        """_XpLevelModal.on_submit, ported (refusal copy verbatim)."""
        role_id = _PICKED_XP_ROLE.get(_key(req))
        if role_id is None:
            return Reply(BLOCKED,
                         "XP tier: pick a role to grant at a level first.")
        value = _parse_positive_int(
            str(req.args.get("level") or "").strip(), _MAX_LEVEL)
        if value is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         f"⚠️ Enter a whole number level between 1 and "
                         f"{_MAX_LEVEL}.")
        role_name = str(role_id)
        return await _stage_threshold(
            req, kind=KIND_XP, role_id=role_id, role_name=role_name,
            value=value,
            label=f"role tier: @{role_name} at XP level {value}")


# --- registration -----------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.roles_detail_render")):
        handler("setup.roles_detail_render")(_render_roles_detail)
    if not is_registered(PanelRef(ROLES_DETAIL_PANEL_ID)):
        panel(ROLES_DETAIL_PANEL_ID)(roles_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    # NO recommended builder (roles.run: recommended_ops_builder=None —
    # no safe default tier exists).
    section_card.register_customize_panel(SLUG, ROLES_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_register()
_register_panels()
_register_section()
_register_set_role_threshold_op_kind()


def ensure_setup_roles_refs() -> None:
    _register()
    _register_panels()
    _register_section()
    _register_set_role_threshold_op_kind()
