# 2026-07-17 — verified in-env Postgres provisioning wall (port loop #1/#2)

> **Status:** `in-progress`

- **📊 Model:** Opus 4.8 · medium · docs/ledger

A docs-only slice that SHARPENS the existing port-backlog wall note: this
session verified in-env that the port oracle CAN be attached but Postgres
CANNOT be provisioned at all in this environment class, so NEXT-TASKS #1/#2
stay blocked until an external Postgres is provided.

## WHAT

`docs/current-state.md` — the existing 2026-07-17 port-backlog prerequisite
note is sharpened with a dated NEUTRAL sub-note recording this session's
verified in-env findings (oracle attach works; Postgres cannot be provisioned)
plus a paste-ready provisioning need. Session card records the evidence.

## WHY

The prior note said Postgres was merely "not provisioned" / `5432 - no
response`. That understates the wall: this session attempted provisioning and
found there is **no path** to a live Postgres in this environment class — no
docker daemon socket and no native server binaries — so a session here cannot
self-provision the DB the golden-mint pin needs (`tools/mint_golden.py` refuses
to fake oracle byte-verification, and the db_delta is part of the pin).
Recording the sharper, evidence-backed finding keeps the next session from
re-deriving the same dead ends and names exactly what an unblock requires.

## VERIFIED FINDINGS

- Oracle attach — **CONFIRMED working**: add_repo + clone brings
  `menno420/superbot` into scope; cloned at `/workspace/superbot` HEAD
  `bd7b738`.
- Postgres — **CANNOT be provisioned in this environment class**:
  - `pg_isready` → "no response", exit 2 on `/var/run/postgresql:5432`,
    `localhost:5432`, `127.0.0.1:5432`.
  - `psql` client present (`/usr/bin/psql`) but NO native server binaries:
    `postgres`, `initdb`, `pg_ctl` all absent.
  - `docker` CLIENT present (`/usr/bin/docker`) but daemon is DOWN:
    `/var/run/docker.sock` does not exist; `docker info` exits 1
    (`dial unix /var/run/docker.sock: connect: no such file or directory`),
    so `docker run postgres` is also impossible.
- Therefore NEXT-TASKS #1 (port-to-parity) and #2 (game-surface) remain
  **walled in-env**; unblock requires an externally-provided Postgres.

## CHANGES

- `docs/current-state.md` — dated NEUTRAL sub-note next to the existing
  port-backlog wall note + a paste-ready provisioning need (server package or
  external `DATABASE_URL`).
- `.sessions/2026-07-17-pg-wall-verified.md` — this card.

## VERIFICATION

Docs-only slice; the six named gates are unaffected by the ledger/card text.
Card + ledger reviewed against `.sessions/README.md` marker requirements.

## 💡 Session idea

💡 Idea — ship a `tools/dev_pg.sh` disposable-Postgres helper (apt install +
`initdb` into the scratchpad + `pg_ctl` start) so any session self-provisions
the port-loop DB in one command, retiring this recurring wall. It only helps
once the environment setup-script installs a Postgres **server** package (this
env ships the `psql` client but no `postgres`/`initdb`/`pg_ctl`), so the helper
should fail loudly with the exact apt line when the server binaries are absent.

## ⟲ Previous-session review

🔎 Previous-session review (`.sessions/2026-07-17-port-recon-ledger-notes.md`,
#509 recon): it correctly recorded the port backlog (#1/#2) as blocked on the
oracle + a live Postgres (`5432 - no response`) and named the mint prerequisite
honestly. This session verifies and sharpens that note from "not provisioned"
to "cannot provision in-env" — the oracle attach is confirmed working, and the
Postgres wall is shown to be structural (no daemon, no server binaries), not
merely a down service. No regression noted.
