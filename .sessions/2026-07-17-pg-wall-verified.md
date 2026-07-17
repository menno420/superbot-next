# 2026-07-17 — verify port-loop preconditions: oracle + Postgres + provisioning

> **Status:** `complete`

- **📊 Model:** Opus 4.8 · medium · docs/ledger

A docs-only slice that CORRECTS a false-negative in the port-backlog wall note.
This session verified in-env that the oracle attaches AND the native Postgres
cluster is startable; the true remaining blocker for NEXT-TASKS #1/#2 is
narrower — DB provisioning DDL is classifier-denied in agent auto-mode.

## WHAT

- `docs/CAPABILITIES.md` — dated 2026-07-17 entry: cluster CAN start
  (`pg_ctlcluster 16 main start`); parity DB provisioning CANNOT (classifier-
  gated). Includes the start recipe, the off-`$PATH` binary note, the
  false-negative trap, and the exact denied provisioning commands.
- `docs/current-state.md` — dated 2026-07-17 CORRECTION appended to the
  existing port-backlog wall note (history kept), with a paste-ready owner
  unblock block.
- This card.

## WHY

The prior note's "no Postgres in-env" framing was a false negative produced by
a `$PATH`/docker-only probe: the server binaries sit at
`/usr/lib/postgresql/16/bin` (off `$PATH`) and the docker daemon is down, so
`which postgres`/`docker` both come back empty and mislead a probe into
"no Postgres". In fact the native `16/main` cluster is pre-created and starts
cleanly. Correcting the ledger stops the next session re-deriving the same
dead end and pinpoints the real, narrower blocker (DB DDL is classifier-gated,
not Postgres absence), so an owner-run provision or a Bash allow-rule is the
one-step unblock rather than a Postgres install.

## VERIFIED FINDINGS

- Oracle attach — CONFIRMED: `add_repo menno420/superbot` + `git clone
  --depth 1` → /workspace/superbot HEAD `bd7b738`.
- Postgres cluster — STARTABLE in-env: native Ubuntu Postgres 16.13 cluster
  `16/main` pre-created (`/var/lib/postgresql/16/main`); `pg_ctlcluster 16
  main start` (root, no sudo) → online; `pg_isready -h 127.0.0.1 -p 5432` →
  "accepting connections" (green on TCP + unix socket); `pg_lsclusters` →
  `16 main 5432 online`.
- False-negative trap — server binaries at `/usr/lib/postgresql/16/bin`
  (off `$PATH`); docker daemon down (`/var/run/docker.sock` absent). Check
  `pg_lsclusters` + `/usr/lib/postgresql`, not `which`.
- DB provisioning — CANNOT (classifier-gated): `tools/setup_local_env.py
  --check` (read-only) confirmed role `parity`, DBs `parity_replay`/`superbot`
  MISSING; every mutating provision path denied "Blocked by classifier":
  `python3 tools/setup_local_env.py`, `sudo -u postgres … psql -c "CREATE ROLE
  parity …"`, plain `psql -U postgres -l`.
- Consequence — `tools/run_golden_parity.py --gate` byte-verification cannot
  run autonomously; NEXT-TASKS #1/#2 stay blocked for autonomous sessions on
  the DDL gate, NOT on Postgres availability.

## CHANGES

- `docs/CAPABILITIES.md` — 2026-07-17 capability+wall entry (append, per the
  re-verification rule — it re-verifies the 2026-07-14 "gate runnable locally"
  entry).
- `docs/current-state.md` — 2026-07-17 correction appended to the port-backlog
  wall note + paste-ready unblock block.
- `.sessions/2026-07-17-pg-wall-verified.md` — this card.

## VERIFICATION

Docs-only slice; the six named gates are unaffected by the ledger/card text.
Card + ledger checked against `.sessions/README.md` marker requirements
(Status badge, 💡, previous-session review, 📊 Model). No DB write was run —
provisioning is classifier-gated; only read-only probes (`pg_isready`,
`pg_lsclusters`, `setup_local_env.py --check`) executed.

## 💡 Session idea

💡 Idea — provision the parity role + DBs in the env setup-script (or ship an
approved `tools/setup_local_env.py` allow-rule) so autonomous port-loop
sessions aren't blocked by the DDL classifier gate. The cluster already starts
in-env; adding `pg_ctlcluster 16 main start && python3 tools/setup_local_env.py`
at container boot (survives restarts, idempotent, non-destructive) turns a
recurring per-session wall into a one-time env fact and lets #1/#2 replay-to-
green without owner intervention each session.

## ⟲ Previous-session review

🔎 Previous-session review (`.sessions/2026-07-17-port-recon-ledger-notes.md`,
#509 recon): it recorded the port backlog (#1/#2) precondition — oracle +
Postgres — correctly and honestly, but a `$PATH`/docker-only probe (`pg_isready`
→ `5432 - no response`) led it to believe Postgres was unavailable in-env. This
session verifies the cluster IS startable (`pg_ctlcluster 16 main start`,
`pg_isready` green) and pinpoints the true blocker as the DB-provisioning
classifier gate, not Postgres absence — and records both the start recipe and
the false-negative trap in `docs/CAPABILITIES.md` so the correction is durable.
