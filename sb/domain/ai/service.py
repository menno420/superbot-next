"""AI-surface handlers (band 7) — the shipped !ai + !aireview groups as
typed routes/views over K10 diagnostics, the decision audit, the review
log, and the preset lanes."""

from __future__ import annotations


from sb.spec.outcomes import SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _ok(text: str) -> Reply:
    return Reply(SUCCESS, text)


def _argv(req) -> list[str]:
    return [str(a) for a in tuple(req.args.get("argv", ()) or ())]


# --- !ai group -------------------------------------------------------------------


async def ai_usage_view(req) -> Reply:
    return _ok(
        "**!ai** — AI platform operator views.\n"
        "`status` · `readiness` · `settings` · `policy` · `diagnostics` · "
        "`providers` · `routing` · `why-no-response` · `forget` · "
        "`support-report`")


async def status_view(req) -> Reply:
    from sb.kernel.ai import flags
    from sb.kernel.ai.diagnostics import get_default_collector

    snap = get_default_collector().snapshot()
    lines = ["**AI gateway status**"]
    try:
        lines.append(f"Enabled: {'yes' if flags.ai_enabled() else 'no'}")
        lines.append(f"Default provider: {flags.default_provider()}")
    except Exception:  # noqa: BLE001 — config not installed yet
        lines.append("Enabled: no (AI config not installed)")
    for key in ("provider_active", "requests_observed", "failures_observed"):
        if key in snap:
            lines.append(f"{key}: {snap[key]}")
    return _ok("\n".join(lines))


async def readiness_view(req) -> Reply:
    from sb.kernel.ai import flags, tasks
    from sb.kernel.ai.grounding import verify

    lines = ["**AI readiness**"]
    try:
        enabled = flags.ai_enabled()
    except Exception:  # noqa: BLE001
        enabled = False
    state = ("ENABLED" if enabled
             else "disabled (AI_ENABLED off or config uninstalled)")
    lines.append(f"- platform: {state}")
    lines.append(f"- registered tasks: {len(tasks.registered_task_ids())}"
                 f"/{len(tasks.LEGACY_TASK_IDS)} legacy ids claimed")
    lines.append(f"- grounding verifiers: "
                 f"{', '.join(verify.registered_verifier_tasks()) or 'none'}")
    from sb.kernel.ai import evals

    suites = [s.suite_id for s in evals.registered_suites()]
    lines.append(f"- eval suites: {', '.join(suites) or 'none'}")
    return _ok("\n".join(lines))


async def settings_view(req) -> Reply:
    return _ok(
        "AI settings ride the declared `ai.*` settings (band-1 rails): "
        "`!settings` → AI group — enabled, natural_language_enabled, "
        "default_provider/model, minimum_level_default, cooldown_seconds, "
        "fresh_user_mention_allowance, guild_instruction_profile, "
        "memory_window_minutes, memory_channel_scan_enabled, "
        "review_channel. One write path — no separate AI mutator.")


async def policy_view(req) -> Reply:
    from sb.kernel.ai import policy as kpolicy

    try:
        bundle = await kpolicy._load_bundle(int(req.guild_id or 0))  # noqa: SLF001
    except Exception:  # noqa: BLE001 — no reader armed → fail-closed copy
        bundle = None
    if bundle is None:
        return _ok(
            "No AI policy resolves for this server yet (reader not armed "
            "or ai.* settings undeclared) — the NL path fails CLOSED.")
    return _ok(f"**Resolved NL policy:** {bundle}")


async def why_view(req) -> Reply:
    from sb.kernel.ai import decision_audit

    try:
        rows = await decision_audit.query(int(req.guild_id or 0), limit=5)
    except Exception:  # noqa: BLE001
        rows = []
    if not rows:
        return _ok("No NL decisions on record for this server yet.")
    lines = ["Recent NL decisions (newest first):"]
    for row in rows:
        r = dict(row) if not isinstance(row, dict) else row
        lines.append(f"- {r.get('task', '?')}: {r.get('decision', '?')} "
                     f"({r.get('reason_code', '?')})")
    return _ok("\n".join(lines))


async def diagnostics_view(req) -> Reply:
    from sb.kernel.ai.diagnostics import get_default_collector

    snap = get_default_collector().snapshot()
    if not snap:
        return _ok("No AI diagnostics recorded yet this process.")
    return _ok("\n".join(f"- {k}: {v}" for k, v in sorted(snap.items())))


async def providers_view(req) -> Reply:
    from sb.kernel.ai import flags

    try:
        default = flags.default_provider()
    except Exception:  # noqa: BLE001
        default = "(config uninstalled)"
    return _ok(
        f"Providers: anthropic · openai · deterministic (CI/eval). "
        f"Default: {default}. Keys arm via ANTHROPIC_API_KEY / "
        "OPENAI_API_KEY (flag 29); per-guild overlay via "
        "ai.default_provider/ai.default_model settings.")


async def routing_view(req) -> Reply:
    from sb.kernel.ai import routing, tasks

    lines = ["**Task routing (anthropic defaults; K10(b) ruling):**"]
    for task_id in tasks.registered_task_ids():
        lines.append(
            f"- {task_id} → {routing.default_model_for('anthropic', task_id)}")
    return _ok("\n".join(lines))


async def forget_view(req) -> Reply:
    from sb.kernel.ai import conversation, policy

    gid = int(req.guild_id or 0)
    try:
        conversation.reset_conversation_for_tests()
        policy.forget_guild_throttles(gid)
    except Exception:  # noqa: BLE001
        pass
    return _ok(
        "🧹 In-process conversation memory + cooldown bookkeeping cleared "
        "for this process. (Durable rows — decision audit / review log — "
        "are erasure-workflow territory, not `forget`.)")


async def support_report_view(req) -> Reply:
    from sb.domain.ai import store as ai_store
    from sb.kernel.ai import tasks

    gid = int(req.guild_id or 0)
    try:
        unreviewed = await ai_store.count_unreviewed(gid)
    except Exception:  # noqa: BLE001
        unreviewed = 0
    return _ok(
        "**AI support report**\n"
        f"- registered tasks: {len(tasks.registered_task_ids())}\n"
        f"- unreviewed review-log entries here: {unreviewed}\n"
        "- export the backlog with `!aireview export`.")


# --- !aireview group ---------------------------------------------------------------


async def aireview_usage_view(req) -> Reply:
    return _ok(
        "**!aireview** — the AI answer review loop.\n"
        "`list [unknown|correction]` · `resolve <id>` · `export` · "
        "`channel <#channel>` · `off` · `preset add <q> | <a>` · "
        "`preset from <entry_id> <answer…>` · `preset list` · "
        "`preset remove <q>`")


def _fmt_entry(row: dict) -> str:
    flag = "✅" if row.get("reviewed") else "🔸"
    return (f"{flag} **#{row['id']}** [{row.get('kind')}] "
            f"{row.get('task') or '—'} ({row.get('reason_code') or '—'}): "
            f"{(row.get('question') or '')[:80]}")


async def review_list_view(req) -> Reply:
    from sb.domain.ai import store as ai_store

    kind = next((a for a in _argv(req)
                 if a in ("unknown", "correction")), None)
    rows = await ai_store.query_entries(
        int(req.guild_id or 0), kind=kind, limit=10)
    if not rows:
        return _ok("Review log is empty for this server — nothing flagged.")
    return _ok("\n".join(_fmt_entry(r) for r in rows))


async def review_export_view(req) -> Reply:
    from sb.domain.ai import store as ai_store

    rows = await ai_store.query_entries(
        int(req.guild_id or 0), unreviewed_only=True, limit=25)
    if not rows:
        return _ok("Nothing unreviewed to export.")
    lines = ["**Unreviewed backlog export:**"]
    for r in rows:
        lines.append(
            f"#{r['id']}|{r.get('kind')}|{r.get('task') or ''}|"
            f"{(r.get('question') or '')[:60]}|"
            f"{(r.get('correction') or r.get('answer') or '')[:60]}")
    return _ok("\n".join(lines))


async def review_channel_view(req) -> Reply:
    return _ok(
        "The review feed channel is the declared `ai.review_channel` "
        "setting — set it through `!settings` (band-1 write path); the "
        "live feed posts when the message shell arms at the composition "
        "root.")


async def preset_list_view(req) -> Reply:
    from sb.domain.ai import store as ai_store

    rows = await ai_store.list_presets(int(req.guild_id or 0))
    if not rows:
        return _ok("No vetted answer presets stored here yet.")
    lines = ["**Vetted answer presets:**"]
    for r in rows:
        lines.append(f"- #{r['id']} “{r['question'][:60]}” → "
                     f"“{r['answer'][:60]}”")
    return _ok("\n".join(lines))


def _run_op(ref: str, params_fn):
    async def route(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(
            WorkflowRef(ref), _ctx_from_req(req, params_fn(req)))
        message = (result.after or {}).get("message") if result.ok else None
        return Reply(SUCCESS if result.ok else result.outcome,
                     message or result.user_message or "Done.")
    return route


def _resolve_params(req) -> dict:
    argv = [a for a in _argv(req) if a.isdigit()]
    return {"entry_id": int(argv[0]) if argv else 0}


def _preset_add_params(req) -> dict:
    text = " ".join(_argv(req)).strip()
    if not text:
        text = f"{req.args.get('question') or ''} | {req.args.get('answer') or ''}"
    question, _, answer = text.partition("|")
    return {"question": question.strip(), "answer": answer.strip(),
            "source": "operator"}


async def preset_from_route(req) -> Reply:
    """``preset from <entry_id> <answer…>`` — vets a review-log entry's
    question with the operator-authored answer."""
    from sb.domain.ai import store as ai_store
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    argv = _argv(req)
    entry_id = int(argv[0]) if argv and argv[0].isdigit() else 0
    answer = " ".join(argv[1:]).strip()
    entry = await ai_store.get_entry(int(req.guild_id or 0), entry_id)
    if not entry or not entry.get("question"):
        return _ok(f"❌ No review entry #{entry_id} with a stored question.")
    result = await engine.run(
        WorkflowRef("ai.set_preset"),
        _ctx_from_req(req, {"question": entry["question"], "answer": answer,
                            "task": entry.get("task"),
                            "source": f"review:{entry_id}"}))
    message = (result.after or {}).get("message") if result.ok else None
    return Reply(SUCCESS if result.ok else result.outcome,
                 message or result.user_message or "Done.")


def _preset_remove_params(req) -> dict:
    return {"question": " ".join(_argv(req)).strip()
            or str(req.args.get("question") or "")}


resolve_route = _run_op("ai.resolve_review_entry", _resolve_params)
preset_add_route = _run_op("ai.set_preset", _preset_add_params)
preset_remove_route = _run_op("ai.remove_preset", _preset_remove_params)


_HANDLERS = (
    ("ai.usage_view", ai_usage_view),
    ("ai.status_view", status_view),
    ("ai.readiness_view", readiness_view),
    ("ai.settings_view", settings_view),
    ("ai.policy_view", policy_view),
    ("ai.why_view", why_view),
    ("ai.diagnostics_view", diagnostics_view),
    ("ai.providers_view", providers_view),
    ("ai.routing_view", routing_view),
    ("ai.forget_view", forget_view),
    ("ai.support_report_view", support_report_view),
    ("ai.review_usage_view", aireview_usage_view),
    ("ai.review_list_view", review_list_view),
    ("ai.review_export_view", review_export_view),
    ("ai.review_channel_view", review_channel_view),
    ("ai.review_resolve_route", resolve_route),
    ("ai.preset_add_route", preset_add_route),
    ("ai.preset_from_route", preset_from_route),
    ("ai.preset_list_view", preset_list_view),
    ("ai.preset_remove_route", preset_remove_route),
)


def ensure_handler_refs() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
