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


_register_pending()
_register_state_handlers()


def ensure_handler_refs() -> None:
    _register_pending()
    _register_state_handlers()
