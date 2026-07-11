# 2026-07-11 — logging parity flip (pending→ported, the twenty-fourth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `logging` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/logging_cog.py` +
`cogs/logging/{panel,select_view,provision_view,routes_panel,schemas}.py`
+ `services/{server_logging,server_logging_config,moderation_config}.py`
+ `utils/settings_keys/logging.py` @58040c6 (reconstructed via
search_code fragments — full-file oracle reads stay denied, playbook
trap 3/15f). Goldens: `parity/goldens/logging/` —
logging_enable_and_bind, sweep_logging, sweep_logging_create,
sweep_logging_routes, sweep_logging_set, sweep_logging_status,
sweep_logging_test. Pre-flip 0/7 → post 7/7 (first local replay green,
the #154 class).

## What shipped

1. **The shipped panel-first surface** replaces D-0029's projection hub:
   the LoggingPanelView hub (8 STATIC `logging_panel.*` ids via
   `custom_id_override`, 5 shipped rows, the status embed via
   renderer_override, engine nav `nav:help` + `nav:hub:moderation`), the
   zero-component status card (`!logging status` — the karma.error_card
   lane), the Routes panel (`logging_routes.*` select + 4 buttons, NO
   engine nav — the shipped ↩ Back replaces it, ERROR-red embed with the
   quick-start description + per-route resolution field + fallback-chain
   footer), and the LogChannelSelectView channel picker. All four are
   session-lifecycle — the shipped Views were never anchored and the
   goldens pin ZERO `panel_anchors` rows.
2. **Two NEW render/wire capabilities** (kernel + both presenters):
   CONTENT-only panels (`RenderedPanel.embed=None` + `content` — the
   picker's plain-text send; transport omits the embeds key, the live
   presenter sends content) and Discord-native CHANNEL selects
   (`SelectorKind.CHANNEL` → `RenderedComponent.channel_types` → wire
   type 8, `channel_types: [0]`, `required: false`, no options;
   discord.ui.ChannelSelect live). logging_enable_and_bind step 3 pins
   both (select + Clear-binding button session-mint to `<cid:1>`/`<cid:2>`).
3. **enable/disable RETIRED** (D-0066, the D-0065(3) precedent): the
   shipped cog never had them — `!logging enable` fell through
   `invoke_without_command` to the panel, byte-identical to bare
   `!logging` with NO settings write (the golden pins Enabled: ⚪ off on
   both steps). The new dispatch reproduces the fallthrough: no
   subcommand match → longest-match lands the group's PanelRef. Lock
   seed rows removed, sim baseline + compat regenerated (trap 18g).
4. **The shipped 11-slot route table** replaces the 6 interim
   BindingSpecs: names verbatim (`mod_channel` … `role_channel`, legacy
   KV aliases carried), roots-first display order, fallback chain
   (severity/audit → mod; event routes → events), sorted usage bytes
   (sweep_logging_set + sweep_logging_create pin them). `logging create
   <route>` keeps the D-0029(4) polite refusal (provisioning port =
   server_management successor); `logging set <route>` opens the picker;
   picker select/clear ride the band-1 `settings.bind`/`settings.unbind`
   ops (§4.1 — compensator allowlist stays EMPTY, no new compensators).
5. **The shipped counter engine, real + reseeded** (D-0066(4)): the
   16-name process-local counter vocabulary verbatim, bumped by the
   shipped subscriber trio armed on THE bus in BOTH roots — staff
   mod-log feed, public-log twin (disciplinary pre-filter
   {warn,timeout,kick,ban}, default-"none" selector → counted skips),
   audit feed (audit.action_recorded). The goldens pin CAPTURE-trajectory
   values (1 → 18/3) that encode the capture's own ordering (curated
   then command-alphabetical sweeps) + its boot-time on-ready increment
   — not reproducible from the replay's path-sorted, gate-filtered
   ordering — so the runner seeds `CAPTURE_WORLD_COUNTERS` per observing
   case (the CAPTURE_WORLD_SETTINGS sibling; full increment-by-increment
   derivation on the constant). Mode-independent by construction: gate,
   report, and isolation replay all see the same seeded state.
6. **parity.yml**: logging ported (24/49); ratchet
   `logging: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp). **ZERO depth.exemptions rows**,
   zero new exemption/disposition classes; decision record D-0066.

## Traps confirmed / new intel

- **Process-memory capture leakage can pin a TRAJECTORY, not just a
  literal** (10a graduated): when the same leaked surface renders with
  DIFFERENT pinned values across goldens, the pinned-literal move fails
  — the sanctioned move is runner-seeded world reconstruction
  (CAPTURE_WORLD_COUNTERS), derivable increment-by-increment from the
  goldens' own pinned `events` arrays + the capture ordering
  (parity/cases/sweep.py sorts by command qualified_name; curated
  first; parity/harness/boot.py clears boot-noise CALLS/EVENTS but a
  process counter survives the clear — that's the +1 baseline).
- **Live counter accumulation is MODE-DEPENDENT** — the gate replays
  only ported subsystems' cases, the report replays everything,
  isolation replays one: any golden-rendered process state fed by other
  cases' events CANNOT go green in all three by accumulation; seed it.
- **Compiler K1 claims panel action_ids BARE and cross-subsystem**
  (manifest_compile `custom_id:` namespace): shipped tokens like
  `status`/`overview`/`create`/`refresh` collide with btd6/economy/
  channel/treasury — rename the INTERNAL action_id and pin the shipped
  wire byte via `custom_id_override` (the override, not the action_id,
  is the wire truth).
- **A group's unknown-subcommand fallthrough ports for free** when the
  bare group routes at a PanelRef — the 3-token longest-match eats the
  unknown token as argv and panels ignore args (`!logging enable` ≡
  `!logging`).
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 2 (lock additive
  + --write-baseline), 11d/15b-adjacent (session_lifecycle kills the
  anchor row; overrides survive `_mint_ephemeral`), 15f (search_code
  phrases, not paths), 16e (importlib `_replay_corpus`) confirmed as
  written.

## Verification

- goldens/logging 7/7 green on the FIRST local replay (isolation);
  full gate **158/158 across 24 ported** on real Postgres;
  check_parity_depth OK — 49 subsystems (24 ported), 465 goldens, zero
  exemptions; check_sim_gate OK; check_compat_frozen OK;
  check_namespace/intent/slash_cap/egress/no_skip/migrations clean;
  unit suite **1342 passed, 2 skipped** local (canonical order) after
  the band-2 fan-out test moved to the shipped binding name +
  subscriber pair; 5 new flip tests (surface, route table, counter
  vocabulary, reconstruction trajectory, disciplinary pre-filter).

## 💡 Session idea

The R2 settings dimension being dead code (A-16 latent-defect note,
#140) means the 12 logging scalars ride the flip unpinned — when the
settings-dimension arming sweep lands, logging will be one of the rows
that reds first; its ratchet row already carries `settings: 0` so the
sweep can measure the true floor from the goldens rather than guessing.

## ⟲ Previous-session review

(This previous-session review covers the parity lane's wave-6 close.)
The moderation flip (#163) left the LANE END pre-read that D-0029
pre-names logging's reds and that moderation.action_taken fan-out is
logging's subscriber — both held exactly: the fan-out trio is the slice's
core, and the mutation_id payload addition was invisible to logging's
goldens (no logging golden pins a fan-out send; the capture guild had
logging disabled throughout). The wave-6 record's trap 18 list
(capture-world reseed lane) is what this slice extended to process
memory.
