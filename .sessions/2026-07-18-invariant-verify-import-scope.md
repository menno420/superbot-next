# 2026-07-18 — verify-import vs. live-sweep scope divergence: bug or intent?

> **Status:** `in-progress`

- **📊 Model:** <pending>

## Scope

Follow-up to the #568 session idea. In `sb/kernel/invariants/sweep.py` the live
sweep (`tick` / `reconcile_on_boot` via `_run_sweep`) computes its scan targets
as `targets = guilds or (None,)` — an empty guild source still yields one pass
with `guild_id=None`. `run_verify_import` instead iterates
`tuple(_guild_source())` with **no** `or (None,)` fallback, so an
installed-but-empty guild source makes verify-import iterate an empty tuple and
scan nothing. Claim under investigation: verify-import silently skips a
global/None-scoped invariant the live sweep would still check.

Determine whether this is a **real bug** (≥1 None-scoped invariant exists that
verify-import skips while the live sweep checks it, undocumented) or **not a
bug** (no None-scoped invariant exists / it is a deliberate posture), then
either fix-with-test or document-the-intent. Contained + reversible only.

## What landed

<pending — born red, filled at flip>

## Verification

<pending>

## 💡 Session idea

<pending>

## ⟲ Previous-session review

<pending>
