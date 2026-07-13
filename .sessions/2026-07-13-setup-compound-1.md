# 2026-07-13 — setup compound ops slice 1: ensure-channel + create-managed-role (K9→K7)

> **Status:** `complete`

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

## Close-out

Landed as PR #419 (head 082cbd8). 2833 passed / 15 skipped (11 new in
tests/unit/setup_band/test_compound_create_ops.py — real K7 engine over
the widened FakeConn + fake ports); bootstrap check green minus this
card's own designed born-red hold; check_egress clean (the ensure leg
rides the sanctioned `actions = active_actions()` port-binding local);
manifest.snapshot.json recompiled — 7 new workflow refs, purely
additive. Decisions flagged: role op placed in sb/domain/role/ops.py
(oracle routes create through the role domain's lifecycle owner),
ensure-channel in sb/domain/setup/ops.py beside its D-0077 compensator;
RoleProvisioning widened with keyword-only hoist/mentionable (defaults
False — !createrole lane + goldens byte-identical); lifecycle advisory
mints its own mutation_id while the audit fact rides the engine's
central row (the oracle's shared-id pair has no K7 seam — ledgered in
both leg docstrings).

## 💡 Session idea

The engine records the once() outcome at step 4f, BEFORE the EFFECT
legs run (sb/kernel/workflow/engine.py `_in_txn` → `record_outcome`),
so any EFFECT-substance op under DURABLE_ONCE would false-SUCCESS a
retry whose create leg never ran — the exact trap that forced
`role.create_managed_role` onto NONE_JUSTIFIED. A small K7 follow-up —
record the ROLLED-UP outcome after `_run_effect_legs` (or a second
CAS-update of the guard row post-effects) — would let resource-create
ops ride durable dedup honestly; guard recipe: engine.py step 4f +
`_run_effect_legs`, pin with a DURABLE_ONCE spec whose EFFECT leg fails
then replays in tests/unit/workflow/test_engine.py.

## ⟲ Previous-session review

The ticket-setup-panel session (2026-07-13, slice B) landed its wizard
port with the golden gate green and ledgered the missing guild-census
read seam instead of smuggling a port change into domain work — this
session rode that discipline directly when the role-template spec
needed hoist/mentionable: the port widening shipped as an explicit,
defaults-preserving surface change (protocol + live adapter + parity
twin + contract pin) rather than an in-leg workaround, exactly the
boundary that card's 💡 idea argued for.
