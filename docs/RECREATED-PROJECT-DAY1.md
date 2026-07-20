# Recreated-Project — Day 1 runbook

> **Status:** `binding`
>
> The successor's first-session orientation. `main` is the durable artifact that
> carries across the read-only window (the durable-artifact decision, stamped in
> the `docs/decisions.md` ledger); this doc makes day 1 trivial. Source files
> always win over this doc.

## Purpose

The Claude Code Projects EAP surface goes **read-only Tue 2026-07-21**. This
Project is recreated fresh afterward. Nothing carries across the cutover except
what is committed to `main` — the branch is the durable artifact per the
durable-artifact decision stamped in the `docs/decisions.md` ledger (the D6
removal-deferral entry). This runbook records exactly what
day-1 state is, where the live pointers are, and the one owner prerequisite that
is still open, so the successor's first session starts from truth instead of
re-derivation.

## What carried across (state at cutover)

- **`main` SHA at cutover:** `1cec1b8efaeff74240392effd37ea5530cf09eda`
  (merge of PR **#601** — the decision-audit pass; ledger entries dated
  2026-07-20 in `docs/decisions.md`).
- **Test suite:** **3660 passed / 54 skipped**, latest run recorded in
  `.sessions/2026-07-20-decision-audit.md:81`
  (`python3 -m pytest -q --ignore=examples`). Verify by reading that card.
- **Golden corpus:** **526 / 526** (`tools/check_parity_depth.py`; 49/49
  subsystems ported + kernel). Disk count via `parity/goldens/*/*.json` = 526.
- **Decision ledger:** current through the 2026-07-18 owner-agenda-audit entry
  (the ledger's latest, `docs/decisions.md`). One ledger id is **intentionally
  reserved-unminted** — an owner anchor call, not a gap (see the ledger).
- **Session cards:** all flipped complete (`.sessions/`).

## Boot — successor's first session

Follow `.claude/CLAUDE.md` orientation, in order:

1. **Hard-sync** onto origin's HEAD: `git fetch origin main && git reset --hard
   origin/main` (a warm clone can lag origin).
2. `CONSTITUTION.md` — the autonomy rails.
3. `docs/current-state.md` — what is true right now.
4. `docs/NEXT-TASKS.md` — the live, owner-directed task list.

The `control/` message bus is **retired** (ORDER 024, `control/inbox.md:323-327`):
inbox / outbox / status / claims and the wake-chain doctrine are wound down. The
live task list is `docs/NEXT-TASKS.md`; live state is `docs/current-state.md`.
**Do not resurrect the retired bus** and do not issue orders through it.

## D6 apparatus removal — deferred to this Project

The durable-artifact / removal-deferral decision (stamped in `docs/decisions.md`)
deferred **every** step of
`docs/design/D6-autonomy-apparatus-removal.md` to this recreated Project. Read
that doc; its ordered removal sequence (each an independent, single-`git revert`
step) is:

- **S0 / Step 0** — Confirm the replacement merge path (non-destructive go/no-go):
  agents merge their own green PRs directly (MCP/REST); no in-repo lander
  workflow exists; read the "Allow auto-merge" setting; confirm no open PR
  depends on the enabler.
- **S1 / Step 1** — Neuter `auto-merge-enabler.yml` in place (banner + disable),
  keep the file; prove a PR still lands via the Step-0 path. Reversible.
- **S2 / Step 2** — Delete `auto-merge-enabler.yml` after S1 proved the path.
- **S3 / Step 3** — Migrate kit config off `control/` (`claims_dir`,
  `heartbeat_files`, `automerge`) via a `bootstrap` re-render or coordinated kit
  edit, **before** any `control/` deletion, so `substrate-gate` never reds.
- **S4 / Step 4** — Delete the `control/` bus (README, inbox, outbox, status,
  claims/) after S3; optionally preserve as history (tag / archive).
- **S5 / Step 5** — Repoint the doctrine docs that still cite `control/`
  (`CONSTITUTION.md`, `docs/reading-path.md`, `docs/status/README-first.md`,
  `docs/owner-profile.md`) before their targets vanish.
- **S6 / Step 6** — Delete `docs/ROUTINES.md` and repoint
  `docs/AGENT_ORIENTATION.md:38`.
- **S7 / Step 7** — Final verification: `python3 -m pytest` + `python3
  bootstrap.py check --strict` green, a fresh PR lands, no dangling `control/` /
  enabler / ROUTINES reference in live docs.

**Live owner-only prerequisite (one):** confirm the repo **"Allow auto-merge"**
setting posture (Step 0 / open question Q4) — this determines whether deleting
the enabler is a live merge-flow change or already-inert cleanup.

The owner prerequisites that were previously listed against these steps were
**completed on 2026-07-18 and are no longer blockers** (verified at cutover:
the two previously-named residual triggers are absent from the account registry
per `docs/current-state.md:67-73`; the four previously-named orphan merged
branches are absent from origin). Broader orphan merged-branch cleanup (~50+
`claude/*` heads; 54 measured on origin at cutover) **remains blocked by the
GitHub 403 ref-delete wall** and needs an owner/admin.

## Owner agenda

The trimmed **13-row owner agenda** is recorded in the `docs/decisions.md`
ledger (the 2026-07-18 owner-agenda-audit entry) — the rows retained as
genuinely owner-only (irreversible / external / secrets / money / console /
product-intent): **5, 7, 8, 9, 10, 22, 23, 24, 25, 26, 27, 30, 31**. Source
agenda: `docs/design/OWNER-DECISIONS-2026-07-18.md`. Reversible design-posture
rows were adopted as-recommended in the same entry (each a one-line reversal).

## Open forks for day 1

- **(a) The xp-guard fork** — `sb/domain/xp/ops.py` `_record_import`
  negative-level guard is dead via the public path (`reduce_max_levels` `-1`
  sentinel drops `level < 0` first, so `if level < 0: raise` never fires). The
  **remove-vs-make-reachable** call stays **owner-routed** (a product call), not
  an autonomous slice. Pointer: `docs/NEXT-TASKS.md:127-137` (Cleanup leads);
  pinned by `tests/unit/band4/test_band4_xp_depth.py::test_import_negative_level_guard`
  (surfaced PR #542).
- **(b) PR #576** (branch `claude/routines-wake-chain-reauth`) is **parked,
  owner-attended** (`control/status.md:15`). A PR does **not** carry across as a
  branch into the recreated Project — only `main` survives the cutover. So if
  #576 is still open at cutover, its payload must be **re-landed from the PR body
  text** in the new Project; there is no branch to resume.
