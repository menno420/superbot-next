# 2026-07-11 — substrate-kit upgrade v1.8.0 → v1.9.0 (distribution wave)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · maintenance (Q-0194)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.8.0 to v1.9.0 using the pinned,
sha256-verified release asset (tag v1.9.0 @ kit commit 2a779b5, release
run 29139623697, sha256 55181082…adfb9cc90 — verified against the
adjacent release.json by the upgrade engine itself). Kit-owned files
only; no domain work, no control/inbox or control/status edits.

## What shipped

1. **bootstrap.py v1.8.0 → v1.9.0** — canonical path (staged
   `bootstrap.py.new` + `release.json` in repo root, `python3
   bootstrap.py.new upgrade`); the engine printed `verified: sha256 +
   version against release.json` and self-cleaned both inputs. Old copy
   banked as `.substrate/backup/bootstrap-1.8.0.py` — exactly one new
   backup; all pre-existing banks byte-identical (before/after
   sha256-verified).
2. **Search-hygiene plants** — new `.ignore` + `.gitattributes` (2
   entries each: `/bootstrap.py`, `/.substrate/backup/`) under the kit's
   provenance marker. Idempotency verified by a second upgrade pass:
   `kept: … already present`, files byte-identical.
3. **`.sessions/README.md` regenerated from the v1.9.0 compose** — the
   live copy was stale old-template output: label-only markers, missing
   the config-required `📊 Model:` marker and all needle byte-forms. The
   regen adds the exact byte-forms, the ORDER 012 family-level
   model-attribution doctrine, the auto-draft paragraph, and guard
   recipes. No host-authored content existed to preserve.
4. **Staged regens** under `.substrate/` (claude/CLAUDE.md with the
   grep-hygiene note, skills, agents, hooks, ci/substrate-gate.yml with
   the `--added-card` grammar-lint lane + auto-merge-enabler.yml —
   staged only; this repo has no live gate by design).
5. `substrate.config.json` → `kit_version: 1.9.0`.

## Verification

- `python3 bootstrap.py check --strict` → exit 0 (one advisory,
  never-exit-affecting, pre-existing: owner-ask-wall-unrecorded on
  control/status.md — lane-owed, not touched here).
- `python3 -m pytest tests/ -q` → 1295 passed, 2 skipped.
- SessionStart handoff push exercised live: `bootstrap.py hook
  sessionstart` now prints "## Handoff — the previous session's trail
  (pushed…)" with the newest card path + status + read-first pointer.
- v1.9.0 plant-time `automerge.required_context` validation fired
  (informational): 'substrate-gate' matches no job context here — this
  repo lands via REST merge on green required checks; no enabler live.
- First-exercise note: the born-red "HOLD (by design)" notice did NOT
  fire on this repo — its folded-gate CI runs bare `check --strict`,
  which resolves the newest card by mtime; in a fresh CI checkout it
  read a sibling complete card (the known strict-check-mtime class), so
  the in-progress card never held CI red. The HOLD notice remains
  unexercised on superbot-next.

## 💡 Session idea

The bare `check --strict` newest-card-by-mtime resolution is
nondeterministic in fresh CI checkouts (this session: CI graded
`cleanup-parity-flip` while the PR's own card sat in-progress). Kit
idea: resolve the newest card by filename date + git added-in-PR
awareness instead of mtime, so folded-gate repos get deterministic
born-red semantics without a live substrate-gate.yml.

## ⟲ Previous-session review

Previous session (proof_channel parity flip, PR #145) left a clean,
complete card with an exemplary evidence trail — its renderer_override
precedent notes made that card genuinely reusable. Improvement this
session surfaces: its telemetry row left `merged_pr` null even after
merge; a close-out step that backfills outcome fields would make the
model-usage corpus analyzable.

- Next session should know: superbot-next is on kit v1.9.0; the
  control/status.md `kit:` heartbeat line still says the old version and
  the bump is lane-owed (distribution workers do not touch control/).
