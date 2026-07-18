# 2026-07-18 — correct stale autonomy-apparatus framing (enabler live; control/ partially load-bearing)

> **Status:** `in-progress`
>
> Born-red first commit (this card alone) HOLDs the `substrate-gate` red until it
> flips `complete` as the deliberate LAST step (per `.sessions/README.md`). The
> docs-only corrections land in the second commit; the flip is the last. Docs-only
> truth-keeping — no `sb/` code touched, zero goldens, so the six functional named
> gates ride green and `substrate-gate` is the expected sole red until the flip.

- **📊 Model:** opus-4.8 · high · docs · correct stale autonomy-apparatus framing (born-red, holds substrate-gate)

## Scope

Two docs (`docs/current-state.md`, `docs/NEXT-TASKS.md`) carried stale framing about
the merge/coordination apparatus, drifted from what the workflow + kit-config files
actually declare. Two surgical, evidence-cited corrections:

1. **The auto-merge enabler is LIVE, not retired.**
   `.github/workflows/auto-merge-enabler.yml` fires `on: pull_request`
   (`types: [opened, reopened, ready_for_review, synchronize]`, ~L37-46) and carries
   NO deprecation banner (`grep -in 'deprecat\|retired'` → none). It is the SOLE
   in-repo merge automation (arms GitHub-native squash auto-merge at PR-open; the
   required checks stay the enforcement). Any "server-side lander" the docs cite is
   external / owner-side — there is no separate in-repo lander workflow (the only
   `.github/workflows/*.yml` that arms a merge is the enabler; the others mention
   "auto-merge" only in comments). The docs framed the enabler as a
   deprecated/retired part of a wound-down apparatus and named a "server-side lander
   workflow" as if in-repo.

2. **`control/` is PARTIALLY load-bearing, not fully retired.**
   Only the `control/` ORDER-BUS (inbox/outbox as an order channel) was retired
   (per the inbox deprecation banner, `control/inbox.md` ORDER 024 + the
   `control/README.md` / `control/status.md` RETIRED banners; cleanup rode #507).
   The `control/status.md` heartbeat + `control/claims` STAY load-bearing: the
   REQUIRED `substrate-gate.yml` runs `python3 bootstrap.py check --strict
   --status-only` against them (L52), and `substrate.config.json` still points
   `claims_dir` → `control/claims` (L35) and lists `control/status.md` (L51). Naive
   `control/` deletion would RED a required gate — removal is owner-sequenced with
   the kit-config migration first (per the D6 #548 plan).

## Deliver

- `docs/current-state.md`:
  - "Autonomous apparatus" para (~L44-47): scope the retirement to the `control/`
    **order-bus** + wake-chain; add that `control/status.md` + `control/claims` stay
    load-bearing behind the required `substrate-gate.yml`, so naive deletion would
    RED a gate (D6 #548 sequences kit-config first).
  - "Review rhythm" section (~L148-155): correct "a PR lands via the repo's
    server-side lander workflow" → GitHub-native auto-merge armed at PR-open by the
    LIVE in-repo `auto-merge-enabler.yml` (sole in-repo merge automation); mark any
    "server-side lander" external/owner-side; correct "`control/status.md` is
    retired (this ledger replaces it)" → status.md stays live (required
    `--status-only` heartbeat), ledger complements it.
- `docs/NEXT-TASKS.md`:
  - Item #6 (~L51-59): reframe "retired autonomy apparatus" → still-live; add a
    2026-07-18 correction note (enabler LIVE; only the order-bus retired;
    heartbeat/claims load-bearing; removal owner-sequenced per D6 #548).

## Verification

- `python3 bootstrap.py check --strict` → no orphan/reachability regression
  (edited existing read-path docs, added no new doc).
- `python3 -m pytest tests/test_session_card_gate.py -q` → green.
- substrate-gate added-card command exit 0 on the COMPLETE card.
- Docs-only, no `sb/` or test code touched; functional named gates ride green,
  substrate-gate the expected sole hold until the flip.

## 💡 Session idea

The stale framing was internally coherent — a "wind-down" narrative that read the
2026-07-17 order-bus retirement as if the WHOLE apparatus, workflow files included,
had already gone inert. But the workflow + kit-config files are the ground truth, and
they say the opposite in two places: the enabler still fires `on: pull_request` with
no banner, and a REQUIRED gate still validates `control/status.md` + `control/claims`.
A retirement narrative that outruns the files it describes is a truth-keeping hazard:
a session trusting "control/ is retired, drop it" would RED a required gate, and a
session trusting "the enabler is retired" would misread how its own PR merges. The
correction is append/inline, not a rewrite — the wind-down PLAN is real and stays
documented as a next-Project change; only the tense (planned, not done) and the scope
(order-bus, not heartbeat/claims) are corrected to match the files.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-owner-agenda-complete.md` (#547) — a docs-only,
born-red, substrate-gate-holding planning-artifact card that upgraded stale agenda
rows to match now-merged source docs. Same shape and same class of work as this card:
a doc that drifted from ground truth (there, three merged design docs; here, the
workflow + kit-config files) gets reconciled verbatim to the source. The recurring
lesson — a summarized-from-framing line can invert the actual finding — applies
directly: "control/ is retired" summarizes away that a required gate still depends on
it, exactly the inversion this card corrects.
