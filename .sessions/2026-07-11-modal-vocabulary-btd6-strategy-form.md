# 2026-07-11 — replay modal vocabulary + btd6 strategy-form goldens (D-0073)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

Execute the D-0063/D-0066 deletion clause (the D-0066-named successor
slice): grow the golden corpus's input vocabulary with the `modal` step
kind, ship the btd6 strategy-submit form itself (the shipped
StrategySubmitModal as a live G-10 form), mint the first goldens that
CARRY a wire-type-5 input record, and delete the `modal-driven` class's
birth exemption row (`btd6 → table:btd6_strategies`) with the ratchet
climb it promised. Oracle: menno420/superbot
`disbot/views/btd6/strategy_submit.py` + `services/btd6_strategy_mutation.py`
+ `cogs/btd6/_unified.py strat_submit_slash`, reconstructed via
search_code fragments @`8214200a` (full-file oracle reads stay denied).
Decision record: docs/decisions.md **D-0073**.

## What shipped

1. **Corpus schema growth (D-0019 reviewed change)** — golden step
   inputs grow `kind: "modal"` (`custom_id` = static G-10 modal_id root,
   `fields` = submitted values, optional `target_message`) across the
   one vocabulary chain: `Step` (parity/harness/cases.py),
   `_describe_step` (parity/harness/runner.py), `_step_from_input`
   (sb/adapters/parity/cases.py — `<`-normalized ids stay
   non-reconstructable, the click rule) and the new-bot `_drive`
   (sb/adapters/parity/runner.py → `Harness.modal_submit`). The old-bot
   driver deliberately does NOT grow the kind (it drives disbot, absent
   here).
2. **The form** — `btd6.strategy_form`, the shipped StrategySubmitModal
   field-for-field (title 100 / summary paragraph 500 / Map 80 / Mode 40
   / Hero 40 with the shipped placeholders), declared on the new session
   page `btd6.strategy_submit` (sb/domain/btd6/panels.py; run-minted
   ids, zero sim-gate churn — trap 12d; compat pin grew exactly the
   modal root). The submit handler `btd6.strategy_form_submit`
   (oracle_surface.py) is on_submit byte-for-byte: guild guard, strip /
   strip-or-None, display-name snapshot, ONE audited write through the
   EXISTING `btd6.submit_strategy` K7 op, the shipped
   ``✅ Submitted as strategy `#N` (`submitted`). Staff can review with
   `!btd6 pending`.`` / ``❌ title and summary are required`` /
   unexpected-error followups. Ledgered deviation (D-0073): the shipped
   slash-opens-modal ingress needs a CommandSpec modal facet (named
   successor); the declaring surface is the D-0054/D-0066
   intermediating page — the golden-pinned prefix pointer byte and the
   empty slash-drop golden stay byte-identical, no command row changed.
3. **`PanelActionSpec.reply_visibility`** (A-2 schema-growth ledger,
   ≥2 consumers) — the shipped submit was `safe_defer(ephemeral=True)`
   but a user-tier action's lane default is PUBLIC; the CommandSpec
   Group-1 field-3 twin joins the panels grammar ([S], resolve() already
   duck-reads it — zero engine change), consumed by the btd6 action and
   the four ai modal-issuing actions (their oracle twins all followed up
   ephemeral; no golden pins those clicks — fidelity restored).
4. **The first MINTED goldens** —
   `goldens/btd6/btd6_strategy_form_submit{,_minimal}.json`: captured by
   the new bot's own `capture_case`, kernel-spine surfaces stripped
   (audit_log / event_outbox / command.dispatched — old-bot captures
   never carry them and the kernel-surface-drift disposition drops them
   at diff time; leaving them would enshrine NEW-code audit bytes),
   every user-facing byte verified against the oracle reconstruction
   (flags-64 type-5 + flags-64 followup + ack copy + row values).
   parity.yml `source` gains `minted_goldens: 2` (import pin stays 465);
   corpus 467 = 465 imported + 2 minted (count pins updated in
   test_replay_adapter + test_check_parity_depth).
5. **The deletion clause executed (deliberate LAST commit)** —
   `btd6 → table:btd6_strategies` deleted from depth.exemptions (the
   insert is now golden-covered); ratchet `btd6: tables 3 → 4`. The
   `modal-driven` CLASS stays (D-0070's six ai rows still ride it). Also
   fixed in-pass: the #187-parked `seeded-catalog` doc-comment typo
   (migration-0029 → migration-0030).

Ladder (serial, real Postgres): units 1411 passed / 2 skipped; gate
**220/220 GREEN** across 37 ported (218 + the 2 minted); report
467/467 replayable, **258/467 green** (256 + 2); depth checker OK
(49 subsystems, 467 goldens); manifest_compile / namespace /
schema-growth / amendments / sim-gate / compat / egress / no-skip /
config-usage / metric-cardinality / symbol-shadowing / intent-survival /
slash-cap / migrations all clean.

## Notes

- **Trap 24 again, twice**: the oracle default branch moved
  a409d9b7 → **8214200a** during this session. The reconstruction rides
  the head; the fragment set for strategy_submit.py was internally
  consistent and the golden-pinned pointer/guard bytes matched, but the
  minted bytes pin the reconstructed head shape (caveat in D-0073 and in
  the goldens' own notes fields).
- **Pre-existing latent bug, ledgered not touched**:
  sb/domain/btd6/service.py `_run_op` reads `result.ok` and
  `result.after["message"]` FLAT — `WorkflowResult` has no `.ok`, and
  the engine rolls `after` up by step target name. The path is only
  reachable via the argful `!btd6strat submit`/review lanes no golden
  drives (its sweep golden pins the bare-invocation pointer byte, and
  the case is `_unmapped`/pending). Guard recipe: fix
  `_run_op.route` in sb/domain/btd6/service.py to
  `result.outcome == SUCCESS` + rollup reads keyed by leg target name
  (`after["record"]`-style keys are wrong too — see
  oracle_surface.strategy_form_submit for the correct shape), then pin
  with a test driving `!btd6strat submit t | s` through the harness.
- The minted goldens do NOT pin the oracle's 041 `btd6_strategy_audit`
  row: this schema epoch folds transitions into the K7 central audit
  (D-0046), a dropped kernel surface.
- The mint procedure is reproducible from D-0073 (capture_case +
  kernel-drift strip + oracle byte verification); the one-off script was
  deliberately not committed — the committed artifacts are the goldens,
  the vocabulary chain, and the record.

## 💡 Session idea

`command.dispatched` and the audit_log/event_outbox rows are captured
by the new bot on EVERY case but stripped/dropped everywhere — the
kernel section of parity.yml is still `status: pending` with no golden
home. A tiny K-band corpus (one minted golden per kernel surface, the
D-0073 mint procedure re-run with the strip INVERTED) would flip the
kernel coverage home from pending to real without touching any domain
golden.

## ⟲ Previous-session review

The D-0072 card's slice-record pattern (record + parked-terms + trap-24
caveat) transferred directly — this slice's record practically wrote
itself from D-0066's deletion clause. What it under-delivered: nothing
in the playbook warned that a MINTED golden inverts the usual honesty
problem — instead of "the corpus pins what new code must reproduce",
the risk becomes "new code pins itself into the corpus". The
kernel-surface strip + oracle-byte verification is the counter-recipe
(now in D-0073); playbook entry appended this session.
