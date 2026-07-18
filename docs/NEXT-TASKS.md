# superbot-next — Next tasks

> **Status:** `living-ledger`
>
> The owner-directed forward task list. This replaces the retired `control/`
> message bus (inbox / outbox / status) as the source of "what to build next".
> Ordered roughly by dependency, not strict priority — the owner directs; agents
> pick the next contained slice, open a ready PR, and let it land on green.
> Live state ("what is true now") is [`docs/current-state.md`](current-state.md).
> Forward-planning proposal queue (owner reprioritizes, coordinator dispatches):
> [`docs/status/roadmap-2026-07-18.md`](status/roadmap-2026-07-18.md).

## Build backlog

1. **Finish the port to full parity.** Work down
   [`docs/status/completeness-table-2026-07-13.md`](status/completeness-table-2026-07-13.md)
   and [`docs/ideas/port-the-small-four-2026-07-10.md`](ideas/port-the-small-four-2026-07-10.md)
   to close the gap from ~49 ported subsystems to the full corpus. The harness is
   ready — 523 goldens are green today (`tools/check_parity_depth.py`), so each new
   subsystem is a replay-to-green slice.

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

6. **Replace the retired autonomy apparatus with a plain owner-directed flow.**
   Keep the six named CI gates (`.github/workflows/named-gates.yml`) as the merge
   bar, but **merge by owner action** (or a simple server-side lander on green) —
   remove `.github/workflows/auto-merge-enabler.yml` and drop the `control/`
   message bus + wake-chain so nothing self-arms auto-merge or self-fires a wake.
   Agent-side auto-merge / REST-merge is classifier-denied since ~2026-07-15, so
   the doctrine is now: open a ready PR on green CI, the owner merges. This is a
   next-Project (recreation) change — the workflow files are left untouched by the
   2026-07-17 cleanup pass.
