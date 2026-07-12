"""Channel hub action terminals + the golden-pinned command handlers.

The shipped sub-panels (disbot/views/channels/: create/delete/restrict/
move/visibility) stay on their honest refusal terminals (the
role/utility-band precedent) — interactive picker ports are their own
follow-up; every hub click lands on the declared pending terminal,
never a silent stub.

The PREFIX command surface is REAL (the D-0030 channel-ops batch): the
shipped cog bodies (cogs/channel_cog.py) routed through
`ChannelLifecycleService.apply` — the Discord edit(s) through the
channel-state port, then the best-effort audit + lifecycle companions
with a shared mutation_id per operation (goldens/channel/sweep_slowmode
+ sweep_lock + sweep_unlock pinned the first three; the wave-9 re-home
adds sweep_bulkcreate/bulkdelete/channelinfo/clone/create/del/evt/list/
move/permissions/rename/set/topic — wire calls, both event payloads and
every reply byte). Gateway-cache reads (channel roster/metadata, role
names) ride the ChannelDirectory port; an uninstalled port is the
caller's honest BLOCKED refusal (the moderation-actions posture). Refs
register at MODULE IMPORT (the composition-parity invariant — the live
root never runs ENSURE_REFS)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with the channel-ops slice (D-0030)."

#: Discord's slowmode ceiling, verbatim (channel_lifecycle_service
#: MAX_SLOWMODE_SECONDS — 6 h).
_MAX_SLOWMODE_SECONDS = 21600


def _register_pending() -> None:
    from sb.domain.operator_spine import pending_handler

    pending_handler("channel.create_pending",
                    f"➕ The interactive channel creator{_PENDING}")
    pending_handler("channel.delete_pending",
                    f"🗑️ The channel delete picker{_PENDING}")
    pending_handler("channel.restrict_pending",
                    f"🔒 The lock/unlock restriction panel{_PENDING}")
    pending_handler("channel.move_pending",
                    f"↔️ The move/reorder panel{_PENDING}")
    pending_handler("channel.visibility_pending",
                    f"🔍 The subsystem-visibility panel{_PENDING}")


async def _resolve(req, token: str) -> tuple[int | None, str]:
    """(channel id | None, display name) — the converter ladder; the
    display name is the golden's quoted token for the name leg (the
    capture guild's `test`; the mention/id legs have no cached name in a
    headless root and degrade to the raw token)."""
    from sb.domain.channel import service

    channel_id = await service.resolve_channel(int(req.guild_id or 0), token)
    name = str(token).strip().lstrip("<#").rstrip(">")
    return channel_id, name


def _actor_id(req) -> int:
    return int(getattr(req.actor, "user_id", 0) or 0)


async def _apply_overwrite(req, *, argv: tuple, allow: int, deny: int,
                           past: str, verb: str) -> Reply:
    """The shipped lock/unlock shared helper: ONE send_messages
    overwrite for @everyone (the guild's default role — its id IS the
    guild id) on the named channel, then the audit + lifecycle
    companions with a shared mutation_id
    (cogs/channel_cog.py `success=f'"{name}" locked.'` /
    `'"{name}" unlocked.'`; goldens/channel/sweep_lock + sweep_unlock
    pin every byte)."""
    import uuid

    from sb.domain.channel import service
    from sb.kernel.interaction.errors import ValidatorError
    from sb.spec.outcomes import BLOCKED, SUCCESS

    if not argv:
        raise ValidatorError("channel", f"`!{verb}` needs a channel "
                                        f"(`!{verb} #channel`)")
    channel_id, name = await _resolve(req, str(argv[0]))
    if channel_id is None:
        # the shipped converter's not-found path died in bot1.py's
        # envelope; headless roots refuse honestly (unpinned branch).
        return Reply(BLOCKED, f'Could not {verb} "{name}": channel not found.')
    gid = int(req.guild_id or 0)
    try:
        await service.active_actions().set_overwrite(
            int(channel_id), target_id=gid, allow=allow, deny=deny,
            target_type=0, reason=None)
    except RuntimeError as exc:
        # port not armed (live root until D-0049-family wiring) — the
        # moderation-actions posture: honest refusal, no events.
        return Reply(BLOCKED, f'Could not {verb} "{name}": {exc}')
    mutation_id = str(uuid.uuid4())
    await service.emit_channel_audit(
        gid, mutation_id=mutation_id, operation="set_overwrite",
        target=f"channel:{channel_id}",
        new_value=service.overwrite_summary(("send_messages",), gid),
        actor_id=_actor_id(req), actor_type="admin")
    await service.emit_channel_lifecycle(
        gid, mutation_id=mutation_id, operation="set_overwrite",
        outcome="success", applied=[int(channel_id)], failed=[])
    return Reply(SUCCESS, f'"{name}" {past}.')


def _register_state_handlers() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered
    from sb.spec.outcomes import BLOCKED, SUCCESS

    if is_registered(HandlerRef("channel.slowmode")):
        return

    @handler("channel.slowmode")
    async def slowmode(req) -> Reply:
        """!slowmode <channel> <seconds> (alias !slow) — the shipped
        set_slowmode lane: the channel-edit PATCH, then the audit +
        lifecycle companions (goldens/channel/sweep_slowmode pins the
        `edit_channel {rate_limit_per_user}` wire call, both payloads
        and the `Slowmode set to **3s** in "test".` byte)."""
        import uuid

        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2 or not str(argv[1]).lstrip("-").isdigit():
            raise ValidatorError(
                "seconds", "slowmode needs a channel and a duration in "
                           "seconds (`!slowmode #channel <seconds>`)")
        seconds = int(str(argv[1]))
        if seconds < 0:
            raise ValidatorError("seconds",
                                 "slowmode seconds must be 0 or more")
        if seconds > _MAX_SLOWMODE_SECONDS:
            return Reply(BLOCKED,
                         f"Slowmode can be at most "
                         f"{_MAX_SLOWMODE_SECONDS}s (6 hours).")
        channel_id, name = await _resolve(req, str(argv[0]))
        if channel_id is None:
            return Reply(BLOCKED, f'❌ Could not set slowmode in "{name}": '
                                  f"channel not found.")
        gid = int(req.guild_id or 0)
        try:
            await service.active_actions().set_slowmode(
                int(channel_id), seconds=seconds, reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not set slowmode in "{name}": {exc}')
        mutation_id = str(uuid.uuid4())
        await service.emit_channel_audit(
            gid, mutation_id=mutation_id, operation="set_slowmode",
            target=f"channel:{channel_id}",
            new_value=service.slowmode_summary(seconds, name),
            actor_id=_actor_id(req), actor_type="admin")
        await service.emit_channel_lifecycle(
            gid, mutation_id=mutation_id, operation="set_slowmode",
            outcome="success", applied=[int(channel_id)], failed=[])
        if seconds == 0:
            # shipped disable copy, verbatim (cogs/channel_cog.py)
            return Reply(SUCCESS, f'Slowmode disabled in "{name}".')
        return Reply(SUCCESS, f'Slowmode set to **{seconds}s** in "{name}".')

    @handler("channel.lock")
    async def lock(req) -> Reply:
        """!lock <channel> — deny send_messages for @everyone (the
        shipped restriction pair's lock half)."""
        from sb.domain.channel.service import SEND_MESSAGES_BIT

        argv = tuple(req.args.get("argv", ()) or ())
        return await _apply_overwrite(
            req, argv=argv, allow=0, deny=SEND_MESSAGES_BIT,
            past="locked", verb="lock")

    @handler("channel.unlock")
    async def unlock(req) -> Reply:
        """!unlock <channel> — restore send_messages for @everyone (the
        shipped restriction pair's unlock half)."""
        from sb.domain.channel.service import SEND_MESSAGES_BIT

        argv = tuple(req.args.get("argv", ()) or ())
        return await _apply_overwrite(
            req, argv=argv, allow=SEND_MESSAGES_BIT, deny=0,
            past="unlocked", verb="unlock")


# --- the channel-ops batch (D-0030 successor slice) --------------------------------
#
# Shared shapes for the 13 re-homed command lanes. Every mutation follows
# the shipped ChannelLifecycleService sequencing: the Discord effect(s)
# through the channel-state port FIRST, then ONE audit + ONE lifecycle
# companion per operation with a shared mutation_id. No DB legs anywhere
# (the oracle's channel ops were pure Discord state + events — the #207
# posture; no compensator question arises).


async def _snapshot_for(req, token: str):
    """Resolve a command channel token to its gateway-cache snapshot
    (the converter ladder over the channel-state name port, then the
    directory read). None ⇒ not found."""
    from sb.domain.channel import service

    channel_id = await service.resolve_channel(int(req.guild_id or 0),
                                               str(token))
    if channel_id is None:
        return None
    return await service.active_directory().get_channel(
        int(req.guild_id or 0), int(channel_id))


async def _resolve_role(req, token: str) -> tuple[int, str] | None:
    """The shipped RoleConverter ladder: mention → id → exact name
    (goldens drive only the mention leg — sweep_create/sweep_set's
    `<@&…>`)."""
    from sb.domain.channel import service

    token = str(token).strip()
    role_id: int | None = None
    if token.startswith("<@&") and token.endswith(">") and \
            token[3:-1].isdigit():
        role_id = int(token[3:-1])
    elif token.isdigit():
        role_id = int(token)
    roles = await service.active_directory().list_roles(
        int(req.guild_id or 0))
    if role_id is not None:
        for rid, name in roles:
            if rid == role_id:
                return rid, name
        return None
    for rid, name in roles:
        if name == token:
            return rid, name
    return None


async def _find_category(req, token: str):
    """The shipped ``_resolve_category`` (name/id match over the guild's
    category channels). The capture guild carried NO categories, so no
    golden drives the found branch."""
    from sb.domain.channel import service

    token = str(token).strip()
    for snap in await service.active_directory().list_channels(
            int(req.guild_id or 0)):
        if snap.kind != "category":
            continue
        if snap.name == token or str(snap.channel_id) == token:
            return snap
    return None


def _to_bool(token: str) -> bool | None:
    """discord.py's ``_convert_to_bool`` vocabulary (the shipped
    ``permission: bool`` converter)."""
    lowered = str(token).lower()
    if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
        return True
    if lowered in ("no", "n", "false", "f", "0", "disable", "off"):
        return False
    return None


async def _taken_names(req) -> set[str]:
    from sb.domain.channel import service

    return {snap.name for snap in
            await service.active_directory().list_channels(
                int(req.guild_id or 0))}


async def _emit_op(req, *, operation: str, target: str, new_value: str,
                   applied: list, failed: list | None = None,
                   outcome: str = "success") -> None:
    """One shipped lifecycle operation's companions: the best-effort
    audit fact + the advisory lifecycle event, shared mutation_id (the
    goldens pin both payloads per op — always outcome `success` with an
    empty failed list; the partial branch is reconstruction, unpinned)."""
    import uuid

    from sb.domain.channel import service

    gid = int(req.guild_id or 0)
    mutation_id = str(uuid.uuid4())
    await service.emit_channel_audit(
        gid, mutation_id=mutation_id, operation=operation, target=target,
        new_value=new_value, actor_id=_actor_id(req), actor_type="admin")
    await service.emit_channel_lifecycle(
        gid, mutation_id=mutation_id, operation=operation,
        outcome=outcome, applied=applied, failed=list(failed or []))


async def _open_card(req, panel_id: str, params: dict) -> None:
    """Open a zero-component info card (the utility #255 param-card
    lane) — params ride into the renderer as open params."""
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef(panel_id),
                     dataclasses.replace(
                         req, args={**dict(req.args), **params}))


def _overwrites_block(snap) -> str:
    """The shipped overwrite formatter (channel_cog: ``**{name}**\\n
    Allowed: …\\nDenied: …`` blocks, else ``No overwrites.``). The
    pinned case is empty; the non-empty branch degrades to target
    ids + raw bitmasks (the shipped display names/permission-key lists
    need gateway objects this port deliberately does not carry)."""
    formatted = ""
    for ow in snap.overwrites:
        who = f"{'role' if ow.target_type == 0 else 'member'} {ow.target_id}"
        formatted += (f"**{who}**\nAllowed: {ow.allow or 'None'}\n"
                      f"Denied: {ow.deny or 'None'}\n\n")
    return formatted or "No overwrites."


def _register_ops_handlers() -> None:  # noqa: PLR0915 — 13 shipped command bodies
    from sb.spec.refs import HandlerRef, handler, is_registered
    from sb.spec.outcomes import BLOCKED, SUCCESS

    if is_registered(HandlerRef("channel.bulkcreate")):
        return

    @handler("channel.bulkcreate")
    async def bulkcreate(req) -> Reply:
        """!bulkcreate <ch1> [ch2...] [category] — the shipped bulk
        create lane (goldens/channel/sweep_bulkcreate pins the
        create_channel POST, the create audit/lifecycle pair and the
        `✅ Created: test.\\n` byte)."""
        from sb.domain.channel import service

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            # shipped guard copy, verbatim (cogs/channel_cog.py)
            return Reply(BLOCKED, "Please provide at least one channel name.")
        try:
            names = list(argv)
            category = None
            if len(names) > 1:
                # the shipped trailing-category convention: a last arg
                # naming an existing category peels off (no golden
                # drives it — the capture guild had no categories).
                category = await _find_category(req, names[-1])
                if category is not None:
                    names = names[:-1]
            taken = await _taken_names(req)
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not create channels: {exc}")
        gid = int(req.guild_id or 0)
        actions = service.active_actions()
        created: list[str] = []
        applied: list[int] = []
        failed: list[str] = []
        for raw in names:
            safe = service.collision_safe_name(str(raw), taken)
            taken.add(safe)
            try:
                cid = await actions.create_text_channel(
                    gid, name=safe, overwrites=(),
                    parent_id=(category.channel_id if category else None),
                    reason=None)
            except RuntimeError as exc:
                if not created:
                    # nothing landed yet — the unarmed-port refusal, no
                    # events (the moderation-actions posture).
                    return Reply(BLOCKED,
                                 f"❌ Could not create channels: {exc}")
                # partial success stays RECORDED (the shipped service
                # collected per-step results and emitted ONE companion
                # pair carrying applied+failed — a created channel never
                # goes unaudited).
                failed.append(safe)
                continue
            created.append(safe)
            applied.append(int(cid))
        await _emit_op(
            req, operation="create", target=f"channels:{len(names)}",
            new_value=service.create_summary(
                len(names), category=(category.name if category else None),
                applied=len(created), total=len(names)),
            applied=applied, failed=failed,
            outcome=("success" if not failed else "partial"))
        # shipped response builder, verbatim (created/failed blocks).
        response = ""
        if created:
            response += f"✅ Created: {', '.join(created)}.\n"
        if failed:
            response += f"❌ Failed: {', '.join(failed)}."
        return Reply(SUCCESS, response)

    @handler("channel.bulkdelete")
    async def bulkdelete(req) -> Reply:
        """!bulkdelete <name|keyword> [more names...] — the shipped bulk
        delete lane: one arg tries the exact resolve first, then the
        keyword-contains scan (goldens/channel/sweep_bulkdelete pins the
        delete_channel call, the delete audit/lifecycle pair and the
        `✅ Deleted: test.\\n` byte)."""
        from sb.domain.channel import service

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            # unpinned guard (the shipped copy is unreconstructed) — the
            # bulkcreate wording, mirrored.
            return Reply(BLOCKED, "Please provide at least one channel name.")
        try:
            if len(argv) == 1:
                word = str(argv[0])
                exact = await _snapshot_for(req, word)
                if exact is not None:
                    targets = [exact]
                else:
                    targets = [
                        snap for snap in
                        await service.active_directory().list_channels(
                            int(req.guild_id or 0))
                        if word in snap.name and snap.kind != "category"]
                    if not targets:
                        # shipped copy, verbatim (cogs/channel_cog.py)
                        return Reply(
                            BLOCKED,
                            f"No channels found matching '{word}'.")
            else:
                targets = []
                for raw in argv:
                    snap = await _snapshot_for(req, str(raw))
                    if snap is not None:
                        targets.append(snap)
                if not targets:
                    return Reply(
                        BLOCKED,
                        f"No channels found matching '{argv[0]}'.")
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not delete channels: {exc}")
        actions = service.active_actions()
        deleted: list[str] = []
        applied: list[int] = []
        for snap in targets:
            try:
                await actions.delete_channel(int(snap.channel_id),
                                             reason=None)
            except RuntimeError as exc:
                return Reply(BLOCKED, f"❌ Could not delete channels: {exc}")
            deleted.append(snap.name)
            applied.append(int(snap.channel_id))
        target = (f"channel:{applied[0]}" if len(applied) == 1
                  else f"channels:{len(applied)}")
        await _emit_op(
            req, operation="delete", target=target,
            new_value=service.delete_summary(
                len(targets), applied=len(deleted), total=len(targets)),
            applied=applied)
        return Reply(SUCCESS, f"✅ Deleted: {', '.join(deleted)}.\n")

    @handler("channel.channelinfo")
    async def channelinfo(req) -> Reply | None:
        """!channelinfo <name|id> — the shipped read-only detail embed
        (WARNING_COLOR yellow; goldens/channel/sweep_channelinfo pins
        every field byte)."""
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            raise ValidatorError(
                "channel", "channelinfo needs a channel "
                           "(`!channelinfo #channel`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not read channel info: {exc}")
        if snap is None:
            # unpinned branch (the shipped copy is unreconstructed).
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        created = (snap.created_at.strftime("%Y-%m-%d %H:%M:%S")
                   if snap.created_at else "?")
        await _open_card(req, "channel.info_card", {
            "card_title": f"Channel Info — {snap.name}",
            "card_fields": (
                ("Type", snap.kind, True),
                ("Category", snap.category or "None", True),
                ("Position", str(snap.position), True),
                ("Topic", snap.topic or "No topic set.", False),
                ("Created", created, True),
                ("ID", str(snap.channel_id), True),
                ("Overwrites", _overwrites_block(snap), False),
            )})
        return None

    @handler("channel.clone")
    async def clone(req) -> Reply:
        """!clone <source> <new_name> — the shipped `channel.clone()`
        lane: the create POST re-sends the source's full option set
        (goldens/channel/sweep_clone pins the payload, the clone
        audit/lifecycle pair and the `"test" cloned as "test".` byte —
        NO collision rename on the clone path, unlike !create)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            raise ValidatorError(
                "channel", "clone needs a source channel and a new name "
                           "(`!clone #channel <new_name>`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED, f'❌ Could not clone "{argv[0]}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        new_name = str(argv[1])
        try:
            cid = await service.active_actions().clone_channel(
                int(req.guild_id or 0), name=new_name, source=snap,
                reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not clone "{snap.name}": {exc}')
        await _emit_op(
            req, operation="clone", target=f"channel:{int(cid)}",
            new_value=service.clone_summary(snap.name, new_name),
            applied=[int(cid)])
        return Reply(SUCCESS, f'"{snap.name}" cloned as "{new_name}".')

    @handler("channel.create")
    async def create(req) -> Reply:
        """!create <name> <@role> <True/False> [category] — the shipped
        create-with-role-access lane: the collision-safe create, then
        the read_messages overwrite for the role — two operations, two
        audit/lifecycle pairs (goldens/channel/sweep_create pins both
        wire calls, all four event payloads and the
        `Channel "test-2" created with granted access for Admin!
        (renamed to "test-2")` byte)."""
        from sb.domain.channel import service
        from sb.domain.channel.service import READ_MESSAGES_BIT
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            raise ValidatorError(
                "channel", "create needs a name, a role and True/False "
                           "(`!create <name> <@role> <True/False>`)")
        channel_name = str(argv[0])
        try:
            role = await _resolve_role(req, str(argv[1]))
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not create "{channel_name}": {exc}')
        if role is None:
            # unpinned branch (the shipped RoleConverter died in the
            # bot1.py envelope; headless roots refuse honestly).
            return Reply(BLOCKED, f'Role "{argv[1]}" not found.')
        role_id, role_name = role
        permission = _to_bool(str(argv[2]))
        if permission is None:
            raise ValidatorError(
                "permission", "create needs True/False for role access "
                              "(`!create <name> <@role> <True/False>`)")
        gid = int(req.guild_id or 0)
        try:
            category = None
            if len(argv) > 3:
                category = await _find_category(req, str(argv[3]))
                if category is None:
                    # the shipped optional category slot refuses on a
                    # miss (a converter/guard death, never a silent
                    # guild-root create); copy unpinned — the module's
                    # not-found convention.
                    return Reply(BLOCKED,
                                 f'Category "{argv[3]}" not found.')
            taken = await _taken_names(req)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not create "{channel_name}": {exc}')
        safe_name = service.collision_safe_name(channel_name, taken)
        actions = service.active_actions()
        try:
            cid = await actions.create_text_channel(
                gid, name=safe_name, overwrites=(),
                parent_id=(category.channel_id if category else None),
                reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not create "{channel_name}": {exc}')
        await _emit_op(
            req, operation="create", target="channels:1",
            new_value=service.create_summary(
                1, category=(category.name if category else None)),
            applied=[int(cid)])
        allow = READ_MESSAGES_BIT if permission else 0
        deny = 0 if permission else READ_MESSAGES_BIT
        state = "granted" if permission else "restricted"
        suffix = (f' (renamed to "{safe_name}")'
                  if safe_name != channel_name else "")
        try:
            await actions.set_overwrite(
                int(cid), target_id=role_id, allow=allow, deny=deny,
                target_type=0, reason=None)
        except RuntimeError as exc:
            # shipped fail label (create landed, access setup failed).
            return Reply(BLOCKED,
                         f'Channel "{safe_name}" created, but access '
                         f'setup failed: {exc}')
        await _emit_op(
            req, operation="set_overwrite", target=f"channel:{int(cid)}",
            new_value=service.overwrite_summary(("read_messages",),
                                                role_id),
            applied=[int(cid)])
        return Reply(SUCCESS,
                     f'Channel "{safe_name}" created with {state} access '
                     f"for {role_name}!{suffix}")

    @handler("channel.del")
    async def del_channel(req) -> Reply:
        """!del <name|id> — the shipped single delete lane
        (goldens/channel/sweep_del pins the delete_channel call, the
        delete audit/lifecycle pair and the `Channel "test" deleted.`
        byte)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            raise ValidatorError(
                "channel", "del needs a channel (`!del #channel`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED, f'❌ Could not delete "{argv[0]}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        try:
            await service.active_actions().delete_channel(
                int(snap.channel_id), reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not delete "{snap.name}": {exc}')
        await _emit_op(
            req, operation="delete",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.delete_summary(1),
            applied=[int(snap.channel_id)])
        return Reply(SUCCESS, f'Channel "{snap.name}" deleted.')

    @handler("channel.evt")
    async def evt(req) -> Reply:
        """!evt <name|id> <create/delete> — the shipped event-channel
        lane (goldens/channel/sweep_evt pins the invalid-action guard
        byte; the valid branches ride the same create/delete legs)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            raise ValidatorError(
                "action", "evt needs a channel and an action "
                          "(`!evt <name|id> <create/delete>`)")
        name_token = str(argv[0])
        action = str(argv[1])
        if action not in ("create", "delete"):
            # shipped guard copy, verbatim (cogs/channel_cog.py)
            return Reply(BLOCKED, 'Invalid action. Use "create" or "delete".')
        gid = int(req.guild_id or 0)
        actions = service.active_actions()
        if action == "create":
            try:
                taken = await _taken_names(req)
            except RuntimeError as exc:
                return Reply(BLOCKED,
                             f'❌ Could not create "{name_token}": {exc}')
            safe = service.collision_safe_name(name_token, taken)
            try:
                cid = await actions.create_text_channel(
                    gid, name=safe, overwrites=(), parent_id=None,
                    reason=None)
            except RuntimeError as exc:
                return Reply(BLOCKED,
                             f'❌ Could not create "{name_token}": {exc}')
            await _emit_op(
                req, operation="create", target="channels:1",
                new_value=service.create_summary(1), applied=[int(cid)])
            # shipped success copy, verbatim (cogs/channel_cog.py)
            return Reply(SUCCESS, f'Event channel "{safe}" created!')
        try:
            snap = await _snapshot_for(req, name_token)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not delete "{name_token}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{name_token}" not found.')
        try:
            await actions.delete_channel(int(snap.channel_id), reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not delete "{snap.name}": {exc}')
        await _emit_op(
            req, operation="delete",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.delete_summary(1),
            applied=[int(snap.channel_id)])
        # unpinned branch (the shipped copy is unreconstructed) — the
        # create branch's wording, mirrored.
        return Reply(SUCCESS, f'Event channel "{snap.name}" deleted!')

    @handler("channel.list")
    async def list_channels(req) -> Reply | None:
        """!list — the shipped categories+channels embed
        (channel_cog.list_channels over views/channels/list_panel.py:
        one field per category, the `— Uncategorized —` bucket LAST,
        ` - {name}` lines; goldens/channel/sweep_list pins the single
        uncategorized field over the capture roster)."""
        from sb.domain.channel import service

        try:
            snaps = await service.active_directory().list_channels(
                int(req.guild_id or 0))
        except RuntimeError as exc:
            return Reply(BLOCKED, f"❌ Could not list channels: {exc}")
        if not snaps:
            # the shipped empty-state embed (channel_cog.list_channels).
            await _open_card(req, "channel.list_card", {
                "card_title": "Categories and Channels",
                "card_description": "No channels found."})
            return None
        fields = []
        for cat in (s for s in snaps if s.kind == "category"):
            # parent relation, never a name match (the shipped
            # by-category walk — duplicate category names stay distinct).
            lines = [f" - {s.name}" for s in snaps
                     if s.kind != "category"
                     and s.parent_id == cat.channel_id]
            fields.append((cat.name, "\n".join(lines) or "No channels",
                           False))
        uncat = [f" - {s.name}" for s in snaps
                 if s.kind != "category" and s.parent_id is None]
        if uncat:
            fields.append(("— Uncategorized —", "\n".join(uncat), False))
        await _open_card(req, "channel.list_card", {
            "card_title": "Categories and Channels",
            "card_fields": tuple(fields)})
        return None

    @handler("channel.move")
    async def move(req) -> Reply:
        """!move <channel> <category> — the shipped category move
        (goldens/channel/sweep_move pins the `Channel or Category not
        found.` guard byte — the capture guild had no categories)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            raise ValidatorError(
                "channel", "move needs a channel and a category "
                           "(`!move #channel <category>`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
            category = await _find_category(req, str(argv[1]))
        except RuntimeError as exc:
            return Reply(BLOCKED, f'❌ Could not move "{argv[0]}": {exc}')
        if not (snap and category):
            # shipped guard copy, verbatim (cogs/channel_cog.py)
            return Reply(BLOCKED, "Channel or Category not found.")
        try:
            await service.active_actions().move_channel(
                int(snap.channel_id),
                category_id=int(category.channel_id), reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED, f'❌ Could not move "{snap.name}": {exc}')
        await _emit_op(
            req, operation="move",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.move_summary(1, int(category.channel_id)),
            applied=[int(snap.channel_id)])
        # shipped success copy, verbatim (cogs/channel_cog.py)
        return Reply(SUCCESS,
                     f'"{snap.name}" moved to "{category.name}".')

    @handler("channel.permissions")
    async def permissions(req) -> Reply:
        """!permissions <name|id> <@role> <allow/deny> — the shipped
        send_messages overwrite lane (goldens/channel/sweep_permissions
        pins the `Invalid action. Use "allow" or "deny".` guard
        byte)."""
        from sb.domain.channel import service
        from sb.domain.channel.service import SEND_MESSAGES_BIT
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            raise ValidatorError(
                "action", "permissions needs a channel, a role and "
                          "allow/deny "
                          "(`!permissions <name|id> <@role> <allow/deny>`)")
        try:
            role = await _resolve_role(req, str(argv[1]))
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not update permissions in '
                         f'"{argv[0]}": {exc}')
        if role is None:
            return Reply(BLOCKED, f'Role "{argv[1]}" not found.')
        role_id, role_name = role
        act = str(argv[2])
        if act not in ("allow", "deny"):
            # shipped guard copy, verbatim (cogs/channel_cog.py)
            return Reply(BLOCKED, 'Invalid action. Use "allow" or "deny".')
        allow = act == "allow"
        word = "allowed" if allow else "denied"
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not update permissions in '
                         f'"{argv[0]}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        try:
            await service.active_actions().set_overwrite(
                int(snap.channel_id), target_id=role_id,
                allow=(SEND_MESSAGES_BIT if allow else 0),
                deny=(0 if allow else SEND_MESSAGES_BIT),
                target_type=0, reason=None)
        except RuntimeError as exc:
            # shipped fail label (cogs/channel_cog.py)
            return Reply(BLOCKED,
                         f'Could not update permissions in '
                         f'"{snap.name}": {exc}')
        await _emit_op(
            req, operation="set_overwrite",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.overwrite_summary(("send_messages",),
                                                role_id),
            applied=[int(snap.channel_id)])
        # shipped success copy, verbatim (cogs/channel_cog.py)
        return Reply(SUCCESS,
                     f'Send messages **{word}** for {role_name} in '
                     f'"{snap.name}".')

    @handler("channel.rename")
    async def rename(req) -> Reply:
        """!rename <old name|id> <new_name> — the shipped rename lane
        (goldens/channel/sweep_rename pins the edit_channel PATCH, the
        rename audit/lifecycle pair and the `"test" renamed to "test".`
        byte)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            raise ValidatorError(
                "channel", "rename needs a channel and a new name "
                           "(`!rename <old name|id> <new_name>`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED, f'❌ Could not rename "{argv[0]}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        new_name = str(argv[1])
        try:
            await service.active_actions().rename_channel(
                int(snap.channel_id), name=new_name, reason=None)
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not rename "{snap.name}": {exc}')
        await _emit_op(
            req, operation="rename",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.rename_summary(snap.name, new_name),
            applied=[int(snap.channel_id)])
        return Reply(SUCCESS, f'"{snap.name}" renamed to "{new_name}".')

    @handler("channel.set")
    async def set_access(req) -> Reply:
        """!set <name|id> <@role> <True/False> — the shipped
        category-or-channel read_messages access lane; a category fans
        out to its children (goldens/channel/sweep_set pins the
        edit_channel_permissions PUT, the set_overwrite audit/lifecycle
        pair and the `text "test" opened for Admin!` byte)."""
        from sb.domain.channel import service
        from sb.domain.channel.service import READ_MESSAGES_BIT
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 3:
            raise ValidatorError(
                "permission", "set needs a channel/category, a role and "
                              "True/False "
                              "(`!set <name|id> <@role> <True/False>`)")
        target_token = str(argv[0])
        try:
            role = await _resolve_role(req, str(argv[1]))
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not set access for '
                         f'"{target_token}": {exc}')
        if role is None:
            return Reply(BLOCKED, f'Role "{argv[1]}" not found.')
        role_id, role_name = role
        permission = _to_bool(str(argv[2]))
        if permission is None:
            raise ValidatorError(
                "permission", "set needs True/False for access "
                              "(`!set <name|id> <@role> <True/False>`)")
        try:
            # the shipped get_category_or_channel ladder: category FIRST.
            target = await _find_category(req, target_token)
            children = None
            if target is not None:
                # the shipped _overwrite_channel_ids fan-out is the
                # category object's OWN children (`tuple(ch.id for ch in
                # target.channels)` — parent relation, never a name
                # match; duplicate category names must not cross-hit).
                snaps = await service.active_directory().list_channels(
                    int(req.guild_id or 0))
                children = [s for s in snaps if s.kind != "category"
                            and s.parent_id == target.channel_id]
            else:
                target = await _snapshot_for(req, target_token)
                children = [target] if target is not None else None
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not set access for '
                         f'"{target_token}": {exc}')
        if target is None:
            # shipped guard copy, verbatim (cogs/channel_cog.py)
            return Reply(BLOCKED,
                         f'Channel or Category "{target_token}" not found.')
        state = "opened" if permission else "closed"
        allow = READ_MESSAGES_BIT if permission else 0
        deny = 0 if permission else READ_MESSAGES_BIT
        applied: list[int] = []
        for snap in children or []:
            try:
                await service.active_actions().set_overwrite(
                    int(snap.channel_id), target_id=role_id, allow=allow,
                    deny=deny, target_type=0, reason=None)
            except RuntimeError as exc:
                return Reply(BLOCKED,
                             f'❌ Could not set access for '
                             f'"{target.name}": {exc}')
            applied.append(int(snap.channel_id))
        target_ref = (f"channel:{applied[0]}" if len(applied) == 1
                      else f"channels:{len(applied)}")
        await _emit_op(
            req, operation="set_overwrite", target=target_ref,
            new_value=service.overwrite_summary(
                ("read_messages",), role_id, channels=len(applied),
                applied=len(applied), total=len(applied)),
            applied=applied)
        # shipped success copy, verbatim (cogs/channel_cog.py —
        # `{target_channel.type} "{name}" {state} for {role.name}!`).
        return Reply(SUCCESS,
                     f'{target.kind} "{target.name}" {state} for '
                     f"{role_name}!")

    @handler("channel.topic")
    async def topic(req) -> Reply:
        """!topic <name|id> [text...] — the shipped topic set/clear lane
        (goldens/channel/sweep_topic pins the `{"topic": null}` clear
        PATCH, the set_topic audit/lifecycle pair and the `Topic cleared
        for "test".` byte)."""
        from sb.domain.channel import service
        from sb.kernel.interaction.errors import ValidatorError

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            raise ValidatorError(
                "channel", "topic needs a channel "
                           "(`!topic #channel [text]`)")
        try:
            snap = await _snapshot_for(req, str(argv[0]))
        except RuntimeError as exc:
            return Reply(BLOCKED,
                         f'❌ Could not update topic for "{argv[0]}": {exc}')
        if snap is None:
            return Reply(BLOCKED, f'Channel "{argv[0]}" not found.')
        text = " ".join(str(a) for a in argv[1:])
        clear = not text.strip()
        try:
            await service.active_actions().set_topic(
                int(snap.channel_id),
                topic=(None if clear else text), reason=None)
        except RuntimeError as exc:
            # shipped fail label (cogs/channel_cog.py)
            return Reply(BLOCKED,
                         f'❌ Could not update topic for '
                         f'"{snap.name}": {exc}')
        await _emit_op(
            req, operation="set_topic",
            target=f"channel:{int(snap.channel_id)}",
            new_value=service.topic_summary(snap.name, clear=clear),
            applied=[int(snap.channel_id)])
        if clear:
            return Reply(SUCCESS, f'Topic cleared for "{snap.name}".')
        return Reply(SUCCESS, f'Topic updated for "{snap.name}".')


_register_pending()
_register_state_handlers()
_register_ops_handlers()


def ensure_handler_refs() -> None:
    _register_pending()
    _register_state_handlers()
    _register_ops_handlers()
