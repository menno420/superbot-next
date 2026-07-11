"""AI-surface handlers (band 7) — the shipped ``!ai`` + ``!aireview``
groups: the ``!ai`` operator views render the SHIPPED embeds
(sb/domain/ai/operator_cards.py — goldens/ai pin the bytes) presented
through the generic ``ai.card`` panel (the projmoon.card pattern);
``forget`` / ``why-no-response`` keep their shipped plain-text replies.

Registered at MODULE IMPORT (declaring IS reserving — the BUG A rule,
sb/domain/role/handlers.py pattern): the live root imports and dispatches
without ever running the manifest ENSURE_REFS hooks. This pruned all 20
``handler:ai.*`` rows from the composition-parity burn-down list.

The ``!aireview`` lanes (review log + vetted presets) keep their
band-7 typed-op routes — their goldens live in ``_unmapped`` until that
sweep family re-homes.
"""

from __future__ import annotations

import dataclasses

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


async def _card(req, embed) -> None:
    """Present one operator card as the shipped public embed reply."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("ai.card"),
                     dataclasses.replace(
                         req, args={**dict(req.args), "_card": embed}))


# --- !ai group -------------------------------------------------------------------


async def status_view(req) -> None:
    """``!ai status`` — the compact gateway status embed + the one-line
    readiness summary (goldens/ai/sweep_ai_status)."""
    from sb.domain.ai import operator_cards as cards

    await _card(req, await cards.build_status_embed(
        int(req.guild_id or 0), req.channel_id))
    return None


async def readiness_view(req) -> None:
    """``!ai readiness`` — the 7-link chain scan embed
    (goldens/ai/sweep_ai_readiness)."""
    from sb.domain.ai import operator_cards as cards

    report = await cards.scan_readiness(int(req.guild_id or 0),
                                        channel_id=req.channel_id)
    await _card(req, cards.build_readiness_embed(report))
    return None


async def settings_view(req) -> None:
    """``!ai settings`` — the shipped SubsystemSettingsView page for the
    ai schema (goldens/ai/sweep_ai_settings pins the embed + the two
    selects + the Back-to-Hub/Open-Panel row)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("ai.settings"), req)
    return None


async def policy_view(req) -> None:
    """``!ai policy`` — the dual dry-run effective-policy embed
    (goldens/ai/sweep_ai_policy)."""
    from sb.domain.ai import operator_cards as cards

    await _card(req, await cards.build_policy_embed(
        guild_id=int(req.guild_id or 0),
        channel_id=int(req.channel_id or 0),
        user_id=int(getattr(req.actor, "user_id", 0) or 0),
        user_role_ids=tuple(getattr(req.actor, "role_ids", ()) or ())))
    return None


async def why_view(req) -> Reply | None:
    """``!ai why-no-response`` — recent denials/skips (shipped
    ai_why_no_response: plain reply when empty, the orange audit embed
    otherwise; goldens/ai/sweep_ai_why-no-response pins the empty byte)."""
    from sb.domain.ai import operator_cards as cards
    from sb.kernel.ai import decision_audit
    from sb.kernel.panels.render import RenderedEmbed

    argv = [a for a in _argv(req) if a.isdigit()]
    limit = max(1, min(50, int(argv[0]) if argv else 10))
    try:
        rows = await decision_audit.query(int(req.guild_id or 0), limit=limit)
    except Exception:  # noqa: BLE001 — audit store unreachable → empty
        rows = []
    denials = [r for r in rows
               if str(r.get("decision")) in ("denied", "skipped", "errored",
                                             "degraded")][:25]
    if not denials:
        return _ok("No recent denials or skips for this guild.")
    lines = [cards.format_audit_row(dict(r)) for r in denials]
    oldest = dict(denials[-1]).get("created_at")
    footer = (f"Showing {len(denials)} most recent · "
              f"oldest: {oldest.isoformat()}"
              if hasattr(oldest, "isoformat")
              else f"Showing {len(denials)} most recent")
    await _card(req, RenderedEmbed(
        title="AI — why no response", description="\n".join(lines),
        footer=footer, style_token="orange"))
    return None


async def diagnostics_view(req) -> None:
    from sb.domain.ai import operator_cards as cards

    await _card(req, cards.build_diagnostics_embed())
    return None


async def providers_view(req) -> None:
    from sb.domain.ai import operator_cards as cards

    await _card(req, cards.build_providers_embed())
    return None


async def routing_view(req) -> None:
    from sb.domain.ai import operator_cards as cards

    argv = _argv(req)
    await _card(req, cards.build_routing_embed(argv[0] if argv else None))
    return None


async def forget_view(req) -> Reply:
    """``!ai forget`` — flush the chat-memory cache for THIS channel
    (shipped ai_forget; goldens/ai/sweep_ai_forget pins the ✅ byte)."""
    from sb.kernel.ai import conversation

    gid = int(req.guild_id or 0)
    channel_id = int(req.channel_id or 0)
    dropped = conversation.forget_channel(gid, channel_id)
    if dropped:
        return _ok(f"✅ Cleared chat memory for <#{channel_id}>.")
    return _ok(f"No chat memory cached for <#{channel_id}>.")


async def support_report_view(req) -> None:
    from sb.domain.ai import operator_cards as cards

    await _card(req, await cards.build_support_report_embed(
        int(req.guild_id or 0)))
    return None


# --- panel-only pending terminals (the shipped chooser pages port with the
# --- policy/behavior/tools panel slices; clicks are golden-unpinned) --------------


async def policy_chooser_pending(req) -> Reply:
    return _ok("The AI policy chooser (per-channel/category/role scopes) "
               "ports with the policy-mutation slice — use `!ai policy` "
               "for the read-only dry-run meanwhile.")


async def behavior_chooser_pending(req) -> Reply:
    return _ok("The AI Behavior presets page ports with the "
               "policy-mutation slice — the declared `ai.*` settings are "
               "editable through `!settings` meanwhile.")


async def tools_chooser_pending(req) -> Reply:
    return _ok("The AI Tools & Workflows chooser ports with the "
               "orchestration-mutation slice — profiles are read-only "
               "meanwhile.")


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
    ("ai.policy_chooser_pending", policy_chooser_pending),
    ("ai.behavior_chooser_pending", behavior_chooser_pending),
    ("ai.tools_chooser_pending", tools_chooser_pending),
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


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()   # MODULE IMPORT — the BUG A rule (role/handlers.py pattern)


def ensure_handler_refs() -> None:
    _register()
