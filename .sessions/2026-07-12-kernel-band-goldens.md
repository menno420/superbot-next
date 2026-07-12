# 2026-07-12 — kernel-band golden set + the kernel coverage home flips (D-0075)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

Execute the D-0073 named 💡 follow-up (the #194 session card's own
words: "the D-0073 mint procedure re-run with the strip INVERTED would
flip the kernel coverage home from pending to real"): mint the first
KERNEL-BAND goldens, give the A-16 clause-3 kernel coverage home its
golden dir + checker + gate lanes, and flip parity.yml
`kernel.status: pending → ported`. Decision record: docs/decisions.md
**D-0075**. No oracle reconstruction in this slice — kernel-band
goldens deliberately pin the NEW kernel's spine contract (there is no
oracle for the spine; the old bot never had one).

## Why this slice exists

The two honesty rules that made domain parity work each cast the same
shadow: the D-0073 mint strip keeps new-code audit bytes OUT of domain
goldens, and the flag-13 kernel-surface-drift disposition drops the
spine from every imported-golden diff. Together they made kernel-only
regressions invisible everywhere — a changed audit verb, a lost
event_outbox row, or a lost command.dispatched event could not red ANY
gate. The flag-13 record's own sentence ("their coverage obligation
stays real: it lives in the parity.yml `kernel` section") was
unenforced; the checker even carried pre-built `!= "kernel"` escapes
for kernel exemption/ratchet rows that nothing could mint.

## What shipped

1. **Four kernel-band goldens** (`parity/goldens/kernel/`,
   `subsystem: kernel`, minted by `capture_case` with the strip
   INVERTED — double-captured across two independent harness boots,
   byte-identical, then committed):
   - `kernel.audited_modal_submit` — the D-0073 btd6.submit_strategy
     K7 op behind the modal: the audit_log row's
     mutation_type/target/leg-rollup bytes + its audit.action_recorded
     outbox row + the surface=modal dispatch trace.
   - `kernel.audited_prefix_command` — `!createrole test` (admin): the
     xp.award audit_log+outbox pair, the role lane's BUS
     audit.action_recorded (`role_create`) + role.lifecycle_changed,
     the surface=prefix trace with authority_ref=administrator.
   - `kernel.denied_prefix_command` — same command as member: the
     tier-lane deny copy with NO dispatch trace (pre-ack denials return
     before the trace skeleton — resolve.py `_deny`) and no spine
     surfaces beyond the message-driven xp.award pair.
   - `kernel.slash_dispatch_trace` — `/economy`: the surface=slash
     trace over the sanctioned UN-audited idempotent ensure write
     (playbook 14e) — the spine stays silent on non-op writes.
   Tripwire proof (in-session): a changed audit verb, a deleted outbox
   row, and a dropped dispatch event each produce exactly one red diff
   line on the kernel band; the identical audit-verb drift on a
   domain-band doc stays disposition-inert.
2. **The disposition carve-out** — `apply_dispositions` skips the
   kernel-surface-drift drop for `subsystem == "kernel"` docs,
   symmetrically (a fresh capture of a kernel case carries the same
   subsystem); the other two ruled classes still apply. This is
   band-scoped mechanism, NOT a re-encoding of the ORDER-009 ruled
   classes — domain-band behavior is byte-identical.
3. **The checker home** — check_parity_depth treats kernel as a
   pseudo-subsystem on the same four rules: goldens/kernel/ legal iff
   the `kernel:` section exists (never a subsystems row), R2-kernel
   over the kernel section's OWN events/tables lists, R3
   mandatory/one-way `kernel` ratchet row (--write-ratchet mints it),
   R4 one-way door. run_golden_parity gains `_statuses_with_kernel` —
   goldens/kernel/ is required-green in the gate when
   `kernel.status: ported`, denominator-checked.
4. **The floor** — covered: audit_log, event_outbox, both kernel
   events. The seven never-covered kernel tables take
   depth.exemptions.kernel rows under EXISTING classes (no vocabulary
   growth): idempotency_keys ops-not-behavior (no domain op rides
   DURABLE_ONCE this epoch — verified by grep, every CompoundOpSpec is
   NATURAL_KEY), sb_due_queue/sb_quarantine/sb_invariant_sweep_log
   time-driven, sb_drafts/sb_credential_rotation ops-not-behavior,
   ai_decision_audit env-keyed-integration (NL unarmed; OWNER-ACTION 5).
5. **The flip (deliberate LAST commit)** — `kernel.status: ported` +
   ratchet `kernel: {events: 4, tables: 5, settings: 0}` (raw
   covered-side, trap 14d); corpus 471 = 465 imported + 6 minted
   (`minted_goldens: 6`); count pins updated.

Ladder (serial, real Postgres): full pytest 1575 passed / 2 skipped;
gate **341/341 GREEN** across 43 ported (337 + the 4 kernel-band);
report 471/471 replayable, 347/471 green; check_parity_depth OK
(50 subsystems, 42 ported, kernel ported, 471 goldens); manifest_compile
/ amendments / compat / config-usage / egress / escape-hatches /
metric-cardinality / money-race / namespace / no-skip / schema-growth /
sim-gate / symbol-shadowing / lockfile-fresh all OK. Zero manifest /
sim-gate / compat churn — no commands, panels, tables, or events
changed.

## Notes

- **Framing, deliberate**: kernel-band goldens are regression
  tripwires, not parity evidence — a DELIBERATE kernel contract change
  re-mints the affected kernel goldens in the same PR with the diff
  explained (parity/README.md integrity rule); an accidental one goes
  red in the gate. D-0075 records this and the flag-13 disposition
  record's clause-1 sentence confirms the coverage-home framing (no
  divergence to ledger).
- The `kernel.denied_prefix_command` golden pins that pre-ack denials
  emit NO command.dispatched trace — current contract, verified at
  resolve.py `_deny`. If deny-tracing is ever added deliberately, that
  golden re-mints with the diff explained.
- The mint script is one-off per the D-0073 procedure (committed
  artifacts = goldens + machinery + record); double-capture determinism
  was checked across two full harness boots before writing.
- 💡 Follow-up (small): the report leg's per-dir status column reads
  the same `_statuses_with_kernel` map, so kernel shows `[ported]` —
  but `check_parity_depth`'s OK line now also names the kernel status,
  which the heartbeat can quote directly.

## ⟲ Previous-session review

The D-0073 card's 💡 follow-up section did exactly what it promised —
this slice's scope was copy-paste executable from it, zero re-derivation.
What it under-specified: it said "one minted golden per kernel surface",
but the honest shape turned out to be per OP-PATH CLASS (modal/prefix/
deny/slash), with the never-writable kernel tables going to exemption
rows instead of dead mints — the ticket-flip lesson (trap 15b: don't
mint dead tables just to exempt them) transferred to the kernel band
unchanged.
