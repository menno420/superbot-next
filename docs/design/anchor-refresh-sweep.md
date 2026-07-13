# Anchor-refresh sweep — PROPOSED design (game-sections successor)

> **Status:** `ideas`
>
> Owner-reviewable PROPOSAL, NOT a decision. Badge note (flagged): the
> docs badge vocabulary is closed (archive/audit/binding/historical/
> ideas/living-ledger/owner-guidance/plan/reference — no `proposed`
> token), and `plan` would claim a committed build; `ideas` is the
> closest honest token for an undecided proposal (ideas promote to
> plans, Q-0172). The game-sections lane
> ([game-sections.md](game-sections.md) — its ledger entry is the
> decision home) shipped
> next-interaction consistency and named the anchor sweep a successor
> (PR #341 §"Update contract"); scoping that successor surfaced FOUR
> design calls no agent should make alone. This doc lays them out with
> options, recommendation, and cost. `docs/decisions.md`'s entry-status
> grammar is also closed (`decided|superseded|retired` — no
> `proposed`), so this doc is the proposal vehicle; the D-entry (next
> free: D-0083) mints when the owner decides. Citations verified at
> main `de3824b`.

## 1. What the sweep was supposed to be

When a guild's game enablement changes (the game-sections settings
surface),
already-posted channel panels keep showing the old roster until someone
clicks them. Next-interaction consistency (every fresh render
re-resolves at click time) ships with the slice-3 lane (#341, in
flight at writing). The promised sweep would go further: find every
anchored channel message showing an affected panel and EDIT it in
place. Scoping that sweep found it structurally unbuildable today —
four findings, each hiding a design call.

## 2. The findings (verified at `de3824b`)

**F1 — the target population is empty.** The panels that render the
enabled set are session-lifecycle and the engine never anchors session
panels. `games.hub` / `games.world` / `games.world_card` carry
`session_lifecycle=True` (`sb/domain/games/panels.py:222,276,307`), as
does `casino.hub` (`sb/domain/casino/panels.py:174`) and every
blackjack session view (`sb/domain/blackjack/panels.py:187,220,259,
304,331`). The engine skips anchoring for them twice —
`sb/kernel/panels/engine.py:105-110` (`_record_anchor` returns on
`spec.session_lifecycle`, with the comment pinning the shipped
registry's panel-MANAGER-only population) and `:323-326` (the
`open_panel` guard). The leaderboard golden pins the no-anchor-row
delta by absence (`parity/goldens/leaderboard/sweep_leaderboard.json`
carries no `panel_anchors` key). A `panel_anchors`-keyed sweep
therefore never fires for any game hub. *(Drift note vs the parked
finding: `blackjack.hub` at `sb/domain/blackjack/panels.py:109` is NOT
session-lifecycle — it anchors normally; the original `276,307` lines
were its tournament-table/results session views. Immaterial to the
finding: blackjack's hub renders no enablement state.)*

**F2 — `panel_anchors` has `subsystem` but NO panel id.** The
nine-column shape (`migrations/0025_panel_anchors.sql`: anchor_id,
guild_id, channel_id, message_id, subsystem, user_id, is_stale,
created_at, last_updated_at) is pinned verbatim by the
`parity/goldens/help/help_panel_open.json` db_delta. A sweep cannot
know WHICH panel an anchored message shows — only which subsystem
posted it — so it cannot re-render the right panel for multi-panel
subsystems.

**F3 — no code path edits a stored channel message.**
`DiscordPanelPresenter` edits only the interaction's own origin
message (`sb/adapters/discord/panel_view.py:209-219` —
`req.origin.message` on the `edit_message_ref` refresh path). A sweep
must fetch an arbitrary `(channel_id, message_id)` and edit it, which
needs: a new bot-holding adapter (per the `DiscordChannelEmitter(bot)`
precedent, `sb/adapters/discord/egress.py:46-50`), a kernel port for
it, boot wiring after the bot exists (`sb/app/main.py:384`
`bot = gw.build_bot(cfg)`; the emitter precedent installs at `:392`;
note `install_panel_runtime()` runs earlier at `:333`, before any bot),
and a parity-twin + golden story for the new egress wire.

**F4 (secondary) — subsystem→hub mapping is uninstalled at live boot.**
Mapping a changed subsystem to the hub panels that display it needs the
FOLLOW_PARENT hub resolver, which live boot never installs:
`sb/kernel/panels/render.py:246` defaults `_hub_resolver = None`
(installer at `:249`, consumer at `:544`), and nothing under
`sb/app/main.py` calls `install_hub_resolver`.

## 3. Decision call (a) — session-hub anchorability

The sweep is pointless while its targets are never anchored (F1).

- **a1 — flip `games.hub` (+ world/casino hubs) off
  `session_lifecycle`.** Smallest diff, but session_lifecycle also
  drives the session mint / custom-id override machinery those hubs
  use (`games.hub`'s explicit persistent ids ride the session mint —
  `sb/domain/games/panels.py:220-222` comment); conflates two
  behaviors.
- **a2 — anchor session panels too (engine rule change at
  `engine.py:105/:323`).** Touches every session panel in the fleet;
  blackjack tables and poker games would start writing anchor rows
  they can never honor.
- **a3 — a new explicit `anchorable` spec flag** on `PanelSpec`,
  default `not session_lifecycle` (today's behavior byte-for-byte),
  set `True` on the game hubs. Decouples "has a session lifecycle"
  from "worth refreshing in place". **Recommended.**
- **a4 — do nothing.** Next-interaction consistency remains the whole
  contract; the sweep is abandoned.

**Cost (a1/a2/a3):** golden re-mints wherever a newly-anchored open
adds a `panel_anchors` db_delta row (the games sweeps; a2 also the
leaderboard/blackjack/casino deltas), plus a parity decision: are the
new rows a sanctioned delta or a re-cut? a3 confines the re-mint to
the hubs deliberately flagged. A-2 note: a new PanelSpec field is a
spec-grammar growth — schema-growth ledger entry.

## 4. Decision call (b) — panel-id provenance in `panel_anchors`

- **b1 — new `panel_id` column.** Migration `00XX` (next free; ladder
  tip is `0050` at writing) + `help_panel_open` golden re-mint (the
  db_delta grows a tenth column) + A-2 schema-growth ledger entry.
  Honest and future-proof. **Recommended.**
- **b2 — derive the panel as the subsystem's single non-session
  panel.** Zero migration, but fails for any multi-panel subsystem
  and silently mis-renders when a second anchorable panel lands.
- **b3 — encode panel id into the `subsystem` field**
  (`"games:games.hub"`). No migration but corrupts the field every
  existing index/query keys on (`idx_panel_anchors_guild_subsystem`).
  Dirty; rejected.

**Cost (b1):** migration + checksums, one golden re-mint, one ledger
entry. Existing rows get NULL panel_id — the sweep skips them honestly.

## 5. Decision call (c) — the anchor-editor adapter port

No option space to speak of — if the sweep builds, this builds:

- A bot-holding **`DiscordAnchorEditor`** adapter (the
  `DiscordChannelEmitter(bot)` shape, `egress.py:46-50`): fetch
  channel → fetch message → edit(embed, view); typed misses
  (deleted message / channel / permissions) return a signal, never
  raise through the sweep.
- A **kernel port** (install/reset pair, the emitter's
  `install_channel_emitter` pattern) so kernel code never imports the
  adapter.
- **Boot wiring** in `sb/app/main.py` next to the emitter install
  (`:392`) — the bot exists from `:384`.
- **Parity story**: a capture twin for the new egress wire + goldens
  for the refresh edit (what bytes the sweep writes), else the sweep
  is the first unaudited seam that mutates guild-visible messages.

**Cost:** new adapter surface + twin + goldens; test-plane double for
CI (no live Discord in gates).

## 6. Decision call (d) — fan-out + rate limits

- **Resolver install:** boot installs the FOLLOW_PARENT hub resolver
  (`render.py:249 install_hub_resolver`) so subsystem→hub mapping
  exists at live runtime, not only under tests. (Needed regardless of
  the sweep for FOLLOW_PARENT nav honesty — flagged as a candidate
  standalone fix.)
- **Fan-out policy:** refresh only anchors whose panel displays the
  changed subsystem (hub panels of the section containing the toggled
  game), never "all anchors in the guild".
- **Rate-limit posture:** batch per channel and debounce per guild
  (one sweep per settings burst, not one per toggle) — Discord edit
  limits are per-channel; a 10-toggle settings session must not issue
  10x per-anchor edits. **Recommended: debounce keyed on
  (guild_id, panel_id) with a short flush window.**
- **Failure = honest skip + `is_stale`:** a missed edit marks the row
  `is_stale = TRUE` and moves on. Note: `is_stale` currently has NO
  reader — the only touch is `sb/kernel/panels/anchors.py:35` writing
  it back to FALSE on upsert. Marking stale is only honest if
  something eventually reads it (sweep retry, or a reaper that prunes
  stale anchors); otherwise drop the column from the story.

## 7. Recommendation — and the cheap default

**Recommended bundle** (if the owner wants the sweep at all):
(a3) explicit `anchorable` spec flag, (b1) `panel_id` column,
(c) build the editor port with its parity twin, (d) resolver install
at boot + per-(guild,panel) debounce + is_stale-with-a-reader. Order:
(d)'s resolver install and (a3)+(b1) are independently landable
slices; (c) lands last and turns the sweep on.

**The do-nothing alternative is genuinely viable.** Next-interaction
consistency — every fresh render re-resolves at click time — ships
with #341 (in flight at writing) and already guarantees no user
ever *acts* on a stale roster (stale-click deny + fresh re-render).
The sweep buys only cosmetic promptness on already-posted messages,
at the price of a spec flag, a migration, a golden re-mint, a new
audited egress seam, and a rate-limit engine. If that trade reads
poor, decide a4/do-nothing and retire the successor promise
explicitly in the D-entry.

## 8. What this doc is NOT

Not a decision, not an order, not in-flight work. No code, migration,
golden, or D-number accompanies it. When the owner decides:
mint D-0083 citing this doc (whichever way the call goes — a
do-nothing decision is also a decision), flip this badge to `plan`
(build) or `retired` (do nothing), and slice per §7.
