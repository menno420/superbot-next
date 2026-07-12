# 2026-07-12 — CommandSpec MODAL facet + the btd6 slash-declaration parity ruling (D-0076)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

Execute the #194 session card's named follow-up ("the shipped
slash-opens-modal ingress needs a CommandSpec modal facet — a Group-1
grammar amendment is the named successor", D-0073) — the last kernel-lane
item on the band-7 remaining map: grow the command grammar so a
CommandSpec can declare "this command opens modal X" (the shipped
`send_modal`-as-initial-response app-command ingress, ORACLE
`disbot/cogs/btd6/_unified.py strat_submit_slash`), and wire the btd6
strategy-form slash ingress through it **exactly as far as parity
allows**. Decision record: docs/decisions.md **D-0076**.

## The parity verdict FIRST (the slice's load-bearing call)

The oracle's ONLY slash-opens-modal ingress is `/btd6 strat submit`
(corpus-wide send_modal survey: every other call site is a button/select
callback — search_code @`1ecc2113`, the default branch having moved AGAIN
from `2c7d2de7` mid-wave, trap 24, head ledgered in D-0076). Its golden,
`goldens/btd6/sweep_slash_btd6_strat_submit`, pins ZERO calls / ZERO
db_delta — green only by the #151 unregistered-slash drop rule, one of
the #218 re-home's 30 structurally-empty `sweep_slash_btd6_*` pins (the
standing trap-17 constraint). Declaring the row registers the name, the
sweep dispatches, and `ParityResponder.open_modal` records a wire type-9
call — a red diff on a PORTED row the gate requires green. Reproducing
the pinned silence while declaring is a contradiction (the silence IS
the unregistered state), so:

**The `/btd6 strat submit` declaration is BLOCKED-BY-GOLDENS**
(`sweep_slash_btd6_strat_submit` directly; the trap-17 class of 30
`sweep_slash_btd6_*` pins generally — same terms as `/setup depth`,
playbook 17). Unblocking needs a D-0019 ruled corpus change (re-capture
or re-rule the empty slash sweeps), NOT a declaration. The D-0054/D-0066
intermediating page stays the form's declaring surface; the golden-pinned
prefix pointer byte and the empty slash golden stay byte-identical.

## What shipped (the facet, engine-complete, zero manifest consumers)

1. **Grammar** — `CommandSpec.modal: ModalSpec | None` ([S],
   sb/spec/commands.py; the PanelActionSpec.modal twin on the §2.2
   facet; A-2 ledger entry `CommandSpec.modal`, ≥2 consumers, the
   kernel-reader precedent). The #194 pattern exactly: additive field,
   zero behavior for non-consumers.
2. **Engine: UNCHANGED.** resolve()'s ACK boundary already duck-reads
   `defer_mode`/`modal` off the target spec — the G-10 open-terminal,
   (form, user, origin-message) stash, and submit-re-entry branches are
   spec-type-blind. Verified by tests, not assumed.
3. **The submit re-entry index rows** — `(modal_id, Surface.MODAL) →
   the declaring CommandSpec` in BOTH dispatch indexes
   (sb/app/build_runtime.py `build_live_index` +
   sb/adapters/parity/boot.py `_build_index`); `request_from_modal`
   already tries that key BEFORE the panel static-table fallthrough.
4. **`modal_ingress` compile fences** (tools/manifest_compile.py
   `_p6_semantic`, duck-typed): defer_mode==MODAL ⇔ modal present;
   kind==slash ONLY (a prefix message has no interaction response
   slot); route must be HandlerRef/WorkflowRef (the submit dispatches
   the command's own route); the `_check_modal` body fences (1..5
   fields, unique field_ids, non-empty modal_id).
5. **Tests** (all DB-free) —
   tests/unit/interaction/test_command_modal_facet.py (open terminal:
   type-9 + no dispatch + no defer-ack; stash/restore round-trip;
   submit re-entry dispatches the route with fields under the declared
   visibility; both indexes' MODAL rows; adapter-level `dispatch_modal`
   resolving with NO panel binding) +
   tests/unit/compiler/test_manifest_compile.py (each fence red, good
   shape green).
6. **Records** — D-0076; the btd6 panels.py deviation note re-pointed
   (facet exists, declaration golden-blocked, with the golden named);
   schema-growth ledger entry names the golden-blocked first manifest
   consumer explicitly; manifest.snapshot.json regenerated (field_roles
   + `modal: null` on every command row — the #194 mechanical diff).

ZERO new commands/panels/events/tables/settings · compat pin
byte-stable · sim-gate zero lock churn · ratchet untouched ·
compensator allowlist EMPTY (no ops) · no new exemption or disposition
classes.

## Evidence (full ladder, serial, real Postgres — run TWICE)

- At the #229 base (59e2e22): gate GREEN 342/342 across 44 ported;
  report 348/471 green, 471/471 replayable — byte-identical to the
  pre-slice baseline; full pytest 1586 passed / 2 skipped.
- Re-run at the branch head after forward-merging origin/main
  (95b6fda — #230 games flip + #231 wrap-up landed mid-slice;
  manifest.snapshot.json resolved by `manifest_compile --write`,
  telemetry keep-both): gate **GREEN — 346/346 across 45 ported**;
  check_parity_depth OK — 50 subsystems (44 ported), kernel ported,
  471 goldens; report **352/471 green, 471/471 replayable** (the +4 are
  #230's flips — this slice moves nothing); full pytest
  **1591 passed / 2 skipped**.
- named gates all clean: schema-growth, namespace, compat (pin
  byte-stable), amendments, sim-gate, no-skip, escape-hatches,
  symbol-shadowing, intent-survival, slash-cap, config-usage,
  metric-cardinality, egress, migrations, lockfile-fresh.

## 💡 Session idea

The #218 card's invariant-test idea is now one notch sharper: "for
every golden whose steps carry a `slash` input and ZERO calls, assert
the name is NOT in the compiled slash registry" would make the D-0076
blocked-by-goldens ruling a one-line CI red instead of a decision-record
sentence — and the facet's first future consumer would trip it exactly
when it should.

## ⟲ Previous-session review

The #228 kernel-band slice (merge 01d49688, D-0075) executed its
predecessor's 💡 idea verbatim and its card made the "why this slice
exists" section carry the two-rules-one-shadow argument — that structure
transferred here as "the parity verdict FIRST". What it could have done
better: its remaining-map entry for THIS slice ("CommandSpec modal facet
(slash-opens-modal ingress)") didn't carry the one-line shape probe the
#218 card asked successor maps to carry — the 30-empty-pins constraint
was discoverable only by re-reading the #218 card. This card names the
blocker in its own title line so the successor map stays self-pricing.
