# 2026-07-11 — substrate-kit upgrade v1.11.0 → v1.12.0 (distribution wave)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · maintenance kit upgrade (Q-0261.3)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.11.0 to v1.12.0 using the pinned,
sha256-verified release asset (tag v1.12.0 → commit `b310aba`, release
run 29160292286, asset sha256
`77c00b811429e1b526ccc7e0dcf597435c11048e16a67edba6050f516ad5e1f8`,
689,586 bytes). Kit-owned files only; no domain work; control/inbox.md
and control/status.md untouched by hard scope.

## What shipped

1. **bootstrap.py v1.11.0 → v1.12.0** — canonical path (staged
   `bootstrap.py.new` + `release.json` in repo root, `python3
   bootstrap.py.new upgrade`); engine self-verified sha256+version
   against the adjacent release.json ("upgrade: verified: sha256 +
   version against release.json") and self-cleaned both inputs. Asset
   hash three-way verified before running: coordinator-stated ==
   release.json == downloaded (`77c00b81…e1f8`, 689,586 bytes).
   All three tree stamps now 1.12.0 (bootstrap.py `KIT_VERSION`,
   `.substrate/state.json`, `substrate.config.json`).
2. **Exactly ONE new backup banked:**
   `.substrate/backup/bootstrap-1.11.0.py` sha256
   `c339bd6a2eb3a139dd0106d5fd3873eb2d067f79723fccb5781d4e72a74a8d29`
   == the pre-upgrade vendored bootstrap.py (byte-identical); all ten
   pre-existing `bootstrap-*.py` banks hash-verified byte-identical
   before/after (`sha256sum -c` full pass).
3. **Carve-out scanner three-way compare (v1.12.0 payload item 4,
   first live exercise) — scan line verbatim:** "carve-out scan: ran —
   no kit-owned live workflow installed, nothing to scan." Correct N/A
   form for this staged-only repo (no live substrate-gate by design;
   ci.yml's folded `gate` job runs bare `check --strict`). NO phantom
   carve-outs, NO pre-regen bank — as the fix predicts.
4. **Boot-set trim applied (`upgrade --apply-docs`):** the two
   consumer-untouched, template-improved planted docs —
   `CONSTITUTION.md` (program-law enumeration condensed to a
   cite-the-register pointer) and `docs/AGENT_ORIENTATION.md`
   (duplicate start-list/verify block dropped) — applied from the new
   templates, hashes re-recorded. The carve-out section survived the
   `--apply-docs` report rewrite (kit #176 fix observed working).
   Staged `.substrate/claude/CLAUDE.md` carries the three-surface
   boot-set regen. All other planted docs: consumer-edited/unchanged,
   nothing applied (kit does not clobber host content).
5. **Upgrade notice (informational, pre-existing):** automerge
   `required_context 'substrate-gate'` matches no job in this repo's
   workflows — expected, no live gate by design; merged via MCP, not
   auto-merge.
6. **Sibling-card needle scan (mtime-lottery defense, #159/#166
   precedent):** all `.sessions/` cards scanned for the four needles
   (Status / 💡 / review / 📊 Model) — every sibling compliant; no
   backfill needed. v1.12.0's advisory-draft change (payload item 3)
   should shrink this red class going forward in this repo's bare
   strict lane.
7. **Heartbeat NOT bumped:** the `control/status.md` `kit:` line is
   hard-scope-excluded this wave (coordinator directive Q-0261.3) —
   lane-owed, deliberately not in this PR.

## Verification

- `python3 bootstrap.py check --strict` → exit 0 (only the
  pre-existing owner-ask-wall-unrecorded advisory on control/status.md,
  never exit-affecting, lane-owed and hard-scope-excluded here).
- `python3 -m pytest tests/ -q` → 1416 passed, 2 skipped.
- Grep for `1.11.0` exact-pins in tests/config (the websites-class
  bump): NONE in this repo outside `.substrate/backup/` — nothing to
  bump.
- `.substrate/guard-fires.jsonl` 104 lines (tracked; committed in the
  flip commit per convention).

## 💡 Session idea

The upgrade engine already prints "2 doc(s) have template improvements
you never edited — take them now with --apply-docs" — but the choice is
easy to miss in a long report and the v1.11.0 card shows waves
alternating on whether they apply. A one-line
`substrate.config.json` knob (`upgrade.auto_apply_untouched_docs:
true|false`) would let an adopter declare the policy once, making the
canonical path fully deterministic per repo instead of per-session
judgment — zero risk since it only ever touches consumer-UNTOUCHED
docs the engine already classifies as safe.

## ⟲ Previous-session review

The v1.11.0 upgrade card (#182) was again a 1:1 playbook — its recipe,
backup-hash discipline, and sibling-scan step transferred directly, and
its "Next session should know" pointer (repo on v1.11.0, heartbeat
lane-owed, HANDOFF.md untracked-by-design) was exactly the right
starting fact set. Improvement it surfaces: it flagged the
heartbeat-owner ambiguity and this wave resolved it by hard scope
(coordinator directive) rather than by a durable convention — the
distribution recipe should still record ONE canonical owner for the
`kit:` heartbeat bump so the per-wave directive stops being load-bearing.

- Next session should know: superbot-next is on kit v1.12.0; the
  `control/status.md` `kit:` heartbeat bump remains OWED by the control
  lane (hard-scope-excluded from upgrade PR #198); the carve-out
  scanner's N/A line for this repo is the correct staged-only shape;
  HANDOFF.md appears untracked at repo root after boots — kit design,
  leave it uncommitted.
