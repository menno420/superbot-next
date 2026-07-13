# 2026-07-13 — tools: check_orphan_pendings — guard the PR #412 bug class

> **Status:** `complete`

- **📊 Model:** `fable-5` · port-tooling lane (claim
  `control/claims/port-tooling-mint-orphan.md`, orphan-checker leg;
  branch `claude/port-tooling-orphan` off main @ 5dac6ce)

## Scope

Ship `tools/check_orphan_pendings.py` — a checker-fleet guard for the
exact bug class PR #412 cleaned by hand: `*_pending` handler refs whose
handler (or referencing panel) no longer exists. Two directions after a
headless composition boot (the `check_runtime_smoke` pattern —
`gate_recompile` → `load_live_manifests` → `register_manifest_panels`,
DB-free, pyyaml-only):

1. **Dangling** — a handler ref referenced by a REGISTERED panel's
   actions/selectors (incl. dynamically minted refs like
   `sb/domain/settings/panels.py:300`'s
   `HandlerRef(f"settings.{action_id}_pending")`, which no static grep
   can resolve) or by a live manifest, with no `_REF_TABLE` entry —
   the RefUnresolved-on-click class. RED, no baseline.
2. **Orphan** — a registered `*_pending` handler referenced by NO
   registered panel and NO manifest ref — the #412 class (registered
   but unreachable). RED against an explicit burn-down baseline
   (the `_KNOWN_ENSURE_ONLY` prior art,
   tests/unit/invariants/test_composition_parity.py): entries may only
   be pruned; a stale row (entry no longer orphaned) is also RED.

Wiring: ONE name added to ci.yml's committed-checker-fleet list
(`.github/workflows/ci.yml`, checkers job) — purely additive. External
test pin: `tests/unit/app/test_orphan_pendings.py` (synthetic fixtures,
the test_runtime_smoke.py hermetic pattern — no roster import
mid-suite).

Scope fences honored: kernel lifecycle `_pending` globals,
`rps_pvp_pending` subsystem strings, and op-key strings never enter —
the check reads only `_REF_TABLE` handler names and walked `*Ref`
objects, never raw greps.

## Baseline found on main @ 5dac6ce (NOT fixed here — reported)

Zero dangling refs. Nine orphan registered-but-unreferenced
`*_pending` handlers, seeded as the burn-down baseline:
`blackjack.tournament_open_pending` / `blackjack.tournament_start_pending`
(knowingly kept — sb/domain/blackjack/handlers.py:508 docstring says the
composition-parity test pins the import roster),
`rps.register_pending` / `rps.start_pending` / `rps.matchup_pending`
(stale docstring — `!rpsregister`/`!rpsstart`/`!rpsmatchup` route to
live handlers per sb/manifest/rps_tournament.py:64-87),
`btd6.events_pending` / `btd6.ops_pending` / `btd6.ref_ct_pending`
(plain handlers in sb/domain/btd6/service.py:382-397; the manifest
routes those groups to `btd6.grp_bare` silence),
`settings.group_pending` (sb/domain/settings/handlers.py:242 registers
it but `open_group` returns the BLOCKED Reply directly, never
dispatching the ref).

**Guard recipe** (for the burn-down session): retiring an orphan means
deleting its `pending_handler(...)` call (e.g.
`_register_pending()` in sb/domain/rps/handlers.py:712 /
sb/domain/blackjack/handlers.py:508) AND pruning the checker baseline
row in tools/check_orphan_pendings.py in the same PR — the stale-row
rule reds otherwise; the blackjack pair also needs the
`test_the_sweep_sees_the_live_roster` pin in
tests/unit/invariants/test_composition_parity.py:150 re-pointed at a
live ref, and `manifest_compile --write` to drop the refs projections
(the #412 procedure).

## Verification (close-out)

Shipped as PR #415 (`claude/port-tooling-orphan` @ f542328 + this flip,
off main @ 5dac6ce). Verbatim final lines:

- `python3 tools/check_orphan_pendings.py` → `check_orphan_pendings:
  OK — 23 registered *_pending handler(s) (14 referenced, 9 on the
  burn-down baseline); 882 handler ref(s) walked from manifests +
  registered panels, 0 dangling, 0 new orphans`
- `pytest tests/unit/app/test_orphan_pendings.py -q` →
  `11 passed in 0.04s`
- `pytest tests/ -q` → `2830 passed, 9 skipped in 63.20s (0:01:03)`
  (full suite; this container's uv-tool pytest needed
  `uv tool install --with pyyaml pytest` first — the bare tool env
  lacked pyyaml and failed collection on two checker-importing tests)
- the full 24-name committed checker fleet + `manifest_compile`
  (sha256:99ebfbcd…, 48 manifests) green locally;
  `python3 bootstrap.py check --strict` green except the DESIGNED
  born-red hold on this card (flipped by this commit) and the two
  pre-existing claims-format advisories (never exit-affecting;
  one is this lane's own claim file from #413 — pre-dates this branch).

## ⟲ previous-session review

The most recent prior card (2026-07-13-role-orphan-refs-trueup.md,
PR #412) is exactly this session's provenance and it holds up well:
its claim that the three role pendings were unreachable re-verified
cleanly here (the runtime walk finds zero role orphans at HEAD), its
evidence discipline (snapshot-projection cross-check + "re-verified at
HEAD e17fb2a") made the bug class crisp enough to mechanize, and its
verification section separated local-env noise from CI truth. One gap:
it fixed the three role orphans by hand but left the SAME class alive
in blackjack/rps/btd6/settings (the nine found above) — a manual sweep
stops where the session's attention stops, which is precisely the
argument for this checker existing.

## 💡 Session idea

The orphan direction only sees SPEC references (manifest walk + panel
registry). If a future handler starts dispatching pendings dynamically
(`resolve(HandlerRef(f"{group}_pending"))` at click time — none exist
today, verified), the checker would false-red it; the cheap hardening
is an AST scan for `HandlerRef(` calls with f-string args ending
`_pending"` that AUTO-EXEMPTS matching prefixes, mirroring
check_runtime_smoke's honest W6 dynamic-name boundary. Build it only
when the first such dispatch site actually lands.
