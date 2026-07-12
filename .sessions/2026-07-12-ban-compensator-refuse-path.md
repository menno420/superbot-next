# 2026-07-12 — ban compensator: withdraw the false history row on a never-landed ban

> **Status:** `complete`

- **📊 Model:** fable-class

## Scope

The ⚑ follow-up the ORDER-004 live-drive evidence card flagged (its
compensator probe: `!ban` of a nonexistent id): a Discord-REFUSED ban
(apply leg 404) leaves its durable claim row — the `mod_logs` ban row the
record leg committed — because ban's compensator
(`sb/domain/moderation/ops.py::_compensate_ban`) only knows the Discord-side
symmetric restore (unban), which itself 404s on a ban that never landed;
the engine records the operator finding and returns `partial`, and the
false history row stays.

This slice guards exactly that refuse path: keep the unban as the primary
restore (correct when a LATER leg failed after the ban actually landed),
and when the unban reports NotFound — the ban never landed — fall back to
kick's row-withdraw twin (`_compensate_kick`'s
`store.withdraw_mod_log_rows` shape over the `_ban_row_id` handle the
record leg already stashes), record the operator finding, and return a
successful LegOutcome. Oracle fidelity decides the posture: disbot's
moderation service calls Discord FIRST and writes the row only after
success — a refused ban writes NO row. A non-NotFound unban failure still
propagates so the engine records `partial` honestly.

Out of scope: `_compensate_unban`, the audit_log row (LEDGER, intentionally
permanent — kick leaves its audit row too), every other band.

Tests: `tests/unit/band2/test_band2_slice1.py`, following
`test_kick_blocked_compensates` — refuse path withdraws the row, restore
path never withdraws, missing handle no-ops, non-NotFound propagates, and
the BAN leg-wiring pin. Full suite green (2007 passed, 13 skipped);
check_symbol_shadowing / check_namespace / check_no_skip /
check_config_usage all pass.

## 💡 Session idea

The domain now classifies the port's discord exceptions by NAME in three
places (role/service.py sweep, role/automation.py `_classify_exception`,
and this compensator) with the same "guarded band-2 pattern; discord is
absent in-container" comment re-derived each time. A tiny shared helper —
`sb/kernel/interaction/errors.py::is_discord_not_found(exc)` (name + MRO
match, one docstring citing the layer fence) — would make the idiom
greppable and stop the next lane from inventing a fourth variant with a
subtly different match (e.g. missing the MRO walk automation.py does for
HTTPException).

## ⟲ previous-session review

The ORDER-004 live-drive evidence card was a model handoff for this exact
slice: its ⚑ follow-up named the broken symbol (`_compensate_ban`), the
correct twin (`_compensate_kick`'s `withdraw_mod_log_rows` shape), the
test target directory, AND framed the real decision ("kick-style
claim-withdrawal on a refused APPLY vs the restore posture for a
later-leg failure") as the oracle-fidelity question it is — this session
only had to answer it, not rediscover it. One gap: the card said the
refused ban leaves "mod_logs ban row + audit_log member_banned" without
flagging that the audit row is LEDGER (intentionally permanent, kick's
compensator leaves its own) — a reader without the kick precedent could
have over-scoped the fix into un-writing the audit trail.
