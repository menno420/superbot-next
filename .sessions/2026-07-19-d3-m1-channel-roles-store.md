# 2026-07-19 — D3 access-audit M1 slice 1: persist per-channel role-sets

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

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

Landed the durable model + write lane on PR #586 (base main, from origin/main).
`channel_role_sets` — enforced in the K6 resolver since S9 but never persisted —
now has DB truth. Migration `0057_command_access_channel_roles.sql`
(`guild_command_access_channel_roles`, PK `(guild_id, channel_id, role_id)`, FK
→ `guild_command_access_policy` ON DELETE CASCADE) mirrors the 0018 channel
allowlist; checksum registered in `migrations/checksums.json` by recomputing the
sha256 (not hand-faked). `COMMAND_ACCESS_CHANNEL_ROLES_STORE` mirrors the
allowlist `StoreSpec` and joins the platform manifest stores tuple.
`_fetch_snapshot` gained a third `fetchall` that folds role rows into
`channel_role_sets` as `{channel_id: frozenset(role_id, …)}` (was always the
default empty map). `_record_set_channel_roles` clones the allowlist leg's
atomic replace, but keyed per-`(guild_id, channel_id)` — so writing one
channel's role set leaves other channels untouched (the allowlist leg clears the
whole guild; a per-channel role set must not). Op `SET_CHANNEL_ROLES` (audit
verb `command_access_channel_roles_set`, authority floor `administrator`) +
`set_channel_roles(ctx, *, channel_id, role_ids, allow_empty=False)` wrapper with
`forget_guild` write-through. `manifest.snapshot.json` recompiled (+45 lines: the
new op + store).

Verification: `tests/unit/band5/` + `tests/unit/authority/` → **171 passed**;
full `tests/unit --ignore=examples` → **3548 passed, 15 skipped** (the 2 new
band5 tests over the 3546 baseline). `check_compat_frozen` GREEN (a new op verb
is not a component custom_id, so no pin drift — the prediction held).
`check_symbol_shadowing` / `check_namespace` / `check_no_skip` /
`check_config_usage` clean; `manifest_compile` verify green. Migration
apply confirmed on live Postgres: `pool.init` ran the runner +
`verify_applied_checksums` with no exception, `guild_command_access_channel_roles`
present (5 columns), max applied version 57. No resolver/kernel change; no
panel/UI (Slice 2). Full golden-parity replay left to CI's authoritative gates
(no golden minted — net-new rebuild design, per the slice rule).

## 💡 Session idea

The slice's one non-mechanical judgement is the shape of the atomic replace, and
it is a rule worth pinning: **a replace leg's clear-scope must match the write's
natural key, not the table's parent key.** The allowlist leg
(`_record_set_access_channels`) clears `WHERE guild_id=$1` because a channel
allowlist IS a single per-guild set — the guild is the natural key. Cloning that
verbatim onto the role-set table would have been a latent data-loss bug: setting
channel A's roles would silently wipe channel B's, because the role-set's natural
key is `(guild_id, channel_id)`, not `guild_id`. The table's PK
(`guild_id, channel_id, role_id`) and its FK-to-guild both point at the guild,
so the parent-key instinct is doubly reinforced by the schema — yet the correct
clear scope is the narrower `(guild_id, channel_id)`. The general form: when
porting an atomic DELETE+re-INSERT lane onto a table with a FINER write
granularity than the source, the DELETE predicate must be re-derived from "what
one write call owns", never copied. This is the write-lane twin of S7's
widget-arity rule — both are cases where the faithful clone's *scope* (component
count there, DELETE predicate here) is a property the template silently fixes at
its own granularity.

## ⟲ Previous-session review

S7 (numeric-presets widget, #584) closed the settings `group_edit` widget
frontier; this slice is the first move on the *orthogonal* D3 access-audit axis,
so there is no direct build dependency — but S7's card earned its keep here as
the session-card template (Scope/Result/💡/⟲ shape, the family-level `📊 Model`
line, the "full replay left to CI" slice-rule posture all copied from it). One
forward note for the D3 M1 Slice-2 author: S7's dispatch-order lesson ("test the
ORDER/scope, not just the predicate") is exactly what the Slice-2 panel will need
when it wires a role-chip picker onto this store — the widget that writes a
role set will cross `PANEL_FLOOR` (a variable-arity chip row, per S7's arity
rule) and so will be the first D3 surface to need an explicit sim/Exempt record,
just as S7 was for settings.
