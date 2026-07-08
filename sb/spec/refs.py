"""The ref value types + the module-global ref table (K2, frozen L0 spec 01 §3.1).

Every callable a spec points at (a command handler, a panel renderer override,
an engine, a workflow, a provider) is carried in the manifest as a **ref value
object** holding only a string name, never the callable — this is what makes
the snapshot 100% data (design-spec §2.0).

Duplicate registration is an error, never a silent overwrite: a second module
binding an already-bound (kind, name) raises `RefRedefined` at import time —
surfaced as a P1 COMPILE_ERROR naming both modules. Belt-and-suspenders: the
same cross-manifest dup also surfaces as a P3 collision on the matching K1
namespace kind.

`PredicateRef` is the one `*Ref` that is NOT purely table-resolved (spec 02
§3.0 / spec 01 §3.1): the NAMESPACED string form `"<kind>:<key>[=<value>]"`
(kind in {setting, binding, capability, flag}; "" = constant-true) serializes
as the plain string and is evaluated by `predicates.evaluate` at runtime;
only the REGISTERED form serializes as {"$ref": "predicate:<name>"} and
resolves through the table.

Stdlib-only leaf.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, Union

F = TypeVar("F", bound=Callable)

NAMESPACED_PREDICATE_HEADS = ("setting", "binding", "capability", "flag")


@dataclass(frozen=True)
class HandlerRef:
    name: str
    kind = "handler"


@dataclass(frozen=True)
class PanelRef:
    name: str            # a panel_id
    kind = "panel"


@dataclass(frozen=True)
class ViewRef:
    name: str            # a re-homed legacy view class (§2.9 tier-3)
    kind = "view"


@dataclass(frozen=True)
class PredicateRef:
    name: str            # SPECIAL: two forms — namespaced string | registered name
    kind = "predicate"


@dataclass(frozen=True)
class EngineRef:
    name: str
    kind = "engine"


@dataclass(frozen=True)
class WorkflowRef:
    name: str            # returns the §2.7 WorkflowResult | None grammar (K7)
    kind = "workflow"


@dataclass(frozen=True)
class ProviderRef:
    name: str            # a read-model / data provider
    kind = "provider"


AnyRef = Union[HandlerRef, PanelRef, ViewRef, PredicateRef, EngineRef, WorkflowRef, ProviderRef]

REF_KINDS = ("handler", "panel", "view", "predicate", "engine", "workflow", "provider")


class RefRedefined(Exception):
    """A second module bound an already-bound (kind, name). Names BOTH modules."""

    def __init__(self, kind: str, name: str, first_module: str, second_module: str) -> None:
        super().__init__(
            f"{kind}:{name} bound twice — first by {first_module}, again by {second_module}"
        )
        self.kind = kind
        self.name = name
        self.first_module = first_module
        self.second_module = second_module


class RefUnresolved(Exception):
    """resolve() found no table entry for (kind, name) — ref_unresolved_at_boot."""


_REF_TABLE: dict[tuple[str, str], Callable] = {}
_REF_MODULES: dict[tuple[str, str], str] = {}


def _register(kind: str, name: str) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        key = (kind, name)
        module = getattr(fn, "__module__", "<unknown>")
        if key in _REF_TABLE:
            raise RefRedefined(kind, name, _REF_MODULES[key], module)
        _REF_TABLE[key] = fn
        _REF_MODULES[key] = module
        return fn

    return decorator


def handler(name: str) -> Callable[[F], F]:
    """Bind a handler ref name to a callable in sb/manifest/<x>.py."""
    return _register("handler", name)


def panel(name: str) -> Callable[[F], F]:
    return _register("panel", name)


def view(name: str) -> Callable[[F], F]:
    return _register("view", name)


def predicate(name: str) -> Callable[[F], F]:
    """Bind the REGISTERED PredicateRef form: a pure (PanelContext) -> bool."""
    return _register("predicate", name)


def engine(name: str) -> Callable[[F], F]:
    return _register("engine", name)


def workflow(name: str) -> Callable[[F], F]:
    return _register("workflow", name)


def provider(name: str) -> Callable[[F], F]:
    return _register("provider", name)


def is_namespaced_predicate(ref: PredicateRef) -> bool:
    """True for the parsed-string form (never table-resolved). "" = constant-true."""
    if ref.name == "":
        return True
    head, sep, _rest = ref.name.partition(":")
    return bool(sep) and head in NAMESPACED_PREDICATE_HEADS


def parse_namespaced_predicate(name: str) -> tuple[str, str, str | None]:
    """Parse "<kind>:<key>[=<value>]" -> (kind, key, value). ValueError if malformed.

    The empty string (constant-true) is the caller's short-circuit, not parsed here.
    """
    head, sep, rest = name.partition(":")
    if not sep or head not in NAMESPACED_PREDICATE_HEADS:
        raise ValueError(f"not a namespaced predicate: {name!r} "
                         f"(head must be one of {NAMESPACED_PREDICATE_HEADS})")
    if not rest:
        raise ValueError(f"namespaced predicate has empty key: {name!r}")
    key, eq, value = rest.partition("=")
    if not key:
        raise ValueError(f"namespaced predicate has empty key: {name!r}")
    return head, key, (value if eq else None)


def resolve(ref: AnyRef) -> Callable:
    """(kind, name) lookup; raises RefUnresolved if absent (FAILED_STARTUP at boot)."""
    try:
        return _REF_TABLE[(ref.kind, ref.name)]
    except KeyError:
        raise RefUnresolved(f"{ref.kind}:{ref.name} has no registered callable") from None


def is_registered(ref: AnyRef) -> bool:
    return (ref.kind, ref.name) in _REF_TABLE


def ref_inventory() -> dict[str, dict]:
    """{"handler:economy.give": {"module": "sb.manifest.economy"}} — the refs projection."""
    return {
        f"{kind}:{name}": {"module": _REF_MODULES[(kind, name)]}
        for (kind, name) in sorted(_REF_TABLE)
    }


def clear_ref_table() -> None:
    """Test/compiler support: reset the table (paired with purging sb.manifest
    modules from sys.modules so re-import re-registers). Never called at runtime."""
    _REF_TABLE.clear()
    _REF_MODULES.clear()
    for mod_name in [m for m in sys.modules if m.startswith("sb.manifest.")]:
        del sys.modules[mod_name]
