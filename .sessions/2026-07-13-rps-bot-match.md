# 2026-07-13 — rps bot-match deep flow (ORDER 017 night-run slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1
  (top gap 9: "rps bot-match deep flow — `!rpsbot` pending;
  interactive match orchestration. Free.")

## Scope

Arm the `!rpsbot` deep bot-match flow (`rps.bot_route` →
`sb/domain/rps/handlers.py`, the last pending terminal in the
rps_tournament row): the shipped per-player bot match — mode/best-of
guards, per-round bot throw + reveal, best-of scoring, per-round stats
through the audited lane, terminal match copy — faithful to the oracle
(menno420/superbot `disbot/cogs/rps_tournament/_bot_matches.py`),
carried onto the ledgered home-channel BUTTON-view deviation the
tournament match panel already rides (private match channels +
no-prefix move parsing stay the resource-provision successor).

Secondary micro-task (report-only): probe whether the hermes
work-order send (`sb/domain/hermes/handlers.py:19`) is a code slice or
env/owner-keyed; capture evidence, build nothing if env-gated.

## What shipped (PR #351)

- `sb/domain/rps/bot_match.py` (new) — the shipped `_bot_matches`
  in-memory per-player state headless: replace-on-new-`!rpsbot`
  overwrite, `best_of // 2 + 1` scoring, alias-normalized throws, the
  scripted-rng test seam (`set_bot_rng_for_tests`).
- `sb/domain/rps/handlers.py` — `rps.bot_route` ports
  `run_rps_bot_command` (invalid-mode sweep bytes + the odd-positive
  best_of copy verbatim; member mentions + invoker fallback; role
  expansion/by-name lookup = live member-census successor, ledgered);
  new `rps.botmatch_move` click handler (peer lock, shipped
  already-over / invalid-move copy, per-round audited stats, staged
  `refresh_session_view` edits); `rps.bot_pending` retired — zero rps
  pending routes remain.
- `sb/domain/rps/panels.py` — `rps_tournament.botmatch` panel
  (CHANNEL_ANCHOR, session-lifecycle, mode-subset move buttons on
  `bot_move_*` ids — custom_id claims are SUBSYSTEM-scoped and `move_*`
  belongs to the tournament match panel) + staged renderer carrying the
  shipped `_bot_matches.py` channel copy byte-for-byte.
- `sb/domain/rps/ops.py` — `rps.bot_round` audited stats leg (the
  shipped per-throw `update_player_stats` site; no money — shipped bot
  matches are free play).
- `manifest/layout/rps_tournament.lock.json` + `sim/sim-gate-baseline.json`
  — legacy-seed Exempt pins for the new panel's arrangement (the match
  panel's exemption carried to the bot lane); `manifest.snapshot.json`
  recompiled; compat pin untouched (no custom_id_override/modal_id).
- `docs/status/completeness-table-2026-07-13.md` — rps_tournament core
  ⚑→✅, Top-gaps item 9 struck, headline counts 43/7, item 10 hermes
  verdict added.
- `tests/unit/band6/test_band6_rps_botmatch.py` — 10 tests: renderer
  copy pins, pure match core, walking-skeleton best-of-3 drive with
  scripted bot throws + per-round audited-stats evidence, peer-lock and
  late-click guards, multi-player views.

**Hermes probe verdict (secondary):** env/owner-keyed, NOT a free slice
— the transmit leg is a small un-ported code slice (the oracle's
~40-line aiohttp POST, `disbot/cogs/hermes_cog.py:44-81`) behind
DORMANT owner credentials `CLAUDE_ROUTINE_FIRE_URL` +
`CLAUDE_ROUTINE_TOKEN` (`sb/spec/config.py:197-204`); both absent in
the build env, `bridge_configured() == False`, one-shot attempt →
verbatim `RuntimeError: missing_config`. Ledgered in
`docs/CAPABILITIES.md`; nothing built.

Verification (close-out): `python3 -m pytest tests/` **2194 passed,
2 skipped** (full suite, clean local run after the change). Post-merge
of main (peer lanes game-sections-3 / claims releases): 2196 passed
with 11 integration failures from the ledgered local-env class
(`test_*_race.py` + btd6 seed — verified PRE-EXISTING: the same set
fails on a pristine origin/main checkout in this container, local DB
residue; CI's required bar is the authority, per the #340 card's guard
recipe);
`python3 bootstrap.py check --strict` green except the DESIGNED
born-red session-card hold (this card, flipped by this commit) and a
pre-existing advisory on a peer claim file
(`control/claims/mining-write-parity-lane.md` claims-format);
`check_sim_gate` OK · `check_compat_frozen` OK · `manifest_compile` +
`check_namespace` clean. `.substrate/guard-fires.jsonl` restored before
commit (never committed).

**Guard recipe:** a blanket rename across `sb/domain/rps/` is a
footgun — `handlers.py` calls BOTH `tournament.state_or_none` /
`tournament.record_move` and the bot-match twins; the
`check_symbol_shadowing` guard forces distinct public names per
package (`bot_state_or_none` / `record_bot_move` /
`set_bot_rng_for_tests`), and the walking-skeleton suite
(`tests/unit/band6/test_band6_rps_tournament.py`) is the test target
that catches a cross-module rename bleed immediately.

## 💡 Session idea

`_bot_matches` state and the tournament bracket are both in-memory and
both forfeit on restart — fine for the shipped parity, but the
checkpoint-row pattern the PvP lane already rides
(`rps_pvp_pending` rows, `sb/domain/rps/ops.py`) would make bot
matches restart-safe for ~30 lines: persist
`{mode, best_of, wins, bot_wins}` per (guild, user) and rehydrate on
the first click after eviction. Worth a slice only if live drives show
players actually losing matches to restarts.

## ⟲ Previous-session review

Previous night-run slice (setup wizard interior, PR #340) left two
trails this session consumed: its session card's guard recipe about the
`parity_replay` DB contamination class (honored — one `pytest tests/`
at a time, no concurrent harness drives; both full runs came back
clean), and its completeness-table edit pattern (strike the Top-gaps
item + flip the row + amend headline counts in the same PR), mirrored
here for item 9. Its "zero unregistered refs" claim held: the rps
manifest's ENSURE_REFS re-arm registered the new refs without a
RefUnresolved anywhere.
