# 2026-07-17 — provisioning-unblock record: DB provision + golden-parity gate run autonomously in the project-default env

> **Status:** `in-progress`
>
> Born-red first commit — holds the PR red until the main session writes the
> close-out and flips this badge to `complete` as the deliberate last step.

- **📊 Model:** opus-4.8 · medium · docs-correction (evidence-first)
- **Born:** 2026-07-17 (born-red first commit)

## Scope

Correct a now-contradicted record. The HEAD docs (from PR #510) state that
autonomous DB provisioning is **classifier-denied** — that
`tools/setup_local_env.py` and every mutating provision path are "Blocked by
classifier", so the port loop cannot run autonomously. In **this** environment
(the project-default env), that wall does **not** reproduce: provisioning runs
to exit 0 with no classifier denial, and the golden-parity gate runs GREEN
autonomously.

The correction is framed as **env-specific**, not a global refutation of #510:
#510's wall was almost certainly measured in a different (non-default) venue.
In the project-default env the mutating provision path is not walled, so
NEXT-TASKS #1/#2 (the port loop) are autonomously runnable here after a
one-line boot recovery.

Branch `claude/provisioning-unblock-record` off origin/main `0b1134b`. This
card is the first commit (born red); the doc edits follow in a second commit.

## Evidence (reproduced live this session, `date -u` Fri Jul 17 2026)

- `pg_ctlcluster 16 main start` → exit 0 (cluster online);
  `pg_isready` → `/var/run/postgresql:5432 - accepting connections` (exit 0).
- `python3 tools/setup_local_env.py` → exit 0; provisions role `parity` +
  DBs `parity_replay`/`superbot` with **no** "Blocked by classifier".
  `--check` confirms role `parity`, DBs `parity_replay`/`superbot`, role
  `superbot` all present and authenticating (exit 0).
- `DATABASE_URL='postgresql://parity:parity@localhost:5432/parity_replay'
  SB_DATA_PLANE=test python3 tools/run_golden_parity.py --gate` →
  "gate: GREEN — all 523 golden(s) across 50 ported subsystem(s) replay
  clean", gate exit 0.
- `tools/check_parity_depth.py` → "OK — 49 subsystems (49 ported), kernel
  ported, 523 goldens", exit 0.
- Pristine BOOT state (before recovery): cluster `down`, DBs unprovisioned,
  `DISCORD_TOKEN`/`PARITY_DATABASE_URL`/`POSTGRES_PASSWORD` unset,
  `DATABASE_URL` set. One-line recovery restores the runnable state:
  `pg_ctlcluster 16 main start && python3 tools/setup_local_env.py`.

## Files touched

- `docs/current-state.md` — the provisioning/classifier note corrected to
  record the env-specific autonomous-provisioning result (boot-state fact kept).
- `docs/CAPABILITIES.md` — appended a dated 2026-07-17 CORRECTION entry
  (append, not edit) recording the env-specific reproduction with verbatim
  commands + outputs; #510's entry is preserved and superseded, not deleted.

## Verification

- Doc-lint safe (docs-only change): this card carries a Status badge in the
  first 12 lines and is reachable; no code paths touched.
- The four evidence commands above all reproduced green this session.

## 💡 Session idea

*(to be written at close-out by the main session)*

## ⟲ Previous-session review

*(to be written at close-out by the main session)*
