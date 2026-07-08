"""The runtime read surface over the frozen index (frozen L0 spec 03 §3.3).

Stdlib-only leaf; frozen after build. No DB, no mutation after boot — every
runtime name is either a manifest identity (immutable) or a custom trigger
(stored elsewhere), so the reservation set never changes at runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sb.namespace.kinds import CommandScope, NamespaceKind, Surface, normalize
from sb.namespace.records import ReservationHit, ReservationRecord

IndexKey = tuple[NamespaceKind, str, CommandScope | None]


@dataclass(frozen=True)
class ReservationIndex:
    _by_key: Mapping[IndexKey, ReservationRecord]

    def is_reserved(
        self,
        value: str,
        kind: NamespaceKind,
        *,
        surface: Surface | None = None,
        parent: str | None = None,
    ) -> ReservationHit | None:
        """The canonical predicate — a POINT query, not the exhaustive oracle.

        surface: for kind=command, if given, checks only that surface's scope;
                 if omitted (None), checks BOTH surfaces (conservative — a name
                 reserved in either is unavailable). For non-command kinds,
                 surface/parent are ignored (global scope).
        parent:  parent=None (default) restricts the query to the TOP-LEVEL
                 scope. To query a subcommand scope explicitly, pass
                 parent="ticket". There is NO any-parent wildcard here —
                 exhaustive cross-scope collision detection is `validate`'s
                 job. Consequence (relied on by check_trigger): a word equal to
                 a SUBCOMMAND name with the default parent=None is reported
                 AVAILABLE (a subcommand is not bare-word invokable).
        Returns the blocking ReservationHit (origin + renamed_to + reason), or None.
        """
        norm = normalize(value, kind)
        if kind is not NamespaceKind.COMMAND:
            return self._by_key.get((kind, norm, None))
        surfaces = (surface,) if surface is not None else (Surface.PREFIX, Surface.SLASH)
        for s in surfaces:
            hit = self._by_key.get((kind, norm, CommandScope(s, parent)))
            if hit is not None:
                return hit
        return None

    def resolve_command(self, name: str, *, surface: Surface) -> ReservationHit | None:
        """Exact command lookup returning a LEAF-SAFE record (owner + spec_id +
        qualified path) — NOT a TargetRef. The resolver/composition (K8)
        assembles the TargetRef from spec_id (spec 03 §4 seam correction).
        None => not a declared command on that surface. Checks the top-level
        scope (bare-word invokable names).
        """
        return self._by_key.get(
            (NamespaceKind.COMMAND, normalize(name, NamespaceKind.COMMAND),
             CommandScope(surface, None))
        )

    def command_corpus(self, surface: Surface) -> frozenset[str]:
        """The fuzzy candidate set (C-5 consumes). K1 owns the CORPUS; C-5 owns
        the AUTO/SUGGEST/NONE thresholds. Top-level names on `surface`."""
        return frozenset(
            value
            for (kind, value, scope) in self._by_key
            if kind is NamespaceKind.COMMAND
            and scope is not None
            and scope.surface is surface
            and scope.parent_group is None
        )

    def all_for_kind(self, kind: NamespaceKind) -> frozenset[str]:
        return frozenset(value for (k, value, _scope) in self._by_key if k is kind)

    def records(self) -> tuple[ReservationRecord, ...]:
        """Deterministic full dump (tooling/tests)."""
        return tuple(self._by_key[k] for k in sorted(
            self._by_key,
            key=lambda key: (key[0].value, key[1],
                             "" if key[2] is None
                             else f"{key[2].surface.value}/{key[2].parent_group or ''}"),
        ))
