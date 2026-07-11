# 2026-07-11 — channel parity flip (pending→ported, the tenth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `channel` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/channel_cog.py` (`channel_menu`,
`@is_admin_or_owner()`) + `disbot/views/channels/main_panel.py`
(`_ChannelManagerView.build_embed` — title/description/footer/
CHANNEL_COLOR verbatim); golden:
`parity/goldens/channel/sweep_channelmenu.json` (case
`sweep.channelmenu`, the row's only golden). The band-2 manifest had
already declared the 17-command surface with `channelmenu` routed to the
operator-spine placeholder hub; this PR replaces that placeholder with
the REAL shipped panel.

## What shipped

1. **`!channelmenu` opens the shipped Channel Management Panel
   byte-for-byte** — `sb/domain/channel/panels.py`: the 🛠️ blurple embed
   (CHANNEL_COLOR = discord.Color.blurple(); the shipped four-line action
   legend — the fifth button was never in the shipped description) over
   the shipped action rows: ➕ Create Channel (green) / 🗑️ Delete Channel
   (red) / 🔒 Manage Restrictions (blurple) + ↔️ Move / Reorder (blurple)
   / 🔍 Subsystem Visibility (grey), every button carrying its emoji as a
   SEPARATE component field (the shipped `discord.ui.button(emoji=...)`
   wire shape).
2. **Session-lifecycle panel** — the shipped view was a timeout-bound
   author-locked `HubView` (the root of the channels navigation stack),
   so `session_lifecycle=True`: run-minted `<cid:N>` custom_ids (#117),
   no `panel_anchors` row (#118), `Audience.INVOKER` (the shipped
   ctx.author lock), and the shipped standard nav row — `nav:help` +
   `nav:hub:admin` "↩ Administration" (the shipped parent hub is `admin`;
   docs/help-command-surface-map.md "hub child (Admin)").
3. **The author-lock footer literal** via `renderer_override`
   (`channel.render_hub`) — "Only the command author can interact with
   this panel." is outside FooterMode's vocabulary (the utility/ux_lab
   precedent; justification carried on the spec).
4. **Pending action terminals** — the shipped sub-panels
   (create/delete/restrict/move/visibility — disbot/views/channels/) are
   the channel-ops Discord-mutation slice (D-0030, the named successor);
   every hub click lands on the declared + honest refusal terminal
   (role/utility-band precedent). Refs register at module import (the
   composition-parity invariant).
5. **Sim gate** — manifest/layout/channel.lock.json gains the three
   channel.hub arrangement rows with legacy-seed Exempt provenance
   (additive; the band-2 command rows stay) + baseline regen; compat pin
   unchanged (command roster untouched; `channelmenu` gains the shipped
   `administrator` tier).
6. **The flip**: `parity.yml` `channel: ported` + the A-16 ratchet row
   `channel: {events: 1, tables: 2, settings: 0}` (xp + ai_decision_audit
   from the ported message pipeline). R2 vacuous (channel declares no
   stores/events/settings); zero exemptions; the flip is the last commit.

Gate leg: 24/24 goldens across 10 ported subsystems GREEN against real
Postgres. Dashboard moves 9 → 10 ported (of 49); report leg 32 → 33
green (of 465). Full suite green.

## Notes

- The reasonless invoking-message delete in the golden rides the ruled
  `invoking-message-deletion` disposition (ORDER 009) — no new classes.
- Under-port carried in-code: the five sub-panels port with D-0030; the
  hub's buttons refuse honestly until then.

## 💡 Session idea

`manifest/layout/<sub>.lock.json` overlays are load-bearing for OTHER
subsystems' sim-runner tests (the monkeypatched gate tests read the
overlay files from disk): a flip that REGENERATES a lock file instead
of amending it silently strands the band-2 command pins in the baseline
and only `tests/unit/sim_runner` catches it. A checker rule — "a lock
file diff may only add entries unless the manifest dropped the surface"
— would make the amend-vs-overwrite mistake impossible.

## ⟲ Previous-session review

The uxlab-flip card's promise that the twin-row flip is
"near-mechanical" held for this different-shape case too: the
general/ux_lab panel playbook (session_lifecycle + separate-emoji +
footer renderer_override + HUB_NAV_LABELS) replayed the channel golden
green on the FIRST attempt. What it under-delivered: neither twin card
mentioned that a subsystem with a pre-existing band-2 lock file needs
the amend (not overwrite) move — this session tripped it and burned a
test-suite cycle finding the stranded pins.
