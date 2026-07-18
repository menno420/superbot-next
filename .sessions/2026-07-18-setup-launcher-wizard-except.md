# 2026-07-18 — setup launcher/wizard except boundaries (finish C1)

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · test writing · except-boundary characterization pins (C1 final slice)

## Scope

The LAST uncovered setup-band `except Exception` sites — closing backlog
item C1 (the setup-band except-density audit). Prior slices covered
`moderation.py` (#516), the count/list soft-fail family (#519), and
`final_review.py` + `essential_steps.py` (#526). This slice reaches the two
files those left as an explicit deferral:

- `sb/domain/setup/launcher.py` — the 9 `except Exception` swallows across
  the render (L225), the join workspace/fallback lane (L303, L349) and the
  button handlers (advisor L490, mark-in-progress L511, summary read L527,
  repost refresh L570). L310 (`ensure_setup_channel`) and L423 (handler
  isolation) are already pinned by `test_guild_join_launcher.py`.
- `sb/domain/setup/wizard.py` — the 7 `except Exception` swallows: the gate
  ladder (session read L391, owner-directory read L404), the panel refresh
  (L552), the depth handler (L619), essential_save apply (L747), and the two
  review reads/writes (rerun L859, stage L897). L391, L619 and L747 are
  already pinned by `test_wizard_interior.py`.

## Audit finding

**No fail-open.** Every launcher/wizard swallow pins to its intended shape:

- fail-CLOSED (surfaces a `BLOCKED` refusal): the launcher advisor read
  (L490), the wizard deterministic-rerun read (L859), the wizard staging
  write (L897).
- fail-SOFT / degrade: the launcher render session read → the fresh card
  (L225), the join session read → no prior pointers / posts fresh (L303),
  the channel-directory read → "no sendable channel" `None` (L349), the
  summary session read → the not-complete refusal (L527, the conservative
  degrade — an unreadable session never shows a summary), and the gate's
  owner-directory read → deny (L404, an unreadable owner is a closed door).
- best-effort / logged-never-raised: the launcher `mark_in_progress` marker
  (L511) and `start_session` refresh (L570), and the wizard panel refresh
  (L552) — a failure is logged and swallowed; the surface still answers and
  NO write is masked (each guards a trailing marker/refresh/re-render whose
  primary mutation already committed or never ran).

## Deliverable

New `tests/unit/setup_band/test_setup_launcher_wizard_except_boundaries.py`
— 11 characterization pins that force each uncovered guarded call to raise
and assert the observed boundary (degrades / logged-and-continues /
refuses). Additive, DB-free, zero product-behavior change — mirrors the
sibling `test_setup_final_review_and_essential_except_boundaries.py` (#526)
harness. C1 (the setup-band except-density audit) is now fully complete:
every `except Exception` in the setup band is pinned to its boundary.

## Verification

- `pytest tests/unit/setup_band/ -q` → `468 passed in 3.73s` (the new file
  alone: `11 passed in 0.24s`).
- PR CI: functional gates expected green; `substrate-gate` the sole red —
  the born-red hold, cleared by this card flip.

## 💡 Session idea

C1 is now a four-file harness (`moderation` / soft-fail / final_review+
essential / launcher+wizard), all sharing ONE assertion vocabulary: force
the guarded call to raise, pin the outcome to fail-CLOSED `BLOCKED` /
logged-never-raised / fail-SOFT degrade. The #526 card already floated the
`assert_boundary(reply, shape=...)` helper; with the whole band now pinned,
a follow-up slice could extract that helper across all four files AND add a
lightweight guard test that asserts EVERY `except Exception` in `sb/domain/
setup/*.py` has a matching characterization pin (an AST count vs a test
registry) — so a NEW swallow lands red until its posture is declared,
turning C1 from a one-time audit into a standing invariant.

## ⟲ Previous-session review

Reviewed the direct predecessor #526
(`test_setup_final_review_and_essential_except_boundaries.py`), which pinned
the `final_review.py` + `essential_steps.py` remainder and explicitly
deferred `launcher.py` (~9) and `wizard.py` (~7) as "a coherent next slice."
This slice picks up exactly that deferral with the same DB-free,
monkeypatched-seam harness. The #526 pin reads clean; its three-shape
vocabulary (fail-CLOSED / logged-never-raised / fail-SOFT) transferred
one-to-one, and its `_open_gate` / `_Gate` monkeypatch template is the shape
this suite reuses for the gated review/summary/repost lanes.
