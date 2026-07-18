# 2026-07-18 — cover the untested CI-gating AST checkers (check_config_usage, check_symbol_shadowing)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · additive test slice (born-red, holds substrate-gate)

## Scope

Two AST checker tools are wired as **named CI gates**
(`.github/workflows/named-gates.yml` / `ci.yml`) yet carry **zero unit
coverage** — the checkers that GATE every PR are themselves unverified:

- `tools/check_config_usage.py` — bans `os.getenv` / `os.environ` reads
  anywhere under `sb/` except `sb/kernel/config/` (and the ledgered
  `sb/adapters/parity/boot.py` widening). Public seam:
  `check(root: Path) -> list[str]` (empty list = clean), AST helper
  `_env_reads(tree) -> list[tuple[int, str]]`.
- `tools/check_symbol_shadowing.py` — guards SYMBOL identities: no
  in-module top-level re-bind, cross-module public-name collision inside
  one package, globally-unique grammar names (`*Spec`/`*Result`/lexicon),
  the banned bare `ActionSpec`. Public seam `check(root: Path) -> list[str]`,
  AST helpers `_top_defs(tree)` and `_is_grammar_name(name)`.

This slice is deliberately CONTAINED and purely additive: NO product or
tool code changes (new test files only ⇒ cannot regress anything). It
stays locally verifiable — the two checkers are stdlib-`ast`-only and
run against a `tmp_path` fake `sb/` tree, no DB, no bot boot, no golden
parity.

## Deliver — pin each checker's report + clean-tree pass

New files, matching the existing checker-test home
(`tests/unit/parity_gate/test_check_parity_depth.py` style):

- `tests/unit/tools/test_check_config_usage.py` — plants `sb/foo.py`
  with an `os.getenv(...)` read and asserts `check()` REPORTS it; plants
  a clean tree and asserts no violations; pins the `sb/kernel/config/`
  and `sb/adapters/parity/boot.py` allow-prefixes; drives `_env_reads`
  directly over small AST inputs (`os.getenv`, `os.environ`,
  `from os import getenv`); and re-runs `check(REPO_ROOT)` to pin the
  committed tree green.
- `tests/unit/tools/test_check_symbol_shadowing.py` — plants an
  in-module duplicate top-level def, a cross-module public collision, a
  duplicate grammar name, and a bare `class ActionSpec`, asserting each
  is reported; plants a clean tree (and confirms `__init__.py`
  re-exports + `ENSURE_REFS` module-hooks are exempt); drives `_top_defs`
  and `_is_grammar_name` directly; and re-runs `check(REPO_ROOT)` green.

## Verification

- `python3 -m pytest tests/unit/tools/test_check_config_usage.py
  tests/unit/tools/test_check_symbol_shadowing.py -q` → green (verbatim
  summary in the PR body). Full `tests/unit/` NOT run here — this
  container has a pre-existing `yaml`-module gap + pytest-randomly
  ordering pollution that makes the whole-suite run a non-signal; the
  CI named-gates carry the authoritative sweep.
- Both checkers were also run against the committed repo
  (`python3 tools/check_config_usage.py .` /
  `python3 tools/check_symbol_shadowing.py .`) to confirm the test
  harness matches the real invocation shape.

## 💡 Session idea

The other stdlib-`ast` guard tools carry the same gate-without-coverage
shape and are worth the same one-file pin next — `tools/check_no_skip.py`
and `tools/check_namespace.py` (both referenced in the layer-map guard
list in `CLAUDE.md` and wired into CI). A single `tests/unit/tools/`
sweep that plants a fake tree per checker would close the whole
checker-coverage class; this slice does the two called out in the
config/symbol seam so the pattern is established.

## ⟲ Previous-session review

Reviewed the predecessor `.sessions/2026-07-18-setup-except-boundary-
tests.md` (backlog C1), an additive characterization slice that pinned
`sb/domain/setup/moderation.py`'s four `except` swallows (fail-CLOSED
refusal vs. informational fail-soft degrade) with a new
`tests/unit/setup_band/` file and NO product change. Same born-red,
holds-substrate-gate posture as this card; it confirms the current
hardening rhythm is small, contained, new-test-only slices that pin an
unverified behavior. This slice carries that rhythm one layer down — from
product-band except boundaries to the CI checker tools that gate every
one of those PRs.
