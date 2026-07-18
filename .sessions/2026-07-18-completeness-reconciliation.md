# 2026-07-18 — verify-first completeness reconciliation snapshot: supersede the stale 07-13 table

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · review/verify · dated completeness reconciliation snapshot (born-red, holds substrate-gate)

## Scope

A docs-only planning artifact. The `docs/status/completeness-table-2026-07-13.md`
inventory has drifted: several rows it lists as pending have since landed (mining
`!cook`/`!use`, fishing deep-system + minigame, settings audit surface, xp.config,
setup compound-op apply seams, utility Invite, effect-leg compensation, ensure-only
registration), while a handful of remaining flags were mis-scoped (`server_management`
axis-5 and casino roulette are byte-faithful oracle stubs, not gaps).

This slice produces a fresh dated snapshot,
`docs/status/completeness-table-2026-07-18.md`, that SUPERSEDES the 07-13 table.
Every verdict was re-verified this session by an oracle-vs-HEAD pass — the live
oracle `menno420/superbot @ 69a061d` compared against superbot-next HEAD `782ca2d`.
It is a reconciliation of an EXISTING record, not new product behavior: no `sb/`
code changes, docs-only.

## Deliver

- New `docs/status/completeness-table-2026-07-18.md` — a verify-first reconciliation
  snapshot carrying the DONE / NOT-A-GAP flips, the genuinely-OPEN remaining work
  (with mintability calls), the owner-gated / sibling / forward lanes, and a plain
  conclusion: the user-facing port surface is essentially exhausted; recommend the
  loop shift toward PLANNING mode (D1–D6 design docs) while opportunistically
  closing the small mintable items (B2/B3 mining panel re-points, C1 except-boundary
  tests, the wizard.py docstring).
- Reachability (docs-gate orphan check): a one-line link from `docs/NEXT-TASKS.md`
  and a "superseded by" pointer at the top of the 07-13 table.
- `> **Status:** \`reference\`` badge (a valid docs-gate token).

## Verification

- `python3 bootstrap.py check --strict` → the only red is this card's own designed
  born-red hold (verbatim in the PR body); 0 badge / reachability findings.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold until this card flips complete.

## 💡 Session idea

The snapshot's own conclusion is the next idea: with the user-facing port surface
essentially exhausted, the highest-leverage next work is turning the D1–D6 forward
lanes (themed renderer, real-time minigame framework, access-matrix/audit dashboard,
observability/metrics, e2e/live-guild harness, autonomy-apparatus removal) into
fuller design docs — a PLANNING-mode loop — rather than hunting for more port
slices. A recurring reconciliation cadence (a dated snapshot per wave) would keep
the completeness ledger from drifting the way the 07-13 table did; this snapshot is
itself point-in-time and derived from a shallow oracle clone, so it wants a
successor, not amendment.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-setup-except-boundary-tests.md` (backlog C1), which
characterized `sb/domain/setup/moderation.py`'s four `except` swallows with pinning
boundary tests and named the higher-density modules (`final_review.py`,
`launcher.py`, `essential_steps.py`) as the next targets. That card's survey is the
direct evidence for this snapshot's C1 row (PARTIAL, MINTABLE — additive DB-free
tests over the still-uncovered `final_review`/`essential_steps`/`launcher`/`wizard`
swallow sites). It confirms the setup band is the current hardening frontier and
that the remaining agent-actionable work is small and additive — consistent with
this snapshot's headline that the port surface is essentially exhausted.
