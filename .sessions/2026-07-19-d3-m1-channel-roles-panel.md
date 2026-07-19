# 2026-07-19 — D3 access-audit M1 slice 2: per-channel role-set editor panel

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · shape]]

## Scope

Execute **slice 2 of D3 access-audit M1** (`docs/decisions.md` D-0095; plan
`docs/design/D3-access-audit-model.md`). Slice 1 (#586, merged) landed the
durable model + write lane: migration 0057 `guild_command_access_channel_roles`,
the `SET_CHANNEL_ROLES` op, the `set_channel_roles(ctx, *, channel_id,
role_ids, allow_empty=False)` wrapper, and the `_fetch_snapshot` fold that now
populates `channel_role_sets` as `{channel_id: frozenset(role_id, …)}`. That
capacity is persisted + enforced (K6 resolver `role_not_held` gate) but has NO
UI to write it. This slice adds the UI.

Deliverables (on `settings.command_access` only — no group_edit involvement):
- A **"Role gates" FieldsBlock field** on the command_access panel rendering the
  snapshot's per-channel role-sets (channel → roles) so the operator sees what
  is set.
- A **role-set editor control** — run-minted custom_id `ca_channel_roles` — plus
  a `settings.ca_channel_roles` handler that calls Slice 1's `set_channel_roles`
  lane.
- The refresh path re-reads the snapshot after a write (mirrors
  `_refresh_command_access`).

Tested via per-interaction custom_id mint / render assertions (B2/B3 posture, no
oracle-replay golden — net-new rebuild surface). Recompile manifest if
components change. `check_compat_frozen` stays GREEN (the
`settings_command_access.*` leaves are excluded from the freeze).

Stacked from Slice 1's branch; rebased `--onto origin/main` after #586 squash-
merged (Slice 1 SHA `64973d4b185163766e633838c7f067ec785264ae`) — PR shows a
clean panel-only diff.

## ⚑ Flagged decision (decide-and-flag)

[[fill: the editor UX shape chosen (current-channel-bound RoleSelect vs
channel-then-roles two-step) + one-line rationale]]

## Result

[[fill: what landed, files, verification counts, compat + manifest status]]

## 💡 Session idea

[[fill: the one non-mechanical judgement worth pinning]]

## ⟲ Previous-session review

[[fill: one-line review remark on the Slice-1 session card]]
