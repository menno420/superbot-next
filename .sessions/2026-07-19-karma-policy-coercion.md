# Session — karma policy: cover load_policy's stored-value coercion + fallback

> **Status:** `in-progress`
>
> Born-red: this card is the session's FIRST commit (it alone holds the
> substrate-gate). The test lands in the second commit; the flip to
> `complete` is the deliberate LAST step once the close-out is written.

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 8) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Fresh-territory hunt on
unclaimed domain pure-derivation found `sb/domain/karma/policy.py::load_policy`:
its defensive coercion ladder (malformed stored `cooldown_seconds`/`daily_cap`
→ shipped default; `None` reaction_emoji → OFF; `bool()`/`int()` coercion of
string-typed KV rows) has NO test — the only existing test feeds `undeclared`
(pure-default) values.

## Scope

Test-only. `sb/` source untouched; no dependency change.

## What the tests pin

[[fill: enumerate the pinned branches after the test lands]]

## Verification

[[fill: pytest tail + counts, guards, bootstrap check]]

## 💡 Session idea

[[fill]]

## ⟲ Review

### previous-session review

[[fill: predecessor card + carried convention]]
