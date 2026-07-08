"""AI tool catalogue + deterministic selection (K10) — the orchestration
foundation, ported from shipped ``disbot/services/ai_tool_catalogue.py``
with the closed domain dict cut: the shipped ``CATALOGUE`` hardcoded ~35
BTD6/server tool rows; here tools REGISTER (spec + metadata + handler
factory) — domains bring their toolsets at their port band.

The invariants carry over verbatim:

* **Authority is never widened.** ``AIToolSpec.min_scope`` stays
  authoritative; a toolset/disable policy can *remove* a scope-allowed
  tool but can never grant one above the caller's :class:`AIScope`.
* Selection is deterministic and inspectable (the model never chooses
  what it may see); exclusions carry a stable
  :class:`ToolExclusionReason` in precedence order: scope → explicit
  disable → toolset filter.
* Grounding allowlists are DERIVED from ``grounding_domain`` metadata
  (:func:`grounding_tool_names`) so they cannot drift from the
  registered tool set by hand.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sb.kernel.ai.contracts import (
    AIScope,
    AIToolMetadata,
    AIToolSpec,
    ToolExclusionReason,
)

__all__ = [
    "RegisteredTool",
    "ToolDecision",
    "clear_tools_for_tests",
    "grounding_tool_names",
    "known_toolsets",
    "register_tool",
    "registered_tool",
    "registered_tools",
    "scope_allows",
    "select_tools",
]

# --- Scope ordering (canonical home) ----------------------------------------

_SCOPE_RANK: dict[AIScope, int] = {
    AIScope.USER: 0,
    AIScope.MODERATOR: 1,
    AIScope.ADMIN: 2,
    AIScope.SERVER_OWNER: 3,
    AIScope.PLATFORM_OWNER: 4,
    AIScope.SYSTEM: 5,
}


def scope_allows(caller: AIScope, required: AIScope) -> bool:
    """True if ``caller`` is privileged enough to be offered ``required``."""
    return _SCOPE_RANK.get(caller, 0) >= _SCOPE_RANK.get(required, 0)


# --- The registry ------------------------------------------------------------

#: A handler factory binds the tool's live async handler for one request
#: context (guild/actor); kept OUT of the spec so the model-visible data
#: object stays clean and redaction-safe.
HandlerFactory = Callable[..., Callable[[dict[str, Any]], Awaitable[Any]]]


@dataclass(frozen=True)
class RegisteredTool:
    """One catalogued tool: the provider-facing spec, the selection
    metadata, and (optionally) the runtime handler factory."""

    spec: AIToolSpec
    metadata: AIToolMetadata
    owner_subsystem: str
    handler_factory: HandlerFactory | None = None


_REGISTRY: dict[str, RegisteredTool] = {}


def register_tool(tool: RegisteredTool) -> RegisteredTool:
    """Register a tool by ``tool.spec.name``. A differing re-registration
    raises (two bands claiming one tool name is a build error)."""
    name = tool.spec.name
    prior = _REGISTRY.get(name)
    if prior is not None and prior != tool:
        raise ValueError(
            f"AI tool {name!r} already registered by {prior.owner_subsystem!r}",
        )
    _REGISTRY[name] = tool
    return tool


def registered_tool(name: str) -> RegisteredTool | None:
    return _REGISTRY.get(name)


def registered_tools() -> tuple[RegisteredTool, ...]:
    return tuple(_REGISTRY[name] for name in sorted(_REGISTRY))


def clear_tools_for_tests() -> None:
    _REGISTRY.clear()


def known_toolsets() -> frozenset[str]:
    """Every toolset name any registered tool declares membership in."""
    return frozenset(
        ts for tool in _REGISTRY.values() for ts in tool.metadata.toolsets
    )


def grounding_tool_names(domain: str) -> frozenset[str]:
    """Tools whose results may ground a ``domain`` answer (join the
    faithfulness ledger) — derived, never hand-maintained."""
    return frozenset(
        name
        for name, tool in _REGISTRY.items()
        if tool.metadata.grounding_domain == domain
    )


# --- Deterministic selection --------------------------------------------------


@dataclass(frozen=True)
class ToolDecision:
    """Why one candidate tool was offered or withheld for a request. The
    ``included`` set is exactly the offered toolset; exclusions carry a
    stable reason for an effective-policy preview / dry run."""

    name: str
    included: bool
    reason: ToolExclusionReason | None = None


def select_tools(
    candidates: Sequence[AIToolSpec],
    *,
    scope: AIScope,
    enabled_toolsets: Collection[str] | None = None,
    disabled_tools: Collection[str] | None = None,
    catalogue: Mapping[str, AIToolMetadata] | None = None,
) -> list[ToolDecision]:
    """Decide which ``candidates`` to offer. Precedence (authority first;
    policy may only narrow):

    1. ``scope_denied`` — caller below the tool's ``min_scope``.
    2. ``explicitly_disabled`` — named in ``disabled_tools`` (explicit
       disable wins over an enabling toolset).
    3. ``toolset_disabled`` — ``enabled_toolsets`` set and the tool
       shares no toolset with it.

    ``enabled_toolsets=None`` + ``disabled_tools=None`` → scope is the
    only filter (the historical behaviour). ``catalogue`` defaults to the
    registry's metadata view.
    """
    if catalogue is None:
        cat: Mapping[str, AIToolMetadata] = {
            name: tool.metadata for name, tool in _REGISTRY.items()
        }
    else:
        cat = catalogue
    disabled = set(disabled_tools or ())
    enabled = set(enabled_toolsets) if enabled_toolsets is not None else None

    decisions: list[ToolDecision] = []
    for spec in candidates:
        reason = _exclusion_reason(
            spec,
            scope=scope,
            enabled=enabled,
            disabled=disabled,
            cat=cat,
        )
        decisions.append(ToolDecision(spec.name, reason is None, reason))
    return decisions


def _exclusion_reason(
    spec: AIToolSpec,
    *,
    scope: AIScope,
    enabled: set[str] | None,
    disabled: set[str],
    cat: Mapping[str, AIToolMetadata],
) -> ToolExclusionReason | None:
    if not scope_allows(scope, spec.min_scope):
        return ToolExclusionReason.SCOPE_DENIED
    if spec.name in disabled:
        return ToolExclusionReason.EXPLICITLY_DISABLED
    if enabled is not None:
        meta = cat.get(spec.name)
        tool_toolsets = meta.toolsets if meta is not None else frozenset()
        if enabled.isdisjoint(tool_toolsets):
            return ToolExclusionReason.TOOLSET_DISABLED
    return None
