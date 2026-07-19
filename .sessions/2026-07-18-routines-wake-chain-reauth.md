# 2026-07-18 — record wake-chain re-authorization in docs/ROUTINES.md

> **Status:** `in-progress`
>
> Born-red first commit (this card alone) — holds the `substrate-gate` red until
> the deliberate LAST-commit flip to `complete` (per `.sessions/README.md`).
> Docs-only slice; no `sb/` code touched, zero goldens — the six functional named
> gates ride green and `substrate-gate` is the expected sole red until the flip.

- **📊 Model:** opus-4.8 · low · docs · record owner-live wake-chain re-authorization in docs/ROUTINES.md (born-red, holds substrate-gate)

## Scope

`docs/ROUTINES.md` carries a RETIRED banner (2026-07-17) on the coordinator wake
chain (`send_later` pacemaker + failsafe wake) from the pre-recreation Project
wind-down. Two worker agents tonight (2026-07-18) declined `send_later` calls
citing that stale banner, even though the owner re-authorized the wake chain
live tonight. This slice records the re-authorization so the friction clears —
workers reading the banner see, adjacent to it, that scheduling calls are now
authorized for the current recreated Project.

Single-file docs edit (`docs/ROUTINES.md` only):

1. Add a clearly-visible `## ✅ ADDENDUM` section immediately below the Status
   badge (keeping the badge inside the first-12-lines window the docs-gate
   scans), superseding — not deleting — the RETIRED banner: the coordinator
   wake chain (`send_later` pacemaker + failsafe wake) is **RE-AUTHORIZED by
   owner-live direction on 2026-07-18** for the current recreated Project.
2. Quote the two verbatim owner statements as provenance, attributed as
   owner-live direction relayed via the coordinator session on 2026-07-18
   ~21:20Z.
3. Historical RETIRED context stays intact (superseded, not removed).

Out of scope (untouched): `control/status.md` (coordinator's file), and every
other file except this card.

## Verification (to fill at close-out)

- `python3 -m pytest -q --ignore=examples` — docs-only, expected green.
- `python3 bootstrap.py check` — docs-gate exit 0 (ROUTINES.md reachable +
  Status badge intact in first 12 lines).
