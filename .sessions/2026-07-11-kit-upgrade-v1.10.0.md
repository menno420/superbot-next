# 2026-07-11 — substrate-kit upgrade v1.9.0 → v1.10.0 (distribution wave)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · maintenance (Q-0194)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.9.0 to v1.10.0 using the pinned,
sha256-verified release asset (tag v1.10.0 @ kit commit 1b5db16, release
run 29142780212, sha256 ba69fc5c…c2f3b5a4 — three-way verified: asset
hash == release.json, tag → 1b5db16, release run green with this asset
attached). Kit-owned files only; no domain work, no control/inbox or
control/status edits.

## What shipped

1. **bootstrap.py v1.9.0 → v1.10.0** — canonical path (staged
   `bootstrap.py.new` + `release.json` in repo root, `python3
   bootstrap.py.new upgrade --apply-docs`); the engine printed
   `verified: sha256 + version against release.json` and self-cleaned
   both inputs. Old copy banked as `.substrate/backup/bootstrap-1.9.0.py`
   (sha256 55181082… — byte-identical to the v1.9.0 dist) — exactly one
   new backup; all pre-existing bootstrap-*.py banks byte-identical
   (before/after sha256-verified).
2. **Staged gate regen** (`.substrate/ci/substrate-gate.yml`) now carries
   the v1.10.0 session-card-hold payload: an ADDED card rides
   `check --strict --added-card`, whose in-progress verdict is the
   locked-door `session-card-hold` finding (never allowlistable), and the
   gate-regen branch also runs `--simulate-added-card` so the lane stays
   observable. Staged only — this repo has no live substrate-gate by
   design.
3. **`--apply-docs` carve-out survival verified**: the rewritten
   `.substrate/upgrade-report.md` carries its "## Carve-out scan" section
   ("ran — no kit-owned live workflow installed, nothing to scan") — the
   v1.9.0-wave websites regression is fixed.
4. **Retroactive model-doctrine append**: correctly no-oped —
   `.sessions/README.md` is byte-identical (the v1.9.0 regen already
   embedded the doctrine; `_merge_model_doctrine` detected its shared
   phrase and skipped, per the idempotency covenant). No host content
   touched.
5. `substrate.config.json` → `kit_version: 1.10.0`; kit-owned
   guard-fires.jsonl telemetry appended by this session's check runs.
6. **⚑ In-passing (venture-lab #17 precedent): sibling-card grammar
   backfill.** The close-out push went red when CI's bare `check
   --strict` mtime-picked `.sessions/2026-07-11-ticket-parity-flip.md`
   (missing `💡`/review needles) — the sibling-card lottery striking
   live. Six cards carried needle gaps (2× missing `📊 Model:` from the
   pre-doctrine era, 4× missing `💡` + review); each got an explicitly
   provenance-marked, grammar-only backfill (nothing fabricated — the
   Model backfills say `unknown`), and every card in `.sessions/` now
   grades exit 0 individually via `--session-log`, so no future mtime
   pick can red the gate on pre-existing drift.

## Verification

- `python3 bootstrap.py check --strict` → exit 0 at close (mid-session it
  held with the designed born-red HOLD on this card, as v1.10.0 intends;
  the pre-existing owner-ask-wall-unrecorded advisory on
  control/status.md remains lane-owed, not touched here).
- New `check --simulate-added-card <this card>` exercised while
  in-progress: "the added-card lane would HOLD (born-red …)", advisory
  only, exit 0.
- `python3 -m pytest tests/ -q` → 1315 passed, 2 skipped.
- First-exercise data point: the session-card-hold did NOT engage in this
  repo's CI — the folded `checkers` job runs bare `check --strict` with
  no added-card diff detection, and on head 8d7554d it graded a sibling
  complete card (proof-channel-parity-flip) by mtime and passed while
  this card sat in-progress (job 86521011399, success). superbot-next
  still has no live born-red hold; the hold ships staged-only.

## 💡 Session idea

Fold added-card detection into ci.yml's `checkers` step: the staged gate
already computes `git diff --diff-filter=A -- '.sessions/*.md'` and calls
`check --strict --added-card`; porting those ~10 lines into the folded
gate would give superbot-next real born-red hold semantics (closing the
sibling-card mtime hole this session re-confirmed) without adopting the
full substrate-gate workflow.

## ⟲ Previous-session review

The v1.9.0 kit-upgrade session (#150) left an excellent card — its
"first-exercise note" on the HOLD notice not firing here predicted
exactly what this session observed again, saving a re-derivation.
Improvement it points at: that card recorded the folded-gate mtime hole
twice now without a guard; the session idea above converts the repeat
observation into an enforcing fix, which is where this should end.

- Next session should know: superbot-next is on kit v1.10.0; the
  control/status.md `kit:` heartbeat line still says an older version and
  the bump is lane-owed (distribution workers do not touch control/).
