# 2026-07-13 — setup compound ops slice 2 (FINAL): routing resolver port + routing.set_policy + automation add_rule seam

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · setup compound-ops lane, slice 2 (final) ·
  mandate: control/claims/setup-compound-ops.md (slice 1 = PR #419, merged)

## Scope

Make the staged `set_cog_routing` and `add_automation_rule` draft rows APPLY
instead of failing closed (oracle-verbatim semantics — menno420/superbot @
f969b95, LOCAL clone), plus the command-routing resolver port:

- **routing port**: `command_routing_policy` migration (oracle 036 schema),
  a routing store + the `is_cog_enabled` resolver (channel → category →
  guild → default-TRUE, no cache) in sb/domain/server_management/, a
  `routing.set_policy` K7 compound op (read-old → upsert → central audit
  with real prev_value) bound to op_kind `set_cog_routing`, and the
  access_projection axis-3 wire (the "NOT PORTED" ledger flips true).
  NO dispatch-time command enforcement — the oracle has none.
- **automation-rule apply seam**: `automation_rules` migration (oracle 032
  schema), the minimal create-rule write path (template slug →
  trigger/action config; rules insert DISABLED; `scheduled_time` blocked),
  an `automation.add_rule` K7 op bound to op_kind `add_automation_rule`.
  The runtime consumer (scheduler/executor, 1,658 LOC) is OUT of scope —
  the oracle itself writes inert disabled rows.
- K9 bindings registered in the staging modules (cog_routing.py /
  preset_select.py); stale fail-closed docstrings + fail-closed test pins
  flipped to binding pins; unit tests per the slice-1
  test_compound_create_ops.py harness.

Definition of done: `python3 -m pytest tests/ -q` +
`python3 bootstrap.py check --strict` green; PR opened READY on
menno420/superbot-next.

## Close-out

(in progress)

## 💡 Session idea

(in progress)

## ⟲ Previous-session review

(in progress)
