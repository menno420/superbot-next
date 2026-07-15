# Claim: band-5 partial-honesty tail (compensated PARTIAL echoes the withdrawn success copy + proof `<#0>` acks)

- branch: `band5-partial-honesty`
- scope: `sb/kernel/workflow/engine.py` (speaking-compensator copy seam),
  `sb/domain/proof_channel/{ops,handlers}.py`, `sb/domain/role/ops.py`,
  `tests/unit/band5/test_band5_partial_honesty.py`, D-0091.
- why unclaimed elsewhere: the 3 band-5 live-drive bugs landed in #111;
  this is the remainder that ledger row left implicit — the D-0062 leg
  acks made `result.user_message` carry success copy that a compensated
  PARTIAL still renders, and the proof success acks read a `"record"`
  after-key that never existed.
- session: .sessions/2026-07-15-band5-partial-honesty.md
