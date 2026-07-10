# 2026-07-10 — effect-leg compensation gaps captured (idea seed, #101)

> **Status:** `complete`

- **📊 Model:** not recorded (catch-up ender by a later session)

> **Catch-up note:** the session that shipped #101 (`ec356d2`) closed without a
> session log; this log was written after the fact by the session-close session
> (2026-07-10) from the merged content. What-shipped is read from the merge, not
> from memory.

## Scope

Route superbot's verification of the external (Codex/Sol) runtime review into
this repo's idea backlog: two verified DB-commits-before-uncompensated-EFFECT
ops plus the invariant that kills the class at authoring time.

## What shipped (#101, `ec356d2`)

1. `docs/ideas/effect-leg-compensation-gaps-2026-07-10.md` — the capture:
   `moderation.timeout` and `proof_channel.end_access` each commit a DB row
   before a `"reversible"` EFFECT leg with no compensator (verified against
   HEAD `04436ab`), plus the class-killer proposal (unit invariant over every
   registered `CompoundOpSpec`).
2. `docs/ideas/README.md` — backlog index line (`captured` → quick-win lane).
3. One stamp-guard fire recorded in `.substrate/guard-fires.jsonl` (D-0029
   double-cite), settled in-PR by switching to an indirect citation.

The seeded lane shipped the same day as #105 (`2c222e1`) — capture to merged
fix in under a day.

## 💡 Session idea

The idea file's frontmatter (`shipped_pr`/`state`/`outcome`) is the backlog's
tracker, but nothing makes the shipping session flip it — #105 shipped this
exact design and the file still says `shipped_pr: null` / `state: captured`.
The session that ships a seeded idea should flip the frontmatter in the same
PR; cheapest fence is a checker warning when a `captured` idea's named ops
gain the very tests it proposed.

## ⟲ Previous-session review

The idea-seeds session (#99, same night) filed its Session-idea ender as a
parenthetical pointing at its own deliverables — legal, but it shows the ender
can be satisfied without a forward-looking thought. This session then skipped
the log entirely, which is the stronger failure: the born-red-first-commit
rule only works if the log exists at all. The kit's session-log guard catches
an incomplete log but not a missing one for a merged PR.
