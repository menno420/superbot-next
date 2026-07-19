# Session — spec grammar: cover the namespaced-predicate parsers

> **Status:** `in-progress`
>
> Born-red: this card is the session's FIRST commit (per `.sessions/README.md`),
> committed alone to hold the substrate-gate while in-flight. Flipped to
> `complete` as the deliberate LAST commit once the close-out is written.

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
  **[[fill: N]] passed**.
- Full `python3 -m pytest -q --ignore=examples` → **[[fill: tail + count]]**.
- Guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **[[fill:]]**.
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

[[fill: one concrete idea surfaced while writing]]

## ⟲ Review

### previous-session review

[[fill: byte-form review of the predecessor card]]
