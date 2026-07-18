# 2026-07-18 — verify + mark backlog C2/C3 status at HEAD

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · review/verify

## Scope

Verify two hardening items from the merged production-readiness backlog
(`docs/status/prod-readiness-backlog-2026-07-17.md`) at live HEAD and, if
genuinely closed, mark them DONE with dated, evidence-cited notes. This is
the sibling-owner-delegated backlog edit (C2/C3 lines only).

- **C2 — effect-leg compensation gaps.** Ref
  `docs/ideas/effect-leg-compensation-gaps-2026-07-10.md`, NEXT-TASKS #3.
  Sibling reported SHIPPED in #105.
- **C3 — ensure-only registration gaps.** Ref NEXT-TASKS #3. Sibling
  reported the gap EMPTIED in #508.

## Verdict (verified at HEAD `1bcc8e3`)

**C2 — CLOSED.** #105 (merged 2026-07-10, `842bafb`) landed the two
compensators + the class-killer invariant; the moderation parity flip
(2026-07-11) then went further — `moderation.timeout` was restructured to
have NO effect leg at all (`sb/domain/moderation/ops.py:520-526`, oracle
call-Discord-first sequencing), and `kick` also gained a compensator.
At HEAD every EFFECT leg after a DB leg in `sb/domain/moderation/ops.py`
and `sb/domain/proof_channel/ops.py` is `compensatable` with a wired
compensator; `proof_channel.compensate_unlock` is live
(`sb/domain/proof_channel/ops.py:173-217, 261-262`). The class-killer
`tests/unit/workflow/test_compensator_invariant.py` ships an EMPTY
`_ALLOWLIST` (line 23) and passes at HEAD — the defect class is
unwritable.

**C3 — CLOSED.** #508 (merged 2026-07-17, `cbc3ab2`) registered the last
ensure-only ref (`panel:role.hub`) at module import
(`sb/domain/role/panels.py:362-386`, the #111 pattern) and pruned it from
the burn-down set. At HEAD `_KNOWN_ENSURE_ONLY` in
`tests/unit/invariants/test_composition_parity.py:35-36` is an EMPTY
frozenset; `test_composition_parity.py` passes — no live-invisible refs
remain.

Both invariant tests green at HEAD (`7 passed`). No fix needed; this PR
carries the backlog-status annotation only.

**B7 — xp.config panel actions — DONE (folded in mid-session on coordinator
delegation).** Stale-listed as pending but already ported + landed on main
(curation-rework chain, `46b545e`); verified at HEAD. Panel `xp_config_spec()`
(`sb/domain/xp/panels.py:267`) registered in `sb/manifest/xp.py:156`; the 4
handlers live in `sb/domain/xp/handlers.py` (:159/:181/:194/:236); no
`*_pending` terminals remain; `tests/unit/band4/test_band4_xp.py` 25/25 green;
goldens present. The `!xpimport` channel-scan front door stays a separate
honest BLOCKED boundary (not covered).

## 💡 Session idea

C2/C3 each ship a standing invariant test (`_ALLOWLIST` / `_KNOWN_ENSURE_ONLY`,
both now empty) that keeps the closed class unwritable. The backlog doc
now points at those tests as the durable proof-of-closure. Worth a
convention: when a hardening backlog item lands its own class-killer
invariant, cite the test in the DONE note (not just the PR) so a future
re-audit reads the live floor instead of re-deriving it — the two notes
here do exactly that.

## ⟲ Previous-session review

Reviewed the two closing sessions: the 2026-07-10 band-5 compensator-fixes
card (#105) and the 2026-07-17 ensure-only-registration-sweep card (#508).
Both were born-red, held only substrate-gate, and landed via the
server-side lander per CONSTITUTION. The #508 card's own "Session idea"
flagged that with `_KNOWN_ENSURE_ONLY` empty the burn-down became a pure
floor — this verification confirms that floor holds at HEAD `1bcc8e3` and
that the moderation parity flip strengthened C2 past what #105 shipped
(timeout now has no post-commit effect leg to strand). Handoff read clean;
no drift to reconcile.
