# 2026-07-11 — settings parity flip (pending→ported, the twelfth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `settings` parity row pending→ported through the A-16 door —
the first FOUR-golden flip of wave 2 and the first row whose manifest
declares stores + an event (R2 is NOT vacuous). Oracle: menno420/superbot
`disbot/cogs/settings_cog.py` + `disbot/views/settings/hub.py`
(`SettingsHubView`/`build_embed`) + `disbot/views/access/explorer.py`;
goldens: `parity/goldens/settings/` — settings_hub_open, sweep_settings,
sweep_slash_settings (the ⚙️ hub on both surfaces) and
sweep_settings_access (the 🔍 explorer). The band-1 manifest had already
declared `/settings` routed to a placeholder read-view hub; this PR
replaces that placeholder with the REAL shipped panel.

## What shipped

1. **`!settings` / `/settings` opens the shipped Settings Manager
   byte-for-byte** — `sb/domain/settings/panels.py`: the ⚙️ blurple embed
   (the shipped two-paragraph blurb; the golden-pinned Inventory +
   Customization-findings fields; the Tip footer via renderer_override)
   over the shipped three component rows — the 19-group subsystem select,
   the grey diagnostic quartet (Needs setup / Invalid settings / Missing
   bindings / Recent changes — emoji as a SEPARATE component field), and
   the Command access door — every component carrying its shipped
   PERSISTENT `settings_hub.*` custom_id verbatim (`custom_id_override`;
   `session_lifecycle=True` with every id override-pinned — nothing
   minted, no `panel_anchors` row, the server_management-hub precedent).
   The slash twin answers direct ephemeral type-4 (`DeferMode.NONE`, the
   utility-flip trap rule; `Audience.INVOKER` — the golden pins flags 64).
2. **`!settings access` opens the shipped Access Policy Explorer** — the
   shipped independently-dispatched subcommand lands as a
   `group="settings"` CommandSpec (qualified_name "settings access"; the
   parity boot's 3-token prefix lookup dispatches it — first grouped
   PREFIX front door in the flip lane). The 🔍 blue panel: the PAGED
   subsystem select (run-minted `<cid:1>`; the shipped "— page 1/2"
   placeholder; the 25-option page-1 roster pinned), the persistent
   `access:select_scope` (channel default) / `access:explain` /
   `access:reset` pins, the run-minted ◀ Prev / Next ▶ pair, and the
   standard nav row (`nav:help` + `nav:hub:admin` "↩ Administration").
   The renderer_override stamps the DYNAMIC invoker-named author-lock
   footer (the name rides the opening request's args — the economy
   author-display precedent), marks the prompt fields inline=True, and
   disables first-page ◀ Prev — three surfaces outside the grammar's
   vocabulary, justification carried on the spec.
3. **Pending terminals** — every hub/explorer click (group select, the
   four diagnostics, Command access, explain/reset/scope/paging) lands on
   the declared + honest refusal terminal (`sb/domain/settings/
   handlers.py`, registered at module import — the composition-parity
   invariant): the drill-down pages (`settings_subsystem.*`), diagnostic
   sub-panels, the Command Access panel (`settings_command_access.*`) and
   the explorer's live governance reads are their own port slices.
4. **Sim gate** — manifest/layout/settings.lock.json AMENDED additively
   (the band-1 command row stays) with both panels' arrangement rows +
   the access help_section_order; baseline regen. Compat pin amended
   additively (9 new legacy custom_ids: the six `settings_hub.*` + the
   three `access:*`; plus the `settings access` command row — gate 6
   fired as designed).
5. **The flip**: `parity.yml` `settings: ported` + the A-16 ratchet row
   `settings: {events: 1, tables: 2, settings: 0}` (xp +
   ai_decision_audit from the ported message pipeline). R2 is NOT vacuous
   here — settings declares 2 stores + 1 event that its four read-only
   goldens never touch — so three depth-exemption rows land under the
   EXISTING `covered-elsewhere` reason class (the K7 scalar lane pinned
   by goldens/rps_tournament/sweep_rpsregister.json's `guild_settings`
   row; the binding lane by goldens/_unmapped/sweep_setlogchannel.json's
   `subsystem_bindings` + `binding_audit_log` rows; the advisory
   `settings.changed` fires only from those K7 ops — the shipped bot
   published no tap-able event on those flows, so no imported golden can
   carry it). No new classes; the closed vocabulary was enough.

Gate leg: 29/29 goldens across 12 ported subsystems GREEN against real
Postgres. Dashboard moves 11 → 12 ported (of 49); report leg 34 → 38
green (of 465). Full suite 1255 passed.

## Notes

- **Deliberate under-ports (in-code notes):** the hub's Inventory/
  Customization-findings numbers and both option rosters are
  golden-pinned literals (the shipped `customization_catalogue` /
  `settings_registry` live reads belong to the settings-mutation slice —
  the servermanagement badge-literal precedent); the explorer's page 2 is
  unpinned and lands with its interaction slice.
- The reasonless invoking-message deletes in the three prefix goldens
  ride the ruled `invoking-message-deletion` disposition (ORDER 009) —
  no new classes.

## 💡 Session idea

R2's "exercised by a golden" test is DIRECTORY-scoped, so a subsystem
that owns a shared platform lane (settings' K7 stores, exercised by
OTHER subsystems' config-write goldens like sweep_setlogchannel) can
never satisfy the floor from its own directory — every such flip will
spend a cycle rediscovering the `covered-elsewhere` move. A checker
amendment that lets an exemption row NAME a sibling golden and then
VERIFIES the citation (the cited file actually touches the surface)
would make the class self-auditing instead of prose-trust.

## ⟲ Previous-session review

The servermanagement card's "override-pinned persistent hub under
session_lifecycle" recipe replayed the settings hub green on the FIRST
attempt — panels, manifest, locks, compat all landed exactly per the
documented dance (zero re-cycles; the K1 bare-action_id trap was checked
up front and `needs_setup`/`audit`/`explain`/`reset` were all free).
What it under-delivered: no predecessor card mentions the A-16 R2 floor
BITES when the flipped row declares stores/events its goldens don't
touch — every prior row was R2-vacuous, so the depth-exemption lane
(existing reason classes, `depth.exemptions`) had never been exercised
by this wave; this session spent its only extra cycle deriving the
`covered-elsewhere` citations from a corpus-wide table scan.
