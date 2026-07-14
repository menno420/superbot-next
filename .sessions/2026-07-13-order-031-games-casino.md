# 2026-07-13 — ORDER 031 phase 1: games finalization reviews + casino section spec (docs)

> **Status:** complete

- **📊 Model:** `fable-5` · ORDER 031 phase 1 (games finalization) · branch
  `claude/order-031-games-casino` (docs-only)

## Scope

Land the phase-1 analysis of ORDER 031 as two documents, assembled from the
five parallel review seats (mining / fishing / idle-farm end-to-end reviews,
casino/minigame inventory, section-spec draft):

1. `docs/review/games-finalization-2026-07-13.md` — per-game headline
   verdicts (mining/fishing/idle), what's ported / parity state / gaps vs
   oracle / world-hub integration / ranked extend-improve lists with
   BLOCKED-BY-CLAIM flags, plus ORDER 019 item dispositions (items 3, 4, 6, 7)
   and the stale artifacts found (lingering `fishing-bait-race-fence` claim
   post-#394, stale completeness-table fishing residue sentence).
2. `docs/specs/casino-section-spec.md` — the D-0082 §7 plug-in-slot
   publication: 10-game inventory + readiness table, the recommended
   🎰 casino / 🕹️ arcade / 🌍 world taxonomy (2-section zero-churn fallback
   named), enable-all-or-pick-a-few semantics on the existing
   `GameSectionSpec` machinery, dynamic-panel update contract, expansion
   slots, exclusions, honest blast-radius ledger. The casino SECTION BUILD
   itself stays a separate order.

Docs-only diff + reachability links (docs/review/README.md,
docs/design/README.md, one pointer line in docs/design/game-sections.md §7).
No code, no claims edited, nothing armed.

## Close-out

Both docs landed; branched from main `9634e81` (which already carries the
ORDER 019 item 3 fix, #425 — the review's item-3 disposition was updated
from "unclaimed" to LANDED accordingly, source of truth over order text).
Reachability: review indexed in docs/review/README.md; spec indexed in
docs/design/README.md + a single arrived-spec pointer line in
docs/design/game-sections.md §7 (its `plan` badge untouched). Stamp
discipline honored: the new docs cite decision HOMES
(game-sections.md / docs/decisions.md), never raw D-ids — the strict check
flagged the duplicate stamps on first draft and the rephrase cleared it.

Verification: `python3 -m pytest tests/ -q` — **2871 passed, 15 skipped**
(65.81s). `python3 bootstrap.py check --strict` — doc findings ZERO; the
only exit-affecting item pre-flip was this card's own designed born-red
hold ("This red is the designed hold, not a defect"); claims warnings are
pre-existing advisory (never exit-affecting). No claim collides with
docs/review/ or docs/specs/ (grep over control/claims/ at HEAD: zero hits).

## 💡 Session idea

`check_stamp_discipline` flags duplicate D-id citations only AFTER the doc
is written; a one-line note in docs/design/README.md (or the doc-authoring
skill) saying "cite the decision's home doc, not the D-id — one stamp per
decision" would save every future doc-writing session the same
write-check-rephrase loop. Guard recipe: the rule lives at
`bootstrap.py::check_stamp_discipline` (~:4488, regex `_LED_ID_RE`
~:4224); the fix is doc guidance, not checker change.

## ⟲ previous-session review

Previous card (2026-07-13-night-money-race-checker-fix.md, PR #425): a
model close-out — root cause named at the exact propagation-loop line,
red-then-green proof for the new pins, and the ALLOWLIST-vs-KNOWN_RISKS
decision flagged with the checker's own doctrine as rationale. Its 💡 idea
(restrict lock/SELECT classification to literals inside DB_CALL_NAMES call
args) carries a real guard recipe. No nits found; its bare-word Status
badge follows the gate-greppable convention this card also uses.
