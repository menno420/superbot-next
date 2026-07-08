-- 0007: the credential-rotation ledger (S13, frozen L0 spec 12 §2.B(1c)).
-- One row per (name, horizon_epoch) rotation attempt — the small closed
-- phase state machine committed across the executor's multi-txn protocol:
--   reserved -> issued_pending_verify -> verified | failed
-- The SECRET VALUE never enters this table: `fingerprint` is the new
-- credential's NON-SECRET identity (key id / last-4 / issuance tag) only.
-- last_rotated_at for the cadence detector = MAX(verified_at) per name.

CREATE TABLE IF NOT EXISTS sb_credential_rotation (
    name            TEXT        NOT NULL,   -- CredentialSpec.name (registry key)
    horizon_epoch   BIGINT      NOT NULL,   -- the cadence horizon this rotation serves
    phase           TEXT        NOT NULL DEFAULT 'reserved'
        CHECK (phase IN ('reserved', 'issued_pending_verify', 'verified', 'failed')),
    fingerprint     TEXT,                   -- non-secret identity of the ISSUED credential
    issued_at       TIMESTAMPTZ,            -- set at issued_pending_verify
    verified_at     TIMESTAMPTZ,            -- set at verified (terminal success)
    detail          TEXT,                   -- failure reason / resume notes
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (name, horizon_epoch)
);

-- the cadence detector's join: latest verified rotation per credential.
CREATE INDEX IF NOT EXISTS idx_credential_rotation_verified
    ON sb_credential_rotation (name, verified_at DESC)
    WHERE phase = 'verified';
