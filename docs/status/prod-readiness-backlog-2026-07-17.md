# Production-Readiness Backlog — superbot-next

> **Status:** `reference`
>
> Derived from a full-tree survey @ `1893d32` (2026-07-18). Product code is
> marker-clean (14 TODOs, all non-product; 1 by-design `NotImplementedError`;
> no bare `except:`; zero silent gaps per the completeness table). The backlog
> below is therefore **not** bug-cleanup — it is (A) owner-only operational
> cutover, (B) porting the remaining *declared-honest* pending terminals to
> full oracle parity, and (C) hardening + forward design.
>
> Each buildable item is written to be picked up **cold** by a fresh session:
> title, files, why-it-matters, size (S/M/L), dependency. Port items MUST
> byte-verify against the local oracle clone (`menno420/superbot`) via
> `tools/mint_golden.py` + `tools/run_golden_parity.py` — never fabricate a
> golden.

## A. Owner-only operational cutover (flag — NOT agent-buildable)

These are the true go-live blockers but require owner secrets / console access.
An agent cannot complete them; route to the owner queue.

- **A1 — Provision live production (Railway).** Set `DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`, `SB_DATA_PLANE=prod`, `SB_PROD_ATTEST`; run CUT-1→CUT-3 cutover. Ref `docs/NEXT-TASKS.md:32-39`. **Biggest single go-live blocker.** Owner-only.
- **A2 — Turn on the data safety net.** `BACKUP_ENABLED=true`, add `DATABASE_PUBLIC_URL`, raise artifact retention, confirm `restore-verify.yml`. Ref `docs/NEXT-TASKS.md:41-45`. No verified backup/restore = production risk. Owner-only.
- **A3 — Arm hermes egress + ai NL path.** hermes needs owner creds `CLAUDE_ROUTINE_FIRE_URL`/`CLAUDE_ROUTINE_TOKEN` (`sb/spec/config.py:197-204`); ai NL path needs `ANTHROPIC_API_KEY` (`parity.yml:361`). Both dark until keyed. Owner-only.

## B. Buildable port slices (agent-shippable, oracle byte-verified)

Ordered by value × tractability. Each is independently shippable behind the
audited seams. **Dependency for all:** local env booted (`pg_ctlcluster 16
main start`; `tools/setup_local_env.py`) + working golden pipeline.

- **B1 — mining vault deposit/withdraw write faces.** Files: `sb/domain/mining/panels.py:629` (vault_deposit_pending), `:634` (vault_withdraw_pending); service seam in `service.py`. Why: vault is core progression; users currently hit a refusal on deposit/withdraw. Oracle: `disbot` mining vault handlers. Size: M. Dep: env+goldens.
- **B2 — mining skill spend.** File: `sb/domain/mining/panels.py:749` (skill_spend_pending). Why: skill-tree spend is a primary sink; refusal blocks progression. Size: S–M. Dep: env+goldens.
- **B3 — mining workshop craft.** File: `sb/domain/mining/panels.py:1152` (workshop_craft_pending). Why: crafting is the mid-game loop. Size: M. Dep: B1/B2 helpful but independent.
- **B4 — mining !cook/!use energy lane.** File: `sb/domain/mining/service.py:1256` (loop generating `mining.{name}_pending` for argful-write faces). Why: largest single-subsystem write-gap; the text-command energy lane. Size: M–L. Dep: env+goldens.
- **B5 — fishing deep-system roster + minigame rung.** Files: `sb/domain/fishing/service.py:1613` (PENDING roster loop), `:1066` (`_FishingDoneView` cast-again continuation), bite/reel timing gate. Why: fishing is shipped live but the real-time minigame computes timing that never gates a catch; cast-again is dead. Fidelity gap on a user-facing surface. Size: L. Dep: env+goldens.
- **B6 — settings admin-audit surface.** Files: `sb/domain/settings/handlers.py:242` (group_pending), `panels.py:300` (defaults 9 actions + 2 selectors to `settings.{action_id}_pending`). Why: the hub advertises command-access matrix / audit view / health chips that all refuse. Size: M–L. Dep: env+goldens.
- **B7 — xp.config panel actions.** 4 actions (`xp.config_{range,cooldown,channel}_pending` + `xp.import_setup_pending`) per completeness table. Why: XP tuning only reachable via K7 settings workaround today. Size: M. Dep: env+goldens.
  > DONE (2026-07-18): already ported + landed on main (curation-rework chain, earliest introducing commit `46b545e`); verified at HEAD `1bcc8e3`. Panel `xp_config_spec()` `sb/domain/xp/panels.py:267` (renderer `_render_config` :441) registered in the manifest `sb/manifest/xp.py:156`; the 4 handlers are live in `sb/domain/xp/handlers.py` — `xp.config_range_submit` (:159), `xp.config_cooldown_submit` (:181), `xp.config_channel_submit` (:194), `xp.import_setup_submit` (:236); no `*_pending` terminals remain. Goldens `parity/goldens/xp/sweep_xpconfig.json` (+ sweep_xpimport, sweep_xpmenu) cover it under CI golden-parity. `tests/unit/band4/test_band4_xp.py` 25/25 green (incl. `test_retired_config_pendings_are_gone`). Oracle match: `disbot/views/xp/config_panel.py` XpConfigView. NOTE: the `!xpimport` channel-scan/preview-apply front door is a SEPARATE honest BLOCKED boundary, NOT covered by this note.
- **B8 — ux_lab wing interiors.** File: `sb/domain/ux_lab/handlers.py:50-62` (9 pending terminals: buttons/selects/modals/embeds/components_v2/pil_cards/mock_studio/probe_bench/compare). Why: the whole UX-lab interior is refusal-only. Size: L (can split per-wing into 9 micro-slices). Dep: env+goldens.
- **B9 — help editor home message.** File: `sb/domain/help/editor.py:612` (help.editor_home_message_pending). Why: small, self-contained; good warm-up port. Size: S. Dep: env+goldens.
- **B10 — role hub back-button route-origin signal.** Oracle `disbot/views/server_management/hub.py:169` ("↩ Server Management"). Why: a role manager opened from the server_management hub cannot route back — no route-origin signal exists. Decision-sized (needs a small cross-band origin token). Size: M. Dep: design note first.
- **B11 — server_management availability projection axis.** Files: `sb/domain/server_management/access_projection.py:75` (axis 5 "future — stubbed"), `:492` ("availability policy not implemented"). Why: a genuinely un-ported projection dimension. Confirm against oracle whether it exists there before building. Size: M. Dep: verify oracle has it.

## C. Hardening + correctness (no golden needed for most)

- **C1 — setup-band except-density audit.** ~60+ `except Exception:` across `sb/domain/setup/*` (final_review 13, essential_steps 11, launcher 9, wizard 7). Most carry `# noqa: BLE001 — FAIL CLOSED` intent, but audit that none silently swallow a real error; add the intent comment where missing; unit-test the fail-closed boundaries. Why: setup is fail-closed staging; a swallowed error there strands a server mid-provision. Size: M. Dep: none (unit tests only).
- **C2 — effect-leg compensation gaps.** Ref `docs/ideas/*-2026-07-10.md`, NEXT-TASKS #3. Close saga compensation gaps behind the audited seams. Size: M. Dep: read the ideas doc.
  > DONE (2026-07-18): closed by #105 (`842bafb`) and hardened further at the 2026-07-11 moderation parity flip. At HEAD `1bcc8e3` every EFFECT leg after a DB leg in `sb/domain/moderation/ops.py` + `sb/domain/proof_channel/ops.py` is `compensatable` with a wired compensator (`proof_channel.compensate_unlock` at `ops.py:173,261-262`; `moderation.timeout` restructured to NO effect leg, `ops.py:520-526`). Class-killer `tests/unit/workflow/test_compensator_invariant.py` ships an EMPTY `_ALLOWLIST` and is green — the defect class is unwritable.
- **C3 — ensure-only registration gaps.** Ref NEXT-TASKS #3. Make registration idempotent/ensure-only where currently create-only. Size: S–M. Dep: read the ideas doc.
  > DONE (2026-07-18): closed by #508 (`cbc3ab2`) — the last ensure-only ref (`panel:role.hub`) now registers at module import (`sb/domain/role/panels.py:362-386`). At HEAD `1bcc8e3` `_KNOWN_ENSURE_ONLY` in `tests/unit/invariants/test_composition_parity.py:35` is an EMPTY frozenset and `test_composition_parity.py` is green — no live-invisible refs remain.
- **C4 — tournament open-flag TOCTOU fix.** Ref NEXT-TASKS #2 (games backlog). Fix the open-flag time-of-check/time-of-use race in tournament open. Size: S. Dep: none.
- **C5 — setup compound-op apply seams.** Files: `sb/domain/setup/wizard.py:88,95,109` (create_managed_role / create_channel / set_cog_routing rows skip until seams exist). Why: wizard completes but these ops silently no-op — no live command-routing resolver in this build. Size: L (needs the resolver seam). Dep: design note first.

## D. Forward / planning ideas (feed to PLANNING mode)

Design proposals + roadmap for when buildable work thins. Land each as a
durable design doc under `docs/ideas/` before building.

- **D1 — themed card renderer.** Replace placeholder solid-panel PNGs (`sb/domain/xp/rank_card.py:13`, `sb/domain/utility/profile_card.py:11`) with a real themed renderer. Design: a shared render band (fonts/layout/theming) both cards + future cards draw from. Large; design-first.
- **D2 — real-time minigame framework.** Generalize the fishing bite/reel timing rung (B5) into a reusable minigame primitive other subsystems (mining, games) can adopt. Design-first.
- **D3 — command-access matrix / audit dashboard.** The settings-audit surface (B6) implies a durable access-control + audit-log model. Design the data model + panel taxonomy before porting piecemeal.
- **D4 — observability/metrics surface.** No production metrics/health dashboard is catalogued. Propose a minimal ops surface (uptime, command latency, error-rate, DB health) drawing on `sb/kernel/observability`.
- **D5 — integration/e2e test harness expansion.** Suite is 3,160 unit tests + golden parity; propose a live-guild smoke harness (Galaxy Bot test bot) that exercises real Discord round-trips for the ported bands.
- **D6 — autonomy-apparatus removal.** NEXT-TASKS #6: remove the deprecation-bannered `auto-merge-enabler.yml` + `control/` bus once the recreated Project is stood up (post-2026-07-21 EAP window). Deferred; owner-sequenced.

## How to pick up a slice cold

1. HARD-SYNC (`git fetch origin main && git reset --hard origin/main`).
2. Boot env: `pg_ctlcluster 16 main start` → `tools/setup_local_env.py` → confirm `tools/run_golden_parity.py --gate` green (523/523 baseline).
3. Attach the oracle read-only (`menno420/superbot`) and read the named oracle path for the slice.
4. Branch `claude/<slug>`; born-red card FIRST commit; PR READY at open.
5. Implement the handler; `tools/mint_golden.py` to capture the real oracle bytes; `tools/run_golden_parity.py` to verify parity — NEVER hand-write a golden.
6. Keep CI green (golden-parity workflow-level red is by-design; judge the required `gate` job). Flip card complete LAST.
