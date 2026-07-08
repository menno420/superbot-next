"""``sb/kernel/db`` — the DB seam (K3) + the data-plane rail (K0-consumed).

S1 landed `data_plane.py` (pure config logic — `preflight()` calls it,
spec 05 §3.5). S4 (K3) lands `pool.py` (+`transaction()`, `checked_acquire()`,
`DBUnavailable`), `migrations.py` (fresh chain 0001+, checksum verify), and
`idempotency.py` (`IdempotencyKey`/`once()`/`record_outcome()`/`read_outcome()`).
asyncpg-only below this seam (import-guarded); no upward imports. Raw
`conn.execute`/`conn.transaction()` are banned outside this package (spec 05
§7) — domains use `fetchone/fetchall/execute` or `db.transaction()`.
"""
