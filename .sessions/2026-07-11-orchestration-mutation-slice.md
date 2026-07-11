# 2026-07-11 — the orchestration-mutation slice (band 7, D-0072)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

The band-7 remaining map's last D-0070 parked slice ("the tools profile
pickers — need ai_orchestration_mutation + the orchestration_profile
columns, migration 062"). The tools chooser's Guild / Channel /
Category / Preview pickers go LIVE on the armed component lanes; the
behavior Routing-matrix button stays the last honest chooser pending
terminal (the routing-matrix follow-up slice, unchanged).

## What shipped

1. **migrations/0031_ai_orchestration_profile.sql** — the oracle 062
   shape NAME_STABLE: nullable `orchestration_profile` TEXT on
   ai_channel_policy + ai_category_policy (no CHECK — the shipped
   comment: keys validate at the audited seam). The shipped
   ai_guild_policy column ports as the `ai_orchestration_profile`
   guild_settings KV row (D-0025; the ai_policy_generation precedent).
2. **sb/domain/ai/policy_store.py** — the shipped COLUMN-ONLY setters
   (fresh row minted mode='inherit'; a conflicting row's
   mode/min_level/cooldown/instruction_profile_id NEVER touched —
   SQL-seam pinned by test), the guild KV twin (empty string = the
   shipped NULL), and the orchestration reads
   (`get_guild_orchestration_profile`, `load_orchestration_overlays`).
3. **sb/domain/ai/orchestration_ops.py** — `ai.set_guild_orchestration`
   / `ai.set_channel_orchestration` / `ai.set_category_orchestration`:
   ONE reversible DB leg each (scoped upsert + bump_generation, one
   txn, K7 central audit), the shipped advisory
   `ai.orchestration.*_changed` events after commit (BEST_EFFORT,
   payload guild_id + mutation_id), key validation with the shipped
   InvalidAIOrchestrationValueError sentence ("… (or null to clear)"),
   leg re-check in-txn (§4.1). Compensator allowlist stays EMPTY.
4. **sb/domain/ai/orchestration_widgets.py + panels.py** — the five
   pages: `ai.tools_guild_picker` (the page IS the profile select, NO
   clear — the shipped include_clear=scope != "guild"),
   `ai.tools_channel_picker` / `ai.tools_category_picker` (the shipped
   `_tools_page_embed` bytes + "↩ AI Tools" back-route; category rides
   the D-0070 roster string select), `ai.tools_profile_picker` (the
   shipped _ProfileChoiceView prompt "Pick an orchestration profile for
   {label}." + the Clear (inherit)/__inherit__ option; the pick applies
   immediately and acks the shipped "✅ {Set **key** as…|Cleared…} the
   orchestration profile for {label} (generation N)."), and
   `ai.tools_preview_picker` → the shipped dry-run analyzer embed
   ("AI Tools & Workflows — preview": Resolved profile / Offered tools /
   Withheld by profile / Precedence + the dry_run footer) on the kernel
   resolve_orchestration(dry_run=True) + select_tools(SYSTEM)
   primitives. The chooser's "Current" field now reads the REAL guild
   key + override counts (per-part fail-soft; fresh-guild bytes
   unchanged).
5. **sb/domain/ai/readers.py** — `_profile_key_with_overlays` installed
   OVER the band-1 K10 profile-key reader at install_ai_platform:
   channel/category keys from the typed columns, guild key from the KV
   row (band-1 fallback when unset), FAIL-SAFE degrade on a store miss
   (DB-free replay keeps band-1 behavior exactly).
6. **parity/parity.yml** — THREE exemption rows for the new advisory
   events under the EXISTING `select-driven` class (D-0064 re-argued
   per row; no new class, no new table exemptions — the tables were
   already D-0070 modal-driven and the guild KV home is kernel-owned).
   Ratchet UNTOUCHED (no goldens move). **compat/compat-frozen.json**
   amended +3 event payload pins (guild_id + mutation_id). ZERO
   sim-gate/lock churn (session-minted picker ids only, trap 12d).
7. **docs/decisions.md** — D-0072 (the full verdict, deviations, and
   the trap-24 sha caveat: default branch a03e5fe8→a409d9b7 during
   reconstruction; no golden pins these clicks).
8. **tests/unit/band7/test_band7_orchestration_mutation.py** — 14
   tests: the three scope-page byte drives, the profile-page bytes
   (roster order + Clear option), guild/channel/category picks through
   the recorded engine seam (clear → profile_key=None pinned), the
   unknown-key refusal byte, the K6 member gate, the preview analyzer
   bytes (Resolved profile/Precedence/footer), the leg re-check, the
   column-only SQL seam, the widened reader (+ its fail-safe), and the
   event payload shape. Two sibling tests updated (test_band7_ai_surface
   store/event/panel rosters).

## Codex triage (Q-0120 source-verified — 3 taken, 1 documented)

Review 2026-07-11 on head `b943138` (2 P2 + 2 P3, all line-anchored):

- **P2 TAKEN** — an explicit guild CLEAR (`profile_key=None` through
  `ai.set_guild_orchestration`) stored the empty-string marker, read
  back as "unset", and RESURRECTED the band-1
  `guild_instruction_profile` fallback (the oracle's clear resolved
  straight to the compatible default). Fixed:
  `read_guild_orchestration_profile` now returns `(row_present, key)`
  and a PRESENT row is authoritative (cleared included); band-1 serves
  only while the row was never written. Regression-pinned.
- **P2 TAKEN** — the tools chooser's "Current" field read ONLY the KV
  row while the resolver also fell back to band-1: a legacy
  `guild_instruction_profile` colliding with a preset key would show
  `compatible_default (today)` while resolving differently. Fixed: a
  shared `readers.guild_orchestration_default` helper mirrors the K10
  reader exactly (the shipped single-source posture —
  snapshot.orchestration.guild_profile_key fed both surfaces); the
  preview footer rides it too. Regression-pinned.
- **P3 TAKEN** — the `[:25]` roster cap could truncate the "Clear
  (inherit)" option once the registry grows past 24 presets; the cap
  now truncates PRESETS only (shipped roster was 5, uncapped).
  Regression-pinned.
- **P3 DOCUMENTED, NOT TAKEN (oracle-faithful)** — a tools-only write
  mints a `mode='inherit'` policy row that the `ai.policy_list` page
  then shows as a mode override. That IS the shipped behavior: the
  oracle's column-only setter inserts `mode='inherit'` (utils/db/ai.py,
  migration 062) and the oracle list_view's `_channel_entry_summary`
  renders mode/min_level/cooldown with no orchestration awareness —
  "fixing" it would diverge from the oracle. Cited on the PR.

## Verification (serial, local Postgres)

Final head (after the codex fixes + the #186 merge-forward):

- units: `pytest tests/ -q` → **1405 passed / 2 skipped**
- gate: `run_golden_parity.py --gate` → **GREEN 214/214 across 34
  ported** (migration 0031 applied by the harness boot)
- report: `run_golden_parity.py --report` → **251/465 green, 465/465
  replayable, 34/49 ported** (unchanged by this slice — no goldens
  move; the +2 green / +1 ported vs first push is main's admin flip
  #186 merged forward)
- named gates: manifest_compile (rewritten + verified green),
  check_parity_depth OK (49 subsystems, 465 goldens), check_namespace /
  check_sim_gate / check_compat_frozen / check_migrations (31) /
  check_escape_hatches / check_schema_growth / check_amendments /
  check_symbol_shadowing / check_no_skip / check_config_usage /
  check_metric_cardinality / check_egress / check_data_lifecycle /
  check_rollback_disposition / check_intent_survival / check_slash_cap /
  check_cost_posture / check_credential_lifecycle /
  check_lockfile_fresh / check_verified_live + kit check --strict —
  all clean.

## Honest notes

- The tools surfaces are golden-UNPINNED (no imported golden drives any
  chooser click) — byte claims rest on search_code fragment
  reconstruction of the oracle's DEFAULT branch, which moved mid-session
  AGAIN (a03e5fe8 → a409d9b7) and can be ahead of the corpus sha
  7f7628e1 (trap 24; ledgered in D-0072).
- The shipped `❌ InvalidAIOrchestrationValueError:` echo is REBUILT in
  the widget pre-check (this engine's ValidatorError envelope prefixes
  "invalid argument: " — the karma-16a class); the leg still re-checks.
- The shipped views sent/edited ephemerals in place; session pages
  re-open (the projmoon edit-in-place deviation class, unchanged).
- The shipped AIConfigSnapshot.orchestration projection and the durable
  per-decision orchestration audit trace stay unported (the oracle's own
  §12.1 deferral).
- The local container came up fresh (no parity role/DB) — recreated to
  the CI env shape (user parity / db parity_replay) before the ladder.
- ORDER-004 live-drive leg: NOT run this session; the walking-skeleton
  suite carries the CI-runnable drive (testing-report row 9 untouched by
  convention).

- CI STALL (trap 13a, second sighting after #145): the push of the
  codex-fix head `f7ba81f` (14:57Z) and the one sanctioned empty-commit
  retrigger `eb53d40` (15:06Z) both spawned ZERO workflow runs (~25+
  min; get_check_runs total_count 0, actions_list shows the branch's
  last runs on `b943138`); per the #145 precedent the fix is the next
  REAL push — this stall-note commit is that push. Codex posted a
  usage-limit notice on the PR (the trap-14g class): no review reply
  will come; the posted @codex question satisfies Q-0259 regardless.

## 💡 Session idea

parity.yml's ai `seeded-catalog` row still says "migration-0029" from
the pre-renumber draft while its own comment block says 0030 — a
one-word doc fix for the next parity.yml-touching PR; not taken here to
keep this diff slice-scoped.

## ⟲ Previous-session review

The behavior-preset card (.sessions/2026-07-11-behavior-preset-slice.md,
PR #185 merge `168ef80`) named this slice's exact missing pieces and its
D-0070/D-0071 park wording scoped it without re-derivation; its
migration-renumber note (0029→0030 on a main collision) was the reason
this slice's migration took 0031 with a pre-flight number check. Same
friction as last time: oracle access is fragment-by-fragment (~35
search_code queries) and the default branch moved mid-reconstruction.
