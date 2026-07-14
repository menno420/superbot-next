# 2026-07-13 — night: curation-night ledger wrap-up (ORDER 019 item 2)

> **Status:** `complete`

- **📊 Model:** `Fable (Claude 5 family)` · night lane worker · mandate: ORDER 019 item 2 wrap-up — append tonight's two verified capability discoveries to `docs/CAPABILITIES.md` (discovery rule step 4: same-session append) and true up the night-bundle claim file · claim: `control/claims/curation-rework-night-bundle.md`

## Scope

Docs-only wrap-up of the curation night lane: (1) append two verified
findings to the `docs/CAPABILITIES.md` append log — the EnterWorktree
pinned-cwd worker wall (hit by both bundle workers tonight, PRs #428/#434)
and the local-Postgres-for-`tools/mint_golden.py` capability (verified
working 2026-07-13); (2) update
`control/claims/curation-rework-night-bundle.md` — bundles 1 and 2 LANDED
(rows 45/59/60 via PR #434 → 9f863a1; row 2 via PR #428 → 7fdd682),
bundle 3 (row 72 + farm goldens) stays PARKED pending the
wp-stack-reconcile lane, claim stays active for it.

## Previous-session review

`2026-07-13-night-channel-recommender.md` (PR #446) — a model oracle port:
the pure/adapter split (PURE scorer in `sb/domain/setup/recommender.py`,
live fill in `sb/adapters/discord/setup_reads.py`), the byte-verbatim
reason strings, and the proved-pre-existing-on-main strict-findings
diagnosis are exactly the evidence-first close-out this lane's doctrine
asks for; its two-source reason-grammar guard recipe is the kind of trap
note that saves a future seat.

## What shipped

PR #447, branch `claude/curation-night-ledger` (docs-only, no code):

- `docs/CAPABILITIES.md` — two append-log entries per the discovery rule:
  - wall: `EnterWorktree` unavailable to pinned-cwd workers (`subagent`
    venue) — verbatim denial captured from both night-bundle worker seats
    (PR #428 and #434); workaround is a manual `git fetch origin main &&
    git worktree add <path> origin/main`, which both bundle PRs shipped
    with. Existing Status badge and seed fence untouched.
  - capability: local Postgres for `tools/mint_golden.py` VERIFIED WORKING
    2026-07-13 — 16.13 binaries at `/usr/lib/postgresql/16/bin` (not on
    PATH), `initdb` refuses root, `runuser -u postgres -- initdb`/`pg_ctl`
    recipe with a /tmp data dir; pre-set `DATABASE_URL` has no listener by
    default; `CREATE DATABASE superbot` then `SELECT 1` returns 1; asyncpg
    installed; pytest/pytest-asyncio still pip-install-needed.
- `control/claims/curation-rework-night-bundle.md` — bundles 1–2 marked
  LANDED (PR #434 → `9f863a1`; PR #428 → `7fdd682`), bundle 3 PARKED
  pending wp-stack-reconcile (#312/#317/#371 open as of
  2026-07-13T23:5xZ, checked); claim stays ACTIVE for bundle 3; row 45's
  `!mine` prefix flip + durable grid state noted as parity.yml-walled and
  handed to the wp-stack/owner lane (recipes in
  `.sessions/2026-07-13-curation-night-1.md`).
- `docs/seat-digest.md` + `.substrate/` state — regenerated via
  `python3 bootstrap.py seat-digest` (derived render; the capability
  append changed one of its sources — drift proven ABSENT on pristine
  origin/main before regenerating, so this PR cleans up after itself).
- Verification: `python3 -m pytest tests/ -q` → **3012 passed, 15
  skipped**; `python3 bootstrap.py check --strict` → exit 0 (claims
  advisories pre-exist on main; the only card finding was this card's own
  designed born-red hold, flipped in this commit).

## 💡 Session idea

The seat-digest drift advisory fires on ANY capability-ledger append but
only says "regenerate" — since every discovery-rule append (a doctrinal
same-session duty) now implies the regen step, `bootstrap.py check` could
auto-detect that the only digest-source delta is an append-log addition
and offer `--fix`-style regeneration, so ledger appenders stop needing to
know the derived-render dependency by heart.
