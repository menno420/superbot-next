# superbot-next — Next tasks

> **Status:** `living-ledger`
>
> The owner-directed forward task list. This replaces the retired `control/`
> message bus (inbox / outbox / status) as the source of "what to build next".
> Ordered roughly by dependency, not strict priority — the owner directs; agents
> pick the next contained slice, open a ready PR, and let it land on green.
> Live state ("what is true now") is [`docs/current-state.md`](current-state.md).

## Build backlog

1. **Finish the port to full parity.** Work down
   [`docs/status/completeness-table-2026-07-18.md`](status/completeness-table-2026-07-18.md)
   (verify-first reconciliation; supersedes the
   [07-13 table](status/completeness-table-2026-07-13.md))
   and [`docs/ideas/port-the-small-four-2026-07-10.md`](ideas/port-the-small-four-2026-07-10.md)
   to close the gap from ~49 ported subsystems to the full corpus. The harness is
   ready — 523 goldens are green today (`tools/check_parity_depth.py`), so each new
   subsystem is a replay-to-green slice. With that surface essentially exhausted, the
   snapshot recommends a PLANNING-mode loop — the forward design proposals live in
   [`docs/design/README.md`](design/README.md) (the D1–D6 + B8/B10 design series).
   **D2 real-time minigame framework — DECIDED — DEFER-until-2nd-consumer
   (2026-07-20, recorded in the decisions ledger):** do not build the
   `RealtimeRound` kernel primitive for fishing alone; when a second real-time
   minigame is on the roadmap, build D2.1 (the pure extraction) first and grow
   the new game onto it. This was the LAST open owner block —
   [`docs/question-router.md`](question-router.md) now has **ZERO** open owner
   blocks (B10/S6/D2 all deferred; the 2026-07-18 agenda trimmed to its
   genuine-owner remainder — see the decisions ledger and
   [`OWNER-DECISIONS-2026-07-18.md`](design/OWNER-DECISIONS-2026-07-18.md)).

   - **Settings `group_pending` edit-page epic — ✅ essentially COMPLETE.** The
     per-group scalar-edit-page epic
     ([`docs/design/settings-group-pending-epic-plan.md`](design/settings-group-pending-epic-plan.md))
     is done for **every reachable scalar type**: S0 (page frame) + S1 bool / S2
     enum / S3 number-modal / S4 text-modal / S5 channel-select / S7
     numeric-presets have all landed or are landing (PRs #579–#584). The
     `settings.group_pending` blocked terminal is **fully retired** for every
     non-hub group (replaced by the live `settings.group_edit` page per the
     option-A ruling; the 5 operator-spine hub groups keep their read-only hubs
     by design). **The only open item is S6 (role-select)**, which is BLOCKED,
     not built: no reachable honest golden target exists — the port declares zero
     `input_hint="role"` settings, and the oracle's role settings live in
     `moderation` (unported) and `welcome` (a read-only hub, unreachable under
     option A). S6 is routed as a scoping question — see
     [`docs/question-router.md`](question-router.md) → Open questions → "settings
     epic S6 (role-select edit widget)" (recommend DEFER until a role-typed
     non-hub setting exists; the widget is ~1 slice once a target does).

2. **Land the scoped game-surface backlog.** ✅ **Essentially complete** — all
   three sub-items have either landed or are a settled do-not-fix:
   - **Blackjack remaining surface** — ✅ **DONE** (PR #551, squash `70b8a8a`,
     "blackjack: hub Solo buttons open the interactive table"). Scope doc:
     [`docs/ideas/blackjack-remaining-surface-2026-07-10.md`](ideas/blackjack-remaining-surface-2026-07-10.md).
   - **RPS remaining surface** — ✅ **DONE** (PR #552, squash `2804428`,
     "rps(solo): edit the picker message in place into the result embed"). Note:
     the `!rpsbot` bullet in
     [`docs/ideas/rps-tournament-remaining-surface-2026-07-10.md`](ideas/rps-tournament-remaining-surface-2026-07-10.md)
     was already built on main, so that idea doc is now stale.
   - **Tournament open-flag TOCTOU** — ✂️ **Struck (do-not-fix).** Settled by an
     explicit owner decision (decided 2026-07-18): keep the non-atomic
     accepted-posture, no atomic fence; PR #517 pinned it with a characterization
     test. Not pending work — the decision's canonical home is
     [`docs/decisions.md`](decisions.md); scope context lives in
     [`docs/ideas/tournament-open-flag-toctou-2026-07-12.md`](ideas/tournament-open-flag-toctou-2026-07-12.md)
     (`outcome: accepted-posture`).

3. **Close the documented correctness gaps.** Robustness work behind the audited
   seams, both already scoped:
   [`docs/ideas/effect-leg-compensation-gaps-2026-07-10.md`](ideas/effect-leg-compensation-gaps-2026-07-10.md)
   and [`docs/ideas/ensure-only-registration-gaps-2026-07-10.md`](ideas/ensure-only-registration-gaps-2026-07-10.md).

4. **Stand up live production.** Provision the Railway service pointed at this repo
   with the runtime secrets/vars (`DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`,
   `SB_DATA_PLANE=prod`, `SB_PROD_ATTEST`); run the CUT-1 → CUT-3 cutover; then
   execute the parked human-operator live-drive runbooks that were blocked on a
   gateway token in CI —
   [`docs/operations/live-drive-guild-effects.md`](operations/live-drive-guild-effects.md)
   and [`docs/operations/plugin-proof-live-drive.md`](operations/plugin-proof-live-drive.md).
   (Owner action: the secrets/vars and Railway service are owner-only steps.)

5. **Turn on the data safety net.** Set `BACKUP_ENABLED=true`, add the
   `DATABASE_PUBLIC_URL` secret, raise GitHub Actions artifact retention to 400
   days, and confirm `.github/workflows/restore-verify.yml` goes green. Rollback
   runbook: [`docs/operations/rollback-playbook.md`](operations/rollback-playbook.md).
   (Owner action: the repo secret + variable + retention setting are owner-only.)

6. **Replace the still-live autonomy apparatus with a plain direct-merge flow.**
   Keep the six named CI gates (`.github/workflows/named-gates.yml`) plus
   `pip-audit` (`.github/workflows/ci.yml`) as the merge bar; with the enabler
   gone, agents just **merge their own green PRs directly**
   (MCP/REST) — remove `.github/workflows/auto-merge-enabler.yml` and retire the
   `control/` order-bus + wake-chain so nothing self-fires a wake.
   **Correction (2026-07-18):** the enabler is currently **LIVE** (fires
   `on: pull_request`, no deprecation banner — the sole in-repo merge automation),
   NOT already retired; and `control/` is only **partially** removable — the
   `control/status.md` heartbeat + `control/claims` stay **load-bearing** (gated by
   the required `substrate-gate.yml --status-only`; `substrate.config.json` points
   `claims_dir` → `control/claims`), so only the inbox/outbox **order-bus** was
   retired. Naive `control/` deletion would RED a required gate — removal is
   owner-sequenced, with the kit-config migration first (per the D6 #548 plan).
   The doctrine is: open a ready PR on green CI, then merge it directly (agents
   merge their own green PRs — MCP/REST — with the enabler as a fallback until it
   is removed). This is a next-Project (recreation) change — the workflow files
   are left untouched by the 2026-07-17 cleanup pass.

## Executable backlog (2026-07-20 audit)

HONESTY GUARD: **no contained honest build slice is currently unblocked.** The
port surface is essentially exhausted and the honest-goldens rule forbids
shipping speculative dormant infra, so there is no "pick the next slice and land
it on green" work today. What remains:

1. **Owner-gated provisioning** — live prod (item 4: Railway service + runtime
   secrets), the data safety net (item 5: `BACKUP_ENABLED=true` + backup
   secret/retention), and the AI / btd6 access gates (OWNER-DECISIONS rows
   26–27: `ANTHROPIC_API_KEY` / NK data account). None is an agent action.
2. **Design engines awaiting a real consumer or owner-go** — D4 observability,
   D5 e2e/live-guild harness, R resilience/delivery hardening. Build the moment a
   real consumer or an owner go-ahead arrives; the reversible design postures are
   pre-recorded in the decisions ledger (the 2026-07-20 owner-agenda-audit entry)
   so the next Project inherits the answers. D2 (minigame framework) is DEFERRED
   until a 2nd real-time minigame; B10 route-origin until a 2nd consumer (both
   deferred, in the ledger). Decision ids are stamped once, in
   [`docs/decisions.md`](decisions.md).
3. **One routed cleanup** — the xp `_record_import` negative-level guard
   remove-vs-make-reachable call stays **OWNER-ROUTED** (a product call, see
   Cleanup leads below), not an autonomous slice.

## Cleanup leads

- [cleanup lead] `sb/domain/xp/ops.py` `_record_import` negative-level guard is
  dead via the public path (`reduce_max_levels` `-1` sentinel drops `level < 0`
  first, so `if level < 0: raise` never fires); decide remove-vs-make-reachable
  (owner/fuller-context call). Pinned by
  `tests/unit/band4/test_band4_xp_depth.py::test_import_negative_level_guard`.
  (surfaced PR #542)
