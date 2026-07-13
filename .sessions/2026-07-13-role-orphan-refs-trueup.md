# 2026-07-13 — role: retire the three orphan `_pending` refs + completeness-table true-up

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · completeness-remainders hygiene lane
  (claim `control/claims/completeness-remainders.md` follow-through —
  post-#405 remainder audit; branch `claude/role-orphan-refs-trueup`
  off main @ e17fb2a)

## Scope

Small hygiene slice, two legs:

1. **Retire the three orphan role pendings.** `role.roleinfo_pending` /
   `role.assignroles_pending` / `role.debug_pending` were registered in
   `_register_pending()` (sb/domain/role/handlers.py) but UNREACHABLE:
   the live handlers landed via #358 (`role.roleinfo` /
   `role.assignroles` / `role.debugroles`, wired at
   sb/manifest/role.py:84/97/112, goldens pinned) and nothing routed to
   the pendings — re-verified at HEAD e17fb2a: the compiled snapshot
   carried them only as bare `projections/refs` entries (no command,
   panel, or route targets them), and the only other reference was the
   band-5 import-registration test. Retired per the role.create
   precedent (ORDER 017 edits A, #358): `_register_pending()` removed,
   the module-import doctrine (band-5 live-drive bug 1 — declaring IS
   reserving) carried as a comment on the module-level registration
   block, the module docstring trued up;
   `test_pending_terminals_registered_at_module_import` re-pinned as
   `test_handlers_registered_at_module_import` on the live refs;
   `manifest_compile --write` dropped exactly the 3 refs entries
   (compat pin unmoved — no persistent roots changed).
2. **True-up docs/status/completeness-table-2026-07-13.md.** Rows
   flipped with citations: server_management admin ✅ (#332 routes the
   hub moderation/roles/cleanup nav trio to the ported hubs), cleanup
   admin ✅ (#333 words/logging · #408 settings/anti-evasion · #411
   policies — zero cleanup pendings remain), fishing core ✅ (#410
   retires `fishing.howtofish_pending`; the cast-leg starter-profile
   residue stays ledgered fidelity, not a pending terminal). Headline
   counts re-summed (core 44✅/5⚑ · admin 46✅/3⚑ · setup 47✅/2⚑) and
   top-gaps items 1/6 annotated; badge + format intact; no other rows
   touched (the utility row's #332 Invite mention is knowingly left —
   out of this slice's scope). Honest note added on the roles row: the
   oracle hub→manager back-button ("↩ Server Management",
   disbot/views/server_management/hub.py:169) is unported EVERYWHERE —
   needs a route-origin signal in the panel engine; decision-sized
   follow-up, not ledgered elsewhere.

## Verification

Shipped as PR #412 (`claude/role-orphan-refs-trueup` @ b302d7c, off main
@ e17fb2a — origin/main did not move during the slice, no merge needed):

- `python3 -m pytest tests/ -q` (local Postgres DOWN — the banner-test
  posture): **2821 passed, 15 skipped**.
- `python3 tools/run_golden_parity.py --gate` (local Postgres up via
  tools/setup_local_env.py): **GREEN — all 494 golden(s) across 50
  ported subsystem(s) replay clean** (goldens untouched; the snapshot
  diff is refs-only, so the gate run is belt-and-braces).
- Guards: `check_parity_depth` OK (494) · `manifest_compile` green
  (sha 99ebfbcd…) · `check_compat_frozen` OK without regen (no
  persistent roots moved — the #408 regen procedure was NOT needed) ·
  namespace / shadowing / no-skip / config-usage clean.
- `bootstrap.py check --strict`: green modulo this card's designed
  born-red hold (flips with this commit) + the pre-existing
  claims-format advisory (control/claims/mining-write-parity-lane.md,
  not this lane's file).

## 💡 Session idea

The orphan class this slice retired — a pending terminal whose live
twin already landed, kept alive only by its own registration and a test
that pins the pending NAME — is mechanically findable: every
`pending_handler(...)` name that no manifest route, panel handler, or
snapshot consumer references outside `projections/refs` is an orphan.
A small `tools/check_orphan_pendings.py` (walk the snapshot's routed
refs, diff against the registered `*_pending` set) would turn the next
#358-style "live handlers landed, pendings forgotten" residue into a
same-PR red instead of a weeks-later audit find. Cheap: the snapshot
already carries both sides.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-cleanup-policies-panel.md` @ e17fb2a,
PR #411.) Load-bearing and accurate: its Postgres-DOWN pytest posture
(2821/15 — reproduced exactly here), its strict-tail shape (born-red
hold + the same pre-existing mining-write-parity claims advisory), and
its #408 compat-regen pointer all transferred; this slice confirmed the
regen is conditional (refs-only snapshot diffs don't move the pin —
worth knowing). Its COUNT-PIN CORRECTION (five sites, not four) was
harvested into the team memory this session as ordered. Its 💡
(count-pin-coherence guard test) remains unbuilt and still right — and
this session's own orphan-pending find suggests the same shape
generalizes: derived-consistency checks over the snapshot beat prose
enumerations, whether the number is a golden count or a pending roster.
