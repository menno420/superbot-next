# 2026-07-13 — operator-hub edits C: admin cogmgr interaction slice (ORDER 017 fix slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1 (completeness table `docs/status/completeness-table-2026-07-13.md`, Top-gaps item 6 — admin cogmgr; sibling of slices A #355 / B #356)

## Scope

Slice C of the operator-hub EDIT-controls family: the admin Cog Manager's
wireable interaction terminals become live — the cog select (pick memory +
the shipped "Selected: cogs.<name>" footer swap + the "← selected"
roster marker) and the ◀ Prev / Next ▶ select windowing (the shipped
3-page 25-option windows with edge-disable). The Load/Unload/Reload trio
and the hub's Reload All stay their DELIBERATE by-design terminals
(docs/decisions.md — extension management has no analog in the compiled
architecture; the copy already states this and is final), reclassified in
the completeness table from "pending" to "by-design terminal".

## Coordination check

Same evidence set as slices A/B (PR #355/#356 bodies): the
`operator-hubs-interactive` claim covers read-only nav only; no peer claim
or PR touches sb/domain/admin.

## Previous-session review

Slices A (#355) + B (#356) established the lane's conventions: fresh
re-open pick memory (#331), renderer-override state surfaces (the cogmgr
footer/disabled precedent itself), golden-safety on bare opens.

## What shipped

PR #357 — `admin.cogmgr_select` + `admin.cogmgr_prev/next` live (the
shipped pick footer swap, `← selected` roster marker, 3-page 25-option
SelectWindow with edge-disable); Load/Unload/Reload + Reload All
reclassified BY-DESIGN in the completeness table per docs/decisions.md
(extension management has no compiled-architecture analog; copy final).
Verification: unit 2206 passed, integration 11 passed, golden gate GREEN
484/484 (bare `!coglist` bytes pinned by the new tests), sim-gate/compat
untouched-clean. CI: 13/14 green; `checkers` red was solely this card's
designed born-red hold (job log carries the explicit notice).

## 💡 Session idea

Renderer-override state surfaces need a leaf-matching convention: this
lane matched components by `custom_id.rsplit('.', 1)[-1]` in three
sibling renderers (cogmgr, channel grid, diagnostic). A kernel helper
(`rendered.component(leaf)`) would collapse the copies and survive a
future custom-id scheme change in one place.
