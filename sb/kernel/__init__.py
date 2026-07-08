"""``sb/kernel`` — kernel bands (config, observability, db, ...).

Kernel modules import ``sb/spec`` (dataclasses) + stdlib/asyncpg only.
No upward import to services/views/cogs, ever (design-spec §1.1).
"""
