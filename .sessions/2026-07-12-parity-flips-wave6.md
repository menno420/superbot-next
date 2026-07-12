# 2026-07-12 — parity flips wave 6 (the games-family flips: inventory · casino · creature · four_twenty birth · games)

> **Status:** `complete`

- **📊 Model:** Fable · high · feature build (Q-0194 / ORDER 012)

## Scope

The parity-flips lane's wave 6: the games-family subsystem rows that
the band-6 lane's ports left flippable. Five PRs merged green this
wave — four pending→ported flips plus one subsystem BIRTH — each its
own squash-merged-on-green PR on the 6-check ruleset (`report`
red-by-design, non-required). Main moved constantly around this lane
(#217/#218/#220–#223/#225/#228/#229 from sibling lanes landed
interleaved with ours); every count below is re-verified at the
current HEAD `8730200` (#230's merge, main HEAD at wrap-up), not
replayed from mid-wave memory. This wrap-up card + its telemetry row
+ the status fold ride the wrap-up PR (control fast lane, docs-only —
trap 25: no Postgres ladder in the wrap-up seat; counts are
CI-LOG-VERIFIED instead).

## The five PRs (each merge sha verified against `git log origin/main` at `8730200`)

1. **#219** `d3dba9b` — inventory pending→ported (1/1 goldens,
   sweep_inventory). Codex returned findings on this one: 2 verified
   REAL and fixed in-PR, 1 verified-and-declined with source citation
   (the Q-0120 discipline held on both sides).
2. **#224** `cc59a6e` — casino pending→ported (2/2 goldens,
   sweep_casino + sweep_poker). Kernel seam: `HUB_NAV_LABELS` gained
   the `"games"` entry (sb/kernel/panels/render.py) so the casino
   panel's back-nav byte renders the shipped hub label.
3. **#226** `f032e8a` — creature pending→ported (6/6 goldens — the 5
   creature sweeps + sweep_dextop re-homed `_unmapped`→creature). The
   `!catch` command is KEPT DECLARED while skip-listed (doctrine
   documented in-PR: skip-listed-but-declared is NOT a contradiction
   when golden-pinned bytes depend on the declaration — the treasury
   grant / admin restart precedent; `_sweep_skips.json` pins WHY no
   golden exists, the manifest pins the shipped surface). Two depth
   exemptions, both under EXISTING classes:
   `table:creature_collection_log` (env-keyed-integration — the catch
   lane's unseeded private RNG kept the writer out of the capture
   corpus by design) and `table:creature_battle_record` (time-driven —
   battle rows land only at PvP resolution inside the interactive
   challenge view, the rps_players precedent).
4. **#227** `39bf226` — four_twenty subsystem BORN ported (1/1
   goldens, sweep_420). The passive content-trigger is armed LIVE, not
   parity-only: `handle_four_twenty` rides the shared message feed
   (sb/adapters/discord/message_feed.py) ordered AFTER
   `handle_chat_award`, and the parity harness's `boot.send_command`
   drives the same stage — the golden pins the trigger firing on the
   command message itself, so the arming had to be in the ingress
   path, with the module-global RNG simulated under the runner seed
   before the panel build. Style seam: `STYLE_TOKEN_COLORS` gained
   `leaf_green` (sb/kernel/panels/render.py:97;
   sb/domain/four_twenty/panels.py pins it).
5. **#230** `8730200` — games pending→ported (4/4 goldens — the 2
   games sweeps + sweep_world/sweep_worldcard re-homed
   `_unmapped`→games). The hub reshaped 4→10 rows on STATIC persistent
   ids (`custom_id_override="games:open:<key>"` through the session
   mint, no `_mint_ephemeral` — the community precedent); the shipped
   BOTH command split to PREFIX + SLASH twins with the slash side
   ephemeral (recon had labeled it "public"; the golden's flags byte
   64 says ephemeral — the golden won). Five depth exemptions, all
   covered-elsewhere/trap-14f under existing classes: game_state (via
   ported blackjack siblings), guild_settings (via ported
   rps_tournament), and game_xp + game_xp.awarded + game_xp.level_up
   citing the NAMED `_unmapped` mining-lane siblings
   (sweep_fastmine/sweep_chop/sweep_explore each carry the game_xp
   row — the settings `table:subsystem_bindings` precedent: when no
   ported sibling exists, a named `_unmapped` sibling that pins the
   bytes is honest coverage pending its re-home). A reviewer
   suggestion to UNDECLARE game_xp was rejected on source: creature
   ops award game_xp in-txn, the surface is real.

## End counts (wave-6 END state, CI-LOG-VERIFIED at main `8730200`, #230's merge)

- gate **GREEN 346/346 across 45 ported** (44 subsystem rows + the
  kernel coverage home) — main-push golden-parity run 29178063196
  gate job 86610739481: "gate: GREEN — all 346 golden(s) across 45
  ported subsystem(s) replay clean" + "golden-parity gate: 45 ported /
  6 pending" + "check_parity_depth: OK — 50 subsystems (44 ported),
  kernel ported, 471 goldens" (same job); integration 10 passed same
  job.
- report **352/471 green, 471/471 replayable** — report job
  86610739470 same run: "report: RED — 119 golden(s) not yet at
  parity (EXPECTED until the last subsystem flips ported)"
  (red-by-design, non-required).
- units **1568 passed / 7 skipped in CI** (ci run 29178063197 tests
  job 86610739516 — the deps-free CI shape; local canonical ladders
  with deps differ by the standing guarded-import skip delta).
- corpus **471 = 465 imported + 6 minted** (unchanged this wave — all
  five flips rode imported/re-homed goldens, zero mints); `_unmapped`
  **111** at HEAD (wave movement: sweep_dextop → creature at #226,
  sweep_world + sweep_worldcard → games at #230).
- parity **44/50 subsystem rows ported** + kernel home ported.
  Remaining pending (verified in parity.yml AND the gate job's
  pending table at HEAD): **farm** (1 golden), **fishing** (2),
  **mining** (2) — still pending; the #217 farm/mining merge was the
  money-race FIX, not a flip — **setup** (8, PARKED at the
  create-channel wall, trap 17), **quicksetup** (1, BLOCKED D-0030),
  plus the `_unmapped` re-home pool (111).

## Traps confirmed / new intel

- **Skip-listed-but-declared can be doctrine, not contradiction**
  (#226): keep the command declared when golden-pinned bytes depend on
  the lane existing; the skip entry documents why no golden drives it.
- **Exemption-class honesty**: guard-only-capture requires an
  actually-captured bare invocation; when the writer never ran in the
  capture world, env-keyed-integration / time-driven are the honest
  classes (#226). Covered-elsewhere may cite NAMED `_unmapped`
  siblings when no ported sibling carries the bytes (#230).
- **Content-triggers arm LIVE when the golden pins firing on the
  command message itself** — message_feed + boot.send_command, ordered
  after handle_chat_award, module-global RNG seeded before build
  (#227).
- **Static-id hubs**: custom_id_override + no `_mint_ephemeral`;
  crossing the arrangement floor mints lock rows ADDITIVELY, and the
  post-#197 checker's own failure text carries the same-PR instruction
  for removing stale pins (#230).
- **Recon "public" labels can be wrong — trust golden flag bytes**
  (flags 64 = ephemeral, #230).
- Trap 25 honored: wrap-up seat ran no Postgres ladder; every count
  above is CI-log-verified at the merge sha.

## Verification

Merge shas verified against `git log origin/main` at `8730200`
(inventory `d3dba9b53bf87ededee6ed4942a1e7c87e185add`, casino
`cc59a6eabd603df173fad74ede53240c61f63e77`, creature
`f032e8aec85383c1f2a0e209ce6ca3405b1fd2c6`, four_twenty
`39bf226b98b48083f9b9d1b1cc8a644cd3dae9e3`, games
`87302001f993ea36480fedfc6cc7e85eab8d4255`); end counts CI-LOG-VERIFIED
at that sha (run/job ids per claim above); `python3 bootstrap.py check
--strict` green at the wrap-up head; parity.yml statuses re-read at
HEAD (44 ported / 6 pending hand-counted); source anchors for every
wave fact re-verified at HEAD (HUB_NAV_LABELS, leaf_green,
custom_id_override, the creature/games exemption rows, the
message_feed arming).

## 💡 Session idea

The remaining flip map is now THREE real rows + two walls: fishing (2
goldens) and mining (2) flip together naturally — their `_unmapped`
game sweeps (sweep_fastmine/sweep_chop/sweep_explore and the fishing
family) re-home WITH the flips and retire the #230 game_xp
covered-elsewhere citations in the same motion (the exemption rows
name them; the flip PR should convert covered-elsewhere→direct
coverage). Farm (1 golden) rides the same band. After those three,
only setup (trap 17) / quicksetup (D-0030) stand between the corpus
and full parity — both walls are owner-shaped, not agent-shaped, so
the endgame is a re-home sweep of the residual `_unmapped` 111 minus
the game families.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-11-parity-flips-wave5.md`, this lane's
direct predecessor.) Its `_unmapped` histogram was the map this wave
navigated by, and its two standing laws both held: the #193
"re-homes are flip-sized" law priced sweep_dextop and world/worldcard
correctly (both needed real port work, not file moves), and its
CI-log-verification discipline transferred verbatim (this card cites
the same run/job shape). What it under-called: it filed the
games-family rows as "band-6 games lane" territory, but the flips
landed here in the parity lane once band-6's ports made them
flippable — lane boundaries follow readiness, not the org chart. Its
birth-kit lesson (the verified_live.yml roster row) was exercised
again by the four_twenty birth at #227 without friction — the
documented trap held. One thing it could not have foreseen: wave 6's
distinctive work was doctrine (skip-listed-but-declared, named
`_unmapped` siblings as coverage) rather than mechanism — the
playbook grew rules this wave, not seams.
