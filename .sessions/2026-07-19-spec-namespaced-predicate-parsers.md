# Session — spec grammar: cover the namespaced-predicate parsers

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`): the first commit was this card alone (born-red, held
> the substrate-gate); the test landed in the second commit; this flip is the
> last.

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 6) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Fresh-territory hunt on
the `sb/spec` grammar leaves (stdlib-only, easy) found the two namespaced-
predicate parsers in `sb/spec/refs.py` — `is_namespaced_predicate` and
`parse_namespaced_predicate` — have NO dedicated test, yet carry the silent-
failure hazards the round targets: string parsing with tie-break/empty-value
edges that never raise on a wrong *answer* (only on malformed input).

## Scope

Test-only. Added `tests/unit/spec/test_refs_predicates.py`. Zero `sb/` source
edited; no dependency change (pip-audit n/a). No claimed domain touched — this is
a kernel/spec grammar leaf.

## What the tests pin

Behavior of the two parsers, each assertion verified against a live run of the
real functions before being committed:

1. **`is_namespaced_predicate` — the head whitelist + the empty-string short-
   circuit.** `""` → `True` (the constant-true predicate); each of the four
   heads (`setting`/`binding`/`capability`/`flag`) with a key → `True`; an
   unknown head → `False`; no colon → `False`; a leading colon (`":foo"`, empty
   head) → `False`; head match is **case-sensitive** (`"Setting:foo"` → `False`).
2. **The `is_namespaced_predicate` / `parse` empty-key asymmetry.** The sharp
   edge: `is_namespaced_predicate("setting:")` returns `True` (sep present, head
   valid) but `parse_namespaced_predicate("setting:")` **raises** `ValueError`
   (empty key). The two functions deliberately disagree on the empty-key case —
   pinned so a refactor that "aligns" them silently doesn't change which strings
   reach the parser (the caller in `sb/kernel/interaction/predicates.py` only
   parses AFTER `is_namespaced_predicate` gates True, and does NOT catch
   `ValueError`).
3. **`parse_namespaced_predicate` — the value tie-break.** The load-bearing
   distinction: no `=` sign → value `None` (truthiness-only check downstream);
   an `=` with nothing after it (`"setting:foo="`) → value `""` (an *empty
   string*, not `None` — a real compare-to-empty semantic). A `.split("=")` or
   `if "=" in rest` refactor would collapse this. Also: first-`=` split preserves
   later `=` in the value (`"foo=bar=baz"` → value `"bar=baz"`); the dotted key
   (`"a.b.c"`) is returned whole for the downstream `subsystem.name` partition.
4. **`parse_namespaced_predicate` — the raise paths.** Empty string, bare head
   (no colon), unknown head, empty key (`"setting:"`), and empty key before `=`
   (`"setting:=bar"`) each raise `ValueError`; the constant-true `""` is the
   caller's short-circuit and is NOT silently accepted by the parser.

## Verification

- `python3 -m pytest -q tests/unit/spec/test_refs_predicates.py` →
  **25 passed** in 0.04s.
- Full `python3 -m pytest -q --ignore=examples` (Postgres started + discord
  present) → **3674 passed, 2 skipped, 1 warning** in 110s. The 2 skips are
  pre-existing/unrelated; the 1 warning is the pre-existing `discord/player.py`
  `audioop` DeprecationWarning (stdlib, unrelated). The +25 delta is exactly
  this file — no other test moved.
- Guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

The gate/parser empty-key asymmetry (test 2) is currently latent-safe only
because manifest predicate strings are author-written and validated upstream —
but `evaluate()` in `sb/kernel/interaction/predicates.py` catches only
`LookupError`, not the `ValueError` that `parse_namespaced_predicate("setting:")`
raises after `is_namespaced_predicate` waves it through. A hand-authored or
future-generated `"setting:"` (trailing-colon typo) would therefore surface as
an uncaught `ValueError` at render/gate time rather than a fail-closed `False`.
Worth a one-line decision: either tighten `is_namespaced_predicate` to also
reject the empty key (making the two agree), or widen the `except` in `evaluate`
to `(LookupError, ValueError)` so a malformed predicate fails closed like every
other unreadable one. Guard recipe: anchor on `is_namespaced_predicate` +
`parse_namespaced_predicate` in `sb/spec/refs.py` and the `except LookupError`
in `sb/kernel/interaction/predicates.py::evaluate`; a behavioral pin would be an
`evaluate(PredicateRef("setting:"), ctx)` case asserting `False` (fail-closed)
once the posture is chosen. This test file pins TODAY's behavior (parse raises),
so whichever way the decision lands, the change to this test is the signal.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-mining-rewards-rolls.md` (`complete`, same
`opus-4.8 · high · test writing` class). That card's convention carried here
verbatim: read-only HUNT to prove the exact gap is genuinely uncovered before
writing (confirmed neither `parse_namespaced_predicate` nor
`is_namespaced_predicate` appears in any test), a born-red card as the sole
first commit holding the substrate-gate, the test in a second commit, and a
verification section that re-runs the exact commands and records tails/counts.
One concrete carry heeded: that card's *honesty seam* discipline — do NOT assert
behavior the shipped code does not produce (it declined to claim a legacy-bonus
amount difference that rounds to a no-op). Applied here to the `is_namespaced`/
`parse` asymmetry: rather than assert the two "should agree", the tests pin that
they deliberately DISAGREE on the empty-key edge (gate True, parse raises) — the
real shipped behavior — and the divergence is routed to the 💡 idea as a posture
question, not silently "fixed". Where this slice diverges: mining was
game-economy loot math (rounding/clamp); this is a kernel/spec grammar leaf
gating every `enabled_when`/`visible_when` predicate — lower blast radius per
call but on the hotter path, and the value tie-break (`""` vs `None`) is the
assertion that earns its keep, since a `.split("=")` refactor would silently
flip a compare-to-empty into a truthiness check across every guild's gates.
