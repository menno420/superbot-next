# 2026-07-13 — game sections slice 3: hub renders the enabled set (ORDER 017 item 4)

> **Status:** `complete`

- **📊 Model:** `fable-5` · NIGHT-RUN lane · mandate: ORDER 017 item 4, slice c of D-0082

## Scope

Slice 3 (final) of `docs/design/game-sections.md` (D-0082 §6): the games
hub consumes the per-guild enabled set — the `games.hub_fields` provider
filters through the slice-1 `enabled_games(guild_id)` read seam, the hub
buttons gain `visible_when` enablement predicates (render-time drop +
resolve.py dispatch-time stale-click deny), sections with zero enabled
games drop, and fully-default guilds render BYTE-IDENTICAL to the ported
games goldens (fail-open all-enabled). Update contract = next-interaction
consistency (click-time re-resolution, §6.1); NO anchor sweep (named
successor). Stacked on `claude/minigame-sections-2` (PR #337, head
274dd56, unmerged at branch time). Covered by the existing lane claim
`control/claims/minigame-sections.md`. Excludes the peer fishing /
mining-WP / energy lanes.

## What shipped

- `sb/domain/games/panels.py` — the `games.hub_fields` provider filters
  through `enabled_games(guild_id)`: one catalog field per section VIEW
  (`f"{emoji} {title}"` + the shipped `f"{emoji} **{label}** — {desc}"`
  line builder over the roster blurbs — GameEntry carries no blurb by
  design, so `_GAME_DESCRIPTIONS` maps key→blurb from the roster
  constants); a fully-disabled section drops, all-disabled ⇒ zero
  fields. `games.world_fields` gets the same treatment over the new
  keyed `_WORLD_PLACE_LINES` (mining/fishing/farm; `_WORLD_PLACES`
  re-derived byte-identically). **Flag (PL-001):** design §6 names only
  the hub; the world hub lists the same games, so the identical filter
  ships here too — the 🪪 World Card button is NOT a game and stays.
- Buttons: every game action carries
  `visible_when=games.enabled_<key>` (10 registered PredicateRefs, the
  first `visible_when` consumers in domain code) — the ONE predicate
  serves render-time drop (render.py `_visible`) AND resolve.py's
  dispatch-time stale/replayed-custom_id re-evaluation (02 §3.0), so a
  STALE rendered message's disabled-game click is denied ("This control
  is no longer available.") — no strand, test-proven end-to-end through
  `resolve()`.
- **Fail-open posture (flagged):** an unreadable enablement (no DB /
  seam failure) or an unpopulated sections registry renders TODAY'S
  full static roster byte-for-byte (`_STATIC_HUB_FIELDS`) — a render
  outage never blanks the hub, enforcement stays at dispatch, and the
  ported goldens can never blank. Registered predicates fail-open too
  (deliberate divergence from the namespaced kinds' fail-closed rule:
  this gate is UI visibility, not admission — dispatch gating is
  upstream).
- **Hub select:** design §6 says "disabled games drop off the hub
  select" — at HEAD the shipped hub carries ONLY buttons (goldens pin
  zero selects; `test_hub_has_no_selectors_so_no_options_to_filter`
  documents it), so no options provider was minted. The slice-2
  settings panel's selects intentionally SHOW disabled games (their job
  is toggling).
- **Update contract (§6, C):** next-interaction consistency — every
  fresh render re-resolves at click time (`engine.py handle_nav` §2.4);
  slice-2's post-mutation `refresh_session_view` already refreshes the
  settings page in place; NO engine change, NO anchor sweep (named
  successor, design §6.3).
- Tests (13 new, `tests/unit/band6/test_band6_games_hub_enablement.py`):
  byte-identity all-enabled (hub + world), pick-a-few filtering
  (fields + buttons), section drop, all-disabled empty, broken-read +
  empty-registry fail-open, next-interaction consistency,
  stale-click deny + enabled-click open through the REAL `resolve()`.
- `manifest.snapshot.json` recompiled (`--write`): 10 predicate refs +
  `visible_when` values — NO new field roles (`check_schema_growth`
  clean, ledger untouched; the slice-1 trap avoided).
- Gates: pytest 2097 passed / 13 skipped; `manifest_compile.py` green
  post-write; full 23-checker fleet green; **golden parity gate GREEN
  locally** (`run_golden_parity.py --gate`: 471/471 across 51 ported
  subsystems replay clean over a real Postgres — the games goldens
  replay UNCHANGED, no re-cut); `bootstrap.py check --strict` red only
  on this card's designed born-red hold + the known mining-lane claims
  advisory.

## 💡 Session idea

Each hub render now costs up to 11 sequential `subsystem_visibility`
queries (one per predicate + the fields provider's per-key reads via
`enabled_games`). A per-request memo — or the slice-1/2 cards' governance
`enabled_map(guild_id, keys)` batch read — would collapse it to one;
anchor points: `sb/domain/games/panels.py::_game_enabled_fail_open`,
`sb/domain/games/sections.py::enabled_games`, test target
`tests/unit/band6/test_band6_games_hub_enablement.py`. Belongs to a
governance-lane follow-up (cross-lane API), not this slice.

## ⟲ Previous-session review

Newest card (`2026-07-13-minigame-sections-2.md`) is a complete, honest
close-out: its shipped list matches the branch head diff (sections panel
+ settings-hub group routing + golden re-cut, all flagged), its layout
budget note is verifiable against the spec, and it adopted slice 1's
guard recipe as a pre-push gate — this session adopts the same gate
order. Its PL-001 flag (dedicated `_GROUP_PANELS` mapping because
`games.hub` is the player hub) is honest and correctly scoped. Its 💡
(governance `enabled_map` batch read to make the submit diff atomic)
targets exactly this slice's provider work — evaluated this session:
still no batch read in governance; the provider keeps per-key reads
(the slice-1 seam shape) and the idea stays open for a governance-lane
follow-up rather than minting a cross-lane API here.
