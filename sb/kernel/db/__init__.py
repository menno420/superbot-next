"""``sb/kernel/db`` — the DB seam (K3) + the data-plane rail (K0-consumed).

S1 lands `data_plane.py` only (pure config logic — `preflight()` calls it,
spec 05 §3.5). S4 (K3) lands `pool.py` (+`transaction()`), `migrations.py`,
`idempotency.py`. asyncpg-only below this seam; no upward imports.
"""
