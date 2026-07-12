# `docs/scoping/` — pre-build scoping records

> **Status:** `reference`

Durable scope-only records for multi-slice ports: the collision map, the
deferred owner decision, and the ordered slice plan captured **before** any
implementation lands. A scoping doc is the paper trail a gated port reads from
so a later session (or the owner) can pick up the decision without re-deriving
the surface.

- [energy-system-scope.md](energy-system-scope.md) — mining/fishing energy
  system port. Slice 0 (pure domain core) landed; persistence + `!cook`/`!use`
  wiring and `!fastmine` dig-gating are later, owner-gated slices (dig-gating
  awaits an owner decision and sequences strictly after WP-3 #317).
