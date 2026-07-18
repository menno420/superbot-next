# D3 — Access-control + audit-log data model (settings admin-audit surface)

> **Status:** `plan`
>
> A forward design **proposal** from the 2026-07-18 planning phase, opened per
> the completeness snapshot's recommendation to turn the D1–D6 lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`). This is a PLAN,
> not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line`
> at HEAD `fd6f71d` unless noted. (The docs-gate badge taxonomy has no
> `proposal` token — `bootstrap.py:270-282` — so the series-standard `plan`
> badge carries the proposal status; see the D4/D2 precedent.)

## TL;DR

The B6 admin-audit surface is **already armed** over a data model that
**already exists** — the completeness snapshot marks B6 **DONE**
(`docs/status/completeness-table-2026-07-18.md:42`) and records that the
scout's "9 actions + 2 selectors pending" survey was **stale**. So this is not
a "build the backing model from scratch" doc. The rebuild ships a per-guild
command-access policy store (`sb/domain/platform/command_access.py`) behind the
K6 authority resolver (`sb/kernel/authority/channel_access.py`) and a single
append-only central audit spine (`sb/kernel/workflow/audit.py` → `audit_log`).
The genuine, code-grounded gaps the "matrix / audit view / health chips"
framing *implies* but that the current model does **not** back are narrower and
real: (1) the per-channel **role-set** constraint is modelled in the resolver
but has **no persistence store** and no editor; (2) the oracle's
**delete-blocked-commands** toggle has no store column here (a ledgered
under-port); (3) there is **no per-command** granularity — access is per-guild /
per-channel only, never "who can run *which* command"; and (4) **health chips**
do not exist anywhere in the code — they are a net-new aggregate read if the
owner wants them. This doc proposes the durable model of record that closes
those four, and maps the "matrix editor / audit view / health chips" panel
taxonomy onto it.

## Problem

The settings hub advertises a command-access matrix, a recent-changes audit
view, and (per the survey) health chips. The honest current state, grounded in
the code:

### P0 — The premise is partly stale; state it plainly

The task framing ("9 actions + 2 selectors route to `settings.{action_id}_pending`
and all refuse") does not match HEAD. The `_hub_button` pending default still
exists (`sb/domain/settings/panels.py:300`,
`handler=target or HandlerRef(f"settings.{action_id}_pending")`) but **no hub
control uses it** — `settings_hub_spec` arms all five buttons and the one
selector with explicit `PanelRef`s (`panels.py:336-348`: `needs_setup` /
`invalid` / `missing_bindings` / `audit` / `command_access`, plus the
`subsystem_select` → `settings.open_group` navigation). The completeness table
records exactly this: *"All 5 hub buttons armed … The
`settings.{action_id}_pending` default (`panels.py:300`) is now dead/unreachable.
Scout's '9 actions + 2 selectors pending' was stale."*
(`docs/status/completeness-table-2026-07-18.md:42`). The **only** residual
pending terminal in the surface is `settings.group_pending` — the per-group
**scalar edit** page (`sb/domain/settings/handlers.py:242-243,277`), which is a
separate settings-mutation *write* slice, not an access/audit gap.

So the design question is not "what backs the refusing panels" (they do not
refuse) but **"what is the durable model of record that the armed panels read
and write, and where is it genuinely thin?"**

### P1 — The access-control model exists but is coarse (per-guild/per-channel, not per-command)

The write store is `sb/domain/platform/command_access.py`: two permanent
`StoreSpec`s — `guild_command_access_policy` (`:53-63`) and
`guild_command_access_channels` (`:65-75`) — with K7 compound-op lanes
`SET_ACCESS_MODE` / `SET_ACCESS_CHANNELS` (`:290-296`) that INSERT/UPSERT the
`mode` and atomically DELETE+re-INSERT the channel allowlist
(`_record_set_access_mode` `:147-171`, `_record_set_access_channels`
`:174-203`), each stamping `updated_by`/`created_by` = the actor
(`ctx.actor.user_id`). Reads go through a 60 s TTL cache
(`read_policy_snapshot` `:106-114`) that fills the K8 admission reader
(`install_access_reader` `:129-140`).

The decision half is `sb/kernel/authority/channel_access.py`: `AccessMode` is
the three shipped strings verbatim (`all_channels` / `selected_channels` /
`disabled_except_bootstrap`, `:38-45`) and `CommandAccessSnapshot` carries
`mode`, `allowed_channels`, and — critically — `channel_role_sets`, an
**optional per-channel role-set constraint** (`:47-61`) the resolver already
enforces (`_policy_verdict` `:99-102`: a channel with a configured role-set
admits only actors holding one of those roles, denial token `role_not_held`).

**The gap:** `channel_role_sets` is **modelled and enforced but never
persisted**. No store, no migration, no writer feeds it — a grep for
`channel_role_sets` finds only the resolver and its snapshot dataclass
(`sb/kernel/authority/channel_access.py:52-102`), never a DB read. So the R-16
per-channel role gate is dead capacity: it resolves, but the snapshot always
arrives with an empty mapping. Access is effectively **per-guild mode + a
channel allowlist** — there is no "who can run *which command*" matrix at all.

### P2 — The oracle carries model surface the rebuild deliberately dropped

The oracle's model (from its migrations) is richer in two named ways the
rebuild ledgered as under-ports:

- **delete-blocked-commands** — oracle migration `096_command_access_delete_blocked.sql`
  adds `guild_command_access_policy.delete_blocked_commands BOOLEAN NOT NULL
  DEFAULT FALSE`. The rebuild's store has **no such column**, and the panel
  documents the honest absence: *"the policy store carries mode + channels only
  … so both [toggle + embed field] stay out until that store column ports"*
  (`sb/domain/settings/panels.py:906-909`).
- **per-feature access projection** — the oracle's Access Map is a **display-only**
  projection of effective allow/deny per feature for a *simulated* audience tier
  (`/workspace/superbot/disbot/views/server_management/access_map.py:1-25`,
  over `services.access_projection.project_access_map`). The rebuild's nearest
  analogue is the read-only Access Policy Explorer
  (`settings.access` panel, `handlers.py:283-300`), which resolves *subsystem*
  visibility state per scope — governance, not command-access. There is no
  effective-access **matrix** surface in the rebuild.

### P3 — The audit-log spine exists and is consolidated, but the "audit view" reads only settings rows

The rebuild **consolidated** the oracle's several audit tables
(`governance_audit_log`, `settings_mutation_audit`,
`resource_provisioning_audit`, `economy_audit_log`, `feature_flag_audit`, … —
see `/workspace/superbot/disbot/migrations/006,029,030,025,014`) into **one**
central append-only spine: `sb/kernel/workflow/audit.py` → `audit_log`
(`AUDIT_LOG_STORE` `:41-59`, `retention="permanent"`,
`checkpoint_class=LEDGER`, `data_class=MEMBER_ID` with a TOMBSTONE erasure
ref). Every K7 compound op writes exactly one row in-txn via
`emit_central_audit` (`:72-121`): columns `mutation_id, subsystem,
mutation_type, target, scope, guild_id, prev_value, new_value, actor_id,
actor_type, occurred_at, detail, correlation_id`. So the command-access
mutations already audit themselves (their ops declare `audit_verb`
`command_access_mode_set` / `command_access_channels_set`,
`sb/domain/platform/command_access.py:293-296`).

The armed audit **view** (`settings.audit` panel) reads the last-10
`audit_log` rows *filtered to* `subsystem = settings`
(`sb/domain/settings/panels.py:800-819`, `WHERE subsystem='settings'`,
`_RECENT_LIMIT`). **The gap:** command-access writes land under
`subsystem = platform` (the op's `domain`), so **they do not appear in the
settings audit view** — the very panel that sits next to the Command Access
door does not show command-access changes. This is a filter/scope decision, not
a missing table.

### P4 — Health chips do not exist

A repo grep for `health` under `sb/domain/settings/` and `sb/kernel/settings/`
returns nothing; the completeness snapshot's B6 row makes no mention of them.
"Health chips" is part of the same stale scout survey as the "9 actions". If
the owner wants an at-a-glance health summary of the access/audit config
(policy configured? allowlist non-empty? recent audit activity? role-sets
defined?), it is **net-new** — a small aggregate read over the stores above,
with no existing surface to port.

## Goals / non-goals

**Goals**

- Name the **durable model of record** for command access + audit so future
  slices extend one store family, not several.
- Close the four real gaps: persist `channel_role_sets` (P1), decide the
  `delete_blocked_commands` port (P2), fix the audit-view scope so
  command-access changes are visible (P3), and specify health chips if wanted
  (P4).
- Map the "matrix editor / audit view / health chips" panel taxonomy onto the
  model, respecting the layer rules and the golden-parity posture.

**Non-goals**

- Re-porting the audit spine — it exists, is consolidated, and is permanent.
  This doc does **not** propose a second audit table.
- The per-group **scalar settings edit** page (`settings.group_pending`) — that
  is a separate settings-**mutation** write slice, out of scope here.
- A full RBAC/permissions engine. Authority tiers (`administrator` floor, owner
  override, R-16 role sets) already resolve in K6
  (`sb/kernel/authority/__init__.py`); this doc extends the **command-access**
  policy data, not the authority engine.
- Byte-for-byte oracle parity of the model — the rebuild has already chosen a
  *consolidated* audit spine over the oracle's per-subsystem tables (an owner
  question below asks whether that stands).

## Proposed design

### The data model

The model of record stays in the **`platform` command-access store family**
(`sb/domain/platform/command_access.py`) plus the **kernel audit spine**
(`sb/kernel/workflow/audit.py`). Three durable extensions:

**M1 — persist the per-channel role-set constraint (fills P1).** A new store,
sole-written by `platform.command_access_store`, keyed
`(guild_id, channel_id, role_id)` — the durable backing for
`CommandAccessSnapshot.channel_role_sets`:

```
guild_command_access_channel_roles
  guild_id    BIGINT  NOT NULL  -- FK guild_command_access_policy(guild_id) ON DELETE CASCADE
  channel_id  BIGINT  NOT NULL
  role_id     BIGINT  NOT NULL
  created_by  BIGINT            -- actor; NULL only for migration rows
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
  PRIMARY KEY (guild_id, channel_id, role_id)
```

`_fetch_snapshot` (`command_access.py:88-101`) gains a third read that folds
these rows into `channel_role_sets` (channel_id → frozenset of role_ids); a new
K7 lane `SET_CHANNEL_ROLES` mirrors `_record_set_access_channels`'s atomic
DELETE+re-INSERT shape and audits under `command_access_channel_roles_set`. No
change to the resolver — it already consumes the mapping
(`channel_access.py:99-102`). This turns dead capacity into a live control.

**M2 — the `delete_blocked_commands` column (resolves P2's under-port).** If the
owner wants the auto-delete behaviour, add
`guild_command_access_policy.delete_blocked_commands BOOLEAN NOT NULL DEFAULT
FALSE` (oracle migration 096 verbatim) and lift the ledgered absence at
`panels.py:906-909`. This is the smallest of the extensions — one column, one
toggle button, one resolver read on the cleanup auto-mod path.

**M3 — audit-view scope (fixes P3).** No schema change. Either (a) the
`settings.audit` panel widens its filter from `subsystem='settings'` to include
`subsystem='platform' AND target LIKE 'platform.set_access_%'`
(`panels.py:814`), or (b) command-access ops declare `subsystem='settings'`
instead of `domain='platform'` for audit purposes. Option (a) is a pure read
change and keeps the op's domain honest; recommended. This is the cheapest
high-signal fix — it makes the audit view actually cover the door beside it.

**M4 — health chips (net-new, P4, optional).** No new store: a pure aggregate
read (`health_summary(guild_id)`) over the three stores + `audit_log`, returning
a small fixed set of chip states, e.g.:

| Chip | Green when | Source |
|---|---|---|
| Policy | a `guild_command_access_policy` row exists | policy store |
| Allowlist | mode≠`selected_channels` OR ≥1 allowed channel | channels store |
| Role gates | (info) count of channels with role-sets | M1 store |
| Audit | ≥1 `audit_log` row for this guild in N days | audit spine |
| Lockout-safe | mode≠`disabled_except_bootstrap` OR operator reachable | policy store |

Chips are a `FieldsBlock` provider on the hub or a `settings.health` sub-panel;
read-only, no writes.

**Relationships / how it plugs into `sb/kernel/authority`.** Unchanged: the
domain store writes rows and fills the K8 reader
(`install_access_reader` `:129-140`); the K6 resolver
(`resolve_channel_access`) reads the snapshot and decides. M1 is purely
additive to the snapshot the resolver already destructures. **No kernel→domain
import edge** is introduced — the kernel authority band still imports only
`spec`/`namespace`/`observability` (`sb/kernel/authority/__init__.py` docstring),
and the domain store still fills the kernel's port from below, exactly as today.

### Module placement — extend the `platform` band, do not add a new band

Recommendation: **extend `sb/domain/platform/command_access.py`**, not a new
band. Justification, grounded in the layer map (`.claude/CLAUDE.md` §
Architecture):

- The command-access *store* already lives in `sb/domain/platform` and is the
  named sole-writer (`EngineRef("platform.command_access_store")`,
  `command_access.py:78-80`); M1/M2 are the same aggregate, same writer, same
  reader domains (`interaction`, `diagnostics`).
- The *audit* spine is a **kernel** band (`sb/kernel/workflow/audit.py`) and
  stays there — domains emit into it via the workflow engine, never write a
  parallel audit table. M3 is a read change in the settings **domain** panel.
- The settings *panels/handlers* stay in `sb/domain/settings` and **reuse** the
  platform write lanes (they already do — `handlers.py:429-476` calls
  `command_access.set_access_mode` / `set_access_channels`); M1's editor adds a
  selector + handler that calls the new `set_channel_roles` lane, no new write
  path.

A new band would fracture the sole-writer invariant and add a kernel→domain
temptation for no benefit. The one honest call: if the owner later wants
**per-command** access (P1's deeper form — "who can run *which* command"), that
is a genuinely larger model (a command × scope grant matrix) that *might*
warrant its own store; this doc scopes M1 to the **per-channel role-set** the
resolver already supports and flags per-command as an open question.

### Migrations / persistence (Postgres)

Forward-only, idempotent SQL through the existing migration runner
(`sb/kernel/db/migrations.py`), mirroring the oracle's style
(`CREATE TABLE IF NOT EXISTS`, FK `ON DELETE CASCADE`, composite PK). M1 is one
new table; M2 is one `ADD COLUMN IF NOT EXISTS`. Both register via `StoreSpec`
(`retention="permanent"`, `checkpoint_class=AGGREGATE`, the
`command_access.py:53-75` precedent) so the versioning/backup invariants cover
them automatically. The `audit_log` spine needs **no** migration — it exists.

### Parity treatment — per-case mint, like B2/B3

These are **data-driven** panels (button/select clicks over embed fields), not
attachment PNGs — so parity is the mintable-interaction posture B2/B3 use, not
a rendered-image golden. The armed panels already mint their custom_ids
per-panel (the compat freeze deliberately excludes `settings_command_access.*`
and `settings_hub.*` leaves — `panels.py:906-920` note), keeping
`compat/compat-frozen.json` untouched. New M1 controls (`ca_channel_roles`
selector, role-set editor) follow the same rule: run-minted custom_ids, one
claimant per leaf, `check_compat_frozen` stays green. Golden cases are
per-interaction mints: click `command_access` → assert the rendered embed
fields; pick a role-set → assert the re-rendered "Role gates" field; the audit
view (M3) asserts the widened row set. No PNG bytes, no attachment goldens.

## Affected surfaces

| Band | Files | Slice |
|---|---|---|
| domain / platform | `sb/domain/platform/command_access.py` — new `guild_command_access_channel_roles` `StoreSpec` + `SET_CHANNEL_ROLES` lane + `_fetch_snapshot` fold (`:88-114`); optional `delete_blocked_commands` (M2) | M1, M2 |
| kernel / db | `sb/kernel/db/migrations.py` — one new table + one `ADD COLUMN` | M1, M2 |
| kernel / authority | none for M1 (resolver already reads `channel_role_sets`, `channel_access.py:99-102`); M2 adds one resolver read on the cleanup path | M2 |
| domain / settings | `sb/domain/settings/panels.py` — role-set selector + field on the Command Access panel (`:938-1020`), widen audit filter (`:814`), optional `settings.health` sub-panel; `sb/domain/settings/handlers.py` — `ca_channel_roles` handler reusing the new lane (`:412-476` precedent) | M1, M3, M4 |
| kernel / workflow | `sb/kernel/workflow/audit.py` — **no change**; command-access ops already emit central rows | M3 |
| tests / parity | per-interaction golden mints for the role-set editor + widened audit view (B2/B3 posture); store round-trip + resolver enforcement tests; `check_compat_frozen` untouched | all |

No new band, no kernel→domain edge, no second audit table.

## Rough size + suggested slicing

Overall **M** (net-new is one small table + one column + read changes; the
resolver, write-lane pattern, and audit spine all already exist to copy).

- **Slice 1 — data model + migration (M1 store, M2 column)** — **S–M**. One
  `StoreSpec` + one migration table + one `ADD COLUMN`, the `_fetch_snapshot`
  fold, and the `SET_CHANNEL_ROLES` K7 lane (clone of
  `_record_set_access_channels`). Store round-trip + resolver-enforcement tests.
  Land first, standalone.
- **Slice 2 — matrix / role-set editor panels** — **M**. The role-set selector +
  "Role gates" field on the Command Access panel, the handler reusing the lane,
  per-interaction goldens. Depends on Slice 1. (If M2 lands, the
  delete-blocked toggle rides here.)
- **Slice 3 — audit view scope fix (M3)** — **S**. Widen the `settings.audit`
  filter so command-access changes appear; one read change + a golden asserting
  the widened rows. Independent of Slices 1–2.
- **Slice 4 — health chips (M4)** — **S–M**, **owner-gated**. Only if the owner
  wants them; the `health_summary` aggregate + a `FieldsBlock`/sub-panel + a
  golden. No store.

Suggested order: **Slice 3 → Slice 1 → Slice 2 → Slice 4** (Slice 3 is the
cheapest real-signal fix and is independent; Slice 4 waits on the owner).

## Open questions for the owner

1. **Consolidated audit spine vs oracle's per-subsystem tables.** The rebuild
   collapsed the oracle's `governance_audit_log` / `settings_mutation_audit` /
   `economy_audit_log` / … into one central `audit_log` (`audit.py:41-59`). Does
   this consolidated model stand as the model of record, or do you want the
   oracle's per-subsystem separation back? (This doc assumes the consolidated
   spine stays — a cleaner rebuild model, **not** byte-for-byte oracle parity.)
2. **Audit-log retention.** `audit_log` is `retention="permanent"` with a
   TOMBSTONE erasure ref (`audit.py:44,57-58`). Keep permanent (forensic spine),
   or add an owner-gated pruning/retention window (e.g. keep N months, archive
   older)? The store comment already flags "pruning = owner-gated retention".
3. **Granularity — per-channel vs per-command.** Today access is per-guild mode
   + per-channel allowlist + (proposed M1) per-channel role-sets. Do you want
   true **per-command** granularity ("who can run `/blackjack` specifically")?
   That is a materially larger model (a command × scope grant matrix, possibly
   its own store) — flag it and it becomes a D3-follow-on, not part of M1.
4. **`delete_blocked_commands` (M2).** Port the oracle's auto-delete-on-blocked
   toggle (migration 096), or leave it as a permanent under-port? It is the
   cheapest extension but adds behaviour (auto-deleting messages), so it is a
   product call, not a mechanical one.
5. **Who can edit the matrix.** All access controls currently sit on the
   `administrator` authority floor (`command_access.py:293` `authority_ref=
   "administrator"`; the hub buttons are `audience_tier="administrator"`,
   `panels.py`). Keep admin-floor, or restrict the **role-set / matrix** editor
   to **owner-only** (a higher bar for "who gates whom")?
6. **Health-chip definitions (M4).** Do you want health chips at all, and if so
   are the five proposed chips (Policy / Allowlist / Role gates / Audit /
   Lockout-safe) the right set and thresholds (e.g. "Audit green when ≥1 row in
   N days" — what N)?
7. **Audit-view scope (M3).** Should the settings audit view show **only**
   settings+command-access changes, or become a **guild-wide** recent-changes
   view across all `subsystem`s (economy, governance, xp, …)? The spine supports
   either; today it is `subsystem='settings'`-only (`panels.py:814`).
