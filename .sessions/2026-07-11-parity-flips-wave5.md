# 2026-07-11 — parity flips wave 5 (sim-gate value-drift hardening)

> **Status:** `complete`

- **📊 Model:** Fable · high · bug fix (Q-0194)

## Scope

Trap-30 hygiene fix (the #190 role-flip ledger follow-up,
control/status.md #190 entry: "a value-comparing checker is the hygiene
follow-up"): `tools/check_sim_gate.py` did not flag VALUE drift on an
existing [A] pin — `current_assignments()` merged the
`manifest/layout/*.lock.json` overlays LAST, so a stale overlay value
overwrote the manifest-derived value before the diff; both "current" and
the baseline carried the OLD value while the manifest shipped the NEW
one, and nothing redded (observed on #190: role.hub's 3/2/2→3/3/1
reshape passed silently).

## What shipped

1. **The value-comparing checker** (`tools/check_sim_gate.py`):
   `manifest_assignments()` exposes the raw manifest-derived [A]
   assignments BEFORE the overlay merge, and `overlay_mask_problems()`
   reds any key present on BOTH sides whose overlay value differs from
   the manifest-derived value (overlay-masks-manifest drift), naming the
   key, the overlay value, and the manifest value. `check()` runs it;
   `--write-baseline` REFUSES (exit 1) instead of silently re-pinning a
   stale overlay value. Overlay-ONLY keys (legacy-seed Exempt rows with
   no manifest-derived counterpart — the setup `WizardSectionSpec.order`
   seeds) stay legitimate; auto-exempt below-floor keys stay outside the
   gate's jurisdiction, matching every other check.
2. **42 existing masked drifts found and amended to the manifest truth**
   (the first run of the hardened checker over HEAD redded them all):
   - 6 REAL reshape residues, exactly the #190 class:
     `games:games.world` ×3 (manifest gained `world_deathmatch` +
     `world_casino`; lock/baseline still pinned the 2-row split without
     them) and `server_management:server_management.hub` ×3 (the #179
     `help_back` row never reached the lock/baseline).
   - 36 seed-time `"value": 0` placeholders (ai ×24 — 4 panel layout
     trios + 11 `SettingSpec.group` + 1 `BindingSpec.group`; btd6/chain/
     counting/projmoon hub trios ×3 each) that had masked every reshape
     of those keys since the legacy seed.
   Provenance untouched (all legacy-seed Exempt); baseline regenerated
   via the hardened `--write-baseline` — 738 pins, zero keys
   added/removed, exactly 42 values changed, zero provenance churn.
3. **Regression tests** (`tests/unit/sim_runner/test_run_and_gate.py`,
   `TestOverlayMasksManifestDrift`): overlay masking a reshaped manifest
   value → red; overlay-only key → still green (check + write-baseline);
   `--write-baseline` refusal on drift (baseline file byte-unchanged);
   matching overlay value → green. 45/45 sim_runner tests pass.

## Traps confirmed / new intel

- **Trap 30 closed at the checker**: the masked-drift class can no
  longer pass silently; a reshape now demands the lock amendment in the
  same PR (the #190 hand-amend recipe is now machine-enforced).
- **The seed placeholders were a standing mask**: `"value": 0` entries
  (band-6/7 seeds) made every subsequent reshape of those keys
  invisible to the gate — the games.world deathmatch/casino row and the
  server_management help_back row both slipped through this hole.
- Trap 25 honored: no Postgres ladder run in this slice (a sibling
  worker owned the shared Postgres); the slice is checker + lock/
  baseline bytes + unit tests, verified with the non-Postgres suites.

## Verification

`python3 tools/check_sim_gate.py` → OK (1159 [A] assignments, 421
auto-exempt below-floor); full CI-scope `pytest tests/` → 1407 passed,
4 skipped; `manifest_compile` green; kit `check --strict` green. No
Postgres ladder run (trap 25 — a sibling worker owned the shared
Postgres; this slice never touches replay surfaces).

## 💡 Session idea

The 36 seed placeholders suggest auditing the OTHER seed-era lock
carriers for `"value": 0` on keys that later gain manifest counterparts
(e.g. `CommandSpec.help_section_order` rows) — today they compare equal
only while the manifest side also derives 0.

## ⟲ Previous-session review

The #190 role card ledgered this exact gap and prescribed the fix
("a checker that compares pinned values is the hygiene follow-up") —
the prescription held: the hardened checker's first run found the two
real reshape residues the card's class predicted, plus a 36-key
placeholder mask nobody had seen.
