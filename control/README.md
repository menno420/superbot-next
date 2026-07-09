# Fleet coordination protocol — `control/`

> Local copy for this repo. Canonical spec: `menno420/superbot` →
> `docs/planning/fleet-coordination-protocol-2026-07-09.md` (§1). Projects cannot talk to each
> other directly — committed git files are the only shared medium; this directory is the bus.
> Protocol extensions below (per-lane heartbeats, order claiming, `kit:` line, OWNER-ACTION
> format) merged from substrate-kit v1.6.0's control template at the v1.6.0 upgrade.

## The two files
- `control/inbox.md` — ORDERS to this Project. **One writer: the manager** (appends via the
  GitHub Contents API). Never edit this file.
- `control/status.md` — STATE from this Project. **One writer: this Project** (overwrite it each
  session).

## The one rule that keeps it conflict-free
**One writer per file.** The manager is the sole writer of `inbox.md`; this Project is the sole
writer of its own `status.md`. Two writers never touch the same file, so there are no merge
conflicts. Everything is append-only / overwrite-own — forward-only git.

## Multi-Project repos — per-lane heartbeats (optional extension)

A SHARED repo can host several Projects ("lanes" — e.g. a mining lane and an exploration lane
cohabiting one game repo). The one-writer rule scales by **splitting the heartbeat, never by
sharing it**:

- **One status file per lane** — `control/status-<lane>.md` (e.g. `control/status-mining.md` +
  `control/status-exploration.md`). Each lane is the sole writer of its own file and overwrites
  it as its session's deliberate LAST step; no lane ever edits another lane's heartbeat.
- **`control/inbox.md` stays single** — the manager remains its one writer; a lane-specific
  order names its lane in `do:`.
- **Declare every lane heartbeat to the kit** — `substrate.config.json` →
  `"heartbeat_files": ["control/status-mining.md", "control/status-exploration.md"]` (default
  when unset: `["control/status.md"]`). The status checker then gates each listed file
  independently (missing / heartbeat-less lane = strict RED; per-lane staleness warns), and the
  Stop hook's overwrite reminder clears when any lane's heartbeat is fresh (it cannot know which
  lane a session belongs to). An empty list falls back to the default — misconfiguration never
  silently disables the gate.

## Per-session ritual (every session, and every routine wake)
- **FIRST:** git pull (a stale clone reads stale orders); read `control/inbox.md`; execute any
  order whose status is `new`, in priority order (P0 before P1) — **claim it first** (see
  "Claiming an order" below). An order's `do:` is a pointer to
  a committed doc — read it. If an order is ambiguous or you disagree, do NOT guess: write it in
  your status under `⚑ needs-owner` and proceed with the rest.
- **LAST (deliberate final step):** overwrite `control/status.md` — updated timestamp, current
  phase, health (green / red-by-design+why / broken+what), kit self-report, last-shipped PR,
  blockers, orders acked/done (with any active claim), `⚑ needs-owner`. You report order
  progress ONLY here; never edit `inbox.md` (the manager owns it — one writer per file).

## Claiming an order — one executor per order (claim FIRST, build second)

An order's `status: new` is visible to every session that wakes, so two readers can both
believe they are its executor — a realized failure, not a theoretical one (substrate-kit
PRs #50/#51: two lanes independently executed the same ORDER 005 the same day, and a whole
session's work had to be reconciled as twins). The manager only flips `new→done` after
seeing the status report; the claim covers the gap in between.

Before executing any `new` order:

1. **Re-read the bus at origin/main HEAD** — `control/inbox.md` AND every sibling status
   file (`control/status*.md`). If another lane's status already claims the order
   (`claimed-by:` naming its id) or reports it in `done=`, stand down and pick other work.
2. **Claim FIRST, on your own status file's orders line** — append
   `claimed-by: <order-ids> <lane-or-session> <ISO8601>` — and land it on **main** BEFORE
   any build work (a control-only fast-lane PR, or a direct commit where your rules allow
   one). A claim that exists only on a branch is invisible; only main counts.
3. **Re-read once more after the claim merges** — two claims can race in flight; the
   tiebreak is the earliest claim merged to main. The loser withdraws its claim line in
   its next status overwrite and stands down.
4. **Claims expire** — a claim with no visible build activity (no open PR, no fresh
   heartbeat referencing the order) after ~24h may be treated as abandoned and re-claimed;
   note the takeover in your status `notes:`. A dead lane must never deadlock an order.

With an active claim the `orders:` line reads e.g.:
`orders: acked=001-008 done=001-006 claimed-by: 007+008 coordinator-lane 2026-07-09T18:38Z`
— the executor drops the `claimed-by:` annotation in the overwrite that moves those ids
into `done=`. One writer per file is preserved: you only ever claim on your OWN status.
(Shipped by inbox ORDER 007 — the root-cause fix for the twin-execution failure; the
ritual was live-proven manually on substrate-kit's own orders before graduating here.)

## `status.md` format (what you write every session — your heartbeat)
```markdown
# <project> · status
updated: <ISO8601>            # heartbeat — stale = the manager treats the Project as dark
phase: <what I'm doing right now, one line>
health: green | red-by-design (<why>) | broken (<what>)
kit: v<X.Y.Z> · check: green|red · engaged: yes|no   # kit self-report — see below
last-shipped: #<PR> — <one line>
blockers: <what's stopping me, or `none`>
orders: acked=<ids> done=<ids> [claimed-by: <ids> <lane-or-session> <ISO8601>]
⚑ needs-owner: <a decision/action only the owner can give, or `none`>
notes: <anything the manager should know>
```

The `kit:` line is the **substrate-coordinator visibility** channel (kit-lab reads it via the
manager relay — zero write access to this repo): `v<X.Y.Z>` = the vendored kit version this
repo actually runs (update it in the same session as every `bootstrap upgrade`); `check:` =
the latest `check --strict` verdict on this tree; `engaged:` = the post-adopt engagement gate
(`yes` once no UNRENDERED banner/slot remains, live CI runs the gate, and the session loop
has engaged).

## ⚑ needs-owner — the OWNER-ACTION item format (quality contract)

The owner is the scarcest resource in the program: every ask routed to the owner costs
attention, and an unclear or unnecessary ask stalls your own lane on top of burning his.
**Before routing ANYTHING to the owner, try it yourself or cite the exact wall** — an
assumption-based ask ("agents probably can't do X") is banned; the bar is the capability
ledger (`docs/CAPABILITIES.md`) plus one real attempt with the captured error.

Every ⚑ needs-owner item carries ALL of these REQUIRED fields — inline on the item, or as a
structured block the item links to:

```markdown
⚑ OWNER-ACTION
WHAT: <one plain sentence, zero jargon — the thing the owner does>
WHERE: <exact click path or URL>
HOW: <paste-ready text/values where applicable, or "click only">
WHY-IT-MATTERS: <one sentence, in product terms>
UNBLOCKS: <what starts moving the moment it's done>
VERIFIED-NEEDED: <the attempt you made + the exact error/wall proving only the owner can do
this — never an assumption>
```

Hygiene: **expire or withdraw stale asks every session** (an answered or obsolete ask left in
the list is drift), and **fewer, clearer asks beat complete lists**. `check` warns — advisory,
never exit-affecting — when a non-`none` ⚑ needs-owner list lacks these fields.

## `inbox.md` order format (manager-written, append-only)
```markdown
## ORDER <nnn> · <ISO8601> · status: new     # manager flips new→done after seeing status done=
priority: P0 | P1 | P2
do: <pointer to a committed doc/section + the ask, kept short>
why: <one line>
done-when: <acceptance test>
```
