# 2026-07-10 — ux_lab parity flip (pending→ported, the eighth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Port the `ux_lab` subsystem's golden-pinned surface and flip its
`parity.yml` row pending→ported through the A-16 door — the general/
utility-flip playbook applied to the shipped UX Lab interface-gallery
home panel. Oracle: menno420/superbot `disbot/cogs/ux_lab_cog.py`
(`!uxlab`, alias `interfacelab`, `@admin_or_owner()` + guild-only) +
`disbot/views/ux_lab/home.py` (`build_home_embed` + `UxLabHomeView`);
golden: `parity/goldens/ux_lab/sweep_uxlab.json` (case `sweep.uxlab`,
the subsystem's only golden). The slash twin (`/uxlab`) is the SIBLING
`uxlab` parity row — its flip is the next PR (one subsystem = one PR).

## What shipped

1. **`!uxlab` opens the shipped UX Lab Home card** —
   `sb/domain/ux_lab/` + `sb/manifest/ux_lab.py`: a session-lifecycle
   PanelSpec (`ux_lab.home`) with the shipped bytes — title
   `🧪 UX Lab — interface gallery`, discord.Color.blurple() (new
   `blurple` style token, 5793266), the two-paragraph zero-write blurb,
   the `Exhibits` coverage line + `How to browse` field, the plan-doc
   footer literal (renderer_override, the utility-panel precedent) —
   over the wing rows: Buttons/Selects/Modals/Embeds ·
   Components V2/PIL cards/Mock studio/Probe bench · Compare, each
   button carrying its emoji as a SEPARATE component field (the shipped
   `discord.ui.Button(emoji=...)` wire shape — first flipped panel to
   pin it). Run-minted custom_ids (#117) symbolize to `<cid:N>`; no
   `panel_anchors` row (#118). Replayed byte-green on first try.
2. **The shipped standard-nav row** — unlike general/utility, the
   shipped UxLabHomeView carried `nav:help` + `nav:hub:admin` with the
   HUB's display label: `sb/kernel/panels/render.py` grows
   `HUB_NAV_LABELS` (hub key → shipped subsystem_registry display_name;
   seeded `admin: Administration`, the golden's byte) — the nav home
   slot now renders `↩ <hub name>` with the `Home` placeholder for
   unmapped hubs. `home_hub="admin"` is the rare explicit pin (the
   shipped parent hub, subsystem_registry category `admin`; no live hub
   resolver exists until the admin hub's band ports).
3. **Wing clicks** → polite pending terminals (role/utility-band
   precedent) — the 8 exhibit browsers + ⚖️ Compare are the lab's own
   follow-up slice.
4. **Sim gate** — `manifest/layout/ux_lab.lock.json` legacy-seed Exempt
   rows + baseline regen; compat pin amended additively (`ux_lab`
   subsystem key + the `uxlab`/`interfacelab` command row).
5. **The flip**: `parity.yml` `ux_lab: ported` + the A-16 ratchet row
   `ux_lab: {events: 1, tables: 2, settings: 0}` (minted via
   `--write-ratchet`, re-applied by hand to keep the file's comment
   header). R2 is vacuous (the shipped lab is zero-write — no declared
   surfaces); zero exemptions; the flip is the PR's last commit.

Gate leg: 18/18 goldens across 8 ported subsystems GREEN against real
Postgres. Dashboard moves 7 → 8 ported (of 49); report leg 30 → 31
green (of 465). Full suite 1219 passed.

## Deliberate under-ports (parity beyond the golden, documented in-code)

- **Exhibits line is a pinned literal** — the shipped value was
  registry-derived (`category_counts()` over the 64-pattern registry);
  re-derivation lands with the wings slice.
- **Author lock** — the shipped view was author-locked while replying
  PUBLIC; the grammar couples the invoker lock to the ephemeral INVOKER
  audience, so this ships `Audience.PUBLIC` (blackjack shared-view
  precedent) and the lock rejoins with the wings slice.
- **`nav:hub:admin` routes on click only once the admin hub band ports**
  (`register_hub("admin", ...)`) — the shipped behavior for a
  not-yet-registered hub id is the polite fallthrough; the golden pins
  the render only.

## 💡 Session idea

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no idea. Backfill exists so the strict session-gate's
newest-card-by-mtime pick cannot red CI on this card — see PR #159's card.)

## ⟲ Previous-session review

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no previous-session review.)
