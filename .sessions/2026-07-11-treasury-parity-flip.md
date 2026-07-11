# 2026-07-11 — treasury parity flip (pending→ported)

> **Status:** `complete`

- **📊 Model:** sonnet-5 · high · parity flip

## Scope

Follow-up to the same session's precutover bug-fix PR (F-001/F-002/F-003 +
sweep): with capacity left, picked up the highest-tractability pending
subsystem toward cutover. `treasury` was already fully IMPLEMENTED
(`sb/domain/treasury/{store,ops,invariants,panels}.py`, 659 lines — a
band-3 sole-writer store, contribute/disburse K7 lanes, the pool⊄ledger
reconciliation invariant) but never verified/flipped against its goldens —
a much smaller, more tractable lift within this session's remaining budget
than porting a subsystem from zero.

## What shipped

Oracle: `menno420/superbot` `disbot/cogs/treasury_cog.py` `TreasuryView`;
goldens: `parity/goldens/treasury/` (`sweep_treasury` — the panel open,
`sweep_treasury_contribute` — the insufficient-funds guard byte). Both
diffed real against the existing declarative panel:

- **`session_lifecycle=True` + run-minted ids** — the shipped view was
  ctx-bound and timeout-based (view-local button decorators, no
  persistent custom_ids); the panel previously had no `session_lifecycle`
  declared, so its buttons carried persistent `treasury.hub.*`
  custom_ids and a `panel_anchors` bookkeeping row the golden's db_delta
  doesn't carry (the cleanup words-manager precedent: session_lifecycle +
  no overrides + no nav row → run-minted `<cid:N>` ids, zero anchor rows).
- **No nav row** — `navigation=NavigationSpec(show_help=False,
  show_home=False)`: the shipped view carried ONLY its own two buttons
  (the golden pins exactly one component row).
- **The gold `ECONOMY_COLOR` accent** (`style_token="gold"`, 15844367) —
  previously unset.
- **The literal footer** `'➕ Contribute · 🔄 Refresh'` and **both fields
  rendered inline** — both outside `FooterMode`'s none/subsystem/
  provenance vocabulary and the 2-tuple-fields-render-inline=False
  grammar default, so both ride a `renderer_override` (the cleanup-hub
  precedent: grammar render + two named adjustments only, everything else
  stays declared).
- **The extra "Disburse" field removed** — the shipped panel carries only
  "Treasury" + "Your wallet"; a third field describing `!treasury grant`
  was invented, not shipped.

One A-16 depth exemption needed (`table:guild_treasury`, class
`guard-only-capture`): the capture-world admin persona held 0 🪙, so the
only captured `!treasury contribute <amount>` invocation hit the
insufficient-funds guard before ever touching the store — no imported
golden corpus-wide carries the table (the `!treasury grant` disburse lane
is staff-tier, entirely outside the sweep's member/admin persona pair).
`tools/check_parity_depth.py --write-ratchet` minted the ratchet row
(`treasury: {events: 0, tables: ..., settings: 0}` — the splice-only
writer, byte-identical elsewhere).

## Evidence

- Both treasury goldens replay green in isolation
  (`_replay_corpus({'treasury'})`) and as part of the full corpus,
  rebased onto the fresh `main` after the sibling fix PR (#213) and an
  unrelated `starboard` flip both merged ahead of this one:
  `tools/run_golden_parity.py --gate` against a real local Postgres 18 →
  `gate: GREEN — all 266 golden(s) across 39 ported subsystem(s) replay
  clean` (zero denominator mismatches; this PR's own delta is +2 goldens
  / +1 ported subsystem — treasury's own two). `check_parity_depth.py`:
  `OK — 50 subsystems (39 ported), 467 goldens`.
- New unit tests (`tests/unit/band3/test_band3_treasury_inventory.py`):
  `test_treasury_hub_spec_shape_matches_the_golden` pins the declared spec
  (style_token, session_lifecycle, navigation, action shapes);
  `test_treasury_hub_renders_the_golden_bytes` drives the actual
  `renderer_override` and asserts the footer literal + both fields
  inline=True + exactly 2 fields (no "Disburse") + exactly one component
  row. Both verified red-then-green (fail against the pre-flip spec with
  `renderer_override=None` / the un-fixed field count, pass after).
- `manifest_compile.py --write` regenerated (confirmed: this diff's hash
  moves ONLY because of the treasury panel change — with the treasury
  files stashed out, recompiling reproduces the exact pre-session
  baseline hash byte-for-byte).
- `tests/unit/` — 1468 passed (2 net-new to this PR), 2 skipped. The full
  committed checker fleet + `bootstrap.py check --strict` green.

## 💡 Session idea

Several `pending` subsystems in `parity/parity.yml` may be in the SAME
shape treasury was: fully implemented, never verified — a `pending` row
signals "not yet at golden parity," not "not yet built." A cheap
pre-flight scan (`sb.domain.<name>` module exists + non-trivial line
count + its goldens already replay clean against current source) would
let a session pick the next flip target by tractability instead of by
re-deriving "is this actually a full build or just a verify?" from
scratch each time — worth a `tools/rank_pending_subsystems.py` if the
port keeps alternating between "build from zero" and "verify and flip"
work.

## ⟲ Previous-session review

This PR's own predecessor, in the same session: the precutover bug-fix PR
(F-001/F-002/F-003 + the sweep + the adversarial-review-caught GC-sweep/
solo_start races). What it did well: every fix shipped with a real
red-then-green regression test against a genuine Postgres instance, not a
mocked one — the strongest evidence bar available, and it's what let this
follow-up trust the shared `store.py`/`wager.py` surface was solid ground
to build on rather than re-verifying it. What it could have done better:
none of its three named bugs or its five adversarial-review findings
overlapped with the port/panel-rendering layer this PR touches, so there
was no direct carry-forward lesson to apply here — the two PRs are
genuinely orthogonal (money-mutation locking vs. panel-shape parity),
which is itself the reason they're correctly split into two PRs rather
than one.
