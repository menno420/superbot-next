# 2026-07-12 — program-review addendum (post-review resolutions, snapshot-respecting)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · docs/audit (Q-0194)

## Scope

Append a clearly-dated resolution addendum to the point-in-time program
review (`docs/review/program-review-2026-07-12.md`) WITHOUT editing any
existing dated finding. The review was audited at `c792079`/`edfeca8`
(#254/#255); several Q4 blockers have since landed, so the snapshot reads
some resolved items as open. The addendum re-verifies each Q4 blocker +
named finding at main HEAD `5ca477b` (#308) and buckets them
RESOLVED / PARTIAL / LIVE, every claim re-measured (file:line, PR #,
command output) — an evidence log, not a re-review.

Verified at HEAD and recorded:

- RESOLVED — Blocker #7 deathmatch 50→51 (`parity.yml:148` ported;
  `check_parity_depth` OK 51 subsystems / 50 ported, exit 0; birth #261
  `5050b8f` per wave-9 card `:78`) and Blocker #2 deploy packaging
  (Dockerfile/.dockerignore/compose/railway.json/release.yml all present;
  `ci.yml:92` build-image; PR #266 `1b08bc8`).
- PARTIAL — Blocker #1 cutover: runbook + coverage-debt doc landed
  (#264 `2e448ee`) so the DOCUMENTATION gap is closed, but cutover
  EXECUTION is not done and stays owner-gated (LIVE).
- LIVE — #3 backup/DR (restore-verify 0 runs, backup 4/4 skipped,
  `BACKUP_ENABLED` gate), #4 AI dark (`config.py:148/:166`), #5 live
  effect adapters unarmed (`decisions.md:388`(4)), #6 `_unmapped` pool = 15 fishing
  goldens (`parity.yml:133` pending), governance/platform still rosterless.

Docs-only: one addendum appended to the review + this card + telemetry
row. No code, no parity data, no `control/` writes.

## 💡 Session idea

The RESOLVED/PARTIAL/LIVE table at the addendum's foot is a re-runnable
blocker ledger: each row already pins its proof command / file:line / PR,
so a successor can re-measure the whole Q4 blocker set in one pass and
flip rows without re-deriving citations — the same "evidence over memory"
move the review itself used, now with a diff-able table to update in place.

## ⟲ Previous-session review

Covers `.sessions/2026-07-12-program-review.md` (the review this addendum
extends). Its 💡 idea — that the review's Top-10 gaps are a gen-2 backlog
seeded from evidence, each item carrying its own citations — held and is
exactly what let this addendum re-verify mechanically: every blocker in
the snapshot already named its file/PR/run, so re-measuring at HEAD was a
citation-check, not a re-audit. Its trap-37 lesson (re-derive at pick-up,
never honor on faith) was applied literally: the `_unmapped` count was
measured on disk (15, all fishing) rather than trusted, and the deathmatch
birth was cited from the wave-9 card because the shallow local clone
cannot resolve `5050b8f` from git log — both disagreements recorded rather
than smoothed over.

## Close-out

Delivered as PR #310 (`docs/program-review-addendum`), docs-only, 3 files:
the appended addendum (`docs/review/program-review-2026-07-12.md`, 128
insertions / 0 deletions — the original snapshot is byte-untouched, confirmed
by `git diff --numstat`), this card, and one telemetry row appended as the
file's true last line. Bucketing that held at HEAD `5ca477b`: RESOLVED #7
(deathmatch ported, `check_parity_depth` OK 51/50 exit 0) + #2 (deploy
packaging, #266); PARTIAL #1 (runbook landed #264, execution still owner-gated);
LIVE #3/#4/#5/#6 + governance/platform rosterless, each re-verified open.
Two disagreements with supplied expectations were recorded rather than smoothed:
the `_unmapped` pool was measured on disk at 15 (all fishing) and the deathmatch
birth `5050b8f` was cited from the wave-9 card because the shallow local clone
(44 commits) cannot resolve it from git log. Local gates pre-push: pytest 2043
passed / 8 skipped; `bootstrap.py check --strict` clean of `[stamp]` findings
(the three D-ID restamps the first draft introduced were resolved by citing
`docs/decisions.md:326/:368/:388` line anchors instead of the bare IDs — the
predecessor review's proven fix), leaving only the designed born-red card HOLD,
cleared by this flip. Opened READY; auto-merge NOT armed.
