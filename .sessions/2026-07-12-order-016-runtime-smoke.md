# 2026-07-12 — ORDER 016: runtime-smoke merge gate (headless boot + wiring-graph check)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · CI gate build, headless boot-and-wire smoke (Q-0194)

## Scope

One bounded slice: ORDER 016 (control/inbox.md, filed 2026-07-12T15:13Z,
P2) — a per-PR CI job that imports the bot package headless, loads all
handler registrations, wires all panels, and asserts the registry +
EventBus subscription graph is intact. The order's "cogs/views" language
is old-bot vocabulary; the new bot's equivalents are the manifest
handler registrations, `SUBSCRIBE_ROSTER`, and the panel registry.

## Delivered

- `tools/check_runtime_smoke.py` — the gate. It rides the composition
  root's OWN code paths (never a parallel re-implementation, per
  `sb/app/verify_boot.py`'s precedent — its stage-2 `gate_recompile`
  call is this script's step 1): boot-gate leg A (which imports every
  `sb.manifest` module and runs the `ENSURE_REFS` hooks — the same way
  a real boot populates the ref table) → `load_live_manifests()` →
  `build_runtime` + `install_live_target_index` →
  `register_manifest_panels` + `install_panel_runtime` (headless
  branch: presenter uninstalled when discord is absent — panel_host's
  own contract) → an `EventBus`-shaped recorder + `arm_subscribe_roster`.
  Six W-rules assert the graph:
  - W1: every manifest-reachable ref resolves to a real callable
    (runtime twin of compile P2's `is_registered`).
  - W2: every `PanelRef` is registered in the panel registry (the
    band-1 replay's exact LookupError class).
  - W3: every armed bus subscription names a `KNOWN_EVENTS` event and
    binds a callable (no orphan/typo'd listeners).
  - W4: every `AT_LEAST_ONCE` event has ≥1 live subscriber.
  - W5: every `EventSpec.expected_subscribers` ref resolves AND its
    event has ≥1 live subscriber.
  - W6: every statically-enumerable emit site (AST scan over `sb/` for
    `*.emit(<literal-or-module-constant>, …)`) emits a declared event.
- `.github/workflows/named-gates.yml` — the smoke runs as a step INSIDE
  the required `manifest-validate` named gate: required-on-PRs without
  a ruleset edit (the owner flips settings, agents author files —
  build-brief §8.1; riding an armed gate needs no owner action).
- `.github/workflows/ci.yml` — added `check_runtime_smoke` to the
  committed checker fleet loop (alphabetical position).
- `tests/unit/app/test_runtime_smoke.py` — 19 hermetic pins exercising
  every W-rule's red AND green path against in-memory broken fixtures
  (synthetic manifests/bus/specs only; NO full roster import mid-suite —
  the `test_main_wiring.py` front-running lesson), plus the AST scan's
  literal/constant/dynamic-skip/syntax-error behaviors.

## Honest coverage boundary (stated in the script docstring, verbatim class)

- Dynamic emit names (outbox relay re-emit-as-stored, `enqueue_all`'s
  spec-driven names, parity taps) are NOT statically enumerable — they
  stay runtime-guarded by the enqueue name-guard against `KNOWN_EVENTS`.
- Zero-subscriber BEST_EFFORT events are legal by design (§2.8
  fire-and-forget observability) — not red. "Every emit has its expected
  subscriber" binds through W4 (durable) + W5 (declared expectations;
  currently no manifest declares `expected_subscribers`, so W5 binds
  future declarations — stated, not hidden).
- Nothing is dispatched end-to-end: this is the cheap boot-and-wire tier
  the order asks for; the dispatch-tier live-boot job is its named
  follow-up.

## done-when verification

1. Runs required on PRs: inside `manifest-validate`, one of the 6 armed
   §6 gate names in the main-branch ruleset (named-gates.yml header).
2. Green on current main: clean at the PR head — 48 manifests, 946
   dispatch targets, 216 panels, 6 roster modules, 4 subscribed event
   names, 5 static emit sites, 25 declared events. Also green in a
   pyyaml+pytest-only venv (the exact CI env — guarded-import
   discipline holds).
3. Deliberate wiring break turned it red: a temporary fixture module
   emitting an undeclared event (`order016.smoke_break_fixture`) pushed
   as its own commit turned `manifest-validate` red in CI (run URL
   cited in the PR body), then reverted; the red path stays covered by
   the 19 permanent unit pins.

## Evidence

- smoke: `python3 tools/check_runtime_smoke.py` → clean (counts above).
- units: `python3 -m pytest tests/ -q` → 1779 passed, 2 skipped
  (serial, local Postgres re-provisioned parity/parity_replay/superbot —
  the 11 previously-env-red integration/btd6_seed_data tests pass on a
  freshly provisioned cluster).
- fleet: all 22 committed checkers green (incl. the new one) +
  `python3 tools/manifest_compile.py` green (snapshot hash unchanged
  `7da5336e…`) + `python3 bootstrap.py check --strict` green.

## Codex

One technical question posted on the final PR head about W6's
enumeration completeness; merged on green without waiting (repo
doctrine); any returned findings get verification next wake.

## 💡 Session idea

W5 is armed but vacuous today — no manifest declares
`expected_subscribers`. A cheap follow-up order: declare the four
KNOWN consumer relationships (xp.level_up → spotlight + xp role-reward,
economy.balance_changed → economy route, moderation.action_taken →
server_logging pair, audit.action_recorded → server_logging) as
`expected_subscribers` on their EventSpecs, turning today's implicit
roster wiring into a declared, gate-checked contract. Then a roster
module accidentally dropped from `SUBSCRIBE_ROSTER` reds the gate
instead of silently unhooking a consumer (today only W4 catches the
audit case; the three best-effort relationships are unguarded).

## ⟲ Previous-session review

#290's card (treasury/karma argv fix) modeled the evidence-first format
this card follows; its "11 known-red integration tests under local
Postgres" note turned out to be provisioning state, not a stable fact —
this session's freshly provisioned cluster runs them green, so the
known-red ledger entry should not be copied forward as permanent.
