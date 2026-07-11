# 2026-07-11 — counters parity flip (pending→ported, the thirty-first row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `counters` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/counters_cog.py` +
`services/counter_config.py` + `services/counter_service.py` at the
CORPUS sha 7f7628e1 (search_code fragments — full-file oracle reads
stay denied). Goldens: `parity/goldens/counters/sweep_counters.json`
(prefix `!counters`) + `sweep_slash_counters.json` (the `/counters`
ephemeral type-4 slash twin — the singleton run's first slash golden).
Pre-flip 0/2 → post 2/2. Wave-8 R2-singleton 2 of 2 (image_moderation
✅ → counters), next the server_management prefix sibling.

## What shipped

1. **The shipped counters policy embed** replaces the generic hub
   route: `counters.status`, a component-less `session_lifecycle=True`
   result card (the recipe's seventh use). renderer_override composing
   the shipped embed: `**Master:** {flag}`, one row per kind IN ORDER
   (`**{kind.capitalize()}** → {channel mention | *(unbound)*}` +
   `-# → \`{rendered name preview}\``), the ~10-min footer literal
   ("Configure in !settings → Counters. Channels refresh every ~10 min
   (Discord rename rate limit)."), `blurple` (existing token 5793266 =
   discord.Color.blurple(), trap 12e held).
2. **The slash twin costs ZERO manifest posture edits**: the `counters`
   CommandSpec was already `kind=BOTH`; slash+PanelRef resolves
   `DeferMode.NONE` (type-4 direct — the resolver default, trap 14a)
   and `Audience.INVOKER` panels present ephemeral (flags 64) on
   interaction surfaces while staying public channel sends on prefix —
   the transport's audience rule delivers the split both goldens pin.
3. **NEW SHARED-TWIN INTEL (the flip's one real fix)**: discord.py's
   `InteractionResponse.send_message` OMITS the `components` key when
   no view rides along — the capture twin's type-4 panel path
   (`ParityResponder.present_panel`) unconditionally carried
   `components: []` and red-flagged the slash golden
   (`$.steps[0].calls[0].payload.data.components: unexpected`). Fixed
   in `sb/adapters/parity/transport.py`: the type-4 panel data now
   drops an EMPTY components list (non-empty views unaffected —
   servermanagement's hub still pins its rows). Corpus-scan proof: ZERO
   goldens pin an empty `components` key on any type-4; exactly one
   (this one) pins its absence. Prefix channel sends keep
   `components: []` (their goldens pin it). This is the trap-14b class
   (a never-before-pinned wire surface: the corpus's first
   component-less type-4 PANEL response).
4. **Shipped read set as a domain service**
   (`sb/domain/counters/service.py`): `CounterPolicy` (master flag + 3
   channel bindings + 3 templates through THE kernel settings/binding
   seams) and `CounterCounts` with shipped `compute_counts` semantics —
   total prefers `guild.member_count`, bots from the member cache,
   humans = remainder. The bots split rides the EXISTING utility
   guild-directory port: `GuildInfo` grew a defaulted `bots: int = 0`
   field (the shipped read joined the same gateway guild cache; no new
   seam) and the parity boot's `_WorldGuildDirectory` carries the
   capture value (`bots=1` — the bot user; goldens pin 4/3/1).
   `render_counter_name` upgraded to the shipped literal
   (`template.replace("{count}", f"{count:,}")[:100]` — comma
   thousands + the 100-char channel-name cap; the band-2 `str(count)`
   stub under-rendered ≥1000 counts).
5. **parity.yml**: counters ported (31/49); ratchet
   `counters: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp — trap 14d; the slash case
   contributes zero deltas: ephemeral + no chat XP on interactions).
   **ZERO depth exemptions, ZERO new classes, ZERO decision records**
   (`stores=()`/`events=()`; the rename loop arms with the channel-ops
   port). Compensator allowlist stays EMPTY (read-only slice).

## Traps confirmed / new intel

- Trap 24 drift check: PASSED — the current-head fragments compose to
  both goldens' bytes exactly (the drift class stays automod-only).
- Trap 14a inverse confirmed at the resolver source
  (`sb/kernel/interaction/resolve.py _surface_default_defer`): slash +
  PanelRef defaults `DeferMode.NONE` — no explicit declaration needed
  (the #132 explicit `DeferMode.NONE` was belt-and-braces, not load-
  bearing).
- NEW: the type-4 empty-components omission (item 3) — when a slash
  golden pins a COMPONENT-LESS embed response, expect the twin's
  unconditional `components: []` to red it; the fix is the
  drop-when-empty filter on the type-4 panel path with a corpus-wide
  scan proving no golden pins the empty key.
- Traps 1, 12d, 12e, 16e confirmed as written.

## Verification

- goldens/counters 2/2 green (prefix green on the FIRST isolation
  replay; slash green after the item-3 twin fix); full gate **174/174
  across 31 ported** on real Postgres (the transport change replays
  EVERY subsystem — the gate is the regression proof); report leg
  **211/465** green, 465/465 replayable; check_parity_depth OK — 49
  subsystems (31 ported), 465 goldens; check_sim_gate OK (1055 [A],
  370 auto-exempt); check_compat_frozen OK; check_namespace / egress /
  no_skip clean; manifest_compile green; unit suite **1356 passed, 2
  skipped** local (canonical order).

## 💡 Session idea

`GuildInfo.bots` is defaulted-0 for the LIVE root (no live
GuildDirectory is armed anywhere yet — grep shows the port installed
only in the parity boot); when the live directory arms, its
implementation must fill `bots` from the member cache or live
`!counters` will render `Bots: 0` — pin that in the arming slice's
walking skeleton. Also: the four_twenty singleton (1 golden) still
wants the footer/title search_code sweep before assuming the recipe.

## ⟲ Previous-session review

(Covers the image_moderation flip, #176.) Its card predicted counters
would need "the trap-14a AUTO+EPHEMERAL defer check that the
prefix-only singletons never exercised" — half right: the slash twin
DID need surface-specific attention, but the bite was the type-4
components key (item 3), not defer posture (the resolver default
already matched the shipped type-4 direct). The recipe's
"reconstruction dominates flip time" held again; the codex follow-up
from #176 (exempt-tail under-report once a settings-mutation surface
can write the exempt keys) is ledgered at the wave-8 heartbeat.
