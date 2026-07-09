---
name: session-close
description: "End the session correctly — write the log, groom + add an idea, verify, commit, push, drive the PR to a terminal state."
---

# session-close

Close superbot-next's current session correctly.

1. Session log — write `.sessions/<date>-<slug>.md`: what changed, one new idea
   you genuinely believe in, and a one-line review of the previous session.
2. Capability delta — did you discover a new capability or hit a wall this
   session? Append it to `docs/CAPABILITIES.md` (dated, with the exact
   error or the proof it worked, plus any workaround).
3. Owner asks — every ⚑ needs-owner item you leave behind carries the
   OWNER-ACTION fields (WHAT / WHERE / HOW / WHY-IT-MATTERS / UNBLOCKS /
   VERIFIED-NEEDED — you attempted it, or you name the exact wall; see
   `control/README.md`). Withdraw stale asks; fewer, clearer asks beat
   complete lists.
4. Idea backlog — groom one idea forward (the ideas-README lifecycle).
5. Verify — run the project's checks: `python3 -m pytest` and `bootstrap check`.
6. Commit + push on the session branch; open the PR ready (not draft).
7. Drive the PR to a terminal state — merge on green CI, or close with a reason.

Declared capabilities: edit (the log + docs), run (the checks + git).
