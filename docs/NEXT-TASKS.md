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

2. **Land the scoped game-surface backlog.** All three are already analyzed and
   ready to become PRs behind the audited seams:
   [`docs/ideas/blackjack-remaining-surface-2026-07-10.md`](ideas/blackjack-remaining-surface-2026-07-10.md),
   [`docs/ideas/rps-tournament-remaining-surface-2026-07-10.md`](ideas/rps-tournament-remaining-surface-2026-07-10.md),
   and the tournament open-flag TOCTOU fix
   [`docs/ideas/tournament-open-flag-toctou-2026-07-12.md`](ideas/tournament-open-flag-toctou-2026-07-12.md).

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
   Keep the six named CI gates (`.github/workflows/named-gates.yml`) as the merge
   bar; with the enabler gone, agents just **merge their own green PRs directly**
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

## Cleanup leads

- [cleanup lead] `sb/domain/xp/ops.py` `_record_import` negative-level guard is
  dead via the public path (`reduce_max_levels` `-1` sentinel drops `level < 0`
  first, so `if level < 0: raise` never fires); decide remove-vs-make-reachable
  (owner/fuller-context call). Pinned by
  `tests/unit/band4/test_band4_xp_depth.py::test_import_negative_level_guard`.
  (surfaced PR #542)
