# superbot-next — Next tasks

> **Status:** `living-ledger`
>
> The owner-directed forward task list. This replaces the retired `control/`
> message bus (inbox / outbox / status) as the source of "what to build next".
> Ordered roughly by dependency, not strict priority — the owner directs; agents
> pick the next contained slice, open a ready PR, and let it land on green.
> Live state ("what is true now") is [`docs/current-state.md`](current-state.md).

## Build backlog

1. **Planning phase — the port's clean-mint surface is exhausted.** The
   verify-first reconciliation
   ([`docs/status/completeness-table-2026-07-18.md`](status/completeness-table-2026-07-18.md);
   supersedes the [07-13 table](status/completeness-table-2026-07-13.md), and the
   [small-four](ideas/port-the-small-four-2026-07-10.md) mints it tracked) found the
   small mintable re-points all **closed** — B2/B3 (#527/#532) landed, joining C1 and
   the wizard docstring fix (#526/#538). What remains OPEN is no longer single-mint
   work: one LOW-priority larger surface (**B8** ux_lab, an admin-only zero-write dev
   tool), the **settings.group_pending** per-group edit-page **EPIC** (multi-slice;
   the group-routing question is decided option A, #563 —
   [`docs/design/settings-group-pending-epic-plan.md`](design/settings-group-pending-epic-plan.md)),
   and two non-mintable items (**B10** route-origin engine signal; **btd6** NK
   ingestion). 523 goldens stay green (`tools/check_parity_depth.py`), but there is no
   clean mint left to point at — so the loop has shifted to a **PLANNING-mode** cadence
   with two lanes:
   - **(a) owner-gated forward proposals** — the D1–D6 forward lanes + the
     S / O / R / B8 / B10 tracks ([`docs/design/README.md`](design/README.md)), each a
     design doc the owner reacts to and prioritizes. The open questions are
     consolidated, prioritized by leverage, in
     [`docs/design/OWNER-DECISIONS-2026-07-18.md`](design/OWNER-DECISIONS-2026-07-18.md);
     D1 Slice 1 (render band, #560/#561) and D4 P1 (outbox metrics, #562) are the first
     landed slices off these lanes.
   - **(b) small self-initiated improvements** — contained, reversible cleanups an agent
     can land without an owner decision (drift-prevention refactors like the canonical
     `ALL_METRICS` seam #565, docs reconciliation, and the cleanup leads below).

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
