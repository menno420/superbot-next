# 2026-07-12 — kit upgrade v1.15.0

> **Status:** `complete`

Upgraded vendored substrate-kit 1.14.0 → 1.15.0 (release commit eaf4f23; asset sha256 three-way verified against the release.json field, the pinned coordinator value, and the kit's committed dist), then ran the `--apply-docs` pass.

📊 Model: fable-5

## What shipped (PR #294)

- `bootstrap.py` 1.14.0 → 1.15.0; `.substrate/backup/bootstrap-1.14.0.py` banked; all pre-existing bank files byte-identical.
- `--apply-docs` applied 3 template-improved docs: `CONSTITUTION.md`, `docs/SKILLS.md`, `.claude/CLAUDE.md`.
- Planted: `docs/ROUTINES.md` (new ADOPT_PLAN doc) + `docs/seat-digest.md` (reported "already current" by both passes).
- Hand-merged ONLY the minimal ROUTINES.md wiring hunk into the diverged `docs/AGENT_ORIENTATION.md` (doc-list entry + routing paragraph, v1.13.0 precedent) to clear the `[reachable]` orphan red.
- Carve-outs recorded verbatim in the PR body: 8 consumer-edited, 3 diverged (`docs/AGENT_ORIENTATION.md`, `control/README.md`, `control/status.md`) — diverged template deltas stay lane-owed.
- Verify: `python3 -m pytest tests/` 1749 passed / 13 skipped; `bootstrap.py check --strict` green apart from this card's designed born-red hold.

## Lane-owed follow-ups (guard recipes)

- Heartbeat bump: `control/status.md` `kit:` line → v1.15.0 (distribution scope excludes control/status.md; keep the token PLAIN — `KIT_LINE_RE`, kit `src/engine/grammar.py`).
- Hand-merge remaining diverged-doc deltas from `.substrate/upgrade-report.md`: AGENT_ORIENTATION preflight section; `control/README.md` + `control/status.md` `kit:`-grammar/version-truth paragraphs.
- If a local prose copy of the Q-0270 boot-triad/venue-posture rule exists, collapse it into a pointer to `docs/CAPABILITIES.md`'s posture rule (upgrade-report note).

## 💡 Session idea

The upgrade path emits `automerge.required_context 'substrate-gate' matches no job` on every run in this repo (contexts here are `gate`, `checkers`, …). Set `substrate.config.json -> automerge."required_context"` to this repo's actual required context so the repo-settings checklist and enabler log lines stop mislabeling — one-line config fix, kills a recurring warning every future upgrade session re-reads.

## ⟲ Previous-session review

The v1.14.0 upgrade session (2026-07-12, landed #260 @ 764a393) left a clean trail: its card recorded the guard-fires.jsonl union-merge precedent, which this session leaned on when checking mergeability. One improvement it could have made: recording the exact CI-scope pytest invocation (`pytest tests/ -q`, not bare `pytest`) in its card — this session re-derived that the `examples/` collection error is a local-env artifact from the workflow files; now recorded here so the next kit session doesn't repeat the derivation.
