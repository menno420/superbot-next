# 2026-07-12 — ORDER-004 live-drive evidence for the live effect-adapter stack

> **Status:** `complete`

- **📊 Model:** fable-5

## Scope

The LIVE-DRIVE PROOF the #283 landing named as its ⚠ NEXT IMMEDIATE STEP: drive
real Discord effects through the just-merged live effect-adapter stack
(#263 `248d068` moderation · #278 `b7a0513` role · #283 `291caec` channel +
fix pass; runtime-smoke gate #293 `3cc0426`) at main HEAD `291caec`, and land
the evidence in control/status.md. A sibling session shipped the code but its
permission layer denied booting the bot; this fresh session retried and the
boot was ALLOWED — no wall.

## Mechanism (the proven #144/#148/#151 shape)

Real composition root (`run_app`) booted against local Postgres 16
(cluster was WIPED by a container restart — re-provisioned per the standing
recovery: `pg_ctlcluster 16 main start` + role/DB creation matching the env
DSN; migrations 0001–0035 applied fresh), `SB_DATA_PLANE=test` +
`SB_APPCMD_SYNC_GUILD_ID=1522099141671653417` (the double gate), inbound fed
through the REAL pipeline entrypoint `message_feed.handle_prefix_message`
(actor = the guild owner member from the gateway cache). Replies and effects
are real Discord state in Superbot Admin. Verbatim READY line of the driven
boot:

```
2026-07-12 19:12:45,354 INFO sb.adapters.discord.gateway gateway READY: logged in as Galaxy Bot#6724 (id=1298426054636994611), 3 guild(s)
```

All four ARMED lines present (moderation / role / channel / utility-diagnostic
read seams, each `test plane, guild 1522099141671653417 ONLY`); audit canary
delivered; clean SIGTERM shutdown (`lifecycle STOPPED — clean exit`) on both
boots.

## What was driven (links = real posts in Superbot Admin #general)

Full table + DB rows in the control/status.md record this card rides with.
Moderation: `!ban` + `!unban` of the owner's old SuperBot app account
(hackban, ban-list entry REST-verified both ways) + a compensator probe
(`!ban` of a nonexistent id). Channel (the newly-armed ChannelStateActions):
`!evt … create` → `!topic …` (a #283 fix-pass method, pre-fix AttributeError)
→ `!del …` — created, mutated, cleaned up, cache-verified at each step.

## ⚑ Follow-up flagged (decide-and-flag, not fixed here)

A Discord-REFUSED `!ban` (apply leg 404) leaves its durable claim rows
(`mod_logs` ban row + `audit_log member_banned`) — ban's declared compensator
is the Discord-side symmetric restore (`moderation.compensate_ban` = unban),
which itself 404s on a never-landed ban; the engine records the operator
finding and returns `partial`, with NO user-facing reply. Kick has the
row-withdraw twin (`_compensate_kick`); warn got the ORDER-004 item-1 fix.
Guard recipe: `sb/domain/moderation/ops.py::_compensate_ban` (+ the `_leg`
spec pairing in the same file) vs `_compensate_kick`'s
`store.withdraw_mod_log_rows` shape; test target
`tests/unit/band2/` moderation compensator pins. Whether ban should get the
kick-style claim-withdrawal on a refused APPLY (vs the restore posture for a
later-leg failure) is an oracle-fidelity question for the moderation lane.

## 💡 Session idea

The drive harness (a ~150-line scratchpad driver: capture the bot instance at
`build_bot`, poll a command file, feed `handle_prefix_message`, log reply
links as JSON) is re-derived every live-drive session from the PR-body
descriptions. Committing a `tools/live_drive_harness.py` with exactly that
shape (gated on the same env double gate, refusing when `SB_DATA_PLANE !=
test`) would turn every future ORDER-004 leg into "write cmds.txt".

## ⟲ previous-session review

The sibling session that landed #263/#278/#283 left a precise, honest trail —
its "⚠ NEXT IMMEDIATE STEP: the LIVE-DRIVE PROOF" line plus the de-hardcoded
runbook (`docs/operations/live-drive-guild-effects.md`) made this session
mechanical: env names, the double gate, the ARMED-line checklist, and the
audit-row SQL were all correct at HEAD. What it could not verify — that the
newly-implemented `set_topic`/directory-led lanes actually reach Discord — is
exactly what this session proved live. The one friction it bequeathed was
environmental, not documentary: the wiped Postgres cluster (known recovery,
ops-note (2)).
