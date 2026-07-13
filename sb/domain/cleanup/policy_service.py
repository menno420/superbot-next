"""The cleanup-policy operator service — diagnostics, dry-run preview,
audited apply/remove (the 🧹 Cleanup Policies slice), ported from the
oracle's ``disbot/services/cleanup_diagnostics.py`` @9776401 onto this
engine's seams:

* :func:`collect_cleanup_diagnostics` — read-only inheritance/health
  report over ``governance.store.get_all_cleanup_for_guild``: every
  stored policy named back to its level (``level_for_columns``),
  stale-scope detection (channel/category no longer in the guild
  roster) and ineffective-row detection (a legacy guild row keyed by
  anything other than ``guild_id`` is never read by the resolver).
* :func:`preview_cleanup_columns` / :func:`preview_cleanup_change` —
  side-effect-free dry-run: what a scope currently resolves to via the
  REAL :func:`sb.domain.governance.cleanup.resolve_cleanup_policy`
  (preview == runtime, the oracle's reuse-never-reimplement doctrine)
  and what it would resolve to after the change. Writes nothing.
* :func:`apply_cleanup_columns` / :func:`remove_cleanup_change` — the
  audited writes through the K7 ``governance.set_cleanup`` /
  ``governance.remove_cleanup`` ops via the
  ``sb/domain/governance/service.py`` wrappers (row + governance audit
  in one txn, post-commit cache invalidation — the shipped
  GovernanceMutationPipeline twin the wizard slice armed).

Level vocabulary: imported from ``sb.domain.setup.cleanup`` (LEVELS +
``cleanup_scope_id`` — the oracle kept ``services/cleanup_levels.py``
as the single source both the wizard and this panel read; next mirrors
that with the wizard's port as the source). ``level_for_columns`` (the
inverse map the wizard never needed) lives here.

Scope labels + staleness ride the ai guild-scope roster port
(:func:`sb.domain.ai.policy_widgets.guild_scope_roster` — the ONE
guild channel/category enumeration seam). Ledgered degrade: an
uninstalled/empty roster (headless replay, DB-free boot) names scopes
by mention/raw id and flags NOTHING stale — the oracle's
``guild.get_channel`` read had live gateway state; a headless "every
row is stale" report would be a false alarm, never shipped.

Layer: domain → kernel/spec + the governance and ai domain seams (the
repo's established cross-domain import class).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.domain.setup.cleanup import LEVELS, cleanup_scope_id

__all__ = [
    "CLEANUP_SCOPE_TYPES",
    "CUSTOM_LEVEL_LABEL",
    "CleanupDiagnostics",
    "CleanupPolicyPreview",
    "CleanupScopeRow",
    "MAX_DELETE_AFTER_SECONDS",
    "apply_cleanup_columns",
    "collect_cleanup_diagnostics",
    "known_level_names",
    "level_for_columns",
    "preview_cleanup_change",
    "preview_cleanup_columns",
    "remove_cleanup_change",
    "scope_labels",
]

#: cleanup scopes the resolver honours (RC-5: no thread scope) — the
#: oracle constant verbatim.
CLEANUP_SCOPE_TYPES: frozenset[str] = frozenset({"guild", "category", "channel"})

#: bounds for a custom ``delete_after_seconds`` (0 = delete immediately;
#: 5-minute ceiling) — the oracle constant verbatim.
MAX_DELETE_AFTER_SECONDS = 300

CUSTOM_LEVEL_LABEL = "Custom"


def known_level_names() -> frozenset[str]:
    """The operator-facing preset names (cleanup_levels.py verbatim)."""
    return frozenset(LEVELS)


def level_for_columns(*, delete_invalid_commands: bool,
                      delete_failed_commands: bool,
                      delete_after_seconds: int) -> str | None:
    """Name a stored row's three columns back to its preset level, else
    ``None`` (an operator-tuned policy → the caller renders "Custom").
    The oracle ``cleanup_levels.level_for_columns`` verbatim — the four
    presets have distinct column tuples, so the match is unambiguous."""
    for name, cols in LEVELS.items():
        if (cols["delete_invalid_commands"] == delete_invalid_commands
                and cols["delete_failed_commands"] == delete_failed_commands
                and cols["delete_after_seconds"] == delete_after_seconds):
            return name
    return None


# ---------------------------------------------------------------------------
# Read model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CleanupScopeRow:
    """One stored ``cleanup_policies`` row, named and health-checked
    (the oracle dataclass minus ``policy_version`` — next's row read
    carries the three behaviour columns only)."""

    scope_type: str
    scope_id: int
    level_name: str | None  # None → operator-tuned ("Custom")
    delete_invalid_commands: bool
    delete_failed_commands: bool
    delete_after_seconds: int
    target_label: str
    is_stale: bool  # channel/category no longer exists (roster-attested)
    is_ineffective: bool  # guild row not keyed by guild_id → never read

    @property
    def display_level(self) -> str:
        return self.level_name or CUSTOM_LEVEL_LABEL


@dataclass(frozen=True)
class CleanupDiagnostics:
    """Aggregated per-guild cleanup-policy health report (oracle twin)."""

    guild_id: int
    rows: tuple[CleanupScopeRow, ...]
    level_counts: dict[str, int]

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def stale_rows(self) -> tuple[CleanupScopeRow, ...]:
        return tuple(r for r in self.rows if r.is_stale)

    @property
    def ineffective_rows(self) -> tuple[CleanupScopeRow, ...]:
        return tuple(r for r in self.rows if r.is_ineffective)


@dataclass(frozen=True)
class _ScopeNames:
    """The roster read folded to what the panel needs: name maps + the
    channel → category index. ``attested`` False = the roster port is
    uninstalled/empty — labels degrade to mentions, staleness is never
    flagged (module-doc ledger)."""

    channels: dict[int, str]
    categories: dict[int, str]
    channel_category: dict[int, int | None]
    attested: bool


async def scope_labels(guild_id: int) -> _ScopeNames:
    from sb.domain.ai.policy_widgets import guild_scope_roster

    roster = await guild_scope_roster(int(guild_id))
    channels = {int(cid): str(name)
                for cid, name, _cat in roster.text_channels}
    categories = {int(cid): str(name) for cid, name in roster.categories}
    channel_category = {int(cid): (int(cat) if cat is not None else None)
                        for cid, name, cat in roster.text_channels}
    attested = bool(channels or categories)
    return _ScopeNames(channels=channels, categories=categories,
                       channel_category=channel_category, attested=attested)


def _target_label(names: _ScopeNames, guild_id: int, scope_type: str,
                  scope_id: int) -> tuple[str, bool]:
    """``(label, is_stale)`` for a scope row — the oracle ``_target_label``
    over the roster port (mention/raw-id degrade when unattested)."""
    if scope_type == "guild":
        return "Guild default", False
    if not names.attested:
        # headless/uninstalled roster: mention labels, never stale.
        if scope_type == "category":
            return f"Category {scope_id}", False
        return f"<#{scope_id}>", False
    if scope_type == "category":
        name = names.categories.get(int(scope_id))
        if name is None:
            return f"category {scope_id} (deleted)", True
        return f"Category {name}", False
    name = names.channels.get(int(scope_id))
    if name is None:
        return f"channel {scope_id} (deleted)", True
    return f"#{name}", False


async def collect_cleanup_diagnostics(guild_id: int) -> CleanupDiagnostics:
    """Read-only inheritance + health report for a guild's cleanup
    policies (the oracle flow: raw rows → named/level'd/flagged rows →
    stable guild-first ordering + level counts)."""
    from sb.domain.governance import store as gov_store

    raw = await gov_store.get_all_cleanup_for_guild(int(guild_id))
    names = await scope_labels(int(guild_id))
    rows: list[CleanupScopeRow] = []
    level_counts: dict[str, int] = {}
    for r in raw:
        scope_type = str(r["scope_type"])
        scope_id = int(r["scope_id"])
        level_name = level_for_columns(
            delete_invalid_commands=bool(r["delete_invalid_commands"]),
            delete_failed_commands=bool(r["delete_failed_commands"]),
            delete_after_seconds=int(r["delete_after_seconds"]))
        label, is_stale = _target_label(names, int(guild_id), scope_type,
                                        scope_id)
        # A guild row keyed by anything other than guild_id (the legacy
        # scope_id=0 bug) is never read by the resolver — flag it so an
        # operator can re-apply or clean it up (oracle comment verbatim).
        is_ineffective = scope_type == "guild" and scope_id != int(guild_id)
        row = CleanupScopeRow(
            scope_type=scope_type, scope_id=scope_id, level_name=level_name,
            delete_invalid_commands=bool(r["delete_invalid_commands"]),
            delete_failed_commands=bool(r["delete_failed_commands"]),
            delete_after_seconds=int(r["delete_after_seconds"]),
            target_label=label, is_stale=is_stale,
            is_ineffective=is_ineffective)
        rows.append(row)
        key = row.display_level
        level_counts[key] = level_counts.get(key, 0) + 1

    # Stable order: guild first, then category, then channel; by id within.
    order = {"guild": 0, "category": 1, "channel": 2}
    rows.sort(key=lambda r: (order.get(r.scope_type, 9), r.scope_id))
    return CleanupDiagnostics(guild_id=int(guild_id), rows=tuple(rows),
                              level_counts=level_counts)


# ---------------------------------------------------------------------------
# Dry-run preview
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CleanupPolicyPreview:
    """Side-effect-free preview of setting ``scope`` to ``level``
    (the oracle dataclass; ``current`` is the resolver's CleanupPolicy)."""

    scope_type: str
    scope_id: int
    target_label: str
    level: str  # preset name, or "Custom" for an operator-tuned policy
    new_delete_message: bool  # == delete_invalid_commands (drives resolution)
    new_delete_failed_commands: bool
    new_delete_after_seconds: int
    current: object  # governance CleanupPolicy
    will_change: bool
    warnings: tuple[str, ...]


def _resolve_ctx_for_scope(guild_id: int, names: _ScopeNames,
                           scope_type: str, scope_id: int):
    """The context the resolver needs to evaluate ``scope`` today (the
    oracle helper; a channel's category rides the roster index)."""
    from sb.domain.governance.models import GovernanceContext

    if scope_type == "guild":
        return GovernanceContext(guild_id=int(guild_id))
    if scope_type == "category":
        return GovernanceContext(guild_id=int(guild_id),
                                 category_id=int(scope_id))
    category_id = names.channel_category.get(int(scope_id))
    return GovernanceContext(guild_id=int(guild_id),
                             channel_id=int(scope_id),
                             category_id=category_id)


async def preview_cleanup_columns(guild_id: int, scope_type: str,
                                  scope_id: int, *,
                                  delete_invalid_commands: bool,
                                  delete_failed_commands: bool,
                                  delete_after_seconds: int,
                                  level_label: str | None = None,
                                  ) -> CleanupPolicyPreview:
    """Dry-run preview for setting ``scope`` to explicit column values —
    the oracle flow verbatim: validate → resolve CURRENT via the real
    resolver → will_change = effect differs OR pins an explicit source →
    stale + same-effect warnings. Writes nothing, emits nothing."""
    from sb.domain.governance.cleanup import resolve_cleanup_policy
    from sb.domain.governance.models import PolicySource

    _validate_scope(scope_type)
    _validate_columns(delete_after_seconds)
    new_delete = bool(delete_invalid_commands)
    new_failed = bool(delete_failed_commands)
    new_after = int(delete_after_seconds)

    label_name = level_label or (
        level_for_columns(
            delete_invalid_commands=new_delete,
            delete_failed_commands=new_failed,
            delete_after_seconds=new_after)
        or CUSTOM_LEVEL_LABEL)

    names = await scope_labels(int(guild_id))
    current = await resolve_cleanup_policy(
        _resolve_ctx_for_scope(int(guild_id), names, scope_type,
                               int(scope_id)))

    source_for_scope = {
        "guild": PolicySource.GUILD_OVERRIDE,
        "category": PolicySource.CATEGORY_OVERRIDE,
        "channel": PolicySource.CHANNEL_OVERRIDE,
    }
    this_source = source_for_scope[scope_type]
    effect_differs = (current.delete_message != new_delete
                      or current.delete_after_seconds != new_after)
    pins_source = current.resolved_from is not this_source
    will_change = effect_differs or pins_source

    label, is_stale = _target_label(names, int(guild_id), scope_type,
                                    int(scope_id))
    warnings: list[str] = []
    if is_stale:
        warnings.append(
            f"This {scope_type} no longer exists in the server — the policy "
            "will be stored but never matched until it is recreated.")
    if not effect_differs and pins_source:
        warnings.append(
            "Same effect as today, but this pins an explicit override on the "
            f"{scope_type} (currently inherited from "
            f"{current.resolved_from.value}).")

    return CleanupPolicyPreview(
        scope_type=scope_type, scope_id=int(scope_id), target_label=label,
        level=label_name, new_delete_message=new_delete,
        new_delete_failed_commands=new_failed,
        new_delete_after_seconds=new_after, current=current,
        will_change=will_change, warnings=tuple(warnings))


async def preview_cleanup_change(guild_id: int, scope_type: str,
                                 scope_id: int,
                                 level: str) -> CleanupPolicyPreview:
    """The dry-run preview for a preset ``level`` (oracle wrapper)."""
    _validate(scope_type, level)
    cols = LEVELS[level]
    return await preview_cleanup_columns(
        int(guild_id), scope_type, int(scope_id),
        delete_invalid_commands=bool(cols["delete_invalid_commands"]),
        delete_failed_commands=bool(cols["delete_failed_commands"]),
        delete_after_seconds=int(cols["delete_after_seconds"]),
        level_label=level)


# ---------------------------------------------------------------------------
# Audited apply / remove
# ---------------------------------------------------------------------------


async def apply_cleanup_columns(req, scope_type: str, scope_id: int | None,
                                *, delete_invalid_commands: bool,
                                delete_failed_commands: bool,
                                delete_after_seconds: int) -> object:
    """Persist explicit column values for ``scope`` (audited) — the ONE
    apply seam for presets AND custom-tuned policies. Guild scope keys
    at ``guild_id`` (``cleanup_scope_id``, the silent-no-op-bug helper
    verbatim); the K7 op writes row + governance audit in one txn and
    the service wrapper invalidates the cache post-commit."""
    from sb.domain.governance import service as gov_service
    from sb.kernel.interaction.handler_kit import ctx_from_request

    _validate_scope(scope_type)
    _validate_columns(delete_after_seconds)
    effective_id = cleanup_scope_id(scope_type, int(req.guild_id or 0),
                                    scope_id)
    return await gov_service.set_cleanup_policy_for_scope(
        ctx_from_request(req, {}),
        scope_type=scope_type, scope_id=int(effective_id),
        delete_invalid_commands=bool(delete_invalid_commands),
        delete_failed_commands=bool(delete_failed_commands),
        delete_after_seconds=int(delete_after_seconds))


async def remove_cleanup_change(req, scope_type: str,
                                scope_id: int) -> object:
    """Delete one stored cleanup override (audited). Keyed by the
    LITERAL ``scope_id`` so a stale or legacy-keyed row (e.g. a guild
    row written at ``scope_id=0`` the resolver never reads) can be
    cleared from the panel — unlike apply, this does NOT remap guild
    scope to ``guild_id`` (the oracle contract verbatim)."""
    from sb.domain.governance import service as gov_service
    from sb.kernel.interaction.handler_kit import ctx_from_request

    _validate_scope(scope_type)
    return await gov_service.remove_cleanup_policy_for_scope(
        ctx_from_request(req, {}),
        scope_type=scope_type, scope_id=int(scope_id))


def _validate_scope(scope_type: str) -> None:
    if scope_type not in CLEANUP_SCOPE_TYPES:
        raise ValueError(
            f"cleanup scope_type {scope_type!r} is not one of "
            f"{sorted(CLEANUP_SCOPE_TYPES)} (threads inherit; RC-5)")


def _validate_columns(delete_after_seconds: int) -> None:
    if not 0 <= int(delete_after_seconds) <= MAX_DELETE_AFTER_SECONDS:
        raise ValueError(
            f"delete_after_seconds must be between 0 and "
            f"{MAX_DELETE_AFTER_SECONDS} (got {delete_after_seconds!r})")


def _validate(scope_type: str, level: str) -> None:
    _validate_scope(scope_type)
    if level not in known_level_names():
        raise ValueError(
            f"cleanup level {level!r} is not one of "
            f"{sorted(known_level_names())}")
