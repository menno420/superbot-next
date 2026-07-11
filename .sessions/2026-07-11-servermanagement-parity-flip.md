# 2026-07-11 — servermanagement parity flip (pending→ported, the eleventh row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `servermanagement` parity row (the `/server-management` slash
twin — the sibling `server_management` row carries the `!servermanagement`
prefix golden and flips separately) pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/server_management_cog.py` +
`disbot/views/server_management/hub.py` (`build_server_management_hub` +
`ServerManagementHubView`) + `disbot/services/server_management_hub.py`
(the read-only badge composer); golden: `parity/goldens/servermanagement/
sweep_slash_server-management.json` (case `sweep.slash_server-management`,
the row's only golden).

## What shipped

1. **`/server-management` opens the shipped Server Management Hub
   byte-for-byte** — `sb/domain/server_management/panels.py`: the 🧭 red
   embed (entry-point blurb; the two read-only health fields — `Managers`
   badges + `Overall configuration health`; the "Read-only summary ·
   click a manager to open it" footer via renderer_override) over the
   shipped manager rows: 🛡️ Moderation / 📺 Channels / 🎭 Roles (blurple)
   + 🧹 Cleanup (grey) / 🧩 Setup (green) + 🔓 Access Map / 👁 Help
   Preview / ✏️ Help editor / 🔄 Refresh (grey), emoji IN the labels,
   every button carrying its shipped PERSISTENT custom_id verbatim
   (`server_management:<key>` via custom_id_override — the economy-hub
   precedent; K1: bare `refresh` is treasury's claim, so the action_id is
   `sm_refresh` under the verbatim wire override, the general_overview
   precedent).
2. **Direct ephemeral type-4** — `DeferMode.NONE` on the slash
   CommandSpec (the utility-flip excavated trap, applied by rule) +
   `Audience.INVOKER` (the golden pins flags 64). The prefix front door
   keeps the same panel route and gains the shipped administrator tier.
3. **Routing** — Channels forwards to the PORTED `channel.hub` (#131);
   Setup to the band-1 `setup.hub` (the shipped hub's own wizard entry);
   Refresh re-renders in place (REFRESH_PANEL). The unported managers
   (moderation/roles/cleanup/access-map/help-preview/help-editor) land on
   declared + honest pending terminals, registered at module import (the
   composition-parity invariant).
4. **Sim gate** — manifest/layout/server_management.lock.json gains the
   three hub arrangement rows with legacy-seed Exempt provenance
   (additive; the band-2 command rows stay) + baseline regen; compat pin
   amended ADDITIVELY (9 new `server_management:*` legacy custom_ids —
   gate 6 fired as designed).
5. **The flip**: `parity.yml` `servermanagement: ported` + the A-16
   ratchet row (the golden is a pure interaction-response case — no
   db_delta, no events). R2 vacuous (no declared stores/events/settings);
   zero exemptions; the flip is the last commit.

Gate leg: 25/25 goldens across 11 ported subsystems GREEN against real
Postgres. Dashboard moves 10 → 11 ported (of 49); report leg 33 → 34
green (of 465). Full suite 1249 passed.

## Notes

- **Deliberate under-port (in-code note):** the shipped health badges
  are LIVE reads (bot permissions / role-hierarchy feasibility / the
  cleanup+setup diagnostics report). Those reads belong to the
  specialised manager slices, so the golden-pinned badge literal ships
  now (the ux_lab Exhibits-line precedent) and re-derivation lands as
  each manager ports.
- The sibling prefix golden (`server_management` row) replays to 2 diffs
  after this PR: the shipped ANCHORED persistent prefix panel recorded a
  `panel_anchors` row and a fourth component row — that anchor semantics
  is the prefix row's own flip concern, deliberately not smuggled in
  here.

## 💡 Session idea

`session_lifecycle=True` is doing double duty: it means "run-minted ids
+ no anchor + never-strand exemption" for game views, but an
override-pinned persistent hub (this flip) uses it ONLY for the last two
effects — nothing is minted. A distinct `PanelSpec` posture (e.g.
`anchorless=True` or `NavigationSpec(root=True)`) would let the grammar
say "top-of-stack operator hub with no nav row" without borrowing the
game-view flag; worth raising before a third hub borrows it.

## ⟲ Previous-session review

The channel-flip card's idea ("a lock-file diff may only add entries")
proved immediately load-bearing: this flip AMENDED
server_management.lock.json (2 band-2 command rows kept) on the first
pass because the channel session burned the cycle learning it. What the
channel card under-delivered: it did not flag the K1 repo-global
action_id claim as a flip-time cost — this hub's bare `refresh` collided
with treasury's and needed the general_overview rename move
re-excavated from #123's commit message.
