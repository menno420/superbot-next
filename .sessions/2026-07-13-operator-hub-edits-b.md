# 2026-07-13 — operator-hub edits B: channel hub sub-panels over live channel ops (ORDER 017 fix slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1 (completeness table `docs/status/completeness-table-2026-07-13.md`, Top-gaps item 6 — channel hub, 5 actions; sibling of slice A, PR #355)

## Scope

Slice B of the operator-hub EDIT-controls family: the channel hub's five
pending action terminals (`channel.{create,delete,restrict,move,
visibility}_pending`) become the shipped sub-panels
(disbot/views/channels/: create/delete/restrict/move/visibility — the
D-0030 named successor), wired to the LIVE ChannelActions/Directory ports
and the governance visibility op the command twins already ride.

## Coordination check

Same evidence set as slice A (PR #355 body): the
`operator-hubs-interactive` claim covers read-only nav only; edits
deferred → this lane's. No peer claim or PR touches sb/domain/channel
panels (#332 touches server_management/mining/utility only).

## Previous-session review

Slice A (PR #355) landed the pipeline: modal compat pins, snapshot
recompile, fresh-re-open interaction pattern (#331 precedent), sim-gate
layout locks for above-floor panels (the #340 legacy-seed exempt recipe).

## What shipped

PR #356 — the five `channel.*_pending` hub terminals retired: the
shipped sub-panels (create/delete/restrict/move/visibility + the
20-toggle visibility grid) live over the ChannelActions/Directory ports
and the audited governance visibility op. Per-(guild,invoker) pick
memory + fresh re-open (the #331 class); state fields + live-aggregate
toggle glyphs ride renderer overrides. Two honest port-extension
refusals flagged (reorder top/bottom; create-new-category). Verification:
full suite 2229 passed (3 legacy channel-hub tests updated to the live
world in-PR), golden gate GREEN 484/484 on clean local Postgres,
sim-gate green via legacy-seed exempt lock entries for the three
above-floor panels, compat +1 modal id. CI green across 13/14 checks;
`checkers` red was solely this card's designed born-red hold.

## 💡 Session idea

The sim-gate legacy-seed recipe is scriptable: derive the [A]
assignments from `check_sim_gate.manifest_assignments()` and write the
lock entries mechanically (this session did — zero hand-typed values,
zero overlay-masks-manifest risk). Candidate kit helper:
`check_sim_gate --seed-exempt <subsystem:anchor> --reason '…'`.
