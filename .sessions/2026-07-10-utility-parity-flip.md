# 2026-07-10 — utility parity flip (pending→ported, the seventh row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Port the `utility` subsystem's golden-pinned surface and flip its
`parity.yml` row pending→ported through the A-16 door — the first
SEVEN-golden flip (every prior row carried 1–3). Oracle:
menno420/superbot `disbot/cogs/utility_cog.py` (`_UtilityPanelView`,
`ping`/`avatar`/`info`/`serverinfo`, `myprofile`(+slash)) +
`disbot/views/profile/profile_view.py` (`_CARD_FILENAME`); goldens:
`parity/goldens/utility/` — sweep_utilitymenu, sweep_slash_utility,
sweep_ping, sweep_avatar, sweep_serverinfo, sweep_myprofile,
sweep_slash_myprofile.

## What shipped

1. **The 🔧 Utility Panel** (`!utilitymenu` / `/utility`, ephemeral on
   the slash surface) — blue overview embed, 6-line action legend, the
   `More in Utility` children field (subsystem-registry metadata,
   verbatim), footer `Click an action below.` via a footer-only
   renderer_override (the literal is outside FooterMode's vocabulary);
   rows Server Info/User Info/Avatar (blurple) · Poll/Remind/Invite
   (grey) · ↩ Overview · 💬 General + 🍃 420 (blurple forwards). The
   shipped view MIXED auto-minted ids with explicit persistent
   `utility:open:<child>` ids — `_mint_ephemeral` now keeps
   `custom_id_override` components verbatim inside session views (unit-
   tested; no prior session panel used overrides).
2. **`!ping` send-then-edit** — `open_panel` now returns the session
   message key; the handler refreshes with Gateway/Round-trip fields
   (`f"{ms:.0f} ms"` verbatim — capture world reads `nan ms`), and the
   parity responder grew the message-surface edit path
   (fake_http.edit_message shape: embeds+flags+tts, no content).
3. **`!avatar`** — `RenderedEmbed.image_url` (new, wired through both
   presenters) carries the shipped `set_image` hero avatar.
4. **`!serverinfo`** — a new installable guild-directory read port
   (`sb/domain/utility/service.py`); the parity boot arms the
   capture-world implementation (member_count 4, text_channels 8 — the
   4 world channels + the shipped bot's boot-provisioned 4, which every
   Server Information golden pins). Live arming is the
   moderation-actions-precedent follow-up; until then the entry points
   refuse politely.
5. **`!myprofile` / `/myprofile`** — the profile.png hero-card send.
   The capture twin now mirrors fake_http's multipart collapse: a
   file-bearing send/response records `{"_files": [...]}` only (no
   type envelope) — byte-identical information loss to the old capture.
   Card pixels are a documented stdlib-PNG placeholder; the themed PIL
   renderer + participation card + ProfileHomeView are the profile
   band's parked follow-up (the general-band empty-pool precedent).
6. **Pending terminals** (role-band precedent) for Poll/Remind/Invite
   (reaction egress / timed delivery / invite mint ports not armed) and
   the 420 forward (band not ported).
7. **Sim gate** — `manifest/layout/utility.lock.json` legacy-seed
   Exempt rows (9 assignments: the layout triple + 6 help_section_order)
   + baseline regen; compat pin amended additively (same-PR --write).
8. **The flip**: `parity.yml` `utility: ported` + the A-16 ratchet row
   `utility: {events: 0, tables: 0, settings: 0}` (hermes-shape: the
   manifest declares no stores/events/settings — the surface is reads).
   R2 vacuous; zero depth exemptions.

Gate leg: 17/17 goldens across 7 ported subsystems GREEN against real
Postgres. Dashboard moves 6 → 7 ported (of 49); report leg 23 → 30
green (of 465). Full suite 1196 passed.

## Deliberate under-ports (all unpinned by goldens)

- Poll/Remind/Invite click behavior (shipped: modals + invite mint) —
  pending terminals until their effect ports arm; the shipped modal
  field specs are recon'd in the flip PR for the follow-up.
- Profile card pixels + the profile hub view (see 5).
- Sibling shipped commands `!info`, `!userinfo`, `!remind`, `!clear`/
  `!purge` — entry points not declared yet (`_unmapped` corpus rows).
- The children row is pinned to today's roster (general, four_twenty);
  re-derive from the manifest inventory when more utility children port.

## 💡 Session idea

The capture twin now encodes "multipart loses the JSON body" in TWO
places (rendered_panel_payload and present_panel's interaction branch).
A single `MultipartPayload` marker type the transport methods all
understand would make the next file-bearing band (xp's rank.png is
already in the corpus) a zero-transport-change port.

## ⟲ Previous-session review

The general-flip card's sim-gate warning ("an 8-button panel trips 4
unpinned [A] assignments") was exactly right and saved a debug loop —
utility's 9-action panel plus 6 commands tripped 9, all cleared by the
documented lock-file + regen dance on the first try. What it
under-delivered: no mention that a SLASH surface that answered
type-4-direct in the shipped bot needs `defer_mode=DeferMode.NONE` on
its CommandSpec — the resolver's surface-default AUTO defer produced a
type-5 + followup pair and two red slash goldens until excavated.
