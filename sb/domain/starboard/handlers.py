"""Starboard command handlers (the `_unmapped` starboard-family re-home;
NEW subsystem birth) — the shipped cogs/starboard_cog.py `!starboard`
config group at oracle byte parity (see sb/domain/starboard/service.py
for the under-port boundary: the reaction-listener pipeline stays)."""

from __future__ import annotations

import re

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]

#: shipped copy, verbatim (cogs/starboard_cog.py) — each pinned by its
#: golden (goldens/starboard/sweep_starboard / _ignore / _off /
#: _selfstar / _unignore).
_STATUS_OFF = ("⭐ Starboard is off. Turn it on with "
               "`!starboard #channel [threshold]` "
               "(e.g. `!starboard #hall-of-fame 5`).")
_ACK_OFF = "✅ Starboard disabled. Re-enable with `!starboard #channel`."
_ACK_SELF_ON = "✅ Self-stars **count** toward the threshold."
_ACK_SELF_OFF = ("✅ Self-stars are **ignored** (the author's own ⭐ "
                 "doesn't count).")

#: bot1.py's global on_command_error fallback, verbatim — the capture
#: world's answer whenever a converter raised (TextChannel converter on a
#: non-channel token, MissingRequiredArgument on `!starboard selfstar` /
#: `ignore` / `unignore`, BadArgument on a non-int threshold).
#: Handler-owned literal (the goldens/xp/sweep_rank precedent); UNPINNED
#: for the starboard family (no golden drives the converter-failure
#: lanes) but carried so the port degrades through the oracle's own
#: copy, never the new kernel's error envelope.
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."

#: the shipped `selfstar` truthy vocabulary, verbatim
#: (cogs/starboard_cog.py starboard_selfstar) — everything else is OFF
#: (goldens/starboard/sweep_starboard_selfstar drove "test" → False).
_TRUTHY = frozenset({"on", "yes", "true", "1", "enable", "enabled"})

#: channel mention/id parse (the btd6/ai channel-arg shape) — the shipped
#: lanes took a discord.TextChannel converter arg.
_CHANNEL = re.compile(r"^<#(\d{15,20})>$|^(\d{15,20})$")


def _argv(req) -> tuple[str, ...]:
    return tuple(str(t) for t in (req.args.get("argv", ()) or ()))


def _parse_channel_arg(token: str) -> int | None:
    """A channel id from `<#id>`/bare digits; None when unparseable — the
    caller answers the capture world's converter-failure copy
    (``_GENERIC_ERROR``)."""
    m = _CHANNEL.match(token.strip())
    if m is None:
        return None
    return int(m.group(1) or m.group(2))


async def _run_op(req, op_key: str, params: dict):
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    ctx = ctx_from_request(req, params)
    result = await engine.run(WorkflowRef(op_key), ctx)
    return result, ctx


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("starboard.root")):
        return

    @handler("starboard.root")
    async def starboard_root(req) -> Reply:
        """`!starboard [#channel] [threshold]` — the shipped root group
        body (invoke_without_command): bare shows the current config
        (goldens/starboard/sweep_starboard pins the off-state byte);
        argful runs the audited configure upsert (threshold default 3,
        clamped >= 1 in the op leg — the write-bearing invocation exists
        in no imported golden, D-0069)."""
        from sb.domain.starboard import service

        argv = _argv(req)
        gid = int(req.guild_id or 0)
        if not argv:
            settings = await service.get_settings(gid)
            if settings and settings["enabled"]:
                # the shipped configured status line — the oracle resolved
                # the channel and fell back to the raw id in backticks;
                # the port renders the mention form (unpinned degradation
                # corner, the panels.py posture).
                where = f"<#{int(settings['channel_id'])}>"
                return Reply(SUCCESS, (
                    f"⭐ Starboard: {settings['emoji']} ≥ "
                    f"**{settings['threshold']}** → {where}. "
                    f"Set with `!starboard #channel [threshold]`, "
                    f"turn off with `!starboard off`."))
            return Reply(SUCCESS, _STATUS_OFF)

        channel_id = _parse_channel_arg(argv[0])
        if channel_id is None:
            # the shipped TextChannel converter raised → bot1.py generic.
            return Reply(BLOCKED, _GENERIC_ERROR)
        try:
            threshold = int(argv[1]) if len(argv) > 1 else 3
        except ValueError:
            return Reply(BLOCKED, _GENERIC_ERROR)
        result, ctx = await _run_op(req, "starboard.configure",
                                    {"channel_id": channel_id,
                                     "threshold": threshold,
                                     "emoji": "⭐"})
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        stored = int(ctx.params.get("_stored_threshold", threshold))
        # shipped ack verbatim (cogs/starboard_cog.py starboard_group).
        return Reply(SUCCESS,
                     f"✅ Starboard set: ⭐ **{stored}**+ stars → "
                     f"<#{channel_id}>.")

    @handler("starboard.off")
    async def starboard_off(req) -> Reply:
        """`!starboard off` — the shipped disable lane: the pure-UPDATE
        flip (a no-op over an unconfigured guild) + the unconditional
        audit + the unconditional ack (goldens/starboard/
        sweep_starboard_off pins the bytes over an empty table)."""
        result, _ = await _run_op(req, "starboard.disable", {})
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        return Reply(SUCCESS, _ACK_OFF)

    @handler("starboard.selfstar")
    async def starboard_selfstar(req) -> Reply:
        """`!starboard selfstar on|off` — the shipped truthy-set parse
        (anything else is OFF: goldens/starboard/sweep_starboard_selfstar
        drove "test" → self_star=False), the audited pure-UPDATE, the
        state-keyed ack. A missing value died in the capture world's
        MissingRequiredArgument → bot1.py generic copy."""
        argv = _argv(req)
        if not argv:
            return Reply(BLOCKED, _GENERIC_ERROR)
        on = argv[0].strip().lower() in _TRUTHY
        result, _ = await _run_op(req, "starboard.set_self_star",
                                  {"self_star": on})
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        return Reply(SUCCESS, _ACK_SELF_ON if on else _ACK_SELF_OFF)

    async def _ignore(req, *, add: bool) -> Reply:
        """The shipped ignore/unignore pair: parse the channel arg
        (TextChannel converter in the cog — a failure died in bot1.py's
        generic handler), run the audited K7 op, ack with the shipped
        copy. The unignore ack is UNCONDITIONAL (bare DELETE, no-op if
        absent — the #193 oracle-wins class; sweep_starboard_unignore
        pins the success copy over an empty table)."""
        argv = _argv(req)
        channel_id = _parse_channel_arg(argv[0]) if argv else None
        if channel_id is None:
            return Reply(BLOCKED, _GENERIC_ERROR)
        op = "starboard.ignore_add" if add else "starboard.ignore_remove"
        result, _ = await _run_op(req, op, {"channel_id": channel_id})
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        if add:
            # shipped ack verbatim — sweep_starboard_ignore pins the byte
            # (channel.mention → the normalizer's <#…> form).
            return Reply(SUCCESS, f"✅ Ignoring <#{channel_id}> — its "
                                  f"messages won't be starred.")
        return Reply(SUCCESS, f"✅ No longer ignoring <#{channel_id}>.")

    @handler("starboard.ignore")
    async def starboard_ignore(req) -> Reply:
        """`!starboard ignore #channel`."""
        return await _ignore(req, add=True)

    @handler("starboard.unignore")
    async def starboard_unignore(req) -> Reply:
        """`!starboard unignore #channel`."""
        return await _ignore(req, add=False)


_register()


def ensure_handler_refs() -> None:
    """Re-arm after a sanctioned clear_ref_table (#141 doctrine)."""
    _register()
