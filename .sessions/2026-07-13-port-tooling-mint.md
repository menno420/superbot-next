# 2026-07-13 — tools: mint_golden — codify the D-0073 golden mint

> **Status:** `in-progress`

- **📊 Model:** fable-5 · port-tooling lane (claim
  `control/claims/port-tooling-mint-orphan.md`, mint half; branch
  `claude/port-tooling` off main @ 5dac6ce)

## Scope

The D-0073 golden-minting procedure has been re-derived by hand four
times (D-0073 btd6 modal mints, D-0075 kernel band, D-0079 creature
battle, the 2026-07-13 fishing/cleanup mints). This slice ships it as a
tool, INERT in this PR — no golden is minted, no pin value moves, the
corpus stays 494:

1. **`tools/mint_golden.py`** — `python3 tools/mint_golden.py <case-id>
   [--write] [--force]`. Resolves the case (typed
   `parity.cases.CURATED_CASES` first, then golden-document
   reconstruction via `sb.adapters.parity.cases.reconstruct_case` for
   re-mints), captures via `sb/adapters/parity/runner.capture_case`,
   applies the ruled dispositions (`sb.adapters.parity.dispositions.
   apply_dispositions` — imported, not reimplemented; its built-in
   kernel-band skip IS the D-0075 inversion: `subsystem: kernel` docs
   keep the spine), double-captures kernel cases across two independent
   harness boots and byte-compares the prepared docs, writes
   `parity/goldens/<subsystem>/<case>.json` (corpus serialization:
   `indent=1, sort_keys=True, ensure_ascii=False` + trailing newline),
   recomputes the corpus FROM DISK, and rewrites the mutable count pins.
   Refuses to overwrite an existing golden without `--force`; default is
   dry-run (capture + print planned changes, write nothing); prints the
   manual oracle-verification checklist (procedure step b — the tool
   reminds, never fakes it). Goldens are never hand-edited (#193 /
   parity/README.md integrity rule).
2. **Pin rewriting as pure text functions** (`rewrite_parity_yml_pins` /
   `rewrite_replay_adapter_pins` / `rewrite_depth_test_pins`), each
   anchored exactly-once with the import pin guarded untouched:
   `parity/parity.yml` `minted_goldens:` + the `imported + minted −
   retired = N` arithmetic comment; `tests/unit/parity_adapter/
   test_replay_adapter.py` `assert golden_count == N` + the docstring
   `(N/N)`; `tests/unit/parity_gate/test_check_parity_depth.py`
   `assert len(goldens) == N`, `assert "N goldens" in out`, and
   `assert source["minted_goldens"] == N`. The IMPORT pin
   (`source.goldens: 465`, test_check_parity_depth.py:72) is asserted
   unchanged, never rewritten.
3. **`tests/unit/parity_gate/test_mint_golden.py`** — DB-free external
   pins: pin rewriting on copies of the real files (mutable sites move,
   import pin byte-stable), exactly-once anchor failure, count
   arithmetic, refuse-overwrite, kernel vs non-kernel disposition
   routing, case resolution, and serialization matching the on-disk
   corpus byte-form.

Guard recipe (carried, not built here): a count-pin-coherence check —
`compute_counts` + the anchor parsers in `tools/mint_golden.py` already
read every mutable pin; asserting they all agree with the on-disk corpus
inside `tests/unit/parity_gate/test_mint_golden.py` (or a
`tools/check_*` twin) would make a hand-desynced pin a same-PR red.

## Verification

Pending — filled at close-out.

## 💡 Session idea

The corpus now holds two on-disk flavors of minted golden: the early
D-0073/D-0075 mints stored the DISPOSED doc (btd6_strategy_form_submit
carries no spine tables), while the recent mints stored the RAW capture
(creature_battle_accept.json and cleanup_policies_open.json carry
audit_log/event_outbox/command.dispatched — the symmetric replay-time
drop makes both replay green). Equivalent under the diff, but a
one-time normalization PR (re-serialize every minted domain golden
through `apply_dispositions`, reviewed under the D-0019 corpus-change
terms) would leave ONE byte-form and let a future
`tools/check_parity_depth.py` rule assert "no disposition-dropped
surface stored in a non-kernel minted golden" — closing the flavor
drift this tool otherwise freezes in place.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-role-orphan-refs-trueup.md` @ 38b7af4,
PR #412.) Directly load-bearing for this slice: its harvested
COUNT-PIN CORRECTION ("five sites, not four") is the exact roster this
tool mechanizes, and re-verifying it at HEAD found the honest split —
four mutable sites plus the guarded import pin at
test_check_parity_depth.py:72, with a sixth mutable anchor the prose
missed (`assert source["minted_goldens"] == 32`, same file :85) that
any real mint must also move; the tool rewrites it and this card
ledgers it. Its verification posture (Postgres-DOWN pytest 2821/15, the
born-red strict hold, the pre-existing mining-write-parity claims
advisory) reproduced here unchanged. Its 💡 (derived-consistency checks
over prose enumerations) is half-landed by this slice: the pins are now
machine-rewritten from disk truth, though the standing coherence GUARD
it wanted remains a follow-up (recipe above).
