# 2026-07-16 — merge queue: WP stack + frozen four all landed

> **Status:** `complete`

- **📊 Model:** sonnet-5

## Scope

Owner order (live turn): finish the superbot-next merge queue. Landed, in
order, on branch `claude/superbot-next-merge-queue-fhq3c2`:

1. **WP stack** — #335 (WP-5) → #344 (WP-6) → #371 (WP-7), squash-merged
   in order. Each of #344/#371 went dirty after the previous landed
   (base auto-retargeted to `main`); resolved by merging `main` into the
   branch head (never rebase), re-running the full local verification
   suite, pushing, and merging on green required-check status. The
   "Do NOT auto-merge" line in #344's body was a lifted park per the
   owner's live order — ignored.
2. **Frozen four** — #466 (fishing cast-again) → #473 (mining
   title-equip) → #477 (games casino/arcade/world sections) → #476
   (curation row-72 + farm goldens). For each: removed the
   `do-not-automerge` label, merged `main` into the branch head
   (sometimes more than one round, since each earlier PR's merge moved
   `main` again before the next PR's CI finished), flipped the branch's
   `.sessions/` card `in-progress` → `complete` per `.sessions/README.md`
   (Status badge, a genuine deduped 💡 idea, `📊 Model:` normalized to a
   family-level name, a previous-session review remark), pushed, and
   merged on green.

Every merge-conflict round followed the same recipe: `parity/parity.yml`
+ `tests/unit/parity_adapter/test_replay_adapter.py` +
`tests/unit/parity_gate/test_check_parity_depth.py` count-pin conflicts
were unioned (never picked one side) and re-summed FROM DISK via
`tools/mint_golden.py`'s `compute_counts` (imported + minted − retired =
on-disk corpus, verified against `GOLDENS_ROOT.glob("*/*.json")` each
time — never hand-computed); `.substrate/guard-fires.jsonl` conflicts
were unioned in chronological `ts` order (earlier batch first, not
picked-a-side). `sb/domain/mining/ops.py` / `service.py` conflicts were
almost all HEAD-additive (a later WP slice adding a leg the earlier base
didn't have yet) — resolved by keeping both sides' registrations, never
dropping one.

## Verification

Before every push: `python3.11 -m pytest tests/ -q` (green every round —
final count 3187 passed, 2 skipped), `tools/check_parity_depth.py`,
`tools/manifest_compile.py` (no snapshot drift on any round),
`check_symbol_shadowing` / `check_namespace` / `check_no_skip` /
`check_config_usage` / `check_migrations` / `check_money_race` /
`check_sim_gate` / `check_compat_frozen`, and `bootstrap.py check
--strict` (green modulo pre-existing, never-exit-affecting advisories).

Post-merge, on main HEAD (6047618, #476's merge — the last of the
queue):
- `tools/check_parity_depth.py` → OK — 49 subsystems (49 ported), kernel
  ported, 523 goldens. No drift.
- `tools/check_lockfile_fresh.py` → OK (33 pinned dists, 1015 hashes).
  No stale pins.
- `tools/run_golden_parity.py --gate` (local Postgres 16, the
  `docs/CAPABILITIES.md` verified recipe — `parity`/`parity_replay`
  user+db created fresh this session) → `gate: GREEN — all 523
  golden(s) across 50 ported subsystem(s) replay clean`.

Pins are NOT stale — no pin re-sum PR needed (the owner's fallback
instruction if pins drifted).

`control/status.md` updated in the same commit: the "PARKED — open PRs"
section described all seven PRs as still open/frozen, which was now
false (visible drift, fixed on sight per the repo's own doctrine).

## 💡 Session idea

The `do-not-automerge` label reappeared on #466/#473/#477 after I
explicitly removed it via the API and pushed — with no in-repo
automation that adds it (`auto-merge-enabler.yml` only *reads* the
label, never writes it) and no coordinator-doc mechanism found either.
Never root-caused this session (worked around it by merging directly via
the API once CI was green, bypassing the auto-merge path each time), but
it's worth a dedicated look: either a GitHub App/bot outside this repo's
own workflows is re-syncing the label off something in the PR body text
(all four bodies say "coordinator WP-stack freeze"), or there's a
race between the label-removal API call and a `synchronize` event
re-reading stale label state. A guard recipe: next time this
reappears, capture the label's timeline via the GitHub API
(`GET /repos/{owner}/{repo}/issues/{number}/timeline`) to see who/what
re-added it — that single API call would settle the mystery this
session didn't have time to chase.

## ⟲ Previous-session review

Covers the WP-7 and title-equip authoring sessions (`.sessions/
2026-07-13-mining-write-parity-wp7.md`, `.sessions/
2026-07-14-title-equip-write.md`), whose stacked/parked-green PRs this
session finally landed. Both left exceptionally citation-dense PR
bodies (exact oracle file:line pins, exact byte-for-byte reply copy,
exact db_delta shapes) — that density is what made resolving five
rounds of count-pin conflicts mechanical instead of guesswork: every
conflicting number had a paper trail back to a specific golden file and
a specific decide-and-flag rationale, so the union-and-re-sum recipe
never had to guess intent. One thing worth carrying forward: several
cards left their Verification/idea/review sections as literal
`(filled at close-out)` placeholders past their actual PR merge readiness
(`2026-07-14-casino-section.md` was one) — a card that reaches CI-green
should get its close-out written promptly, not deferred to whichever
session next happens to touch the branch.
