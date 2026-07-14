# 2026-07-13 — fishing populated-body fidelity + residue doc true-up (ORDER 031 phase 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · ORDER 031 phase 2 games-lane fishing slice ·
  mandate: the two S-effort fishing items from the published review
  (`docs/review/games-finalization-2026-07-13.md` §5 items 1–2), one PR.

## 💡 Session idea

Two contained fixes cut from the fishing end-to-end review:

- **A. fishtop/trophies populated-body oracle fidelity** — the port's
  populated `!fishtop`/`!trophies` bodies deviate from the shipped copy
  (oracle `disbot/cogs/fishing_cog.py:154-192`): medals 🥇🥈🥉, resolved
  member display names, `— **N** caught (S/21 species)` and the trophy
  `{emoji} **{weight:g} kg** {Species} — {name}` lines. Port verbatim
  into `fishing.top_view`/`fishing.trophies_view`
  (`sb/domain/fishing/service.py:979-1019`) and retire the two
  self-ledgered under-port notes. Goldens pin only the empty-world
  branch (verified: `sweep_fishtop`/`sweep_trophies` carry the
  empty-body descriptions) — populated-branch change is golden-neutral.
- **B. Completeness-table fishing residue true-up** — the retired
  "cast leg still runs the starter shore profile" sentence: at HEAD
  `7c47ac9` the main true-up ALREADY LANDED via #436 (night true-up —
  row 76 + Top-gaps item 1 now name the D-0043 timing rung); the
  surviving residue is the missing **#394** citation (the bait-consume
  race fence that hardened the per-cast bait charge spend the row
  cites). Add it; no other stale mirror in `docs/status/` (grepped).

## previous-session review

`HANDOFF.md` absent in this worktree (fresh branch off `origin/main`
@ `7c47ac9`); trail read instead from the review context and
`git log` — #432 published the phase-1 reviews, #436 trued up the
cast-leg row, #442 ran the mining improve slice on this lane's claim
(`control/claims/order-031-games-casino.md`, PR #423). Claims re-scanned
at HEAD: `fishing-bait-race-fence` claims
`sb/domain/fishing/{service,store}.py` but its functions
(`cast_open`/`consume_bait_charge`, merged #394) are disjoint from the
two read handlers + read queries touched here;
`completeness-remainders` lists the completeness table but its fishing
slice landed (#410) — doc-only residue edit, noted in the PR.

## Work log

- Branch `claude/fishing-body-fidelity` off `origin/main` @ `7c47ac9`.
- A: `store.top_fishers` gains the oracle's `COUNT(*) AS species`
  column (oracle `disbot/utils/db/games/fishing.py:115`); service-local
  `_angler_name` mirrors the panels `_member_display_name` seam with
  the oracle's `User {id}` fallback (`fishing_cog.py:159/186`);
  populated bodies rendered oracle-verbatim.
- B: #394 citation added to the fishing row + Top-gaps item 1; the
  row's drifted `service.py:1032/:1048` anchors trued to `:1066/:1082`
  (this slice's own insertions moved them).

## Close-out

- **Delivered** (commit `fad1471` on `claude/fishing-body-fidelity`):
  `sb/domain/fishing/service.py` (`_angler_name` helper + verbatim
  populated bodies in `top_view`/`trophies_view`, under-port notes
  retired), `sb/domain/fishing/store.py` (`top_fishers` +
  `COUNT(*) AS species`), `docs/status/completeness-table-2026-07-13.md`
  (#394 citation + anchor true-up).
- **pytest**: `11 failed, 2979 passed, 2 skipped` — all 11 are
  economy/games *race* integration tests that fail identically with
  this slice's edits stashed (verified at the card-only tree):
  pre-existing/environmental, zero fishing overlap.
- **Golden gate**: run once — 4 RED, ALL the fleet-wide midnight
  weather-rot set (three fishing cast writes + `howtofish_rules_card`
  embed 07-13's date-derived "Storm"; replays after 00:00Z produce
  "Rain"), owned by the `claude/hotfix-weather-goldens` lane per the
  coordinator HOLD. Nothing beyond those four is red — this slice's
  populated-branch change is golden-neutral (`sweep_fishtop`/
  `sweep_trophies` pin only the empty-world descriptions, verified).
- **Strict**: `bootstrap.py check --strict` red only on this card's
  designed born-red hold (claims warnings are advisory) — flips green
  with this commit.
- **Held un-pushed** per the coordinator HOLD directive (midnight
  golden-rot); PR to follow once the hotfix lands and main is merged
  in.
- **Guard recipe (deferred)**: the date-derived weather goldens will
  rot at EVERY midnight boundary unless minted through
  `seed_weather_for_replay` (the `CAPTURE_WORLD_WEATHER` replay seam,
  `sb/domain/fishing/weather.py:11-20`) — any future fishing golden
  touching the forecast field must seed, never inherit the wall-clock
  date; test target: `tools/run_golden_parity.py --gate` across a
  simulated date flip.
