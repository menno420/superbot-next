# 2026-07-18 — docs: record the golden-parity `--gate` session-window wall (CAPABILITIES)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red HOLD so the server-side lander
> can merge on green. Flip made once CI confirmed every functional gate green on
> PR #522 (`tests`, `code-quality`, `checkers`, `architecture`,
> `manifest-validate`, `sim-gate`, `golden-parity`, `build-image`,
> `check_compat_frozen`, aggregator `gate`), with `substrate-gate` the only red —
> exactly the born-red hold this flip releases.

- **📊 Model:** Opus family · low · docs-only
- **Born:** 2026-07-18 (born-red first commit)

## Scope

Append ONE dated, neutral capability observation to the living `docs/CAPABILITIES.md`
ledger (verified can/cannot record, read at session start): full golden-parity
`--gate` does not complete inside a session/container window, so full parity
verifies only in CI, and `tools/mint_golden.py <case_id>` is the only local
granular oracle check. Recorded as a NEUTRAL capability fact per the ledger's
discovery rule (dated, venue-tagged, how-verified) — a fact, not a rail.

Branch `claude/capabilities-golden-gate-wall` off fresh origin/main. This card is
the first commit (born red); the `docs/CAPABILITIES.md` append follows in a second
commit.

## Files touched

- `docs/CAPABILITIES.md` — one dated entry in the "Append log — newest first"
  section, matching the ledger's `- YYYY-MM-DD · capability|wall · finding ·
  evidence · workaround` format.

## Verification

- `python3 bootstrap.py check --strict` (docs reachability + session-card badges)

## Why born-red

Card is intentionally `in-progress` (born-red) so substrate-gate holds the PR
red. It flips to `complete` as the deliberate LAST commit once CI confirms the
functional `gate` job is green.

## 💡 Session idea

💡 Idea — the golden-parity `--gate` timing wall is exactly the class of fact the
CAPABILITIES ledger exists to make durable: a session that assumes `--gate` is a
quick local check burns its whole window on a run that can only finish in CI.
Guard recipe for the next oracle-port session: to verify parity locally, reach for
`tools/mint_golden.py <case_id>` (per-case oracle mint/verify), and treat
`tools/run_golden_parity.py --gate` as a CI-only, full-corpus gate — never a
session-blocking local step.

## ⟲ Previous-session review

🔎 Prev-session review (`.sessions/2026-07-18-harden-workflow-io-fence.md`): that
session fail-closed the workflow banned-I/O fence and confirmed the `golden-parity`
gate concludes green in CI on its head. This session records the complementary
operational fact — that the SAME full `--gate` run does not finish inside a local
session/container window, so it belongs to CI — which is consistent with, not
contradicted by, the prior card's CI-green baseline.
