# 2026-07-11 — role-family + counting-family `_unmapped` re-home (the #155 lane)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Re-home 19 `_unmapped` sweep goldens to their now-ported subsystems
(the #155 aireview precedent — `git mv` + the 2-line `subsystem` field
flip, bytes otherwise verbatim): the 16-golden role family
(sweep_roles / rolecreator / rolesettings / setrole / unsetrole /
reactroles / removereactrole / listreactroles / temprole / temproles /
assignroles / debugroles / refreshmembers / createrole / deleterole /
roleinfo) → `goldens/role/`, and the 3-golden counting family
(sweep_count_rules / reset_count / toggle_reset_on_wrong_count) →
`goldens/counting/`. Gate 218/218 → **237/237** across the same 37
ported subsystems; `_unmapped` 220 → **201**.

Parity pins ORACLE behavior: 15 of the 16 role sweeps and all 3
counting sweeps REDDED on first replay — every red was a real port gap,
fixed PORT-side (handlers/renderer/ports), never golden-side. Oracle
reconstruction via search_code fragments @ corpus sha 7f7628e1
(role_cog.py, role_grants_cog.py, counting_cog.py,
views/roles/role_info.py, utils/role_feasibility.py,
utils/duration.py, services/role_lifecycle_service.py — trap 24
drift-diffed against the goldens first).

## What shipped

1. **Two port inventions retired ORACLE-WINS** (the D-0065 flip-review
   posture): the shipped `unsetrole` has NO miss branch
   (`match = next((...), role_name)` fallback + unconditional DELETE +
   unconditional ✅ ack — role_cog.py) and the shipped
   `removereactrole` acks unconditionally (role_cog.py:705); the
   band-5 "No such tier was configured." / "That binding did not
   exist." copies came OFF, with the two band-5 tests rewritten to pin
   the shipped semantics.
2. **Routes to the shipped truth**: `rolecreator` + `rolesettings` →
   `PanelRef("role.hub")` (shipped cog bodies are
   `ctx.invoke(self.roles_hub)`); `count_rules` →
   `PanelRef("counting.rules_card")` (the shipped static rules EMBED,
   new component-less session-lifecycle card, welcome recipe);
   `roleinfo`/`createrole`/`deleterole`/`assignroles`/`debugroles`/
   `refreshmembers` → six real handlers replacing pending terminals
   (the pending refs stay registered at module import — #111 roster).
3. **New role ports (moderation-actions posture — uninstalled ⇒ raise
   ⇒ honest BLOCKED)**: `RoleProvisioning`
   (`create_guild_role`/`delete_role` — method named away from the
   A-5 egress fence's banned bare verb `create_role`; the parity twin
   records the fake_http `create_role` wire verb verbatim incl. the
   2.x `colors.primary_color` body and mints the role id off the
   message-id allocator, the golden's `<msg:2>`; `delete_role` records
   an honesty GAP, no golden reaches a feasible delete) and
   `MessageOps` (`fetch_message`/`add_reaction` — the shipped
   !reactroles `get_message` + `add_reaction` wire pair).
4. **The capture-world guild view armed**: `_build_world_guild` in the
   parity boot installs `role.service.install_guild_source` with the
   GUILD_CREATE duck (roles @everyone + Admin@position-1/ADMINISTRATOR,
   members = 3 personas + bot, `me` = bot with top_role Admin) —
   debugroles' "Roles: @everyone, Admin", roleinfo's Members 2,
   deleterole's ABOVE_BOT self-tie refusal, assignroles' 0-assignment
   reconciliation all read it. `role.service.subscribe(bus)` armed in
   the parity boot (already on the live root's SUBSCRIBE_ROSTER).
5. **The shipped RoleLifecycleService companions**: `!createrole` emits
   `audit.action_recorded` (mutation_type `role_create`, target
   `role:<id>`, new_value `create role '<name>'`) + the NEW
   `role.lifecycle_changed` EventSpec (owner role, BEST_EFFORT,
   payload verbatim `mutation_id/guild_id/operation/outcome/applied/
   failed/occurred_at`, ONE shared mutation_id) — compat pin
   `event_payloads` grew the one row (`check_compat_frozen --write`,
   the 18g lane). deleterole's success path mirrors it (delete —
   live-only, gap-recorded in parity).
6. **Copy/guard fixes to shipped bytes**: listreactroles empty copy,
   temproles `whose` branch (`You have` self / `**{display_name}** has`
   other), temprole invalid-duration byte AFTER member/role converters
   + the shipped 1-year duration cap, setrole `display_name=role_name`
   column (services/role_automation.py), assignroles progress line via
   the RC-21 emitter + `format_role_check_result` verbatim,
   refreshmembers = the trap-11b capture artifact literal
   (`guild.chunk()` raised captureside; in-code note),
   `role.info_card` renderer (views/roles/role_info.py field order,
   `%Y-%m-%d` snowflake date, `Requested by {tag}` footer, teal
   default), feasibility `_REASONS` aligned to the shipped bytes
   (utils/role_feasibility.py verbatim — sweep_deleterole pins
   ABOVE_BOT).
7. **counting**: `_require_channel` ValidatorError flipped to the
   copy-only form (role `_verr` posture) — the shipped plain
   "Counting game is not set up for this channel." byte instead of the
   missing-argument envelope (the trap-22 class, #170); the
   `counting.rules_card` panel pins the shipped 5-field green embed.
8. **parity.yml**: role's TWO `covered-elsewhere` depth-exemption rows
   RETIRED (`table:role_thresholds`, `table:reaction_roles` — their
   sweeps now carry the rows IN-DIRECTORY; check_parity_depth agrees),
   the `table:role_grants` guard-only-capture citation re-pathed to
   `goldens/role/`; ratchet `role: {events: 3, tables: 5, settings: 0}`
   (scratch-learned, hand-applied — trap 1), counting unchanged
   `{events: 1, tables: 2, settings: 0}`.

## Ladder (serial, real Postgres — trap 25/27)

- check_parity_depth: `OK — 49 subsystems (37 ported), 465 goldens`
- manifest_compile: green (sha256:635d9701…, 46 manifests);
  check_namespace clean; check_sim_gate `OK — 1144 [A], 406
  auto-exempt below-floor` (ZERO new lock rows — both new cards are
  component-less session panels); check_compat_frozen OK after the
  one-row event_payloads amend; egress/escape-hatches/schema-growth/
  amendments/shadowing/no-skip/config/metric/intent/slash-cap all
  clean.
- units: **1388 passed / 2 skipped** local.
- gate: **GREEN — all 237 golden(s) across 37 ported subsystem(s)
  replay clean** (was 218).
- report: **green 276/465, replayable 465/465** (was 256/465).

## Under-port ledger (in-code notes carry each)

- reaction_view non-empty branch renders text (the shipped ⚙️ embed
  list is unpinned); temproles non-empty lines keep the port shape;
  compound duration forms ("2h30m") unported (no golden); the
  info-card colored-role accent needs a raw-color lane (grammar carries
  style tokens; capture roles are color 0); live arms for
  RoleProvisioning/MessageOps/guild_source are D-0049-class successors.

## 💡 Session idea

The remaining `_unmapped` map (201 goldens) still holds re-home-shaped
families over PORTED subsystems — likely candidates worth a replay
probe: the ticket admin family (sweep_ticketblacklist*/ticketlimit/
ticketpanel/ticketsetup → ticket), the word family (sweep_word*/
→ cleanup), starboard (7 goldens — needs a subsystem row first),
sweep_xpconfig/givexp/resetxp/xpimport (→ xp), sweep_modlogs/
clearwarnings/slowmode/lock/unlock (→ moderation/channel). Each
follows the same law learned here: move → replay → fix the PORT where
red — expect flip-sized work, not free greens (15/16 role sweeps
redded on first replay).

## ⟲ Previous-session review

(This previous-session review covers the #190 role flip, whose card
seeded this re-home.) Its "~14-golden re-home candidate … each needs
its own replay proof before moving" call was right in direction and
optimistic in cost: the re-home surfaced two port INVENTIONS (the
unsetrole/removereactrole miss branches band-5 added against oracle
truth — tests had enshrined them, the #163/D-0065 lesson recurring at
handler scale), one A-5 fence collision (a port method named after the
banned bare verb `create_role`), and the first golden-pinned domain
EVENTS outside a flip (`role.lifecycle_changed` + the audit companion,
which needed the parity boot to arm `role.service.subscribe(bus)` —
the live root's SUBSCRIBE_ROSTER already had it, so the gap was
harness-side only). The counting half cost exactly what the trap-22
class predicted: guards re-homed to the raise-site copy-only form.
