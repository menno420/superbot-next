# 2026-07-18 — setup-band except-boundary tests: pin the moderation-flow swallows (backlog C1)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · additive test slice (born-red, holds substrate-gate)

## Scope

Prod-readiness backlog item **C1** — the "setup-band except-density
audit". `sb/domain/setup/*` carries ~110 real `except` handler sites
across 21 modules (the survey below); every wide swallow is
`# noqa: BLE001`-annotated with an oracle-faithful soft-fail rationale,
but the BOUNDARY behavior (what the handler actually does when the
guarded op RAISES) has almost no unit coverage — the existing
`tests/unit/setup_band/*` suites drive the happy paths and the gate
refusals, never the except arm.

This slice is deliberately CONTAINED and purely additive: NO product
behavior changes (a behavior change to a swallow needs its own reviewed
slice), just characterization tests that PIN the current boundary. New
test file only ⇒ cannot regress anything. It stays locally verifiable
(unit only — full golden parity does not run locally).

### Survey — `except` handler sites per setup module (real handlers, `bootstrap.py`/`.substrate` excluded)

`final_review.py` 15 · `essential_steps.py` 14 · `launcher.py` 11 ·
`section_card.py` 7 · `wizard.py` 8 · `cleanup.py` 8 · `wizard_nav.py`
8 · `cog_routing.py` 6 · `channels.py` 6 · `logging_presets.py` 4 ·
`moderation.py` 4 · `roles.py` 5 · `recovery.py` 3 · `ops.py` 4 ·
`resume.py` 3 · `preset_select.py` 5 · `role_templates.py` 3 ·
`panels.py` 3 · `notices.py` 1 · `handlers.py` 3 · `service.py` 1.
Grouped by posture: the vast majority are **fail-CLOSED** (surface a
`Reply(BLOCKED, …)` refusal / return a failure result) or informational
**fail-SOFT** (a read-only snapshot degrades to `None`/`0` and can never
block a render — the annotated intent). No fail-OPEN write-swallow (a
real write error silently reported as success) was found in the audited
`moderation.py` cluster; the wider sweep is a follow-up (see 💡).

## Deliver — pin `moderation.py`'s four swallows

`sb/domain/setup/moderation.py` is the most cohesive uncovered cluster:
four real `except Exception` sites, all in two functions, none with
boundary coverage. New file
`tests/unit/setup_band/test_setup_moderation_except_boundaries.py`
characterizes each:

- **L224 `_stage_setting` — `section_card.stage_custom` raises** ⇒
  `Reply(BLOCKED, "Could not stage the moderation setting — see logs.")`.
  **Fail-CLOSED** and pinned: the write error is surfaced as a refusal,
  never reported as a staged success.
- **L232 `_stage_setting` — `wizard.staged_ops_count` raises** ⇒ still
  `SUCCESS`, `pending` degrades to **0**. The stage already committed;
  the count is display-only. Informational fail-soft, pinned.
- **L172 `read_current_state` — `load_policy` raises** ⇒ the three
  policy values degrade to `None`. Read-only snapshot, never blocks.
- **L181 `read_current_state` — settings `resolve` raises** ⇒
  `moderator_role_id` degrades to `None`; the other three still read.

## Verification

- `python3 -m pytest
  tests/unit/setup_band/test_setup_moderation_except_boundaries.py
  tests/unit/setup_band/test_settings_write_flows.py -q` → green
  (verbatim summary in the PR body). Full `tests/unit/` NOT run here —
  this container has a pre-existing `yaml`-module gap + pytest-randomly
  ordering pollution that makes the whole-suite run a non-signal; the
  CI named-gates carry the authoritative sweep.

## 💡 Session idea

Extend the same characterization pattern to the higher-density modules
next — `final_review.py` (15 sites, several `# oracle: logged, never
raised` contracts worth a boundary pin) and `launcher.py` (11, the
`headless/no DB ⇒ fresh card` degrade class). And AUDIT-flag for a
follow-up owner-reviewable slice: sweep every `# the shipped count
soft-fail` / `# the shipped list_ops soft-fail` site (they appear in
`cog_routing`, `cleanup`, `roles`, `role_templates`, `handlers`,
`panels`, `final_review`) to confirm each really rides AFTER its
paired write commit — a count/list swallow that wrapped the write too
would be a genuine fail-OPEN. The moderation cluster is clean on this
(L232 fires strictly after L222-223's committed `stage_custom`); the
others were not individually re-verified in this slice.

## ⟲ Previous-session review

Reviewed the predecessor `.sessions/2026-07-17-ensure-only-registration-
sweep.md` (#508 class), which retired the last `_KNOWN_ENSURE_ONLY`
burn-down entry (`panel:role.hub`) by lifting its `@panel` factory out
of `ensure_panel_refs()` into a module-import `_register_hub_factory()`,
emptying the set so `test_burn_down_entries_are_still_real` becomes a
pure floor. The fix reads clean and its 💡 (a docstring note so a future
author does not re-add an exemption row) is a sound low-cost follow-up.
It confirms the setup/role bands are the current hardening frontier —
this C1 except-boundary slice picks up an adjacent seam in the same
band, from the prod-readiness backlog rather than the ensure-only
ledger.
