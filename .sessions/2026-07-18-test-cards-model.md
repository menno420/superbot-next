# 2026-07-18 — cover error/edge paths of the pure casino card model

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · test writing · additive card-model edge/error coverage (born-red, holds substrate-gate)

## Scope

`sb/domain/casino/cards.py` is the shared, pure, stdlib-only, Discord-free
card model (band 6): a frozen ace-high `Card`, an ordered `Suit` enum, and
the `card()`/`parse_card()`/`make_deck()` builders. Its **happy paths** are
exercised by `tests/unit/band6/test_band6_deathmatch_casino.py`
(`test_cards_and_hand_evaluator` — `card()` + `make_deck(shuffle=False)`),
but every **ERROR / edge branch** is unverified:

- `parse_card` — the three refusal branches: too-short code
  (`ValueError("card code too short: …")`), unknown rank
  (`ValueError("unknown rank in card code: …")`), and unknown suit letter
  (raised through `Suit.from_letter`).
- `Suit.from_letter` — unknown letter raises
  `ValueError("unknown suit letter: …")`; case-insensitive accept.
- `Card.__post_init__` — a rank outside 2..14 raises
  `ValueError("rank must be 2..14, got …")`.
- Ace-high ordering / sort — `Card`'s `order=True` sorts by `rank` then
  `suit` (Suit's declared order S<H<D<C); pin the comparison + `sorted()`.
- `.code` / `str()` round-trip — `parse_card(c.code) == c` across a full
  representative set, plus the `"T"`→ten and lowercase-suit aliases.

This slice is deliberately CONTAINED and purely additive: NO product code
changes (a new test file only ⇒ cannot regress anything). It stays locally
verifiable — the module is stdlib-only, no DB, no bot boot, no golden parity.

## Deliver — pin each refusal + the ordering / round-trip contract

New file, matching the band-6 test home
(`tests/unit/band6/test_band6_deathmatch_casino.py` style):

- `tests/unit/band6/test_cards_model.py` — asserts each `parse_card`
  refusal by exact exception type + message (`pytest.raises(..., match=…)`),
  the `Suit.from_letter` unknown-letter refusal and case-fold accept, the
  `Card.__post_init__` out-of-range refusal (below 2, above 14, and 0),
  the ace-high `<`/`sorted()` ordering with the suit tiebreak, and the
  `parse_card(c.code) == c` round-trip across every rank×suit plus the
  `"T"`/lowercase aliases.

## Verification

- `pytest tests/unit/band6/test_cards_model.py
  tests/unit/band6/test_band6_deathmatch_casino.py -q` → green (verbatim
  summary in the PR body). Full `tests/unit/` NOT run here — this
  container has a pre-existing `yaml`-module gap + pytest-randomly ordering
  pollution that makes the whole-suite run a non-signal; the CI named-gates
  carry the authoritative sweep.

## 💡 Session idea

The band-6 casino `evaluate.py` hand-ranker sits right next to this model
and has the same shape: rich happy-path coverage in
`test_cards_and_hand_evaluator`, but its tie-break key construction and any
malformed-input guards are worth the same one-file edge pin next. Closing
the card model's refusal branches here establishes the pattern for the
evaluator's boundary cases.

## ⟲ Previous-session review

Reviewed the predecessor `.sessions/2026-07-18-test-ast-checker-tools.md`
(PR #518), an additive test slice that pinned the two stdlib-`ast` CI
checker tools (`check_config_usage`, `check_symbol_shadowing`) with new
`tests/unit/tools/` files and NO product change — same born-red,
holds-substrate-gate posture as this card. It confirms the current
hardening rhythm: small, contained, new-test-only slices that pin an
unverified behavior a gate depends on. This slice carries that rhythm into
the pure domain layer — from the CI checkers down to the card model that
every casino game reuses.
