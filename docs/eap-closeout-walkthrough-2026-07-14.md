# EAP close-out walkthrough — superbot-next (2026-07-14)

> **Status:** `owner-guidance`
>
> The one document to review this seat from: what shipped, what's true
> right now, every click the owner owes, a 5-minute tour, and the
> handoff. Depth lives in the
> [EAP project audit](audits/eap-project-audit-2026-07-14.md) — this
> page links, it does not restate. Live facts verified 2026-07-14
> ~11:27–11:30Z at origin/main `7e3a488`; anything weaker is marked
> unverified.

## A. What this seat did — the EAP in this repo

Seven days (2026-07-08 → 07-14): the full seven-band rebuild ported —
466 PRs opened, 448+ merged, ~1 PR per 20 minutes — measured and
sourced in the [audit](audits/eap-project-audit-2026-07-14.md) §1.
Thematic highlights, one or two flagship PRs each:

- **Parity/golden harness** — canonical one-command golden mints
  ([#416](https://github.com/menno420/superbot-next/pull/416)), the
  money-race checker false-green fix
  ([#425](https://github.com/menno420/superbot-next/pull/425)), and the
  golden-parity **report** leg reaching full-corpus 484/484 live green
  ([run 29238825392](https://github.com/menno420/superbot-next/actions/runs/29238825392)).
- **Mining port waves** — the five-PR write-parity WP stack
  ([#312](https://github.com/menno420/superbot-next/pull/312)→[#371](https://github.com/menno420/superbot-next/pull/371),
  §C item 1), the energy core
  ([#320](https://github.com/menno420/superbot-next/pull/320)), and
  windowed-select grammar past Discord's 25-option cap
  ([#435](https://github.com/menno420/superbot-next/pull/435)).
- **Fishing** — the kernel one-shot timer + push-edit seam for the
  minigame (ledger entry 0090;
  [#460](https://github.com/menno420/superbot-next/pull/460) +
  [#462](https://github.com/menno420/superbot-next/pull/462)) and the
  midnight weather-golden date-rot fix
  ([#448](https://github.com/menno420/superbot-next/pull/448)/[#449](https://github.com/menno420/superbot-next/pull/449)).
- **Casino spec + section** — the first-party
  [casino section spec](specs/casino-section-spec.md) (ORDER 031 hook)
  over the ported casino engine (`sb/domain/casino/`); the
  section-swap build is in flight as
  [#477](https://github.com/menno420/superbot-next/pull/477).
- **Curation** — all 1088 commands/components measured in one report
  ([#327](https://github.com/menno420/superbot-next/pull/327) →
  [curation report](review/curation-report-2026-07-13.md): KEEP 918 /
  REWORK 110 / DROP 60), burned down by the night bundles
  ([#428](https://github.com/menno420/superbot-next/pull/428)/[#434](https://github.com/menno420/superbot-next/pull/434))
  and [#476](https://github.com/menno420/superbot-next/pull/476).
- **Control-plane / kit adoption** — the auto-merge enabler
  ([#321](https://github.com/menno420/superbot-next/pull/321)), the
  manifest `stable_hash` conflict-class kill
  ([#386](https://github.com/menno420/superbot-next/pull/386)), and the
  substrate-gate born-red card hold in CI
  ([#479](https://github.com/menno420/superbot-next/pull/479), merged
  as main `7e3a488`).

## B. Current state

**What works right now** (baseline detail:
[current-state.md](current-state.md)): all seven port bands built,
boots to RUNNING on real PostgreSQL, unit suite green, the checker
fleet + six required named gates green on main, and the golden-parity
report leg live green at 484/484 since 2026-07-13
([run 29238825392](https://github.com/menno420/superbot-next/actions/runs/29238825392)).

**How to verify it yourself** (full runbook:
[local-verification.md](operations/local-verification.md)):

```bash
python3 tools/setup_local_env.py   # idempotent Postgres roles/DBs + env printout

export DATABASE_URL='postgresql://parity:parity@localhost:5432/parity_replay'
export SB_DATA_PLANE=test
export SB_TEST_DB_HOSTS=localhost

python3 -m pytest tests/ -q                  # never bare pytest at repo root
python3 tools/run_golden_parity.py --gate    # full corpus replay
python3 tools/run_golden_parity.py --report  # oracle-diff report leg
python3 bootstrap.py check --strict          # kit substrate checks
```

Expected: pytest ends `3113 passed, 15 skipped` (last verified run:
`.sessions/2026-07-14-order-022-verify-1-5.md`); the gate prints
`GREEN — all ... golden(s) ... replay clean`; the report leg is
484/484; `bootstrap.py check --strict` exits green (a handful of
pre-existing claims advisories are non-exit-affecting). There is no
`fleet_status` tool in this repo — that is fleet-manager-side.

**In progress / where parked** (live 2026-07-14 ~11:27Z):

- [#473](https://github.com/menno420/superbot-next/pull/473)
  title-equip write slice — `checkers` FAILED at 11:14:15Z
  ([run 29328152752](https://github.com/menno420/superbot-next/actions/runs/29328152752)),
  everything else green; labeled do-not-automerge. In progress, not
  terminal.
- [#479](https://github.com/menno420/superbot-next/pull/479)
  substrate-gate CI hold — **landed** as main `7e3a488` (~11:28Z,
  observed at this doc's branch cut).
- WP stack
  [#312](https://github.com/menno420/superbot-next/pull/312)→[#317](https://github.com/menno420/superbot-next/pull/317)→[#335](https://github.com/menno420/superbot-next/pull/335)→[#344](https://github.com/menno420/superbot-next/pull/344)→[#371](https://github.com/menno420/superbot-next/pull/371)
  — all-green, mergeable-clean, parked for the owner click-sweep BY
  DESIGN ([control/status.md](../control/status.md):30).
- [#392](https://github.com/menno420/superbot-next/pull/392) (energy
  slice 3, base wp3) and
  [#476](https://github.com/menno420/superbot-next/pull/476) (row 72 +
  farm goldens, base wp7) — all-green with auto-merge armed; they
  retarget to main and land themselves after the sweep.
- [#466](https://github.com/menno420/superbot-next/pull/466) fishing
  Cast-again and
  [#477](https://github.com/menno420/superbot-next/pull/477)
  casino/arcade/world section swap — all green, frozen
  do-not-automerge under the WP-stack freeze
  ([control/status.md](../control/status.md):17); the coordinator
  sends the go-to-flip after the sweep (§C, last note).
- [#474](https://github.com/menno420/superbot-next/pull/474) control
  claim for the ORDER 022 casino lane — open.
- Cross-repo:
  [superbot#2058](https://github.com/menno420/superbot/pull/2058)
  (FLAG 1 read-relay, draft, all green, merges clean) and
  [superbot#2061](https://github.com/menno420/superbot/pull/2061)
  (FLAG 2 HMAC write endpoint, draft, checks green but CONFLICTED —
  the 2-hourly dashboard cron re-dirties it; §C item 3).
  [superbot-plugin-hello#2](https://github.com/menno420/superbot-plugin-hello/pull/2)
  open, clean, no CI on that repo.

## C. OWNER ACTIONS — one sitting

Work top to bottom; items 1–4 are clicks, 5–7 are decisions, 8 is the
standing tail.

1. **Sweep-merge the WP stack, in order:**
   [#312](https://github.com/menno420/superbot-next/pull/312) →
   [#317](https://github.com/menno420/superbot-next/pull/317) →
   [#335](https://github.com/menno420/superbot-next/pull/335) →
   [#344](https://github.com/menno420/superbot-next/pull/344) →
   [#371](https://github.com/menno420/superbot-next/pull/371).
   All five are all-green and mergeable-clean (heads dc35d48 · 259176d
   · b548687 · e6553a7 · 91bc32f,
   [control/status.md](../control/status.md):30). The heartbeat ⚑2
   also says "then #320" — **already done**: #320 merged
   2026-07-13T13:54Z ([audit](audits/eap-project-audit-2026-07-14.md)
   §4). VERIFY: [#392](https://github.com/menno420/superbot-next/pull/392)
   and [#476](https://github.com/menno420/superbot-next/pull/476)
   auto-retarget to main and land themselves. Expect a TRANSIENT
   parity blip on main until #392 lands: the WP-2/WP-3 goldens were
   minted before migration 0052 widened `mining_player_state`, so on
   the merged schema their pinned rows gain the
   `energy`/`energy_updated_at` columns (columns-only diff, replies
   unchanged) — #392 carries the re-mints
   ([PR #392 body, § Goldens](https://github.com/menno420/superbot-next/pull/392)).
2. **Merge
   [superbot-plugin-hello#2](https://github.com/menno420/superbot-plugin-hello/pull/2)**
   (one-line kit_version 1.13.0→1.15.0; independent non-author review
   PASS on record; agent merge was classifier-denied — heartbeat ⚑0).
   VERIFY: fm `gen_kit_versions.py` renders the plugin-hello row OK at
   the next regen (⚑0's own done-when).
3. **Flip + merge the mineverse drafts**
   [superbot#2058](https://github.com/menno420/superbot/pull/2058) and
   [superbot#2061](https://github.com/menno420/superbot/pull/2061)
   (merge = live Railway deploy within minutes).
   **Recommendation: flip+merge #2058 first (it is clean, no dashboard
   delta), then have #2061's conflict resolved fresh —
   `scripts/resolve_generated_conflicts.py` during a merge of main (or
   ask the mineverse lane for a fresh resolve) — and flip+merge it
   within ~2h, before the 2-hourly dashboard cron re-dirties it**
   ([control/status.md](../control/status.md):36). VERIFY: Railway
   deploys; BOTH features stay dormant until the env vars are set —
   paste-ready names:

   ```
   FLAG 1 (superbot):  MINING_SNAPSHOT_RELAY_URL
                       MINING_SNAPSHOT_RELAY_GUILD_ID
   FLAG 2 (superbot):  MINING_WRITE_SHARED_SECRET
                       MINING_WRITE_GUILD_ALLOWLIST
   FLAG 2 (mineverse): MINING_WRITE_ENDPOINT
   ```
4. **Make `substrate-gate` a required status check** — #479 landed
   (main `7e3a488`), so the check now runs on every PR; requiring it
   makes the born-red card hold blocking. Open
   [branch protection settings](https://github.com/menno420/superbot-next/settings/branches)
   (or the rules page) and add this context to the required checks:

   ```
   substrate-gate
   ```

   VERIFY: a PR whose in-diff session card is still `in-progress`
   shows a RED required `substrate-gate` check (this very PR
   demonstrates it before its card flips).
5. **Ratify the curation DROP list** — 60 proposed retirements,
   report-only until ratified:
   [curation report § DROP](https://github.com/menno420/superbot-next/blob/main/docs/review/curation-report-2026-07-13.md#drop--proposed-retirements-report-only-nothing-deleted)
   (from [#327](https://github.com/menno420/superbot-next/pull/327),
   merged 2026-07-13T02:23:43Z). Every row carries a one-line evidence
   citation. **Recommendation: ratify** — the list is dominated by
   deploy-ops relics and dead UI the port deliberately did not carry.
   VERIFY: your ratification (an order/inbox line is enough) unblocks
   a retirement lane; until then nothing is deleted.
6. **Make the anchor-refresh call (ledger entry 0083)** — proposal
   merged via
   [#346](https://github.com/menno420/superbot-next/pull/346), doc:
   [design/anchor-refresh-sweep.md](design/anchor-refresh-sweep.md).
   **The doc's own recommendation (§7): IF you want the sweep, take
   the bundle (a3) explicit `anchorable` spec flag + (b1) `panel_id`
   column + (c) the anchor-editor adapter port + (d) resolver install
   at boot with per-(guild,panel) debounce — and it names do-nothing
   (a4) as genuinely viable, since next-interaction consistency
   already guarantees no user ever acts on a stale roster.** VERIFY:
   ledger entry 0083 minted in [decisions.md](decisions.md) citing the
   doc
   (a do-nothing decision is also a decision), and the doc's badge
   flips to `plan` or `retired` (doc §8).
7. **ORDER 001 test-bot token** — if still wanted: live-testing beyond
   bands 1–4 stays parked owner-side on the test-bot token
   (heartbeat ⚑6 "ORDER 001 token run";
   [current-state.md](current-state.md) § In flight). The
   guild-effect and plugin live-drive legs are human-operator runbooks:
   [live-drive-guild-effects.md](operations/live-drive-guild-effects.md),
   [plugin-proof-live-drive.md](operations/plugin-proof-live-drive.md).
   VERIFY: a band-5+ live-drive session produces its evidence card in
   `.sessions/`.
8. **Standing tail** (verbatim from
   [control/status.md](../control/status.md):40-42):
   - ⚑5 "SBW inventory+spec for sections (SIM-REQUEST 00:55Z,
     unanswered)" — answer or retire the request.
   - ⚑6 "settings-prune ratification; OWNER-ACTION 3
     (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete
     scratch/union-test-a,-b; … hermes egress creds
     (CLAUDE_ROUTINE_FIRE_URL + token)". The merge-queue click alone
     retires the audit's #5 remaining pain
     ([audit](audits/eap-project-audit-2026-07-14.md) §9.5, §10.1);
     branch deletion is a repo setting ("Automatically delete head
     branches") or two clicks on the branches page.
   - ⚑7 cosmetic banner strings — **no action needed**: verified
     done-already via
     [#393](https://github.com/menno420/superbot-next/pull/393)
     (repo-wide grep proof in
     `.sessions/2026-07-14-order-022-verify-1-5.md`); the heartbeat
     line is stale.

*After the sweep (agent-side, not yours):* the coordinator sends the
go-to-flip and the frozen
[#466](https://github.com/menno420/superbot-next/pull/466)/[#477](https://github.com/menno420/superbot-next/pull/477)
land themselves — you don't touch those.

## D. The 5-minute tour

In order, one stop a minute:

1. [audits/eap-project-audit-2026-07-14.md](audits/eap-project-audit-2026-07-14.md)
   — the whole week, evidence-pinned: scale (§1), walls (§3), merge
   friction (§4), self-fixes (§8), remaining pains (§9).
2. [specs/casino-section-spec.md](specs/casino-section-spec.md) — what
   a first-party spec looks like here, over the ported engine:
   [`sb/domain/casino/engine.py`](../sb/domain/casino/engine.py) (+
   `game.py` / `table.py` / `panels.py` in the same package).
3. The review pair —
   [review/games-finalization-2026-07-13.md](review/games-finalization-2026-07-13.md)
   (per-game verdicts + ranked extend/improve lists) and
   [review/curation-report-2026-07-13.md](review/curation-report-2026-07-13.md)
   (all 1088 rows, one verdict each).
4. The section machinery on main —
   [`sb/domain/games/sections.py`](../sb/domain/games/sections.py) +
   [`sb/domain/games/sections_panel.py`](../sb/domain/games/sections_panel.py),
   with the declared swap point `GAME_SECTIONS` at
   [`sb/manifest/games.py`](../sb/manifest/games.py):78 (the seam
   [#477](https://github.com/menno420/superbot-next/pull/477) swaps).
5. A green golden-parity gate on main —
   [run 29255726433](https://github.com/menno420/superbot-next/actions/runs/29255726433)
   (success, head dc0e73d); the report-leg milestone is
   [run 29238825392](https://github.com/menno420/superbot-next/actions/runs/29238825392)
   (484/484).
6. [control/status.md](../control/status.md) — the heartbeat: phase,
   open PRs, the ⚑ needs-owner list §C just walked.

## E. Handoff — what the next phase needs

**Batons (the working grammar):**
[control/status.md](../control/status.md) is the one-writer heartbeat,
overwritten every session; claims discipline lives in
[control/claims/README.md](../control/claims/README.md) — claims land
on main FIRST (a branch-only claim protects nothing); the WP-stack
freeze protocol ([control/status.md](../control/status.md):17):
corpus-moving slices park green under the freeze and flip after the
owner sweep.

**Open threads:**

- The parked/frozen PR set in §B — WP sweep unblocks #392/#476
  automatically and #466/#477 via go-to-flip; #473 needs its
  `checkers` red fixed.
- Conform sweep — gated on the WP merge
  ([audit](audits/eap-project-audit-2026-07-14.md) §11 "Parked at
  close").
- Curation REWORK tail — effectively rows 26 and 72
  ([audit](audits/eap-project-audit-2026-07-14.md) §1 backlog); row 72
  lands with [#476](https://github.com/menno420/superbot-next/pull/476),
  row 26 is WP-lane-owned. The ranked extend/improve backlogs per game
  live in
  [review/games-finalization-2026-07-13.md](review/games-finalization-2026-07-13.md).
- Automation runtime consumer — uncited, per dispatch (no repo-local
  citation found at `7e3a488`).
- DROP retirement lane + anchor-call (entry 0083) slice work — both
  unblock on §C items 5–6.

**Key doctrine in the fleet team memory** (fleet-side directory, not
in this repo — named here so the next seat looks them up):

- *superbot-dashboard-json-churn-conflicts* — the generated-dashboard
  conflict class and its mechanical resolver
  `scripts/resolve_generated_conflicts.py`
  ([superbot#2072](https://github.com/menno420/superbot/pull/2072));
  this is why §C item 3's ~2h window exists.
- *manifest `stable_hash` removal* —
  [#386](https://github.com/menno420/superbot-next/pull/386) killed
  the two-PR recompile conflict class; local write-up:
  [operations/manifest-snapshot-conflicts.md](operations/manifest-snapshot-conflicts.md).
