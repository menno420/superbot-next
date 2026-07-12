# 2026-07-12 — casino poker PLAY layer (dealing + betting on the component seam)

> **Status:** `in-progress`

- **📊 Model:** fable · high · feature build (poker play layer, slices 2+3)

## Scope

Slices 2+3 of the poker port. Slice 1 (the betting engine,
`sb/domain/casino/engine.py`) landed on `casino/poker-engine-port` (PR #267);
this branch STACKS on it. Replace the `casino.poker_start` pending terminal
(the D-0045 "dealing arms with the live adapter" block) with a REAL play
layer: deal a hand through the ported engine, drive betting rounds with
buttons on the component seam, and render the public spectator embed + each
seat's private hand as PURE projections of the one engine snapshot — so the
whole play layer is headless-testable and golden-mintable without a live
adapter. Then mint the headless-shaped golden (D-0073) and keep the lobby
OPEN bytes byte-identical.

## What shipped

1. **sb/domain/casino/table.py** — added the two missing shipped constants
   `TURN_SECONDS=90` and `GAME_TIMEOUT=1800` (verbatim from the oracle view).
2. **sb/domain/casino/game.py** (new) — the shipped in-hand half of
   poker_table.py: one live `PokerGame` per channel (process-memory, keyed by
   `channel_id` like the lobby registry). `start_game` seats every lobby
   player on `START_STACK` and deals the first hand; `rng` defaults to the
   global `random` module so a seeded capture is reproducible while live play
   draws OS entropy. Play-chips only.
3. **sb/domain/casino/view.py** (new) — PURE snapshot projections: the PUBLIC
   spectator embed (`public_spectator_view`), the PRIVATE per-seat hand embed
   (`player_hand_view`, the D-0045 deviation made headless), the seat-lobby
   primer, `raise_targets` (the ⬆️/🔥/💥 presets), and `action_button_plan`
   (the headless twin of the dynamic SeatView). Oracle copy carried verbatim.
4. **sb/domain/casino/panels.py** — new `casino.poker_game` panel (PUBLIC,
   CHANNEL_ANCHOR, `session_lifecycle`, `GAME_TIMEOUT`) with the shipped
   SeatView button set on a STABLE layout + a `renderer_override` that reads
   the live snapshot; layout Exempt recorded in the sim overlay.
5. **sb/domain/casino/service.py** — `casino.poker_start` now DEALS and opens
   the public game panel (no longer a blocked terminal); new
   `casino.poker_action` handler maps every button token → the correct engine
   transition → `refresh_session_view` in place, gated to the seat whose turn
   it is (host end-controls to the host). The blackjack solo-table recipe.
6. **sb/manifest/casino.py** — declares the new panel; manifest snapshot +
   sim baseline regrown.
7. **sb/adapters/parity/boot.py** — `reset_case_state` now clears the poker
   lobby + game registries per case (cross-case isolation for the new
   golden; defensive for sweep_poker too).
8. **parity/goldens/casino/casino_poker_full_hand.json** (minted, D-0073) —
   a full headless hand (lobby → seat → deal → check/call betting rounds →
   showdown) captured as the public spectator embed per action, kernel-spine
   surfaces stripped. Double-captured byte-identical before mint.
   `parity.yml source.minted_goldens` 6 → 7; corpus 468 → 469.
9. **tests/unit/band6/test_band6_poker_play.py** (new) — 16 tests: constants,
   the game registry, the pure projections, the panel spec + renderer, and
   the session-action dispatch (each button → the right engine op, out-of-turn
   rejection, full hand to showdown, host deal-next / end).

## The D-0045 deviation (headless-testable, ledgered)

The oracle dealt each player a per-message auto-updating EPHEMERAL hand (live
`InteractionMessage` handles — the "no headless shape" wall). This port keeps
ONE session state and renders both surfaces from `PokerGame.snapshot()`: the
public spectator (board / pot / result — no hole cards) carries the current
seat's action buttons (authority-gated), and each seat's private hole cards
render via the pure `view.player_hand_view` projection. The play layer is
therefore fully headless — driven and golden-minted with no live adapter.
The only owner-armed step left is DELIVERING those private projections to
real ephemeral messages (D-0045 live-adapter).

## Ladder

- (to be filled at close: full pytest tail + bootstrap check tail + the
  casino golden-parity replay result)
