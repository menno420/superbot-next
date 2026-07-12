# 2026-07-12 — canonical-order flake fix (the 11 full-deps `pytest tests/` reds)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · test infrastructure

## Scope

The follow-up the #218 card ledgered ("Guard recipe (the pre-existing
flake follow-up)"): canonical `pytest tests/` with FULL local deps failed
11 tests at main `977bb27`/`249ecaa0` — 2× `tests/unit/ai` (k10 nl), 4×
`tests/unit/band2/test_channel_state_rehome.py`, 1× band3 treasury hub
bytes, 4× band6 — all green in isolation, invisible to CI (the required
tests job installs only pytest+pyyaml, so the dep-guarded suites skip).
The #141/#156 cross-test registry-leak family.

## Root cause

ONE upstream trigger, THREE leak mechanisms. The trigger: #213's
`tests/integration/` suite collects FIRST and its `Harness.start()`
imports the ENTIRE composition (`_load_manifests` → every `sb.manifest.*`
→ every `sb.domain.*`) at session start. Pre-#213, those modules were
first imported BY their band's own tests, so import-time registration
fired after any earlier wipe; post-#213 every module is cached from
minute one and import-time registration is a one-shot that later
one-way registry wipes destroy permanently.

1. **ai (2 victims)** — `tests/unit/ai/conftest.py`'s after-only reset
   re-arms `sys.modules["sb.manifest.ai"].ENSURE_REFS()` (the #199
   consolidation). That hook ends in `_readers.install_ai_platform()`
   (`sb/manifest/ai.py:290`) — a composition-root READER install, never
   an import-time registration — and it ran AFTER the fixture's
   `policy.reset_policy_for_tests()`. Pre-#213 the branch was dead under
   canonical order (manifest never cached); post-#213 it fires after
   every ai test, so the deny-when-unconfigured tests inherited a
   DB-backed policy-bundle reader over a closed pool
   (`sb/kernel/db/pool.py:157 RuntimeError`).
2. **band2/band3/band6-blackjack (6 victims)** —
   `tests/unit/authority/test_transparency_and_oracles.py::test_compiler_p4_is_armed_by_the_leaf`
   ended with a bare `clear_ref_table()`: table emptied, `sb.manifest.*`
   purged, NO re-arm. Cached `sb.domain.*` modules' import-time
   registrations (`handler:channel.slowmode`, `handler:treasury.render_hub`,
   `workflow:games.balance_payload_0`, `provider:ux_lab.home_fields`)
   can never re-fire → `RefUnresolved` for every later-listed suite that
   resolves them. Two gap-class members made even a fresh composition
   boot (the band6 skeleton Harness) unable to heal it:
   `sb/domain/games/ops.py::register_ops` did not chain
   `ensure_ops_refs()` (blackjack/rps got that exact fix; games missed
   it) and `sb/manifest/ux_lab.py` registered nothing at module level
   (ensure-only — the D-0025 / ensure-only-registration-gaps class).
3. **band6 providers (2 victims)** —
   `tests/unit/band4/test_band4_community.py`'s autouse fixture wipes the
   rank-provider registry to builtins-only on teardown, and the cached
   registrants could not be re-armed because
   `sb/domain/counting/service.py` + `sb/domain/deathmatch/service.py`
   guarded `register_provider_rows()` with a module-global boolean latch
   — "I ran once" instead of registry truth — so the sanctioned wipe
   stranded `get_provider("countlb")`/`("dm_lb")` forever.

## Fix shape (test hygiene + registration idempotency; zero behavior change)

- `tests/unit/ai/conftest.py` — after the `ENSURE_REFS()` re-arm, the
  reader seams `install_ai_platform()` arms now END un-armed (policy
  bundle / memory ports / profile-key / profile reader / nl preset+floors),
  exactly like the kernel-plumbing tail already did for gateway/flags.
- `tests/unit/authority/test_transparency_and_oracles.py` — the
  `test_band5_role` recipe: snapshot cached `sb.manifest.*` names, run
  the compile probes in `try/finally`, then clear → re-import each →
  `ENSURE_REFS()` → RE-PURGE `sb.manifest.*`. The re-purge is
  load-bearing: it preserves `clear_ref_table`'s documented post-state,
  which `test_band5_platform`/`test_band5_role` pin (they assert
  IMPORT-TIME port fills, so they need the fresh import).
- `tests/unit/band4/test_band4_community.py` — teardown re-arms the
  cached provider registrants (games/counting/deathmatch) after the wipe.
- `sb/domain/counting/service.py` + `sb/domain/deathmatch/service.py` —
  the boolean latch replaced by registry truth (`get_provider(...) is
  None`), making `register_provider_rows()` genuinely re-armable.
- `sb/domain/games/ops.py` — `register_ops()` chains `ensure_ops_refs()`
  (the blackjack/rps posture, comment carried).
- `sb/manifest/ux_lab.py` — `_ensure_refs()` now also runs at module
  import (both hooks `is_registered`-guarded), pruning an
  ensure-only-registration gap-class member.

NOT fixed here (out of scope, pre-existing on clean main): artificial
orders skipping intermediate suites still flake (e.g.
`pytest tests/integration tests/unit/band4 tests/unit/band6` reds 5
tournament tests on clean main too; `tests/integration tests/unit/band5`
reds the 2 import-time-port-fill pins) — same family, not in the
canonical 11, ledgered as follow-up below.

## Evidence

- Reproduced first: full `pytest tests/ -q` at `249ecaa0` with full deps
  = 11 failed / 1462 passed / 2 skipped, list identical to the #218 card.
- Mechanisms proven by minimal chains (serial, one DB user at a time —
  an early experiment invalidated itself by racing a background full run
  against the shared Postgres; redone clean):
  `tests/integration tests/unit/ai` → the 2 ai reds;
  `tests/integration tests/unit/authority tests/unit/band2/... band3/...`
  → the 5 RefUnresolved reds; `tests/integration tests/unit/band4/...
  tests/unit/band6/...` → the 2 provider reds; the band6
  blackjack/ux_lab pair additionally needed band5's partial-snapshot
  clear in the chain.
- After the fix: full `pytest tests/ -q` = **1473 passed, 2 skipped**
  (canonical order), and the alternate order `pytest tests/unit
  tests/integration -q` = **1473 passed, 2 skipped**. Touched/victim
  suites green in isolation (ai 141, authority 49, band4 30, band6 176,
  band2+3+5 160). `tests/integration` standalone (the CI invocation) 5/5.
- Ladder: `run_golden_parity.py --gate` **GREEN — 328/328 across 39
  ported subsystems** (zero golden movement); `check_parity_depth` OK —
  50 subsystems (39 ported), 467 goldens; `manifest_compile --write`
  byte-stable (no snapshot diff from the ux_lab/games edits); all 12
  named checkers clean (namespace, escape hatches, schema growth,
  amendments, shadowing, no-skip, config usage, metric cardinality,
  egress, sim gate, parity depth, compat).

## @codex triage (Q-0120-verified, per ORDER 010 / Q-0259)

The review's top-level ACTION CLAIMS were PHANTOM, again: "Committed
6ec0eb2 …" — `git cat-file -t 6ec0eb2` = "Not a valid object name", no
such commit on any local or remote branch (`git ls-remote`); "Created
PR …" — the repo's only open PR is #222 itself (`list_pull_requests`
verified at triage time). Consistent with the standing top-level-claims-
phantom-prone calibration. Its SUBSTANTIVE findings, each verified
against shipped source:

1. ACCEPTED (re-derived, not pulled): the authority teardown's
   `ENSURE_REFS` sweep leaves `install_ai_platform()`'s reader seams
   armed for later-listed suites. Real divergence from the
   post-ai-suite world (whose conftest ends those seams un-armed).
   Fixed in my own version: the finally block now resets the same
   reader-seam set the ai conftest uses, guarded on `sb.manifest.ai`
   having been cached.
2. DECLINED (with citation): a new kernel seam in
   `sb/kernel/interaction/reactions.py` to remove the single
   `ai.review_thumbs_down` consumer. Unnecessary —
   `register_reaction_consumer` is a name-keyed dict UPSERT
   (`reactions.py:61-66`, "Idempotent re-registration … is a no-op"),
   so nothing accumulates, and the consumer registers at MODULE IMPORT
   (`sb/domain/ai/review.py:251`), so it is armed from session start in
   every full-deps run; removing it mid-suite would deviate from the
   world every other suite sees.
3. ALREADY IN: preserving the final `sb.manifest.*` re-purge — that was
   this PR's own load-bearing step (band5's import-time port-fill pins).

## 💡 Session idea

The three mechanisms share one testable invariant: "the world a suite
finds is the world it leaves." A tiny session-scoped autouse fixture in
`tests/conftest.py` that snapshots `ref_inventory()` + `provider_names()`
at each DIRECTORY boundary and asserts no shrinkage would turn the next
one-way wipe into a red naming the leaking suite instead of an
11-victim mystery three bands downstream.

## ⟲ Previous-session review

The #218 btd6 re-home (merge `249ecaa0`) ledgered this flake instead of
chasing it mid-slice — right call, and its guard recipe (exact failing
list + "all green in isolation" + the #141/#156 family pointer) priced
this slice accurately. What it could have done better: the recipe's
bisect suggestion (`--deselect` halving) was the slow path — the decisive
probe turned out to be "what NEW suite collects before the victims"
(#213's tests/integration), findable from the failing-window PR list in
minutes; successor recipes should name the window's collection-order
changes first, not just the halving procedure.
