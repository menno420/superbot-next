"""Access Map projection — side-effect-free composed read model (the
shipped P1A seam, ORACLE disbot/services/access_projection.py @HEAD,
ported over the COMPILED policy owners).

For a ``(feature, context)`` pair this answers **"is this allowed here,
and if not, why?"** by *composing the existing policy owners in a fixed
precedence*. It owns **no policy of its own** — there is no second
permission system; every ``allow``/``deny`` traces to an existing owner,
recorded in ``source_chain``.

**Read-only.** The projection calls async resolvers that *read* DB
policy, but it performs **no writes** and imports **no** mutation
service. It computes on demand and does **not** persist.

**Axes (shipped precedence order; short-circuits on the first ``deny``)
and the PORTED owner each delegates to:**

======  =================  ===============================================
 axis    name               owner in the compiled architecture
======  =================  ===============================================
 1+2     command access     ``platform.command_access.read_policy_snapshot``
                            + ``kernel.authority.channel_access.
                            resolve_channel_access`` (the shipped
                            resolver's ported channel lane; the K5
                            admission legs — lifecycle drain / DM — run
                            upstream of resolve() and are not
                            re-evaluated here)
 3       cog routing        NOT PORTED (a setup-wizard section slug only)
                            — recorded ``skipped``, never guessed
 4       governance         ``governance.resolve_visibility`` (the same
                            read every governance surface uses; the
                            Q-0045/D-0039 declared-tier path)
 5       availability       FUTURE central resolver — not built;
                            ``skipped`` (shipped posture verbatim)
 6       help visibility    the compiled help projection's category
                            staff-gate (sb/domain/help/categories.py) —
                            *informational only*; never flips an
                            execution ``allow`` to ``deny``
 7       user preference    FUTURE — can hide/sort, never grants
======  =================  ===============================================

The reason vocabulary reuses the ported owners' stable detail tokens
(``channel_access`` verdict details; governance ``subsystem_hidden``)
plus the shipped drafted denial-copy union in :data:`_SAFE_TEXT`.

Cycle discipline (the shipped module's rule, kept): every cross-package
import is **function-local**; top-level imports are stdlib only.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger("sb.domain.server_management.access_projection")

_PROJECTION_VERSION = 1


# ---------------------------------------------------------------------------
# Public types (shipped shapes, headless — D-0039: ids + declared facts)
# ---------------------------------------------------------------------------


class AccessAxis(enum.Enum):
    """The composed policy axes, in evaluation order (shipped verbatim)."""

    COMMAND_ACCESS = "command_access"  # axes 1+2 (channel admission)
    ROUTING = "routing"                # axis 3 (not ported — skipped)
    GOVERNANCE = "governance"          # axis 4 (visibility + tier)
    AVAILABILITY = "availability"      # axis 5 (future — stubbed)
    HELP = "help"                      # axis 6 (informational, non-gating)
    PREFERENCE = "preference"          # axis 7 (future — never grants)


# An axis result. ``allow``/``deny`` gate the effective decision (for axes
# 1-5); ``unknown`` means the owner could not resolve (does not gate, but
# blocks a confident ``allow``); ``skipped`` is a deliberately-not-evaluated
# axis and never affects the result; ``shown``/``hidden`` are the help
# axis's non-gating states.
AxisState = Literal["allow", "deny", "unknown", "skipped", "shown", "hidden"]

# The effective access result for a feature.
Effective = Literal["allow", "deny", "unknown"]


@dataclass(frozen=True)
class LockedReason:
    """A structured, *user-safe* explanation of a denial.

    ``safe_text`` is renderable to any audience and **never** leaks a role
    name, channel id, or policy internal — it is drawn from the static
    :data:`_SAFE_TEXT` table, not interpolated from context.
    """

    code: str
    safe_text: str
    source: str
    unlock_hint: str | None = None


@dataclass(frozen=True)
class AxisOutcome:
    """One axis's contribution to the decision chain.

    ``detail`` is an *internal* diagnostic string (it may name the
    source/mode) and is **not** rendered to users — only
    :attr:`LockedReason.safe_text` is.
    """

    axis: AccessAxis
    state: AxisState
    reason_code: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class AccessDecision:
    """The composed effective access for one feature in one context."""

    feature: str  # subsystem key (snake_case) — the unit of the read model
    command_name: str | None  # the representative command evaluated, if any
    effective: Effective
    deciding_axis: AccessAxis | None  # axis that produced a deny, else None
    reason: LockedReason | None  # populated on deny
    source_chain: tuple[AxisOutcome, ...]  # every axis evaluated, in order
    remediation: str | None = None  # safe pointer to the owning surface


@dataclass(frozen=True)
class FeatureEntry:
    """One row of the feature inventory (registry + manifest)."""

    subsystem: str
    command_name: str | None  # representative command (first declared)
    visibility_tier: str | None


@dataclass(frozen=True)
class AccessContext:
    """Explicit, fully-specified input to the projection (no implicit
    globals) — HEADLESS per D-0039: ids + declared facts, no gateway
    objects. Building one performs no I/O; the resolvers it is passed to
    do their own (read-only) lookups.

    ``member_tier`` is the **audience-simulation input** (the shipped
    Q-0045 option-b path): when set, the governance axis evaluates as
    that declared tier — governance's own tier resolution prefers a
    declared tier verbatim. Simulated contexts must label their limits:
    a declared tier cannot model live Discord channel-permission
    overrides the simulation was not given.
    """

    guild_id: int | None
    channel_id: int | None = None
    category_id: int | None = None
    user_id: int | None = None
    member_role_ids: tuple[int, ...] = ()
    member_tier: str | None = None
    is_guild_operator: bool = False
    is_bot_owner: bool = False
    invocation_type: str = "prefix"  # "prefix" | "slash"


# ---------------------------------------------------------------------------
# User-safe reason text. Static strings only — never interpolate context
# (this is what keeps `safe_text` leak-free). The shipped drafted
# denial-copy union, verbatim, plus ONE compiled-architecture row:
# `role_not_held` (the R-16 per-channel role-set constraint the ported
# channel lane can deny with — the shipped resolver had no such leg).
# ---------------------------------------------------------------------------

# code -> (safe_text, source, unlock_hint, remediation)
_SAFE_TEXT: dict[str, tuple[str, str, str | None, str | None]] = {
    # axis 1+2 — command_access
    "lifecycle_draining": (
        "The bot is restarting — try again in a moment.",
        "command_access",
        "retry shortly",
        None,
    ),
    "dm_not_supported": (
        "This command isn't available in direct messages.",
        "command_access",
        "use it inside the server",
        None,
    ),
    "commands_disabled": (
        "Commands are currently disabled in this server.",
        "command_access",
        None,
        "Enable commands in the Command Access settings.",
    ),
    "channel_not_allowed": (
        "This command isn't enabled in this channel.",
        "command_access",
        "try one of the server's command channels",
        "Add this channel in the Command Access settings.",
    ),
    # R-16 (compiled architecture only): per-channel role-set constraint.
    "role_not_held": (
        "Commands in this channel are limited to specific roles.",
        "command_access",
        None,
        "Adjust the channel's role list in the Command Access settings.",
    ),
    # axis 3 — routing
    "routing_disabled": (
        "This feature is turned off here.",
        "routing",
        None,
        "Re-enable the feature in the Cog Routing setup section.",
    ),
    # axis 4 — governance
    "subsystem_hidden": (
        "You don't have access to this feature here.",
        "governance",
        None,
        None,
    ),
    "capability_insufficient": (
        "You don't have permission to do that here.",
        "governance",
        None,
        None,
    ),
    # axis 5 — availability (future)
    "availability_window": (
        "This feature isn't available right now.",
        "availability",
        "try again later",
        None,
    ),
    "quiet_mode": (
        "The server is in quiet hours — this feature is paused.",
        "availability",
        "try again after quiet hours",
        "Adjust quiet hours in the Availability settings.",
    ),
    # bootstrap — setup staging
    "setup_stage_required": (
        "This feature isn't set up yet.",
        "bootstrap",
        None,
        "Finish this feature's setup in the setup wizard.",
    ),
}

_GENERIC_DENIAL = LockedReason(
    code="access_denied",
    safe_text="You can't use this feature here right now.",
    source="unknown",
)


def _locked_reason(reason_code: str | None) -> tuple[LockedReason, str | None]:
    """Map a stable reason code to a user-safe ``LockedReason`` +
    remediation.

    Falls back to a generic denial for an unmapped code so the renderer
    can never crash on a new code and never leaks an internal string.
    """
    if reason_code and reason_code in _SAFE_TEXT:
        text, source, hint, remediation = _SAFE_TEXT[reason_code]
        return (
            LockedReason(
                code=reason_code,
                safe_text=text,
                source=source,
                unlock_hint=hint,
            ),
            remediation,
        )
    return _GENERIC_DENIAL, None


def safe_locked_reason(reason_code: str | None) -> LockedReason:
    """Public read-only lookup: stable reason code → user-safe copy.

    Same fallback contract as the internal resolver: an unmapped code
    yields the generic denial, never a crash or an internal string.
    """
    return _locked_reason(reason_code)[0]


# ---------------------------------------------------------------------------
# Feature inventory adapter
# ---------------------------------------------------------------------------


def feature_inventory() -> tuple[FeatureEntry, ...]:
    """Enumerate every subsystem as a feature row.

    The inventory source is the governance registry's shipped
    ``SUBSYSTEM_META`` (the verbatim 43-row harvest of the shipped
    ``SUBSYSTEMS`` dict — the exact table the oracle projection read via
    ``utils.subsystem_registry``); the representative ``command_name`` is
    the subsystem's first declared manifest command (qualified name, the
    live inventory the help projection derives — the compiled analog of
    the shipped ``entry_points[0]``). A registry row whose subsystem has
    no ported manifest yet carries ``command_name=None`` and the
    command-access axis records ``skipped`` for it — never a guess.
    """
    from sb.domain.governance.registry import SUBSYSTEM_META
    from sb.domain.help.service import command_inventory

    inventory = command_inventory()
    out: list[FeatureEntry] = []
    for key, meta in SUBSYSTEM_META.items():
        commands = inventory.get(key, ())
        out.append(
            FeatureEntry(
                subsystem=key,
                command_name=commands[0][0] if commands else None,
                visibility_tier=meta.get("visibility_tier"),
            ),
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# Axis evaluators — each delegates to an existing owner, never decides policy
# ---------------------------------------------------------------------------


async def _axis_command_access(
    feature: FeatureEntry,
    ctx: AccessContext,
) -> AxisOutcome:
    """Axes 1+2 — channel admission via the ported command-access owner
    (``read_policy_snapshot`` + ``resolve_channel_access``).

    The shipped resolver also carried the lifecycle-drain and DM legs;
    in the compiled architecture those are K5 admission (upstream of
    resolve()) and are not re-evaluated by a read model. The simulated
    audience is never the owner-override, so ``owner_override=False``;
    the bootstrap bypass evaluates exactly as shipped.
    """
    if feature.command_name is None:
        return AxisOutcome(
            AccessAxis.COMMAND_ACCESS,
            "skipped",
            detail="no representative command",
        )
    if ctx.guild_id is None:
        return AxisOutcome(AccessAxis.COMMAND_ACCESS, "skipped",
                           detail="no guild")
    from sb.domain.platform.command_access import read_policy_snapshot
    from sb.kernel.authority.channel_access import resolve_channel_access
    from sb.namespace.bootstrap import is_bootstrap_command

    try:
        policy = await read_policy_snapshot(int(ctx.guild_id))
        decision = await resolve_channel_access(
            policy,
            ctx.channel_id,
            owner_override=False,
            is_bootstrap=is_bootstrap_command(feature.command_name),
            is_operator=ctx.is_guild_operator,
            is_owner=ctx.is_bot_owner,
            actor_role_ids=frozenset(ctx.member_role_ids),
        )
    except Exception as exc:  # noqa: BLE001 — a read model must never crash
        logger.warning(
            "access_projection: command_access axis raised: %s", exc)
        return AxisOutcome(
            AccessAxis.COMMAND_ACCESS,
            "unknown",
            detail="resolver error",
        )
    if decision.allowed:
        detail = None
        if decision.bootstrap_bypass:
            detail = "bootstrap bypass"
        return AxisOutcome(AccessAxis.COMMAND_ACCESS, "allow", detail=detail)
    return AxisOutcome(
        AccessAxis.COMMAND_ACCESS,
        "deny",
        reason_code=decision.detail or None,
        detail=f"mode={decision.mode.value if decision.mode else None}",
    )


def _axis_routing(feature: FeatureEntry, ctx: AccessContext) -> AxisOutcome:
    """Axis 3 — per-channel cog routing.

    NOT PORTED: the compiled architecture carries cog routing only as a
    setup-wizard section slug (sb/domain/setup/sections.py) — there is no
    live routing resolver to delegate to. A ``skipped`` axis never
    affects the effective result; it is recorded so the chain documents
    the axis exists and is intentionally inert until the routing port.
    """
    del feature, ctx
    return AxisOutcome(
        AccessAxis.ROUTING,
        "skipped",
        detail="cog routing not ported (setup-wizard section only)",
    )


async def _axis_governance(
    feature: FeatureEntry,
    ctx: AccessContext,
) -> AxisOutcome:
    """Axis 4 — subsystem visibility + member tier via governance.

    Reuses ``governance.resolve_visibility`` — the exact read every
    governance surface uses — so there is no duplicate visibility logic.

    **Audience simulation (Q-0045 option b, D-0039):** when
    ``ctx.member_tier`` is set it is passed through to governance, whose
    tier resolution prefers a declared tier verbatim. A context with *no*
    resolved member facts but a declared tier therefore evaluates instead
    of degrading to ``unknown``. The outcome ``detail`` labels the
    simulation and its limit (a declared tier cannot model live Discord
    channel-permission overrides).
    """
    if ctx.member_tier is None and ctx.user_id is None:
        # Without declared member facts we cannot evaluate tier/visibility;
        # report unknown rather than guess (a guess could falsely allow).
        return AxisOutcome(AccessAxis.GOVERNANCE, "unknown",
                           detail="no member")
    from sb.domain.governance.models import GovernanceContext
    from sb.domain.governance.resolver import resolve_visibility

    simulated = (
        f"simulated tier={ctx.member_tier} "
        "(live channel-permission overrides not modeled)"
        if ctx.member_tier is not None
        else None
    )
    gctx = GovernanceContext(
        guild_id=ctx.guild_id or 0,
        channel_id=ctx.channel_id,
        category_id=ctx.category_id,
        user_id=ctx.user_id,
        role_ids=set(ctx.member_role_ids),
        member_tier=ctx.member_tier,
    )
    try:
        result = await resolve_visibility(gctx)
    except Exception as exc:  # noqa: BLE001
        logger.warning("access_projection: governance axis raised: %s", exc)
        return AxisOutcome(AccessAxis.GOVERNANCE, "unknown",
                           detail="resolver error")
    if feature.subsystem in result.visible_subsystems:
        return AxisOutcome(AccessAxis.GOVERNANCE, "allow", detail=simulated)
    deny_detail = f"required_tier={feature.visibility_tier}"
    if simulated is not None:
        deny_detail = f"{deny_detail}; {simulated}"
    return AxisOutcome(
        AccessAxis.GOVERNANCE,
        "deny",
        reason_code="subsystem_hidden",
        detail=deny_detail,
    )


def _axis_availability(feature: FeatureEntry,
                       ctx: AccessContext) -> AxisOutcome:
    """Axis 5 — central availability policy. Not built yet → skipped
    (shipped posture verbatim).

    A ``skipped`` axis never affects the effective result; it is recorded
    so the chain documents that the axis exists and is intentionally
    inert today.
    """
    del feature, ctx
    return AxisOutcome(
        AccessAxis.AVAILABILITY,
        "skipped",
        detail="availability policy not implemented",
    )


def _axis_help_visibility(feature: FeatureEntry,
                          ctx: AccessContext) -> AxisOutcome:
    """Axis 6 — help visibility (informational ONLY; never gates
    execution).

    The compiled help projection's only hiding rule is the category
    staff-gate (sb/domain/help/service.py ``_visible_categories``: the
    moderation/admin mother hubs render for operators only — the shipped
    gate, goldens-pinned). For a simulated tier the operator-ness is
    modeled as ``tier >= moderator`` (the two staff hubs' member tiers);
    a real invoker context uses its declared operator facts.
    """
    if feature.command_name is None:
        return AxisOutcome(
            AccessAxis.HELP,
            "skipped",
            detail="no representative command",
        )
    from sb.domain.governance.tiers import tier_at_or_above
    from sb.domain.help import categories as cats

    category = cats.category_by_key(
        cats.category_for_subsystem(feature.subsystem))
    if category is None:
        return AxisOutcome(AccessAxis.HELP, "unknown",
                           detail="no category mapping")
    if not category.staff_only:
        return AxisOutcome(AccessAxis.HELP, "shown")
    if ctx.member_tier is not None:
        try:
            is_staff = tier_at_or_above(ctx.member_tier, "moderator")
        except (ValueError, KeyError):
            is_staff = False
        detail = "simulated staff-gate: tier >= moderator"
    else:
        is_staff = ctx.is_guild_operator or ctx.is_bot_owner
        detail = "declared operator facts"
    return AxisOutcome(
        AccessAxis.HELP,
        "shown" if is_staff else "hidden",
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------

# Axes 1-5 gate the effective result, evaluated in this order; the first
# ``deny`` short-circuits. Axis 6 is appended as non-gating context.
_GATING_DENY_ORDER = (
    AccessAxis.COMMAND_ACCESS,
    AccessAxis.ROUTING,
    AccessAxis.GOVERNANCE,
    AccessAxis.AVAILABILITY,
)


async def resolve_feature_access(
    feature: FeatureEntry,
    ctx: AccessContext,
) -> AccessDecision:
    """Compose every axis into one :class:`AccessDecision` (read-only).

    Short-circuits on the first ``deny`` among the gating axes (1-5). If
    no axis denies but one returned ``unknown``, the effective result is
    ``unknown`` (the model never claims ``allow`` it could not verify).
    The help axis (6) is always recorded but can never change
    ``effective``.
    """
    chain: list[AxisOutcome] = []

    # Gating axes 1-5, in precedence order.
    ca = await _axis_command_access(feature, ctx)
    chain.append(ca)
    if ca.state == "deny":
        return _denied(feature, ca, chain)

    rt = _axis_routing(feature, ctx)
    chain.append(rt)
    if rt.state == "deny":
        return _denied(feature, rt, chain)

    gv = await _axis_governance(feature, ctx)
    chain.append(gv)
    if gv.state == "deny":
        return _denied(feature, gv, chain)

    av = _axis_availability(feature, ctx)
    chain.append(av)
    if av.state == "deny":
        return _denied(feature, av, chain)

    # Axis 6 — help visibility (informational; never gates).
    chain.append(_axis_help_visibility(feature, ctx))

    # No deny. If any gating axis was unknown, we cannot confidently allow.
    gating = {AccessAxis.COMMAND_ACCESS, AccessAxis.ROUTING,
              AccessAxis.GOVERNANCE}
    effective: Effective = (
        "unknown"
        if any(o.axis in gating and o.state == "unknown" for o in chain)
        else "allow"
    )
    return AccessDecision(
        feature=feature.subsystem,
        command_name=feature.command_name,
        effective=effective,
        deciding_axis=None,
        reason=None,
        source_chain=tuple(chain),
    )


def _denied(
    feature: FeatureEntry,
    outcome: AxisOutcome,
    chain: list[AxisOutcome],
) -> AccessDecision:
    reason, remediation = _locked_reason(outcome.reason_code)
    return AccessDecision(
        feature=feature.subsystem,
        command_name=feature.command_name,
        effective="deny",
        deciding_axis=outcome.axis,
        reason=reason,
        source_chain=tuple(chain),
        remediation=remediation,
    )


async def project_access_map(ctx: AccessContext) -> tuple[AccessDecision, ...]:
    """Project the access decision for **every** feature in one context.

    The batch surface the read-only Access Map panel renders. Pure
    composition over :func:`feature_inventory`; no persistence.
    """
    return tuple(
        [await resolve_feature_access(feature, ctx)
         for feature in feature_inventory()],
    )


__all__ = [
    "AccessAxis",
    "AccessContext",
    "AccessDecision",
    "AxisOutcome",
    "FeatureEntry",
    "LockedReason",
    "feature_inventory",
    "project_access_map",
    "resolve_feature_access",
    "safe_locked_reason",
]
