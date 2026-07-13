# 2026-07-13 — curation rework: ledger the leaderboard alias set deliberate (row 44)

> **Status:** `complete`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  row 44 (`docs/review/curation-report-2026-07-13.md` L948 + §Rework
  backlog "leaderboard alias fold" L1548), claim
  `control/claims/leaderboard-alias-fold.md` (PR #380), token
  `claude/rework-leaderboard-alias-fold`.

## Scope

The `leaderboard` CommandSpec (`sb/manifest/leaderboard.py:27-30`) carries
ELEVEN aliases the curation sweep flags as unexplained legacy duplicates.
Q-A03 (`docs/decisions.md:290`) is an owner-held default: legacy routes
stay callable — so the aliases stay VERBATIM; trimming would contradict an
owner ruling without an owner turn. The honest rework is regularization:
a DELIBERATE ALIAS SET ledger block in the manifest (row 73 / PR #379
precedent), plus a strengthened band4 set-pin test that fails toward
Q-A03 + the ledger on drift in either direction. Wire behavior unchanged,
zero golden churn, snapshot byte-stable (comments don't compile in —
verified via manifest_compile).

## What shipped

**Shape chosen: regularize, not trim.** The claim framed the lane as
"trim OR ledger"; Q-A03 is owner-held, so trimming without an owner turn
was never on the table — the honest rework answers the sweep's real
complaint (an UNEXPLAINED legacy set) in-code:

- **Ledger** — `sb/manifest/leaderboard.py` now carries a `DELIBERATE
  ALIAS SET` block directly above the CommandSpec (row 73 / #379
  precedent): provenance (oracle `leaderboard_cog:211`
  `alias_classification` = `legacy_duplicate`), the ruling quoted
  verbatim from D-0038 (docs/decisions.md:290, "Q-A03 held default:
  legacy routes stay callable"), what changes it (an owner turn amending
  Q-A03, never a curation lane alone), the two guarding pins, and an
  anti-conflation note: the provider-registry alias rows
  (`rank_providers.py` band 4, `sb/domain/games/providers.py` band 6,
  e.g. `minelb`) share names but are a SEPARATE dispatch-keyword seam.
- **Drift-guard test** —
  `tests/unit/band4/test_band4_community.py::test_leaderboard_alias_set_is_ledgered_deliberate`
  pins the exact 11-alias tuple (order included) AND the ledger's
  markers (`DELIBERATE ALIAS SET` / `Q-A03` / `legacy_duplicate` via
  `inspect.getsource`); drift in either direction fails with a message
  routing to Q-A03 + the ledger block. The existing set-pin at :210-213
  kept, annotated to point at the new test.
- **No docs edits** — the curation report is append-only history;
  docs/decisions.md carries no non-owner amendment grammar for an
  owner-held default, so the manifest ledger IS the record (deliberate;
  the claim's file list named decisions.md/current-state.md as
  candidates — declined with this rationale).
- **Housekeeping riding the PR** — retired the completed claim files
  `control/claims/settings-access-rework.md` (#375) and
  `control/claims/server-management-name-pair.md` (#379).

Wire behavior unchanged; zero golden churn; snapshot byte-stable
(comments don't compile in — manifest_compile green with no --write,
sha `736bc9cc…` unchanged). Verification: manifest_compile /
check_schema_growth / check_compat_frozen green; full 23-checker fleet
green; `python3 -m pytest tests/` — **2435 passed, 13 skipped**;
`bootstrap.py check --strict` exit 0 (mining-lane claims-format advisory
known-OK); parity gate **GREEN — 484 goldens / 50 ported subsystems**.

## 💡 Session idea

The DELIBERATE-ledger pattern now has two instances (row 73 name pair,
row 44 alias set) with the same three-part anatomy — provenance, ruling,
what-changes-it — enforced only by per-case tests grepping module
source. If a third lands, a tiny house convention (a `DELIBERATE` marker
grammar + one parametrized test that walks `sb/manifest/*.py` and
asserts every `DELIBERATE` block names a ruling anchor
`docs/decisions.md:<line>` or `Q-*` id) would make ledger presence
structural instead of per-case, for ~20 lines.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-rework-server-management-name-pair.md`.)
Its shape-A-over-B call (ledger over grammar growth) was this lane's
direct template — same argument, reused verbatim: the complaint is the
missing explanation, not the declaration, and schema/alias surgery would
be churn against an owner ruling for zero honesty gain. Its guard recipe
(projectmoon/uxlab dir-alias pattern) and session idea (parity-row
normalization checker) are untouched by this lane — both remain live
follow-ups. One pattern it modeled that paid again: verify the pin
BEFORE writing prose (its wave-9 diff check ↔ this session's
grep-the-snapshot-for-`minelb` confirming the alias tuple is
snapshot-pinned and compat-frozen before citing both as guards). Its
`git mv` husk-directory friction didn't apply (no file moves here).
