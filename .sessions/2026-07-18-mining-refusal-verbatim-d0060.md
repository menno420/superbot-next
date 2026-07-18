# Session — mining stash/unstash refusals render verbatim (D-0060) 2026-07-18

> **Status:** `in-progress`

- **📊 Model:** Opus 4 family · high · fix

## Goal
Slice C6: fix the D-0060 single-arg `ValidatorError` bug in the mining
stash/unstash lane so domain refusals render VERBATIM instead of wrapped in the
missing-argument boilerplate. The vault deposit/withdraw/stash-all op legs (and
the shared `_item_from` / `_qty_from` argv helpers) raised
`ValidatorError(sentence)` — the whole domain sentence rode the `param` slot, so
`sb.kernel.interaction.errors.from_exception` wrapped every refusal in
"Missing/invalid argument: `<sentence>`. `!help …` for usage." instead of the
shipped oracle copy. Convert each to the established D-0060 TWO-arg form
`ValidatorError(param, message)` so the 2nd arg is the verbatim user copy the
render layer speaks bare — matching the oracle `mining_workflow.vault_deposit` /
`vault_withdraw` / `vault_deposit_all_resources` strings.

## Scope
Contained to mining, unit-testable, **NO golden minted** (the refusal branches
are unpinned by any golden — no curated case drives an insufficient/absent
stash; the parity harness cannot drive the modal submit, and the command lane's
existing goldens pin only the SUCCESS write). Branch
`claude/mining-refusal-verbatim-d0060` off origin/main `10615b5` (#520 merged).
Born red (`in-progress`) as the first commit; holds the PR red until the
deliberate Status flip.

The diff is exactly:
1. **The fix** — `sb/domain/mining/ops.py`: five raise sites converted to the
   two-arg form. `_item_from` (`ValidatorError("item", "Name an item.")`),
   `_qty_from` (`ValidatorError("qty", "Quantity must be positive.")`),
   `_record_stash` (`("item", "You have {owned} to deposit.")`),
   `_record_unstash` (`("item", "Your vault holds {owned}.")`),
   `_record_stash_all` (`("item", "You have no raw resources to stash — go mine
   some!")`). Copy byte-identical to the pre-fix sentences; only the arg slot
   changes so `.user_copy` (not `.param`) carries the sentence.
2. **Command-lane coverage** — the fix lands at the SHARED op legs + helpers.
   Both the modal/panel path (`mining.vault_deposit_route` /
   `vault_withdraw_route`) AND the `!stash` / `!unstash` command path
   (`stash_route` / `unstash_route`) route to the SAME `mining.stash` /
   `mining.unstash` / `mining.stash_all` op, so ONE op-level fix covers every
   lane — no separate command-lane callsite exists.
3. **Tests** — `tests/unit/mining/test_mining_refusal_verbatim.py` (7 new cases,
   asserting the rendered envelope carries the exact sentence with NO
   boilerplate wrapper, driven through `from_exception` WITH a target so the
   wrap-path is exercised and proven skipped); and
   `tests/unit/mining/test_mining_vault_move.py` (6 refusal assertions flipped
   from the old buggy `.param == sentence` to `.user_copy == sentence`, and the
   deferred-follow-up NOTE rewritten as the landed behaviour).
4. **This card.**

## Trail
- BUG: `ValidatorError.__init__(param, message="")` (`sb/kernel/interaction/
  errors.py:38-41`) puts a single arg in `param` and leaves `user_copy=None`;
  `_user_message` (`errors.py:85-95`) renders `user_copy` verbatim when set,
  else the "Missing/invalid argument: `<param>`. `!help <cmd>` for usage." wrap.
  Single-arg raise → sentence in `param` → wrapped. The D-0060 fix is the
  two-arg form (`docs/decisions.md` D-0060; band-3 finding).
- PRECEDENT: the two-arg form is the established convention across the tree —
  mining's own `_record_equip_title` (`ops.py:356`, "two-arg D-0060 form: the
  raise site owns the sentence VERBATIM"), `_record_allocate` (`ops.py:914`),
  xp `ops.py:112/127`, role `_verr` (`role/ops.py:44` — the empty-param twin),
  economy `_DomainRefusal`. Band-3/4/5 all fixed this exact single-arg-wrap bug
  in their refusal families (decisions D-0060/D-0061).
- ORACLE (menno420/superbot): `disbot/services/mining_workflow.py:563-615` —
  `vault_deposit` / `vault_withdraw` / `vault_deposit_all_resources` return the
  refusal sentences VERBATIM ("You have {owned} to deposit." / "Your vault holds
  {owned}." / "You have no raw resources to stash — go mine some!", owned =
  "only **{have}× {item}**" | "no **{item}**"). The fix makes sb render these
  bare, matching the oracle.
- THIS SLICE realises the follow-up the 2026-07-18 mining-vault-write-faces (B1)
  card flagged (its Trail §FOLLOW-UP, lines 82-89) — the pre-existing latent
  single-arg refusal-wrap bug it deliberately deferred to keep B1 a clean
  modal-wiring slice.
- Verify: `pytest tests/unit/mining/test_mining_refusal_verbatim.py
  test_mining_vault_move.py` → 25 passed; full `tests/unit` → 3291 passed, 2
  skipped; `tests/test_session_card_gate.py` → 2 passed;
  `tools/check_compat_frozen.py` → OK (this fix touches no custom_ids). No
  `golden --gate` run — the refusal path is golden-unpinned and unit-tested.

## 💡 Session idea

The single-arg-`ValidatorError`-wraps-the-sentence bug has now been found and
fixed band-by-band (economy D-0060, xp/karma D-0061, role/proof_channel/
governance band-5, and now mining C6) — always the same shape, always caught
late (live-drive or a sibling's flagged follow-up), because the render layer
silently downgrades a domain sentence into a `param` label with NO signal at the
raise site. A cheap standing guard would end the whack-a-mole: an AST checker
(the `tools/check_*` lineage) that flags any `ValidatorError("<a sentence>")` —
a single-arg call whose sole arg contains a space or ends in `.`/`!`/`?` — as a
probable mis-slotted domain refusal, steering the raise to the two-arg form.
The `.sessions/2026-07-14-title-equip-write.md` card already names the audit
recipe (`rg -n 'ValidatorError\('`); promoting it to a CI checker would make the
convention self-enforcing before the next domain port re-plants it.

## ⟲ Previous-session review

The 2026-07-18 mining-vault-write-faces (B1) session (`complete`) is the direct
parent: it ported the vault deposit/withdraw modal write faces and, with
"read-the-ledger" discipline, deliberately did NOT smuggle an out-of-scope fix
into the slice — instead it FILED the single-arg-`ValidatorError` refusal-wrap
defect it uncovered as an explicit flagged follow-up (its Trail §FOLLOW-UP) and
left a NOTE-pinned test documenting the buggy `.param` behaviour. This C6 slice
is that follow-up executed: it honours the same discipline in reverse — a
contained, single-purpose fix that touches ONLY the flagged refusal raises,
flips the parent's deferred NOTE-tests to assert the corrected verbatim render,
and mints no golden because the refusal branch remains genuinely unpinned. The
parent's honesty (flag, don't smuggle) is what made this slice a clean,
self-contained unit of work.
