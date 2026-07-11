# 2026-07-11 — proof_channel parity flip (pending→ported, the fifteenth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `proof_channel` parity row pending→ported through the A-16
door. Oracle: menno420/superbot `disbot/cogs/proof_channel_cog.py`
(`!prizemenu` → `_PrizeManagerView`, `!prizestatus`, `!timedprize`,
`+prize`/`-prize`); goldens: `parity/goldens/proof_channel/` —
sweep_prizemenu (the manager-panel send), sweep_prizestatus and
sweep_timedprize (both the shipped `#proof`-not-found guard). The
band-5 manifest already carried the full command family, the K7
lock/unlock compound ops WITH their compensators (the runtime-review
end_access defect was already fixed on main — `END_PRIZE` declares
`compensate_unlock` since #105/#108, `GRANT_PRIZE` `compensate_lock`
since #111; this flip did NOT need to touch the op lanes, and the
compensator allowlist stays EMPTY) and a generic placeholder hub; this
PR replaces the placeholder with the shipped panel bytes.

## What shipped

1. **`!prizemenu` opens the shipped Prize Channel Manager** — the gold
   `ECONOMY_COLOR` embed (`style_token="gold"`, 15844367 — already in
   STYLE_TOKEN_COLORS), the STATE-dependent `build_embed` description
   (`Managing <#ch>` when the binding resolves / "⚠️ No `#proof`
   channel found. Create one first." otherwise) + the footer literal
   "Use buttons below to manage prize access." via renderer_override
   (the cleanup-hub precedent; both adjusted surfaces named in the
   justification), over the shipped rows verbatim: 🏆 Grant Access
   (green) / ⏱️ Timed Access (blurple) / 🔒 End Session (red) on row 0,
   🔄 Refresh Status (grey) on row 1 — emoji IN the labels, no separate
   emoji field, no nav row (`show_help=False, show_home=False`). The
   shipped view was ctx-bound and timeout-based (view-local button
   decorators, no persistent custom_ids) — `session_lifecycle=True`:
   run-minted `<cid:1>`..`<cid:4>` ids, no `panel_anchors` row (the
   golden pins the no-anchor delta). Zero `custom_id_override`s ⇒ zero
   compat-frozen rows, zero lock-file rows (sim gate green untouched).
2. **`!prizestatus` answers the shipped guard byte** — "Channel
   '#proof' not found." (one string; ops.`_resolve_channel` already
   carried the same literal for the timedprize lane, which was the
   row's 1/3 incidentally-green golden at #134).
3. **Composition parity improvement** — the panel + render_hub refs now
   register at module import (the role/handlers pattern), so
   `panel:proof_channel.hub` left the ensure-only burn-down list
   (test_composition_parity's prune rule fired and the row was removed).
4. **The flip**: `parity.yml` `proof_channel: ported` + the A-16
   ratchet row `proof_channel: {events: 1, tables: 2, settings: 0}`
   (xp.awarded / xp + ai_decision_audit — the chat-award lane every
   sweep rides). R2 non-vacuous, first table bite of this shape: the
   manifest declares `proof_channel_locks` but NO golden corpus-wide
   carries a row of it — the capture guild had no #proof channel, so
   every prize-family capture (own goldens + _unmapped
   sweep_+prize/-prize) pinned the not-found guard and the lock-write
   lane never ran. One depth-exemption row under the EXISTING
   `covered-elsewhere` class citing those named siblings (the
   xp.level_up / settings.changed unreachable-surface wording). No new
   classes; settings dimension stays dead code (10c).

Gate leg: 42/42 goldens across 15 ported subsystems GREEN against real
Postgres. Dashboard moves 14 → 15 ported (of 49). Full suite 1281
passed + affected subsets re-run post-flip.

## Notes

- **Deliberate under-port (in the spec justification):** the shipped
  bound-branch "Current Permissions" field renders LIVE channel
  overwrites (`_format_overwrites(ch.overwrites)`) — a Discord READ
  with no capture twin and no pinning golden; it lands with the
  channel-ops slice. The `status_overview` provider the placeholder
  hub used is retired with it.
- The reasonless invoking-message deletes in all three goldens ride the
  ruled `invoking-message-deletion` disposition; the xp rows'
  `coins` column rides `xp-coins-alias` (both ORDER 009) — zero new
  disposition work.
- end_access sequencing (runtime-review 2026-07-10): verified already
  correct on main before porting — both EFFECT legs after DB legs
  declare compensators (#105/#108/#111); nothing in this flip touches
  the op lanes and the compensator allowlist stays empty.

## 💡 Session idea

`table:<name>` exemptions now exist in two flavors — "sibling pins the
write bytes" (cleanup/settings) and "no golden CAN carry the row"
(proof_channel_locks, this flip) — under one `covered-elsewhere` class.
A dedicated `capture-unreachable` reason class would make the second
flavor honest at the vocabulary level instead of leaning on precedent
wording; worth raising when several more not-found-guard subsystems
(quicksetup, channel-ops rows) hit the same wall.

## ⟲ Previous-session review

The xp card's recipe list transferred at full value: the scratch-learn
ratchet dance, the cleanup footer-override precedent and the
session-lifecycle anchor kill each resolved a diff class on the first
try (3/3 green on the first replay after the port commit). What it
under-delivered: nothing warned that adding a module-import
registration (ensure_panel_refs at module bottom) would trip the
composition-parity BURN-DOWN test in the *other* direction — the
fixed-defect prune rule is as load-bearing as the no-new-refs rule.
