# 2026-07-11 — community_spotlight parity flip (pending→ported, the thirty-sixth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `community_spotlight` parity row pending→ported through the
A-16 door. Oracle: menno420/superbot
`disbot/cogs/community_spotlight_cog.py` (`build_spotlight_embed` +
`SpotlightView`) reconstructed via search_code fragments (trap 3/15f).
Golden: `parity/goldens/community_spotlight/sweep_spotlight.json` — the
R2-singleton `!spotlight` sweep. Pre-flip 0/1 → post 1/1 (green on the
FIRST isolation replay).

## What shipped

1. **The shipped SpotlightView main embed** replaces the band-4
   approximation (`spotlight_hub_spec` reshape + a NEW
   renderer_override `community_spotlight.render_hub`): the guild-named
   title ("🌟 Community Spotlight — Parity Test Guild" — the guild
   name through the utility guild-directory read, welcome degradation
   posture), the four shipped fields with EXPLICIT inline flags (three
   `true` + Recent Level-Ups `false` — grammar FieldsBlock 2-tuples
   serialize inline=false, so the embed is delegation-override
   territory, the economy 14c recipe), the shipped clock footer
   ("Updated %H:%M UTC • Use the buttons to explore leaderboards" — the
   capture Normalizer maps any `\d{1,2}:\d{2} UTC` read to `<hh:mm>`,
   so the frozen replay wall-clock is byte-safe), GENERAL_COLOR green.
2. **`overview_fields` grew the shipped 👥 members line** (optional
   `member_count` param — the renderer passes the directory read; the
   legacy FieldsBlock provider stays registered and unchanged) and the
   Richest empty state corrected to the shipped per-field literal
   ("*No coins earned yet*"; XP Leaders keeps "*No activity yet*") —
   both golden-pinned.
3. **Session-view semantics**: the shipped view was a timeout session
   view — `session_lifecycle=True` (run-minted `<cid:N>` ids, no
   `panel_anchors` row — the golden's db_delta carries only the kernel
   ingress rows), nav slots off (the golden pins exactly one component
   row). The four buttons already matched the golden byte-for-byte
   (labels, SEPARATE wire emoji fields — trap 15a, styles
   primary/primary/success/secondary): the band-4 declaration survived
   its first golden contact intact.
4. **Trap-24 drift check: NO drift** — current-head cog fragments (the
   members/XP/coins glance lines, both leader-field empty states, the
   Level-Ups feed literal, the footer builder) match the corpus golden
   byte-for-byte. **Trap-28 pre-step**: no spotlight-family entries in
   `_sweep_skips.json`.
5. **parity.yml**: community_spotlight ported; ratchet
   `community_spotlight: {events: 1, tables: 2, settings: 0}`. **ZERO
   depth exemptions, ZERO new reason classes, ZERO decision records**
   (stores/events/settings declared empty — the level-up feed is the
   declared `xp.level_up` consumption, shipped in-memory posture).
   Compensator allowlist stays EMPTY (read-only slice). ZERO lock/
   compat churn (arrangement unchanged, no overrides — trap 12d's
   clean case); snapshot recompiled.

## Traps confirmed / new intel

- **The Normalizer is shared capture/replay** (parity/harness/
  capture.py `Normalizer`, imported by the replay runner): any
  `\d{1,2}:\d{2} UTC` byte the renderer emits normalizes to
  `<hh:mm> UTC` — shipped wall-clock footers need NO clock seam, just
  the shipped strftime format. Cheaper than the #183 ISO-now world
  seam when the golden already pins the placeholder.
- **A band-4 declarative guess CAN survive its golden** — the four
  buttons needed zero edits; the embed (title/fields/footer) was where
  every diff lived. Check components first: if they match, the flip is
  a pure renderer_override.

## Verification

(Ladder run at the post-#186/#187-merge state — see the PR body for
the verbatim gate/report/pytest lines.)

## 💡 Session idea

`overview_fields`' medal builder (`_medal`) and the top-3 slice are
live surfaces no golden reaches (the capture guild had zero XP/coins) —
when a future capture pins a populated spotlight, diff the shipped
`entry.label` format (`**<@id>** — {coins} 🪙`) against the golden
FIRST; the provider labels were built for the leaderboard surface and
may differ from the spotlight cog's own line format.

## ⟲ Previous-session review

(This previous-session review covers the community flip, same session.)
The community card's "check components first" hunch is exactly what
paid here — its all-pinned-override lesson didn't apply (spotlight's
ids are minted, not pinned), but the shared recipe stack (session view
+ delegation override + guild-directory degradation) now covers three
shapes: pinned-id hubs (community), minted-id hubs (spotlight), and
component-less cards (welcome). The trap-13a stall the admin PR hit is
still the session's only infrastructure drag.
