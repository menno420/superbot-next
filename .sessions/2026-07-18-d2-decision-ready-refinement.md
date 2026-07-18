# 2026-07-18 — D2 real-time minigame framework: sharpen into a decision-ready package

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red substrate-gate HOLD. First
> commit was this card alone (held the gate red); the D2 doc + router edits
> landed in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · medium · docs-only

## Goal

Land ONE docs-only slice that makes D2
(`docs/design/D2-realtime-minigame-framework.md`) **decision-ready** — one owner
go/no-go away from executable:

1. Refine the D2 doc IN PLACE with a **Decision-ready refinement** section: a
   recommended reusable-primitive shape (grounded in the fishing code it lifts),
   the six shape sub-questions resolved as flagged decide-and-flag defaults (each
   owner-overridable), and a crisp cost/unblock statement.
2. `docs/question-router.md` — append ONE crisp OPEN owner go/no-go entry (the
   single load-bearing "build the framework now / defer / never" call) with a
   RECOMMENDED DEFAULT + one-line honest rationale, marked OPEN pending owner.

## Scope

Docs-only. Two docs (D2 in place + a router `### Q:` block) + this card. No
`sb/` code touched — D2 stays a PLAN. The fishing determinism decision homed in
the D2 doc is referred to in prose only — **no `D-00NN` token minted or spread**
into the router or this card (stamp-gate respected: that token stays homed in
its one design doc).

## Verification (re-confirmed at HEAD this session)

- **Extraction source re-read against live code (HEAD `49775ab`):** the
  orchestration the primitive would lift is real and cited accurately — the
  logical-clock due-guard `_timer_due` (`sb/domain/fishing/service.py:131-143`),
  the identity-guarded cue timers `_arm_bite_timers` (`service.py:213-278`) and
  `_arm_fight_timers` (`service.py:281-324`), the idempotent
  `_cancel_cast_timers` (`service.py:124-128`), the outer `_sweep_expired_casts`
  (`service.py:360-368`), the per-case `reset_pending_casts_for_tests`
  (`service.py:371-376`), and the per-round identity token
  (`_next_cast_token`/`_cast_token_counter`, `service.py:349-357`). The pure
  per-game leaves the template shows (`sb/domain/fishing/minigame.py`) and the
  two composed kernel seams (`sb/kernel/panels/timers.py`,
  `engine.py` `push_session_refresh`) are unchanged by the proposal. All D2
  citations verify.
- **Question triage:** all six of D2's open questions are **mechanical shape
  decisions** (proving ground, fishing-adoption timing, window/refresh budget,
  multi-round modelling, band home, turn-timeout scope) → resolved as flagged
  decide-and-flag defaults in the doc's new refinement section. The single
  load-bearing owner call is the **umbrella go/no-go** that sits above all six —
  *build the reusable primitive now vs defer vs never* — routed to
  `question-router.md`. Recommendation: **DEFER-until-2nd-consumer** (fishing is
  the only real-time minigame today ⇒ one consumer), same one-consumer logic as
  the B10 recommendation, but with the honest caveat that D2's boilerplate is
  determinism-critical (a 2nd game will re-derive it by hand and can silently get
  it wrong) so D2.1 should be built *first* the moment a 2nd real-time minigame
  is actually on the roadmap.
- **pytest:** `python3 -m pytest -q --ignore=examples` → **3495 passed, 29
  skipped, 1 warning** in 86.69s (docs-only; `examples/` excluded per the
  standing plugin-example import gap).
- **docs-gate:** `python3 bootstrap.py check` → **exit 0**; no unreachable/badge
  finding for the refined D2 doc or the router (both already reachable from
  `design/README.md` / the router's own Open-questions table). Pre-existing
  advisory warnings only (owner-action / claims / seat-digest / automerge-drift /
  model-line-class on OTHER cards) — none mine, none exit-affecting. The gate
  correctly held on this card while it was born-red (missing close-out markers);
  this flip clears it.

## Trail

- **D2-realtime-minigame-framework.md:** added a `## Decision-ready refinement`
  section (before the verbatim-kept `Open questions` list) with (a) the single
  routed owner call framed explicitly, (b) a recommended framework shape that
  points at F1–F4 and re-grounds each lifted piece in its fishing symbol, (c) a
  six-row **decide-and-flag defaults table** (Q1 reflex-casino proving ground /
  Q2-shape leave fishing as reference / Q3 per-game window knob + platform floor
  + cue-edit ceiling / Q4 single-shot first-class with a re-arm hook / Q5
  `sb/kernel/panels/minigame.py` home / Q6 turn-timeouts out of scope), each with
  an override lever, and (d) a cost/unblock paragraph (D2.1 is a pure zero-churn
  addition; unblocks any future real-time minigame; exactly one existing
  consumer — fishing — refactors onto it, and only optionally). Added a
  triage-status note atop the kept Open-questions list.
- **question-router.md:** appended ONE OPEN `### Q:` block in Open questions —
  the D2 build-now/defer/never go/no-go with options (GO / DEFER / NEVER) and the
  recommended **DEFER-until-2nd-consumer, then GO-D2.1-first** default + honest
  rationale (distinguishing it from B10: D2's extraction is determinism-critical,
  not cosmetic). Maintainer answer + routing result left `(pending)`. Rewrote the
  Open-questions header note from "One unanswered block" to "Two". No other
  blocks touched (append-only respected).
- **design/README.md:** no change needed — the D2 row already exists (`plan`
  status) and this slice edits the doc in place, so reachability is unaffected.
- No `sb/` code touched — this is a PLAN refinement (decide-and-flag), not built
  code; it makes D2 executable-pending-one-owner-decision.

## 💡 Session idea

D2's six "open questions" were all shape questions that *presupposed* the build —
the actual load-bearing call (build-at-all/now) was never one of the six, it sat
implicit above them. This is the same triage shape B10 needed. A cheap
recurring-pattern guard: a planning-doc convention where an `## Open questions`
list must separate **shape** questions (mechanical, defaultable) from the
**premise** question (should we build this at all) — and a `tools/` lint that
flags a design doc whose open-questions list has no explicitly-marked premise
question, since a proposal that only asks *how* and never *whether* hides its
real owner gate. Anchor: the `## Open questions` heading in `docs/design/*.md`;
the smell is N questions all downstream of an unstated go/no-go.

## ⟲ Previous-session review

This slice is a direct reuse of the 2026-07-18 B10 decision-ready-plan session
(`.sessions/2026-07-18-b10-decision-ready-plan.md`, `complete`, PR #566): the
same docs-only shape — triage a proposal's questions into one routed owner
go/no-go + mechanical decide-and-flag defaults, born-red-card-then-flip, a
verification section that re-reads every citation against live code. Two useful
carries from its previous-session review chain: (1) route the single premise
question through the router's native `### Q:` convention, not a minted `D-00NN`
token, keeping stamp-gate clean; (2) its 💡 warned that plan docs minting bare
`D<n>` local labels collide with the `D1`–`D6` series namespace — heeded here by
adding no local decision labels at all and referring to the fishing ruling in
prose. Reusing the B10 structure kept this slice fast and audit-clean.
