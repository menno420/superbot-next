# 2026-07-13 — setup compound ops slice 1: ensure-channel + create-managed-role (K9→K7)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · setup compound-ops lane, slice 1 · mandate:
  control/claims/setup-compound-ops.md (PR #414)

## Scope

Make the staged `create_managed_role` and `create_channel` draft rows APPLY
instead of failing closed: two new K7 compound ops (oracle-verbatim
semantics — menno420/superbot @ f969b95, LOCAL clone), plus the K9
`OpKindBinding` registrations in the setup modules that stage the kinds.

- **ensure-channel** (`setup.ensure_channel`, sb/domain/setup/ops.py next to
  its D-0077 compensator): name-based reuse via the ChannelDirectory READ
  port (get-before-create is DOMAIN logic — D-0077) → create through the
  channel-state port → slot bind through `settings.bind` (bind failure does
  NOT undo the channel — the oracle `binding_failed` outcome) → audit
  (K7 central row) + lifecycle advisory.
- **create-managed-role** (`role.create_managed_role`, sb/domain/role/ops.py):
  apply-time UNCONDITIONAL create via the RoleProvisioning port (idempotency
  stays at plan/stage time, per oracle), spec from `payload["role_template"]`
  (name/color/hoist/mentionable — NO permissions by design), best-effort
  threshold fold through `role.set_threshold` (a failed tier never undoes
  the role), audit + lifecycle.
- K9 bindings registered in role_templates.py / logging_presets.py (the 4
  existing registrations' pattern); stale fail-closed docstrings updated;
  unit tests per tests/unit/setup_band conventions.

Definition of done: `python3 -m pytest tests/ -q` +
`python3 bootstrap.py check --strict` green; PR opened READY on
menno420/superbot-next.
