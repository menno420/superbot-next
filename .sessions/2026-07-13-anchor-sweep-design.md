# 2026-07-13 — anchor-refresh sweep: proposed design record (docs-only)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · docs lane · mandate: convert the parked #341
  scoping finding (the anchor-refresh sweep needs four unmade design
  calls) into an owner-reviewable PROPOSED design record

## Scope

Docs-only. The game-sections slice-3 lane (#341) parked the promised
"anchor sweep" as a successor because scoping it surfaced four design
calls no agent should make alone: session-hub anchorability vs the
pinned no-anchor goldens, panel-id provenance missing from
`panel_anchors`, the absent anchor-editor adapter port, and the
subsystem→hub fan-out / rate-limit posture. This session verifies the
parked citations at HEAD, writes `docs/design/anchor-refresh-sweep.md`
as a PROPOSED (not decided) design record laying out each call with
options / recommendation / cost, links it from `docs/design/README.md`,
and claims the branch. No code, no migration, no golden, no D-number —
`docs/decisions.md`'s grammar is closed to `decided|superseded|retired`,
so the D-entry mints only when the owner decides.

## 💡 Session idea

[[fill at close]]

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-minigame-sections-2.md` @ de3824b — the
newest card at boot.) A complete close-out whose shipped list matches
the #337 merge diff (settings panel + hub group + routing + 14 tests +
the flagged settings-golden re-cut). Two things transferred directly:
its PL-001 flag pattern (name the convention that could NOT carry the
work — `f"{group}.hub"` vs the player hub — then state the honest
route) is the exact posture this doc uses for the decisions.md-status
question, and its layout-budget note ("adding a disable-all would cross
the sim-gate floor — deliberately not added") is the model for this
doc's cost lines: name the gate a choice trips, not just the choice.
One friction: the card cites design §5/§6 by number while the design
doc's section numbers shifted during review — this doc pins citations
to file:line at a named HEAD instead.
