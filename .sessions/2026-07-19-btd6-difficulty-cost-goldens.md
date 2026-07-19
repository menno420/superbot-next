# Session — BTD6 difficulty-cost pricing math: pin the live rounding goldens

> **Status:** `in-progress`
>
> Born-red per `.sessions/README.md`: this card is the FIRST commit (holds the
> substrate added-card gate red); the test file lands next; the flip to
> `complete` is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · test writing

## Order

Self-initiated engineering round 3: land ONE genuinely-valuable, contained,
reversible improvement (high quality bar — real value, not churn), or report an
honest dry. HUNT (read-only first) probed the less-trodden surfaces called out
in the order: unclaimed domains, `sb/spec` grammar leaves, adapter edges. The
spec leaves examined (`cost`, `governance`, `setup`) were already covered; the
standout live gap was `sb/domain/btd6/difficulty_costs.py` — pure BTD6
tower/upgrade pricing math with a tricky exact-tie rounding rule and **zero
direct test coverage**, yet consumed by the AI BTD6 grounding surface.

## Scope

Test-only. Adds `tests/unit/band7/test_band7_btd6_difficulty_costs.py`. Zero
`sb/` source edited; no dependency change (pip-audit n/a).

## What the tests pin

`difficulty_costs.py` derives every-difficulty prices from the Medium price and
feeds three live consumers — `ai/tools.py` (the `all_difficulty_costs` grounding
tool answered to users), `paragon_math.py`, and `context.py` (BTD6 grounding
context). A silent regression in the multipliers or the rounding rule would ship
wrong in-game costs into the bot's BTD6 answers. The goldens pin what the code
REALLY does (verified in a REPL before writing):

1. **exact multipliers** — `all_difficulty_costs(100)` ==
   `{easy:85, medium:100, hard:110, impoppable:120}` (×0.85 / ×1.00 / ×1.08 /
   ×1.20); Medium is an exact passthrough (no rounding path).
2. **round-to-nearest-$5, ties resolve DOWN** — the load-bearing edge: medium=50
   Easy → 50×0.85 = 42.5 (an exact $5 tie) → **40**, not 45 (round-half-up would
   give 45). A non-tie probe (51 Easy → 43.35 → 45) pins ordinary nearest-5.
3. **mode aliases + fail-loud** — `''` / `normal` / `standard` → `medium`;
   `chimps` prices as `hard`; `impoppable` canonical; an unknown label RAISES
   `ValueError` (never silently Medium — the module's explicit contract).
4. **shape** — `DIFFICULTIES` order and `all_difficulty_costs` key order.

## Verification

- `python3 -m pytest -q tests/unit/band7/test_band7_btd6_difficulty_costs.py`
  → [[fill: tail + count]]
- Full `python3 -m pytest -q --ignore=examples` → [[fill: tail + count]]
- Guards clean (`check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`): [[fill]]
- `python3 bootstrap.py check` → [[fill: exit 0, card complete]]
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

[[fill]]

## ⟲ Previous-session review

[[fill: previous-session review]]
