"""The ROLE-TEMPLATES section flow (the roles-family slice), ported
from the oracle (menno420/superbot, read from the LOCAL oracle clone:
views/setup/sections/role_templates.py +
services/setup_role_templates.py):

* the DETERMINISTIC CATALOGUE (``_TEMPLATES``, data verbatim): six
  built-in, opt-in, **permission-free** role bundles — community
  hierarchy / moderation team / gaming community / time progression /
  XP progression / support server; a :class:`RoleSuggestion` carries
  name, purpose, cosmetic defaults (colour / hoist / mentionable) and
  an optional time- or XP-tier — and **no permissions field by
  design** (the oracle module docstring: "no permissions unless a
  separately constrained future policy explicitly supports them");
* the PLANNER (``plan_template``, pure — no Discord/DB I/O): partition
  a template's roles into *create* vs *already-exists* against the
  guild's current role names; validation bounds shared with the
  manual roles section (1..3650 days, 1..1000 levels — the same legal
  range);
* the PICKER (``RoleTemplatesSectionView``, flow verbatim): pick a
  template (row 0) → the preview embed renders create-vs-exists with
  the summary counts → **"Stage N new roles"** (row 1; the stage
  button RE-PLANS against the live snapshot before staging) drafts
  one ``create_managed_role`` op per missing role and answers the
  shipped staged/pending confirmation;
* **Final Review remains the only apply gate** — this section never
  calls an apply pipeline; NO auto-recommended path
  (role_templates.run: "creating roles is a deliberate choice the
  operator makes after previewing a template, never part of a blanket
  'apply all recommended' sweep").

NOT :mod:`sb.domain.governance.role_templates` — that module declares
*permission-tier-mapped* governance roles for the provisioning
substrate; this is the setup wizard's user-facing cosmetic catalogue
(the oracle kept the two deliberately separate; so does this port).

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the ``create_managed_role`` op kind BINDS to the audited K7
  ``role.create_managed_role`` compound op (the compound-ops slice —
  this module's previous fail-closed decide-and-flag, resolved): the
  create EFFECT leg runs the oracle RoleLifecycleService's apply-time
  UNCONDITIONAL create through the RoleProvisioning port (dedupe stays
  at plan time — ``plan_template``), the tier leg is the oracle's
  best-effort threshold-fold companion (a failed tier never undoes the
  role), and the K7 engine's ONE central audit row carries the audit
  fact. The staged rows carry ``resource_name`` + ``role_template``
  (the binding's payload schema) and final-review renders the shipped
  label bytes from them;
* the guild's current roles ride the ADVISOR's guild snapshot seam;
  no role index is installed in this build, so the planner sees no
  existing roles (every template role plans as *create* — the
  cleanup headless-degrade class) and ``bot_can_manage_roles`` has no
  perms-bearing read (the plan-level warning arm stays dormant —
  planned with ``True``, ledgered);
* ``parse_color`` validates the ``#RRGGBB`` hex strings without a
  discord.Color carrier (fail-safe ``None`` on unparseable input, the
  shipped posture); the hex bytes ride the staged
  ``role_template`` spec unchanged;
* the oracle carried the role spec on ``metadata["role_template"]`` —
  staged K9 rows have no metadata dict, so the spec rides the payload
  (the target_name above-the-minimum precedent; the dispatcher-to-be
  reads it back from there);
* staged K9 rows carry no oracle metadata dict (source/confidence/
  risk/rollback_note) — the final_review.py ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "ACTION_CREATE",
    "ACTION_EXISTS",
    "MAX_NAME_LEN",
    "MAX_ROLES_PER_TEMPLATE",
    "MAX_TIME_DAYS",
    "MAX_XP_LEVEL",
    "PlannedRole",
    "ROLE_TEMPLATES_DETAIL_PANEL_ID",
    "RoleSuggestion",
    "RoleTemplate",
    "TemplatePlan",
    "build_role_templates_embed",
    "build_template_preview_embed",
    "ensure_setup_role_templates_refs",
    "get_template",
    "known_template_slugs",
    "list_templates",
    "list_templates_by_category",
    "parse_color",
    "plan_template",
    "reset_role_templates_state_for_tests",
    "role_templates_detail_spec",
    "suggestion_to_spec",
    "validate_suggestion",
    "validate_template",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "role_templates"
SUBSYSTEM = "roles"

ROLE_TEMPLATES_DETAIL_PANEL_ID = "setup.role_templates_detail"

_TEMPLATE_OPTIONS_PROVIDER = "setup.role_template_options"

_MAX_PREVIEW_LINES = 12

#: the shipped card copy, verbatim (role_templates.run's ``detected``).
_DETECTED_STATE = (
    "Built-in role bundles (community hierarchy, moderation team, time/XP "
    "progression, …). Click Customize to preview a template and stage the "
    "roles you don't have yet — Final review creates them. No permissions "
    "are ever granted.")


# --- safety bounds (setup_role_templates.py, verbatim) --------------------------------
# The time/XP ceilings mirror the manual roles section
# (sb/domain/setup/roles.py) so a template tier and a hand-set tier
# share the same legal range.

MAX_ROLES_PER_TEMPLATE = 25  # Discord single-select option cap + sanity
MAX_NAME_LEN = 100  # Discord role-name maximum
MAX_PURPOSE_LEN = 120
MAX_TIME_DAYS = 3650  # ~10 years
MAX_XP_LEVEL = 1000

# Planned-role actions (a suggestion either already exists in the guild
# or is proposed for creation).
ACTION_CREATE = "create"
ACTION_EXISTS = "exists"


@dataclass(frozen=True)
class RoleSuggestion:
    """One role a template proposes. Carries **no permissions field**
    on purpose — see the module docstring."""

    name: str
    purpose: str = ""
    color: str | None = None  # "#RRGGBB" hex, or None
    hoist: bool = False  # show separately in the member list
    mentionable: bool = False
    time_days: int | None = None  # optional time-in-server auto-role tier
    xp_level: int | None = None  # optional XP-level auto-role tier


@dataclass(frozen=True)
class RoleTemplate:
    """A named bundle of role suggestions."""

    slug: str
    display_name: str
    description: str
    category: str
    suggestions: tuple[RoleSuggestion, ...] = ()

    @property
    def role_count(self) -> int:
        return len(self.suggestions)


# --- validation / safety (setup_role_templates.py, verbatim semantics) ------------------

_HEX_COLOR = re.compile(r"^#?(?:[0-9a-fA-F]{6})$")


def parse_color(raw: str | None) -> int | None:
    """setup_role_templates.parse_color without the discord.Color
    carrier (module docstring ledger): the ``#RRGGBB`` value parses to
    its int, anything unparseable/empty returns ``None`` fail-safe
    (the role is created with the default colour) rather than
    raising."""
    if not raw:
        return None
    candidate = str(raw).strip()
    if not _HEX_COLOR.match(candidate):
        return None
    return int(candidate.lstrip("#"), 16)


def validate_suggestion(s: RoleSuggestion) -> list[str]:
    """Return a list of validation errors for ``s`` (empty == valid).

    Used to vet both the built-in catalogue (a pinned test) and, in a
    later slice, AI-generated suggestions before they are ever staged."""
    errors: list[str] = []
    name = (s.name or "").strip()
    if not name:
        errors.append("role name is empty")
    elif len(name) > MAX_NAME_LEN:
        errors.append(f"role name exceeds {MAX_NAME_LEN} chars: {name!r}")
    if name.lower() in ("@everyone", "everyone"):
        errors.append("a template must not create @everyone")
    if len(s.purpose or "") > MAX_PURPOSE_LEN:
        errors.append(f"purpose exceeds {MAX_PURPOSE_LEN} chars")
    if s.color is not None and parse_color(s.color) is None:
        errors.append(f"unparseable color {s.color!r}")
    if s.time_days is not None and not (1 <= s.time_days <= MAX_TIME_DAYS):
        errors.append(f"time_days {s.time_days!r} out of range "
                      f"1..{MAX_TIME_DAYS}")
    if s.xp_level is not None and not (1 <= s.xp_level <= MAX_XP_LEVEL):
        errors.append(f"xp_level {s.xp_level!r} out of range "
                      f"1..{MAX_XP_LEVEL}")
    return errors


def validate_template(t: RoleTemplate) -> list[str]:
    """Return a list of validation errors for ``t`` (empty == valid)."""
    errors: list[str] = []
    if not t.slug:
        errors.append("template slug is empty")
    if not t.suggestions:
        errors.append(f"template {t.slug!r} has no roles")
    if len(t.suggestions) > MAX_ROLES_PER_TEMPLATE:
        errors.append(
            f"template {t.slug!r} has {len(t.suggestions)} roles "
            f"(max {MAX_ROLES_PER_TEMPLATE})")
    seen: set[str] = set()
    for s in t.suggestions:
        key = (s.name or "").strip().lower()
        if key and key in seen:
            errors.append(f"duplicate role name in template {t.slug!r}: "
                          f"{s.name!r}")
        seen.add(key)
        errors.extend(f"{t.slug}.{s.name}: {e}"
                      for e in validate_suggestion(s))
    return errors


# --- planning (pure — no Discord / DB I/O; setup_role_templates.py verbatim) -------------

@dataclass(frozen=True)
class PlannedRole:
    """One template suggestion resolved against the guild's current
    roles."""

    suggestion: RoleSuggestion
    action: str  # ACTION_CREATE | ACTION_EXISTS
    existing_role_id: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemplatePlan:
    """A template resolved against a guild: what would be created vs
    reused."""

    template_slug: str
    planned: tuple[PlannedRole, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def to_create(self) -> tuple[PlannedRole, ...]:
        return tuple(p for p in self.planned if p.action == ACTION_CREATE)

    @property
    def existing(self) -> tuple[PlannedRole, ...]:
        return tuple(p for p in self.planned if p.action == ACTION_EXISTS)

    @property
    def create_count(self) -> int:
        return len(self.to_create)

    @property
    def exists_count(self) -> int:
        return len(self.existing)


def plan_template(
        template: RoleTemplate, *,
        existing_roles: dict[str, int] | None = None,
        bot_can_manage_roles: bool = True) -> TemplatePlan:
    """Partition a template's roles into *create* vs *already-exists*.

    Pure: no Discord or DB access. ``existing_roles`` maps
    ``role_name.lower()`` → role id (the operator's current guild
    roles); a suggestion whose name matches an existing role is marked
    :data:`ACTION_EXISTS` (and skipped at staging — re-creating would
    duplicate it). When ``bot_can_manage_roles`` is ``False`` a
    plan-level warning is added so the preview can tell the operator
    creation will be blocked at Final Review until Manage Roles is
    granted."""
    existing = {k.lower(): v for k, v in (existing_roles or {}).items()}
    planned: list[PlannedRole] = []
    warnings: list[str] = []
    if not bot_can_manage_roles:
        warnings.append(
            "the bot lacks the Manage Roles permission — creation will be "
            "blocked at Final Review until it is granted")
    for s in template.suggestions:
        key = (s.name or "").strip().lower()
        existing_id = existing.get(key)
        if existing_id is not None:
            planned.append(PlannedRole(
                suggestion=s, action=ACTION_EXISTS,
                existing_role_id=existing_id))
        else:
            planned.append(PlannedRole(
                suggestion=s, action=ACTION_CREATE,
                warnings=tuple(validate_suggestion(s))))
    return TemplatePlan(template_slug=template.slug, planned=tuple(planned),
                        warnings=tuple(warnings))


def suggestion_to_spec(s: RoleSuggestion, *, template_slug: str) -> dict[str, Any]:
    """Serialise a suggestion to the ``role_template`` payload ride
    (the oracle's ``metadata["role_template"]`` — module docstring
    ledger). This is the single source of truth for the role-spec shape
    carried on a ``create_managed_role`` op (the wizard section builds
    it; the dispatcher-to-be reads it back). Plain JSON-serialisable
    scalars only, so it round-trips through the draft store's payload
    unchanged."""
    return {
        "color": s.color,
        "hoist": bool(s.hoist),
        "mentionable": bool(s.mentionable),
        "time_days": s.time_days,
        "xp_level": s.xp_level,
        "purpose": s.purpose,
        "template_slug": template_slug,
    }


# --- the built-in deterministic catalogue (data verbatim) ---------------------------------
#
# Opt-in suggestions, never automatic creation.  Colours are plain hex
# so the data stays declarative; tiers are only on the progression
# templates.  None of these grant permissions — that is configured
# separately (e.g. the moderator-tier role in `!settings → Moderation`,
# ADR-008).

_TEMPLATES: tuple[RoleTemplate, ...] = (
    RoleTemplate(
        slug="community-hierarchy",
        display_name="Community hierarchy",
        description=(
            "A basic community ladder: owner / admin / moderator / member "
            "label roles (no permissions granted — wire those up separately)."),
        category="community",
        suggestions=(
            RoleSuggestion("Owner", "Server owner / founder", "#E91E63",
                           hoist=True),
            RoleSuggestion("Admin", "Trusted administrator", "#E74C3C",
                           hoist=True),
            RoleSuggestion("Moderator", "Day-to-day moderation", "#3498DB",
                           hoist=True),
            RoleSuggestion("Member", "Verified community member", "#2ECC71"),
        )),
    RoleTemplate(
        slug="moderation-team",
        display_name="Moderation team",
        description=(
            "Staff tiers for a moderation team. Pair the top tier with the "
            "`moderator_role` capability setting to actually grant powers."),
        category="moderation",
        suggestions=(
            RoleSuggestion("Head Moderator", "Lead of the mod team",
                           "#C0392B", hoist=True),
            RoleSuggestion("Moderator", "Full moderator", "#2980B9",
                           hoist=True),
            RoleSuggestion("Trial Moderator", "Moderator in training",
                           "#16A085", hoist=True),
            RoleSuggestion("Helper", "Answers questions, escalates issues",
                           "#27AE60"),
        )),
    RoleTemplate(
        slug="gaming-community",
        display_name="Gaming / event community",
        description=(
            "Cosmetic roles for a gaming or events server — recognition and "
            "event labels members can earn or be assigned."),
        category="gaming",
        suggestions=(
            RoleSuggestion("Veteran", "Long-time member", "#8E44AD",
                           hoist=True),
            RoleSuggestion("Regular", "Active participant", "#9B59B6"),
            RoleSuggestion("Newcomer", "Recently joined", "#95A5A6"),
            RoleSuggestion("Event Winner", "Won a community event",
                           "#F1C40F", mentionable=True),
            RoleSuggestion("Tournament Champion", "Tournament champion",
                           "#F39C12", hoist=True),
        )),
    RoleTemplate(
        slug="time-progression",
        display_name="Time-in-server progression",
        description=(
            "Auto-granted tenure roles: members earn each role after N days "
            "in the server (auto-role time tiers)."),
        category="progression",
        suggestions=(
            RoleSuggestion("Regular", "7 days in the server", "#1ABC9C",
                           hoist=True, time_days=7),
            RoleSuggestion("Veteran", "30 days in the server", "#3498DB",
                           hoist=True, time_days=30),
            RoleSuggestion("Elder", "90 days in the server", "#9B59B6",
                           hoist=True, time_days=90),
            RoleSuggestion("Legend", "365 days in the server", "#F1C40F",
                           hoist=True, time_days=365),
        )),
    RoleTemplate(
        slug="xp-progression",
        display_name="XP-level progression",
        description=(
            "Auto-granted XP roles: members earn each role at an XP level "
            "(auto-role XP tiers; needs the XP system enabled)."),
        category="progression",
        suggestions=(
            RoleSuggestion("Level 5", "Reached XP level 5", "#2ECC71",
                           xp_level=5),
            RoleSuggestion("Level 10", "Reached XP level 10", "#1ABC9C",
                           xp_level=10),
            RoleSuggestion("Level 25", "Reached XP level 25", "#3498DB",
                           hoist=True, xp_level=25),
            RoleSuggestion("Level 50", "Reached XP level 50", "#9B59B6",
                           hoist=True, xp_level=50),
            RoleSuggestion("Level 100", "Reached XP level 100", "#F1C40F",
                           hoist=True, xp_level=100),
        )),
    RoleTemplate(
        slug="support-server",
        display_name="Support server",
        description=(
            "Roles for a product / support server: a support team label plus "
            "verification and recognition roles for members."),
        category="support",
        suggestions=(
            RoleSuggestion("Support Team", "Handles support tickets",
                           "#E67E22", hoist=True),
            RoleSuggestion("Verified", "Verified customer / user", "#2ECC71"),
            RoleSuggestion("Contributor", "Contributes fixes or content",
                           "#3498DB"),
            RoleSuggestion("Bug Hunter", "Reported a confirmed bug",
                           "#E74C3C", mentionable=True),
        )),
)


def list_templates() -> tuple[RoleTemplate, ...]:
    """Return the built-in template catalogue."""
    return _TEMPLATES


def known_template_slugs() -> frozenset[str]:
    return frozenset(t.slug for t in _TEMPLATES)


def get_template(slug: str) -> RoleTemplate | None:
    for t in _TEMPLATES:
        if t.slug == slug:
            return t
    return None


def list_templates_by_category(category: str) -> tuple[RoleTemplate, ...]:
    return tuple(t for t in _TEMPLATES if t.category == category)


# --- embeds (role_templates.py, bytes verbatim) ---------------------------------------------

def build_role_templates_embed():
    """The picker embed — explains templates and lists the built-in
    catalogue."""
    from sb.kernel.panels.render import RenderedEmbed

    fields: list[tuple] = []
    for t in list_templates():
        tiers = sum(1 for s in t.suggestions if s.time_days or s.xp_level)
        tier_note = f" · {tiers} auto-role tier(s)" if tiers else ""
        fields.append((f"{t.display_name} · {t.role_count} roles",
                       f"{t.description}{tier_note}", False))
    return RenderedEmbed(
        title="🧩 Role templates",
        description=(
            "Pick a built-in template below to preview a set of roles, then "
            "stage the ones you don't have yet. **Staging creates nothing** — "
            "**Final review** applies the draft.\n\n"
            "Templates only *create roles* (for an existing server); they never "
            "grant permissions — set those up separately."),
        fields=tuple(fields),
        footer=("Pick a template to preview · Final review applies staged "
                "roles."),
        style_token="blurple")


def build_template_preview_embed(template: RoleTemplate, plan: TemplatePlan):
    """Render one template resolved against the guild (create vs
    exists)."""
    from sb.kernel.panels.render import RenderedEmbed

    lines: list[str] = []
    for p in plan.planned[:_MAX_PREVIEW_LINES]:
        s = p.suggestion
        attrs: list[str] = []
        if s.hoist:
            attrs.append("hoisted")
        if s.color:
            attrs.append(s.color)
        if s.time_days:
            attrs.append(f"{s.time_days}d tier")
        if s.xp_level:
            attrs.append(f"XP L{s.xp_level}")
        attr_str = f" ({', '.join(attrs)})" if attrs else ""
        if p.action == ACTION_EXISTS:
            lines.append(f"✅ @{s.name}{attr_str} — already exists (skip)")
        else:
            lines.append(f"➕ @{s.name}{attr_str}")
    if len(plan.planned) > _MAX_PREVIEW_LINES:
        lines.append(f"_+{len(plan.planned) - _MAX_PREVIEW_LINES} more…_")
    fields: list[tuple] = [
        ("Roles", "\n".join(lines) or "_(none)_", False),
        ("Summary",
         (f"➕ **{plan.create_count}** to create · "
          f"✅ {plan.exists_count} already exist"),
         False),
    ]
    if plan.warnings:
        fields.append(("⚠️ Heads up",
                       "\n".join(f"• {w}" for w in plan.warnings), False))
    return RenderedEmbed(
        title=f"🧩 {template.display_name}",
        description=template.description,
        fields=tuple(fields),
        footer=("“Stage new roles” adds them to the draft · Final review "
                "creates them."),
        style_token="blurple")


# --- planning against the guild (role_templates._compute_plan, adapted) ----------------------

async def _existing_roles(guild_id: int) -> dict[str, int]:
    """The guild's current role names → ids. No role index is installed
    in this build (module docstring ledger) — the planner degrades to
    the empty map (every template role plans as *create*)."""
    del guild_id
    return {}


async def compute_plan(guild_id: int, template: RoleTemplate) -> TemplatePlan:
    """role_templates._compute_plan over the ported seams: resolve the
    template against the guild's roles (headless ⇒ empty, ledgered);
    ``bot_can_manage_roles`` has no perms-bearing read here — planned
    ``True`` so the dormant warning arm never invents a refusal."""
    existing = await _existing_roles(int(guild_id))
    return plan_template(template, existing_roles=existing,
                         bot_can_manage_roles=True)


# --- the op-kind registration (the roles.py set_role_threshold precedent) --------------------

_CREATE_MANAGED_ROLE_OP_KIND = "create_managed_role"


def _register_create_managed_role_op_kind() -> None:
    """Bind the ``create_managed_role`` op kind onto the audited K7
    ``role.create_managed_role`` compound op (the module docstring's
    named successor, landed by the compound-ops slice): apply-time
    unconditional create through the RoleProvisioning port + the
    best-effort tier fold — the oracle's RoleLifecycleService route
    (setup_operations.py:1176 → _apply_create_managed_role:1723)."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_CREATE_MANAGED_ROLE_OP_KIND,
        workflow_ref=WorkflowRef("role.create_managed_role"),
        payload_schema=(FieldSpec("resource_name", "str"),
                        FieldSpec("role_template", "dict")),
        is_resource_create=True)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


# --- draft staging (role_templates.py, semantics verbatim) -----------------------------------

def _normalise_name(name: str) -> str:
    """Slugify a role name for use as a per-role draft-slot
    discriminator."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug or "role"


def _op_label(s: RoleSuggestion) -> str:
    label = f"create role @{s.name}"
    if s.time_days:
        label += f" +{s.time_days}d"
    if s.xp_level:
        label += f" +L{s.xp_level}"
    return label


def _build_create_op(s: RoleSuggestion, *, template: RoleTemplate):
    """One ``create_managed_role`` StagedSectionOp for a template
    suggestion. ``name`` carries the per-role slug only as the draft
    SLOT-KEY discriminator (the oracle ``binding_name`` note: without
    it every template role would collide on one slot and only the last
    would survive); the dispatcher-to-be reads ``resource_name`` +
    ``role_template``, never the slot name."""
    from sb.domain.setup.section_card import StagedSectionOp

    return StagedSectionOp(
        op_kind="create_managed_role", subsystem=SUBSYSTEM,
        payload={"name": f"role:{_normalise_name(s.name)}",
                 "resource_name": s.name,
                 "resource_mode": "create",
                 "role_template": suggestion_to_spec(
                     s, template_slug=template.slug)},
        label_body=_op_label(s))


async def _stage_creations(req, *, template: RoleTemplate,
                           plan: TemplatePlan) -> Reply:
    """role_templates._stage_creations, ported onto the K9 spine: one
    ``create_managed_role`` op per not-yet-existing role (per-op
    isolation, the shipped posture), the shipped confirmations
    verbatim."""
    from sb.domain.setup import section_card, wizard
    from sb.domain.setup.wizard import _refresh_own_panel

    _register_create_managed_role_op_kind()
    guild_id = int(req.guild_id or 0)
    if not guild_id:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This can only be used in a server.")
    to_create = plan.to_create
    if not to_create:
        # shipped copy, verbatim.
        return Reply(SUCCESS,
                     f"✅ Every role in **{template.display_name}** already "
                     "exists — nothing to create.")
    staged = 0
    for planned in to_create:
        op = _build_create_op(planned.suggestion, template=template)
        try:
            await section_card.stage_custom(guild_id, SLUG, op)
            staged += 1
        except Exception:  # noqa: BLE001 — per-op isolation (shipped)
            logger.exception(
                "role_templates: setup_draft.append failed for %r",
                planned.suggestion.name)
    if staged == 0:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "Could not stage the roles — see logs.")
    await section_card.mark_step_in_progress(req, SLUG)
    try:
        pending = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped count soft-fail
        logger.exception("role_templates: setup_draft.count failed")
        pending = staged
    await _refresh_own_panel(req, {})
    # shipped confirmation, verbatim.
    return Reply(SUCCESS,
                 f"✅ Staged **{staged}** new role(s) from "
                 f"**{template.display_name}** for Final review. Pending "
                 f"operations: **{pending}**. Nothing is created until you "
                 "apply.")


# --- flow state --------------------------------------------------------------------------------

#: guild:user → the selected template slug (the oracle held it on the
#: view instance; restart forgets it the same way).
_SELECTED: dict[str, str] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def reset_role_templates_state_for_tests() -> None:
    _SELECTED.clear()


# --- the detail panel ----------------------------------------------------------------------------

def role_templates_detail_spec():
    """RoleTemplatesSectionView folded onto one panel: the template
    picker (row 0, placeholder verbatim), the stage button (row 1 —
    created on first selection in the oracle; state-revealed here, its
    dynamic count label patched at render), and the wizard-origin
    ↩ Back to step button."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=ROLE_TEMPLATES_DETAIL_PANEL_ID,
        subsystem="setup",
        title="🧩 Role templates",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="tmpl_pick", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.role_template_pick"),
                options_source=ProviderRef(_TEMPLATE_OPTIONS_PROVIDER),
                placeholder="Pick a role template to preview…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="tmpl_stage", label="Stage new roles",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.role_template_stage")),
            PanelActionSpec(
                action_id="tmpl_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("tmpl_pick",), ("tmpl_stage",), ("tmpl_back_step",))),)),
        renderer_override=HandlerRef("setup.role_templates_detail_render"),
        justification=(
            "the shipped role-templates detail swaps its embed per pick "
            "(the catalogue picker vs the per-template create/exists "
            "preview — build_template_preview_embed), its stage button is "
            "created on first selection with a per-plan count label + "
            "disabled state (RoleTemplatesSectionView._sync_stage_button) "
            "and the ↩ Back to step button rides only the wizard-native "
            "path — all outside the static grammar vocabulary; the "
            "override composes the embed and filters/patches the "
            "components (no golden pins it — the oracle source does)."),
        session_lifecycle=True,
    )


def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_TEMPLATE_OPTIONS_PROVIDER)):
        return

    @provider(_TEMPLATE_OPTIONS_PROVIDER)
    async def template_options(ctx):
        """_TemplateSelect's options, verbatim caps; the current pick
        pre-selected."""
        picked = _SELECTED.get(_key(ctx), "")
        return tuple(
            {"label": t.display_name[:100], "value": t.slug,
             "description": f"{t.role_count} roles · {t.category}"[:100],
             "default": t.slug == picked}
            for t in list_templates())


async def _render_role_templates_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    slug = _SELECTED.get(_key(ctx), "")
    template = get_template(slug) if slug else None
    plan = None
    if template is not None:
        plan = await compute_plan(guild_id, template)
        embed = build_template_preview_embed(template, plan)
    else:
        embed = build_role_templates_embed()

    base = await render_panel(spec, ctx)
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        leaf = c.custom_id.removeprefix(f"{spec.panel_id}.")
        if leaf == "tmpl_stage":
            if plan is None:
                continue    # the button is created on first selection
            n = plan.create_count
            # shipped label bytes + disabled state, verbatim
            # (_sync_stage_button).
            c = dataclasses.replace(
                c,
                label=(f"Stage {n} new role{'s' if n != 1 else ''}"
                       if n else "Nothing new to stage"),
                disabled=n == 0)
        elif leaf == "tmpl_back_step" and not from_wizard:
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers --------------------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.role_template_pick")):
        return

    @handler("setup.open_section_role_templates")
    async def open_section_role_templates(req) -> Reply | None:
        """The hub's Role-templates section button — gate exactly like
        the shipped hub button, land on the section card
        (role_templates.run → section_card.show), record the step
        marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    @handler("setup.role_template_pick")
    async def role_template_pick(req) -> Reply | None:
        """_TemplateSelect.callback → on_template_selected, ported:
        stash the pick; the preview embed + the synced stage button
        render on the refreshed card (the oracle edit_message)."""
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        slug = str(values[0]) if values else ""
        if get_template(slug) is None:
            # shipped copy, verbatim (on_template_selected).
            return Reply(BLOCKED, "Could not load that template.")
        _SELECTED[_key(req)] = slug
        if not await _refresh_own_panel(req, {}):
            await _open(req, ROLE_TEMPLATES_DETAIL_PANEL_ID)
        return None

    @handler("setup.role_template_stage")
    async def role_template_stage(req) -> Reply:
        """The stage button (_on_stage), ported: gate (the channels-flow
        additive fence), RE-PLAN against the live guild before staging
        (the shipped comment: "a role may have been created since the
        preview was rendered"), stage the remainder."""
        from sb.domain.setup import section_card

        template = get_template(_SELECTED.get(_key(req), ""))
        if template is None:
            # shipped copy, verbatim (_on_stage).
            return Reply(BLOCKED, "Pick a template first.")
        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        plan = await compute_plan(int(req.guild_id or 0), template)
        return await _stage_creations(req, template=template, plan=plan)


# --- registration ------------------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.role_templates_detail_render")):
        handler("setup.role_templates_detail_render")(
            _render_role_templates_detail)
    if not is_registered(PanelRef(ROLE_TEMPLATES_DETAIL_PANEL_ID)):
        panel(ROLE_TEMPLATES_DETAIL_PANEL_ID)(role_templates_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    # NO recommended builder (role_templates.run:
    # recommended_ops_builder=None — the hub sweep must never silently
    # create roles).
    section_card.register_customize_panel(SLUG,
                                          ROLE_TEMPLATES_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_ensure_providers()
_register()
_register_panels()
_register_section()
_register_create_managed_role_op_kind()


def ensure_setup_role_templates_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_section()
    _register_create_managed_role_op_kind()
