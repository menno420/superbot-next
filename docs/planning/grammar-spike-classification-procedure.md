# Per-band grammar-spike classification procedure (V-2)

> **Status:** `reference` — the layer-V step-11 deliverable (canonical plan
> §5 step 11: "write the per-band grammar-spike classification procedure"),
> 2026-07-08. The measurement it extends lives in the oracle repo:
> `superbot:tools/grammar_spike/` (measure.py UNITS ledger + RESULTS.md —
> 85.26% tier-1/2 fit over 95 units, verified live, conditional on the
> folded G-1…G-5 families). V-2 RETIRES at cutover per A-19: the mechanical
> tier-3 count (`tools/check_escape_hatches.py` + its committed baseline)
> is its permanent successor.

## What V-2 measures

The declarative bet: what fraction of a subsystem's SURFACE UNITS the
frozen grammar expresses at tier 1 (generated, zero code) or tier 2
(declared-parameterized data) — versus tier 3 (escape-hatch code with
`justification`). The number is a hand-classified JUDGMENT ledger, so a
per-band re-run means **extending the UNITS ledger**, never re-deriving the
method. This document is that method.

## The unit vocabulary (frozen — from the spike)

One row per *surface unit*, kinds exactly as the spike used them:
`command` · `panel` · `panel-action` · `setting` (×N for identical
families) · `binding` (×N) · `resource` (×N) · `subscription` (×N) ·
`listener` · `event` · `store` · `handler` · `provider` · `renderer` ·
`session` · `game` · `engine` · `help`. Multiplicity rows (e.g.
`setting×7`) count N units in totals.

## The tier semantics (design-spec §2.9 — verbatim discipline)

- **Tier 1**: a kernel workflow parameterized entirely by specs (setting
  edit, binding set, open-panel, provisioning, toggles, help projection).
- **Tier 2**: a typed spec family makes the unit pure data (LeaderboardSpec,
  session lifecycle specs, list-valued settings, AnnouncementRouteSpec…).
- **Tier 3**: real registered code — a `HandlerRef`/`EngineRef`/
  `renderer_override`/`legacy_view` with a non-empty `justification`.
  Game rules and thin domain seams are tier 3 BY DESIGN, honestly.

## The per-band procedure (run at each port band's manifest declaration)

1. **Enumerate before classifying.** Derive the band's unit rows from the
   walk row + the old-bot source enumeration (commands incl. aliases,
   panel actions by custom_id, settings keys, listeners, stores, events) —
   never from memory. The parity goldens' case list is a cross-check: a
   golden that drives a surface with no unit row means the enumeration is
   short.
2. **Classify against the grammar AS FROZEN in this repo** (sb/spec/* at
   the band's base SHA) — one `tier` column only. The spike's dual
   spec/proposed columns are DONE: G-1…G-5 either landed in the frozen
   grammar or died; classify against what exists, and record a missing
   spec family as tier 3 with the family named in the rationale (that
   pressure signal is the point of the measurement).
3. **One-line rationale per row**, naming the kernel workflow / spec
   family / escape-hatch class that carries the unit (the spike's
   RESULTS.md rows are the format precedent).
4. **Append, never rewrite.** The band's rows extend the cumulative
   ledger; prior bands' classifications are only revised with a ledger
   note (what re-classified, why — usually a spec family landing later).
5. **Compute the band + cumulative fit** (tier-1/2 unit share, weighted by
   multiplicity) and compare against the 85% spike line. A band falling
   materially under it is a grammar gap to NAME (propose the tier-2
   family), not a number to massage.
6. **Cross-check against the mechanical count**: the band's tier-3 rows
   must reconcile with `check_escape_hatches`' generated report for the
   same manifests (every tier-3 unit ⇒ a justified registration; a
   registration with no unit row ⇒ the enumeration is short). This is the
   A-19 successor discipline being warmed up before it takes over at
   cutover.

## Where the ledger lives

The cumulative rebuild-side ledger starts at band 1 as
`tools/grammar_fit/measure.py` (the spike's `Unit` dataclass + `compute()`
shape, single `tier` column) generating `tools/grammar_fit/RESULTS.md` —
built by the band-1 worker with its first rows; minting it empty now would
just rot. Until then the oracle repo's spike is the sole ledger.

## Related

- design-spec §2.9 (tiers + ratchet) / §10.1 risk 5 (the ~80% hypothesis)
- canonical plan §2.2 V-2 row + §11b A-19 clause (V-2 retires at cutover)
- [decisions.md](../decisions.md) D-0020 (this deliverable's ledger entry)
