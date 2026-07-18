# 2026-07-18 — design-series README status-index reconciliation (docs-only)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the README reconciliation
> landed in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · low · docs-only

## Goal

`docs/design/README.md`'s planning-mode status table (lines ~20-29) drifted:
D4/D1/D3/D6 rows read `**this PR**` and D5/D2/B8 read `planned`, but all 8 core
design docs (D1–D6 + B8/B10) are committed and landed, each carrying a `plan`
Status badge. Decisions D-0093..D-0096 settled several staged questions
(D1 render-band fonts/Pillow; D3 audit-retention + access-granularity; D6
removal deferral). Reconcile the stale status tokens and add a settled-questions
column, decisions-in-prose only.

## Scope

Docs-only. One file (`docs/design/README.md`) + this card. No `sb/` code
touched. **Stamp-gate:** D-0093 already homes in `D1-themed-card-renderer.md`,
D-0094/D-0095 in `D3-access-audit-model.md`, D-0096 in
`D6-autonomy-apparatus-removal.md` (all non-ledger). Every token already has a
sole non-ledger home, so README references them in PROSE only — no `D-00NN`
token minted here.

## Plan

1. Status column: all 8 planning-mode rows → `plan` (mirroring each doc's own
   badge, matching the file's production-readiness table style). Reflect landed
   per-doc progress inline: D1 Slice 1 render band landed (#560/#561); D4 P1
   outbox metric families armed (#562).
2. Add a "Staged questions settled" column citing (in prose, no tokens) the
   render-band Pillow decision (NOTE Pillow shipped `>=12.3.0` per #561, not
   `<12`), the D3 audit-retention + M1 access-granularity decisions, and the D6
   removal-deferral decision.
3. Keep the table format; don't rewrite prose beyond the status/decisions
   reconciliation. The settings epic plan (#563) already has its own
   production-readiness row — no action there.

## Verification (at HEAD this session)

- **pytest:** `python3 -m pytest -q --ignore=examples` → **3490 passed, 29
  skipped, 1 warning** (docs-only; `examples/` excluded per the standing
  plugin-example import gap).
- **docs-gate:** `python3 bootstrap.py check` → **exit 0**. No
  unreachable/badge finding for `docs/design/README.md` (reachable, badge
  intact). The only gating item was this born-red card itself (missing
  close-out) — the HOLD working as designed; cleared by this flip. All other
  warnings are pre-existing advisories on OTHER files (owner-action, claims
  format, seat-digest, automerge branch-drift, model-line-class on other
  cards) — none mine, none exit-affecting.
- **Stamp-gate:** `grep -rnE 'D-009[3-6]' docs/ --include='*.md' | grep -v
  docs/decisions.md` after the edit → **no matches**; each of D-0093..D-0096
  keeps exactly ONE non-ledger home (D-0093→D1, D-0094/D-0095→D3, D-0096→D6).
  README cites all four in prose only — zero tokens minted here.
- **Job A (main health, read-only, pre-edit):** origin/main `701b612` (#563)
  with #562 (`ff13459`) + Pillow #561 (`6b84248`) present. Full suite **3490
  passed / 29 skipped**; four layer guards (`check_namespace`,
  `check_symbol_shadowing`, `check_config_usage`, `check_no_skip`) all clean.
  D4 P1 outbox metric families wired: `build_registry(METRICS + OUTBOX_METRICS)`
  at the composition root (`sb/app/main.py:275`), the four families defined in
  `sb/kernel/outbox/metrics.py`. Main is GREEN — no blocker.

## Trail

- **design/README.md:** planning-mode table (was lines ~20-29) — 4 `**this PR**`
  and 3 `planned` tokens + 1 `plan` all normalized to `plan` (mirrors each
  doc's own badge and the file's production-readiness-table style). Added a
  one-line lead-in noting all 8 docs are written/committed; added a **Staged
  questions settled** column; noted landed slices inline (D1 Slice 1 render band
  #560/#561; D4 P1 outbox metrics #562). Decisions cited in prose only per the
  stamp-gate. Prose elsewhere untouched.
- No `sb/` code touched. `.substrate/guard-fires.jsonl` telemetry delta
  committed with this flip (derived; do not revert).

## 💡 Session idea

The design README's status column overloads two axes on one token — *is the doc
authored* (this-PR / planned / written) vs *what is the doc's content-nature*
(`plan`). Once every doc is committed the authoring axis is always "written", so
the token collapses to the badge and stops carrying signal; the useful axis
becomes *slice landing progress*, which today lives as ad-hoc inline `· Slice N
landed (#NNN)` notes. Guard recipe: a `tools/check_design_index.py` that parses
`docs/design/README.md`'s tables, asserts each row's status token equals the
linked doc's own `> **Status:**` badge, and flags any row whose linked doc has
landed slices (grep `control/claims/` or a per-doc progress marker) but no
inline landed-note — keeps the index from re-drifting the way this session found
it. Test target: a fixture README with one drifted row + one un-noted landed
doc, asserting two findings.

## ⟲ Previous-session review

The 2026-07-18 settings-epic-plan session (`complete`, #563) added the
settings-group-pending row to this same README's production-readiness table and
correctly minted no `D-00NN` token (its native token is `Q-`) — the same
stamp-discipline this session leaned on. It reconciled the file it was writing
into but left the older planning-mode table's stale `**this PR**`/`planned`
tokens untouched (out of its scope); this session closes exactly that residual,
a clean example of one narrow docs slice teeing up the next.
