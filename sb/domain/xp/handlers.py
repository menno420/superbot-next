"""XP read/command handlers (band 4) — thin HandlerRef routes.

`!rank` sends the shipped rank IMAGE card (`rank.png` — the visual
card-engine H3 surface; goldens/xp/xp_chat_award pins the multipart send
+ the avatar `get_from_cdn` read) through the zero-action
``xp.rank_card`` panel. Category ranks resolve through the band-4
provider registry (sb.domain.community.rank_providers) exactly like the
shipped PR-G flow (their thinner provider CARD render is the visual
card-engine slice's follow-up — text until then).
"""

from __future__ import annotations

import dataclasses

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]

_STAT_TYPES = {"xp", "coins", "both"}     # shipped verbatim (xp_helpers)

#: bot1.py on_command_error's generic fallback, verbatim — the copy the
#: shipped bot sent when a command raised anything unclassified. The
#: capture world had no member gateway, so the shipped rank command's
#: member-name escalation (commands.MemberConverter → guild.query_members)
#: RAISED there and the global handler sent this; goldens/xp/
#: sweep_rank.json (`!rank test`) pins the byte.
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("xp.rank_view")):
        return

    @handler("xp.rank_view")
    async def rank_view(req) -> Reply | None:
        """!rank [stat|category|@user] — shipped PR-G arg walk verbatim."""
        from sb.domain.community.rank_providers import get_provider

        gid = int(req.guild_id or 0)
        member = int(getattr(req.actor, "user_id", 0) or 0)
        stat: str | None = None
        category: str | None = None
        for arg in tuple(req.args.get("argv", ()) or ()):
            token = str(arg)
            lowered = token.lower()
            if lowered in _STAT_TYPES:
                stat = lowered
                continue
            if lowered not in {"xp", "coins"}:
                provider = get_provider(lowered)
                if provider is not None:
                    category = provider.name
                    continue
            stripped = token.strip("<@!>")
            if stripped.isdigit():
                member = int(stripped)
                continue
            # DELIBERATE oracle-in-harness pin: the shipped walk escalated
            # a non-mention token to commands.MemberConverter, whose
            # name-lookup leg is a GATEWAY member query — the capture world
            # has none, so the shipped command raised and bot1.py's global
            # on_command_error sent the generic fallback
            # (goldens/xp/sweep_rank.json, `!rank test`). The live
            # name-resolution read lands with the member-directory search
            # port (follow-up slice); until then this is the same honest
            # failure the goldens pin.
            return Reply(BLOCKED, _GENERIC_ERROR)

        if category is not None:
            provider = get_provider(category)
            rank_pos, rendered = await provider.member_rank(gid, member)
            if rank_pos is None:
                return Reply(SUCCESS,
                             f"{provider.display_title} — <@{member}>\n"
                             f"{provider.empty_hint}")
            return Reply(SUCCESS,
                         f"{provider.display_title} — <@{member}>\n"
                         f"Rank **#{rank_pos}** · {rendered}")

        # the shipped H3 surface: the rank IMAGE card send (rank.png —
        # goldens/xp/xp_chat_award pins get_from_cdn + the multipart shape).
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(
            PanelRef("xp.rank_card"),
            dataclasses.replace(req, args={**dict(req.args),
                                           "rank_target": member,
                                           "rank_stat": stat or "both"}))
        return None

    @handler("xp.givexp")
    async def givexp(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            return Reply(BLOCKED, "Usage: `!givexp @user <amount>`")
        result = await engine.run(
            WorkflowRef("xp.award"),
            _ctx_from_req(req, {"argv": argv, "source": "admin:givexp"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not give XP.")
        after = (result.after or {}).get("award", {})
        return Reply(SUCCESS,
                     f"✅ Gave **{after.get('delta', 0)}** XP to "
                     f"<@{ctx_target(argv)}>. They now have "
                     f"**{after.get('new_xp', 0)}** XP "
                     f"(Level **{after.get('new_level', 0)}**).")

    @handler("xp.resetxp")
    async def resetxp(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!resetxp @user`")
        result = await engine.run(
            WorkflowRef("xp.reset"),
            _ctx_from_req(req, {"argv": argv, "source": "admin:resetxp"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not reset XP.")
        return Reply(SUCCESS, f"✅ Reset XP for <@{ctx_target(argv)}>.")

    @handler("xp.xpconfig_view")
    async def xpconfig_view(req) -> Reply | None:
        """!xpconfig — the shipped XpConfigView panel send (disbot/cogs/
        xp_cog.py xpconfig: ``ctx.send(embed=await view.build_embed(),
        view=view)``; goldens/xp/sweep_xpconfig.json pins the bytes)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("xp.config"), req)
        return None

    @handler("xp.xpimport")
    async def xpimport(req) -> Reply | None:
        """!xpimport [source] [#channel] [limit] — the shipped arg walk
        + scan flow verbatim (disbot/cogs/xp_cog.py xpimport: source key
        → int limit → TextChannelConverter, unknown tokens ignored; the
        "📥 Scanning…" send, the history read, the status.edit result —
        goldens/xp/sweep_xpimport.json pins the `!xpimport test` lane:
        "test" resolves BY NAME to a capture-world channel). Formats
        help works headlessly; the scan needs the history-scanner port
        (arms with the message band) — honest BLOCKED until then."""
        return await _xpimport_walk(req)

    @handler("xp.config_range_submit")
    async def config_range_submit(req) -> Reply:
        """The `_XpRangeModal` submit (disbot/views/xp/modals.py) — the
        shipped validation copy verbatim, then the two audited
        `settings.set_scalar` writes the shipped
        SettingsMutationPipeline made (xp_min first, xp_max second —
        the shipped write order; a first-write failure short-circuits
        exactly like the pipeline helper)."""
        try:
            mn = int(str(req.args.get("xp_min", "")).strip())
            mx = int(str(req.args.get("xp_max", "")).strip())
        except ValueError:
            return Reply(BLOCKED, "❌ Both values must be integers.")
        if mx < mn:
            return Reply(BLOCKED, "❌ Max must be ≥ min.")
        for name, value in (("xp_min", mn), ("xp_max", mx)):
            refusal = await _write_xp_scalar(req, name, value)
            if refusal is not None:
                return refusal
        return Reply(SUCCESS,
                     f"✅ XP range set: **{mn}–{mx}** XP per message.")

    @handler("xp.config_cooldown_submit")
    async def config_cooldown_submit(req) -> Reply:
        """The `_XpCooldownModal` submit — shipped validation copy
        verbatim, then the audited `settings.set_scalar` write."""
        try:
            val = int(str(req.args.get("seconds", "")).strip())
        except ValueError:
            return Reply(BLOCKED, "❌ Cooldown must be an integer.")
        refusal = await _write_xp_scalar(req, "xp_cooldown", val)
        if refusal is not None:
            return refusal
        return Reply(SUCCESS, f"✅ XP cooldown set: **{val}s**.")

    @handler("xp.config_channel_submit")
    async def config_channel_submit(req) -> Reply:
        """The `_XpChannelModal` submit — P0-3: the announce channel is
        a BINDING (the xp_announce_channel scalar was retired). Empty
        input clears the binding (announce in-place); a numeric ID sets
        it; anything else is the shipped refusal copy verbatim. Rides
        the audited `settings.bind`/`settings.unbind` ops (the
        server_logging bind precedent)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        raw = str(req.args.get("channel_id", "") or "").strip()
        if raw and not raw.strip("<#>").isdigit():
            return Reply(BLOCKED,
                         "❌ Channel must be empty (to clear) or a "
                         "numeric Discord channel ID.")
        if not raw:
            result = await engine.run(
                WorkflowRef("settings.unbind"),
                _ctx_from_req(req, {"subsystem": "xp",
                                    "name": "announce_channel"}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             result.user_message
                             or "Could not clear the channel.")
            return Reply(SUCCESS,
                         "✅ Level-up announcements now post in the "
                         "channel where the level-up happened.")
        channel_id = int(raw.strip("<#>"))
        result = await engine.run(
            WorkflowRef("settings.bind"),
            _ctx_from_req(req, {"subsystem": "xp",
                                "name": "announce_channel",
                                "kind": "channel",
                                "resource_id": channel_id}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Could not bind the channel.")
        return Reply(SUCCESS,
                     f"✅ Level-up announcements → <#{channel_id}>.")

    @handler("xp.import_setup_submit")
    async def import_setup_submit(req) -> Reply | None:
        """The 📥 import button's modal ingress — collects the SAME
        source/channel/limit args the `!xpimport` front door walks and
        delegates to that LIVE flow (the modal-ingress-over-live-front-
        door pattern; the shipped select-driven XpImportSetupView picker
        + preview/apply panel stay the import-preview slice's port — the
        walk's honest BLOCKED boundaries are unchanged)."""
        argv = tuple(
            str(req.args.get(field, "") or "").strip()
            for field in ("source", "channel", "limit")
            if str(req.args.get(field, "") or "").strip())
        return await _xpimport_walk(
            dataclasses.replace(req, args={**dict(req.args),
                                           "argv": argv}))


async def _write_xp_scalar(req, name: str, value: int) -> Reply | None:
    """One audited scalar write through the live `settings.set_scalar`
    op (the rps `rpssettings` / ai settings-widget precedent) after the
    declared-bounds check the shipped pipeline's SettingSpec validators
    made. Returns ``None`` on success, the refusal Reply otherwise."""
    from sb.kernel import settings as ksettings
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    lo, hi = _SCALAR_BOUNDS[name]
    if not (lo <= int(value) <= hi):
        return Reply(BLOCKED,
                     f"❌ {name} must be between {lo} and {hi}.")
    result = await engine.run(
        WorkflowRef("settings.set_scalar"),
        _ctx_from_req(req, {"key": ksettings.persisted_key("xp", name),
                            "value": str(int(value)),
                            "subsystem": "xp",
                            "name": name}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message or f"Could not update {name}.")
    return None


#: the declared SettingSpec bounds, mirrored (sb/manifest/xp.py
#: _SETTINGS — the manifest imports THIS module, so the domain carries
#: the numbers; the shipped pipeline enforced _validate_positive_int
#: the same way, caller-side of the write).
_SCALAR_BOUNDS = {
    "xp_min": (1, 10_000),
    "xp_max": (1, 10_000),
    "xp_cooldown": (0, 86_400),
}


async def _xpimport_walk(req) -> Reply | None:
    """The shared `!xpimport` walk (command front door + the config
    panel's modal ingress): source key → int limit →
    TextChannelConverter, unknown tokens ignored."""
    from sb.domain.xp import migrate, service

    argv = tuple(req.args.get("argv", ()) or ())
    lowered = {str(a).lower() for a in argv}
    if lowered & {"help", "formats", "list"}:
        lines = ["📥 **Import XP from another bot** — supported "
                 "level-up announcement formats:"]
        for key in migrate.format_keys():
            fmt = migrate.get_format(key)
            default = " *(default)*" if key == migrate.DEFAULT_FORMAT else ""
            lines.append(f"`{key}`{default} — {fmt.label}")
        lines.append("Usage: `!xpimport [source] [#channel] [limit]` — "
                     "raise-only, preview first.")
        return Reply(SUCCESS, "\n".join(lines))
    scanner = service.active_history_scanner()
    if scanner is None:
        return Reply(BLOCKED,
                     "📥 The channel scan needs message-history access, "
                     "which arms with the message band. The parsing "
                     "formats and the raise-only import op are live — "
                     "`!xpimport help` lists the supported bots.")

    gid = int(req.guild_id or 0)
    source_key: str | None = None
    channel_id: int | None = None
    limit: int | None = None
    for arg in argv:
        token = str(arg)
        key = token.lower()
        if migrate.get_format(key) is not None:
            source_key = key
            continue
        try:
            limit = int(token)
            continue
        except ValueError:
            pass
        resolved = await service.resolve_text_channel(gid, token)
        if resolved is not None:
            channel_id = resolved
        # else: unknown token — ignore (the shipped BadArgument pass;
        # the preview shows what was scanned)

    fmt = migrate.get_format(source_key or migrate.DEFAULT_FORMAT)
    target = channel_id or int(req.channel_id or 0)

    from sb.kernel.panels.engine import open_panel, refresh_session_view
    from sb.spec.refs import PanelRef

    base = {"scan_channel_id": target, "scan_fmt_label": fmt.label}
    key_ref = await open_panel(
        PanelRef("xp.import_scan"),
        dataclasses.replace(req, args={**dict(req.args), **base,
                                       "scan_phase": "scanning"}))
    messages = await scanner(target, limit=limit)
    records: list[tuple[int, int]] = []
    for message in messages or ():
        parsed = migrate.parse_level_message(
            str(getattr(message, "content", "") or ""),
            tuple(getattr(message, "mention_ids", ()) or ()),
            fmt=fmt)
        if parsed is not None and parsed.user_id is not None:
            records.append((parsed.user_id, parsed.level))
    scanned = len(tuple(messages or ()))
    if not records:
        await refresh_session_view(
            req, message_key=key_ref,
            params={**base, "scan_phase": "empty",
                    "scan_scanned": scanned},
            expire=True)
        return None
    # UNDER-PORT boundary: the shipped preview panel (XpImportView
    # Apply/Cancel over the raise-only xp.import_levels op) is the
    # import-preview slice's port — no golden reaches a non-empty
    # scan (the capture world held no channel messages), so the
    # honest posture is the declared refusal, never a silent apply
    # (and never the nothing-found edit over a found batch).
    return Reply(BLOCKED,
                 f"📥 Found **{len(records)}** level-up record(s) in "
                 f"**{scanned}** message(s) — the preview/apply panel "
                 "ports with the import-preview slice (the raise-only "
                 "import op is live).")


def ctx_target(argv: tuple) -> int:
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit():
            return int(stripped)
    return 0


_register()


def ensure_handler_refs() -> None:
    _register()
