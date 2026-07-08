-- 0001_idempotency_keys.sql — the K3 idempotency guard store
-- (frozen L0 spec 05 §3.7/§5, T2-2 seed). Fresh chain 0001+ (design-spec §5.2).
--
-- Write paths: once() INSERTs key/namespace/first_seen_at (outcome/result_ref
-- NULL); record_outcome() UPDATEs outcome/result_ref in the same txn;
-- read_outcome() SELECTs them for the False branch. PK on key IS the dedup
-- guard; the secondary index serves the per-namespace retention sweep
-- (StoreSpec.retention per namespace — §10.3 pre-cutover inventory).

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key           TEXT   PRIMARY KEY,   -- IdempotencyKey.render(): {namespace}:{guild_id}:{dedup_token}
    namespace     TEXT   NOT NULL,      -- retention scoping + bounded metrics label
    first_seen_at BIGINT NOT NULL,      -- insertion epoch (set by once())
    outcome       TEXT,                 -- frozen §2.7 vocab; NULL until record_outcome()
    result_ref    TEXT                  -- optional pointer to the durable result
);

CREATE INDEX IF NOT EXISTS idempotency_keys_namespace_first_seen_idx
    ON idempotency_keys (namespace, first_seen_at);
