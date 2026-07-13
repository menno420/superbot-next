# 2026-07-13 — role: retire the three orphan `_pending` refs + completeness-table true-up

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · completeness-remainders hygiene lane
  (claim `control/claims/completeness-remainders.md` follow-through —
  post-#405 remainder audit; branch `claude/role-orphan-refs-trueup`
  off main @ e17fb2a)

## Scope

Small hygiene slice, two legs:

1. **Retire the three orphan role pendings.** `role.roleinfo_pending` /
   `role.assignroles_pending` / `role.debug_pending` are registered in
   `_register_pending()` (sb/domain/role/handlers.py) but UNREACHABLE:
   the live handlers landed via #358 (`role.roleinfo` /
   `role.assignroles` / `role.debugroles`, wired at
   sb/manifest/role.py:84/97/112, goldens pinned) and nothing routes to
   the pendings — the compiled snapshot carries them only as bare
   `projections/refs` entries, and the only other reference is the
   band-5 import-registration test. Retirement follows the role.create
   precedent (ORDER 017 edits A, #358): drop the registrations, carry
   the module-import doctrine comment, update
   `test_pending_terminals_registered_at_module_import`, recompile the
   manifest snapshot to drop the three refs entries.
2. **True-up docs/status/completeness-table-2026-07-13.md.** The
   server_management / cleanup / fishing rows (and their §6 top-gaps
   lines) still describe residues that are now resolved: #332/#358
   already-landed (server_management trio), #408 + #411 (cleanup
   settings/anti-evasion/policies), #410 (fishing howtofish). Only
   those rows change; plus one honest note on the roles row — the
   hub→manager back-button ("↩ Server Management", oracle
   disbot/views/server_management/hub.py:169) is unported everywhere
   and needs a route-origin signal in the panel engine (decision-sized
   follow-up, not ledgered elsewhere).

## Verification

(To be filled at close-out: pytest tail, strict tail, replay gate if
the manifest recompile moves goldens-adjacent state.)

## 💡 Session idea

(To be filled at close-out.)

## ⟲ Previous-session review

(To be filled at close-out — will cover the newest card at branch time,
`.sessions/2026-07-13-cleanup-policies-panel.md` @ e17fb2a, PR #411;
the previous-session review completes when the work is verified.)
