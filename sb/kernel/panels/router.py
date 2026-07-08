"""The kernel custom-id router (K8/S9b — design-spec §3.4, decision 6).

Fixed dispatch precedence, id families disjoint BY CONSTRUCTION:

  1. exact match in the ONE static registration table (legacy verbatim ids
     and canonical ``<panel_id>.<action_id>`` ids live in one table, both
     populations byte-exact-unique at registration);
  2. versioned dynamic parse — an id beginning with a scheme token
     (``g<N>:``) routes to that version's registered parser;
  3. no match → the polite-expiry response ("this session has expired") +
     disable the message's components — schema evolution can never crash
     routing or strand a clickable corpse.

The ``g1`` scheme (``g1:<game_key>:<session_id>:<action>``) parser ships
here; the namespace reserves each game's ``g1:<game_key>:`` prefix so two
games can never mint overlapping session ids. A future shape change mints
``g2:`` while this router keeps the ``g1`` parser for a deprecation window.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from sb.kernel.panels.registry import ComponentBinding, NavBinding, static_route

__all__ = [
    "DynamicRoute",
    "ExpiredRoute",
    "Routed",
    "parse_g1",
    "register_scheme_parser",
    "reset_router_for_tests",
    "route",
]

_SCHEME_TOKEN_RE = re.compile(r"^([a-z]+\d+):")

EXPIRY_MESSAGE = "This session has expired — start a new one."


@dataclass(frozen=True)
class DynamicRoute:
    """A parsed versioned dynamic id (routes to a recovered session; the id
    is never itself the authority)."""

    scheme: str            # "g1"
    key: str               # e.g. the game_key
    session_id: str        # the checkpoint key (restart recovery re-binds)
    action: str


@dataclass(frozen=True)
class ExpiredRoute:
    """Precedence step (3): the polite-expiry terminal."""

    custom_id: str
    message: str = EXPIRY_MESSAGE
    disable_components: bool = True


Routed = ComponentBinding | NavBinding | DynamicRoute | ExpiredRoute

SchemeParser = Callable[[str], DynamicRoute | None]


def parse_g1(custom_id: str) -> DynamicRoute | None:
    """``g1:<game_key>:<session_id>:<action>`` — None on malformed (→ expiry)."""
    parts = custom_id.split(":", 3)
    if len(parts) != 4 or parts[0] != "g1" or not all(parts[1:]):
        return None
    return DynamicRoute(scheme="g1", key=parts[1], session_id=parts[2], action=parts[3])


_parsers: dict[str, SchemeParser] = {"g1": parse_g1}


def register_scheme_parser(token: str, parser: SchemeParser) -> None:
    if not re.fullmatch(r"[a-z]+\d+", token):
        raise ValueError(f"scheme token {token!r} must match [a-z]+<N>")
    if token in _parsers:
        raise ValueError(f"scheme token {token!r} already has a parser")
    _parsers[token] = parser


def reset_router_for_tests() -> None:
    _parsers.clear()
    _parsers["g1"] = parse_g1


def route(custom_id: str) -> Routed:
    """The fixed §3.4 precedence: static → versioned parse → polite expiry."""
    binding = static_route(custom_id)
    if binding is not None:
        return binding
    m = _SCHEME_TOKEN_RE.match(custom_id)
    if m:
        parser = _parsers.get(m.group(1))
        if parser is not None:
            parsed = parser(custom_id)
            if parsed is not None:
                return parsed
    return ExpiredRoute(custom_id=custom_id)
