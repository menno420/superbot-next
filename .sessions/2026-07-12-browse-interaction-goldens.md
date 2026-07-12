# 2026-07-12 — mint the browse-interaction goldens (D-0034 capstone)

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · feature build (D-0034 / D-0073 — interaction goldens)

## Scope

The interaction-golden CAPSTONE of the UI-restoration lane, STACKED on
slice 3 (`dex-browse`, PR #288 → slice 2 `browse-surfaces-convert` #279 →
the engine #270, all unmerged). Slices 1–3 ARMED the shared BrowserView
engine and two browse surfaces (inventory detail sort/filter/page + the
dex element filter) but deliberately shipped ZERO golden churn — no golden
CLICKED a browse control. That left the corpus's real interaction blind
spot open: ~470 goldens, all single-step but ONE (the blackjack Hit
button), and the sort/filter SELECTS had no coverage at all. This session
mints the multi-step click/select→re-render goldens that close it, using
the D-0073 sanctioned mint procedure (capture_case + kernel-spine strip).

## Postgres restore (Step 0)

Prior workers wrongly reported "asyncpg unavailable / golden gate cannot
run". The truth: the remote env HAS a local Postgres 16 cluster but
container restarts WIPE its provisioning. Found: cluster **down**, role
`parity` + the three DBs **absent**, `asyncpg` **not importable**.
Restored: `pg_ctlcluster 16 main start`; `CREATE ROLE parity LOGIN
CREATEDB`; `CREATE DATABASE parity / parity_replay / superbot OWNER
parity`; `pip install asyncpg` (0.31.0). The gate then ran on the
pre-existing corpus: **GREEN — 412 goldens across 51 ported subsystems**.

## Delivered

### The select-driven replay vocabulary (D-0019 reviewed corpus growth)

The click `Step` already carried `values` and the capture `_drive` already
passed them to `harness.click`, but neither end of the golden vocabulary
serialized them — a SELECT click's chosen value was invisible in the
stored document. Grew the ONE vocabulary chain (the D-0073 modal-`fields`
precedent, on the click kind):
- `parity/harness/runner.py` `_describe_step` — serialize a click's
  `values` when present (a value-less button click omits the key, so the
  blackjack Hit / page buttons stay byte-identical).
- `sb/adapters/parity/cases.py` `_step_from_input` — reconstruct them, so a
  select golden round-trips `reconstruct → describe`.

### The curated interaction cases + their minted goldens

- `parity/cases/curated.py` — four multi-step cases. Each: `!inventory` /
  `!creatures` opens the hub (session-minted category buttons) → a
  `component_index` click opens the detail/dex panel → an explicit
  `nav:browse:*` browse-control click (with `values` for the selects)
  re-renders. The seeded category is the only non-empty one, so its hub
  button is `component_index` 0; the member views their OWN inventory so the
  detail provider's target defaults to the actor. Inventory seed rides
  `fixture_sql` (the D-0073 btd6_strategies-insert precedent).
- `parity/goldens/inventory/inventory_browse_sort_quantity.json` — sort
  select: Mining Materials default rarity order (Diamond/Gold/Iron/Stone/
  Wood) → pick `-quantity` → **Iron 50 / Wood 7 / Gold 5 / Stone 3 /
  Diamond 1** (highest-first). The re-render reorders — the sort path.
- `parity/goldens/inventory/inventory_browse_filter_ore.json` — type
  filter: all 5 items → filter `Ore` → **Gold/Iron/Stone** only. The
  re-render drops the two non-Ore items — the filter path.
- `parity/goldens/inventory/inventory_browse_page_next_prev.json` — page
  buttons: 11 items in `Other` (page_size 8 → two pages) → next (**items
  9–11**) → prev (**back to items 1–8**). Both page-turns + the
  bound-disable states — no single catalogue category holds >8 items, so
  the 11-item `Other` seed is the only way to force a second page.
- `parity/goldens/creature/creature_dex_filter_element.json` — dex element
  filter: default first page (Ember creatures) → filter `Stone` → **the six
  Stone creatures** (Gravelpup, Pebblet, …). The dex renders all 36 catalog
  creatures caught-or-not, so no seed is needed for the filter to differ.
- `parity/parity.yml` — `source.minted_goldens` 6 → 10 (+ the accounting
  comment: on-disk corpus 468 → 472 = 465 imported + 10 minted − 3
  retired); a provenance comment on the batch. **Ratchet UNTOUCHED** — the
  browse clicks are read-only re-renders that add no declared event / table
  / setting surface (`check_parity_depth --write-ratchet` would be a no-op).
- Count pins: `tests/unit/parity_adapter/test_replay_adapter.py` (468 →
  472, + two focused round-trip tests for the click-`values` vocabulary)
  and `tests/unit/parity_gate/test_check_parity_depth.py` (corpus count +
  the `minted_goldens` pin + the report-leg "N goldens" string).

## Minting mechanics (how, faithfully)

- The browse controls carry STATIC `nav:browse:*` ids (browserview.encode)
  that fully encode `{panel, block, sort, filter, page}`, so a browse click
  re-renders purely from its custom_id + the select's `values` — the
  component adapter routes it through `handle_nav → _handle_browse →
  _render_and_present`, which presents a FRESH panel (no `edit_message_ref`)
  — the new bot's genuine browse re-render shape, pinned as-is.
- The detail/dex panel opens as an interaction FOLLOWUP, which the capture
  harness does not mint into the `minted` targeting list (only channel
  sends carry a `response_id`). The browse click therefore anchors on the
  already-minted hub message; because the re-render is driven entirely by
  the custom_id (not the anchored message), the captured bytes are
  identical to a click on the detail message — the anchor is invisible in
  the golden (the response records only the interaction + the new panel).
- Minted via `capture_case` then `apply_dispositions` (idempotent) so the
  stored docs are exactly the post-disposition corpus truth: the kernel
  spine (audit_log / event_outbox / ai_decision_audit + command.dispatched
  / audit.action_recorded), the invoking-message delete, and the
  xp-coins-alias column are stripped — matching D-0073's discipline (a
  new-bot capture must not enshrine new-code audit bytes). Only the domain
  `xp` delta from the opening command survives.

## Evidence (local — Postgres restored, so the full gate ran)

- `run_golden_parity --gate` → **GREEN — all 416 golden(s) across 51 ported
  subsystem(s) replay clean** (was 412; +4 mine). Run ALONE — an earlier
  run concurrent with the pytest suite hit Postgres `DeadlockDetectedError`
  on four unrelated cases (DB contention, not a diff); re-run clean.
- `pytest tests/ -q` → **1796 passed, 5 skipped**.
- `check_parity_depth` → **OK — 51 subsystems (50 ported), kernel ported,
  472 goldens**.
- `check_compat_frozen` → OK (compat pin unchanged); `check_sim_gate` → OK;
  `manifest_compile --write` → no snapshot drift (no spec/manifest touched);
  `check_namespace` / `check_escape_hatches` / `check_schema_growth` /
  `check_amendments` / `check_symbol_shadowing` / `check_no_skip` /
  `check_config_usage` → all clean.
- `bootstrap.py check --strict` → **all checks passed** (the only advisories
  are PRE-EXISTING and NOT mine: the `control/status.md` owner-action
  risk-class advisory, never exit-affecting; the base's
  `browse-surfaces-convert.md` missing-`Previous-session review` line
  belongs to another lane — this card carries its own review section).

## ⚑ Flags (owner hand-pass)

- **These goldens pin the NEW BrowserView contract, not an oracle** — like
  the D-0075 kernel band, there is no old-bot oracle for these exact browse
  renders (the shipped chrome differed — a per-tier grouped view / cycling
  sort button vs the generic flat list + selects, the owner presentation
  hand-pass ledgered in the slice-2/3 panel specs). They are regression
  tripwires: a DELIBERATE render change re-mints them in the same PR; an
  ACCIDENTAL one reds the gate.
- **Seed added (fixture_sql):** the three inventory cases seed the member's
  `inventory` rows — five Mining Materials (varied type + rarity + quantity
  so `-quantity` reorders and `Ore` filters to three) and eleven `Other`
  trinkets (the only way to force a 2-page detail; no catalogue category
  holds >8 items). Via the sanctioned per-case `fixture_sql` seam (the
  D-0073 precedent), reset per case. The dex case needs no seed.
- **Presentation note — browse re-render is a fresh send, not an in-place
  edit:** `_render_and_present` presents without `edit_message_ref`, so
  each browse click sends a new panel rather than editing the current one.
  That is the new bot's current armed behavior (not an artifact of this
  capture); the goldens pin it faithfully. If an in-place edit is the
  desired UX, that is a BrowserView engine change (a separate slice) that
  would re-mint these four — flagged, not silently absorbed.
- **Nothing golden-blocked / nothing skipped:** all four target controls
  (inventory sort + filter + page, dex element filter) are captured; the
  optional page-prev/bounds case was folded into the page golden (next →
  prev in one faithful multi-step) rather than a fifth file.

## ⟲ Previous-session review

Slice 3 (`dex-browse`) closed with a `## 💡` that named the remaining
browse surfaces as the successor shape and warned of the truncation
footgun — but the deeper carry it left was the golden posture: slices 1–3
armed the surfaces with ZERO golden churn precisely BECAUSE no golden
clicked a browse control, which is exactly the blind spot this capstone
exists to fix. Its Postgres framing was the load-bearing correction —
dex-browse recorded `run_golden_parity --gate` as "RED only on the local
binding failure (asyncpg not installed) — runs in CI" and sidestepped the
mint infra entirely. That framing was HALF right (the arming needed no
mint) but would have BLOCKED this capstone (which cannot be honestly
completed without a green local gate). Restoring the wiped Postgres cluster
(Step 0) turned that inherited "infra gap" into a running gate — the mint
is a faithful capture verified locally, not a hand-written JSON forced past
a dark gate. Slice 2's `fixture_sql`/`component_index` patterns (blackjack)
and slice 3's `nav:browse:*` static-id grammar were the exact primitives
the cases needed; nothing had to be re-armed.

## 💡 Session idea

The click-`values` vocabulary now armed means these four goldens are the
LAST that must be curated: a future select golden whose OPENING step is
itself a static/command surface (not a session hub button) is fully
RECONSTRUCTABLE — `_step_from_input` now rebuilds the `values`, so it needs
no `curated.py` entry, exactly like the D-0073 modal goldens. The one
remaining infra gap for reconstructable interaction goldens is the
interaction-FOLLOWUP targeting hole (a followup panel is untargetable by
ordinal because it carries no `response_id`); arming `record` to mint a
followup message id would let a browse click target the real detail message
and drop the hub-anchor indirection — a small, gate-verifiable harness
enabler for whoever mints the next interactive surface's goldens.
