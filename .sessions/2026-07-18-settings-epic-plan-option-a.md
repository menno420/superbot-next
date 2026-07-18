# 2026-07-18 — settings group_pending epic plan: land option-A owner decision + executable slice plan

> **Status:** `in-progress`
>
> Born-red as the session's FIRST commit (card alone), holding the
> `substrate-gate` red while the two docs land; flips to `complete` as the
> deliberate LAST commit once the close-out is written (per
> `.sessions/README.md`).

- **📊 Model:** [[fill: model]]

## Goal

Land ONE contained docs-only slice recording the now-made owner decision on the
`settings.group_pending` per-group scalar-edit page, and turning the scoped
epic into an executable clean-slice plan:

1. `docs/question-router.md` — mark the OPEN settings per-group edit-page
   group-routing question (appended in #558) ANSWERED with the maintainer's
   **option A** ruling: the ported edit page replaces `group_pending` for the
   **non-hub groups only**; the 5 operator-spine hub groups
   (welcome / counters / security / automod / image_moderation) keep routing
   to their `<group>.hub`. Record the provenance line and route the answer
   into the new plan doc.
2. `docs/design/settings-group-pending-epic-plan.md` — a NEW planning doc: the
   S0→S7 slice breakdown for the settings-mutation epic, built onto the
   existing seams, incorporating the option-A decision.

## Scope

Docs-only. Two docs + this card. No `sb/` code touched. No decision-ID
(`D-00NN`) token minted (the file's native token is `Q-`; concrete answered
entries carry descriptive `### Q:` titles without own numbers).

## Provenance

Owner directive relayed via the coordinator session on 2026-07-18 (~21:20Z):
**option A** — edit page for non-hub groups only; the 5 hub groups unchanged.
Per the never-wait rider, silence = consent; this is a decide-and-flag record
(PL-001).

## Verification

- [[fill: pytest tail]]
- [[fill: docs-gate / bootstrap check result — new design doc Status badge reachable]]

## Trail

[[fill: trail]]

## 💡 Session idea

[[fill: idea]]

## ⟲ Previous-session review

[[fill: previous-session review]]
