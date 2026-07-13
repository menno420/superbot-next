# 2026-07-13 — setup wizard interior (ORDER 017 night-run slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1
  (top gap 2: "setup wizard interior — the whole interactive wizard is
  pending")

## Scope

Arm the setup wizard's interior — the 10 pending panel actions + 1
selector counted by `docs/status/completeness-table-2026-07-13.md`
(`sb/domain/setup/panels.py:125-128`) plus the `/setup-skip` /
`/setup-unskip` mark-skipped write (`handlers.py:207-221`) and the
`/setup-reset` clearing branch — faithful to the oracle
(menno420/superbot: `views/setup/depth_panel.py`,
`views/setup/essential_setup.py`, `views/setup/hub.py`,
`views/setup/ai_review/main_panel.py`, `cogs/setup_cog.py`), keeping
every golden-pinned open-render byte identical (no golden drives a
click on any of these components — the module's own pin).

Named successors stay honest terminals: the essential flow's steps 2–8,
the per-section flows behind the hub's section buttons, the
per-suggestion Edit modal/repick flow, and the final-review apply lane.

## What shipped

- `sb/domain/setup/wizard.py` (new) — the wizard interior: the shipped
  starter-set/XP-rate/section-depth data verbatim, the in-memory
  essential-pick + review state (the oracle `AcceptedSet` port), the
  `can_apply_setup` ladder (platform owner / server owner / delegated
  admin, fail-closed), the K9 staging lane
  (`replace_recommended_for_section` semantics over `DraftStore`, op-kind
  `bind_channel` → `settings.bind`), and all 22 interior click handlers.
- `sb/domain/setup/store.py` + `ops.py` — `set_depth` /
  `set_section_skip` write primitives (oracle SQL shapes) behind two new
  K7 ops (`setup.set_depth`, `setup.set_section_skip`); the K7 audit rows
  are additive vs the oracle (ledgered in ops.py).
- `sb/domain/setup/panels.py` — the 10 actions + selector repointed off
  `setup.wizard_pending` onto the live handlers; two new panels
  (`setup.sections_hub`, `setup.review_item`) with state-composed
  renderer overrides (hub.build_hub_embed / per-recommendation embed,
  oracle bytes); essential renderer now renders the picked Starter-set
  field; suggestions renderer carries the shipped confidence accent +
  last-action footer.
- `sb/domain/setup/handlers.py` — `/setup-skip`/`/setup-unskip` write for
  real (gate → golden-pinned slug refusal → K7 op → shipped ack);
  `/setup-reset` clearing branch retires its constant-empty read
  (count/clear over the K9 drafts, shipped copy).
- `manifest/layout/setup.lock.json` + `sim/sim-gate-baseline.json` —
  legacy-seed Exempt pins for the two new panels' arrangements (oracle
  rows cited); `manifest.snapshot.json` recompiled.
- `tests/unit/setup_band/test_wizard_interior.py` — 41 DB-free tests
  pinning the oracle click-path copy + renders; plus a DB-backed harness
  drive (evidence in the PR body). Golden-pinned OPEN renders stay
  byte-identical (full parity replay green).

Named successors kept honest (declared BLOCKED terminals): essential
steps 2–8 · the 10 per-section flows + linear wizard steps · the
per-suggestion Edit lane · the final-review apply lane.

Verification (close-out): pre-merge tree `pytest tests/` **2107
passed, 2 skipped** (exit 0, clean run — an earlier red was
cross-process contamination: harness drives sharing `parity_replay`
with a concurrently replaying suite; dbsnap truncates per case).
Post-merge (peer lanes fishing-slice2 / diagnostic-mutations /
curation / game-sections): 2132–2133 passed with 6–7 integration
RACE-test failures from the ledgered local-env flake class (varying
set run-to-run, none in this slice's domain — the
treasury-karma-argv-fix card's known class; CI's required bar is the
authority). `bootstrap.py check --strict` green; `check_sim_gate`
OK; `manifest_compile` verify green. End-to-end harness drive +
adversarial probes recorded in PR #340's body.

**Guard recipe** (for the flake class): the integration race tests
(`tests/integration/test_*_race.py`) share the `parity_replay` DB
with any concurrently running harness/replay process — serialize all
DB-touching runs in one session (one `pytest tests/` at a time, no
harness drives alongside), or they fail with vanished-row phantoms
(`dbsnap` TRUNCATE … CASCADE per replay case).

## 💡 Session idea

The presentation seam is now the wizard's only material divergence: the
oracle swapped views in place (`edit_message`) while `open_panel`
navigation sends a NEW message (the #295 precedent). A small engine lane
— `open_panel(..., replace_message_ref=...)` that re-uses the session's
anchor like `refresh_session_view` does — would make every ported
navigation byte-faithful in place, and retire the per-slice ledger notes
about it.

## ⟲ Previous-session review

Previous night-run slice (completeness table, PR #326) produced the gap
ledger this slice consumes — its row for `setup` counted the exact
surfaces armed here, and its "zero unregistered refs" sweep result held
when this session re-ran `ENSURE_REFS` over the setup manifest. Its
watch-item about `.substrate/guard-fires.jsonl` dirt is honored below
(restored before every commit).
