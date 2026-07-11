# 2026-07-11 — the behavior-preset slice (band 7, D-0071)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

The band-7 remaining map's first parked slice (D-0070: "the behavior
preset pickers — need the preset catalog + ai_instruction_profile +
`apply_preset` seam"). The behavior chooser's Channel / Category /
Preview pickers go LIVE on the armed component lanes; the Routing-matrix
button stays an honest pending terminal (its copy now names the
routing-matrix follow-up slice — views/ai/routing/matrix.py is a
distinct view, not one of D-0070's parked picker pair).

## What shipped

1. **migrations/0030_ai_instruction_profile.sql** — the oracle 039
   `ai_instruction_profile` CREATE (NAME_STABLE) with 043's `is_preset`
   folded in, the SEVEN oracle-044 system presets seeded VERBATIM
   (disabled / mention_only_helper / helpful_channel / btd6_focused /
   quiet_btd6_focused / staff_diagnostics / support_triage), and the
   shipped FKs added to `ai_channel_policy` / `ai_category_policy`
   `.instruction_profile_id` (ON DELETE SET NULL — the column 0028
   deliberately carried FK-less).
2. **sb/domain/ai/behavior_presets.py** — the
   `ai_behavior_profile_service` twin: the in-process catalog (shipped
   headlines + recommended modes, the uncatalogued-row fallback),
   `list_behavior_presets` / `describe_preset` reads, and
   `apply_preset` (scope roster {channel, category} →
   `InvalidBehaviorPresetScopeError`; unknown id →
   `UnknownBehaviorPresetError`; then ONE audited existing op —
   `ai.set_channel_policy` / `ai.set_category_policy` — with
   mode=recommended_mode + instruction_profile_id=preset_id and
   min_level/cooldown PRESERVED). NOTE: the shipped read name
   `list_presets` is taken by the aireview store twin in the flat
   sb/domain/ai package (K symbol-shadowing gate), so the port carries
   the qualified name.
3. **sb/domain/ai/policy_store.py** — the shipped PR-C-pre `UNCHANGED`
   sentinel lands on the channel/category upserts (an UNCHANGED column
   is neither inserted nor conflict-touched; the #177 modal lane, which
   always sends its keys, is byte-identical — pinned by test); preset
   reads (`list_preset_profiles`, `get_preset_profile`);
   `AI_INSTRUCTION_PROFILE_STORE` registered; the erasure detach grows
   the catalog's `created_by` column.
4. **sb/domain/ai/policy_ops.py** — the channel/category legs accept an
   optional `instruction_profile_id` (ABSENT param key → UNCHANGED) and
   re-check the id names a seeded `is_preset` row IN-TXN (§4.1 seam
   authority). No new ops, no new events; compensator allowlist stays
   EMPTY (single reversible DB leg, unchanged).
5. **sb/domain/ai/behavior_widgets.py + panels.py** — the four pages:
   `ai.behavior_channel_picker` / `ai.behavior_category_picker` (the
   shipped `_behavior_page_embed` bytes + "↩ AI Behavior" back-route;
   category rides the D-0070 roster string select capped at 25),
   `ai.behavior_preview_picker` (the shipped chooser REUSE of the
   policy `PreviewChannelSelectView` under behavior page bytes — same
   `ai.policy_preview_pick` handler), and `ai.behavior_preset_picker`
   (the shipped `build_preset_picker_embed` page; the select PICK
   applies immediately — the shipped callback had no modal — and acks
   the shipped byte ``✅ Bound preset `key` (mode `mode`) to scope
   **label**. mutation_id=`…`.``; unknown key → ``❌ Unknown preset
   `key`.``).
6. **parity/parity.yml** — NEW depth reason class `seeded-catalog`
   (decision record D-0071; the D-0069 vocabulary-growth pattern) + ONE
   exemption row `ai → table:ai_instruction_profile`: rows are minted
   only by the K3 migration seed (they precede every case's
   before-snapshot, so a per-case db_delta structurally cannot carry
   them) and the slice ships NO runtime write ingress. Ratchet
   UNTOUCHED; compat pin UNTOUCHED (no new commands/modals/events —
   trap 12d).
7. **docs/decisions.md** — D-0071 (the full verdict, deviations, and
   the trap-24 sha caveat: the oracle views were reconstructed from the
   default branch [e1090dbc→a03e5fe8 mid-reconstruction]; no golden
   pins these clicks).
8. **tests/unit/band7/test_band7_behavior_presets.py** — 15 tests: the
   three page-byte drives, the preset-page bytes (7 fields + options),
   channel/category applies through the recorded engine seam (the
   min_level/cooldown-ABSENT contract pinned), the unknown-key refusal,
   the K6 member gate, the catalog/fallback/apply_preset pure seams,
   the UNCHANGED SQL-seam test (modal lane column set byte-identical),
   and the in-txn profile re-check. Two sibling tests updated to the
   flipped shape (test_band7_ai_surface store/panel rosters; the
   settings-mutation skeleton's pending-copy test now drives the
   still-parked Routing matrix button).

## Verification (serial, local Postgres)

- units: `pytest tests/ -q` → **1388 passed / 2 skipped**
- gate: `run_golden_parity.py --gate` → **GREEN 175/175 across 32
  ported** (the slice migration applied by the harness boot)
- report: `run_golden_parity.py --report` → **212/465 green, 465/465
  replayable, 32/49 ported** (unchanged — no goldens move)
- POST-MERGE rerun (origin/main moved mid-session: the parallel wave-9
  diagnostic flip #183 `10bf073` + heartbeat #184 `73db26d`; the slice
  migration renumbered 0029→0030 on a number collision with main's new
  `0029_platform_migration_checkpoints.sql`, checksums/guard-fires
  keep-both, snapshot recompiled, fresh DB): units **1388/2**, gate
  **GREEN 212/212 across 33 ported**, report **249/465 green, 465/465
  replayable, 33/49** — every named gate clean again.
- named gates: manifest_compile (rewritten + verified green),
  check_parity_depth OK (49 subsystems, 465 goldens),
  check_namespace / check_sim_gate / check_compat_frozen /
  check_migrations (29) / check_escape_hatches / check_schema_growth /
  check_amendments / check_symbol_shadowing / check_no_skip /
  check_config_usage / check_metric_cardinality / check_egress /
  check_data_lifecycle / check_rollback_disposition — all clean.

## Honest notes

- The behavior surfaces are golden-UNPINNED (no imported golden drives
  any chooser click) — byte claims rest on search_code fragment
  reconstruction of the oracle's DEFAULT branch, which moved mid-session
  (e1090dbc → a03e5fe8) and can be ahead of the corpus sha 7f7628e1
  (trap 24; ledgered in D-0071).
- `apply_preset_to_guild` NOT ported — the oracle's own docstring parks
  it ("will unlock a future … helper if needed").
- The shipped views edited ONE anchor message in place; session pages
  re-open (the projmoon edit-in-place deviation class, unchanged).
- ORDER-004 live-drive leg: NOT run this session (no gateway drive
  attempted); the walking-skeleton suite carries the CI-runnable drive.
  The live drive rides the next live-testing pass (testing-report row 9
  stays untouched by convention).

## 💡 Session idea

The `seeded-catalog` class text names its own deletion trigger ("the
row dies when a runtime profile-mutation lane ships") — a cheap future
guard would be a checker rule that greps each seeded-catalog table for
op-leg writers and reds the exemption automatically when one appears,
so the deletion clause enforces itself instead of relying on reviewer
memory.

## ⟲ Previous-session review

The previous-session review: the band-7 wrap-up card
(.sessions/2026-07-11-band7-builder-session.md, PR #181 merge
`251e5d7`) left a clean remaining map and D-0070's parked terms were
precise enough to scope this slice without re-derivation — the only
friction was oracle access (fragment-by-fragment reconstruction, ~30
search_code queries) and a stale local git clone whose origin/main ref
had diverged (hard reset to origin/main resolved it; noted for the
coordinator).
