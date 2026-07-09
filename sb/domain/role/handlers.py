"""Role command handlers (band 5) — thin HandlerRef routes: text views
over the DB truth, K7-lane routes for the audited writes, and honest
pending terminals for surfaces needing the live guild view / the
role-provisioning port (roleinfo, createrole/deleterole, assignroles,
debugroles, refreshmembers, rolecreator — the band-2 precedent).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


def _int_token(argv, index: int = 0) -> int | None:
    toks = [str(t).strip("<@&!#>") for t in argv]
    picked = [t for t in toks if t.isdigit()]
    return int(picked[index]) if len(picked) > index else None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("role.time_roles_view")):
        return

    @handler("role.time_roles_view")
    async def time_roles_view(req) -> Reply:
        """!rolesettings / the hub Time Roles view — the threshold table."""
        from sb.domain.role import store

        rows = await store.get_thresholds(int(req.guild_id or 0))
        time_rows = [r for r in rows if r["days_required"]]
        if not time_rows:
            return Reply(SUCCESS, "⏱️ No time-based role tiers configured. "
                                  "Use `!setrole <days> <role>`.")
        lines = [f"• **{r['role_name']}** — {r['days_required']} day(s)"
                 for r in time_rows]
        return Reply(SUCCESS, "⏱️ **Time role tiers**\n" + "\n".join(lines))

    @handler("role.xp_roles_view")
    async def xp_roles_view(req) -> Reply:
        from sb.domain.role import store

        rows = await store.get_thresholds(int(req.guild_id or 0))
        xp_rows = [r for r in rows if r.get("xp_auto_assign")
                   and r.get("level_required") is not None]
        if not xp_rows:
            return Reply(SUCCESS, "⚡ No XP role tiers configured.")
        xp_rows.sort(key=lambda r: r["level_required"])
        lines = [f"• **{r['role_name']}** — level {r['level_required']}"
                 for r in xp_rows]
        return Reply(SUCCESS, "⚡ **XP role tiers**\n" + "\n".join(lines))

    @handler("role.reaction_view")
    async def reaction_view(req) -> Reply:
        """!listreactroles / the hub Reaction Roles view."""
        from sb.domain.role import store

        gid = int(req.guild_id or 0)
        bindings = await store.list_reaction_bindings(gid)
        menus = await store.list_menus(gid)
        if not bindings and not menus:
            return Reply(SUCCESS, "💬 No reaction roles configured. "
                                  "`!reactroles <message_id> <emoji> <@role>`")
        lines = [f"• msg `{b['message_id']}` {b['emoji']} → <@&{b['role_id']}>"
                 for b in bindings[:20]]
        lines += [f"• menu #{m['menu_id']} “{m['title']}” ({m['style']}, "
                  f"{m['mode']})" for m in menus[:10]]
        return Reply(SUCCESS, "💬 **Reaction roles**\n" + "\n".join(lines))

    @handler("role.exemptions_view")
    async def exemptions_view(req) -> Reply:
        from sb.domain.role import store

        rows = await store.get_exemptions(int(req.guild_id or 0))
        if not rows:
            return Reply(SUCCESS, "🚫 No automation-exempt roles.")
        lines = [
            f"• <@&{r['role_id']}> — "
            f"{'XP ' if r['exempt_xp'] else ''}"
            f"{'Time' if r['exempt_time'] else ''}".rstrip()
            for r in rows]
        return Reply(SUCCESS, "🚫 **Automation exemptions**\n" + "\n".join(lines))

    @handler("role.diagnostics_view")
    async def diagnostics_view(req) -> Reply:
        """The hub Diagnostics view — DB-truth counts; live preflight
        (hierarchy/permission) needs the guild view and reports honestly."""
        from sb.domain.role import service, store

        gid = int(req.guild_id or 0)
        rows = await store.get_thresholds(gid)
        guild = await service.guild_view(gid)
        preflight = "live preflight unavailable (guild view port unarmed)"
        if guild is not None:
            from sb.domain.role.automation import RoleThreshold, check_preflight

            result = check_preflight(guild, tuple(
                RoleThreshold(r["role_name"], int(r["days_required"] or 0),
                              r.get("role_id")) for r in rows))
            preflight = ("✅ preflight OK" if result.ok else
                         f"⚠️ manage_roles={result.bot_has_manage_roles}, "
                         f"blockers={list(result.hierarchy_blockers)}, "
                         f"missing={list(result.missing_roles)}")
        return Reply(SUCCESS,
                     f"🔧 **Role automation** — {len(rows)} threshold row(s)\n"
                     f"{preflight}")

    @handler("role.manage_view")
    async def manage_view(req) -> Reply:
        from sb.domain.role import store

        gid = int(req.guild_id or 0)
        stats = await store.pickup_stats(gid)
        head = "\n".join(
            f"• <@&{s['role_id']}> — {s['picked']} picked / "
            f"{s['removed']} removed" for s in stats[:10])
        return Reply(SUCCESS, "🗂️ **Role pickup stats**\n" +
                     (head or "No pickup activity recorded yet."))

    @handler("role.reactroles_bind")
    async def reactroles_bind(req) -> Reply:
        """!reactroles <message_id> <emoji> <@role> (alias reaktionsrollen)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            return Reply(BLOCKED,
                         "Usage: `!reactroles <message_id> <emoji> <@role>`")
        message_id = _int_token(argv[:1])
        role_id = _int_token(argv[2:])
        emoji = str(argv[1])
        result = await engine.run(
            WorkflowRef("role.bind_reaction"),
            _ctx_from_req(req, {"message_id": message_id, "emoji": emoji,
                                "role_id": role_id, "argv": argv}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind.")
        return Reply(SUCCESS, f"✅ Reacting with {emoji} on message "
                              f"`{message_id}` now grants <@&{role_id}>.")

    @handler("role.reactroles_unbind")
    async def reactroles_unbind(req) -> Reply:
        """!removereactrole <message_id> <emoji>."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            return Reply(BLOCKED,
                         "Usage: `!removereactrole <message_id> <emoji>`")
        result = await engine.run(
            WorkflowRef("role.unbind_reaction"),
            _ctx_from_req(req, {"message_id": _int_token(argv[:1]),
                                "emoji": str(argv[1])}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not unbind.")
        removed = (result.after or {}).get("record", {}).get("removed")
        return Reply(SUCCESS, "🗑️ Binding removed." if removed
                     else "That binding did not exist.")

    @handler("role.setrole")
    async def setrole(req) -> Reply:
        """!setrole <days> <role name> — the time-tier write."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2 or not str(argv[0]).isdigit():
            return Reply(BLOCKED, "Usage: `!setrole <days> <role name>`")
        result = await engine.run(
            WorkflowRef("role.set_threshold"),
            _ctx_from_req(req, {
                "days_required": int(argv[0]),
                "role_name": " ".join(str(a) for a in argv[1:])}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not set the tier.")
        after = (result.after or {}).get("record", {})
        return Reply(SUCCESS, f"✅ **{after.get('role_name')}** auto-assigns "
                              f"at {after.get('days_required')} day(s).")

    @handler("role.unsetrole")
    async def unsetrole(req) -> Reply:
        """!unsetrole <role name>."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!unsetrole <role name>`")
        result = await engine.run(
            WorkflowRef("role.remove_threshold"),
            _ctx_from_req(req, {
                "role_name": " ".join(str(a) for a in argv)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not remove the tier.")
        removed = (result.after or {}).get("record", {}).get("removed")
        return Reply(SUCCESS, "🗑️ Tier removed." if removed
                     else "No such tier was configured.")

    @handler("role.temprole")
    async def temprole(req) -> Reply:
        """!temprole @member <duration> <@role> — duration like 2h/30m/1d."""
        from sb.domain.role import service

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            return Reply(BLOCKED,
                         "Usage: `!temprole @member <duration> <@role>`")
        member_id = _int_token(argv)
        role_id = _int_token(argv, 1)
        seconds = _parse_duration(str(argv[1]))
        if member_id is None or role_id is None or seconds is None:
            return Reply(BLOCKED,
                         "Usage: `!temprole @member <duration> <@role>` — "
                         "duration like `2h`, `30m`, `1d`.")
        try:
            expires = await service.grant_temp_role(
                _ctx_from_req(req, {}), member_id=member_id,
                role_id=role_id, seconds=seconds)
        except RuntimeError as exc:
            return Reply(BLOCKED, f"⚠️ {exc}")
        return Reply(SUCCESS, f"⏳ <@{member_id}> holds <@&{role_id}> until "
                              f"{expires.strftime('%Y-%m-%d %H:%M UTC')}.")

    @handler("role.temproles")
    async def temproles(req) -> Reply:
        """!temproles [@member] — active grants, soonest first."""
        from sb.domain.role import service

        argv = tuple(req.args.get("argv", ()) or ())
        member_id = _int_token(argv) or int(
            getattr(req.actor, "user_id", 0) or 0)
        grants = await service.list_active_grants(
            int(req.guild_id or 0), member_id)
        if not grants:
            return Reply(SUCCESS, f"<@{member_id}> has no active "
                                  "temporary roles.")
        lines = [f"• <@&{rid}> — until {exp.strftime('%Y-%m-%d %H:%M UTC')}"
                 for rid, exp in grants]
        return Reply(SUCCESS, f"⏳ **Temporary roles for <@{member_id}>**\n"
                     + "\n".join(lines))


def _register_task_fire() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("role.grants_expiry_fire")):
        return

    @handler("role.grants_expiry_fire")
    async def grants_expiry_fire(ctx) -> str:
        """The role:grants_expiry ManagedTaskSpec body (A-8): the
        externally-effecting sweep — Discord removal via the actions
        port, row drop through the audited K7 expire lane."""
        from sb.domain.role import service

        resolved = await service.sweep_expired()
        return f"resolved={resolved}"


def _parse_duration(token: str) -> int | None:
    """2h/30m/1d/90s → seconds (shipped duration vocabulary)."""
    token = token.strip().lower()
    if not token:
        return None
    unit = token[-1]
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit)
    body = token[:-1] if mult else token
    if mult is None:
        mult = 60  # bare number = minutes (shipped default)
    if not body.isdigit():
        return None
    value = int(body) * mult
    return value if value > 0 else None


def ensure_handler_refs() -> None:
    _register()
    _register_task_fire()
    from sb.domain.operator_spine import pending_handler

    pending_handler("role.create_pending",
                    "📝 Role creation needs the live role-provisioning "
                    "port (arms with the live adapter at CUT-1).")
    pending_handler("role.roleinfo_pending",
                    "ℹ️ Role info needs the live guild view "
                    "(arms with the live adapter).")
    pending_handler("role.assignroles_pending",
                    "⏱️ The role check needs the live guild view "
                    "(arms with the live adapter).")
    pending_handler("role.debug_pending",
                    "🔧 Live role diagnostics need the gateway cache "
                    "(arms with the live adapter).")


_register()
_register_task_fire()
