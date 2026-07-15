# 2026-07-13 — setup compound ops slice 2 (FINAL): routing resolver port + routing.set_policy + automation add_rule seam

> **Status:** `complete`

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

Landed as PR #429 (head 710c881). 2886 passed / 15 skipped (18 new in
tests/unit/setup_band/test_compound_routing_automation_ops.py — the
real K7 engine over the slice-1 FakeConn harness widened for the
routing/automation SQL, incl. the full resolver-precedence matrix:
channel beats category beats guild, absent = enabled, per-cog
isolation); bootstrap check --strict green minus this card's own
designed born-red hold; check_migrations + check_parity_depth clean;
manifest.snapshot.json recompiled — additive only (+1 manifest,
+2 stores, +2 engine markers, +6 workflow refs). Decisions flagged:
routing store/resolver/op placed in sb/domain/server_management/
(cog routing is its access-projection axis 3 — the ledger this slice
flips true); automation seam minted as its OWN domain + store-and-op
manifest (sb/domain/automation/ + sb/manifest/automation.py) so the
audit subsystem reads "automation" verbatim (oracle
emit_audit_action); op domains carry the oracle audit vocabulary
(cog_routing/set_cog_routing, automation/create_rule); both new
tables MEMBER_ID with tombstone erasure bodies (actor_id/created_by
scrub, the governance_audit_log posture); authority_ref="" (ADMIN
floor) on both ops — the setup apply gate's owner/admin class, same
as the settings ops the drafts already ride; NO dispatch-time command
enforcement ported because the oracle has none (routing.py module
ledger names the enforcement surface: projection + change-plan read);
the oracle's advisory automation.rule_changed event NOT emitted — its
only subscriber is the un-ported scheduler/executor (named successor,
sb/domain/automation/__init__.py); parity.yml gained the
select-driven exemption for table:command_routing_policy (the D-0064
class — the write sits behind the wizard's run-minted select chain).
CI red #1: check_compat_frozen (a standalone required job outside the
fleet loop, the PR #354 class) — the new `automation` subsystem key
drifted the frozen §5.3 `subsystem_keys` pin; amended via the
sanctioned `check_compat_frozen.py --write` path in this PR (never
hand-edited; CODEOWNERS routes the pin to owner review).

## 💡 Session idea

`_patch_owners` now exists in THREE band6 test files and each grew a
routing fake this session (test_band6_access_map / _help_preview each
patch read_policy_snapshot + fetch_visibility_for_chain + routing
.get_policy by hand) — every future axis added to the access
projection costs an N-file sweep and a subtle miss degrades tests to
"unknown"-effective instead of red. A small follow-up: one shared
`tests/unit/band6/conftest.py` fixture (`patch_access_owners`) owning
the full owner set, with per-test override kwargs; guard recipe —
lift test_band6_access_map._patch_owners into the conftest, re-point
both files, and pin it with a test that a NEW unpatched gating axis
makes the fixture fail loudly (assert every AccessAxis member is
either patched or non-DB).

## ⟲ Previous-session review

The setup-compound-1 session (2026-07-13, PR #419) closed with a 💡
warning that the engine records the once() outcome PRE-EFFECT, which
forced role.create_managed_role onto NONE_JUSTIFIED — this session
dodged that trap class entirely by keeping both new ops pure-DB
single-leg NATURAL_KEY (the keyed upsert / unique-name insert IS the
dedup), exactly the posture its card argued keyed config writes
should take; its reusable harness note (widen FakeConn + run the real
engine, mind the check_egress local-binding convention) was lifted
verbatim and cut this slice's test setup to minutes — the
lane-handoff discipline (oracle notes + slice-1 outcome appended in
one brief) is worth repeating for every multi-slice lane.
