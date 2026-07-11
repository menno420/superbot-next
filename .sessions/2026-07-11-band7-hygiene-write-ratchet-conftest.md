# 2026-07-11 — band-7 hygiene slice: comment-preserving --write-ratchet + the ai-dir after-only conftest reset

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · hygiene/tooling (Q-0194 / ORDER 012)

## Scope

The two hygiene items from the band-7 remaining map (control/status.md
CONTINUATION line, minted at the #192 heartbeat): (a) the
`tools/check_parity_depth.py --write-ratchet` comment-destruction fix
(the #144 parked HYGIENE-FIX CANDIDATE: the old writer rebuilt
parity.yml via `yaml.safe_dump` and destroyed every comment including
the ~130-line header — the tool itself printed "comments are lost";
every flip PR ran run-learn-restore-hand-apply); (b) the conftest
after-only reset consolidation in tests/unit/ai. No parity.yml flips,
no new exemption classes, no manifest changes, ratchet semantics and
minted values UNCHANGED.

## What shipped

1. **The comment-preserving writer** (tools/check_parity_depth.py) —
   `--write-ratchet` is now a TEXT SPLICE: `splice_ratchet_text` finds
   the real `ratchet:` key inside the `depth:` block (never the
   `# ratchet:` schema comment above it), replaces exactly that block
   with `render_ratchet_block`'s lines at the committed formatting, and
   leaves every other byte of the file untouched — header, exemption
   prose, key order. Missing `ratchet:` key ⇒ loud SystemExit, never a
   destructive fallback. `write_ratchet` (the upward-only value miner)
   is untouched — same rows, same values as the old destructive path.
   Verified on the real tree: `--write-ratchet` at HEAD is a byte-level
   no-op (`git diff` empty) and the checker stays
   `OK — 49 subsystems (37 ported), 467 goldens`.
2. **The pins** (tests/unit/parity_gate/test_check_parity_depth.py,
   `TestWriteRatchetPreservesComments`) — real-file identity round-trip
   byte-identical (header + `# ratchet:` comment survival), header
   bytes survive a value bump, minted values equal the old
   `yaml.safe_dump(write_ratchet(...))` writer's document exactly,
   missing-key SystemExit, synthetic splice replaces only the block,
   empty ratchet renders `ratchet: {}`.
3. **The ai-dir after-only conftest reset** (tests/unit/ai/) — the four
   scattered per-file autouse reset fixtures (grounding, nl_frontend,
   nl_engine_evals' reset leg, orchestration's after-leg) consolidate
   into ONE dir-wide after-only autouse fixture in conftest.py covering
   every K10 registry the suites touch (tools_catalogue, orchestration
   profiles/key-reader/workflows, verify, absence_guard, policy,
   conversation, router probes, memory, instructions + profile reader,
   feature_facts, nl_engine, evals) with the #156 idempotent
   `ENSURE_REFS` re-arm after the final clear, then the kernel plumbing
   resets (flags/routing/tasks/gateway/collector/guild-policy-reader).
   test_k10_nl_engine_evals keeps only its ai_audit monkeypatch fixture.
4. **The one sanctioned pre-leg, kept with empirical proof** —
   test_k10_orchestration.py retains a slim pristine-baseline BEFORE
   clear (renamed `_pristine_baseline`, docstring cites the ground): a
   pure after-only conversion was tried and REGRESSES the #156 fix — 3
   failures under non-canonical selection
   (`pytest tests/unit/band7/test_band7_projmoon_walking_skeleton.py
   tests/unit/ai/test_k10_orchestration.py`: armed btd6 toolsets break
   `known_toolsets() == {"base"}`, and the manifest-owned
   `analyze_execute_verify` runner double-claims). The after leg lives
   in conftest; the pre-leg is the documented exception.

## Honest notes

- No repo doc documented the old destructive behavior (grep: only the
  tool's own print + neutral mentions in docs/decisions.md D-0016 text
  and docs/status/rebuild-completion-report-2026-07-09.md) — so the fix
  updates the tool docstring/print only; nothing else needed restating.
- Comments INSIDE the machine-minted ratchet block are not preserved
  (nothing hand-written belongs there; documented in the splice
  docstring).

## Ladder (serial, local Postgres — parity role + parity_replay DB, CI shape)

- units, gate, report, named gates: recorded in the PR body (run at the
  final head).

## 💡 Session idea

The #190 checker-gap ledger entry generalizes: check_sim_gate misses
VALUE drift on existing [A] pins, and (this slice's cousin) nothing
diffs the ratchet block's committed values against a fresh mint in CI —
`--write-ratchet` is only run by hand in flip PRs. A `--check-ratchet`
mode (splice in-memory, compare bytes, red on drift) would make the
"regenerate it upward in the same PR" rule self-enforcing for free now
that the splice writer exists — the identity round-trip test already
proves the byte-compare is stable.

## ⟲ Previous-session review

The D-0073 card's mint-procedure record transferred cleanly. What this
slice inherited as friction: the #144 parked list named the
--write-ratchet pain precisely (with the tool's own "comments are
lost" print as the citation), which made scoping trivial — the parked
items that carry their own repro command are the ones a later hygiene
slice can pick up cold. The conftest item, by contrast, was four words
in the remaining map ("conftest after-only reset in tests/unit/ai")
with no repro; recovering the intent needed the #156 commit + an
empirical regression test of the naive reading. Parked items should
carry either a repro or a one-line acceptance test.
