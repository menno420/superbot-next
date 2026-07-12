# 2026-07-12 — kit upgrade v1.13.0 → v1.14.0

> **Status:** `complete`

- **📊 Model:** Fable 5 · distribution worker (kit upgrade wave)

## Scope

Upgraded the vendored substrate-kit bootstrap from v1.13.0 to v1.14.0
(release tag `v1.14.0` = kit commit `2fabf3e`, asset sha256
`47c1b8b954be2f587d88f7ed5923870883deab88a8fa7fbf2bb755decc2ee581`,
779,399 bytes, three-way verified: downloaded asset = release.json =
kit origin/main `dist/bootstrap.py`). Distribution-only session: no
lane/domain work, no control/inbox or control/status writes.

## What shipped

- `bootstrap.py` v1.13.0 → v1.14.0; `substrate.config.json`
  kit_version 1.14.0; previous version banked in-tree at
  `.substrate/backup/bootstrap-1.13.0.py`.
- `python3 bootstrap.py upgrade --apply-docs` second pass applied the
  two template-improved, consumer-untouched docs: `CONSTITUTION.md`
  (owner-assist output standard) and `docs/SKILLS.md` (+ new
  `.substrate/skills/intake/SKILL.md` staged by the kit).
- Capability-seed refresh: the v1.14.0 venue-scoped seed fence
  (`substrate-kit:capability-seed BEGIN/END`) was installed into
  `docs/CAPABILITIES.md` by the upgrade pass; the apply-docs pass then
  reported "fence already current — nothing to refresh". No
  "hand-adopt once" legacy-ledger line appeared.
- Carve-outs: none — report says "no kit-owned live workflow
  installed, nothing to scan."
- Verify: `python3 bootstrap.py check --strict` exit 0 (only red-class
  line is this card's designed born-red hold); `python3 -m pytest
  tests/ -q` → 1729 passed, 13 skipped.

## Lane-owed follow-ups (from .substrate/upgrade-report.md — not failures)

- Diverged (manual merge owed by lane sessions):
  `docs/collaboration-model.md`, `docs/question-router.md`,
  `docs/CAPABILITIES.md`, `control/README.md` — template deltas are
  recorded verbatim in `.substrate/upgrade-report.md`.
- Consumer-edited (consumer-owned, nothing to apply):
  `docs/decisions.md`, `docs/repo-navigation-map.md`,
  `docs/current-state.md`, `docs/ideas/README.md`,
  `control/inbox.md`, `control/status.md`.
- Q-0270-collapse note (expected on this superbot-family repo, left
  lane-owed): "If this repo carries a local prose copy of the
  boot-triad/venue-posture rule (superbot Q-0270), that copy is now
  superseded by docs/CAPABILITIES.md's posture rule — collapse the
  local copy into a pointer."
- New advisory fired by v1.14.0's checker (never exit-affecting):
  `[owner-action-risk-class] control/status.md: 3 ⚑ OWNER-ACTION
  block(s) carry no risk-class token` — control/status.md is
  coordinator-owned, so this is lane-owed, not fixed here.
- Upgrade log note: `automerge.required_context 'substrate-gate'
  matches no job in .github/workflows/` — expected; this repo's folded
  `gate` job replaces a live substrate-gate. Lane may pin
  `substrate.config.json → automerge.required_context` to `gate` if
  the label bothers anyone (informational only).

## 💡 Session idea

The upgrade-report's "Template deltas for diverged docs" section is
already exact unified diffs — a tiny kit affordance (`bootstrap
upgrade --emit-patches` writing each delta as a `.patch` file) would
let lane sessions `git apply --3way` the owed manual merges instead of
hand-transcribing hunks from a markdown code fence, which is where
transcription drift creeps in across a 5-repo wave.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-program-review.md`, the newest completed
card at branch time.) Strong pattern worth keeping: it pinned every
headline count to the audited HEAD (`c792079`) and explicitly flagged
that main moved during assembly — that discipline is exactly what made
this session's preflight trustworthy. Improvement it surfaces: the
review noted golden-parity's born-red `report` job needs a
"read-this-first" pointer wherever CI is interpreted; this session hit
the same class (a red that is by-design) and had to rely on the
distribution playbook rather than anything in-repo near the check
itself — a one-line annotation in `golden-parity.yml` next to the
`report` job name would make the by-design red self-describing.
