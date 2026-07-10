---
state: promoted
origin: consumer:menno420/superbot
shipped_pr: null
shipped_repo: menno420/superbot-next
merged_date: 2026-07-10
outcome: shipped
---

# Reaction adapter — the missing feed seam (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (gen-2 night-prep seed by the grand-review session).
> **Origin:** grand review gap map (superbot `docs/eap/gen1-grand-review-2026-07-09.md`
> §2) — verified: no reaction adapter exists anywhere in `sb/adapters/discord/` or
> `sb/app/` (only `message_feed` + `component_feed`).

**One line:** build the raw-reaction adapter (add/remove events → the kernel's dispatch
rail, mirroring `message_feed`'s shape) — the one seam blocking three shipped-oracle
surfaces: starboard, reaction-role sign-ups, and the AI-review 👎 listeners.

> **SHIPPED** (band-6 rps-tournament-orchestration PR, 2026-07-10):
> `sb/kernel/interaction/reactions.py` (named-consumer registry +
> never-raise dispatch) + `sb/adapters/discord/reaction_feed.py`
> (`on_raw_reaction_add`/`remove` → the seam; bot-reactor guard verbatim),
> armed unconditionally in the composition root (reactions intent is
> non-privileged). First consumer: `rps.tournament_signup` (✅ on the live
> registration message). Starboard / reaction-roles / AI-review 👎 remain
> pure-domain successor consumers — register at module import, no adapter
> work left.

**Why it's a seam, not a subsystem:** the oracle's reaction consumers are independent
domains; the adapter is the shared substrate they all bind to. Building it *before* any
of the three consumers keeps each consumer PR pure-domain — same layering discipline as
the component feed.

**Design notes for the session that takes it:** follow `message_feed.py`'s
intent-marker/degrade posture (reaction intents may be off in a guild — DEGRADE loudly,
never silently); goldens for reaction flows don't exist yet in `parity/` — mint the
starboard goldens from the oracle when the first consumer ports.

**Size:** medium (adapter + tests; consumers are separate PRs).
