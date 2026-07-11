"""AI operator-surface cards (band 7) — every shipped ``!ai``/``!aimenu``
reply embed as a pure builder over the K10 kernel seams, byte-for-byte as
goldens/ai pin them (the projmoon ``oracle_cards`` pattern).

Shipped sources @7f7628e1:

* ``cogs/ai_cog.py`` — build_status_embed / build_diagnostics_embed /
  build_providers_embed / build_routing_embed / build_readiness_embed /
  the why-no-response audit lines;
* ``views/ai/panel.py`` — build_ai_panel_embed (the 💤/⚠️/✅ status emoji);
* ``views/ai/support_report.py`` — the copy-paste draft;
* ``views/ai/policy/preview_view.py`` — build_effective_policy_embed
  (the dual dry-run resolver trace);
* ``services/ai_diagnostics_service.py`` — snapshot_for_cog /
  list_task_routing;
* ``services/ai_readiness_service.py`` — the 7-finding chain scan.

Environment-shaped reads ride installable ports (the parity harness
installs the capture-world twins; the live root installs the real ones):

* :func:`install_runtime_identity` — the support report's
  ``# python: X on Y`` + ``# bot_user_id`` lines (``sys.version`` /
  ``platform.system()`` / the gateway bot id at capture time);
* :func:`install_channel_permission_probe` — the readiness scan's
  ``bot_permissions`` link (a live ``channel.permissions_for(me)`` read;
  uninstalled → the shipped ``skipped`` finding).

Deliberate under-ports (ledgered):

* ``setup_advisor_provider`` — the shipped legacy ``SETUP_ADVISOR_PROVIDER``
  env override is not yet an RC-10 Config field; the port serves the
  shipped FALLBACK (``ai_default_provider``), which is byte-identical in
  every deployment that never set the legacy var (the goldens' state).
"""

from __future__ import annotations

import logging
import platform
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sb.kernel.panels.render import RenderedEmbed

logger = logging.getLogger("sb.domain.ai.operator_cards")

__all__ = [
    "SHIPPED_TASK_ORDER",
    "build_diagnostics_embed",
    "build_panel_embed",
    "build_policy_embed",
    "build_providers_embed",
    "build_readiness_embed",
    "build_routing_embed",
    "build_status_embed",
    "build_support_report_embed",
    "format_audit_row",
    "install_channel_permission_probe",
    "install_runtime_identity",
    "reset_operator_ports_for_tests",
    "snapshot_for_cog",
]

#: the shipped AITask enum DECLARATION order (core/runtime/ai/contracts.py
#: @7f7628e1) — ``!ai routing`` iterated ``for task in AITask``, so the
#: rendering order is the enum order, never alphabetical
#: (goldens/ai/sweep_ai_routing pins all 17 rows in this order).
SHIPPED_TASK_ORDER: tuple[str, ...] = (
    "setup.suggest",
    "setup.explain",
    "platform.explain_status",
    "platform.explain_consistency",
    "logs.triage",
    "settings.explain",
    "settings.propose",
    "help.answer",
    "code_context.explain",
    "moderation.assist",
    "btd6.answer",
    "general.nl_answer",
    "projmoon.answer",
    "btd6.strategy_review",
    "video.describe",
    "video.compare",
    "video.qa",
)


# --- environment ports ---------------------------------------------------------


@dataclass(frozen=True)
class RuntimeIdentity:
    """The support report's environment lines."""

    python_version: str
    system: str
    bot_user_id: int | None = None


_runtime_identity: RuntimeIdentity | None = None

#: probe(guild_id, channel_id, scan_enabled) -> missing-permission names
#: (empty = all good) or None (probe cannot run). Uninstalled → the shipped
#: ``skipped`` finding.
PermissionProbe = Callable[[int, int, bool], Awaitable[list[str] | None]]
_permission_probe: PermissionProbe | None = None


def install_runtime_identity(identity: RuntimeIdentity) -> None:
    global _runtime_identity
    _runtime_identity = identity


def install_channel_permission_probe(probe: PermissionProbe) -> None:
    global _permission_probe
    _permission_probe = probe


def reset_operator_ports_for_tests() -> None:
    global _runtime_identity, _permission_probe
    _runtime_identity = None
    _permission_probe = None


def _identity() -> RuntimeIdentity:
    if _runtime_identity is not None:
        return _runtime_identity
    return RuntimeIdentity(python_version=sys.version.split()[0],
                           system=platform.system())


# --- the diagnostics snapshot (ai_diagnostics_service.snapshot_for_cog) ---------


def _setup_advisor_provider() -> str:
    """Shipped fallback semantics (module-docstring under-port note)."""
    from sb.kernel.ai import flags

    return flags.default_provider()


def snapshot_for_cog() -> dict[str, object]:
    """The shipped cog-shaped snapshot dict — INSERTION ORDER IS THE WIRE
    ORDER of ``!ai diagnostics`` (the embed iterates ``snap.items()``)."""
    from sb.kernel.ai import flags
    from sb.kernel.ai.diagnostics import get_default_collector

    snap = get_default_collector().snapshot()
    return {
        "enabled": snap.enabled,
        "default_provider": flags.default_provider(),
        "setup_advisor_provider": _setup_advisor_provider(),
        "provider_active": snap.provider_active,
        "degraded": snap.degraded,
        "last_error_type": snap.last_error_type,
        "last_fallback_reason": snap.last_fallback_reason,
        "requests_observed": snap.requests_observed,
        "failures_observed": snap.failures_observed,
        "redaction_enabled": snap.redaction_enabled,
    }


def list_task_routing() -> list[dict[str, object]]:
    """ai_diagnostics_service.list_task_routing over the kernel registry,
    in the SHIPPED enum order."""
    from sb.kernel.ai import flags, routing

    rows: list[dict[str, object]] = []
    for task_id in SHIPPED_TASK_ORDER:
        target = routing.resolve(task_id)
        rows.append({
            "task": task_id,
            "provider": target.provider,
            "model": target.model,
            "timeout_seconds": target.timeout_seconds,
            # shipped: task_enabled(task) and ai_enabled() — the kernel
            # port already layers the global gate inside task_enabled.
            "enabled": flags.task_enabled(task_id),
        })
    return rows


# --- panel + status/diagnostics/providers/routing embeds ------------------------


def build_panel_embed() -> RenderedEmbed:
    """views/ai/panel.py build_ai_panel_embed, verbatim."""
    snap = snapshot_for_cog()
    enabled = bool(snap["enabled"])
    degraded = bool(snap["degraded"])
    status_emoji = "✅" if enabled and not degraded else ("⚠️" if degraded else "💤")
    fields: list[tuple[str, str, bool]] = [
        ("Enabled", "yes" if enabled else "no", True),
        ("Default provider", str(snap["default_provider"]), True),
        ("Setup advisor provider", str(snap["setup_advisor_provider"]), True),
        ("Active provider (last call)", str(snap["provider_active"]), True),
        ("Requests / failures",
         f"{snap['requests_observed']} / {snap['failures_observed']}", True),
        ("Redaction", "on" if snap["redaction_enabled"] else "off", True),
    ]
    if degraded:
        fields.append(("Last fallback reason",
                       str(snap["last_fallback_reason"] or "—"), False))
    return RenderedEmbed(
        title=f"{status_emoji} AI Platform",
        description=(
            "Read-only diagnostics for the AI gateway. The buttons below "
            "open the matching subcommands without making a provider call."),
        fields=tuple(fields),
        footer="!ai status / !ai diagnostics / !ai providers / !ai routing",
        style_token="blurple")


async def build_status_embed(guild_id: int, channel_id: int | None) -> RenderedEmbed:
    """cogs/ai_cog.py build_status_embed + _attach_readiness_summary."""
    snap = snapshot_for_cog()
    fields: list[tuple[str, str, bool]] = [
        ("Enabled", "yes" if snap["enabled"] else "no", True),
        ("Default provider", str(snap["default_provider"]), True),
        ("Setup advisor provider", str(snap["setup_advisor_provider"]), True),
        ("Active provider", str(snap["provider_active"]), True),
        ("Requests", str(snap["requests_observed"]), True),
        ("Failures", str(snap["failures_observed"]), True),
    ]
    # best-effort readiness one-liner (shipped: silent on failure — the
    # readiness chain is the diagnostic surface for failures).
    try:
        report = await scan_readiness(guild_id, channel_id=channel_id)
        fields.append(("Readiness", report.summary, False))
    except Exception:  # noqa: BLE001 — shipped silence
        logger.debug("ai status: readiness summary fetch failed", exc_info=True)
    return RenderedEmbed(title="AI Gateway — Status", description="",
                         fields=tuple(fields), style_token="blurple")


def build_diagnostics_embed() -> RenderedEmbed:
    snap = snapshot_for_cog()
    fields = tuple((key.replace("_", " "), str(value), True)
                   for key, value in snap.items())
    return RenderedEmbed(title="AI Gateway — Diagnostics", description="",
                         fields=fields, style_token="blurple")


def build_providers_embed() -> RenderedEmbed:
    snap = snapshot_for_cog()
    return RenderedEmbed(
        title="AI Gateway — Providers",
        description=(
            "Configured providers. The active provider is the one the "
            "gateway selected for the most recent request; the default "
            "provider is the env-driven choice for new requests."),
        fields=(
            ("Default", str(snap["default_provider"]), True),
            ("Active (last call)", str(snap["provider_active"]), True),
            ("Setup advisor", str(snap["setup_advisor_provider"]), True),
        ),
        style_token="blurple")


def build_routing_embed(task_name: str | None = None) -> RenderedEmbed:
    rows = list_task_routing()
    if task_name:
        rows = [r for r in rows if r["task"] == task_name]
    if not rows:
        fields: tuple = (("No matching task",
                          f"Known tasks: {', '.join(SHIPPED_TASK_ORDER)}",
                          False),)
        footer = ""
    else:
        fields = tuple(
            (str(r["task"]),
             f"provider: `{r['provider']}`\n"
             f"model: `{r['model']}`\n"
             f"timeout: `{r['timeout_seconds']}s`\n"
             f"enabled: `{r['enabled']}`", True)
            for r in rows)
        footer = ("Per-guild overrides from ai_guild_policy.default_provider "
                  "/ default_model take precedence at gateway time when set. "
                  "Run !ai policy in a guild to see its typed overrides.")
    return RenderedEmbed(
        title="AI Gateway — Routing",
        description=("Resolved provider/model/timeout for each AI task. "
                     "This view does not invoke any provider."),
        fields=fields, footer=footer, style_token="blurple")


# --- the readiness chain scan (ai_readiness_service, over kernel seams) ---------


@dataclass(frozen=True)
class ReadinessFinding:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    guild_id: int
    channel_id: int | None
    findings: tuple[ReadinessFinding, ...]
    summary: str


_READINESS_STATUS_EMOJI = {
    "ok": "✅", "info": "ℹ️", "warn": "⚠️", "error": "❌", "skipped": "⏭️",
}


async def scan_readiness(guild_id: int,
                         *, channel_id: int | None) -> ReadinessReport:
    """The 7-link chain in the shipped fixed order: provider → ai_enabled →
    nl_or_scoped → resolver → permissions → memory → recent_denials."""
    from sb.kernel.ai import conversation, decision_audit, memory, policy

    snap = snapshot_for_cog()
    bundle = await policy._load_bundle(guild_id)  # noqa: SLF001 — the dry-run read
    row = dict(bundle.policy) if bundle.policy else None
    findings: list[ReadinessFinding] = []

    # 1 — provider_configured
    if not snap["default_provider"]:
        findings.append(ReadinessFinding(
            "provider_configured", "error",
            "No default provider configured for the AI gateway."))
    elif snap["degraded"]:
        findings.append(ReadinessFinding(
            "provider_configured", "warn",
            f"Gateway is degraded "
            f"(last error: {snap['last_error_type'] or 'unknown'}); "
            f"replies will fall back to the deterministic provider."))
    else:
        findings.append(ReadinessFinding(
            "provider_configured", "ok",
            f"Default provider: {snap['default_provider']}."))

    # 2 — ai_enabled (the typed-policy-row hard gate)
    if row is None:
        findings.append(ReadinessFinding(
            "ai_enabled", "error",
            "No typed AI policy row exists for this guild. "
            "Set `ai.enabled` via `!settings` to create one."))
    elif not row.get("enabled"):
        findings.append(ReadinessFinding(
            "ai_enabled", "error",
            "AI master switch is OFF (`ai_guild_policy.enabled=false`)."))
    else:
        findings.append(ReadinessFinding(
            "ai_enabled", "ok", "AI master switch is ON."))

    # 3 — nl_enabled_or_scoped
    nl = bool(row.get("natural_language_enabled")) if row else False
    scoped = len(bundle.channel) + len(bundle.category) + len(bundle.role)
    if nl and scoped == 0:
        findings.append(ReadinessFinding(
            "nl_enabled_or_scoped", "ok",
            "Natural-language baseline is enabled (replies everywhere by "
            "default)."))
    elif nl:
        findings.append(ReadinessFinding(
            "nl_enabled_or_scoped", "ok",
            f"Natural-language baseline ON; {scoped} scoped override(s) "
            f"refine per-channel/category/role."))
    elif scoped > 0:
        findings.append(ReadinessFinding(
            "nl_enabled_or_scoped", "ok",
            f"Natural-language baseline OFF; {scoped} scoped override(s) "
            f"enable AI in specific scopes."))
    else:
        findings.append(ReadinessFinding(
            "nl_enabled_or_scoped", "warn",
            "Natural-language baseline is OFF and no scoped overrides "
            "exist. AI will not reply to messages unless mentioned in a "
            "scope that explicitly allows it."))

    # 4 — resolver_decision (dry-run; the bot stands in for the user)
    if channel_id is None:
        findings.append(ReadinessFinding(
            "resolver_decision", "skipped",
            "No channel reference — pass one to dry-run the resolver."))
    else:
        identity = _identity()
        ctx = policy.MessageContext(
            guild_id=guild_id, channel_id=int(channel_id), category_id=None,
            user_id=int(identity.bot_user_id or 0), user_level=100,
            user_role_ids=(), is_mention=False, is_fresh_user=False)
        try:
            decision = await policy.resolve_policy(ctx, dry_run=True)
        except Exception as exc:  # noqa: BLE001 — shipped warn shape
            findings.append(ReadinessFinding(
                "resolver_decision", "warn",
                f"Resolver dry-run failed: {type(exc).__name__}."))
        else:
            if decision.allowed:
                findings.append(ReadinessFinding(
                    "resolver_decision", "ok",
                    f"Channel resolves to "
                    f"{decision.effective_mode or 'allow'} "
                    f"(source: {decision.effective_source or 'guild'})."))
            else:
                reason = getattr(decision.reason_code, "name",
                                 str(decision.reason_code))
                findings.append(ReadinessFinding(
                    "resolver_decision", "warn",
                    f"Channel would deny with reason {reason} "
                    f"(source: {decision.effective_source or 'guild'})."))

    # 5 — bot_permissions (the installable live probe)
    window, scan_enabled = 0, False
    try:
        window, scan_enabled = await memory.read_memory_settings(guild_id)
    except Exception:  # noqa: BLE001 — reader not armed → floor-only
        pass
    if channel_id is None:
        findings.append(ReadinessFinding(
            "bot_permissions", "skipped",
            "No channel reference — pass one to probe send permissions."))
    elif _permission_probe is None:
        findings.append(ReadinessFinding(
            "bot_permissions", "skipped",
            "Bot member is not in the guild cache; cannot probe "
            "permissions."))
    else:
        missing = await _permission_probe(guild_id, int(channel_id),
                                          scan_enabled)
        if missing is None:
            findings.append(ReadinessFinding(
                "bot_permissions", "skipped",
                "Bot member is not in the guild cache; cannot probe "
                "permissions."))
        elif missing:
            findings.append(ReadinessFinding(
                "bot_permissions", "error",
                f"Bot lacks permissions in this channel: "
                f"{', '.join(missing)}."))
        else:
            findings.append(ReadinessFinding(
                "bot_permissions", "ok",
                "Bot can view, send, and (if scan enabled) read history."))

    # 6 — memory_status
    if window <= 0:
        mode = f"Minimal — {conversation.MIN_FLOOR_TURNS} turn floor"
    else:
        mode = f"{window} min window"
    stats = conversation.stats()
    findings.append(ReadinessFinding(
        "memory_status", "info",
        f"Memory: {mode}, {'scan on' if scan_enabled else 'scan off'}. "
        f"Cache: {stats.channel_count} channel(s), "
        f"{stats.total_turns} turn(s)."))

    # 7 — recent_denials
    try:
        rows = await decision_audit.query(guild_id, limit=50)
    except Exception:  # noqa: BLE001 — audit store unreachable → empty
        rows = []
    if not rows:
        findings.append(ReadinessFinding(
            "recent_denials", "info",
            "No decisions audited yet for this guild."))
    else:
        bad = sum(1 for r in rows
                  if str(r.get("decision")) in ("denied", "degraded",
                                                "errored"))
        if bad == 0:
            findings.append(ReadinessFinding(
                "recent_denials", "ok",
                f"No denials/errors in the last {len(rows)} decisions."))
        else:
            findings.append(ReadinessFinding(
                "recent_denials", "warn",
                f"{bad} of last {len(rows)} decisions "
                "denied/degraded/errored. Run `!ai why-no-response` for "
                "details."))

    return ReadinessReport(guild_id=guild_id, channel_id=channel_id,
                           findings=tuple(findings),
                           summary=_summarise(findings))


def _summarise(findings: list[ReadinessFinding]) -> str:
    if any(f.status == "error" for f in findings):
        first = next(f for f in findings if f.status == "error")
        return f"Not ready: {first.detail}"
    warns = [f for f in findings if f.status == "warn"]
    if warns:
        if len(warns) == 1:
            return f"Ready with caveat: {warns[0].detail}"
        return f"Ready with {len(warns)} caveats; first: {warns[0].detail}"
    return "Ready"


def build_readiness_embed(report: ReadinessReport) -> RenderedEmbed:
    """cogs/ai_cog.py build_readiness_embed: green when all ok/info, orange
    on warns, red on any error; one inline=False field per finding."""
    statuses = [f.status for f in report.findings]
    token = "green" if all(s in ("ok", "info") for s in statuses) else "orange"
    if "error" in statuses:
        token = "red"
    title = "AI Readiness"
    if report.channel_id is not None:
        title += f" — <#{report.channel_id}>"
    fields = tuple(
        (f"{_READINESS_STATUS_EMOJI.get(f.status, '•')} {f.name}",
         f.detail or "—", False)
        for f in report.findings)
    return RenderedEmbed(title=title, description=report.summary,
                         fields=fields, style_token=token)


# --- why-no-response + support report --------------------------------------------


def format_audit_row(row: dict) -> str:
    """cogs/ai_cog.py _format_audit_row, verbatim (relative time + the
    columns; no message content exists to render)."""
    from datetime import datetime, timezone

    created_at = row.get("created_at")
    when = "—"
    if isinstance(created_at, datetime):
        ts = created_at if created_at.tzinfo else created_at.replace(
            tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - ts).total_seconds()
        if delta < 0:
            when = "in the future"
        elif delta < 60:
            when = f"{int(delta)}s ago"
        elif delta < 3600:
            when = f"{int(delta // 60)}m ago"
        elif delta < 86400:
            when = f"{int(delta // 3600)}h ago"
        else:
            when = f"{int(delta // 86400)}d ago"
    return (
        f"`{when:<8}` · `{str(row.get('decision', '')):<8}` · "
        f"`{row.get('reason_code')}` · "
        f"task={row.get('task') or '—'} · route={row.get('route') or '—'} · "
        f"<#{row.get('channel_id')}> · <@{row.get('user_id')}> · "
        f"provider={row.get('provider') or '—'} model={row.get('model') or '—'}"
    )


async def build_support_report_embed(guild_id: int) -> RenderedEmbed:
    """views/ai/support_report.py, verbatim copy — the python/system/bot-id
    lines read the installed RuntimeIdentity (module docstring)."""
    from sb.kernel.ai import decision_audit

    try:
        rows = await decision_audit.query(guild_id, limit=50)
    except Exception:  # noqa: BLE001 — audit store unreachable → empty draft
        rows = []
    rows = list(rows)[:10]
    identity = _identity()
    lines = ["```",
             "# SuperBot AI support report (draft — copy-paste only)",
             f"# guild_id: {guild_id}"]
    if identity.bot_user_id is not None:
        lines.append(f"# bot_user_id: {identity.bot_user_id}")
    lines.append(f"# python: {identity.python_version} on {identity.system}")
    lines.append("# fields below come ONLY from ai_decision_audit; "
                 "no message text.")
    lines.append("")
    if not rows:
        lines.append("(no recent audit rows for this guild)")
    else:
        for r in rows:
            lines.append(
                f"- decision={r.get('decision')} reason={r.get('reason_code')} "
                f"task={r.get('task') or '—'} route={r.get('route') or '—'} "
                f"provider={r.get('provider') or '—'} "
                f"model={r.get('model') or '—'}")
    lines.append("```")
    draft = "\n".join(lines)
    body = draft if len(draft) <= 1000 else draft[:999] + "…\n```"
    return RenderedEmbed(
        title="📋 AI Support report — draft",
        description=(
            "Copy the code block below into your support channel. **This "
            "bot does NOT send anything outbound** — you must paste it "
            "yourself wherever support requests are handled."),
        fields=(("Draft", body, False),),
        footer=("Privacy: no message text is included — only audit rows. "
                "No network egress on this code path."),
        style_token="blurple")


# --- the effective-policy dual dry-run ---------------------------------------------


def _render_verdict(decision) -> str:
    from sb.kernel.ai.contracts import PolicyDenialReason

    if decision.allowed:
        return "✅ **allowed**"
    reason = decision.reason_code
    if reason in (PolicyDenialReason.AI_GLOBALLY_DISABLED,
                  PolicyDenialReason.GUILD_NOT_CONFIGURED):
        marker, label = "⛔", "hard-disabled"
    elif reason is PolicyDenialReason.AI_NL_DISABLED_FOR_GUILD:
        marker, label = "🟡", "baseline-denied (override-able)"
    else:
        marker, label = "❌", "denied"
    return f"{marker} **{label}** · `{reason.value}`"


def _render_effective_summary(decision) -> str:
    source = decision.effective_source or "—"
    mode = decision.effective_mode or "—"
    return (f"effective: source=`{source}` mode=`{mode}` · "
            f"min_level=`{decision.effective_min_level}` · "
            f"cooldown=`{decision.effective_cooldown}s`")


async def build_policy_embed(*, guild_id: int, channel_id: int,
                             user_id: int,
                             user_role_ids: tuple[int, ...],
                             title: str = "AI Effective Policy",
                             category_id: int | None = None,
                             include_context: bool = True) -> RenderedEmbed:
    """views/ai/policy/preview_view.build_effective_policy_embed with the
    ancillary Context field (the ``!ai policy`` prefix path always built
    the snapshot), title ``AI Effective Policy``. The policy chooser's
    Preview picker passes the shipped chooser-path shape instead: title
    ``AI policy preview``, the picked channel's category_id, and NO
    Context field (the shipped chooser callback never built the
    snapshot)."""
    from sb.kernel.ai import policy

    # member level + freshness — the shipped xp_service.get_user_record
    # read (row absent → level 0, fresh user).
    user_level, is_fresh_user = 0, True
    try:
        from sb.domain.xp import store as xp_store

        record = await xp_store.get_xp(int(user_id), int(guild_id))
        user_level = int(record.get("level", 0) or 0)
        is_fresh_user = int(record.get("messages", 0) or 0) == 0
    except Exception:  # noqa: BLE001 — XP read is best-effort here (shipped)
        logger.debug("policy card: xp lookup failed", exc_info=True)

    role_ids = tuple(int(r) for r in user_role_ids if int(r) != int(guild_id))

    fields: list[tuple[str, str, bool]] = []
    for label, is_mention in (("Without mention", False),
                              ("With @mention", True)):
        ctx = policy.MessageContext(
            guild_id=int(guild_id), channel_id=int(channel_id),
            category_id=category_id, user_id=int(user_id),
            user_level=user_level,
            user_role_ids=role_ids, is_mention=is_mention,
            is_fresh_user=is_fresh_user)
        decision = await policy.resolve_policy(ctx, dry_run=True)
        trace_lines = "\n".join(f"· {step}"
                                for step in decision.precedence_trace)
        body = (f"{_render_verdict(decision)}\n"
                f"{_render_effective_summary(decision)}\n{trace_lines}")
        if len(body) > 1024:
            body = body[:1020] + "\n…"
        fields.append((label, body, False))

    # the ancillary Context field — override counts (the typed-table
    # overlays the policy-mutation slice armed) + provider/model. The
    # chooser Preview path skips it (shipped: snapshot=None).
    if include_context:
        bundle = await policy._load_bundle(int(guild_id))  # noqa: SLF001
        try:
            from sb.domain.ai.readers import _guild_policy_overlay

            overlay = await _guild_policy_overlay(int(guild_id))
        except Exception:  # noqa: BLE001 — overlay reader not armed
            overlay = None
        from sb.kernel.ai import flags

        provider_name = (overlay or {}).get("default_provider") or \
            flags.default_provider() or "—"
        model = (overlay or {}).get("default_model") or "—"
        fields.append((
            "Context",
            f"Overrides: {len(bundle.channel)} channel · "
            f"{len(bundle.category)} category · {len(bundle.role)} role\n"
            f"Provider: `{provider_name}` · model: `{model}`", False))

    return RenderedEmbed(
        title=title,
        description=(
            f"Resolving for <#{channel_id}> as <@{user_id}> "
            f"(level `{user_level}`, {len(role_ids)} role(s)).\n"
            "_Dry-run only — no cooldown is touched, no audit is written._"),
        fields=tuple(fields),
        footer="dry_run=True · administrator-only",
        style_token="blurple")
