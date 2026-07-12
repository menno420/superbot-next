# 2026-07-12 — creature native user-select picker + member bot-flag seam + Rematch

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The outstanding creature-PvP tail (the seam consumers the D-0079 battle port
left dormant), ported faithfully to the oracle (menno420/superbot @ 7f7628e1 —
`disbot/views/creature/menu.py` `_OpponentSelect`, `views/creature_battle/
rematch.py` `CreatureRematchView`, `cogs/creature_battle_cog.py` the bot guard).
Three slices, one branch:

- **Slice 1 — member bot-flag seam + the opponent.bot guard.** `MemberInfo`
  grows `is_bot: bool = False` (`sb/domain/utility/service.py`), populated in
  both directory twins (live `sb/adapters/discord/utility_reads.py`, parity
  `sb/adapters/parity/boot.py`). The dormant `opponent.bot` guard in
  `creature.cbattle_route` goes LIVE — `!cbattle @bot` → `🤖 You can't battle a
  bot — challenge a real trainer!` — read through the directory (kernel stays
  Member-free), degrading to no-block when headless.
- **Slice 2 — native MEMBER picker primitive + retire the hub-Challenge pending
  terminal.** Three seam branches mirror the existing ROLE/CHANNEL natives so a
  `SelectorKind.MEMBER` selector renders as a Discord user_select (wire type 5):
  the kernel materializer (`sb/kernel/panels/render.py`), the live presenter
  (`sb/adapters/discord/panel_view.py` → `discord.ui.UserSelect`), and the
  parity output (`sb/adapters/parity/transport.py` type-5). The hub Challenge
  button opens the new `creature.challenge_select` picker; its selection routes
  through the existing `args["values"]` path into `creature.challenge_pick` (the
  non-member / bot / self guards, then the challenge open). The
  `creature.challenge_pick_pending` terminal (the repo's only opponent picker
  refusal) is RETIRED.
- **Slice 3 — the Rematch button.** The oracle `CreatureRematchView` 🔄 Rematch
  affordance rides the resolved outcome card (accept/decline disabled, Rematch
  live; either fighter may click). It re-issues a fresh challenge via the
  shared challenge-open path (`creature.challenge_rematch`) — no new battle
  logic, no picker.

## Verification (local, real Postgres, pristine parity_replay DB)

- `python3 -m pytest tests/ -q` — (recorded on completion)
- `python3 bootstrap.py check --strict` — all checks passed
- `python3 tools/run_golden_parity.py --gate` — GREEN, 463 goldens / 51 ported

## Goldens

- NEW `parity/goldens/creature/creature_cbattle_bot_guard.json` — `!cbattle`
  against the guild bot member → the opponent.bot BLOCK (the `is_bot` seam).
- NEW `parity/goldens/creature/creature_challenge_picker.json` — hub Challenge →
  native user_select OPEN (wire type 5) → select a trainer → the challenge card
  opens (the selected id on the ordinary select `values` round-trip).
- RE-MINTED `parity/goldens/creature/creature_battle_accept.json` — the resolved
  outcome card now carries the live 🔄 Rematch button.
- A rematch-CLICK golden is NOT cleanly capturable (the outcome card is an
  in-place edit whose session-minted button id has no click-targetable message
  id) — the affordance's rendered bytes are pinned via `creature_battle_accept`;
  the handler is unit-covered.

## Decision

- `[D-0081]` — the picker / bot-flag / Rematch faithful-port ruling.
