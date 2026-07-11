# 2026-07-11 — kit upgrade v1.7.1 → v1.8.0

> **Status:** `complete`

📊 Model: claude-fable-5

## Scope

Distribution session: upgrade the vendored substrate-kit from v1.7.1 to
v1.8.0 (release tag `v1.8.0`, kit commit 63c6b39). Kit-owned files only —
no domain/parity work, `control/inbox.md` and `control/status.md` untouched.

## What happened

- Downloaded `bootstrap.py` + `release.json` from the v1.8.0 release;
  sha256 `28c5dcb6…c89b9b` and size 625,066 verified against `release.json`
  before running; the upgrade itself re-verified ("verified: sha256 +
  version against release.json").
- `python3 bootstrap.py.new upgrade` — old v1.7.1 dist archived as
  `.substrate/backup/bootstrap-1.7.1.py` (one new backup, no collisions);
  `kit_version` → 1.8.0 in `.substrate/state.json` + `substrate.config.json`.
- New v1.8.0 plants: `control/claims/README.md` (unified work-claim
  convention), `scripts/env-setup.sh` (setup-script contract,
  skip-if-exists). Auto-merge enabler STAGED at
  `.substrate/ci/auto-merge-enabler.yml` only — NOT installed live (this
  repo has no live substrate gate by design; `adopt --wire-enforcement`
  would install it).
- `control/README.md` was `diverged` (host edits + template moved): applied
  the template delta manually — the "Claiming work" `control/claims/`
  routing section + three "Grammar source of truth" pointers
  (`src/engine/grammar.py`, EAP §6.8).
- `.substrate/upgrade-report.md` carries the new explicit-when-clean
  carve-out section: "carve-out scan: ran — no kit-owned live workflow
  installed, nothing to scan." (first live exercise of kit #156 fix 1).
- Verified: `python3 bootstrap.py check --strict` exit 0 (one pre-existing
  advisory: `owner-ask-wall-unrecorded` on `control/status.md` — out of
  this session's scope, status.md is not mine to write); full unit suite
  1261 passed / 2 skipped; manifest compile + committed checker fleet all
  green under the CI commands.

## Notes for the next session

- The `kit:` heartbeat line in `control/status.md` still says the old
  version — the lane owner should set `kit: v1.8.0 · check: green ·
  engaged: yes` in its next status overwrite (adopter checklist step 4;
  this distribution session is barred from writing status.md).
- The pre-existing `owner-ask-wall-unrecorded` advisory (OWNER-ACTION 3
  wall not recorded in `docs/CAPABILITIES.md`) is still open.

💡 Session idea: the upgrade report's "diverged — manual merge" class could
carry a ready-to-apply patch file under `.substrate/backup/` (the template
delta is already computed for the report); an agent could then `git apply`
it instead of hand-replaying hunks against host edits — cheaper and less
error-prone for every future diverged plant.

⟲ Previous-session review: the previous session
(2026-07-11-servermanagement-parity-flip / blackjack tournament band-6 work,
#132–#134) shipped parity flips with goldens green and kept the status
heartbeat current — clean. One workflow improvement it surfaces: its cards
carry the enders inconsistently across the two 2026-07-10 ux-lab card
duplicates (`ux-lab-parity-flip` vs `uxlab-parity-flip`, one missing the 💡
and ⟲ enders — the kit's session-log guard fires on it every check run);
pruning the stray duplicate card would silence a recurring blocking-posture
guard-fire.
