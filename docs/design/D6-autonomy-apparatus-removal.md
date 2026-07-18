# D6 — Autonomy-apparatus removal (safe removal sequence)

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the D1–D6 lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`). This is a PLAN
> that PROPOSES a removal sequence — it does **not** execute any removal. The
> removal itself is owner-sequenced and deferred to the recreated Project
> (post-2026-07-21 EAP window) per `docs/NEXT-TASKS.md` item #6. The code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line`
> at HEAD `92710e2` unless noted.

## TL;DR

The retired autonomy apparatus — the `auto-merge-enabler.yml` workflow, the
`control/` message bus (inbox / outbox / status / claims), and the wake-chain
doctrine in `docs/ROUTINES.md` — is **half-retired**: the docs carry retirement
banners, but the machinery is still on disk and **partially still live**. Two
facts make a naive `rm` unsafe:

1. **The enabler is NOT bannered and its triggers are live.** Unlike the
   `control/` docs, `.github/workflows/auto-merge-enabler.yml` carries **no**
   deprecation banner and still fires `on: pull_request` at
   `opened/reopened/ready_for_review/synchronize`
   (`.github/workflows/auto-merge-enabler.yml:39-40`). If the repo's "Allow
   auto-merge" setting is ON it may still be arming squash auto-merge on
   `claude/*` PRs today.
2. **`control/` is load-bearing for a required gate.** `control/status.md` is
   the kit heartbeat that `substrate-gate.yml` gates via
   `python3 bootstrap.py check --strict --status-only`
   (`.github/workflows/substrate-gate.yml:52`), and `substrate.config.json`
   still points `claims_dir` at `control/claims`
   (`substrate.config.json:"claims_dir": "control/claims"`). Deleting `control/`
   before migrating that kit config **reds a required check**.

So the removal must be **ordered** — confirm the replacement merge path, migrate
kit config off `control/`, then delete — with each step an independently
revertible PR. This doc proposes that sequence. It executes nothing.

## Problem / context

`docs/NEXT-TASKS.md:50-57` (item #6) directs: keep the six named CI gates as the
merge bar, but **merge by owner action (or a simple server-side lander on
green)** — remove `auto-merge-enabler.yml` and drop the `control/` message bus +
wake-chain "so nothing self-arms auto-merge or self-fires a wake." It explicitly
files this as **a next-Project (recreation) change** and records that "the
workflow files are left untouched by the 2026-07-17 cleanup pass."

The doctrine that replaces the apparatus is already written and binding:

- `CONSTITUTION.md:76-87` (§ Autonomy rails): "landing (merge) is an explicit
  owner / server-side action" — "Agents do NOT arm GitHub auto-merge and do NOT
  merge via the REST/MCP API — that path has been classifier-denied since
  ~2026-07-15."
- `docs/current-state.md:145-155` (§ Review rhythm): "a PR lands via the repo's
  server-side lander workflow the moment CI is green, or the owner merges it …
  In the recreated Project the plan is a plain owner-merge on green (retire
  `auto-merge-enabler.yml`)."

The apparatus's current, honest state — item by item, with file evidence:

### Item A — `auto-merge-enabler.yml` (LIVE, un-bannered)

- Present at `.github/workflows/auto-merge-enabler.yml` (10,878 bytes). Its
  header documents provenance (fleet-owner directive, "fleet-manager inbox ORDER
  029", adapted from idea-engine) and its INERT-until-repo-settings conditions
  (`:24-33`).
- **No deprecation banner** — a `retir|deprecat|wind-down|superseded` grep over
  the file returns nothing, in contrast to every `control/` doc.
- **Live triggers**: `on: pull_request` /
  `types: [opened, reopened, ready_for_review, synchronize]` (`:38-40`).
- Arms native squash auto-merge on the prefix allowlist
  `claude/ port/ mining/ test/ docs/ fix/` unless labeled `do-not-automerge`
  (the `if:` guard, `:60-67`), gated behind a refuse-to-arm-on-zero-required-
  contexts guard (`:69-84`) and an in-progress-card SKIP guard (`:112-176`).
- Whether it still *functions* depends on the repo's "Allow auto-merge" setting
  (owner UI) — the workflow itself runs server-side on GitHub Actions, so the
  ~2026-07-15 classifier denial (which bites *agents* arming via MCP/REST) does
  **not** disable it. This is an owner question (see below).

### Item B — the `control/` message bus (retired-in-doc, still on disk, load-bearing)

- `control/README.md` (11,977 B) — RETIRED banner (`control/README.md:1-9`); the
  protocol spec. Cited by `CONSTITUTION.md:114,119` as the OWNER-ACTION-format
  and owner-assist standard.
- `control/inbox.md` (37,306 B) — manager ORDERS. **No retirement banner** (its
  header is the standard one-writer note, `control/inbox.md:1-3`).
- `control/outbox.md` (18,376 B) — RETIRED banner (`control/outbox.md:1-4`).
- `control/status.md` (2,408 B) — RETIRED banner (`control/status.md:1-8`), but
  **still the kit heartbeat** gated by `substrate-gate.yml:52`.
- `control/claims/` — `README.md` + 4 live claim files
  (`claude-test-depth-role.md`, `help-home-message-builder.md`,
  `test-depth-server-management.md`, `test-depth-xp.md`); the directory
  `substrate.config.json` `claims_dir` points at.

### Item C — the wake-chain doctrine (`docs/ROUTINES.md`)

- `docs/ROUTINES.md` (5,711 B) — RETIRED banner + `> **Status:** historical`
  (`docs/ROUTINES.md:1-9`). Self-wake / pacemaker / failsafe-cron doctrine, kept
  as historical record. Routed to from `docs/AGENT_ORIENTATION.md:38`.
- Residual **live** triggers exist outside the tree: `control/status.md`'s
  ⚑ needs-owner names two enabled "SuperBot 2.0 failsafe wake" duplicates
  (`trig_01E86nBnXqesQTwm6WA4mSUD`, `trig_01UC7wiV3n5Vgs3RpSQt4gWz`) awaiting
  owner disarm via the routines UI. These are console-only (owner action), not
  in-tree files.

## Goals / non-goals

**Goals**

- Produce a **safe, ordered, independently revertible** removal sequence for the
  apparatus that never reds a required gate mid-flight.
- Identify every dependent reference so nothing dangles after deletion.
- Separate what is genuinely dead from what is **still load-bearing** and must
  stay (or be migrated first).

**Non-goals**

- **Executing the removal now.** This is owner-sequenced and deferred to the
  recreated Project (post-2026-07-21). This doc changes no workflow, config, or
  `control/` file.
- Rewriting the historical/audit/retro record. Dated snapshots that cite
  `control/@<sha>` (audits, retros, testing reports) are evidence and stay as
  written.
- Changing the six named gates (`named-gates.yml`) — they remain the merge bar.
- Disarming the residual wake triggers — that is an owner UI action tracked in
  `control/status.md` § ⚑ needs-owner, not an in-tree removal.

## Removal inventory

**To remove (in-tree):**

| # | Path | Bytes | State today |
|---|---|---|---|
| A | `.github/workflows/auto-merge-enabler.yml` | 10,878 | LIVE, un-bannered |
| B1 | `control/README.md` | 11,977 | retired-banner; cited by CONSTITUTION |
| B2 | `control/inbox.md` | 37,306 | un-bannered; ORDER record |
| B3 | `control/outbox.md` | 18,376 | retired-banner |
| B4 | `control/status.md` | 2,408 | retired-banner; **kit heartbeat (load-bearing)** |
| B5 | `control/claims/` (README + 4 claims) | — | `claims_dir` target |
| C | `docs/ROUTINES.md` | 5,711 | historical banner |

**Kit config that references the above (must be migrated, not blind-deleted):**

- `substrate.config.json` → `"claims_dir": "control/claims"` — orphaned by B5.
- `substrate.config.json` → `"automerge": { "branch_patterns": ["claude/*"],
  "required_context": "substrate-gate" }` — kit automerge config, adjacent to
  the enabler's intent (A).
- `heartbeat_files` (default `["control/status.md"]` per `control/README.md`) —
  the file `substrate-gate.yml:52` (`check --strict --status-only`) gates;
  orphaned by B4. **This is the load-bearing coupling** — deleting B4 without
  first repointing/clearing `heartbeat_files` reds the substrate-gate.
- These three keys are **kit-owned** (`bootstrap.py` / `.substrate` machinery),
  so the migration is a `bootstrap` re-render or a coordinated kit edit, not a
  free-hand change (open question 6).

**Live doctrine docs that CITE `control/` as a current standard (repoint before
deletion):**

- `CONSTITUTION.md:114,119` — cite `control/README.md` as the OWNER-ACTION-format
  and owner-assist standard. Deleting B1 orphans these citations; the format
  must first move to a surviving home.
- `docs/reading-path.md:25,41,50` — routes work "through the coordination bus
  (`control/README.md`)" and reads sibling `control/status.md` heartbeats in the
  fleet map.
- `docs/status/README-first.md:31,35` — names `control/status.md` as the live
  status ledger.
- `docs/ROUTINES.md:8,100` — references `control/status.md` (self-referential;
  removed with C).
- `docs/owner-profile.md:15` — describes the **old** auto-merge flow ("PRs …
  auto-merge (squash) the moment the six required named checks are green");
  stale doctrine to update when A is removed.
- `docs/AGENT_ORIENTATION.md:38` — routes trigger/routine/wake work to
  `docs/ROUTINES.md`; repoint when C is removed.
- `docs/NEXT-TASKS.md:5,53-56` — the removal order itself + "replaces the retired
  `control/` bus"; update the framing once removal lands.

**References that must be LEFT ALONE (historical/evidence, or non-load-bearing):**

- All of `docs/audits/*`, `docs/retro/*`, `docs/review/*`,
  `docs/status/*-report-*.md`, `docs/eap-closeout-walkthrough-2026-07-14.md` —
  dated snapshots citing `control/@<sha>` and the enabler as historical record.
  Rewriting them would falsify the record.
- `sb/adapters/parity/runner.py:179` — a code **comment** mentioning
  `control/status.md`; cosmetic, no runtime dependency.
- `docs/scoping/energy-system-scope.md` — cites `control/claims/*` by path as
  historical scoping evidence.

## Proposed removal sequence

Each step is an independent PR/commit, revertible with a single `git revert`. The
ordering guarantees no required gate goes red between steps: the replacement path
is confirmed first, the kit config is migrated **before** the file it gates is
deleted, and doctrine docs are repointed **before** their cited targets vanish.

**Step 0 — Confirm the replacement merge path (non-destructive gate; go/no-go).**
Before touching anything, verify how PRs actually land now:
(a) confirm whether an external/server-side lander is operating or whether
merges are plain owner clicks (there is **no** in-repo lander workflow —
`.github/workflows/` has none matching `lander`); (b) read the repo's "Allow
auto-merge" setting to learn whether the enabler (A) is still functionally
arming; (c) confirm no open PR currently depends on the enabler to land. This is
the precondition for every later step and answers open questions 3–4.

**Step 1 — Neuter the enabler in place (reversible), keep the file.** Add a
retirement banner comment (parity with the `control/` docs) and disable the job —
either gate it behind `if: false` or drop the `on:` triggers — WITHOUT deleting
the file. Then open a normal test PR and confirm it still lands via the Step-0
path with the enabler inert. This **proves** the replacement path lands PRs
before the enabler is destroyed. Revert = restore the triggers.

**Step 2 — Delete `auto-merge-enabler.yml` (A).** Only after Step 1 proved the
lander/owner path lands a green PR. Verify a subsequent test PR still merges on
green with the file gone. Revert = `git revert` restores the workflow.

**Step 3 — Migrate kit config off `control/` (before any `control/` deletion).**
Repoint or clear `claims_dir` and `heartbeat_files` (and review the `automerge`
block) via a `bootstrap` re-render or coordinated kit edit, so
`substrate-gate.yml:52` no longer gates `control/status.md` and the claims
checker no longer expects `control/claims`. Verify `substrate-gate` stays GREEN
with `control/` **still present** — config change first, deletion second, so the
required gate never reds mid-sequence.

**Step 4 — Delete the `control/` bus (B1–B5).** After Step 3. First remove the 4
live claim files (confirm no active session holds a claim — a claim is abandoned
after ~72h with no activity per `control/claims/README.md`), then
`inbox.md`/`outbox.md`/`status.md`/`README.md`/`claims/`. Verify `substrate-gate
--status-only` still green (Step 3 already migrated the heartbeat). Optionally
preserve the bus as history (open question 2) — a tag or `docs/archive/` move
rather than an in-tree delete — since `inbox.md`/`outbox.md` hold the ORDER
record.

**Step 5 — Repoint the doctrine docs that CITE `control/` (before/with B1
deletion).** Move the OWNER-ACTION + owner-assist format out of
`control/README.md` to a surviving home and fix `CONSTITUTION.md:114,119`; update
`docs/reading-path.md:25,41,50`, `docs/status/README-first.md:31,35`, and the
stale auto-merge doctrine in `docs/owner-profile.md:15`. Leave the historical
docs untouched.

**Step 6 — Delete `docs/ROUTINES.md` (C).** After the residual live wake triggers
are owner-disarmed (console UI). Either hard-delete or downgrade to a one-line
historical stub; repoint `docs/AGENT_ORIENTATION.md:38`.

**Step 7 — Final verification.** `python3 -m pytest` + `python3 bootstrap.py
check --strict` green; a fresh test PR opens and lands via the confirmed path;
`rg 'control/|auto-merge-enabler|ROUTINES'` over live (non-historical) docs
returns no dangling reference.

**Must stay (do NOT remove):**

- `.github/workflows/named-gates.yml` — the six-gate merge bar. KEEP.
- `.github/workflows/substrate-gate.yml` — the born-red card gate + status
  check. KEEP (but reconfigure `heartbeat_files` in Step 3).
- `bootstrap.py` + `.substrate/` — kit machinery. KEEP.
- The external/owner lander path — the actual merge mechanism. Removing the
  enabler removes the **only in-repo** merge automation, so this path must be
  confirmed operative (Step 0) before Step 2.
- `control/status.md` — must survive until `heartbeat_files` is migrated
  (Step 3 strictly precedes Step 4).

## Sequencing / preconditions

**Why deferred to the recreated Project (post-2026-07-21).** The 2026-07-17
wind-down deliberately bannered-in-place rather than deleted
(`docs/current-state.md:44-53`: "retired (deprecation-bannered in place, not
deleted)"), because the Claude Code Projects EAP goes read-only Tue 2026-07-21
and "**The Project will be recreated** fresh after the read-only window; this
repo … and its `main` are the durable artifact that carries across." The
recreated Project is the clean cutover point; `NEXT-TASKS.md:56-57` files the
removal as "a next-Project (recreation) change."

**What must be true first:**

1. **Replacement merge path confirmed operative** (Step 0) — owner-merge and/or
   an external server-side lander demonstrably lands a green PR without the
   enabler.
2. **All sessions migrated off the `control/` bus** — `NEXT-TASKS.md` is already
   the source of "what to build next" and `docs/current-state.md` the live state
   (`NEXT-TASKS.md:5`, `current-state.md:155`); confirm no session/tool still
   *writes* `control/status.md` as its heartbeat before Step 3/4.
3. **Kit config migrated** (Step 3) so no required gate references `control/`.
4. **Residual live wake triggers disarmed** (owner UI) before Step 6 —
   `control/status.md` § ⚑ needs-owner names the two.

## Affected surfaces

- Workflows: `.github/workflows/auto-merge-enabler.yml` (remove);
  `.github/workflows/named-gates.yml`, `.github/workflows/substrate-gate.yml`
  (keep; the latter's `--status-only` heartbeat coupling is the pivot).
- Config: `substrate.config.json` (`claims_dir`, `heartbeat_files`, `automerge`
  — kit-owned).
- Dirs/files: `control/` (README, inbox, outbox, status, claims/) and
  `docs/ROUTINES.md`.
- Doctrine docs: `CONSTITUTION.md`, `docs/current-state.md`,
  `docs/reading-path.md`, `docs/status/README-first.md`, `docs/owner-profile.md`,
  `docs/AGENT_ORIENTATION.md`, `docs/NEXT-TASKS.md`.
- Console-only (not in-tree): "Allow auto-merge" repo setting; the two residual
  failsafe-wake triggers.

## Rough size

**M** overall, sliced into small independent PRs:

- **S1 (S)** — enabler banner + neuter in place (Step 1).
- **S2 (S)** — delete `auto-merge-enabler.yml` (Step 2).
- **S3 (S–M)** — migrate kit config (`claims_dir`/`heartbeat_files`/`automerge`);
  may require a `bootstrap` re-render / kit coordination (Step 3).
- **S4 (S)** — delete the `control/` bus + claims (Step 4).
- **S5 (M)** — repoint doctrine docs (Step 5); largest because the OWNER-ACTION
  format must land a new home.
- **S6 (S)** — delete `docs/ROUTINES.md` + orientation route (Step 6).

## Open questions for the owner

1. **Timing vs the EAP window.** Execute in the recreated Project post-2026-07-21
   as filed, or start the reversible slices (S1/S3) now on this repo since
   `main` is the durable artifact that carries across? **Recommendation:** hold
   destructive steps (S2, S4, S6) for the recreated Project; the non-destructive
   Step 0 audit can happen anytime.
2. **`control/` history — archive or hard-delete?** `inbox.md`/`outbox.md` hold
   the ORDER record. Keep as an in-tree archive (`docs/archive/` or a git tag)
   vs rely on git history alone. **Recommendation:** tag `control/@<sha>` and
   hard-delete — git history preserves it, the tree stays clean.
3. **Is the lander real, or is it owner-manual-merge?** There is **no** in-repo
   lander workflow; removing the enabler removes the only in-repo merge
   automation. Confirm the actual merge mechanism before Step 2.
4. **Is the enabler still arming today?** It has no banner and live
   `pull_request` triggers — is the repo's "Allow auto-merge" setting ON (so
   deletion is a live merge-flow change) or OFF (so it is already inert cleanup)?
5. **External automation depending on the enabler?** Its provenance is a
   fleet-owner directive (ORDER 029) copied from idea-engine — does any
   fleet-level or sibling-repo expectation ride on it existing here?
6. **Kit-owned config — re-render or hand-edit?** `claims_dir`,
   `heartbeat_files`, and `automerge` are `bootstrap.py`/`.substrate` machinery.
   Should Step 3 be a `bootstrap` upgrade/re-render coordinated with the kit, or
   a pinned hand-edit? **Recommendation:** coordinate with the kit so the change
   survives the next `bootstrap upgrade`.
