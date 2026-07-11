# 2026-07-11 — admin parity flip (pending→ported, the thirty-fourth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `admin` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/admin_cog.py` (`_AdminPanelView`
— the consolidated Server & Admin section, oracle PR #1290)
reconstructed via search_code fragments (full-file reads stay denied,
trap 3/15f). Goldens: `parity/goldens/admin/sweep_adminmenu.json` (the
`!adminmenu` prefix open) + `sweep_slash_admin.json` (the `/admin`
ephemeral type-4 twin, flags 64). Pre-flip 0/2 → post 2/2 (green on the
FIRST isolation replay).

## What shipped

1. **The shipped ⚙️ Server & Admin hub** replaces the generic
   operator-spine hub (`sb/domain/admin/panels.py`, panel id
   `admin.hub` — the D-0067 ORACLE-WINS reshape lane): the red embed
   (ADMIN_COLOR = the existing `red` token 15158332) with the
   three-section legend description, the "Only you can interact with
   this panel." footer via renderer_override (outside FooterMode's
   vocabulary — the server_management precedent; the override adjusts
   ONLY the footer), and the shipped four button rows (Tools 4 /
   Configure & Operate 4 / Platform & Diagnostics 5 / Help+Overview 2)
   at the golden's exact styles. `session_lifecycle=True` — the shipped
   view was a timeout-bound invoker-locked session view: run-minted
   `<cid:N>` ids on both surfaces, no `panel_anchors` row (trap 11d),
   never-strand via the session-view exemption (general.menu
   precedent).
2. **The slash twin cost ZERO posture edits** — the existing `admin`
   BOTH CommandSpec routes PanelRef, and slash+PanelRef resolves
   DeferMode.NONE (trap 26); Audience.INVOKER carries flags 64.
3. **Capture-world literal (trap 10a)**: "Loaded cogs: **58**" — the
   shipped `len(bot.cogs)` interpolation in the capture world; both
   goldens pin the one value, so the line ships as a pinned literal
   with the module-docstring under-port note.
4. **Button routing (no golden drives clicks)**: nine navigation
   buttons route to their REAL ported panels (settings.hub /
   server_management.hub / channel.hub / ai.hub /
   diagnostic.platform_hub / diagnostic.hub / ux_lab.home / logging.hub
   / cleanup.hub), 📚 Help → help.home, ↩ Overview → REFRESH_PANEL on
   admin.hub (the shipped row-3 "overview anchor (rebuilds this panel
   in place)"), Server Stats / Cog List / Log Level land on the
   existing band-2 handler reads, Reload All on a declared pending
   terminal (deploy-ops). K1 claims action_ids bare and repo-global
   (trap 19/21) — the `admin_*` prefixes keep the namespace clean; the
   minted session ids never reach the wire.
5. **Trap-28 pre-step (first formal use)**: `_sweep_skips.json` lists
   admin-family `force`/`loadall`/`unloadall`/`syncslash`/`restart`/
   `system_info` as deliberately capture-skipped — this flip declares
   NONE of them anew. The pre-existing band-2 `restart` CommandSpec
   (K5 lifecycle seam) predates the flip and stays as designed
   (ledgered in the manifest header).
6. **parity.yml**: admin ported (34/49); ratchet
   `admin: {events: 1, tables: 2, settings: 0}` (raw covered-side —
   trap 14d). **ZERO depth exemptions, ZERO new reason classes, ZERO
   decision records** (stores/events/settings all declared empty).
   Compensator allowlist stays EMPTY (read-only slice). The
   invoking-message delete tail is the ruled invoking-message-deletion
   disposition (trap 15c). Lock file amended ADDITIVELY with the 3
   admin.hub arrangement rows (legacy-seed Exempt, the diagnostic
   wording) + `check_sim_gate --write-baseline`; compat pin untouched
   (no overrides, no command changes — trap 12d).

## Traps confirmed / new intel

- **Trap-24 drift check: NO drift** — the oracle current-head
  admin_cog.py fragments (title, description sections, footer, color,
  row order incl. the row-3 overview-anchor comment) match the corpus
  goldens byte-for-byte.
- **12d nuance re-confirmed at the spine→real reshape**: a session
  panel that GAINS a LayoutSpec (the spine hub had none) DOES mint the
  3 arrangement lock rows (PanelSpec.layout / LayoutSpec.pages /
  PageSpec.rows) — "zero lock churn" holds only when the arrangement
  keys already existed; the sanctioned fix is the additive legacy-seed
  Exempt trio + write-baseline (the #183 wording).
- The general.menu recipe (session view, no nav slots, static TextBlock
  legend) + the server_management footer-override recipe compose
  cleanly — one override, one line of adjustment.

## Verification

- goldens/admin 2/2 green (isolation replay, first try); full gate
  **214/214 across 34 ported** on real Postgres; report leg **251/465**
  green, 465/465 replayable (serial — trap 25/27); check_parity_depth
  OK — 49 subsystems (34 ported), 465 goldens; check_sim_gate OK (1126
  [A], 391 auto-exempt); check_compat_frozen OK; check_namespace /
  egress / no_skip / schema_growth / symbol_shadowing /
  metric_cardinality / config_usage / escape_hatches / amendments
  clean; manifest_compile green (snapshot recompiled in-PR); unit suite
  **1374 passed, 2 skipped** local (canonical order).

## 💡 Session idea

community's two goldens pin the same shipped hub-view shape (the
GENERAL_COLOR `views/community/hub.py` build with the same invoker-lock
footer literal) — the admin recipe (session hub + footer override +
`_nav` routes) should port it nearly mechanically; check the golden's
row split and whether its buttons route to PORTED panels (xp/role are
mixed-band) before promising real routes.

## ⟲ Previous-session review

(This previous-session review covers the diagnostic flip, #183.) The
diagnostic card's two appended traps both bound here on day one: trap
27 (serial ladder during ratchet scratch states) was followed to the
letter — nothing ran backgrounded between the scratch-learn and the
hand-apply — and trap 28's skip-grep is now a per-row pre-step (item 5
above is its first formal record). The #183 posture note
(slash+HandlerRef AUTO-defers; slash+PanelRef defaults NONE) saved a
red: `admin` is a PanelRef front door, so no explicit DeferMode was
needed — verified against the golden's type-4 before writing any
manifest edit.
