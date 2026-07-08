---
name: session-close
description: "End the session correctly — write the log, groom + add an idea, verify, commit, push, drive the PR to a terminal state."
---

# session-close

Close superbot-next's current session correctly.

1. Session log — write `.sessions/<date>-<slug>.md`: what changed, one new idea
   you genuinely believe in, and a one-line review of the previous session.
2. Idea backlog — groom one idea forward (the ideas-README lifecycle).
3. Verify — run the project's checks: `${verify_command}` and `bootstrap check`.
4. Commit + push on the session branch; open the PR ready (not draft).
5. Drive the PR to a terminal state — merge on green CI, or close with a reason.

Declared capabilities: edit (the log + docs), run (the checks + git).
