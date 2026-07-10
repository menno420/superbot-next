---
state: captured
origin: consumer:menno420/superbot
shipped_pr: null
shipped_repo: null
merged_date: null
outcome: open
---

# Effect-leg compensation gaps: timeout + end_access, plus the invariant that prevents the class (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (routed from superbot's verification of the external
> runtime review — superbot `docs/eap/superbot-next-runtime-review-2026-07-10.md`
> incl. its verification addendum, and
> `docs/eap/codex-review-round-verification-2026-07-10.md` §4).
> **Origin:** external (Codex/Sol) review, independently verified by Claude
> against this repo's HEAD `04436ab` (mechanisms traced, tests re-run).

**One line:** two ops commit a DB row before an uncompensated Discord EFFECT —
a refused effect leaves durable history claiming something happened that didn't
— plus one invariant test that makes the whole class unwritable.

## The two confirmed instances

1. **`moderation.timeout`** — `record_timeout` writes the mod-history row via
   `store.log_mod_action(..., action="timeout")` (`sb/domain/moderation/ops.py:150-152`)
   and commits; `apply_timeout` (EFFECT) is declared `"reversible"` with **no
   compensator** (`TIMEOUT = _op(...)`). A Discord-refused timeout (permissions /
   role hierarchy — common live) leaves history saying the member was timed out.
   Fix = the warn pattern: thread the row id, declare `compensatable`, withdraw
   the row in `moderation.compensate_timeout`, pin with a blocked-path test like
   `test_warn_escalation_blocked_compensates`.
2. **`proof_channel.end_access`** — `record_unlock` (DB) commits before
   `apply_unlock` (EFFECT, `"reversible"`, no compensator)
   (`sb/domain/proof_channel/ops.py:154-162`). Same fix shape; contrast
   `GRANT_PRIZE`, which already declares `compensate_lock`.

## The class-killer (the more valuable half)

A `"reversible"` EFFECT leg without a compensator behaves identically to
`irreversible` at runtime (engine: failed effect without compensator → operator
finding only; `sb/kernel/workflow/engine.py:326-360`) — the label promises
safety that isn't wired. **Add a unit invariant** (the
`test_no_domain_module_redeclares_reply` pattern): every non-`optional`,
non-`irreversible` EFFECT leg that follows a DB leg in a `CompoundOpSpec` must
declare a `compensator`. This catches the class at authoring time; both
instances above fail it today, and `KICK` (deliberately `irreversible` + typed-phrase confirmation —
the kick-reversibility ruling stamped at its one home in `docs/decisions.md`) passes it by design.

## Route

Quick-win lane: two compensators + two blocked-path tests + one invariant test,
all inside `sb/domain/moderation`, `sb/domain/proof_channel`, and
`tests/unit/`. No decisions needed; the warn fix is the in-repo precedent.
