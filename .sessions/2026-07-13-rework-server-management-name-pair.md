# 2026-07-13 — curation rework: regularize the server-management prefix/slash pair (row 73)

> **Status:** `complete`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  row 73 (`docs/review/curation-report-2026-07-13.md` L1210 + §Rework
  backlog "server-management" L1554), claim
  `control/claims/server-management-name-pair.md` (PR #376), token
  `claude/rework-server-management-name-pair`.

## Scope

The `server-management` surface shipped as TWO CommandSpecs at
`sb/manifest/server_management.py` — prefix `servermanagement` and slash
`server-management`, both routing to `panel:server_management.hub` —
with its goldens split across TWO directories
(`parity/goldens/server_management/sweep_servermanagement.json` prefix,
`parity/goldens/servermanagement/sweep_slash_server-management.json`
slash). Decide the minimal honest regularization; parity gate must stay
green without re-cutting golden bytes.

## What shipped

**Shape chosen: A (ledger + dir unification), not B (grammar growth).**
Rationale: `CommandKind.BOTH` folds only SAME-name twins (G-6, the
`!karma`/`/karma` class); the oracle ships this pair under two DIFFERENT
names, so two CommandSpecs is the regular declaration — a slash-twin-name
field on CommandSpec would be schema growth with this pair as its sole
consumer (no other differently-named pair exists in the manifests), a
snapshot/compat cascade for zero honesty gain. The report's real
complaint was the unledgered split, and both halves close mechanically:

- **Ledger** — `sb/manifest/server_management.py` module docstring now
  carries a `DELIBERATE NAME PAIR` block (the `sb/manifest/setup.py`
  deliberately-not-declared precedent) stating why two specs is the
  regular shape, + a pointer comment on the slash spec itself.
- **Golden dir unification** — `sweep_slash_server-management.json`
  re-homed `goldens/servermanagement/` → `goldens/server_management/`
  via the wave-9 re-home mechanism (git mv + the ONE-line `subsystem`
  field edit `servermanagement`→`server_management`; #248/#252/#202
  precedent — the replay adapter reconstructs the case dir FROM that
  field, sb/adapters/parity/cases.py:96, so field and dir must agree;
  response bytes untouched).
- **Row retirement** — the emptied `servermanagement` row retired from
  `parity/parity.yml` (subsystems row + ratchet `{0,0,0}` — the moved
  golden has zero covered surfaces, so `server_management`'s ratchet
  `{1,3,0}` is unchanged and no --write-ratchet regen was needed) and
  from `verification/verified_live.yml` (V4 mirror) — the `_unmapped`
  retirement mechanism (#350, R1/V4 pair rows with non-empty dirs).
  Retirement note appended to the parity.yml subsystems block comment.
- **Stale path prose** updated at every reference: panels.py docstring +
  `justification` string (→ `manifest.snapshot.json` recompile; diff is
  exactly the prose + stable_hash), `sb/kernel/panels/context.py`
  surface-field comment, hub test docstrings.
- **Tests** (`tests/unit/band6/test_band6_server_management_hub.py`):
  `test_name_pair_goldens_share_one_directory` (both sweeps in the one
  dir, retired dir stays retired, golden subsystem-field/dir/roster/
  mirror agreement) + `test_name_pair_is_ledgered_deliberate` (ledger
  present; exactly one spec per kind, different names, shared route).

Verification: manifest_compile / check_schema_growth /
check_compat_frozen green; full 23-checker fleet green; `python3 -m
pytest tests/` — **2428 passed, 13 skipped**; `bootstrap.py check
--strict` exit 0; parity gate **GREEN — 484 goldens / 50 ported
subsystems** (byte-identical replay; roster 51→50 by the row retirement,
golden count unchanged).

Guard recipe (follow-up, NOT this lane): `projectmoon` and `uxlab` are
the same oracle-cog-named dir-alias pattern (`parity/parity.yml`
subsystems rows with `{0,0,0}` ratchets beside `project_moon`/`ux_lab`);
if curation ever REWORKs those rows, this session's mechanism applies
verbatim — git mv + subsystem-field edit + row retirement pair
(parity.yml + verified_live.yml), test target
`tests/unit/parity_gate/test_check_parity_depth.py::TestRealTreeIsGreen::test_roster_matches_golden_dirs_both_directions`.

## 💡 Session idea

The golden-dir → parity-row attribution lives in THREE places that must
agree by hand (the doc's `subsystem` field, the dir name, the
parity.yml/verified_live.yml row pair) and nothing structural prevents a
future capture minting a NEW oracle-cog-named dir and re-splitting a
subsystem. A tiny checker rule — "no two subsystems rows may normalize
to the same key modulo underscores/hyphens unless ledgered" — would have
flagged servermanagement/project_moon/uxlab at import time and would
fence the pattern permanently for ~15 lines in check_parity_depth R1.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-rework-settings-access.md`.) Its
build-the-seam-honestly framing didn't bite here (this lane was pure
attribution mechanics, no new seam), but two of its patterns carried:
the decide-and-flag one-line-rationale discipline (its reset-arming
call ↔ this session's shape-A-over-B call, both argued from an existing
shipped mechanism rather than new machinery), and its
verify-the-boundary-against-the-audit move (its PARK-boundary check ↔
this session's verifying the re-home mechanism against the actual
wave-9/#350 diffs before touching parity.yml rather than trusting the
prose). Its session idea (kernel PanelSession.params bag) remains
unactioned and untouched by this lane. One friction it did not warn
about, hit here: `git mv` leaves the emptied source DIRECTORY on disk
(git tracks no dirs), and two roster tests iterate real dirs — `rmdir`
the husk in the same change or the suite reds.
