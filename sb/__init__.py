"""SuperBot rebuild source root (``sb/``).

Layer map (rebuild design-spec §1.1):

- ``sb/spec/``       — stdlib-only grammar leaves (frozen dataclasses, registries).
- ``sb/namespace/``  — stdlib-only namespace-registry leaf (K1).
- ``sb/kernel/``     — kernel bands (config, observability, db, authority, ...).
- ``sb/adapters/``   — I/O adapters (http health, discord surfaces).
- ``sb/app/``        — the composition root (may import everything).
- ``sb/manifest/``   — pure declarations + handler registrations.

No ``kernel -> domain`` import edge, ever.
"""
