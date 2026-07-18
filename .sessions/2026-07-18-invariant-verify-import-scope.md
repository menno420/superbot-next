# 2026-07-18 — verify-import vs. live-sweep scope divergence: bug or intent?

> **Status:** `complete`

- **📊 Model:** opus-4.8 · small · kernel correctness-audit

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

**Verdict: NOT A BUG (harmless-but-confusing).** Evidence:

- **No None/global-scoped invariant exists.** All four declared invariants
  (karma, economy, xp, treasury) use the default `scope=TaskScope.GUILD`; every
  `check_ref` queries `WHERE guild_id = $1`. With `guild_id=None`, Postgres
  `= NULL` matches zero rows → zero violations. The live sweep's `(None,)` pass
  on an empty source is itself a **no-op scan** for every current invariant.
- **The capability is explicitly deferred:** `sb/spec/invariants.py` —
  `scope: TaskScope = TaskScope.GUILD  # per-guild batched (GLOBAL scan = later band)`.
- **The `(None,)` in the live sweep is a bookkeeping heartbeat**, not a semantic
  global scan: the module docstring says "Default: no guilds — the sweep is a
  structural no-op", and `_run_sweep` increments `run.guilds_scanned` and writes
  one `SweepRun` log row even with zero guilds. `run_verify_import` writes **no**
  SweepRun row, so it correctly scans nothing on an empty installed source.
- D-0015 documents verify-import as "the SAME sweep dry-run FORCED" — no
  documented intent for a scope divergence, but the divergence has zero
  behavioral consequence for any current invariant and would only matter once
  the deferred GLOBAL-scan band ships (reworking BOTH paths — the live sweep's
  `(None,)` only fires on an empty source, so it wouldn't scan a global
  invariant in a populated deployment either).

The "real bug" bar (≥1 None-scoped invariant skipped) is **not met**, so I
documented rather than "fixed" (aligning would cargo-cult the heartbeat
placeholder into a path with no SweepRun to record — the do-not-"fix"-deliberate
-design precedent):

- **`sb/kernel/invariants/sweep.py`** — a clarifying comment at
  `run_verify_import` explaining *why* it deliberately omits the `or (None,)`
  fallback (heartbeat vs. no-log; all invariants `scope=GUILD`; GLOBAL scan is a
  deferred band that reworks both paths). No production behavior changed.
- **`tests/unit/invariants/test_s12_invariants.py`** —
  `test_empty_installed_guild_source_diverges_between_sweep_and_verify_import`
  pins the divergence: with a guild-agnostic check and an installed-but-empty
  source, the live `tick` runs its one `(None,)` heartbeat pass
  (`guilds_scanned == 1`, `violations_found == 1`) while `run_verify_import`
  scans nothing and returns clean. A future alignment must consciously update it.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3496 passed, 29 skipped**
  (baseline 3495 + 1 new test). The invariants file alone: 13 passed (was 12).
- Guards clean, no new fires: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`.
- Layer rule respected: kernel change touches only kernel/spec-visible symbols;
  no new imports.

## 💡 Session idea

When the GLOBAL-scan band (`sb/spec/invariants.py` `scope`) is actually built,
neither path handles a global invariant in a *populated* deployment: the live
sweep's `targets = guilds or (None,)` scans `None` **only** when the guild list
is empty, so with guilds present a `scope=GLOBAL` invariant is never passed
`guild_id=None`. That band should make `_run_sweep` append the `None` global
target unconditionally for GLOBAL-scoped specs (and verify-import mirror it),
not rely on the empty-source degenerate case — worth pinning as the acceptance
test for that band.

## ⟲ Previous-session review

The prior card (`invariant-sweep-boot-alert-tests`, #568) added the two missing
sweep-lane tests and *flagged* this exact divergence as its 💡 idea, explicitly
leaving it as "a behaviour question, not a test gap". This session closed that
question: audited the invariant registry + specs, found the divergence inert
today (all `scope=GUILD`), and resolved it the lightweight way — a clarifying
comment + a characterization test that pins the behavior — honoring #568's
posture of pin-real-behavior, touch-minimal-production-code, stay reversible.
