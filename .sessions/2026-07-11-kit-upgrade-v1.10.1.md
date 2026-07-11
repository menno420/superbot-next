# 2026-07-11 — substrate-kit upgrade v1.10.0 → v1.10.1 (distribution wave)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · maintenance kit upgrade (Q-0261.3)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.10.0 to v1.10.1 using the pinned,
sha256-verified release asset (tag v1.10.1 @ kit commit `7e361bb`,
release run 29146372884 green, asset sha256
`fbe83ce35d1fb3b544ac58fc60ee2609eaa6c69c13d77883e9fdc5da6bbad158` —
three-way verified: coordinator-stated == GitHub asset digest ==
release.json == local sha256). Kit-owned files only; no domain work.
Payload: session-gate `tail -1` multi-card shadowing fix (every card in
the diff graded) + `_MODEL_DOCTRINE_PHRASE` emphasis-blind presence
check.

## What shipped

1. **bootstrap.py v1.10.0 → v1.10.1** — canonical path (staged
   `bootstrap.py.new` + `release.json` in repo root, `python3
   bootstrap.py.new upgrade`); the engine self-verified sha256+version
   against the adjacent release.json and self-cleaned both inputs.
   Vendored dist now sha256 `fbe83ce3…` (byte-exact release asset);
   `kit_version: "1.10.1"` in substrate.config.json;
   `last-upgrade.json` honest (`from_version: "1.10.0"`, archived dist
   `.substrate/backup/bootstrap-1.10.0.py`).
2. **Exactly ONE new backup banked:**
   `.substrate/backup/bootstrap-1.10.0.py` sha256 `ba69fc5c…c2f3b5a4`
   == the pre-upgrade vendored `bootstrap.py` (byte-identical,
   hash-verified before/after); all eight pre-existing `bootstrap-*.py`
   banks untouched (git-clean, hashes recorded pre-run).
3. **Staged gate regen carries the every-card-graded fix**
   (`.substrate/ci/substrate-gate.yml`, +60/−35): the `tail -1`
   single-card picker is gone — the gate now loops EVERY added card
   through the added-card lane (any in-progress/drafted added card
   HOLDs; gate-touching PRs keep the full locked door +
   `--simulate-added-card` per added card), logs siblings modified
   alongside an added card as advisory-only, and grades each card of a
   modified-only diff through the locked door. Still STAGED only — no
   live substrate-gate on this repo by design (ci.yml's folded
   `checkers` job runs bare `check --strict`).
4. **Carve-out section intact** in the rewritten
   `.substrate/upgrade-report.md`: "## Carve-out scan — ran — no
   kit-owned live workflow installed, nothing to scan" (correct N/A
   form here).
5. **Model doctrine no-op verified:** `.sessions/README.md`
   byte-identical (not in the diff); `_MODEL_DOCTRINE_PHRASE` content
   present exactly once — no duplicate append (the emphasis-blind
   presence check is the v1.10.1 payload's second half).
6. **⚑ Sibling-card grammar backfill (mtime-lottery defense, #159
   precedent):** pre-flip scan found two post-#159 cards missing the
   `💡`/review needles and failing individually
   (`.sessions/2026-07-11-codex-p2-triage.md`,
   `.sessions/2026-07-11-moderation-parity-flip.md`, both exit 1 via
   `--session-log`); each got a provenance-marked, grammar-only
   backfill (nothing fabricated) and now grades exit 0, so no CI mtime
   pick can red this PR — or a later one — on pre-existing drift.
7. **Heartbeat:** `control/status.md` `kit:` line → v1.10.1 (the one
   control edit the distribution recipe specifies — closes the chronic
   heartbeat-lag drift class; everything else in control/ untouched).

## Verification

- `python3 bootstrap.py check --strict` → exit 0 at close (mid-session
  it held with the designed born-red HOLD on this card; the
  pre-existing owner-ask-wall-unrecorded advisory on control/status.md
  remains lane-owed, not touched here).
- Both backfilled sibling cards + this card grade exit 0 individually
  via `check --strict --session-log <card>`.
- `python3 -m pytest tests/ -q` → 1337 passed, 2 skipped.
- `python3 tools/manifest_compile.py` → exit 0.
- Upgrade notice (informational, pre-existing): automerge
  `required_context 'substrate-gate'` matches no job in this repo's
  workflows — expected, no live gate by design; enabler stays staged.

## 💡 Session idea

The #159 card already proposed folding added-card detection into
ci.yml's `checkers` step; v1.10.1 makes that port strictly better —
the staged gate's new loop grades EVERY added card, so porting those
~15 lines now would close both the sibling-shadowing hole AND the
mtime lottery in one move, with the loop logic already written and
kit-maintained in `.substrate/ci/substrate-gate.yml` to copy from.
(Ci.yml is host-owned; left for a repo-lane session, not a
distribution worker.)

## ⟲ Previous-session review

The #159 (v1.10.0) kit-upgrade session's card was the playbook this
session ran on: its sibling-lottery record predicted exactly the two
new needle-gapped cards found here, and its backfill style was reused
verbatim. Improvement it points at: two waves in a row have now paid a
manual sibling-scan tax that its own session idea (fold added-card
detection into ci.yml) would retire — the idea has been proposed twice
without an owning lane; it should be promoted to the repo's idea/lane
queue rather than re-proposed a third time.

- Next session should know: superbot-next is on kit v1.10.1; the
  `control/status.md` `kit:` heartbeat was bumped IN this upgrade PR
  (#166) per the v1.10.1 distribution recipe — the lane no longer owes
  it.
