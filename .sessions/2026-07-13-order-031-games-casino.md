# 2026-07-13 — ORDER 031 phase 1: games finalization reviews + casino section spec (docs)

> **Status:** in-progress

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
