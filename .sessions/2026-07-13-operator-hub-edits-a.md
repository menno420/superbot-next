# 2026-07-13 — operator-hub edits A: utility modals + role create + counter preset apply (ORDER 017 fix slice)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1 (completeness table `docs/status/completeness-table-2026-07-13.md`, Top-gaps item 6 — the operator-hub admin action cluster)

## Scope

Slice A of the operator-hub EDIT-controls family (the read-only NAV slice
is peer-claimed by `control/claims/operator-hubs-interactive.md`; the EDIT
controls were explicitly deferred there and are this lane's):

- **utility.panel** — 📊 Poll + 🔔 Remind Me become G-10 modal ingresses
  over the LIVE command twins (`utility.poll_view` / `utility.remind_view`
  lanes; the moderation.hub.warn precedent); 🌿 420 forwards to the PORTED
  `four_twenty.overview` panel. (🔗 Invite is peer PR #332's — untouched.)
- **role.hub** — 📝 Create becomes the shipped `RoleCreateModal` ingress
  (name + colour) over the LIVE `!createrole` lane (audited provisioning +
  audit/lifecycle companions).
- **counters** — the argful `!counterpreset <name>` APPLY branch goes live:
  the oracle's three audited template writes through `settings.set_scalar`
  + the shipped ack/refusal copy (the xp.config settings-ops precedent).

## Coordination check (read at origin/main HEAD 3ea2282)

- `operator-hubs-interactive` claim = read-only nav SLICE 4 only; edit
  controls explicitly deferred → this lane's work. No newer claim covers
  these surfaces.
- Peer PR #345 owns ALL of xp.config (skipped here); #333 owns cleanup
  words + hub logging nav (skipped); #332 owns server_management nav trio +
  mining ws_back + utility 🔗 Invite (skipped — this slice touches only
  poll/remind/open_four_twenty in utility).

## Previous-session review

Fresh lane off the completeness table + ORDER 017; mirrored conventions
from merged #331 (diagnostic operator mutations) and #340 (setup wizard):
modal ingress over live ops, one-way pending→ported flips, compat pins for
new modal ids, manifest recompile.

## What shipped

PR #358 (supersedes #355 — that branch's PR events all fell into the
2026-07-13 Actions outage window; root cause of the no-checks state was
the PR's DIRTY mergeable_state: GitHub creates no pull_request runs for
a conflicted PR). Five pending terminals retired: utility
poll/remind/four_twenty, role.create, counters.preset. Modal ingress
over live twin lanes (oracle-verbatim copy), the shared create-role
lane, the audited three-write preset apply. Verification: full suite
green on re-run (race-test flake class on run 1), golden gate GREEN
478/484 across the branch lifetime on clean local Postgres, compat +3
modal ids, sim-gate untouched-clean.

## Guard recipe

A PR whose `mergeable_state` is `dirty` silently gets ZERO check runs —
no red, no queue, nothing (pull_request workflows run on the merge ref,
which doesn't exist). Symptom: `actions/runs?branch=<head>` →
`total_count: 0` while sibling branches process. Fix: merge origin/main
into the head (never rebase), resolve, push — checks attach instantly.
Check `mergeable_state` BEFORE kicking CI with empty commits.

## 💡 Session idea

The kit's PR-babysit route should poll `mergeable_state` alongside
check runs: `dirty` explains "no checks" instantly and the fix (merge
main in) is mechanical — tonight it cost two no-op kicks, a
close/reopen and a superseding PR to discover.
