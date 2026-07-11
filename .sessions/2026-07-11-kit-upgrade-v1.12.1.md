# 2026-07-11 — substrate-kit upgrade v1.12.0 → v1.12.1 (distribution wave)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · maintenance kit upgrade (distribution seat)

## Scope

Kit-seat distribution session: upgrade the vendored substrate-kit from
v1.12.0 to v1.12.1 (carries the substrate-gate false-green fix) using the
pinned, sha256-verified release asset (asset sha256
`1055ca2cfd32a83e3dab7a978b05fbec2a82932a3375de0b1034f2519c16e4aa`,
704,108 bytes). Kit-owned files only; no domain work; control/inbox.md
and control/status.md untouched by hard scope.

## What shipped

1. **bootstrap.py v1.12.0 → v1.12.1** — canonical path (staged
   `bootstrap.py.new` + `release.json` in repo root, `python3
   bootstrap.py.new upgrade`); engine self-verified sha256+version
   against the adjacent release.json and self-cleaned both inputs.
   Asset hash three-way verified before running: coordinator-stated ==
   release.json == downloaded (`1055ca2c…e4aa`, 704,108 bytes); the
   vendored bootstrap.py now hashes byte-identical to the release
   asset. All three tree stamps now 1.12.1 (bootstrap.py
   `KIT_VERSION`, `.substrate/state.json`, `substrate.config.json`).
2. **Exactly ONE new backup banked:**
   `.substrate/backup/bootstrap-1.12.0.py` sha256
   `77c00b811429e1b526ccc7e0dcf597435c11048e16a67edba6050f516ad5e1f8`
   == the pre-upgrade vendored bootstrap.py (byte-identical, verified
   against `git show HEAD:bootstrap.py`); no pre-existing bank
   modified (git status clean on all other `bootstrap-*.py`).
3. **Carve-out scan: 0 found** — report line verbatim: "carve-out
   scan: ran — no kit-owned live workflow installed, nothing to scan."
   Correct N/A form for this repo (no live substrate-gate.yml by
   design; ci.yml's folded `gate` job runs bare `check --strict`; the
   upgrade regens only the staged `.substrate/ci/substrate-gate.yml`,
   +23/−4 lines).
4. **Template deltas: NONE** — every planted doc is either "unchanged
   (template identical across versions)" or "consumer-edited, template
   unchanged — nothing to apply." No DIVERGED entries, no
   `--apply-docs` needed this wave.
5. **Upgrade notice (informational, pre-existing):** automerge
   `required_context 'substrate-gate'` matches no job in this repo's
   workflows — expected, no live gate by design; merged via MCP, not
   auto-merge.
6. **Sibling-card needle scan (mtime-lottery defense):** all
   `.sessions/` cards scanned for the four needles (Status / 💡 /
   previous-session review / 📊 Model:) — every sibling compliant; no
   backfill needed.
7. **Heartbeat NOT bumped:** the `control/status.md` `kit:` line is
   hard-scope-excluded (lane-owed), deliberately not in this PR —
   it will read stale (v1.12.0) until the control lane bumps it.

## Verification

- `python3 bootstrap.py check --strict` → the ONLY red was the
  designed born-red hold on this session's own in-progress card
  (flips with this commit).
- `python3 -m pytest tests/ -q` → 1468 passed, 7 skipped.
- Grep for `1.12.0` exact-pins in tests/config: none outside
  `.substrate/backup/` — nothing to bump.

## 💡 Session idea

The upgrade engine's self-clean of `bootstrap.py.new`/`release.json` is
correct, but it also erases the exact verification banner from any
scrollback-limited harness. A one-line
`.substrate/last-upgrade-verification.txt` (version, sha256, byte size,
verified-against-release.json yes/no) written by the engine at upgrade
time would make the sha-verification claim durably auditable from the
tree instead of from the session transcript.

## ⟲ Previous-session review

The v1.12.0 upgrade card (#198) was again a 1:1 playbook — its
three-way hash verification, single-new-bank check, sibling needle
scan, and "heartbeat lane-owed" framing all transferred directly, and
its "Next session should know" block was exactly the right starting
fact set. Improvement it surfaces: it recommended recording ONE
canonical owner for the `kit:` heartbeat bump so the per-wave directive
stops being load-bearing — that is still unresolved as of this wave
(the heartbeat is stale again); the distribution recipe should name the
owner durably.

- Next session should know: superbot-next is on kit v1.12.1; the
  `control/status.md` `kit:` heartbeat bump remains OWED by the control
  lane (hard-scope-excluded from upgrade PR #215); carve-out scan 0
  found is the correct staged-only shape for this repo; the `report`
  check on PRs is red-by-design and not required.
