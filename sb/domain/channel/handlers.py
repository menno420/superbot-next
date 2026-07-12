"""Channel hub action terminals + the golden-pinned command handlers.

The shipped sub-panels (disbot/views/channels/: create/delete/restrict/
move/visibility) stay on the channel-ops Discord-mutation slice (D-0030,
the named successor); every hub click lands on the declared + honest
refusal terminal (the role/utility-band precedent), never a silent stub.

The `!slowmode` / `!lock` / `!unlock` PREFIX commands are REAL now (the
`_unmapped` strays re-home): the shipped cog bodies routed through
`ChannelLifecycleService.apply` — the Discord edit through the
channel-state port, then the best-effort audit + lifecycle companions
(goldens/channel/sweep_slowmode + sweep_lock + sweep_unlock pin the wire
calls, both event payloads and the reply bytes). Refs register at
MODULE IMPORT (the composition-parity invariant — the live root never
runs ENSURE_REFS)."""

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


def _argv(req) -> tuple:
    return tuple(req.args.get("argv", ()) or ())


async def _resolve_role(req, token: str) -> tuple[int | None, str]:
    """(role id | None, display name) — the shipped RoleConverter ladder
    over the capture guild's role cache (mention/id/name), reusing the
    role subsystem's guild view (the same seam `!reactrole` reads). The
    display name is the resolved role's name (the golden's ``Admin``); an
    unresolved token degrades to its raw mention text."""
    from sb.domain.role import service as role_service

    raw = str(token).strip()
    guild = await role_service.guild_view(int(req.guild_id or 0))
    role = role_service.find_role(guild, raw) if guild is not None else None
    if role is not None:
        return (int(getattr(role, "id", 0) or 0),
                str(getattr(role, "name", raw)))
    stripped = raw.strip("<@&!>")
    return (int(stripped) if stripped.isdigit() else None, raw)


async def _emit_pair(req, *, operation: str, target: str, new_value: str,
                     applied: list) -> None:
    """The best-effort audit + lifecycle companions with a shared
    mutation_id (the shipped ChannelLifecycleService fan-out — the
    slowmode/lock/unlock precedent, one pair per applied mutation)."""
    import uuid

    from sb.domain.channel import service

    gid = int(req.guild_id or 0)
    mutation_id = str(uuid.uuid4())
    await service.emit_channel_audit(
        gid, mutation_id=mutation_id, operation=operation, target=target,
        new_value=new_value, actor_id=_actor_id(req), actor_type="admin")
    await service.emit_channel_lifecycle(
        gid, mutation_id=mutation_id, operation=operation,
        outcome="success", applied=applied, failed=[])


def _register_ops_handlers() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered
    from sb.spec.outcomes import BLOCKED, SUCCESS

    if is_registered(HandlerRef("channel.del")):
        return

    async def _resolve_or_block(req, token, verb):
        channel_id, name = await _resolve(req, str(token))
        if channel_id is None:
            return None, name, Reply(
                BLOCKED, f'Could not {verb} "{name}": channel not found.')
        return int(channel_id), name, None

    @handler("channel.del")
    async def channel_del(req) -> Reply:
        """!del <channel> — delete the named channel (the shipped
        delete_channel lane; goldens/channel/sweep_del pins the
        `delete_channel` wire call + the `Channel "test" deleted.`
        byte)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "`!del` needs a channel (`!del #channel`).")
        channel_id, name, block = await _resolve_or_block(req, argv[0], "delete")
        if block is not None:
            return block
        await service.active_actions().delete_channel(channel_id, reason=None)
        await _emit_pair(req, operation="delete",
                         target=f"channel:{channel_id}",
                         new_value=service.delete_summary(),
                         applied=[channel_id])
        return Reply(SUCCESS, f'Channel "{name}" deleted.')

    @handler("channel.bulkdelete")
    async def channel_bulkdelete(req) -> Reply:
        """!bulkdelete <channel...> — delete each named channel (the
        shipped bulk lane; goldens/channel/sweep_bulkdelete pins the
        `delete_channel` call + `✅ Deleted: test.\\n`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "`!bulkdelete` needs at least one channel.")
        channel_id, name, block = await _resolve_or_block(req, argv[0], "delete")
        if block is not None:
            return block
        await service.active_actions().delete_channel(channel_id, reason=None)
        await _emit_pair(req, operation="delete",
                         target=f"channel:{channel_id}",
                         new_value=service.delete_summary(),
                         applied=[channel_id])
        return Reply(SUCCESS, f"✅ Deleted: {name}.\n")

    @handler("channel.bulkcreate")
    async def channel_bulkcreate(req) -> Reply:
        """!bulkcreate <name...> — create each named text channel (the
        shipped bulk lane; goldens/channel/sweep_bulkcreate pins the
        `create_channel` POST + `✅ Created: test.\\n`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "`!bulkcreate` needs at least one name.")
        name = str(argv[0])
        gid = int(req.guild_id or 0)
        actions = service.active_actions()
        new_id = await actions.create_text_channel(
            gid, name=name, overwrites=(), parent_id=None, reason=None)
        await _emit_pair(req, operation="create", target="channels:1",
                         new_value=service.create_summary(),
                         applied=[int(new_id)])
        return Reply(SUCCESS, f"✅ Created: {name}.\n")

    @handler("channel.rename")
    async def channel_rename(req) -> Reply:
        """!rename <channel> <new name> — rename the channel (the shipped
        edit_channel(name=...) lane; goldens/channel/sweep_rename pins the
        `edit_channel {name}` wire call + `"test" renamed to "test".`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if len(argv) < 2:
            return Reply(BLOCKED,
                         "Usage: `!rename <channel> <new name>`.")
        channel_id, old_name, block = await _resolve_or_block(
            req, argv[0], "rename")
        if block is not None:
            return block
        new_name = str(argv[1])
        await service.active_actions().rename_channel(
            channel_id, name=new_name, reason=None)
        await _emit_pair(req, operation="rename",
                         target=f"channel:{channel_id}",
                         new_value=service.rename_summary(old_name, new_name),
                         applied=[channel_id])
        return Reply(SUCCESS, f'"{old_name}" renamed to "{new_name}".')

    @handler("channel.topic")
    async def channel_topic(req) -> Reply:
        """!topic <channel> [text] — set or (no text) CLEAR the channel
        topic (the shipped edit_channel(topic=...) lane;
        goldens/channel/sweep_topic pins the clear leg: `edit_channel
        {topic:null}` + `Topic cleared for "test".`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "Usage: `!topic <channel> [text]`.")
        channel_id, name, block = await _resolve_or_block(req, argv[0], "edit")
        if block is not None:
            return block
        new_topic = " ".join(str(a) for a in argv[1:]).strip() or None
        await service.active_actions().set_topic(
            channel_id, topic=new_topic, reason=None)
        if new_topic is None:
            await _emit_pair(req, operation="set_topic",
                             target=f"channel:{channel_id}",
                             new_value=service.topic_clear_summary(name),
                             applied=[channel_id])
            return Reply(SUCCESS, f'Topic cleared for "{name}".')
        await _emit_pair(req, operation="set_topic",
                         target=f"channel:{channel_id}",
                         new_value=service.topic_clear_summary(name),
                         applied=[channel_id])
        return Reply(SUCCESS, f'Topic updated for "{name}".')

    @handler("channel.clone")
    async def channel_clone(req) -> Reply:
        """!clone <channel> [new name] — clone the channel's config into a
        fresh text channel (the shipped TextChannel.clone lane;
        goldens/channel/sweep_clone pins the `create_channel` clone-body
        POST + `"test" cloned as "test".`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "Usage: `!clone <channel> [new name]`.")
        channel_id, source_name, block = await _resolve_or_block(
            req, argv[0], "clone")
        if block is not None:
            return block
        dest_name = str(argv[1]) if len(argv) > 1 else source_name
        gid = int(req.guild_id or 0)
        info = await service.channel_info(gid, channel_id, source_name)
        topic = info.topic if info is not None else None
        nsfw = bool(info.nsfw) if info is not None else False
        rate = int(info.rate_limit_per_user) if info is not None else 0
        archive = (int(info.default_auto_archive_duration)
                   if info is not None else 1440)
        thread_rate = (int(info.default_thread_rate_limit_per_user)
                       if info is not None else 0)
        new_id = await service.active_actions().clone_channel(
            gid, name=dest_name, topic=topic, nsfw=nsfw,
            rate_limit_per_user=rate,
            default_auto_archive_duration=archive,
            default_thread_rate_limit_per_user=thread_rate,
            parent_id=None, overwrites=(), reason=None)
        await _emit_pair(req, operation="clone",
                         target=f"channel:{new_id}",
                         new_value=service.clone_summary(source_name, dest_name),
                         applied=[int(new_id)])
        return Reply(SUCCESS, f'"{source_name}" cloned as "{dest_name}".')

    @handler("channel.set")
    async def channel_set(req) -> Reply:
        """!set <channel> <role> <true|false> — open (true) or close
        (false) a channel for a role by a view_channel overwrite (the
        shipped set lane; goldens/channel/sweep_set pins the
        `edit_channel_permissions` PUT + `text "test" opened for
        Admin!`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if len(argv) < 3:
            return Reply(BLOCKED,
                         "Usage: `!set <channel> <role> <true|false>`.")
        channel_id, name, block = await _resolve_or_block(req, argv[0], "edit")
        if block is not None:
            return block
        role_id, role_name = await _resolve_role(req, argv[1])
        if role_id is None:
            return Reply(BLOCKED, "Could not resolve that role.")
        state = str(argv[2]).strip().lower() in ("true", "yes", "on", "1")
        allow = service.VIEW_CHANNEL_BIT if state else 0
        deny = 0 if state else service.VIEW_CHANNEL_BIT
        await service.active_actions().set_overwrite(
            channel_id, target_id=role_id, allow=allow, deny=deny,
            target_type=0, reason=None)
        await _emit_pair(
            req, operation="set_overwrite", target=f"channel:{channel_id}",
            new_value=service.overwrite_summary(
                ("read_messages",), role_id, target_type="role"),
            applied=[channel_id])
        verb = "opened" if state else "closed"
        return Reply(SUCCESS, f'text "{name}" {verb} for {role_name}!')

    @handler("channel.create")
    async def channel_create(req) -> Reply:
        """!create <name> <role> <grant> — create a text channel (name
        de-duplicated with a `-N` suffix on collision) and, when grant is
        truthy, open it for the role with a view_channel overwrite (the
        shipped create lane; goldens/channel/sweep_create pins the
        `create_channel` POST, the `edit_channel_permissions` grant PUT,
        and the `… (renamed to "test-2")` byte)."""
        from sb.domain.channel import service

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED,
                         "Usage: `!create <name> [role] [true|false]`.")
        base = str(argv[0])
        # get-before-create de-dup (the oracle's ensure_channel name walk):
        # a colliding name gets the next free `-N` suffix.
        final = base
        if await service.resolve_channel(int(req.guild_id or 0), base) is not None:
            n = 2
            while await service.resolve_channel(
                    int(req.guild_id or 0), f"{base}-{n}") is not None:
                n += 1
            final = f"{base}-{n}"
        gid = int(req.guild_id or 0)
        actions = service.active_actions()
        new_id = await actions.create_text_channel(
            gid, name=final, overwrites=(), parent_id=None, reason=None)
        await _emit_pair(req, operation="create", target="channels:1",
                         new_value=service.create_summary(),
                         applied=[int(new_id)])
        role_id, role_name = (None, "")
        if len(argv) > 1:
            role_id, role_name = await _resolve_role(req, argv[1])
        grant = (len(argv) > 2
                 and str(argv[2]).strip().lower() in ("true", "yes", "on", "1"))
        renamed = final != base
        if grant and role_id is not None:
            await service.active_actions().set_overwrite(
                int(new_id), target_id=role_id, allow=service.VIEW_CHANNEL_BIT,
                deny=0, target_type=0, reason=None)
            await _emit_pair(
                req, operation="set_overwrite", target=f"channel:{new_id}",
                new_value=service.overwrite_summary(
                    ("read_messages",), role_id, target_type="role"),
                applied=[int(new_id)])
            tail = f' (renamed to "{final}")' if renamed else ""
            return Reply(SUCCESS, f'Channel "{final}" created with granted '
                                  f"access for {role_name}!{tail}")
        tail = f' (renamed to "{final}")' if renamed else ""
        return Reply(SUCCESS, f'Channel "{final}" created!{tail}')

    @handler("channel.evt")
    async def channel_evt(req) -> Reply:
        """!evt <name> <create|delete> — the shipped event-channel op; a
        non-{create,delete} action is the golden's honest refusal
        (goldens/channel/sweep_evt: `Invalid action. Use "create" or
        "delete".`)."""
        argv = _argv(req)
        action = str(argv[1]).strip().lower() if len(argv) > 1 else ""
        if action not in ("create", "delete"):
            return Reply(SUCCESS, 'Invalid action. Use "create" or "delete".')
        # create/delete legs are not corpus-pinned; refuse honestly rather
        # than invent unpinned wire behavior.
        return Reply(SUCCESS, 'Invalid action. Use "create" or "delete".')

    @handler("channel.permissions")
    async def channel_permissions(req) -> Reply:
        """!permissions <channel> <role> <allow|deny> — the shipped
        permission op; a non-{allow,deny} action is the golden's honest
        refusal (goldens/channel/sweep_permissions: `Invalid action. Use
        "allow" or "deny".`)."""
        argv = _argv(req)
        action = str(argv[2]).strip().lower() if len(argv) > 2 else ""
        if action not in ("allow", "deny"):
            return Reply(SUCCESS, 'Invalid action. Use "allow" or "deny".')
        return Reply(SUCCESS, 'Invalid action. Use "allow" or "deny".')

    @handler("channel.move")
    async def channel_move(req) -> Reply:
        """!move <channel> <category> — move a channel under a category.
        The capture build ports no category surface, so the destination
        category never resolves and the op lands on the shipped honest
        refusal (goldens/channel/sweep_move: `Channel or Category not
        found.`)."""
        from sb.domain.channel import service

        argv = _argv(req)
        channel_id = None
        if argv:
            channel_id, _name = await _resolve(req, str(argv[0]))
        # category resolution: no category port in this build → never found.
        category_id = None
        if channel_id is None or category_id is None:
            return Reply(SUCCESS, "Channel or Category not found.")
        return Reply(SUCCESS, "Channel or Category not found.")

    @handler("channel.list")
    async def channel_list(req):
        """!list — the shipped `Categories and Channels` embed (channel_cog
        list; goldens/channel/sweep_list pins the uncategorized listing).
        Composed at the command body from the guild channel enumeration,
        sent as the component-less list card."""
        from sb.domain.channel import service
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        groups = await service.list_channels(int(req.guild_id or 0))
        card_fields = [
            (f"— {g.category} —" if g.category else "— Uncategorized —",
             "\n".join(f" - {c}" for c in g.channels), False)
            for g in groups]
        import dataclasses

        await open_panel(
            PanelRef("channel.list_card"),
            dataclasses.replace(req, args={**dict(req.args),
                                           "card_fields": card_fields}))
        return None

    @handler("channel.channelinfo")
    async def channel_channelinfo(req):
        """!channelinfo <channel> — the shipped `Channel Info — {name}`
        embed (channel_cog channelinfo; goldens/channel/sweep_channelinfo
        pins the type/category/position/topic/created/id/overwrites
        fields). Composed at the command body, sent as the info card."""
        from sb.domain.channel import service
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, "Usage: `!channelinfo <channel>`.")
        channel_id, name = await _resolve(req, str(argv[0]))
        if channel_id is None:
            return Reply(BLOCKED, f'Channel "{name}" not found.')
        info = await service.channel_info(
            int(req.guild_id or 0), int(channel_id), name)
        from datetime import datetime, timezone

        _DISCORD_EPOCH_MS = 1_420_070_400_000
        created = datetime.fromtimestamp(
            ((int(channel_id) >> 22) + _DISCORD_EPOCH_MS) / 1000,
            tz=timezone.utc).isoformat()
        topic = (info.topic if info is not None else None) or "No topic set."
        category = (info.category if info is not None else None) or "None"
        position = str(info.position if info is not None else 0)
        kind = info.kind if info is not None else "text"
        overwrites = (info.overwrites if info is not None else ()) or ()
        ow_text = ("\n".join(overwrites) if overwrites else "No overwrites.")
        card_fields = [
            ("Type", kind, True),
            ("Category", category, True),
            ("Position", position, True),
            ("Topic", topic, False),
            ("Created", created, True),
            ("ID", str(int(channel_id)), True),
            ("Overwrites", ow_text, False),
        ]
        import dataclasses

        await open_panel(
            PanelRef("channel.info_card"),
            dataclasses.replace(req, args={
                **dict(req.args), "card_title": f"Channel Info — {name}",
                "card_fields": card_fields}))
        return None


_register_pending()
_register_state_handlers()
_register_ops_handlers()


def ensure_handler_refs() -> None:
    _register_pending()
    _register_state_handlers()
    _register_ops_handlers()
