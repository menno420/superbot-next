# 2026-07-12 — ORDER 015: boot-doc render (.claude/CLAUDE.md live) + orientation pointer fix + trap-index promotion

> **Status:** `complete`

- **📊 Model:** fable-5 · high · docs/audit (Q-0194)

## Scope

ORDER 015 (P2, inbox 2026-07-12T08:30Z — relocation of startup-prompt
v3.1 F3): render CLAUDE.md from `.substrate/claude/CLAUDE.md` via the
kit, fix `docs/AGENT_ORIENTATION.md`'s working-agreement pointers, and
promote the flip-playbook trap index to docs/. Docs/control-only; no
domain code touched.

## What shipped

1. **`.claude/CLAUDE.md` rendered via the kit** — `python3 bootstrap.py
   adopt --include-claude` (kit v1.13.0), the kit's ONE sanctioned
   mechanism for a live `.claude/` write (default adopt deliberately
   only STAGES CLAUDE.md; `render`/`render --live` never write
   `.claude/`). The planted file is byte-identical to the staged render
   source `.substrate/claude/CLAUDE.md` (diff-verified), and its sha256
   is recorded in `.substrate/state.json` `planted_doc_hashes` by the
   same run (kit provenance for future upgrade diffs). The adopt run
   also banked the running dist as
   `.substrate/backup/bootstrap-1.13.0.py` (the kit's §4.3
   archive-first step; committed — the bank directory is tracked).
2. **Decide-and-flag (PL-001):** the same opt-in also planted
   `.claude/settings.json` (live PreToolUse/SessionStart/PostToolUse/
   Stop hook wiring). NOT committed — ORDER 015 orders the CLAUDE.md
   render only, and installing live executable hooks is a separate
   behavioral opt-in (the kit's own safety doctrine: never install
   executable hooks silently). Flagged here + in the PR body; a future
   order can wire enforcement deliberately (`adopt --wire-enforcement`).
3. **Orientation pointers** — `docs/AGENT_ORIENTATION.md`'s two
   `${agreement_home}` renders (lines 10 and 39 at HEAD; the ORDER's
   `:10`/`:34` cites predate the v1.13.0 SKILLS.md router line) flipped
   `CONSTITUTION.md` → `.claude/CLAUDE.md`, mirroring the kit's own
   engine rule (`agreement_home()`, bootstrap.py ~:9516: the pointer is
   `.claude/CLAUDE.md` exactly when that file is live in the tree).
   Note the v1.13.0 upgrade (#251, merge `559a0d8`) had already
   re-routed the ORDER's dead pointers to `CONSTITUTION.md`; this
   session completes the ORDER's primary verb (the render) and
   re-points orientation to the now-live boot file.
4. **Trap index promoted** — `docs/parity/flip-playbook-traps.md`
   (`reference` badge): traps 1–37 indexed one line each from the
   team-memory playbook `superbot-next-parity-flip-playbook`, so every
   `trap N` citation in code/goldens/cards/status resolves in-repo.
   Reachability link added in `docs/retro/README.md` (the #256
   program-review precedent). Six D-NNNN cites reworded to prose to
   satisfy the one-stamp-home rule (`bootstrap.py check --strict`
   green locally).
5. **control/status.md** orders line: acked= and done= gain 015
   (done-when re-verified: boot pointer resolves, orientation matches
   the tree at this PR's HEAD).

## Verification

- `python3 bootstrap.py check --strict` → all checks passed (badge,
  reachability, stamp discipline, session-log markers).
- `diff .claude/CLAUDE.md .substrate/claude/CLAUDE.md` → identical.
- No sb/, tests/, manifest/, parity/ paths in the diff — docs/control
  lane only.

## 💡 Session idea

`adopt --include-claude` plants CLAUDE.md and settings.json as one
opt-in, but they are different risk classes (a boot DOC vs live
EXECUTABLE hooks). Kit-side idea (propose upstream): split the flag —
`--include-claude-doc` vs the hooks half riding `--wire-enforcement`
where the other forcing functions already live — so a doc-only order
never has to hand-discard a planted hooks file.

## ⟲ Previous-session review

The v1.13.0 kit-upgrade session (#251, card
`.sessions/2026-07-12-kit-v1130-upgrade.md`) did this ORDER's pointer
half early by applying the release's template-improved docs — correct
call, and its card said so explicitly ("this is the release's headline
fix landing here"). What it could not do (kit doctrine: upgrade never
live-writes `.claude/`) is exactly what this session adds. Its
bank-hash cross-check practice was reused here for the 1.13.0 bank
file.
