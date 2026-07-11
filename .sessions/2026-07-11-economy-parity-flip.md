# 2026-07-11 — economy parity flip (pending→ported, the nineteenth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `economy` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/economy_cog.py` +
`disbot/services/economy_helpers.py` (`_build_economy_embed`) +
`disbot/views/economy/{main,work,shop}_panel.py` @7f7628e1. Goldens:
`parity/goldens/economy/` — economy_balance_and_daily (INV-F,
balance→daily→balance), sweep_balance, sweep_daily, sweep_economymenu,
sweep_slash_economy, sweep_work. Pre-flip state: 1/6 green (sweep_daily
— the daily card + K7 claim lane shipped with band 3/blackjack).

## What shipped

1. **`!balance` → the shipped Wallet embed** (economy_cog.balance
   verbatim): `💰 {display_name}'s Wallet`, gold accent, avatar
   THUMBNAIL, two inline fields (`🪙 Coins` **bold** `{coins:,}` /
   `🏆 Level`) — a new component-less `economy.wallet_card` panel,
   `session_lifecycle=True` (transient result message, no anchor row —
   the daily-card shape exactly). Pure read: the shipped balance never
   ensured the tracking row (sweep_balance pins the no-economy-row
   delta). The capture twin gained `thumbnail_ref` serialization —
   `_embed_payload` now mirrors the live presenter's `set_thumbnail`
   (sb/adapters/discord/panel_view.py:67); the twin simply lacked the
   field until the first thumbnail-pinning golden.
2. **`!economymenu` → the shipped Economy Panel embed** via
   renderer_override (the cleanup/proof_channel precedent — every
   adjusted surface named): invoker author line, gold accent, FIVE
   inline stat fields (Coins `{coins:,}` / Level / Daily Streak + the
   cooldown-derived `🎁 Daily`/`💼 Work` "✅ Available!"-or-⏰ values),
   footer literal "Use the buttons below to take actions.", no
   description. COMPONENTS delegate to render_panel untouched — the
   shipped glyphs moved INTO the labels ("🎁 Daily" etc., no wire
   emoji field), custom_ids stay the pinned verbatim `economy:*` set ⇒
   zero sim-gate lock/compat rows (playbook 12d). The open runs the
   shipped `ensure_and_get_economy` READ-THAT-WRITES
   (store.ensure_tracking_row, autocommit like the oracle's
   pool.execute) — the golden pins the zero-row economy db_delta on
   every hub open. Author name/avatar ride the utility
   guild-directory read port (parity boot arms it; degrades to no
   author line, never invented data).
3. **`/economy` defers ephemeral then follows up** — the shipped
   `economy_slash` was `safe_defer(ephemeral)` + `safe_followup`
   (golden: type-5 `{"flags": 64}` ack + flags-64 followup), so the
   slash CommandSpec declares `DeferMode.AUTO` +
   `ReplyVisibility.EPHEMERAL`, overriding the slash-PanelRef type-4
   default (the INVERSE of trap 4: shipped slash panels that DID defer
   need AUTO declared, exactly as type-4-direct ones need NONE).
   Interaction present ⇒ no message_ref ⇒ no anchor row (golden pins
   economy-row-only delta).
4. **`!work` → the shipped Job Center dropdown** — jobcenter reshaped:
   `session_lifecycle=True` (run-minted `<cid:1>` select, no anchor
   row), blue accent (`style_token="blue"`, 3447003 = INFO_COLOR), NO
   nav controls (the shipped bare-`!work` `_WorkView` carried only the
   select), renderer_override for the two INLINE Level/Coins fields
   (Coins UNFORMATTED — `{coins} 🪙`, the oracle read
   `xp_row['coins']` raw) + footer literal "Pick a job from the
   dropdown.", grammar TextBlock description kept verbatim. The jobs
   provider now yields RICH options (label `{emoji} {Title}`, value,
   description `Base pay: {pay} 🪙  |  +{xp} XP  |  Tier {tier}` —
   BASE pay, not mastery-adjusted). Shipped `work` took NO argument
   (economy_cog.py: `async def work(self, ctx)`) — the handler's old
   `!work <job>` argv lane was NEW-code drift and is gone; the audited
   `economy.work` op runs from the selector pick only. The command
   start runs the shipped ensure (golden pins the zero-row delta).

The flip: `parity.yml economy: ported` + ratchet
`economy: {events: 2, tables: 5, settings: 0}` (scratch-learned via
--write-ratchet on a copy, header restored, hand-applied). Gate leg:
98/98 goldens across 19 ported subsystems GREEN against real Postgres.
Dashboard 18 → 19 of 49. Full suite 1292 passed.

## A-16 R2: three table exemptions, ONE reviewed vocabulary growth

Economy declares 5 stores; goldens touch `economy` +
`economy_audit_log`. The other three:

- `table:economy_balances` — `env-keyed-integration` (the #145 codex
  ruling: NO golden corpus-wide carries the table ⇒ NOT
  covered-elsewhere; corpus-scanned). Ground = the capture SCHEMA
  EPOCH: the table is the ledgered-coins boundary's NEW home; old-bot
  captures stored coins on the `xp.coins` alias (the `xp-coins-alias`
  disposition documents this verbatim). Wallet-mutation bytes stay
  pinned through economy_audit_log deltas in this row's own gating
  goldens.
- `table:job_progress` + `table:inventory` — **new reason class
  `select-driven` (D-0064)**, the D-0063 structural-unreachability
  test re-argued for the select ingress per that record's own
  instruction: the ONLY shipped write paths are the Job Center /
  shop dropdown PICKS (run-minted ids → `<cid:N>` at import →
  cases.py returns None; click steps carry no component `values`), so
  no imported golden can EVER carry the inserts. `modal-driven` was
  NOT reused — a select pick is not a modal submission and D-0063
  scopes itself to modals. Flagged for review in the PR body + the
  codex question. Deleted-when-armed posture identical to D-0063.

## Notes

- sweep_work went green BEFORE the jobcenter renderer_override landed
  in the same session (the spec reshape + rich provider alone matched
  bytes only after the override; order within one commit — no
  intermediate state shipped).
- Compensator surface untouched: no op lanes changed; the allowlist
  stays EMPTY. The two writes this flip ADDS (ensure_tracking_row)
  are idempotent INSERT..ON CONFLICT DO NOTHING get-or-creates
  mirroring the oracle's untransacted read-that-writes — no EFFECT
  legs follow them inside any workflow.
- Reasonless invoking-message deletes ride the ruled
  `invoking-message-deletion` disposition; `xp.coins` rides
  `xp-coins-alias`; ai_decision_audit/kernel rows ride
  `kernel-surface-drift` — zero new disposition work.
- `_KNOWN_ENSURE_ONLY` untouched — economy panels/handlers already
  registered at import pre-flip.
- Deliberate deviation (unpinned, noted): the hub's 💼 Work button now
  opens the session Job Center as a fresh send; the shipped
  `_WorkSubView` edited the hub message in place with a Back button —
  no golden drives that click; the in-place-edit sub-panel lands with
  the panel-refresh slice if ever pinned.

## 💡 Session idea

The proof_channel card predicted this wall: "no golden CAN carry the
row" now spans THREE grounds (env resource: proof_channel_locks;
schema epoch: economy_balances; input vocabulary: btd6_strategies +
job_progress/inventory). A single `capture-unreachable` umbrella class
with a mandatory ground token (`env:`/`schema:`/`input:`) would
replace three stretched classes with one honest one — raise it before
the ticket/karma flips hit the same wall.

## ⟲ Previous-session review

proof_channel's codex-triage list transferred at full value: its
ruling #1 (covered-elsewhere needs the TABLE's rows, not related
bytes) directly shaped the economy_balances row; its DeferMode finding
generalized cleanly to the inverse slash-defer case here.
