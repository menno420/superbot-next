"""Moderation policy + the guild-action port (band 2).

Policy resolution rides THE K7 settings seam (sb.kernel.settings.resolve)
against the manifest-declared moderation keys; the shipped defaults
(services/moderation_config.py) are carried verbatim as the declaration
defaults, so an unset guild resolves to shipped behavior.

The GUILD-ACTION PORT is the moderation twin of RC-21's ChannelEmitter:
kick/ban/timeout/unban are Discord state mutations, so the domain never
touches discord — the composition root installs the adapter implementation;
the not-installed default raises LOUDLY (an EFFECT leg failure classifies
as PARTIAL + operator finding, never a silent success).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from sb.kernel.interaction.handler_kit import Reply

__all__ = [
    "GuildModerationActions",
    "ModerationPolicy",
    "ReasonRequiredError",
    "active_actions",
    "install_moderation_actions",
    "load_policy",
    "parse_target_and_reason",
    "reset_moderation_ports_for_tests",
]

# shipped defaults, verbatim (services/moderation_config.py)
DEFAULT_REASON = "No reason provided"
WARN_ESCALATION_ACTIONS = ("timeout", "kick", "ban", "none")
PUBLIC_LOG_ACTIONS = ("none", "bans", "removals", "all")
POST_ACTION_CLEANUP_ACTIONS = ("none", "kick", "ban", "both")
DM_NOTIFY_ACTIONS = ("warn", "timeout", "kick", "ban")

_MENTION = re.compile(r"^<@!?(\d{15,20})>$")


class ReasonRequiredError(Exception):
    """require_reason is on and no reason was supplied — raised BEFORE any
    side effect (the shipped seam contract, verbatim semantics)."""

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"A reason is required to {action} a member.")


@dataclass(frozen=True)
class ModerationPolicy:
    warn_threshold: int = 3
    warn_timeout_minutes: int = 10
    warn_escalation_action: str = "timeout"
    dm_on_action: bool = False
    dm_actions: str = ",".join(DM_NOTIFY_ACTIONS)
    dm_template: str = ""
    require_reason: bool = False
    ban_delete_message_days: int = 0
    max_timeout_minutes: int = 40320
    post_action_cleanup: str = "none"
    post_action_cleanup_limit: int = 100
    public_log_actions: str = "none"


def _as_int(value: object, fallback: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def _as_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("1", "true", "yes", "on"):
        return True
    if token in ("0", "false", "no", "off"):
        return False
    return fallback


async def load_policy(guild_id: int) -> ModerationPolicy:
    from sb.kernel.settings import resolve

    d = ModerationPolicy()

    async def _get(name: str) -> object:
        return await resolve(guild_id, "moderation", name)

    return ModerationPolicy(
        warn_threshold=_as_int(await _get("warn_threshold"), d.warn_threshold),
        warn_timeout_minutes=_as_int(await _get("warn_timeout_minutes"),
                                     d.warn_timeout_minutes),
        warn_escalation_action=str(await _get("warn_escalation_action")
                                   or d.warn_escalation_action),
        dm_on_action=_as_bool(await _get("dm_on_action"), d.dm_on_action),
        dm_actions=str(await _get("dm_actions") or d.dm_actions),
        dm_template=str(await _get("dm_template") or ""),
        require_reason=_as_bool(await _get("require_reason"), d.require_reason),
        ban_delete_message_days=_as_int(await _get("ban_delete_message_days"),
                                        d.ban_delete_message_days),
        max_timeout_minutes=_as_int(await _get("max_timeout_minutes"),
                                    d.max_timeout_minutes),
        post_action_cleanup=str(await _get("post_action_cleanup")
                                or d.post_action_cleanup),
        post_action_cleanup_limit=_as_int(await _get("post_action_cleanup_limit"),
                                          d.post_action_cleanup_limit),
        public_log_actions=str(await _get("public_log_actions")
                               or d.public_log_actions),
    )


def resolve_reason(reason: str, policy: ModerationPolicy, *, action: str) -> str:
    """Shipped `_resolve_reason` semantics: require-or-default."""
    if not reason or not reason.strip():
        if policy.require_reason and action != "timeout":
            raise ReasonRequiredError(action)
        return DEFAULT_REASON
    return reason.strip()


def parse_target_and_reason(params: dict) -> tuple[int, str]:
    """Surface-normalized arg extraction: explicit target_id/reason params
    (slash/panel) or the prefix argv form (`<@id> free text reason`).
    Bare numeric ids are accepted too — the shipped `!unban <user_id>`
    contract (a banned user can never be mentioned).

    A missing/unparseable target raises ``ValidatorError`` so dispatch
    classifies it as a polite ``user_error`` denial (usage hint), never a
    BUG envelope (band-2 testing finding, 2026-07-09)."""
    from sb.kernel.interaction.errors import ValidatorError

    target = params.get("target_id") or params.get("member") or params.get("user")
    reason = str(params.get("reason", "") or "")
    if target is None:
        argv = tuple(params.get("argv", ()) or ())
        if argv:
            first = str(argv[0])
            match = _MENTION.match(first)
            if match:
                target = int(match.group(1))
                reason = " ".join(str(a) for a in argv[1:])
            elif first.isdigit():
                target = int(first)
                reason = " ".join(str(a) for a in argv[1:])
    if target is None:
        raise ValidatorError(
            "member", "no target member supplied (mention or user id)")
    return int(str(target).strip("<@!>")), reason


# --- the guild-action port ------------------------------------------------------

@runtime_checkable
class GuildModerationActions(Protocol):
    """Adapter-implemented Discord state mutations (kernel-defined port)."""

    async def timeout_member(self, guild_id: int, user_id: int, *,
                             minutes: int, reason: str) -> None: ...
    async def kick_member(self, guild_id: int, user_id: int, *,
                          reason: str) -> None: ...
    async def ban_member(self, guild_id: int, user_id: int, *, reason: str,
                         delete_message_days: int) -> None: ...
    async def unban_member(self, guild_id: int, user_id: int, *,
                           reason: str) -> None: ...
    async def dm_member(self, user_id: int, text: str) -> None: ...


class _NoActions:
    async def _refuse(self, *_a, **_k) -> None:
        raise RuntimeError(
            "GuildModerationActions not installed — the composition root "
            "must install the discord adapter's implementation "
            "(sb/domain/moderation/service.install_moderation_actions)")

    timeout_member = kick_member = ban_member = _refuse
    unban_member = dm_member = _refuse


_actions: GuildModerationActions = _NoActions()  # type: ignore[assignment]


def install_moderation_actions(actions: GuildModerationActions) -> None:
    global _actions
    _actions = actions


def active_actions() -> GuildModerationActions:
    return _actions


def reset_moderation_ports_for_tests() -> None:
    global _actions
    _actions = _NoActions()  # type: ignore[assignment]


# --- read handlers (HandlerRef routes) --------------------------------------------


def _register_handlers() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered
    from sb.spec.outcomes import SUCCESS

    if is_registered(HandlerRef("moderation.modlogs_view")):
        return

    @handler("moderation.modlogs_view")
    async def modlogs_view(req) -> Reply:
        from sb.domain.moderation.store import get_mod_logs
        from sb.domain.moderation.service import parse_target_and_reason

        try:
            target_id, _ = parse_target_and_reason(dict(req.args))
        except ValueError:
            target_id = int(getattr(req.actor, "user_id", 0) or 0)
        rows = await get_mod_logs(target_id, int(req.guild_id or 0), limit=10)
        if not rows:
            return Reply(SUCCESS, f"No moderation history for <@{target_id}>.")
        lines = [f"• {r['action']} — {r['reason']} (by <@{r['moderator_id']}>)"
                 for r in rows]
        return Reply(SUCCESS, f"Moderation history for <@{target_id}>:\n"
                              + "\n".join(lines))

    @handler("moderation.warnings_view")
    async def warnings_view(req) -> Reply:
        from sb.domain.moderation.store import get_warnings
        from sb.domain.moderation.service import parse_target_and_reason

        try:
            target_id, _ = parse_target_and_reason(dict(req.args))
        except ValueError:
            target_id = int(getattr(req.actor, "user_id", 0) or 0)
        count = await get_warnings(target_id, int(req.guild_id or 0))
        return Reply(SUCCESS, f"<@{target_id}> has {count} warning(s).")


_register_handlers()


def ensure_handler_refs() -> None:
    _register_handlers()
