# Session — mining vault deposit/withdraw write-faces port 2026-07-18

> **Status:** complete

- **📊 Model:** Opus 4 family · high · port

## Goal
Port backlog slice B1: the 🏦 Mining Vault panel's 📥 Deposit / 📤 Withdraw
write faces, which stood at pending terminals (`mining.vault_deposit_pending`
/ `mining.vault_withdraw_pending`, `sb/domain/mining/panels.py`). Make the two
buttons open a live G-10 modal (item + amount) that runs the audited
deposit/withdraw and replies to the invoker — faithfully reproducing the
superbot oracle's `_VaultMoveModal` submit flow onto the sb panel grammar.

## Scope
Modal-wiring slice, Path A (coordinator-confirmed) — precedent-consistent with
landed, gate-green siblings, no new kernel seam, no parity-machinery change.
Branch `claude/mining-vault-write-faces` off origin/main `0607d8f`. Born red
(`in-progress`) as the first commit; holds the PR red until the deliberate
Status flip lands.

The diff is exactly:
1. **Panel wiring** — `sb/domain/mining/panels.py`: `va_deposit` / `va_withdraw`
   become `defer_mode=DeferMode.MODAL` with a `VAULT_DEPOSIT_MODAL` /
   `VAULT_WITHDRAW_MODAL` `ModalSpec` (item + qty fields, qty default "1"),
   routed to two new handlers, `result_render=RESULT_CARD`. The two
   `pending_handler` registrations (`_vault_modal_handlers`) are removed.
2. **Handlers** — `sb/domain/mining/service.py`: `mining.vault_deposit_route` /
   `mining.vault_withdraw_route` read the modal `item`/`qty` fields and run the
   ALREADY-PORTED `mining.stash` / `mining.unstash` op via `_op_after`, then
   reply `<@u> {message}` (RESULT_CARD) — mirroring `stash_all_route` /
   `vaultupgrade_route` + the treasury Contribute precedent. A `_modal_qty`
   helper reuses the sb `!stash` argv posture (non-digit → 1).
3. **Tests** — `tests/unit/mining/test_mining_vault_move.py` (18 cases).
4. **Snapshot** — `manifest.snapshot.json` recompiled (P9 recompile-parity).
5. **Frozen-pin amend** — `compat/compat-frozen.json`: the two new modal ids
   (`mining.vault_deposit_form` / `mining.vault_withdraw_form`) legitimately
   grow the §5.3 `legacy_custom_ids` contract; refreezed the SANCTIONED way
   (`tools/check_compat_frozen.py --write`, never hand-edited). The pin file is
   CODEOWNERS-routed, so this PR is BLOCKED ON OWNER REVIEW of that amendment —
   the expected named blocker for this slice (it will not auto-merge on green).
6. **This card.**

**NO golden minted — and that is the honest, correct outcome.** The vault
deposit/withdraw WRITE is already byte-pinned by
`goldens/mining/mining_stash_write.json` + `mining_unstash_write.json` through
the LIVE `!stash` / `!unstash` command lane (the SAME `mining.stash` /
`mining.unstash` op the modal now runs). No curated case drives a vault-panel
click, and the parity harness cannot drive a modal submit (`runner.py::_drive`
has no `modal` branch; zero cases use `kind="modal"`), so this terminal is
UNMINTABLE. The MODAL-defer button renders identical session `<cid:N>` wire
bytes (the treasury Contribute precedent), so `sweep_vault.json` is diff-clean.
The write face is therefore covered by unit tests, NOT a fabricated golden.

### Accepted divergences (each mirrors a landed sibling, decide-and-flag)
- **RESULT_CARD text reply, not the oracle's in-place panel re-render** — the
  `stash_all_route` / `vaultupgrade_route` posture (mining vault panel writes
  reply `<@u> {message}`, they do not redraw the panel with a ✅/❌ note).
- **Verbatim item, no fuzzy resolver** — the oracle modal ran
  `resolve_item_name`; sb carries no vault-item resolver and `stash_route` /
  `unstash_route` already ship the verbatim-item posture, so the modal matches
  the command lane.

## Trail
- ORACLE: `disbot/views/mining/vault_panel.py` (`_VaultMoveModal.on_submit` →
  `mining_workflow.vault_deposit` / `vault_withdraw`) +
  `disbot/services/mining_workflow.py:548-601` (the atomic pack↔vault move +
  the Deposited/Withdrew copy, VERBATIM). The oracle `!stash` / `!unstash`
  commands (`mining_cog.py:584-618`) run the same workflow.
- SB REUSE: `mining.stash` / `mining.unstash` ops (`ops.py:554-598`) reproduce
  `vault_deposit` / `vault_withdraw` verbatim; already live + pinned via the
  command lane.
- Verify: `pytest tests/unit/mining/test_mining_vault_move.py` → 18 passed;
  full `tests/unit/mining/` → 118 passed (zero drift). `manifest_compile`,
  `check_runtime_smoke`, `check_namespace`, `check_symbol_shadowing`,
  `check_no_skip`, `check_config_usage`, `check_parity_depth`,
  `check_escape_hatches`, `check_compat_frozen` (after the `--write` refreeze)
  → all green. `sweep.vault` dry-run capture → zero
  vault-panel/button byte changes (the only capture delta is pre-existing
  local-vs-CI environmental drift — an `ai_decision_audit` NL row + a
  `delete_message` call — which B1 cannot cause and must not re-mint away).
- FOLLOW-UP (flagged, NOT in scope): `_record_stash` / `_record_unstash` (and
  `_item_from` / `_qty_from` / `_record_stash_all`) raise the SINGLE-arg
  `ValidatorError`, so their domain refusals ride `.param` and render wrapped
  in the missing-argument boilerplate instead of verbatim (the D-0060 two-arg
  form is the fix). This is a pre-existing latent bug SHARED with the
  `!stash` / `!unstash` command lane (unpinned by any golden); the modal
  inherits it identically, so B1 stays a clean modal-wiring slice and the
  refusal-copy fix is deferred.

## 💡 Session idea

The parity harness advertises a `kind="modal"` Step (dataclass +
`_describe_step` both handle it) but `runner.py::_drive` never implements the
drive branch and zero cases use it — a half-armed corpus vocabulary. Every
G-10 modal write face (treasury Contribute, the chain quartet, and now the
vault move) therefore ships golden-unpinned at its submit boundary, verified
only by unit tests. Wiring the `_drive` modal branch (a self-contained parity
slice) would let these submit flows be byte-pinned from a real boot — closing
the one place where "reuse the already-pinned op" is the strongest available
evidence rather than a golden. Worth a dedicated harness slice before the next
modal-heavy subsystem port.

## ⟲ Previous-session review

The 2026-07-18 tournament-open-toctou session (`complete`) correctly resolved
a backlog row as a posture-PIN once its accepted-posture ledger was read,
rather than forcing the originally-scoped fix — the "read the ledger before you
build" discipline. This B1 slice carries the same discipline into a PORT: the
phase-1 recon read the tree and found the write already pinned via the command
lane and the submit boundary unmintable, so it deliberately ships as a
precedent-consistent modal-wiring slice with an honest "no golden minted"
statement instead of fabricating parity — and, like the tournament session,
files the one real defect it uncovered (the single-arg-ValidatorError refusal
wrap) as a flagged follow-up rather than smuggling an out-of-scope fix into the
slice.
