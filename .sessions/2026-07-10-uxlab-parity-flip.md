# 2026-07-10 — uxlab parity flip (pending→ported, the ninth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `uxlab` parity row (the `/uxlab` slash twin of `ux_lab`'s
`!uxlab` — two parity.yml rows, ONE shipped cog with two entry points)
pending→ported through the A-16 door. Oracle: menno420/superbot
`disbot/cogs/ux_lab_cog.py` (`uxlab_slash` — "Slash front door to the
same panel (one door, not one per action)";
`@app_commands.default_permissions(administrator=True)` +
`app_admin_or_owner()` + guild-only); golden:
`parity/goldens/uxlab/sweep_slash_uxlab.json` (case
`sweep.slash_uxlab`, the row's only golden). The panel runtime shipped
in the sibling ux_lab flip (#128); this PR is the slash surface + flip.

## What shipped

1. **`/uxlab` opens the same shipped Home card byte-for-byte** —
   `sb/manifest/ux_lab.py` gains the SLASH CommandSpec onto the SAME
   `ux_lab.home_view` handler with `DeferMode.NONE` (the shipped slash
   path answered DIRECTLY — the golden pins the bare type-4 response
   with embeds+components and NO ephemeral flag; the utility-flip
   excavated trap, applied by rule).
2. **The shipped original-response bind** — the shipped cog's
   `view.message = await interaction.original_response()` is the slash
   golden's SECOND call (`get_original_response` — the only golden in
   the 465-corpus that pins it). The handler mirrors it through an
   optional duck-typed responder port:
   `ParityResponder.fetch_original_response()` records the wire verb
   (interaction surfaces only, post-ack); the live discord responders
   don't carry the method — the live `DiscordPanelPresenter` already
   performs that fetch inside its own send path (no double-GET).
3. **Sim gate** — the duplicate-name disambiguated
   `ux_lab:uxlab:SubsystemManifest.commands/CommandSpec.help_section_order`
   Exempt row (the ai:list twin-name precedent shape) + baseline regen;
   compat pin amended additively (the second `uxlab` command row —
   derive() walks every CommandSpec).
4. **The flip**: `parity.yml` `uxlab: ported` + the A-16 ratchet row
   `uxlab: {events: 0, tables: 0, settings: 0}` (the golden is a pure
   interaction-response case — no db_delta, no events). R2 vacuous (the
   `uxlab` dir name owns no manifest key; the runtime's declarations
   live under `ux_lab`); zero exemptions; the flip is the last commit.

Gate leg: 19/19 goldens across 9 ported subsystems GREEN against real
Postgres. Dashboard moves 8 → 9 ported (of 49); report leg 31 → 32
green (of 465). Full suite 1220 passed.

## Notes

- Near-mechanical second PR as scoped: the two rows share #128's
  runtime; this PR's diff is the slash CommandSpec, the responder hook
  pair, and the regenerated pins.
- The author-lock / registry-derived-Exhibits under-ports are carried
  in the sibling card (`2026-07-10-ux-lab-parity-flip.md`) and in-code.
