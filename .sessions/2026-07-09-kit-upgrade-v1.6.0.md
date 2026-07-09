# 2026-07-09 — vendored kit upgrade to substrate-kit v1.6.0

> **Status:** `in-progress`

## Scope

Third real-world run of the kit's `upgrade` verb (v1.0.0 → PR #46,
v1.2.0 → PR #66-era): move the vendored `bootstrap.py` from v1.2.0 to the
released v1.6.0 (sha256
`787d561728f64070efd7e25db05a1264db24b4bee66b08a296ebd205d6d8060f`, verified
against `release.json`, `bootstrap.py.sha256`, and the release-asset digests
before starting). Deltas inherited since 1.2.0: v1.3.0 heartbeat `kit:` line +
adopters registry, v1.4.0 configurable `heartbeat_files`, v1.5.0
CAPABILITIES.md + orientation wiring + close nudge, v1.6.0 owner-action
six-field checker + order-claim convention. Then: report classification,
`--apply-docs` only where safe, honest `check --strict` fixes (incl. the new
owner-action advisory on `control/status.md` if it fires), full local gate run.

- **📊 Model:** claude-fable-5 · high · mechanical upgrade + doc reconcile
