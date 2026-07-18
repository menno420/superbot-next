# 2026-07-18 — rps solo result view edit-in-place (the message-edit presenter seam)

> **Status:** `in-progress`
>
> Born-red FIRST commit (this card + the claim) — holds the HOLD gate red so
> parallel sessions see the in-flight work and the lander waits. The
> implementation + tests land in the second commit; the deliberate LAST commit
> flips this badge to `complete`.

- **📊 Model:** [[fill:model-family · effort · task-class]]

## Scope

Item 2 of `docs/ideas/rps-tournament-remaining-surface-2026-07-10.md` — the
**solo result view edit-in-place**. The shipped `views/rps/solo_play._RpsView`
EDITED the picker message into the result embed; v1's `rps_tournament.quickplay`
move buttons dispatch the audited `rps.solo_play` op DIRECTLY (a `WorkflowRef`
action with `ResultRender.RESULT_CARD`) and answer with a `followup_send` TEXT
line — the picker message is left untouched. The idea doc named the blocker as
"needs a message-edit presenter seam"; that seam now exists
(`refresh_session_view`, built for PvP/match/botmatch — the blackjack
`table_click` precedent is identical).

Route the quickplay move buttons through a new `rps.solo_click` handler that
runs `rps.solo_play` then `refresh_session_view` — editing the picker message
IN PLACE into the result embed (move vs bot move + the leg's own result copy,
verbatim), the single throw terminal so the session expires with the move
buttons disabled. The shipped "play again" button is the ledgered deferral —
hub re-entry stays one `!rps` away (the item-1(b) PvP terminal posture).

Contained to `sb/domain/rps/`; mirrors the blackjack solo `table_click`
edit-in-place shape exactly. DB-free additive/updated tests.

## Deliver

- [[fill:handler + panel wiring delivered]]
- [[fill:renderer result stage delivered]]
- [[fill:tests updated + golden wire shape]]

## Verification

- [[fill:pytest result tail]]

## Deviation ledger

- [[fill:brief-vs-tree deviations]]

## Close-out

- [[fill:PR # + URL, branch, CI]]

## 💡 Idea

[[fill:one genuine idea]]

## ⟲ Previous-session review

[[fill:one-line previous-session review remark]]
