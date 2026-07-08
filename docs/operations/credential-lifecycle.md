# Credential lifecycle — compromise-recovery runbook + rotation cadence

> **Status:** `reference` — the S13 ops runbook (frozen L0 spec 12 §2.B(3)).
> The registry of record is `sb/spec/credentials.py` (`CREDENTIAL_REGISTRY`);
> CI gate `tools/check_credential_lifecycle.py`; rotation executor
> `sb/kernel/credentials/rotation.py` (phase ledger `sb_credential_rotation`,
> migration 0007); cadence detector `sb/kernel/credentials/cadence.py` +
> `tools/check_rotation_due.py`.

## The design invariant

LEAF credentials rotate/revoke fully autonomously; only ROOT credentials
(the Railway account token + the GitHub repo-write token — the container's
own authorization roots) keep ONE irreducible owner touch, as a **scheduled
prompt**, never an operational dependency. Cadence defaults: leaf 90 d /
root 180 d (ops-tunable constants, not a fork).

## Rotation mechanics (why it survives its own restart)

Swapping a `WORKER_ENV` credential auto-redeploys the worker (merge/var
change = deploy = restart, Q-0193) — the swap restarts the process
performing it. So the cadence routine only DETECTS due and ARMS a
`TaskDurability.DURABLE` `OneShot` on 09's due-queue
(`arm_due_rotations`); the durable one-shot runs the resumable multi-txn
protocol over the phase ledger:

| `phase` | committed | meaning |
|---|---|---|
| `reserved` | txn-1, with the horizon-stable `once()` guard, BEFORE any external call | we own this horizon |
| `issued_pending_verify` | txn-2, after provider re-issue + store-var swap (non-secret fingerprint only) | the state the swap-redeploy lands in |
| `verified` | txn-3, post-boot read-back green | terminal success (`last_rotated_at`) |
| `failed` | any phase, non-retryable | terminal; operator finding |

The `once()` key is `credential.rotation:0:{name}:{horizon_epoch}` —
horizon-stable, so a duplicate arm and a boot-reconcile re-fire resolve to
the same guard row and RESUME (never a second credential). Concrete
provider/Railway/Discord API bindings are CUT-1 ops wiring behind the
installable `RotationProvider` port; un-wired rotations FAIL loudly.

The detector is a **scheduled ops routine** (owner arms it at CUT-1 — no
Routine is created by the build): run `python3 tools/check_rotation_due.py`
on a daily/weekly cadence; with a live DB it joins the ledger's
`last_rotated_at`; due leaves arm the one-shot, due roots prompt the owner.

## Compromise-recovery procedure (spec 12 §2.B(3))

Multiple compromised credentials triage **highest `BlastTier` first**
(`ACCOUNT > PROD_DATA > CONTROL > BOT_PRESENCE > SPEND > TEST_ONLY`). Per
credential, five steps:

1. **Detect** — live: the Railway $15 usage alert + the deploy webhook;
   this repo adds the `pip-audit` CI gate (known-CVE dep). Owner-toggle
   (flagged): GitHub secret-scanning push-protection + Dependabot security
   alerts.
2. **Contain** — per-credential, not blanket: the internal `DATABASE_URL`
   is structurally rail-capped (`assert_data_plane`); the external
   `DATABASE_PUBLIC_URL` proxy has NO structural containment — it is a
   first-priority rotation target; account/control/spend leaves likewise
   contain only via Rotate+Revoke.
3. **Rotate** — `WORKER_ENV`: the durable one-shot (above). Others:
   synchronous re-issue + read-back in-fire under the same horizon guard.
4. **Revoke** — kill the leaked copy via the row's `revocation_ref`
   (closed vocabulary). Leaf revocation being agent-runnable needs the
   CL-2 brake carve-out (owner-gated — see the question router).
5. **Post-mortem** — confirm prod healthy on new creds; the `verified`
   ledger row IS the `last_rotated_at` write; if supply-chain, remove/pin
   the dep + regenerate `requirements.lock` in the same PR.

## Supply-chain posture (spec 12 §2.C)

`requirements.txt` = human-edited constraints (with `<next-major`
ceilings, CL-6); `requirements.lock` = the hash-pinned resolved output
(`pip-compile --generate-hashes`). Deploy installs
`pip install --require-hashes -r requirements.lock`. Adopt-freely (Q-0105)
stands: adopt → regenerate the lock in the same PR → the lock diff is the
deferred-review artifact. CI: `check_lockfile_fresh` (static + `--regen`)
and `pip-audit` over the resolved lock (`.github/workflows/ci.yml`).

## Owner-gated (proposed, never self-applied — routed in the question router)

- **CL-1** recovery arm at all (recommended: yes — recovery is orthogonal
  to the Q-0213 concentration decision).
- **CL-2** narrow the Q-0213 `*Delete` brake so credential REVOCATION (the
  `RevocationRef` closed set) is agent-runnable recovery; resource deletion
  stays ask-first.
- **CL-3** lockfile + CI gates composing WITH adopt-freely (recommended:
  built as-shipped; the lock diff is the deferred review).
- **CL-5b** `SB_PROD_ATTEST` durable custody SOURCE (plain env vs sealed vs
  OIDC) — carried forward unresolved (SF-d); only its rotation ROW lives in
  the registry.
