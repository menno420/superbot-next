# 2026-07-19 — D3 access-audit M1 slice 1: persist per-channel role-sets

> **Status:** `in-progress`

- **📊 Model:** `[[fill:model-family]]`

## Scope

Execute **slice 1 of D3 access-audit M1** (`docs/decisions.md` D-0095: access
granularity is M1 per-channel; per-command deferred. Plan:
`docs/design/D3-access-audit-model.md`, its internal "M1" = persist
`channel_role_sets`; M2/M3/M4 are out of scope — still-open Q4/Q7/Q6).

The precise gap: `channel_role_sets` is modelled and ENFORCED in the resolver
(`sb/kernel/authority/channel_access.py` snapshot field + `role_not_held`
gate) but NEVER persisted — `_fetch_snapshot`
(`sb/domain/platform/command_access.py`) only reads `mode` + the channel
allowlist, so `channel_role_sets` always arrives as the default empty map.
This slice turns that dead capacity into a persisted, writable control (the
durable model + the write lane). NET-NEW rebuild design (the oracle has no
per-channel role concept) → NO oracle-replay golden; tested via store
round-trip unit tests. The resolver enforcement is already green — the
resolver/kernel are NOT touched.

Deliverables (mirror the existing allowlist lane closely):
- Migration `0057_command_access_channel_roles.sql`: new
  `guild_command_access_channel_roles` table (PK `(guild_id, channel_id,
  role_id)`, FK → `guild_command_access_policy` ON DELETE CASCADE).
- A third `StoreSpec` mirroring `guild_command_access_channels`.
- `_fetch_snapshot` fold: a third `fetchall` folding role rows into
  `channel_role_sets` as `{channel_id: frozenset(role_id, …)}`.
- Write leg `_record_set_channel_roles`: atomic DELETE-then-INSERT keyed on
  `(guild_id, channel_id)`; audit verb `command_access_channel_roles_set`.
- Op `SET_CHANNEL_ROLES` mirroring `SET_ACCESS_CHANNELS`; authority floor
  `administrator` (sibling-consistent).
- Wrapper `set_channel_roles(ctx, *, channel_id, role_ids, …)` with
  `forget_guild` write-through.
- Manifest snapshot recompiled for the new op/store.

No panel/handler/UI (that is Slice 2). No resolver/kernel change.

## ⚑ Flagged decision (decide-and-flag)

`SET_CHANNEL_ROLES` authority floor set to `administrator`, sibling-consistent
with the other command-access lanes (`set_access_mode` / `set_access_channels`).
The plan doc's **Q5** leaves open whether the role-set editor should instead be
owner-only. Defaulting to `administrator` for consistency; reversible.

## Result

`[[fill:result]]`
