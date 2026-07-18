# 2026-07-18 — setup-band count/list soft-fail boundary audit + characterization pins

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · test writing · fail-open audit + characterization pins

## Scope

A targeted correctness audit of the setup band (`sb/domain/setup/`),
extending the moderation-except pin #516 (backlog item C1) to the rest of
the "count / list soft-fail" family the production-readiness backlog
(#513) flagged.

The hypothesis under test: several `except Exception` handlers wrap a
pending-count / ops-list read that is meant to be an INFORMATIONAL
soft-fail (degrade to `0` / empty). That is benign ONLY IF the swallow
sits STRICTLY AFTER the paired WRITE has already committed. If any such
`try` ALSO enclosed the write or the commit, a failure there would be
silently swallowed and the handler would report SUCCESS on a write that
never landed — a genuine **fail-OPEN** correctness bug.

Candidate sites audited: `cog_routing.py`, `cleanup.py`, `roles.py`,
`role_templates.py`, `handlers.py`, `panels.py`, `final_review.py`
(against the known-benign `moderation.py` L232 reference), plus a
re-scan of `essential_steps.py` / `launcher.py` / `wizard.py`.

## Audit finding

**No fail-open.** Every audited "count / list soft-fail" swallow is
BENIGN. The invariant holds uniformly: the write (`section_card.
stage_custom` — a real `DraftStore.add` that commits and returns) sits in
its OWN `try` that fails CLOSED (returns `BLOCKED` on failure); the
count/list read is a SEPARATE call in a SEPARATE `try` reached only AFTER
the commit, so its swallow cannot mask the write. Two structural
contrasts confirm the shape:

- `final_review.complete_delete` L926 — the staged-ops count is a
  destructive-delete GUARD, not a display feed: a count read failure
  fails CLOSED (`BLOCKED`), never proceeds on a degraded 0.
- `handlers.reset_view` L183 / `final_review.final_apply` L755 — the
  count/list read runs BEFORE the mutation as a decision gate and its
  swallow is either a benign no-op ("already empty") or a fail-CLOSED
  refusal, never a masked write.

Per-site verdicts live in the PR body's Findings table.

## Deliverable

New `tests/unit/setup_band/test_setup_softfail_boundaries.py` —
characterization pins that PIN the current benign behavior of each
audited swallow: with a REAL draft store recording the row, the count
read is forced to RAISE and the handler still answers SUCCESS with the
write's effect persisted (success is real; only the display count
degrades). Additive, DB-free, zero product-behavior change — mirrors the
moderation-except / settings-write harnesses.

## Verification

- `pytest tests/unit/setup_band/ -q` → pasted verbatim in the PR body.

## 💡 Session idea

The audit confirmed the whole setup band shares ONE staging shape:
`stage_custom` (own fail-CLOSED try) → `mark_step_in_progress` →
`staged_ops_count` (own soft-fail try) → confirm. That regularity is
worth a one-line structural lint idea: a checker that flags any
`staged_ops_count` / `_staged_ops` call that is NOT the sole statement in
its `try` (i.e. shares a `try` with a `stage_custom` / `store.add`)
would catch a future fail-open at the source instead of relying on a
hand audit. Cheap to prototype against `sb/domain/setup/` first.

## ⟲ Previous-session review

Reviewed the direct predecessor #516
(`test: pin setup-band except-boundary behavior (backlog C1)`), which
pinned the FOUR `except Exception` swallows in `moderation.py`
(`test_setup_moderation_except_boundaries.py`) — establishing the
harness (DB-free, `_FakeStore` reflecting added rows, `staged_ops_count`
monkeypatched) and the reference verdict (`moderation.py` L232 count
read rides after the committed `stage_custom` — benign). This slice
extends that exact harness to the remaining candidate files named in the
#513 production-readiness backlog. The #516 pin reads clean and its
`test_count_read_failure_still_answers_success_with_zero_pending` is the
template this suite generalizes across `cog_routing` / `cleanup` /
`roles` / `role_templates` / `final_review` / `panels`.
