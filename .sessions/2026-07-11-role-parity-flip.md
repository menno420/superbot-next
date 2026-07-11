# 2026-07-11 — role parity flip (pending→ported, the thirty-seventh row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `role` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/role_cog.py` (the
RoleHubPanelView field list) + `disbot/views/roles/` +
`disbot/utils/db/role_menus.py` (menu-builder provenance for the depth
exemptions), reconstructed via search_code fragments (trap 3/15f).
Golden: `parity/goldens/role/sweep_rolemenu.json` — the `!rolemenu`
anchored hub open. Pre-flip 0/1 → post 1/1 (green on the FIRST
isolation replay).

## What shipped

1. **The band-5 hub reshaped to the golden's exact bytes**
   (`sb/domain/role/panels.py`): teal accent (existing `teal` token
   1752220), NO description, the SEVEN static inline-true blurb fields
   via a delegation renderer_override (role_cog.py's literal
   `(name, blurb, True)` add_field list — grammar FieldsBlock 2-tuples
   serialize inline=false, the economy 14c recipe), emoji IN the
   button labels (the golden pins no separate wire emoji field —
   the INVERSE of trap 15a's ticket case: check the wire shape first,
   both directions exist), shipped styles (Create green, Manage/Time/
   XP/Reaction blurple, Diagnostics/Exemptions grey), rows 3/3/1, and
   the grammar nav row `nav:help` + `nav:hub:community` ("↩ Community"
   — explicit `home_hub="community"`, label already in HUB_NAV_LABELS
   since the ticket flip).
2. **Anchored-panel semantics kept**: the golden pins the
   `panel_anchors` row on the prefix open — `session_lifecycle` stays
   False (the #179 surface split); the seven persistent `role:*`
   custom_id_override pins were already in the band-5 spec (zero compat
   churn).
3. **EIGHT depth exemptions, ALL under EXISTING classes** (trap 7's
   biggest bite yet; parity.yml `depth.exemptions.role`):
   - `table:role_thresholds` + `table:reaction_roles` →
     covered-elsewhere (named siblings `_unmapped/sweep_setrole.json` /
     `_unmapped/sweep_reactroles.json` carry the added rows verbatim);
   - `table:role_grants` → guard-only-capture (D-0069): the only
     grant-lane sweep (`_unmapped/sweep_temprole.json`) drove an
     unparseable duration token ("test") — guard bytes only, corpus
     grep confirms zero goldens carry the table;
   - `table:role_menus` / `role_menu_options` /
     `role_menu_pickup_stats` / `reaction_role_message_modes` /
     `role_automation_exemptions` → select-driven (D-0064, the D-0063
     test re-argued per row): every writer sits behind the shipped
     INTERACTIVE reaction-roles surfaces (the PR-2 menu builder's
     one-tap pickers, the published RoleMenuView dropdown, the manager
     mode picker, the Exemptions panel role picker) — select values the
     corpus click schema structurally lacks.
   ZERO new reason classes, ZERO decision records (D-0071 stays free).
4. **Composition-parity doctrine bite**: dropping the live-count
   FieldsBlock from the spec made `role.hub_overview` (and the sibling
   spotlight overview provider) ENSURE-ONLY —
   `test_no_new_ensure_only_refs` red; both providers now register at
   MODULE IMPORT (the #111 pattern). The provider stays a real read
   surface; the shipped hub renders the static blurbs the golden pins.
5. **Trap-24 drift check: NO drift** (current-head role_cog.py field
   list matches the golden byte-for-byte). **Trap-28**: no role-family
   `_sweep_skips.json` entries.
6. **parity.yml**: role ported; ratchet
   `role: {events: 1, tables: 3, settings: 0}`. Compensator allowlist
   stays EMPTY (this flip adds no ops; the existing temp-grant
   compensator lineage #105/#108/#111 is untouched). Lock values
   amended to the golden's 3/3/1 arrangement + baseline regen;
   snapshot recompiled.

## Traps confirmed / new intel

- **NEW CHECKER GAP (ledgered, PR-body + codex question): check_sim_gate
  does NOT flag VALUE drift on an existing [A] pin** — reshaping
  role.hub's rows while the lock/baseline still carried the old 3/2/2
  split passed the checker silently (admin/community REDDED only
  because their keys were NEW). The lock values were hand-amended to
  the golden arrangement anyway; a checker that compares pinned values
  is the hygiene follow-up.
- **Emoji wire shape has TWO shipped forms** (trap 15a bidirectional):
  ticket pinned emoji as a SEPARATE field; role pins emoji IN the
  label. Read the golden's component dict before declaring either.
- **An anchored-hub reshape is cheaper than a session one**: compat
  pins were already right (band-5 declared the `role:*` overrides),
  so the whole flip is spec-bytes + override + exemptions.

## Verification

(Ladder run at the post-merge state of the stacked train — see the PR
body for the verbatim gate/report/pytest lines.)

## 💡 Session idea

Three `_unmapped` sweeps (sweep_roles, sweep_rolecreator,
sweep_rolesettings) pin this same hub view (corpus grep) — plus
sweep_setrole/sweep_reactroles/sweep_temprole/sweep_unsetrole/
sweep_removereactrole/sweep_listreactroles/sweep_roleinfo/
sweep_temproles/sweep_assignroles/sweep_debugroles/sweep_createrole/
sweep_deleterole form a ~14-golden role-family re-home candidate (the
#155 lane) now that the row is ported; each needs its own replay proof
before moving.

## ⟲ Previous-session review

(This previous-session review covers the community_spotlight flip,
same session.) The spotlight card's "check components first" rule paid
again — role's components were nearly right (band-5 had pinned the
custom_ids correctly) and the work concentrated in the embed + nav +
depth block, exactly where the recipe stack predicted. What the
spotlight card missed and this flip surfaced: the FIRST R2-heavy row
of the day (8 exemptions) and the sim-gate value-drift gap — both now
recorded above.
