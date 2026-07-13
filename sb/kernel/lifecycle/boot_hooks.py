"""The app-boot hook registry (the ORDER-019 on-ready seam).

The oracle ran per-domain restart recovery in cog ``on_ready`` listeners
(``disbot/cogs/setup_cog.py``: ``_resume_launchers()`` +
``revive_essential_flows(bot)`` — the restart-revive sweep). This
architecture has no cogs and NO kernel→domain import edge, so the boot
work inverts: domains REGISTER a hook here (through their manifest — the
declaring-IS-reserving import), and the composition root FIRES the
registry once the process reaches RUNNING (gateway up, ports installed,
DB live). The kernel owns only the registry + firing discipline; it
never names a domain.

Contract:

* ``register_boot_hook(name, hook, order=...)`` — idempotent per name
  (a manifest ``ENSURE_REFS`` re-run re-registers; the LAST callable
  wins, the registration slot keeps its original position so firing
  order stays stable across re-imports).
* ``run_boot_hooks()`` — fires every hook ONCE, in ``(order,
  registration sequence)`` order, each isolated exactly like the
  oracle's per-guild ``try/except`` (one failing domain never blocks
  another's recovery); returns the per-hook results and NEVER raises.
* Hooks take no arguments: boot work reads its own state through the
  domain's ports/stores (the oracle iterated ``bot.guilds`` because its
  state lived in gateway objects; here the durable rows already know).
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass

__all__ = [
    "BootHookResult",
    "register_boot_hook",
    "registered_boot_hooks",
    "reset_boot_hooks_for_tests",
    "run_boot_hooks",
]

logger = logging.getLogger("sb.kernel.lifecycle.boot_hooks")

#: default registration order — hooks with a smaller ``order`` fire first;
#: ties fire in registration sequence.
DEFAULT_ORDER = 100


@dataclass(frozen=True)
class BootHookResult:
    """One hook's firing outcome (``error`` is the repr of the exception
    the isolation lane swallowed; ``None`` on success)."""

    name: str
    ok: bool
    error: str | None = None


@dataclass
class _Registration:
    name: str
    hook: object          # async () -> object
    order: int
    seq: int


_hooks: dict[str, _Registration] = {}
_seq = 0


def register_boot_hook(name: str, hook, *, order: int = DEFAULT_ORDER) -> None:
    """Register (or re-register) the boot hook *name*.

    ``hook`` must be an async callable taking no arguments. Re-registering
    an existing name replaces the callable IN PLACE (same order slot, same
    sequence) — the manifest re-import / ``ENSURE_REFS`` idempotency
    posture (#141 doctrine twin). A non-coroutine callable is refused at
    registration time, not at boot (fail at declare, never at fire).
    """
    global _seq
    if not callable(hook) or not inspect.iscoroutinefunction(hook):
        raise TypeError(
            f"boot hook {name!r} must be an async callable "
            f"(got {type(hook).__name__})")
    existing = _hooks.get(name)
    if existing is not None:
        existing.hook = hook
        existing.order = int(order)
        return
    _hooks[name] = _Registration(name=name, hook=hook, order=int(order),
                                 seq=_seq)
    _seq += 1


def registered_boot_hooks() -> tuple[str, ...]:
    """The registered hook names, in firing order."""
    return tuple(reg.name for reg in _ordered())


def _ordered() -> list[_Registration]:
    return sorted(_hooks.values(), key=lambda reg: (reg.order, reg.seq))


async def run_boot_hooks() -> tuple[BootHookResult, ...]:
    """Fire every registered hook once, isolation per hook — a raising
    hook is logged + recorded and the next hook still fires (the oracle's
    per-guild ``on_ready`` posture, lifted to per-domain). Never raises."""
    results: list[BootHookResult] = []
    for reg in _ordered():
        try:
            await reg.hook()
        except Exception as exc:  # noqa: BLE001 — isolation IS the contract
            logger.exception("boot hook %s failed (isolated)", reg.name)
            results.append(BootHookResult(name=reg.name, ok=False,
                                          error=repr(exc)))
            continue
        results.append(BootHookResult(name=reg.name, ok=True))
    return tuple(results)


def reset_boot_hooks_for_tests() -> None:
    """Clear the registry. Test-only."""
    global _seq
    _hooks.clear()
    _seq = 0
