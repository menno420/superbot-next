# Session — prod-readiness backlog 2026-07-18

> **Status:** complete

- **📊 Model:** Opus 4 family · high · docs-only

## Goal
Land docs/status/prod-readiness-backlog-2026-07-17.md — a prioritized, cold-pickup-ready backlog of production-readiness slices for superbot-next, derived from a full-tree survey @ 1893d32.

## Scope
Docs-only. Adds one backlog doc + this card. No product-code change.

## Trail
- Survey @ 1893d32: product code marker-clean (14 TODOs all non-product, 1 by-design NotImplementedError, no bare excepts). Backlog = owner-only ops cutover + ~7 subsystems of declared-honest pending terminals.

## 💡 Session idea

The backlog doc is the read-path anchor for cold pickup. Wiring it into
`docs/status/README-first.md` (the status index) means the next fresh
session reaches the prioritized slice list by following the normal
orientation route instead of grepping — worth doing for every durable
status doc so reachability, not memory, carries the trail.

## ⟲ Previous-session review

The 2026-07-17 port-recon / ledger recon session left the tree
marker-clean and ledgered the pending terminals this backlog now
prioritizes; that survey carried cleanly into this docs-only close-out
with no code drift to reconcile.
