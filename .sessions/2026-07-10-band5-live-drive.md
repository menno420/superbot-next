# 2026-07-10 — band-5 live-drive leg (testing ladder step 7, live half)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5

## Scope

The band-5 LIVE-DRIVE leg (the replay half landed via PR #95/#97). Boot the
new bot live against Discord on the test-app token, re-verify the grant
state, drive the band-5 surfaces (role, proof_channel, general/utility) as
far as grants allow, record the ORDER 011 live-boot verification, and ship
the results into the testing ledger. Docs/status-only PR by design — the
three live bugs found are RECORDED for the fix lane, not fixed here.

## What shipped

1. `docs/status/testing-report-2026-07-09.md` — step-7 row amended to
   live-leg-done + the new "Band-5 evidence (step 7 LIVE-DRIVE leg)"
   verbatim block, including the surface ledger
   (exercised / degraded / blocked-by-bug / not-ported).
2. This session log.

## Key results (detail in the testing report's band-5 evidence block)

- **ORDER 011 live verification DONE**: `python3 -m sb` @ main `5fcc1a9`
  with `SB_TEST_DB_HOSTS` unset booted a fresh DB to RUNNING on the one
  loud line ("DB-host allowlist not set — accepting DSN host
  '127.0.0.1'"); no refusal, no ask; clean SIGTERM exit.
- **Grant state moved under us (re-verified, both better than
  control/status.md records)**: `SB_INTENT_MSGCONTENT_OK=true` /
  `SB_INTENT_MEMBERS_OK=true` are now PRESENT in the session env (zero
  degrade markers at READY), and the OLD SuperBot is GONE from
  MineSnakeBotTest (404 Unknown Member) — flag 15 resolved owner-side, no
  test prefix needed. New fact: `SB_APPCMD_SYNC_GUILD_ID` points at a NEW
  owner guild "Superbot Admin" (1522099141671653417); the boot synced 12
  commands there, not to MineSnakeBotTest.
- **Every ported band-5 surface exercised live** (real gateway, real posts,
  prefix + component bands, K7 writes audited, outbox 18/18 delivered);
  the role/proof-channel EFFECT ports are honest PARTIAL degrades and the
  PR #105 compensators fired for real (no stranded rows).
- **3 live bugs found (fix lane next)**: (1) role pending terminals
  unregistered in the live root (ENSURE_REFS never runs with zero plugins
  admitted → RefUnresolved BUG envelopes); (2) setrole/unsetrole/
  removereactrole acks read `result.after["record"]` which doesn't exist →
  wrong copy over correct audited writes; (3) temprole failure copy leaks
  the raw `WorkflowResult` repr.

## 💡 Session idea

The live leg keeps finding one shape of bug the replay leg structurally
cannot: registrations that only happen on a path the parity boot takes but
the live root doesn't (this session: ENSURE_REFS/pending_handler; band 1:
panel registration; band 4: the chat award with no caller). A cheap fence
would be a composition-parity test that boots BOTH roots headless and
diffs the registered ref/handler/panel sets — any ref reachable from a
manifest command that resolves in one root but not the other is a red.
That one test would have caught three bands' worth of live-only finds at
authoring time.

## ⟲ Previous-session review

The #105 session's compensator work paid off exactly as designed — this
leg watched `compensate_grant_temp` and `compensate_lock` fire against the
real uninstalled-port refusals and leave zero stranded rows, which turned
what would have been two "phantom state" bug reports into two one-line
confirmations. What it under-delivered: its heartbeat's grants block went
stale within a day (intents now set, old bot now gone, sync guild id now
different) — grant facts belong to re-verification at drive time, not to
the heartbeat, and this session's re-verify-first step is what caught all
three deltas.
