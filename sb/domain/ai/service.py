"""AI-surface handlers (band 7) — the shipped ``!ai`` + ``!aireview``
groups: the ``!ai`` operator views render the SHIPPED embeds
(sb/domain/ai/operator_cards.py — goldens/ai pin the bytes) presented
through the generic ``ai.card`` panel (the projmoon.card pattern);
``forget`` / ``why-no-response`` keep their shipped plain-text replies.

Registered at MODULE IMPORT (declaring IS reserving — the BUG A rule,
sb/domain/role/handlers.py pattern): the live root imports and dispatches
without ever running the manifest ENSURE_REFS hooks. This pruned all 20
``handler:ai.*`` rows from the composition-parity burn-down list.

The ``!aireview`` lanes (review log + vetted presets) are the shipped
cogs/ai_review_cog.py command surface reply-for-reply over the K7 typed
ops — the re-homed goldens/ai/sweep_aireview* family pins the bytes.
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


async def _card(req, embed, files: tuple = ()) -> None:
    """Present one operator card as the shipped public embed reply
    (``files`` ride as message attachments — the shipped
    ``discord.File`` send; the export dump uses it)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args), "_card": embed}
    if files:
        args["_card_files"] = tuple(files)
    await open_panel(PanelRef("ai.card"), dataclasses.replace(req, args=args))


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


# --- !aireview group ---------------------------------------------------------------
# The shipped cogs/ai_review_cog.py command surface, reply-for-reply (the
# re-homed goldens/ai/sweep_aireview* family pins the bytes). Unparseable
# int/channel arguments mirror the shipped converter behavior: discord.py
# raised BadArgument/MissingRequiredArgument, which the shipped bot only
# reported to its ops webhook — the invoker saw NOTHING (silent return).


def _clip(text: object, cap: int = 1000) -> str:
    """Stringify + trim to *cap* chars — shipped ai_review_cog._clip."""
    value = ("" if text is None else str(text)).strip()
    if not value:
        return ""
    return value if len(value) <= cap else value[: cap - 1] + "…"


#: shipped no-guild guard byte (every !aireview subcommand carries it).
_NEEDS_GUILD = "This command needs a server context."

#: discord.py StringView opening→closing quote pairs (the subset a chat
#: client actually produces; the harness/live feed collapses whitespace
#: before this parser sees the text).
_QUOTES = {'"': '"', "“": "”", "‘": "’", "«": "»", "‹": "›",
           "„": "“", "‟": "”"}


def _split_leading_token(text: str) -> tuple[str, str]:
    """(first argument, rest) with discord.py-style quote handling — the
    shipped ``preset add "<question>" <answer>`` converter split."""
    text = text.strip()
    if not text:
        return "", ""
    close = _QUOTES.get(text[0])
    if close:
        end = text.find(close, 1)
        if end > 0:
            return text[1:end], text[end + 1:].strip()
    head, _, rest = text.partition(" ")
    return head, rest.strip()


async def _review_channel_display(guild_id: int) -> str:
    """The bare-status "Review channel:" value — the shipped
    resolve_settings_channel read over the legacy-KV pointer. Ledgered
    under-port: no live channel-existence probe (the shipped helper
    checked ``guild.get_channel``); a set-but-deleted channel renders as
    its mention here instead of ``*(not set)*``."""
    from sb.domain.ai import store as ai_store

    try:
        value = await ai_store.get_review_channel_value(guild_id)
    except Exception:  # noqa: BLE001 — store unreachable → unset display
        value = None
    if value and value.isdigit() and int(value):
        return f"<#{int(value)}>"
    return "*(not set)*"


async def _count_unreviewed_safe(guild_id: int, kind: str) -> int:
    """Shipped ai_review_log_service.count_unreviewed: 0 on any failure."""
    from sb.domain.ai import store as ai_store

    try:
        return await ai_store.count_unreviewed(guild_id, kind=kind)
    except Exception:  # noqa: BLE001 — shipped fail-safe read
        return 0


async def _get_entry_safe(guild_id: int, entry_id: int) -> dict | None:
    """Shipped ai_review_log_service.get_entry: None on any failure."""
    from sb.domain.ai import store as ai_store

    try:
        return await ai_store.get_entry(guild_id, entry_id)
    except Exception:  # noqa: BLE001 — shipped fail-safe read
        return None


async def aireview_usage_view(req) -> Reply | None:
    """Bare ``!aireview`` — the shipped review-log status embed
    (goldens/ai/sweep_aireview pins every byte)."""
    from sb.kernel.panels.render import RenderedEmbed

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    gid = int(req.guild_id)
    where = await _review_channel_display(gid)
    unknown_n = await _count_unreviewed_safe(gid, "unknown")
    corr_n = await _count_unreviewed_safe(gid, "correction")
    await _card(req, RenderedEmbed(
        title="🔎 AI answer review log",
        description=(f"Review channel: {where}\n"
                     f"Unreviewed — **{unknown_n}** didn't-know · "
                     f"**{corr_n}** corrections"),
        footer=("!aireview channel #chan · !aireview list "
                "[unknown|correction] · !aireview export · "
                "!aireview resolve <id> · !aireview off"),
        style_token="dark_red"))
    return None


async def _run_review_channel_op(req, channel_id: int | None):
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    return await engine.run(
        WorkflowRef("ai.set_review_channel"),
        _ctx_from_req(req, {"channel_id": channel_id}))


async def review_channel_route(req) -> Reply | None:
    """``!aireview channel #chan`` — set the review feed channel (the
    no-argument usage byte is golden-pinned: sweep_aireview_channel)."""
    import re

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    argv = _argv(req)
    if not argv:
        return _ok("Usage: `!aireview channel #channel` "
                   "(or `!aireview off` to clear).")
    m = re.match(r"^<#(\d{15,20})>$|^(\d{15,20})$", argv[0])
    if m is None:
        # shipped: TextChannel converter raised ChannelNotFound →
        # webhook-only report, no invoker reply (name-lookup is a
        # ledgered under-port; the btd6 announcechannel precedent).
        return None
    channel_id = int(m.group(1) or m.group(2))
    result = await _run_review_channel_op(req, channel_id)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message or "Couldn't update the setting.")
    return _ok(f"✅ AI didn't-know answers + user corrections will post to "
               f"<#{channel_id}>. Clear with `!aireview off`.")


async def review_off_route(req) -> Reply:
    """``!aireview off`` — clear the review channel (entries are still
    recorded; goldens/ai/sweep_aireview_off pins reply + row bytes)."""
    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    result = await _run_review_channel_op(req, None)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message or "Couldn't update the setting.")
    return _ok("✅ Review channel cleared — entries are still recorded; "
               "query them with `!aireview list`.")


def _entry_heading(row: dict) -> str:
    mark = "✅" if row.get("reviewed") else "•"
    label = ("correction" if row.get("kind") == "correction"
             else "didn't-know")
    return f"{mark} #{row.get('id')} · {label} · {row.get('reason_code') or '?'}"


def _entry_summary(row: dict) -> str:
    parts: list[str] = []
    question = _clip(row.get("question"), 300)
    if question:
        parts.append(f"**Q:** {question}")
    if row.get("kind") == "correction":
        fix = _clip(row.get("correction"), 300)
        if fix:
            parts.append(f"**Fix:** {fix}")
    else:
        answer = _clip(row.get("answer"), 300)
        if answer:
            parts.append(f"**A:** {answer}")
    return "\n".join(parts) or "*(no text captured)*"


def _list_kind_filter(token: str | None) -> str | None:
    if not token:
        return None
    lowered = token.lower()
    if lowered in ("unknown", "u", "didnt-know", "didntknow"):
        return "unknown"
    if lowered in ("correction", "corrections", "c"):
        return "correction"
    return None


async def review_list_view(req) -> Reply | None:
    """``!aireview list [unknown|correction] [n]`` — shipped list embed;
    the empty-state byte is golden-pinned (sweep_aireview_list)."""
    from sb.domain.ai import store as ai_store
    from sb.kernel.panels.render import RenderedEmbed

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    argv = _argv(req)
    limit = 10
    if len(argv) > 1:
        if not argv[1].lstrip("-").isdigit():
            return None            # shipped int-converter BadArgument
        limit = int(argv[1])
    rows = await ai_store.query_entries(
        int(req.guild_id), kind=_list_kind_filter(argv[0] if argv else None),
        limit=max(1, min(25, limit)))
    if not rows:
        return _ok("No AI review entries recorded yet.")
    await _card(req, RenderedEmbed(
        title="🔎 AI review log — recent", description="",
        fields=tuple((_entry_heading(r), _entry_summary(r), False)
                     for r in rows[:10]),
        footer="Mark one done with !aireview resolve <id>",
        style_token="dark_red"))
    return None


def _parse_export_flags(flags: tuple[str, ...]) -> tuple[str | None, bool]:
    """Shipped ai_review_cog._parse_export_flags, verbatim."""
    lowered = {f.lower() for f in flags}
    include_reviewed = "all" in lowered
    filter_kind: str | None = None
    if {"unknown", "u", "unknowns"} & lowered:
        filter_kind = "unknown"
    elif {"correction", "corrections", "c"} & lowered:
        filter_kind = "correction"
    return filter_kind, include_reviewed


async def review_export_view(req) -> Reply | None:
    """``!aireview export [all|unknown|correction]`` — the triage dump
    (shipped JSON file send; the empty-state byte is golden-pinned:
    sweep_aireview_export)."""
    import json

    from sb.domain.ai import store as ai_store
    from sb.kernel.panels.render import RenderedAttachment, RenderedEmbed

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    gid = int(req.guild_id)
    filter_kind, include_reviewed = _parse_export_flags(tuple(_argv(req)))
    rows = await ai_store.export_entries(
        gid, kind=filter_kind, include_reviewed=include_reviewed)
    if not rows:
        scope = "any" if include_reviewed else "unreviewed"
        return _ok(f"No {scope} AI review entries to export.")
    entries = []
    for row in rows:
        item = dict(row)
        created = item.get("created_at")
        if hasattr(created, "isoformat"):
            item["created_at"] = created.isoformat()
        entries.append(item)
    payload = {
        "schema": "ai_review_export",
        "version": 1,
        "guild_id": gid,
        "kind": filter_kind or "all",
        "include_reviewed": include_reviewed,
        "count": len(entries),
        "entries": entries,
    }
    blob = json.dumps(payload, indent=2, ensure_ascii=False)
    # ledgered deviation: the shipped send was plain CONTENT + file; the
    # port rides the panel attachment seam, so the summary line lands as
    # the card description (the multipart capture shape — filenames only —
    # is identical on both).
    n = len(entries)
    summary = (
        f"📤 Exported **{n}** AI review "
        f"{'entry' if n == 1 else 'entries'} "
        f"({'all' if include_reviewed else 'unreviewed'}"
        f"{', ' + filter_kind if filter_kind else ''}). "
        "Paste this file's contents back to work the backlog, or run "
        "`scripts/ai_review_triage.py` on it.")
    await _card(req, RenderedEmbed(title="", description=summary),
                files=(RenderedAttachment(
                    filename=f"ai_review_export_{gid}.json",
                    data=blob.encode("utf-8")),))
    return None


async def review_resolve_route(req) -> Reply | None:
    """``!aireview resolve <id>`` — mark one entry reviewed (shipped
    bytes; the miss byte is golden-pinned: sweep_aireview_resolve)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    argv = _argv(req)
    if not argv or not argv[0].lstrip("-").isdigit():
        return None                # shipped int-converter BadArgument
    entry_id = int(argv[0])
    entry = await _get_entry_safe(int(req.guild_id), entry_id)
    if entry is None:
        return _ok(f"⚠️ No entry `#{entry_id}` in this server.")
    result = await engine.run(
        WorkflowRef("ai.resolve_review_entry"),
        _ctx_from_req(req, {"entry_id": entry_id}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message
                     or f"⚠️ No entry `#{entry_id}` in this server.")
    return _ok(f"✅ Entry #{entry_id} marked reviewed.")


# --- !aireview preset subgroup -------------------------------------------------------


async def preset_usage_view(req) -> Reply:
    """Bare ``!aireview preset`` — the shipped usage copy
    (goldens/ai/sweep_aireview_preset pins the bytes)."""
    return _ok(
        "Vetted answer presets — the bot serves these verbatim, no AI "
        "call:\n"
        '`!aireview preset add "<question>" <answer>` · '
        "`!aireview preset from <entry_id> <answer>` · "
        "`!aireview preset list` · `!aireview preset remove <id>`")


async def _store_preset(req, question: str, answer: str, *,
                        task: str | None = None,
                        source: str | None = None) -> Reply:
    """Shared add/from leg — validate, store, confirm (shipped
    _store_preset: the ✅ byte with mentions suppressed; the guard bytes
    are the shipped service ValueError strings)."""
    from sb.domain.ai import normalize
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not normalize.normalize_question(question):
        return _ok("⚠️ Couldn't store that preset: question is empty "
                   "after normalization.")
    if not (answer or "").strip():
        return _ok("⚠️ Couldn't store that preset: answer is empty.")
    result = await engine.run(
        WorkflowRef("ai.set_preset"),
        _ctx_from_req(req, {"question": question, "answer": answer,
                            "task": task, "source": source or "operator"}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     "⚠️ Couldn't store that preset: "
                     f"{result.user_message or 'storage failed'}.")
    # engine rollup keys each leg's after by its StepResult target_name
    after = (result.after or {}).get("set_preset") or {}
    preset_id = after.get("preset_id")
    return Reply(
        SUCCESS,
        f"✅ Preset `#{preset_id}` stored — the bot will answer "
        f"“{_clip(question, 120)}” with your vetted text (no AI call). "
        f"Remove it with `!aireview preset remove {preset_id}`.",
        suppress_mentions=True)


async def preset_add_route(req) -> Reply | None:
    """``!aireview preset add "<question>" <answer>`` — author a preset
    (goldens/ai/sweep_aireview_preset_add pins reply + row bytes)."""
    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    text = str(req.args.get("text") or "") or " ".join(_argv(req))
    question, answer = _split_leading_token(text)
    if not question or not answer:
        return None            # shipped MissingRequiredArgument (silent)
    return await _store_preset(req, question, answer, source="operator")


async def preset_from_route(req) -> Reply | None:
    """``!aireview preset from <entry_id> <answer…>`` — vet a logged
    question (the miss byte is golden-pinned: sweep_aireview_preset_from)."""
    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    text = str(req.args.get("text") or "") or " ".join(_argv(req))
    token, answer = _split_leading_token(text)
    if not token or not token.lstrip("-").isdigit() or not answer:
        return None            # shipped converter error (silent)
    entry_id = int(token)
    entry = await _get_entry_safe(int(req.guild_id), entry_id)
    if entry is None:
        return _ok(f"⚠️ No review entry `#{entry_id}` in this server.")
    question = (entry.get("question") or "").strip()
    if not question:
        return _ok(f"⚠️ Entry `#{entry_id}` has no captured question text "
                   "to key a preset on.")
    return await _store_preset(req, question, answer,
                               task=entry.get("task"),
                               source=f"review:{entry_id}")


async def preset_list_view(req) -> Reply | None:
    """``!aireview preset list [n]`` — the shipped 🧠 embed; the
    empty-state byte is golden-pinned (sweep_aireview_preset_list)."""
    from sb.domain.ai import store as ai_store
    from sb.kernel.panels.render import RenderedEmbed

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    argv = _argv(req)
    limit = 10
    if argv:
        if not argv[0].lstrip("-").isdigit():
            return None            # shipped int-converter BadArgument
        limit = int(argv[0])
    rows = await ai_store.list_presets(int(req.guild_id),
                                       limit=max(1, min(25, limit)))
    if not rows:
        return _ok("No vetted presets yet. Add one with "
                   '`!aireview preset add "<question>" <answer>`.')
    fields = []
    for row in rows[:10]:
        mark = "" if row.get("enabled", True) else " *(disabled)*"
        fields.append((f"#{row.get('id')}{mark}",
                       f"**Q:** {_clip(row.get('question'), 200)}\n"
                       f"**A:** {_clip(row.get('answer'), 300)}",
                       False))
    await _card(req, RenderedEmbed(
        title="🧠 Vetted answer presets", description="",
        fields=tuple(fields),
        footer="Remove one with !aireview preset remove <id>",
        style_token="green"))
    return None


async def preset_remove_route(req) -> Reply | None:
    """``!aireview preset remove <id>`` — delete one preset (the miss
    byte is golden-pinned: sweep_aireview_preset_remove)."""
    from sb.domain.ai import store as ai_store
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not req.guild_id:
        return _ok(_NEEDS_GUILD)
    argv = _argv(req)
    if not argv or not argv[0].lstrip("-").isdigit():
        return None                # shipped int-converter BadArgument
    preset_id = int(argv[0])
    try:
        existing = await ai_store.get_preset(int(req.guild_id), preset_id)
    except Exception:  # noqa: BLE001 — store unreachable → miss byte
        existing = None
    if existing is None:
        return _ok(f"⚠️ No preset `#{preset_id}` in this server.")
    result = await engine.run(
        WorkflowRef("ai.remove_preset"),
        _ctx_from_req(req, {"preset_id": preset_id}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message
                     or f"⚠️ No preset `#{preset_id}` in this server.")
    return _ok(f"✅ Preset `#{preset_id}` removed.")


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
    ("ai.review_usage_view", aireview_usage_view),
    ("ai.review_list_view", review_list_view),
    ("ai.review_export_view", review_export_view),
    ("ai.review_channel_route", review_channel_route),
    ("ai.review_off_route", review_off_route),
    ("ai.review_resolve_route", review_resolve_route),
    ("ai.preset_usage_view", preset_usage_view),
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
