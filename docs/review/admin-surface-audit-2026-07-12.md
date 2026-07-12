# Admin-surface audit — core admin functions (2026-07-12)

> **Status:** `audit` — point-in-time audit of the core admin function
> surfaces (owner directive 2026-07-12), consolidated from four parallel
> read-only audit passes. Distinct from the whole-program
> [program-review-2026-07-12.md](program-review-2026-07-12.md); reuses its
> terms (golden, gate, `_unmapped`, compensator, cutover).

## Scope & provenance

**Audited HEAD: main `764a393633a60ed82906e2b15ea41c4932120f4d` (#260).**
Four parallel audit areas, each handler → op → store → effect traced in
source (no name-trust), manifests/panels/goldens/sim-gate cross-checked,
the old bot `menno420/superbot` consulted as oracle where parity intent
was in question:

1. **AI settings panel** — verify-and-document pass (programmatic
   PanelSpec instantiation + ref-registry resolution through the live
   manifest import edge `sb/manifest/ai.py:19-30`). This pass also
   **re-ran the golden-parity gate locally on real Postgres 16: GREEN —
   412/412 goldens across 51 ported subsystems** at HEAD.
2. **Moderation admin / guild settings admin / setup-onboarding.**
3. **Tickets/ticket-admin, xp-admin, channel admin (incl. proof-channel).**
4. **Diagnostics/health/status, economy admin, behavior/routing admin**
   (ref-registration verified programmatically: 63/32/24/85 refs reachable
   from the diagnostic/economy/admin/ai manifests, **0 unregistered**).

While this document was being assembled, main moved to `dd76427`
(#261 deathmatch row birth 50→51, gate 412/412; #262 docs-only). All
file:line cites below are at `764a393` and were spot-re-verified at
`dd76427` where load-bearing; none of the intervening merges touch the
audited surfaces. The `!givexp` fix (the one FIX-now item) is being
shipped by a **parallel slice of the same directive** — cross-referenced
in §3.1, deliberately NOT duplicated here.

**Verdict legend.** **OK** = implemented end-to-end and coherent at this
SHA. **FIX** = actionable inconsistency with no (found) ledger entry.
**PARK** = deliberate, ledgered under-port (declared pending terminal or
unarmed live port with a named successor) — real functional hole, no
action now. **PRUNE** = dead surface that should be deleted (none found —
§7).

---

## 1. Master verdict table

Every row cites file:line at the audited SHA. "e2e" = the full
handler → op → store/effect chain confirmed in source (replay semantics;
live-arming caveats are called out per row and in §4).

| surface | function/component | end-to-end? | order logical? | dead/orphaned | golden exposure | verdict |
|---|---|---|---|---|---|---|
| moderation | `!warn` / `mod:warn` modal (op `moderation.warn`) | YES — warnings upsert + mod_logs + in-txn escalation ladder (sb/domain/moderation/ops.py:59-109) → post-commit effects (:251-278); refused escalation compensated (:341-381) | yes | none | sweep_warn, moderation_warn_flow | OK |
| moderation | `!timeout` / `mod:timeout` | YES in replay (call-first inside the DB leg, ops.py:131-201). LIVE: `GuildModerationActions` never installed by sb/app/main.py — only sb/adapters/parity/boot.py:493-494 arms it | yes | none | sweep_timeout (pins the half-applied capture) | PARK (unarmed-adapters family; docs/decisions.md:391 item 4) |
| moderation | `!kick` `!ban` `!unban` + panel twins | YES in replay — record leg → effect leg → compensators (ops.py:319-338, :384-416). LIVE: same unarmed port | yes | none | sweep_kick (the kick typed-challenge confirm resolved oracle-wins at the flip, ops.py:489-497), sweep_ban, sweep_unban | PARK (same) |
| moderation | `!clearwarnings`, `!modlogs` + modal | YES — DB-only lanes, work live (ops.py:209-227; service.py:282-300, store.py:154-159) | yes | none | sweep_clearwarnings, sweep_modlogs | OK |
| moderation | `!modmenu` / `/moderation` hub (7 buttons → 7 modals) | YES — every modal submit routes to a registered op/handler (sb/domain/moderation/panels.py:78-178); readiness field degrades honestly (service.py:252-269) | yes (oracle 3/3/1 rows, panels.py:181-185) | none | sweep_modmenu, sweep_slash_moderation + sim-gate layout rows | OK |
| moderation | settings `dm_on_action`/`dm_actions`/`dm_template` | NO effect — loaded (service.py:100-102), no op reads them; target-DM is the ledgered successor (ops.py:12-18; docs/decisions.md:439-442 item 3) | n/a | inert-but-declared (sb/manifest/moderation.py:48-59) | none (transport records the DM as `gap`) | PARK (named successor) |
| moderation | settings `post_action_cleanup` + `_limit` | NO effect — loaded (service.py:108-111), **zero consumers anywhere**, no ledger entry found | n/a | inert keys (sb/manifest/moderation.py:72-79) | none | **FIX** (§3.2) |
| moderation | `public_log_actions` setting + `public_log` binding | NO effect — declared editable (sb/manifest/moderation.py:80-90) but `_on_moderation_action_public` hardcodes the `"none"` default and never reads setting or binding (sb/domain/server_logging/service.py:365-382) | n/a | declared-but-ignored pair | none | **FIX** (§3.3) |
| settings | `/settings` `!settings` hub open | YES — CommandSpec → `settings.hub`, ephemeral (sb/manifest/settings.py:67-81) | yes (pinned rows, sb/domain/settings/panels.py:313-317) | none | settings_hub_open, sweep_settings, sweep_slash_settings | OK |
| settings | hub 19-group select + 5 buttons; `!settings access` explorer's 5 interactions | NO — all pending terminals (sb/domain/settings/handlers.py:36-62); roster/inventory are pinned capture literals (panels.py:104-154) | yes | dead (declared) | hub + sweep_settings_access goldens pin the bytes | PARK (settings-mutation slice — §4.2) |
| settings | K7 mutation lane (`settings.set_scalar/clear_scalar/bind/unbind/platform_latch`) | YES — declared-key fence + txn upsert + audit + post-commit events (sb/domain/settings/ops.py:60-68); consumed live by ai/rps/economy/governance; `_state_write` audited (service.py:196-234, the four-reviewer-audit finding CLOSED per the same decision record's item 1) | n/a | none | sweep_setlogchannel, sweep_ai_settings family | OK |
| setup | `!setup` / `/setup` | YES in replay — ensure/create `#superbot-setup` + Step-1 card (sb/domain/setup/service.py:141-165). LIVE: channel-state create port unarmed (service.py:30-35 docstring) | yes | none | sweep_setup, sweep_slash_setup (overwrite masks are golden bytes) | PARK (unarmed-adapters family / D-0077) |
| setup | `/setup-hub` `-advanced` `-status` `-describe` | YES — session mint (ops.py:111-127), create-before-DB workspace (ops.py:130-170, D-0077), read-only status, deterministic suggest | yes | none | 4 sweep_slash_setup-* goldens | OK (live channel-port caveat) |
| setup | `/setup-reset` `-skip` `-unskip` | HOLLOW/HALF — `pending_before=0` hardcoded, clearing branch unreachable (handlers.py:159-168); valid slug → BLOCKED pending (:170-205) | yes | unreachable branch handlers.py:165-168 | goldens pin the empty/refusal bytes | PARK (wizard-lifecycle slice) |
| setup | all 4 wizard panels' interactive components (depth buttons, kind-select, Save/Skip, 5 review buttons) | NO — every one routes to `setup.wizard_pending` (sb/domain/setup/panels.py:128-135); onboarding is open-and-look only | yes (oracle layouts) | dead (declared, honest) | 9 setup + 1 quicksetup goldens pin panels; no golden drives any click | PARK (wizard-lifecycle successor — §4.2) |
| setup | `/setup-depth`, delegate pair, prefix twins | Deliberately NOT declared (sb/manifest/setup.py:11-27) — the `-depth` golden **pins silence** (trap 17/D-0076) | n/a | intentional absence | sweep_slash_setup-depth pins zero calls | OK (do not "fix") |
| tickets | `!ticket` hub, `!ticket new/add/remove/claim/close`, open-modal, my-tickets | Render yes; every action lane refuses NOT_CONFIGURED — no `tickets` table exists (sb/domain/ticket/store.py:7-11); config read then discarded (handlers.py:397-415); dead duplicate guard returns at handlers.py:128/140/152/164; `my_tickets` non-empty branch returns empty-state copy (:191) | yes | unreachable branches (above) — booby-traps for the ticket-mutation slice, not orphans | 6 sweep_ticket* goldens (guard bytes) | PARK (ticket-mutation slice) |
| ticket-admin | `!ticketpanel` launcher; `!ticketsetup` wizard | Launcher render fully real, persistent `ticket:launcher:open` has a live submit handler (handlers.py:474); setup reads the live config row but all 5 controls → `ticket.setup_pending` (:285-295) | yes | none | sweep_ticketpanel (footer+reaction bytes), sweep_ticketsetup + sim-gate rows | OK / PARK (wizard-mutation) |
| ticket-admin | `!ticketlimit`, `!ticketblacklist [add/remove]` | YES — complete K7 lanes → `ticket_config`/`ticket_blacklist` (ops.py:50-92, store.py:101-147, migration 0032) | yes | none | sweep_ticketlimit, sweep_ticketblacklist(+_add/_remove) | OK |
| xp-admin | `!xpmenu` hub (rank / configure / give / reset) | YES — Give XP modal → K7 `xp.award`; Reset + TYPED_PHRASE confirm → K7 `xp.reset` (sb/domain/xp/panels.py:183-208); danger never row 0 (:228-231) | yes | none | sweep_xpmenu (multipart rank.png shape) | OK |
| xp-admin | `!givexp @user <amount>` | YES for the mention form (handlers.py:99-118 → ops.py:93-119); **bare-ID form misparses** — `_target_from`/`_amount_from` both take the FIRST digit token (sb/domain/xp/ops.py:58-88) | n/a | none | sweep_givexp (mention form only — bug lane unpinned) | **FIX** (§3.1 — parallel slice) |
| xp-admin | `!resetxp @user` | YES — single numeric token, no misparse (handlers.py:120-134, ops.py:122-135) | n/a | none | sweep_resetxp | OK |
| xp-admin | `!xpconfig` panel; `!xpimport` | Render real (live settings reads, panels.py:401-426); all 4 buttons pending (:122-146); import scan port armed only in parity boot (sb/adapters/parity/boot.py:535); `xp.import_levels` op registered, reachable by no surface (ops.py:138-170, :297 — deliberate, awaiting the import-preview UI) | yes | none | sweep_xpconfig, sweep_xpimport | PARK |
| channel | `!channelmenu` hub (5 buttons) + 13 reserved prefix ops | NO — all → `channel.*_pending` / `channel.ops_pending` honest terminals (sb/domain/channel/handlers.py:30-42, sb/manifest/channel.py:28-31, :84-86); pending handlers registered at module import (handlers.py:185) | yes (shipped rows; the legend's 4-of-5 omission is oracle-verbatim, panels.py:53-62) | none | sweep_channelmenu + sim-gate rows | PARK (the ledgered channel-ops slice) |
| channel | `!slowmode` `!lock` `!unlock` | YES in code — handler → `ChannelStateActions` port → audit + lifecycle events (handlers.py:112-182, service.py:225-263). LIVE: no root installs the port (only boot.py:562) → honest BLOCKED | n/a | none | sweep_slowmode/sweep_lock/sweep_unlock | OK (code) / PARK (live arming — §4.1) |
| proof-channel | `+prize` / `timedprize` / `-prize` / `!prizestatus` / `!prizemenu` / lock-reconcile sweep | YES — full two-leg K7 with both compensator directions closed (ops.py:104-128, :164-204; the 2026-07-10 residual FIXED, program-review-2026-07-12.md:227-235); 60s ManagedTask reconcile (service.py:88-121). `ChannelPermActions` port unarmed in the live root (service.py:38-48 fail-loud) | yes | none | 5 sweep_* goldens incl. both prizemenu state branches | OK (code) / PARK (live arming) |
| diag | `!diagnostics` hub | 5/8 buttons real; Bot Status / System Info / Recent Errors → `diag_pending` (sb/domain/diagnostic/panels.py:347-362, handlers.py:404-412) | yes (pinned 3-3-2 rows) | 3 pending by design | sweep_diagnostics | PARK |
| diag | `!list_commands_detailed` | Page 1 only — both paginator buttons pending (handlers.py:265-272); page 1 is the OLD bot's registry (command_catalog.py capture literal) | yes | 2 pending stubs | sweep_list_commands_detailed | PARK (⚑ §4.4) |
| diag | `!platform` hub + 29 `!platform <view>` cards | Hub selects dispatch (handlers.py:361-381); every card is a **static capture literal** — build_view_embed substitutes only ch/gid/tier/ts (platform_views.py:419-443); `economy`/`economytrend` always report zero flow (:219-245) | yes | none | 33 sweep_platform_* goldens | PARK (⚑ live-misleading — §4.4) |
| diag | `!check_database` | NO real check — hardcoded "✅ Schema healthy 16/16 / 103/103 / 106" capture-epoch literal (handlers.py:182-200) | n/a | none | sweep_check_database | PARK (⚑ live-misleading — §4.4) |
| diag | `!latency` + hub 📡 | Handler real; `install_ws_latency_reader` has **zero callers repo-wide** (handlers.py:76-82) → live prints "nan ms" | n/a | unarmed seam | sweep_latency (pins "nan ms") | PARK (§4.1) |
| diag | `!lifecycle`; `!platform backfill` dry-run | YES — real K5 lifecycle read; real CompoundOp preview, `apply` refused (handlers.py:316-357) | n/a | none | sweep_lifecycle, sweep_platform_backfill | OK |
| diag | 🚩 Flag Manager, 🤖 Automation panels | NO mutations — all controls pending (panels.py:524-549, :574-628); option lists are the OLD bot's registries | yes | parity-locked stubs | sweep_platform_flag, sweep_platform_automation | PARK |
| admin | `!adminmenu` / `!admin` hub | YES — 10 nav targets all registered; "Loaded cogs: **58**" is a capture literal (sb/domain/admin/panels.py:91-100); Log Level is a READ where the oracle opened a SET modal (:49-52, successor named) | yes (pinned 4-row layout) | none | sweep_adminmenu, sweep_slash_admin | OK |
| admin | `!coglist` Cog Manager | NO — OLD bot's 58-cog roster verbatim (sb/domain/admin/cogmgr.py:82-98); select/Load/Unload/Reload/Prev/Next all pending (:257-270); honest successor read `admin.subsystems_view` exists but is unrouted (handlers.py:36-48) | yes | 5 pending stubs + 1 unrouted successor read | sweep_coglist | PARK (§4.3) |
| admin | `!serverstats` | Handler + card real; `install_guild_directory` armed only by parity boot (boot.py:598-602) → live always BLOCKED (handlers.py:109-141) | n/a | unarmed live port | sweep_serverstats | PARK (§4.1) |
| admin | `!loglevel`, `!restart`, `!slashes` | YES — real setLevel / K5 restart (handlers.py:79-107); `!slashes` pinned copy recommends the unported `!syncslash guild` (:64-69, same channel-ops deferral) | n/a | misleading pinned copy only | sweep_loglevel, sweep_slashes | OK / PARK (copy) |
| econ | `!setlogchannel` + log-channel fan-out | YES — settings.bind workflow + legacy alias (sb/domain/economy/handlers.py:164-183); `economy.balance_changed` subscriber → bound channel (service.py:179-201), armed live via SUBSCRIBE_ROSTER (sb/app/main.py:76-83) | n/a | none | sweep_setlogchannel, sweep_daily deltas | OK |
| econ | hub / shop / jobcenter / daily / balance | YES — audited K7 ops + INV-F invariant; `economy.shop_view` registered-but-unrouted (handlers.py:151-162 — documented fallback) | yes (pinned rows) | 1 documented unrouted read | 9 goldens in goldens/economy/ | OK |
| econ | admin balance adjustment (add/remove/set coins) | Does not exist in EITHER bot (oracle-searched) — no parity gap; product decision if wanted | n/a | n/a | none | OK (no gap) |
| ai | `!ai` group + `!aimenu` / `/aimenu` hub | YES — 10 subcommand cards real reads; hub buttons route real views/panels (sb/domain/ai/service.py:140-159) | yes (pinned; see §5 PARK-1) | none | sweep_ai, sweep_aimenu, sweep_slash_aimenu + 17 card twins | OK |
| ai | `!ai diagnostics` — setup-advisor field | Partial — `_setup_advisor_provider()` ignores the declared `SETUP_ADVISOR_PROVIDER` (sb/domain/ai/operator_cards.py:135-139 vs sb/spec/config.py:170) | n/a | none | sweep_ai_diagnostics (byte-identical while unset) | PARK (control/status.md:200 item 2 — still open; §4.5) |
| ai | settings panel + edit/reset selects | YES — both selects dispatch through audited `settings.set_scalar` (sb/domain/ai/settings_widgets.py:166-219); full verification in §5 | yes (byte-pinned; §5 PARK-2) | none | sweep_ai_settings (persistent ids + `<cid:1>`/`<cid:2>` pinned) | OK |
| ai | policy/behavior/tools choosers, pickers, edit modals, list, routing matrix | YES end-to-end — every write is ONE audited op (`ai.set_*_policy`/`set_*_orchestration`/preset chokepoint; D-0070/71/72/74); matrix is a read-only dry-run (routing_matrix.py:152) | yes | none | click routes golden-unpinned (the corpus-wide interaction blind spot: 1 click + 3 modals) | OK |
| ai | `!aireview` loop + presets | YES — review log + preset stores (migration 0024), binding, export, resolve all real | yes | none | 12 aireview goldens | OK |
| ai | live NL consumer | The NL reply shell is deliberately dormant in the live message feed (sb/adapters/discord/message_feed.py:153-155) — every policy/behavior/tools setting governs a consumer that never replies live | n/a | none | n/a | PARK (named arming slice; OWNER-ACTION 5 key gate) |

---

## 2. Master verdict — the one-paragraph read

Everything that claims to work, works, in replay semantics: **zero
orphaned custom_ids, zero unregistered refs, zero silent no-ops** across
all four audit areas (§7). The three genuinely actionable items are §3.
Everything else that looks dead is a *declared pending terminal* with
honest refusal copy naming its successor slice, or a byte-pinned parity
artifact whose "staleness" is the pinned capture state — §4 lists the
headline ones with their ledger cites. Panel ordering is coherent
everywhere audited; every layout in scope is byte-pinned by goldens AND
pinned in `sim/sim-gate-baseline.json` under `legacy-seed` exempt
provenance, so any reorder is golden re-cut + sim-ratification territory
(§5, §6).

---

## 3. FIX list (actionable, no ledger entry found)

### 3.1 `!givexp` bare-ID argv misparse — being fixed in a parallel slice

`_target_from` (sb/domain/xp/ops.py:58-70) and `_amount_from` (:73-88)
each scan argv for the FIRST digit-only token. The mention form is safe
(`<@id>` fails `_amount_from`'s `isdigit()` test), but the old bot's
`MemberConverter` also accepted bare user IDs (oracle:
disbot/cogs/xp_cog.py `givexp(self, ctx, member: discord.Member,
amount: int)`), so in the new bot `!givexp 123456789012345678 100`
resolves BOTH target and amount to the snowflake — awarding ~1.2e17 XP,
with the success copy repeating the misparse
(sb/domain/xp/handlers.py:241-246). The lane is golden-unpinned
(sweep_givexp uses a mention). **A parallel slice of this same owner
directive is shipping the fix** (in flight at this doc's merge; not
duplicated here). `!resetxp` is unaffected (single numeric token).

### 3.2 `post_action_cleanup` + `post_action_cleanup_limit` — settings with zero consumers

Declared editable (sb/manifest/moderation.py:72-79), loaded into
`ModerationPolicy` (sb/domain/moderation/service.py:108-111), and then
consumed by **nothing** — a repo-wide search finds only the policy load,
the manifest declaration, and the settings-key alias
(sb/domain/settings/keys.py:138-139). Unlike the DM keys (which have the
named successor at docs/decisions.md:439-442 item 3), no ledger
entry names a post-action-cleanup sweep. Either implement the sweep or
ledger a named successor like the target-DM one.

### 3.3 `public_log_actions` / `public_log` — declared editable, hardcoded-ignored

The setting and binding are declared editable in the moderation manifest
(sb/manifest/moderation.py:80-90), but
`_on_moderation_action_public` hardcodes
`DEFAULT_PUBLIC_LOG_ACTIONS = "none"` and never reads the setting or the
binding (sb/domain/server_logging/service.py:365-382 — its docstring
says the policy EDIT surface "is server-management successor work"):
every disciplinary action skips, counted. A value set today via the K7
lane would be silently ignored. Either wire the subscriber to
`resolve(guild, "moderation", "public_log_actions")` + the binding, or
de-declare the pair until the slice lands.

---

## 4. Headline structural gaps — all PARK, all ledgered

These are the big functional holes an operator hits live. None is a
defect at this SHA; each has its ledger/decision cite.

1. **Live effect adapters unarmed (the ledgered unarmed-adapters family).** The live
   composition root `sb/app/main.py` installs NONE of:
   `GuildModerationActions` (sb/domain/moderation/service.py:159 — only
   sb/adapters/parity/boot.py:493-494 arms the capture twin),
   `ChannelStateActions` (only boot.py:562), `ChannelPermActions`
   (proof-channel, service.py:38-48 fail-loud), the ws-latency reader
   (`install_ws_latency_reader`, sb/domain/diagnostic/handlers.py:76 —
   zero callers repo-wide), or the guild directory
   (`install_guild_directory`, only boot.py:598-602) — parity boot only.
   Live: moderation effects degrade to PARTIAL + finding or generic
   error, channel/setup lanes refuse loudly, `!latency` prints "nan ms",
   `!serverstats` always refuses. Ledgered: docs/decisions.md:391 item 4;
   sb/domain/setup/service.py:30-35;
   docs/review/program-review-2026-07-12.md Top-10 item 5 ("Live effect
   adapters unarmed"). The `ai_operator_ports` install at
   sb/app/main.py:490-494 is the precedent to copy at cutover.
2. **Settings Manager hub + setup wizard are deliberate pending-terminal
   shells.** The hub's 19-group selector and all five diagnostics
   buttons refuse (sb/domain/settings/handlers.py:36-47), the access
   explorer's five interactions likewise (:48-62), and every interactive
   component of all four setup-wizard panels routes to one
   `setup.wizard_pending` terminal (sb/domain/setup/panels.py:128-135).
   The audited K7 mutation lane exists and is proven (ai/rps/economy
   drive it live) — what is missing is the per-group edit UI
   (settings-mutation slice) and the wizard interior (wizard-lifecycle
   slice). Same conclusion codex reached for image_moderation at #176
   (control/status.md:152). This is the single biggest guild-config +
   onboarding gap.
3. **Cog Manager stub.** `!coglist` shows the old bot's 58-cog roster
   literal (sb/domain/admin/cogmgr.py:82-98) with all five controls
   pending (:257-270); the honest successor read `admin.subsystems_view`
   is registered but unrouted (sb/domain/admin/handlers.py:36-48).
   Deliberate (the channel-ops/deploy-ops deferral + sweep_coglist); post-parity either re-point at
   the manifest registry or prune the panel.
4. **Capture-literal diagnostics cards that read healthy without
   touching the DB (⚑ live-misleading).** `!check_database` renders
   "✅ Schema healthy — 16/16 / 103/103 / 106" as a capture-epoch
   constant (sb/domain/diagnostic/handlers.py:182-200, ledgered in the
   module docstring as the "named successor read"); all 29
   `!platform <view>` cards are static capture literals
   (platform_views.py:419-443), including `!platform economy` /
   `economytrend` always reporting zero coin flow (:219-245); the
   command-list paginator is dead past its old-bot page 1
   (handlers.py:265-272). All golden-pinned, all documented successor
   reads — but on a live deployment these are the surfaces an operator
   would trust, and they lie in the healthy direction. Any live-arming
   must keep the goldens' capture-state bytes reproducible in the
   harness (the ws-latency install seam is the template).
5. **AI diagnostics card ignores `SETUP_ADVISOR_PROVIDER`.** The parked
   item at control/status.md:200 (item 2, PARKED from #151) is still
   open at HEAD: sb/spec/config.py:170 declares the field,
   sb/domain/ai/operator_cards.py:135-139 never reads it. Byte-safe to
   fix while the env var is unset (the goldens' state).

---

## 5. AI settings panel — verification result (rebuild NOT needed)

The scope-changed verify-and-document pass confirmed every claim that
mattered:

- **26 PanelSpecs** in `sb/domain/ai/panels.py:1557-1593` (`_SPECS`),
  instantiated programmatically.
- **114/114 handler refs resolve, 0 misses** — every action handler,
  selector on_select, options_source provider, nav extra_route,
  renderer_override and FieldsBlock provider across all 26 specs,
  walked through the LIVE manifest import edge (`sb/manifest/ai.py:19-30`).
  Method caveat for future auditors: importing only
  `sb.domain.ai.service` yields 37 false misses — the widget modules
  register at module import via the manifest edge; this is exactly the
  BUG A class the composition-parity invariant guards, and that
  invariant is green at HEAD.
- **0 pending terminals remain in `sb/domain/ai/`** — the last
  (`chooser_scope_pending`) retired at #204/D-0074; the defect chain
  #151→#160→#165→#177→#185→#187→#204 is closed.
- **The old layout is deliberately byte-pinned** —
  `parity/goldens/ai/sweep_ai_settings.json` pins 3 component rows, the
  persistent `settings_subsystem.*` ids, the run-minted `<cid:1>`/`<cid:2>`
  selects and the description bytes; `parity/parity.yml` ai row:
  `ported`. **Rebuild NOT needed.**
- Gate re-proof: `python3 tools/run_golden_parity.py --gate` at HEAD on
  local Postgres 16 → **GREEN, 412/412 goldens across 51 ported
  subsystems** (ai's 31 goldens included).

**Five modernization candidates — all PARK** (golden re-cut + sim-lab
ratification territory; no unilateral redesign — 788/788 sim-gate pins
are `Exempt`, `sim/records/` is empty, so no sim run backs any layout):

- **PARK-1** — ai.hub row order (diagnostics quartet above config
  quartet) + the 💤 title emoji reading "asleep" on fresh guilds
  (panels.py:161-213).
- **PARK-2** — ai.settings nav pair is row 0, ABOVE the working selects
  (panels.py:1122-1126); convention would be edit → reset → nav last.
- **PARK-3** — ai.settings stale byte-pinned description ("Read-only AI
  gateway diagnostics… lives in core/runtime/ai/._",
  panels.py:1055-1060) — factually wrong at HEAD (the subsystem owns
  four audited mutation lanes) and cites the OLD repo's layout.
- **PARK-4** — `audit_log_channel` binding declared
  (settings_schema.py:110-115), displayed, settable nowhere (the
  economy setlogchannel bindings reshape at #252 is the precedent lane).
- **PARK-5** — settings.hub's "AI Platform" group pick refuses
  (`settings.group_pending`, sb/domain/settings/handlers.py:36-37) even
  though `ai.settings` is fully live — trivially routable, but it sits
  on the settings row's goldens, not ai's (settings-mutation slice's
  named successor).

---

## 6. Ensure-only allowlist — count correction

HEAD truth is **42 rows = mining 26 + fishing 15 + role 1**
(tests/unit/invariants/test_composition_parity.py:35-78, counted
programmatically; the invariant test passes at HEAD, so the set is exact
in both directions). The circulating "mining 28, fishing 15, creature 1,
role 1" (45) is the #160-era hand count at control/status.md:204 — the
creature row and 2 mining rows have since been pruned (prune-on-fix is
the list's contract). All 42 are PARK: the fishing/mining pending
terminals ride the deep-systems port decision (docs/decisions.md:326),
`panel:role.hub` rides the queued role effect-adapter lane. Nuance worth
keeping: until registered at import, these fire the BUG-class
RefUnresolved envelope live, not the polite refusal.

---

## 7. Zero PRUNE-grade dead surface

Stated explicitly because the directive asked whether anything was
"blindly copied": **no PRUNE candidates were found anywhere in the
audited surfaces.** No orphaned custom_ids (every `custom_id_override`
resolves to a registered handler — real op, real handler, or an explicit
honest-refusal terminal via the operator spine,
sb/domain/operator_spine.py:104-112); no unregistered refs (0/204 across
the four programmatically-walked manifests + 114/114 AI panel refs); no
unreachable commands. The near-misses are documented, deliberate, and
mostly golden-pinned: two registered-but-unrouted successor reads
(`admin.subsystems_view`, `economy.shop_view` — both documented at their
definitions), the D-0077 compensator kept ready with an empty allowlist
(sb/domain/setup/ops.py:27-38 — do not prune), and the unreachable
guard-duplicate branches inside the ticket lanes (§1). The
"blindly copied" things are honest pending terminals or byte-pinned
parity artifacts whose bytes are the contract.
