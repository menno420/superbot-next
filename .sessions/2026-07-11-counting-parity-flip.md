# 2026-07-11 — counting parity flip (pending→ported, the twenty-fifth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `counting` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/views/counting/hub_panel.py`
(_CountingHubView / _ChannelPick / _ModePick / _RefreshButton /
build_embed) + `cogs/counting/_channel_manager.py` @58040c6
(reconstructed via search_code fragments — full-file oracle reads stay
denied, playbook trap 3/15f). Goldens: `parity/goldens/counting/` —
sweep_count_info, sweep_countingmenu, sweep_counttop. Pre-flip 2/3
(count_info + counttop guard bytes already green from the band-6 port)
→ post 3/3.

## What shipped

1. **The shipped Counting Manager view** replaces the band-6 declarative
   hub invention (7 buttons + enum selector + engine nav): a
   session-lifecycle root panel (run-minted `<cid:N>` ids, ZERO
   `panel_anchors` rows) with the shipped three inactive-state rows —
   the type-8 text-channel picker ("Select a channel to manage…",
   `required: false`, `channel_types: [0]` — the #167
   LogChannelSelectView wire twin), the 9-mode Enable-Here select
   (provider-fed rich options `{label: mode.capitalize(), value: mode}`
   over the shipped `_ENABLE_MODES` order — trap 14i; "Enable counting
   here — pick a mode…", `required: true`) and the "🔄 Refresh" grey
   button (emoji INSIDE the label string) — under the blue "🔢 Counting
   Manager" embed with the shipped not-active description (incl. the
   `<#<#general>>` double-wrap: the shipped f"<#{cid}>" around the
   Normalizer's channel token) + "Select a channel above to manage it."
   footer. NO nav row (the shipped root panel was allowlisted back-less;
   `NavigationSpec(show_help=False, show_home=False)`).
   goldens/counting/sweep_countingmenu pins every byte.
2. **State-keyed component assembly in the renderer_override** (the
   shipped `_rebuild` if/else — one step past the #145/12c
   state-dependent-description precedent): active target ⇒ the four
   shipped staff buttons (🔄 Toggle Turns / ♻️ Toggle Reset / 🔁 Reset
   Count / 🛑 Disable Here) + the Managing embed (Mode / Current Count /
   Taking Turns / Reset on Wrong inline fields, "Buttons operate on the
   selected channel." footer), no ModePick; inactive ⇒ ModePick, no
   staff buttons. `SelectorSpec` has no `visible_when` field, so the
   override delegates to `render_panel` and drops exactly the other
   state's components by CANONICAL id (overrides run before
   `_mint_ephemeral` and before the refresh remap — trap 9); every kept
   component's bytes come from the declared spec. Pick memory is
   process-local per (guild, invoker) — the logging `_route_choice`
   class; never golden-rendered, so trap 20 does not bind.
3. **Click lanes (all unpinned — D-0064's select territory)**: channel
   pick re-targets and re-opens the hub; Enable-Here runs the existing
   audited `counting.enable_channel` op on the SELECTED channel (the
   shipped whitelist flow); the staff buttons inject the selected
   channel through the existing `_target_channel` arg seam and delegate
   to the band-6 routes (`counting.toggle_flag` / `reset_count` /
   `disable_channel` ops). Ledgered deviation: the shipped view edited
   itself in place — the port re-opens a fresh hub send (the projmoon
   edit-in-place class).
4. **parity.yml**: counting ported (25/49); ratchet
   `counting: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp). ONE depth exemption:
   `table:counting_state` under the EXISTING `select-driven` class
   (D-0064) — the only capture-reachable write ingress is the
   run-minted Enable-Here pick; `!start_match` sits behind the
   D-0030/trap-17 create-channel wall (never swept into the imported
   corpus) and the mutation commands touch only an already-active
   channel no capture case establishes (the pinned "Counting game is
   not set up for this channel." refusals). Zero new
   exemption/disposition classes; compensator allowlist stays EMPTY.
   Decision record D-0068.

## Traps confirmed / new intel

- **SelectorSpec has NO `visible_when`** (only PanelActionSpec does) —
  a shipped view whose SELECT visibility is state-keyed cannot use the
  grammar gate; the sanctioned move is the renderer_override dropping
  canonical-id-named components (D-0068 wording), not SelectorSpec
  schema growth for a state no golden exercises.
- **The channel-select + `required` wire machinery from #167 is fully
  reusable** — SelectorKind.CHANNEL → type 8 + `required: false`, ENUM
  min_values≥1 → `required: true`; zero transport work this flip.
- **A band-6-born subsystem can flip 2/3-green**: only the panel byte
  gap was real; the guard-byte sweeps were already exact from the
  original port. Check the isolation replay FIRST — the red list is the
  work list.
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 12d (session
  panels, no overrides/commands ⇒ ZERO sim-gate/compat churn — lock
  KEY set unchanged, values stay 0), 14i (dict options pass through
  verbatim, default:false added), 15f (search_code phrases), 16e
  (importlib `_replay_corpus`) confirmed as written.

## Verification

- goldens/counting 3/3 green (isolation replay); full gate **161/161
  across 25 ported** on real Postgres; report leg 199/465 green,
  465/465 replayable; check_parity_depth OK — 49 subsystems (25
  ported), 465 goldens; check_sim_gate OK (1040 [A], 355 auto-exempt);
  check_compat_frozen OK; check_namespace / intent_survival / slash_cap
  / egress / no_skip clean; unit suite **1356 passed, 2 skipped** local
  (canonical order).

## 💡 Session idea

Three counting-family sweeps still sit in `_unmapped`
(sweep_count_rules, sweep_reset_count, sweep_toggle_reset_on_wrong_count
— the first pins the green rules embed, the other two the same guard
byte the flipped row already answers); an aireview-style re-home slice
(#155 class) would move them under `goldens/counting/` and likely go
green on the first replay, growing the gate by 3 for near-zero port
work.

## ⟲ Previous-session review

(This previous-session review covers the logging flip, #167.) The
logging card's new capabilities carried exactly as advertised: the
CHANNEL-select wire twin and the `required` semantics needed ZERO
transport work here, and trap 19's K1 bare-token warning was pre-empted
by keeping `counting_`-prefixed internal ids. Trap 20 (seed, don't
accumulate) was checked and found NOT to bind — the counting pick
memory is never golden-rendered; the distinction the trap draws
(golden-rendered vs mere process-local UI state) held up on first
contact.
