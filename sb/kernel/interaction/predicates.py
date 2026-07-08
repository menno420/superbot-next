"""`predicates.evaluate(ref, ctx)` — the shared PredicateRef evaluator
(frozen L0 spec 02 §3.0 / shared-vocab §7.4). Two forms:

- NAMESPACED string `"<kind>:<key>[=<value>]"`, kind ∈ {setting, binding,
  capability, flag}; `""` = the constant-true predicate. A parsed string,
  never `resolve()`d.
- REGISTERED ref (`PredicateRef` value object / `predicate:<name>`) resolved
  through the ref table to a pure `(ctx) -> bool`.

Read-only: settings through the K7 `sb.kernel.settings` read seam; bindings/
capabilities/flags through installable read ports (armed by their bands).
An unresolvable read is FAIL-CLOSED (False) — a gate that cannot be read
must not admit — and logged once per key.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from sb.spec.refs import PredicateRef, is_namespaced_predicate, parse_namespaced_predicate, resolve

logger = logging.getLogger("sb.kernel.interaction.predicates")

__all__ = ["EvalContext", "evaluate", "install_binding_reader",
           "install_capability_reader", "install_flag_reader",
           "reset_predicate_ports_for_tests"]


@dataclass(frozen=True)
class EvalContext:
    """The read-only evaluation context (the panel engine's PanelContext
    narrows to this at render time)."""

    guild_id: int
    channel_id: int | None = None
    actor: object | None = None


BindingReader = Callable[[int, str], Awaitable[bool]]        # bound?
CapabilityReader = Callable[[int, str], Awaitable[bool]]     # capability on?
FlagReader = Callable[[int, str], Awaitable[bool]]           # guild feature flag


async def _closed(guild_id: int, key: str) -> bool:
    return False


_binding_reader: BindingReader = _closed
_capability_reader: CapabilityReader = _closed
_flag_reader: FlagReader = _closed
_warned: set[str] = set()


def install_binding_reader(reader: BindingReader) -> None:
    global _binding_reader
    _binding_reader = reader


def install_capability_reader(reader: CapabilityReader) -> None:
    global _capability_reader
    _capability_reader = reader


def install_flag_reader(reader: FlagReader) -> None:
    global _flag_reader
    _flag_reader = reader


def reset_predicate_ports_for_tests() -> None:
    global _binding_reader, _capability_reader, _flag_reader
    _binding_reader = _capability_reader = _flag_reader = _closed
    _warned.clear()


def _warn_once(key: str, why: str) -> None:
    if key not in _warned:
        _warned.add(key)
        logger.warning("predicate %s unreadable (%s) — fail-closed", key, why)


async def evaluate(ref: object, ctx: EvalContext) -> bool:
    """THE evaluator — shared by the resolver's step-2a `enabled_when` /
    `visible_when` gate and the panel engine's render-time `visible_when`."""
    if ref is None or ref == "":
        return True                              # the constant-true predicate

    text = ref.name if isinstance(ref, PredicateRef) else str(ref)
    if text == "":
        return True
    if not is_namespaced_predicate(PredicateRef(text)):
        # the REGISTERED form — resolve through the ref table
        fn = resolve(PredicateRef(text))
        out = fn(ctx)
        return bool(await out) if hasattr(out, "__await__") else bool(out)

    kind, key, value = parse_namespaced_predicate(text)
    try:
        if kind == "setting":
            from sb.kernel import settings
            subsystem, _, name = key.partition(".")
            current = await settings.resolve(ctx.guild_id, subsystem, name)
            if value is None:
                return bool(current)
            return str(current).lower() == str(value).lower()
        if kind == "binding":
            return await _binding_reader(ctx.guild_id, key)
        if kind == "capability":
            return await _capability_reader(ctx.guild_id, key)
        if kind == "flag":
            return await _flag_reader(ctx.guild_id, key)
    except LookupError as exc:
        _warn_once(text, str(exc))
        return False
    _warn_once(text, f"unknown predicate kind {kind!r}")
    return False
