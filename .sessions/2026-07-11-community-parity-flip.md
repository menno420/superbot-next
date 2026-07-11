# 2026-07-11 — community parity flip (pending→ported, the thirty-fifth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `community` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/views/community/hub.py`
(`build_community_hub_panel` / `build_community_hub_embed` /
`discover_community_children` + the shared `HubChildButton` primitive)
and `disbot/utils/subsystem_registry.py` child entries, reconstructed
via search_code fragments (trap 3/15f). Goldens:
`parity/goldens/community/sweep_community.json` (the `!community`
prefix open) + `sweep_slash_community.json` (the `/community` ephemeral
type-4 twin, flags 64). Pre-flip 0/2 → post 2/2 (green on the FIRST
isolation replay).

## What shipped

1. **The shipped 🌱 Community Hub** replaces the invented band-4
   4-button hub (`sb/domain/community/panels.py community_hub_spec` —
   the D-0067 ORACLE-WINS reshape lane): the two-section bullet legend
   description ("• {emoji} **{display}** — {desc}" builder verbatim),
   GENERAL_COLOR green (existing `green` token 3066993), the "Only you
   can interact with this panel." footer via a footer-ONLY
   renderer_override (the utility/admin precedent), and the shipped
   TEN child buttons: seven blurple primary children (Support Tickets /
   XP & Levels / Karma / Community Spotlight / Welcome / Server
   Counters / Roles, rows 5+2) + three grey cross-links (Counting /
   Word Chain / Leaderboard).
2. **The roster is a capture-world PIN** (the utility UTILITY_CHILDREN
   precedent): the shipped view ran `discover_community_children()` per
   render over the subsystem registry; the spec pins the snapshot the
   goldens captured (`COMMUNITY_PRIMARY` / `COMMUNITY_CROSS_LINKS`) —
   re-derivation from the manifest inventory is the ledgered follow-up.
3. **Persistent ids through the session mint**: the shipped
   child-forwarding buttons carried EXPLICIT `community:open:<key>`
   custom_ids inside a timeout session view — `custom_id_override`
   rides them verbatim through `_mint_ephemeral` (the utility
   `utility:open:<key>` precedent); `session_lifecycle=True`, no
   `panel_anchors` row in either golden (trap 11d). The row-4 📚 Help
   button is the grammar's OWN `nav:help` slot
   (`NavigationSpec(show_help=True)` — custom_id/label/style all
   grammar-native, both goldens pin the bytes).
4. **Every child routes to its REAL ported surface** (no golden drives
   clicks; the shipped HubChildButton forwarded into each child cog's
   `build_help_menu_view`): ticket.hub / xp.hub / karma.card_view /
   community_spotlight.hub / welcome.status / counters.status /
   role.hub / counting.hub / chain.hub / leaderboard.board. K1 claims
   action_ids bare (trap 19/21) — `co_<key>` ids keep the namespace
   clean (utility owns `open_<key>`, ticket owns `open_ticket`).
5. **Trap-24 drift check: NO drift** — current-head fragments (the
   description builder, the "Community games & standings" heading, the
   registry's ticket row display_name/description/emoji) match the
   corpus goldens byte-for-byte. **Trap-28 pre-step**: no
   community-family entries in `_sweep_skips.json`; nothing newly
   declared beyond the goldens' own surfaces.
6. **parity.yml**: community ported (35/49 at this branch's merge
   order); ratchet `community: {events: 1, tables: 2, settings: 0}`.
   **ZERO depth exemptions, ZERO new reason classes, ZERO decision
   records** (stores/events/settings all declared empty). Compensator
   allowlist stays EMPTY (read-only slice). Lock file amended
   ADDITIVELY (3 arrangement rows, legacy-seed Exempt) + baseline
   regen; compat pin grew EXACTLY the 10 verbatim `community:open:*`
   custom_id pins (`check_compat_frozen --write`, reviewed by hand);
   snapshot recompiled.

## Traps confirmed / new intel

- **The utility mixed-id precedent generalizes to ALL-pinned session
  views**: community's buttons are ALL override-pinned (utility mixed
  minted + pinned) — `_mint_ephemeral` skips every one, and the golden
  still shows a session view (no anchors) with fully persistent wire
  ids. Session-lifecycle ≠ minted ids; it's the anchor/timeout
  semantics.
- **nav:help is grammar-verbatim**: the shipped row-4 "📚 Help"
  button's custom_id/label/style match `render.py`'s injected slot
  byte-for-byte — declaring `show_help=True` costs zero override work
  (first golden to pin the slot on a flip since ticket's hub).
- Traps 1/12d/16e/25/27 confirmed as written.

## Verification

(Ladder run at the post-#186-merge state — the numbers below are from
the final serial ladder on this PR's head after merging main forward.)
See the PR body for the verbatim gate/report/pytest lines.

## 💡 Session idea

The three `_unmapped` role-family sweeps (sweep_roles,
sweep_rolecreator, sweep_rolesettings) pin the SAME rolemenu view the
role row's own golden pins — a #155-style re-home candidate the moment
the role flip lands (grep confirmed identical field lists). Same for
checking whether other `_unmapped` sweeps alias ported hubs.

## ⟲ Previous-session review

(This previous-session review covers the admin flip, #186 — same
session, earlier lane slot.) The admin card's 12d nuance (a session
panel GAINING a LayoutSpec mints the 3 arrangement lock rows) repeated
here exactly as recorded — the community reshape hit the same three
RED sim-gate rows and the same additive legacy-seed fix applied
cleanly. The admin PR also hit the trap-13a Actions stall (zero
pull_request runs for its head); the one sanctioned empty-commit
retrigger was burned there — this PR rode the stall out instead.
