"""`from_exception` — the ONE dispatch error envelope (frozen L0 spec 02
§3.3). The classifier core reads ONLY the exception type; `surface`/`target`
enrich nothing but `user_message` (PIN-4 — a headless MAINTENANCE fire
passes `target=None` and discards the copy). The wizard's
`recovery_context_from_exception` is retired: `surface=SETUP` +
`section_label` render the same envelope.

discord/commands exception types are matched by GUARDED import when discord
is installed, and by (module, class-name) fallback otherwise — the module
must stay importable in discord-less containers.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sb.spec.outcomes import BLOCKED, DISCORD_FAILED, DenialReason, ErrorClass

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.interaction.request import Surface, TargetRef

logger = logging.getLogger("sb.kernel.interaction")

__all__ = ["ErrorEnvelope", "ValidatorError", "from_exception"]


class ValidatorError(ValueError):
    """The step-2b argument-validation failure (a `user_error` row input).
    Carries the offending parameter name for the usage hint."""

    def __init__(self, param: str, message: str = ""):
        super().__init__(message or f"invalid argument: {param}")
        self.param = param


@dataclass(frozen=True)
class ErrorEnvelope:
    error_class: ErrorClass
    reason: DenialReason
    retryable: bool
    user_message: str
    log_level: int              # WARNING for user_error/denied/transient; ERROR for bug
    outcome: str                # the §2.7 constant this class maps to


_USER_ERROR_NAMES = frozenset({
    "MissingRequiredArgument", "BadArgument", "TransformerError",
    "BadUnionArgument", "BadLiteralArgument",
})
_DENIED_NAMES = frozenset({"CheckFailure", "MissingPermissions", "NotOwner"})
_TRANSIENT_NAMES = frozenset({"HTTPException", "RateLimited", "DiscordServerError"})


def _name_chain(exc: BaseException) -> set[str]:
    return {t.__name__ for t in type(exc).__mro__}


def _classify(exc: BaseException) -> tuple[ErrorClass, DenialReason, bool, str]:
    """(error_class, reason, retryable, outcome) — surface/target-independent."""
    names = _name_chain(exc)
    if isinstance(exc, ValidatorError) or names & _USER_ERROR_NAMES:
        return ErrorClass.USER_ERROR, DenialReason.USER_ERROR, True, BLOCKED
    if "Forbidden" in names:
        # the bot lacks a Discord permission — OUR operational gap, not the
        # actor's authority (reason=DISPATCH_ERROR, not AUTHORITY)
        return ErrorClass.DENIED, DenialReason.DISPATCH_ERROR, False, BLOCKED
    if isinstance(exc, PermissionError) or names & _DENIED_NAMES:
        return ErrorClass.DENIED, DenialReason.AUTHORITY, False, BLOCKED
    if isinstance(exc, (ConnectionError, asyncio.TimeoutError, TimeoutError)) \
            or names & _TRANSIENT_NAMES:
        return ErrorClass.TRANSIENT, DenialReason.DISPATCH_ERROR, True, DISCORD_FAILED
    return ErrorClass.BUG, DenialReason.DISPATCH_ERROR, False, BLOCKED


def _user_message(exc: BaseException, error_class: ErrorClass, *,
                  target: "TargetRef | None", section_label: str | None) -> str:
    if error_class is ErrorClass.USER_ERROR:
        param = getattr(exc, "param", None)
        name = getattr(param, "name", param) or "?"
        cmd = target.key if target is not None else "?"
        message = f"Missing/invalid argument: `{name}`. `!help {cmd}` for usage."
    elif error_class is ErrorClass.DENIED:
        if "Forbidden" in _name_chain(exc):
            perm = getattr(exc, "missing_permission", None) or "?"
            message = f"I'm missing a Discord permission for this: `{perm}`."
        else:
            message = (getattr(exc, "denial_message", None)
                       or "You don't have permission to use this.")
    elif error_class is ErrorClass.TRANSIENT:
        message = "Discord/the service is busy — try again shortly."
    else:
        message = "Something went wrong on our end — it's been logged."
    if section_label:
        # the wizard fold-in: section label + the recommended action
        message = f"[{section_label}] {message} You can Retry or Skip this step."
    return message


def from_exception(exc: BaseException, *, surface: "Surface",
                   target: "TargetRef | None",
                   section_label: str | None = None) -> ErrorEnvelope:
    """The frozen exception→class→reason→outcome table (02 §3.3).
    `CommandOnCooldown` is NOT an input (cooldown is caught at step 3)."""
    error_class, reason, retryable, outcome = _classify(exc)
    if target is None:
        # headless (MAINTENANCE) — the class's canonical copy verbatim
        message = _user_message(exc, error_class, target=None, section_label=None)
    else:
        message = _user_message(exc, error_class, target=target,
                                section_label=section_label)
    if error_class is ErrorClass.BUG:
        log_level = logging.ERROR
        logger.error("unhandled dispatch exception (surface=%s target=%s)",
                     getattr(surface, "value", surface),
                     target.key if target is not None else None, exc_info=exc)
        try:
            from sb.kernel.observability.findings import record_operator_finding
            record_operator_finding(
                source="interaction.dispatch", severity="error",
                summary=f"unhandled {type(exc).__name__}: {exc}",
                detail=f"surface={getattr(surface, 'value', surface)}",
                correlation_id=None)
        except Exception:  # noqa: BLE001 — findings never block the envelope
            pass
    else:
        log_level = logging.WARNING
        logger.warning("dispatch %s (%s): %s", error_class.value, reason.value, exc)
    return ErrorEnvelope(
        error_class=error_class, reason=reason, retryable=retryable,
        user_message=message, log_level=log_level, outcome=outcome,
    )
