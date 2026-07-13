# 2026-07-13 — diagnostic operator mutations (ORDER 017 fix slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1 follow-up (completeness table `docs/status/completeness-table-2026-07-13.md`, diagnostic row)

## Scope

Bring the diagnostic subsystem's 10 pending panel actions + 2 pending
selectors to production-ready (implemented + tested + golden-parity
preserved + final user-facing copy): the flag-manager mutations
(`pf_flag_pick` select + Enable/Disable), the automation-panel
mutations (`pf_auto_rule` select + Enable/Disable/Delete), the
Diagnostics-hub process-state trio (Bot Status / System Info / Recent
Errors), and the `!list_commands_detailed` ◀ Prev / Next ▶ paging
(pages 2–14). Port oracle: menno420/superbot (read-only clone at
/workspace/superbot). Existing diagnostic goldens (subsystem is
`ported` in parity/parity.yml) must stay byte-green on the bare opens.

## What shipped

PR #331 — zero `*_pending` routes remain in `sb/domain/diagnostic/`:

- **cmdlist pages 1–14** (`command_catalog.py` `COMMAND_LIST_PAGES`):
  oracle-extracted by a static class-level registry walk over the old
  bot's cogs (INITIAL_EXTENSIONS load order → `__cog_commands__`,
  `build_command_list_pages` re-applied). The walk reproduced page 1
  BYTE-IDENTICAL to the golden-pinned literal — the identity that
  certifies pages 2–14. ◀/▶ step via fresh re-open with `cmdlist_page`
  in the panel args; the renderer edge-disables both buttons (the
  shipped `_update_buttons`).
- **Flag Manager** (`flag_catalog.py` + handlers + pick-aware
  renderer): select → the shipped detail-embed shape over the
  verbatim-ported 8-flag declaration registry; Enable/Disable run the
  shipped guard ladder and refuse the silent no-op write with final
  copy (v1 has no flag consumer — the oracle's own "never offer a
  no-op control" rule, decision flagged in the PR body).
- **Automation panel**: pick tracked per (guild, invoker) (the
  counting `_manage_target` precedent); Enable/Disable/Delete answer
  the shipped guards — complete truthful behavior of the zero-rule
  world.
- **Process-state trio**: live successor reads keeping the shipped
  shapes — `process_state.py` (/proc CPU/RAM/uptime + disk),
  `log_buffer.py` (ported ring on the `sb` logger tree, installed at
  `cli()`), and the `install_gateway_census_reader` seam armed beside
  `install_ws_latency_reader` in `sb/app/main.py`.
- 26 new tests (`tests/unit/diagnostic_band/test_operator_mutations.py`),
  full suite 2089 passed / 2 skipped; `bootstrap.py check --strict`
  green (born-red hold only); all 43 diagnostic goldens replayed green
  on a clean local Postgres (`setup_local_env.py` +
  `_replay_corpus({"diagnostic"})` → red: 0). Completeness-table
  diagnostic admin cell ⚑ → ✅, Top-gaps #5 → DONE (same PR).

## 💡 Session idea

The oracle-extraction trick generalizes: a static class-level registry
walk over the oracle clone (import cog modules, never instantiate,
enumerate `__cog_commands__`) yields deterministic capture literals for
ANY registry-shaped surface, and a byte-compare against an existing
golden-pinned subset certifies the rest. Candidate next user: the
`admin.cogmgr_page_pending` select windows (pages 2/3 of the cog
roster — the exact same paginator family this slice retired for
cmdlist).

## ⟲ Previous-session review

Previous session (completeness table, PR #326) produced the exact map
this slice executes against — the diagnostic row's citation
(`sb/domain/diagnostic/handlers.py` `*_pending`) resolved in seconds,
no re-derivation needed; that is the table doing its job. Its card
also carried forward the `.substrate/guard-fires.jsonl` dirt warning —
honored here (restored before every commit). One friction for the
next lane: the local parity DB accumulates state across replays —
recreate `parity_replay` before trusting local golden results, or
39/43 false reds greet you (guard recipe: `tools/setup_local_env.py`,
then terminate sessions + DROP/CREATE DATABASE `parity_replay` via
`sudo -u postgres psql`, then `tools/run_golden_parity._replay_corpus`).
