# 2026-07-18 — setup-band except-boundary remainder (final_review + essential_steps) + stale wizard docstring fix

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · test writing · except-boundary characterization pins (C1 remainder)

## Scope

The C1 remainder: extend the setup-band `except Exception` characterization
pins (#516 `moderation.py`, #519 count/list soft-fail family) to the two
files the reconciliation still lists as uncovered:

- `sb/domain/setup/final_review.py` — the best-effort / "logged-never-raised"
  swallow arms plus the fail-CLOSED / fail-SOFT boundaries that lacked
  dedicated tests (restage-remainder L459, `_mark_complete` L476, recovery
  render L694, apply/retry staged-ops reads L755 & L852, session read L915,
  channel-resolve L958, pointer-clear L1021).
- `sb/domain/setup/essential_steps.py` — its ~13 `except Exception` sites,
  only ~2 of which were force-raise-tested before this slice.

Plus a trivial docstring-only fix: `wizard.py:106-113` still claimed the
compound-op apply seams (`create_managed_role` / `create_channel` /
`set_cog_routing` / `add_rule`), the automation-rule apply seam and the
windowed-select successor were open / "apply fail-closed as skipped until
their seams exist." The 2026-07-13 compound-ops slice landed those and they
apply for real (the sibling `role_templates.py` / `logging_presets.py` /
`cog_routing.py` docstrings already say "resolved").

## Audit finding

**No fail-open.** Every `final_review.py` / `essential_steps.py` swallow
pins to its intended shape:

- fail-CLOSED (surfaces a `BLOCKED` refusal): the apply / recovery-retry
  staged-ops reads (L755 / L852), the complete-delete session read (L915),
  and every essential `_save` write try (greet / mods / spam / log / reward /
  helpdesk / commands).
- best-effort / logged-never-raised: `_restage_remainder` (L459),
  `_mark_complete` (L476), `_clear_workspace_pointers` (L1021),
  `persist_progress` (L365) — a failure is logged and swallowed; the summary /
  outcome surface still answers, and NO write is masked (the mutation each
  guards already committed or already raised on non-SUCCESS).
- fail-SOFT / degrade: the recovery + resume renders degrade to the empty /
  step-1 default (L694 / L1369), the health read degrades to "nothing
  configured" (L532), the create-channel / create-role ports degrade to
  `None` (L443 / L472), and the channel-resolve on `complete_delete` (L958)
  degrades an unreadable cache to the "already gone" branch (clears the
  pointer, answers SUCCESS — it NEVER deletes, so no destructive action and
  no falsely-reported write).

## Deliverable

New `tests/unit/setup_band/test_setup_final_review_and_essential_except_boundaries.py`
— characterization pins that force each guarded call to raise and assert the
observed boundary behavior (degrades / logged-and-continues / refuses).
Docstring-only edit to `wizard.py`. Additive, DB-free, zero product-behavior
change — mirrors the moderation-except / count-list soft-fail harnesses.

Deferred (flagged follow-up): `launcher.py` (~9) and `wizard.py` (~7)
except sites remain uncovered — a coherent next slice, kept out of this PR.

## Verification

- `pytest tests/unit/setup_band/ -q` → (recorded on the card flip).
- CI: functional gates green; `substrate-gate` the expected sole born-red
  hold, cleared by this card flip.

## 💡 Session idea

The setup band now has three sibling except-boundary harnesses
(`moderation` / soft-fail / this one). They share ONE assertion vocabulary:
force the guarded call to raise, then pin the outcome to one of three shapes
(fail-CLOSED `BLOCKED` / logged-never-raised / fail-SOFT degrade). A tiny
enum-tagged helper (`assert_boundary(reply, shape=...)`) shared across the
three files would make the intended posture of each swallow self-documenting
in the test, and make a future posture drift (a fail-CLOSED arm quietly
becoming fail-SOFT) a one-line test diff instead of a re-read.

## ⟲ Previous-session review

Reviewed the direct predecessor #519
(`test_setup_softfail_boundaries.py`, the count/list soft-fail audit), which
established that the whole band shares one staging shape (`stage_custom` in
its own fail-CLOSED try → `staged_ops_count` in its own soft-fail try) and
that every audited count/list swallow is benign. This slice picks up its
explicit deferral — the `final_review.py` best-effort / recovery-render arms
and the `essential_steps.py` `_save` family it did not reach — and pins them
with the same DB-free, monkeypatched-seam harness. The #519 pin reads clean;
its `_FakeStore` + `_break_count` template is the shape this suite reuses for
the fail-CLOSED / degrade contrasts.
