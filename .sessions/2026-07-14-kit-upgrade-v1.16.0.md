# 2026-07-14 — kit upgrade v1.16.0

> **Status:** `complete`

Upgraded vendored substrate-kit 1.15.0 → 1.16.0 (asset sha256 three-way verified: computed == release.json field == coordinator pin `bba34e21…9170`, 980,026 B), then ran the mandatory second pass `upgrade --apply-docs`.

- **📊 Model:** fable-5 · medium · mechanical refactor

## What shipped (PR #483)

- `bootstrap.py` 1.15.0 → 1.16.0; `.substrate/backup/bootstrap-1.15.0.py` banked (sha256 `25d22af9…650e` == the v1.15.0 release asset); all pre-existing banks byte-identical.
- `--apply-docs` applied 4 template-improved docs: `CONSTITUTION.md`, `docs/SKILLS.md`, `docs/ROUTINES.md`, `control/claims/README.md`. capability-seed + seat-digest both "already current".
- New v1.16.0 plant `docs/reading-path.md` (fleet reading path): its three interview slots (`fleet_status_command`, `fleet_dark_repos`, `fleet_siblings`) answered from documented fleet truth (superbot Q-0272 route; pokemon-mod-lab is the only dark repo) + `render --live` — decide-and-flag, correct in place if any row drifts. Minimal wiring hunk hand-merged into the diverged `docs/AGENT_ORIENTATION.md` (doc-list entry + routing paragraph, v1.13.0/v1.15.0 precedent) to clear the `[reachable]` orphan.
- Gate carve-out handled per Q-0261.3: the kit regen DROPPED the host-added enabler step ("Skip arming while the PR's own in-diff session card is in-progress", landed at PR #479) — `.github/workflows/auto-merge-enabler.yml` restored byte-identical to origin/main; the kit's pre-regen bank committed at `.substrate/backup/auto-merge-enabler.pre-regen-00170bc1.yml` as the audit artifact.
- Verify: `python3 -m pytest` 3119 passed / 15 skipped; `bootstrap.py check --strict` green apart from this card's designed born-red hold.

## Lane-owed follow-ups (guard recipes)

- Heartbeat bump: `control/status.md` `kit:` line → v1.16.0 (distribution scope excludes control/status.md; keep the token PLAIN — `KIT_LINE_RE`, kit `src/engine/grammar.py`).
- Hand-merge diverged-doc deltas from `.substrate/upgrade-report.md` § Template deltas: `docs/collaboration-model.md` (rationalize-checkpoint sentence + PL register refresh), `docs/AGENT_ORIENTATION.md` (rest of the template delta beyond the wired hunk), `docs/CAPABILITIES.md` (fleet master-copy path casefix `docs/capabilities.md` → `docs/CAPABILITIES.md`).
- New `[automerge-branch-drift]` advisory: the live enabler arms {claude/*, docs/*, fix/*, mining/*, port/*, test/*} but `substrate.config.json automerge.branch_patterns` regenerates only {claude/*} — put the host branch list in the config so the next kit regen stops dropping it (same class as the dropped host step; one config edit kills both recurrences).
- `check` now NOTES `scripts/preflight.py` missing (new v1.16.0 `preflight_scripts` config default) — plant one or empty the config list.
- Ten pre-existing `[model-line-shape]`/`[model-line-class]` advisories on 2026-07-14 sibling cards (three-field `📊 Model:` payload) — advisory-only, sibling lanes own their cards.

## 💡 Session idea

The upgrade engine already detects host-added steps in kit-owned workflows and banks the pre-regen copy — but it still *overwrites* the live file, forcing every host-customized adopter (this repo's enabler, idea-engine's gate preflight) to hand-restore from origin/main each wave. Teach the regen to emit the regenerated template to `.substrate/ci/` only and leave the live carve-out-carrying file untouched (report line instead of overwrite): same audit trail, zero restore step, removes the highest-recurrence manual action left in distribution waves.

## ⟲ Previous-session review

The v1.15.0 upgrade session (#294 @ bd0fd17) left an excellent trail — its card's lane-owed list and the "examples/ collection error is a local-env artifact" note were both load-bearing here. One gap: it recorded the `automerge.required_context 'substrate-gate'` mismatch as its session idea, but nobody routed it — this session the context question resurfaced (a live gate landed at #479). Improvement: session ideas that name a one-line config fix should land as the fix in the same session (decide-and-flag) rather than as an idea; the idea lane is for work that needs design.
