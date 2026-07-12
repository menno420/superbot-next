# 2026-07-12 — arm the creature dex browse surface (D-0034, slice 3)

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · feature build (D-0034 slice 3 — dex/creature)

## Scope

Slice 3 of the UI-restoration lane, STACKED on slice 2
(`browse-surfaces-convert`, PR #279 → the engine PR #270, both unmerged).
Slice 2 armed the SHARED BrowserView engine's auto-arm hook
(`default_browse_state` + the `_render_and_present` open-hook) so a
DECLARED `ListSpec`/`TableSpec` panel arms its sort/filter/page controls
just by being declared. Its 💡 named the successor exactly: "the next
surface's conversion is pure DECLARATION — give it a `ListBlock` + a row
provider and it arms itself." This session is that successor for the
**dex/creature** surface.

## Step A — oracle verification gate (done FIRST)

The prior surface in the plan (leaderboards) was SKIPPED as a degenerate
oracle (static top-10, no controls). Applied the same test to dex.

Oracle (`menno420/superbot`, read via raw):
- `disbot/views/creature/menu.py` — `CreatureDexView`: row 0 is a
  `_ElementFilterSelect` (a real element FILTER — "All elements" +
  one option per `ELEMENTS`), row 1 a Back button. **No sort control.
  No pagination.**
- `disbot/views/creature/embeds.py` — `build_dex_embed(display_name, log,
  level, *, element=None)`: `element` filters the grouped per-element
  fields; no slicing/sort.
- `disbot/cogs/creature_cog.py` — `!dex` sends `build_dex_embed(...)` with
  **no view** (`await ctx.send(embed=embed)`); the INTERACTIVE view is the
  hub Dex button only.

**Verdict: PROCEED.** The dex has GENUINE interactivity — a real
single-select element filter (All + 6 elements). That is materially
unlike the degenerate leaderboard. Derived the algebra EXACTLY from the
oracle: element FILTER only, NO sort, NO pagination (never invented).

## Delivered (domain layer only — no kernel edits)

- `sb/domain/creature/panels.py`:
  - `dex_line(creature, count)` / `dex_row(creature, count)` — the browse
    ROW: `{element, _line}`. `_line` is the shipped `build_dex_embed`
    per-creature line VERBATIM (`{emoji} **{name}** ×{n}` or `{emoji}
    {name} — *not yet caught*`); `element` is the declared filter value.
    NO sort key (the shipped dex declares no sort).
  - `creature.dex_rows` provider (emits rows GROUPED by element — the
    shipped six-field fold — within-element in catalog order) +
    `creature.render_dex_line` item renderer (row → `_line`).
  - `dex_browse_spec()` → panel `creature.dex`: a `ListBlock` whose
    `ListSpec` DECLARES `filter_options` = the oracle's `ELEMENTS`
    (`dict.fromkeys(c.element for c in CREATURES)` = Ember, Stone, Gust,
    Tide, Spark, Bramble — the golden's dex field order), `sort_options=()`,
    `default_sort=""`, `page_size=18`. No `renderer_override` (so the
    inherited auto-arm hook fires); `NavigationSpec(parent=creature.hub)`
    (the shipped Back button); `session_lifecycle=True` (a timeout view,
    like every sibling creature panel).
  - the hub Dex button repointed `HandlerRef("creature.dex_view")` →
    `PanelRef("creature.dex")` (the shipped hub Dex opened the INTERACTIVE
    view; the `!dex` COMMAND keeps the static grouped card). Repointing the
    action's route never touches the hub's rendered bytes.
- `sb/manifest/creature.py` — `creature.dex` added to the panels tuple.
- `manifest.snapshot.json` — regenerated; scoped diff (+78): the new panel
  + provider + line-renderer refs + the hub Dex action's `$ref` flip
  (`handler:creature.dex_view` → `panel:creature.dex`). No frozen compat
  field changed.
- Tests: `tests/unit/band6/test_band6_creature_panels.py` — 8 new
  (dex_line verbatim, dex_row shape, the browse spec's declared algebra,
  auto-arm, element-grouped provider rows + caught count, per-element
  filter, paginate-every-creature-without-truncation), plus the
  compile-fence / refs / manifest-panel-set / hub-route assertions
  extended.

## Golden posture — ZERO churn (no re-mint needed)

Deliberately arms ONLY the path NO golden exercises:
- `sweep_dex` = the `!dex` COMMAND → the static grouped card
  (`creature.dex_card`, untouched) — byte-identical. The oracle `!dex`
  sent an embed with `components: []`; that stays.
- `sweep_creatures` = `!creatures` OPENS the hub and never CLICKS the Dex
  button — byte-identical (repointing the button's route is not a rendered
  byte).
No golden reaches `creature.dex`, so no re-mint. `git status` proves every
golden byte-identical (468 goldens, `check_parity_depth` unchanged). This
sidesteps the local golden-mint infra gap (no Postgres/asyncpg) entirely —
had a golden churned it would have needed a CI mint.

## Evidence (local; golden replay is CI-only — no local Postgres)

- `pytest tests/ -q` → **1784 passed, 8 skipped**.
- `check_compat_frozen` → **OK — compat artifacts match the pin**.
- `check_parity_depth` → **OK — 51 subsystems (50 ported), kernel ported,
  468 goldens**.
- `check_sim_gate` → OK; `check_namespace` → clean; `check_money_race` →
  OK (0 violations); `check_schema_growth` → clean; `check_no_skip` →
  clean; `check_symbol_shadowing` → clean; `check_escape_hatches` → clean;
  `check_amendments` → OK; `check_config_usage` → clean;
  `check_metric_cardinality` → clean; `check_egress` → clean;
  `manifest_compile` → green.
- `run_golden_parity --gate` → RED **only** on the local binding failure
  (`Postgres unavailable: asyncpg is not installed`); runs in CI. **No
  golden file changed.**
- `bootstrap.py check --strict` → the ONLY exit-affecting line is a
  PRE-EXISTING one on `.sessions/2026-07-12-browse-surfaces-convert.md`
  (missing `Previous-session review`) — confirmed identical on the clean
  base (stash-verified); not introduced here. Plus the pre-existing
  `control/status.md` owner-action advisory (never exit-affecting).

## ⚑ Flags (owner hand-pass)

- **Presentation deviation (owner sign-off):** the generic engine renders
  a FLAT list (element-grouped emission) with a SELECT element filter + a
  page indicator; the shipped `CreatureDexView` used a select + a Back
  button over SIX per-element embed FIELDS and NO pagination. Two forced
  consequences of riding the generic engine, both DATA-faithful:
  (1) **flat list vs grouped fields** — the engine has no grouped-field
  render (the inventory-detail precedent); (2) **a page control the oracle
  lacked** — the engine renders a list into ONE ≤1024-char description; the
  shipped 36 creatures were six separate ≤1024-char fields, so the all-view
  MUST page (18/page, element-aligned) to keep EVERY creature visible
  without truncation. The genuine shipped interaction — the element FILTER
  — is armed verbatim (All + the six `ELEMENTS`). The "All" pseudo-option
  label is the engine's generic `All` (the shipped select said "All
  elements"): kernel-owned chrome, not editable from the domain layer.
- **Title/description/footer flattening:** the browse panel has a static
  title ("🐾 Creature Dex", no per-member name), no counts/level
  description (that live-progress context is on the hub's "Your progress"
  field), and a subsystem footer (the shipped literal "🐾 Catch to hunt · 🏆
  Ladder…" is outside FooterMode's vocabulary without an override, and an
  override would disarm the browse hook). Same class as inventory detail.
- **Oracle copy provenance:** the per-creature line + the element set are
  reconstructed from raw fetches of the oracle `menu.py` / `embeds.py` /
  `creature_cog.py` (paths cited in the PR); the line format matches the
  existing `sweep_dex` golden bytes (byte-anchored). No oracle number
  invented.
- **Claims:** `control/claims/` had no active creature-lane claim at start
  (only `browse-surfaces-convert` [inventory + kernel] and
  `browserview-engine-k8` [kernel]) — no collision on
  `sb/domain/creature/`. Claimed `dex-browse`.

## ⟲ Previous-session review

Slice 2 (`browse-surfaces-convert`) landed the auto-arm-by-declaration
policy and named THIS conversion as "pure DECLARATION." That held exactly:
zero kernel edits were needed — declaring a `ListBlock` + a row provider
armed the surface through the inherited hook. Its inventory-detail
conversion was the byte-for-byte template for the row shape (`_line`
carrier), the item-render-ref pattern, and the presentation hand-pass
framing (flat list + generic controls). One place this session went
FURTHER than slice 2's guidance: slice 2 could arm inventory with no
golden churn because its golden hit the empty hub; dex's `sweep_dex` hits
the surface directly, so the conversion had to be routed to the
hub-button path (which no golden exercises) rather than the `!dex` command
path — restoring the oracle's own command-static / button-interactive
split that the parity flip had collapsed. Net: arming with zero golden
churn AND higher oracle fidelity.

## 💡 Session idea

The remaining named surfaces (fishlog, recipe browsers) are the same
successor shape — but each needs its Step-A oracle gate FIRST: only arm
what the oracle actually made interactive, and route the arming to a path
no golden pins (a new panel + a repointed affordance) so the conversion
stays golden-churn-free until a deliberate re-mint is warranted. Guard
recipe for the truncation footgun: a browse `ListBlock` whose full,
unfiltered item count × avg line length exceeds ~1024 chars will silently
truncate the last rows (render.py `_render_body`, the `budget =
min(field_budget_chars, FIELD_VALUE_LIMIT)` clamp on the list branch);
size `page_size` so a page fits, or add a `test_*_paginates_without_
truncation` assertion (see `test_dex_browse_paginates_every_creature_
without_truncation`) — a full-catalog page_size is a truncation trap.
