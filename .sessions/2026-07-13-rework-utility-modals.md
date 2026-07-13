# 2026-07-13 — curation rework: utility panel Poll/Remind modal ingress

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · curation rework lane (ORDER 017 item 2 successor;
  evidence: `docs/review/curation-report-2026-07-13.md` L1356-1357 +
  consolidated backlog L1557) · mandate: arm the utility panel's 📊 Poll and
  🔔 Remind Me buttons via G-10 modal ingress onto the LIVE command-twin
  lanes, retiring the two pending terminals

## Scope

The curation report's two REWORK rows for `utility.panel`: both buttons
route to pending terminals (`utility.poll_pending`,
`utility.remind_pending`, sb/domain/utility/handlers.py:464-465) while the
command twins are live and golden-backed — `!poll` (`utility.poll_view`,
handlers.py:354, golden sweep_poll.json) and `!remind`
(`utility.remind_view`, handlers.py:375, golden sweep_remind.json). Rework:
each button opens a declared ModalSpec (the moderation/general G-10
precedent) whose submit normalizes the form fields into the SAME code path
the command twin runs — shared outcome helpers extracted from the
argv-shaped views, no duplicated parsing/formatting, no new egress
capability (poll's valid lane still ends on the honest `_POLL_DOWN`
refusal; remind's on the pinned ack copy). The two pending registrations
retire. Wire bytes stay golden-pinned verbatim (labels/styles; session
panels mint `<cid:N>` ids) — no golden re-cut; the snapshot recompiles for
the handler/modal manifest change.

Adjacency: PR #332 (claude/curation-rework-nav-wiring) touches the SAME
`sb/domain/utility/panels.py` row-1 region for the Invite one-liner — this
lane does not touch the invite lines or the row-1 lead comment.

## Close-out

(pending)

## 💡 Session idea

(pending)

## ⟲ Previous-session review

(pending — covers `.sessions/2026-07-13-anchor-sweep-design.md`)
