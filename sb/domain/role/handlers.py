"""Role command handlers (band 5) — thin HandlerRef routes: text views
over the DB truth, K7-lane routes for the audited writes, and honest
pending terminals for surfaces needing the live guild view / the
role-provisioning port (roleinfo, createrole/deleterole, assignroles,
debugroles, refreshmembers, rolecreator — the band-2 precedent).
"""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _int_token(argv, index: int = 0) -> int | None:
    toks = [str(t).strip("<@&!#>") for t in argv]
    picked = [t for t in toks if t.isdigit()]
    return int(picked[index]) if len(picked) > index else None


def _leg_after(result, step_name: str) -> dict:
    """One leg's ``after`` payload out of a WorkflowResult. The engine's
    rollup keys ``result.after`` by each step's ``target_name`` (there is
    no "record" key — reading one ackked over correct writes with None/
    miss copy, the band-5 live-drive bug 2)."""
    after = result.after if isinstance(result.after, dict) else {}
    leg = after.get(step_name)
    return leg if isinstance(leg, dict) else {}


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
            # the shipped empty copy verbatim (role_cog.py list command /
            # goldens/role/sweep_listreactroles)
            return Reply(SUCCESS, "No reaction roles configured.")
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
        """!reactroles <message_id> <emoji> <@role> (alias reaktionsrollen)
        — the shipped sequence verbatim (role_cog.add_reaction_role /
        goldens/role/sweep_reactroles): fetch the target message
        (`get_message` on the wire), write the binding, add the bot's own
        reaction (`add_reaction`), then ack with the ROLE NAME."""
        from sb.domain.role import service
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            return Reply(BLOCKED,
                         "Usage: `!reactroles <message_id> <emoji> <@role>`")
        message_id = _int_token(argv[:1])
        role_id = _int_token(argv[2:])
        emoji = str(argv[1])
        channel_id = int(req.channel_id or 0)
        try:
            # the shipped `ctx.fetch_message(message_id)` — NotFound
            # answers the shipped guard byte; an uninstalled port is the
            # honest wait (moderation-actions posture).
            await service.active_message_ops().fetch_message(
                channel_id, int(message_id or 0))
        except LookupError:
            # the shipped discord.NotFound branch (role_cog.py)
            return Reply(BLOCKED,
                         "❌ Message not found in this channel.")
        except RuntimeError as exc:
            return Reply(BLOCKED, f"⚠️ {exc}")
        result = await engine.run(
            WorkflowRef("role.bind_reaction"),
            _ctx_from_req(req, {"message_id": message_id, "emoji": emoji,
                                "role_id": role_id, "argv": argv}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind.")
        reaction_warn = None
        try:
            # the shipped `message.add_reaction(emoji)` — a refused
            # reaction keeps the saved row and warns (role_cog.py).
            await service.active_message_ops().add_reaction(
                channel_id, int(message_id or 0), emoji)
        except Exception:  # noqa: BLE001 — shipped HTTPException guard
            reaction_warn = ("⚠️ Role saved, but I couldn't add the "
                             "reaction (invalid emoji?).")
        if reaction_warn is not None:
            return Reply(SUCCESS, reaction_warn)
        role_name = f"<@&{role_id}>"
        guild = await service.guild_view(int(req.guild_id or 0))
        if guild is not None and role_id is not None:
            role = service.find_role(guild, str(role_id))
            if role is not None:
                role_name = str(getattr(role, "name", role_name))
        # the shipped ack verbatim (role_cog.py / sweep_reactroles)
        return Reply(SUCCESS, f"✅ Reaction role set: reacting with "
                              f"{emoji} assigns **{role_name}**.")

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
        # the shipped ack is UNCONDITIONAL (role_cog.py:705 — the cog runs
        # a bare DELETE and always speaks the removed byte; there is no
        # existence branch in the oracle, and goldens/role/
        # sweep_removereactrole pins the success ack over an absent row).
        # The band-5 "That binding did not exist." miss copy was a port
        # invention — retired at the re-home (oracle-wins).
        return Reply(SUCCESS,
                     f"✅ Reaction role for {argv[1]} on that message "
                     "removed.")

    @handler("role.setrole")
    async def setrole(req) -> Reply:
        """!setrole <days> <role name> — the time-tier write."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2 or not str(argv[0]).isdigit():
            return Reply(BLOCKED, "Usage: `!setrole <days> <role name>`")
        role_name = " ".join(str(a) for a in argv[1:])
        result = await engine.run(
            WorkflowRef("role.set_threshold"),
            _ctx_from_req(req, {
                "days_required": int(argv[0]),
                "role_name": role_name,
                # the shipped write carries display_name=role_name
                # (services/role_automation.py set_time_threshold —
                # goldens/role/sweep_setrole pins the column)
                "display_name": role_name}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not set the tier.")
        after = _leg_after(result, "set_threshold")
        # the shipped ack verbatim (role_cog.py:534 / sweep_setrole golden)
        return Reply(SUCCESS,
                     f"✅ Role **{after.get('role_name')}** will be "
                     f"assigned after **{after.get('days_required')}** "
                     "day(s).")

    @handler("role.unsetrole")
    async def unsetrole(req) -> Reply:
        """!unsetrole <role name>."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        from sb.domain.role import store

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!unsetrole <role name>`")
        role_name = " ".join(str(a) for a in argv)
        # the shipped normalized-match-or-fallback (role_cog.unsetrole:
        # `match = next((r["role_name"] ... == key), role_name)` — the
        # DELETE runs on the matched-or-raw name and the ack is
        # UNCONDITIONAL; goldens/role/sweep_unsetrole pins the success
        # byte over an absent row. The band-5 "No such tier was
        # configured." miss copy was a port invention — retired at the
        # re-home (oracle-wins).
        key = role_name.strip().lower()
        thresholds = await store.get_thresholds(int(req.guild_id or 0))
        match = next(
            (r["role_name"] for r in thresholds
             if str(r["role_name"] or "").strip().lower() == key),
            role_name)
        result = await engine.run(
            WorkflowRef("role.remove_threshold"),
            _ctx_from_req(req, {"role_name": str(match)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not remove the tier.")
        # the shipped ack verbatim (role_cog.py:565 / sweep_unsetrole)
        return Reply(SUCCESS,
                     f"✅ Removed **{match}** from time-based assignment.")

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
        if member_id is None or role_id is None:
            return Reply(BLOCKED,
                         "Usage: `!temprole @member <duration> <@role>` — "
                         "duration like `2h`, `30m`, `1d`.")
        seconds = _parse_duration(str(argv[1]))
        if seconds is None:
            # the shipped invalid-duration byte (role_grants_cog.py /
            # goldens/role/sweep_temprole — member/role converted, THEN
            # parse_duration guards)
            return Reply(BLOCKED,
                         "❌ Invalid duration — try `30m`, `2h`, or `7d` "
                         "(max 1 year).")
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
        """!temproles [@member] — active grants, soonest first. The
        `whose` prefix is the shipped branch verbatim (role_grants_cog:
        `"You have" if is_self else f"**{target.display_name}** has"`;
        goldens/role/sweep_temproles pins the self-view empty byte)."""
        from sb.domain.role import service

        argv = tuple(req.args.get("argv", ()) or ())
        actor_id = int(getattr(req.actor, "user_id", 0) or 0)
        member_id = _int_token(argv) or actor_id
        is_self = member_id == actor_id
        whose = "You have"
        if not is_self:
            display = f"<@{member_id}>"
            try:
                from sb.domain.utility.service import guild_directory

                info = await guild_directory().member_info(
                    int(req.guild_id or 0), member_id)
                display = str(info.tag).rsplit("#", 1)[0]
            except Exception:  # noqa: BLE001 — headless ⇒ mention fallback
                pass
            whose = f"**{display}** has"
        grants = await service.list_active_grants(
            int(req.guild_id or 0), member_id)
        if not grants:
            # the shipped empty copy verbatim (role_grants_cog.py)
            return Reply(SUCCESS, f"📭 {whose} no active temp roles.")
        lines = [f"• <@&{rid}> — until {exp.strftime('%Y-%m-%d %H:%M UTC')}"
                 for rid, exp in grants]
        return Reply(SUCCESS, f"⏳ **Temporary roles for <@{member_id}>**\n"
                     + "\n".join(lines))


def _register_guild_surfaces() -> None:
    """The re-homed guild-view/effect commands (the `_unmapped`→role
    sweep re-home): assignroles/debugroles/createrole/deleterole/roleinfo
    run over the guild-view + provisioning ports; refreshmembers carries
    its capture artifact. Registered at MODULE IMPORT (#111 doctrine)."""
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("role.assignroles")):
        return

    @handler("role.assignroles")
    async def assignroles(req) -> Reply:
        """!assignroles — role_cog.assign_roles_cmd verbatim: the progress
        line, the reconciliation, the summary
        (goldens/role/sweep_assignroles pins both sends)."""
        from sb.domain.role import service
        from sb.kernel.interaction.egress import (
            OutboundContent,
            TrustLevel,
            active_channel_emitter,
        )

        gid = int(req.guild_id or 0)
        guild = await service.guild_view(gid)
        if guild is None:
            return Reply(BLOCKED,
                         "⏱️ The role check needs the live guild view "
                         "(arms with the live adapter).")
        emitter = active_channel_emitter()
        await emitter.send(
            int(req.channel_id or 0),
            OutboundContent(body="🔄 Running role assignment…",
                            trust=TrustLevel.SYSTEM),
            guild_id=gid)
        result = await service.run_role_check(gid)
        return Reply(SUCCESS, service.format_role_check_result(result))

    @handler("role.debugroles")
    async def debugroles(req) -> Reply:
        """!debugroles — the shipped cached-role dump verbatim
        (role_cog: `Roles: {', '.join(r.name for r in guild.roles)}`;
        goldens/role/sweep_debugroles pins the byte)."""
        from sb.domain.role import service

        guild = await service.guild_view(int(req.guild_id or 0))
        if guild is None:
            return Reply(BLOCKED,
                         "🔧 Live role diagnostics need the gateway cache "
                         "(arms with the live adapter).")
        names = [str(getattr(r, "name", "")) for r in
                 (getattr(guild, "roles", ()) or ())]
        return Reply(SUCCESS, f"Roles: {', '.join(names)}")

    @handler("role.refreshmembers")
    async def refreshmembers(req) -> Reply:
        """!refreshmembers — CAPTURE-ENVIRONMENT ARTIFACT, reproduced
        deliberately (trap 11b, the xp `!rank test` precedent): the
        shipped body is `await ctx.guild.chunk()` + a ✅ ack, but the
        capture world had no real gateway so the chunk RAISED and every
        captured `!refreshmembers` died in bot1.py's generic
        on_command_error — goldens/role/sweep_refreshmembers pins that
        envelope, and no golden reaches the ✅ branch. The live
        member-chunk seam is a successor (arms with the live adapter);
        until it does, the handler answers the golden-pinned literal
        rather than faking a refresh."""
        del req
        return Reply(BLOCKED,
                     "⚠️ An unexpected error occurred. Please try again.")

    @handler("role.createrole")
    async def createrole(req) -> Reply:
        """!createrole <name> [color] — the shipped create lane through
        the role-provisioning port (fake_http captured guild.create_role
        as the `create_role` wire verb; goldens/role/sweep_createrole
        pins the call + the ✅ ack)."""
        from sb.domain.role import service

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!createrole <name> [color]`")
        name = str(argv[0])
        color = 0
        if len(argv) > 1:
            token = str(argv[1]).lstrip("#")
            try:
                color = int(token, 16)
            except ValueError:
                color = 0
        gid = int(req.guild_id or 0)
        try:
            rid = await service.active_provisioning().create_guild_role(
                gid, name=name, color=color, reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not create role: {exc}")
        # the shipped RoleLifecycleService companions verbatim — ONE
        # mutation_id shared by the best-effort audit event and the
        # advisory lifecycle event (services/role_lifecycle_service.py;
        # goldens/role/sweep_createrole pins both payloads).
        import uuid

        mutation_id = str(uuid.uuid4())
        actor_id = int(getattr(req.actor, "user_id", 0) or 0)
        await service.emit_role_audit(
            gid, mutation_id=mutation_id, mutation_type="role_create",
            target=f"role:{rid}", new_value=f"create role '{name}'",
            actor_id=actor_id, actor_type="admin")
        await service.emit_role_lifecycle(
            gid, mutation_id=mutation_id, operation="create",
            outcome="success", applied=[rid], failed=[])
        # the shipped ack verbatim (role_cog.createrole)
        return Reply(SUCCESS, f"✅ Created role **{name}**.")

    @handler("role.deleterole")
    async def deleterole(req) -> Reply:
        """!deleterole <role> — the shipped delete lane: the feasibility
        guard speaks first (goldens/role/sweep_deleterole pins the
        ABOVE_BOT refusal through role_cog's
        `❌ Could not delete **{name}**: {first_error}` byte)."""
        from sb.domain.role import service
        from sb.domain.role.feasibility import evaluate_role

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!deleterole <role>`")
        guild = await service.guild_view(int(req.guild_id or 0))
        if guild is None:
            return Reply(BLOCKED,
                         "📝 Role deletion needs the live guild view "
                         "(arms with the live adapter).")
        role = service.find_role(guild, " ".join(str(a) for a in argv))
        if role is None:
            return Reply(BLOCKED, "❌ Role not found.")
        verdict = evaluate_role(role, bot_member=getattr(guild, "me", None))
        name = str(getattr(role, "name", ""))
        if not verdict.ok:
            # the shipped refusal shape verbatim (role_cog.deleterole)
            return Reply(BLOCKED,
                         f"❌ Could not delete **{name}**: {verdict.reason}")
        gid = int(req.guild_id or 0)
        rid = int(getattr(role, "id", 0) or 0)
        try:
            await service.active_provisioning().delete_role(
                gid, rid, reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not delete **{name}**: {exc}")
        import uuid

        mutation_id = str(uuid.uuid4())
        await service.emit_role_audit(
            gid, mutation_id=mutation_id, mutation_type="role_delete",
            target=f"role:{rid}", new_value=f"delete role '{name}'",
            actor_id=int(getattr(req.actor, "user_id", 0) or 0),
            actor_type="admin")
        await service.emit_role_lifecycle(
            gid, mutation_id=mutation_id, operation="delete",
            outcome="success", applied=[rid], failed=[])
        # the shipped ack verbatim (role_cog.deleterole)
        return Reply(SUCCESS, f"🗑️ Deleted role **{name}**.")

    @handler("role.roleinfo")
    async def roleinfo(req) -> None | Reply:
        """!roleinfo <role> — resolve the cached role, open the read-only
        info card (views/roles/role_info.build_role_info_embed;
        goldens/role/sweep_roleinfo pins the embed)."""
        import dataclasses

        from sb.domain.role import service
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!roleinfo <role>`")
        guild = await service.guild_view(int(req.guild_id or 0))
        if guild is None:
            return Reply(BLOCKED,
                         "ℹ️ Role info needs the live guild view "
                         "(arms with the live adapter).")
        role = service.find_role(guild, " ".join(str(a) for a in argv))
        if role is None:
            return Reply(BLOCKED, "❌ Role not found.")
        await open_panel(
            PanelRef("role.info_card"),
            dataclasses.replace(req, args={
                **dict(req.args),
                "roleinfo_role_id": int(getattr(role, "id", 0) or 0)}))
        return None


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
    if value > 365 * 86400:      # shipped MAX_DURATION_SECONDS (1 year)
        return None
    return value if value > 0 else None


def _register_pending() -> None:
    """The four polite pending terminals. Registered at MODULE IMPORT
    (declaring IS reserving) — the live root imports and dispatches without
    ever running the manifest ENSURE_REFS hooks when zero plugins are
    admitted, so an ensure-only registration left `!roleinfo`/`!createrole`/
    `!assignroles`/`!debugroles` and the role:create click dying in
    RefUnresolved BUG envelopes live (band-5 live-drive ledger, bug 1)."""
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


def ensure_handler_refs() -> None:
    _register()
    _register_guild_surfaces()
    _register_task_fire()
    _register_pending()


_register()
_register_guild_surfaces()
_register_task_fire()
_register_pending()
