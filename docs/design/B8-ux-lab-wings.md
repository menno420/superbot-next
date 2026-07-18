# B8 — ux_lab 9-wing foundation-then-per-wing port approach

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the remaining port lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`, B8 row). This is a
> PLAN, not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line` at
> HEAD `b39a37f` unless noted. Oracle internals (the shipped `disbot/views/ux_lab/*`
> browser + the `utils/ux_patterns` registry) are named as the sb-side docstrings and
> tests reference them; their exact line shapes are confirmed at port time against the
> parity goldens, not asserted here.

## TL;DR

`ux_lab` is the shipped zero-write interface gallery. Its **home panel is fully
ported** — golden-pinned bytes, nav row, footer override, all nine wing buttons
present (`sb/domain/ux_lab/panels.py`, proven by
`tests/unit/band6/test_band6_ux_lab_home.py`). What is *not* ported is the nine wing
**interiors**: every wing click lands on a declared, honest pending refusal
(`sb/domain/ux_lab/handlers.py:50-63`), never a silent stub. Because the surface is
**admin-only** (`audience_tier="administrator"`) and **zero-write** (CI-fenced), this
is the completeness snapshot's one remaining **LOW-priority** larger surface — no
user-facing gap. But it is the *last visible* port surface, so the owner deserves a
real approach to decide against.

The approach is **foundation-first**: one Slice 0 ports the pattern **registry** and
the **exhibit-browser grammar** into the panel engine — which the engine already
mostly has (`BrowserView` paging, `SelectWindow`, edit-in-place refresh, image /
attachment carriers). Slice 0 also lets the home `_EXHIBITS` count line **re-derive**
instead of shipping a pinned literal (`sb/domain/ux_lab/panels.py:77-81`). Then each
wing is an **independent** per-wing slice, sequenced easiest→hardest: **embeds** first
(pure static — the cleanest mint, the proof slice); then the other mintable renders;
and **defer** the three special wings (image bytes / discord.py-version+live-errors /
channel-side CV2 send) behind either a render-only port or a scoped special slice each.
A sound stopping point is **foundation + embeds as proof**, parking the rest behind
owner priority.

## Problem

### The surface today

The home front door is complete. `!uxlab` / `/uxlab` opens `ux_lab.home`
(`sb/domain/ux_lab/handlers.py:20-39`), a session-lifecycle panel with the shipped
blurple Home card, the two-paragraph zero-write blurb, the `Exhibits` coverage line,
the `How to browse` field, the plan-doc footer, and the nine wing buttons over three
layout rows (`sb/domain/ux_lab/panels.py:111-162`). The manifest confirms the surface
is deliberately write-free: `MANIFEST.stores == ()`, `MANIFEST.events == ()`,
`MANIFEST.settings == ()`, asserted by
`tests/unit/band6/test_band6_ux_lab_home.py:177-179`.

Every wing button, however, routes to a **pending terminal**. `_register_pending()`
binds all nine handlers to `pending_handler(...)` refusals
(`sb/domain/ux_lab/handlers.py:42-63`):

- `ux_lab.buttons_wing`, `ux_lab.selects_wing`, `ux_lab.modals_wing`,
  `ux_lab.embeds_wing`, `ux_lab.components_v2_wing`, `ux_lab.pil_cards_wing`,
  `ux_lab.mock_studio_wing`, `ux_lab.probe_bench_wing` — each carries the shared
  `"'s exhibit browser ports with the lab's wings slice."` tail;
- `ux_lab.compare_wing` — `"⚖️ The Compare panel ports with the lab's wings slice."`

These are **honest refusals**, not silent stubs: the test
`test_wing_clicks_land_on_the_polite_pending_terminal`
(`tests/unit/band6/test_band6_ux_lab_home.py:210-220`) asserts `reply.outcome ==
BLOCKED` with the wing name in the message. The home panel's own docstring records the
under-port deliberately: the `_EXHIBITS` line "is registry-derived
(`category_counts()` over the 64-pattern registry); the wings' exhibit browsers are
their own slice, so the golden-pinned literal ships here and re-derivation lands with
the wings" (`sb/domain/ux_lab/panels.py:20-24, 74-81`).

### Why this is LOW priority

Two independent gates make the gap invisible to users:

1. **Admin-only.** Every wing button declares `audience_tier="administrator"`
   (`sb/domain/ux_lab/panels.py:107`), and the command front doors are gated the same
   (`tests/unit/band6/test_band6_ux_lab_home.py:167,173`). This is a developer /
   diagnostic workbench, not a member-facing feature.
2. **Zero-write, CI-enforced.** The Home card copy states it verbatim — "the lab never
   writes to the database or changes the server (CI-enforced)"
   (`sb/domain/ux_lab/panels.py:66-72`) — and the empty `stores`/`events`/`settings`
   manifest is fence-tested (`test_manifest_declares_the_home_entry_points`). Any wing
   port must **stay inside that fence**: read-only renders and ephemeral interaction
   echoes only, never a persisted effect.

The completeness snapshot files B8 accordingly: **OPEN, LOW priority**, "No
user-facing gap (honest refusals)" (`docs/status/completeness-table-2026-07-18.md`
B8 row). It is the only remaining *larger* surface, but it is a diagnostic one.

### The decision to frame

So the owner is choosing between three postures, not being handed a mandatory port:

- **(A) Port the wings** — restore the shipped exhibit browsers so the admin gallery
  is fully live. Highest fidelity; most effort (esp. the 3 special wings).
- **(B) Render-only port the hard ones** — port the mintable wings fully, and for the
  special wings render the exhibit *content* but leave the live action a declared
  refusal. Middle cost; keeps the fence trivially.
- **(C) Leave declared-refused** — the honest pending terminals already ship and read
  well; do nothing until a higher-priority need appears.

This doc's recommendation (see Rough size) is a **staged (A) with a (B)/(C) tail**:
build the foundation + one proof wing, then let priority decide the rest.

## Proposed approach

Two phases. **Foundation first** (one slice), then **independent per-wing slices**
sequenced easiest→hardest. Every slice respects the layer rules in `.claude/CLAUDE.md`
(the browser grammar is kernel-level in `sb/kernel/panels/*`; the registry + per-wing
exhibit data live in `sb/domain/ux_lab/*`; no kernel→domain edge) and the zero-write
fence.

### What the panel engine already offers vs what a wing needs

The shipped `ExhibitWingView` is a stateful browser: ◀ ▶ pagination, a page counter, a
🏠 home button, a per-exhibit spec-card append, and **edit-in-place** (the view edits
its own message rather than sending a new one). The panel engine **already ships most
of that grammar**:

- **Pagination + counter + bounds** — the `BrowserView` engine renders prev/next page
  buttons plus a disabled page indicator over a declared List/Table block, state
  round-tripping through the `nav:browse:` custom-id family
  (`sb/kernel/panels/browserview.py:1-45, 55-90`). This is the paging/counter half of
  a wing, already generic and router-wired.
- **Edit-in-place** — session-lifecycle panels already refresh by **editing** the same
  message instead of re-sending (the "shipped in-place game-view edit" refresh on the
  render model, `sb/kernel/panels/render.py:238-240`); the home panel already sets
  `session_lifecycle=True` (`sb/domain/ux_lab/panels.py:147`).
- **🏠 home / nav** — the standard nav row already carries a home affordance
  (`nav:hub:*`), pinned live on the home panel
  (`tests/unit/band6/test_band6_ux_lab_home.py:117-122`).
- **Windowed selects** — the `SelectWindow` engine pages any >25-option select
  (`sb/kernel/panels/selectwindow.py:1-25`) — directly reusable by the Selects wing.
- **Images + attachments** — the render model already carries an embed hero image
  (`RenderedEmbed.image_url`, `sb/kernel/panels/render.py:196-200`) and file
  attachments (`RenderedAttachment` bytes, `:209-217`; `RenderedPanel.attachments`,
  `:229-231`) — the carriers the PIL/mock wings need already exist.

What is genuinely **missing** is the **exhibit model**: a wing page is not a row in a
list — it is a live, pressable component demo *plus* its spec card. So the foundation
slice adds an **exhibit-page grammar** (a wing = an ordered set of exhibits, each an
embed + a live component group + an appended spec card, paged by the existing
`nav:browse:` machinery) and the **pattern registry** the spec cards read from.

### Slice 0 — Foundation (the registry + the exhibit-browser grammar)

Port two things, together, because each is useless without the other:

- **The pattern registry** (`utils/ux_patterns` → a kernel/spec-appropriate leaf, e.g.
  `sb/spec/ux_patterns.py` or a `sb/domain/ux_lab/patterns.py` data module depending on
  who must read it). The shipped `PatternSpec` / `register()` / `category_counts()` /
  `get_spec()` / `spec_card()` grammar becomes declared pattern data + a pure
  count/lookup/card-render API. `category_counts()` is what the home panel's
  `_EXHIBITS` line is *supposed* to derive from — porting it here closes the pinned
  literal (below).
- **The exhibit-browser grammar** — an `ExhibitWingView` analogue expressed over the
  existing `BrowserView`/session-refresh machinery: a wing spec declares its ordered
  exhibits; the engine renders exhibit *k* (embed + live components + `spec_card`
  append) with ◀ ▶ / counter / 🏠, editing in place on flip. This lives in
  `sb/kernel/panels/*` (generic, no ux_lab knowledge) so any future gallery-shaped
  surface can reuse it, exactly as `BrowserView` and `SelectWindow` are domain-free.

**Re-derive the home literal.** Once `category_counts()` is available, the home
`_EXHIBITS` line stops being a pinned literal (`sb/domain/ux_lab/panels.py:77-81`) and
is computed from the registry — the module docstring already promises this
(`:20-24`). Small, satisfying, and it removes a golden-drift risk.

**Size:** M. Two ported primitives + the home re-derive + goldens for the empty
browser shell. It is the load-bearing slice; every wing depends on it and nothing
else does.

### Per-wing slices (independent, easiest → hardest)

Each wing is its own slice on top of Slice 0, mergeable in any order. Characterizations
are from the completeness snapshot's B8 row and the sb-side wing names; the exact
exhibit inventory is confirmed against the parity goldens at port time.

**Proof slice — embeds** (pure static render; the cleanest mint). The Embeds wing is
static embed exhibits — no live callback state, no image bytes, no non-determinism.
It is the ideal first wing: it exercises the whole Slice 0 grammar (pages, counter,
🏠, spec card) with the least surface, so it **proves the foundation** end-to-end and
becomes the template every other wing copies. **Size: S.**

**Mintable renders** (interactive but deterministic; each an S wing after the proof):

- **buttons** — button exhibits; the press echoes an ephemeral, zero-write reaction
  (the "reacts when you press it" blurb). Straightforward once the exhibit grammar
  carries a live component group.
- **selects** — select exhibits; reuses `SelectWindow`
  (`sb/kernel/panels/selectwindow.py`) directly for any >25-option demo.
- **modals** — modal exhibits; the shipped modal open + a zero-write echo of the
  submitted values. Slightly more wiring (modal round-trip) but deterministic.
- **mock_studio** — the Q-0108–Q-0112 mock exhibits (`_EXHIBITS` names "Mock studio
  **9**"); static-ish mock renders, mintable as embeds/components.
- **compare** — the ⚖️ Compare panel (its own refusal string,
  `sb/domain/ux_lab/handlers.py:62-63`); a side-by-side static comparison render, no
  live state.

**Defer — special handling** (each M; recommend render-only port or a scoped slice):

- **pil_cards** — **image bytes + timing.** PIL-rendered card exhibits produce PNG
  bytes; the carriers exist (`RenderedAttachment`, `RenderedEmbed.image_url`) but the
  *generation* is non-trivial and the **golden strategy for image output is an open
  question** (byte-exact vs shape-only). Render-only port (show a pre-rendered sample /
  describe the card, action declared-refused) is the cheap honest option.
- **probe_bench** — **non-deterministic by nature.** The 10-probe bench reports
  discord.py **version**, the current **date**, and **live error** conditions
  (completeness B8 row). These cannot be golden-pinned byte-for-byte without freezing
  clock/version. Needs either injected deterministic sources (a `Clock`/version seam)
  or a render-only port that states the probe and refuses the live read.
- **components_v2** — **channel-side send + external CDN URLs.** The Components V2 wing
  involves a channel-side send of CV2 layout and external CDN image URLs — the closest
  to a real *effect*, so it is the most fence-sensitive. Recommend render-only (echo
  the layout as an ephemeral, no channel send) or a carefully scoped special slice that
  keeps every byte inside the zero-write fence.

For all three, the honest cheap posture is **render the exhibit content, leave the
live action a declared refusal** (posture B) — the surface stays truthful and the
fence stays trivially intact.

## Affected surfaces

| Band | Files | Slice |
|---|---|---|
| kernel / panels | new exhibit-browser grammar leaf in `sb/kernel/panels/*` (reusing `browserview.py` paging + session-refresh) | Slice 0 |
| spec / domain | pattern registry (`utils/ux_patterns` → `sb/spec/ux_patterns.py` or `sb/domain/ux_lab/patterns.py`): `PatternSpec`, `register`, `category_counts`, `get_spec`, `spec_card` | Slice 0 |
| domain / ux_lab | `sb/domain/ux_lab/panels.py:77-81` — `_EXHIBITS` re-derives from `category_counts()` (drops the pinned literal) | Slice 0 |
| domain / ux_lab | `sb/domain/ux_lab/handlers.py:50-63` — each wing's `pending_handler(...)` replaced by (or, for special wings, kept alongside) its exhibit-wing panel handler | per-wing |
| domain / ux_lab | per-wing exhibit data + panel specs (new `sb/domain/ux_lab/wings/*` or per-wing spec functions) | per-wing |
| tests / goldens | per-wing exhibit-render goldens; the Slice 0 empty-browser golden; the re-derived `_EXHIBITS` assertion in `tests/unit/band6/test_band6_ux_lab_home.py:115` | Slice 0 + per-wing |
| fence | the zero-write manifest fence (`test_manifest_declares_the_home_entry_points`) stays green — `stores/events/settings` remain `()` | every slice |

No change outside `sb/kernel/panels`, `sb/spec`, `sb/domain/ux_lab`, and their tests —
consistent with the layer map (kernel grammar stays domain-free; ux_lab data stays in
its domain band; no kernel→domain edge).

## Rough size + suggested slicing

- **Slice 0 — foundation (registry + exhibit-browser grammar + home re-derive)** —
  **M**. Load-bearing; land first, standalone. Everything else depends on it.
- **embeds (proof)** — **S**. The first wing; proves the foundation end-to-end and
  becomes the per-wing template. Land second.
- **buttons / selects / modals / mock_studio / compare** — **S each**, independent.
  Land opportunistically, any order, once the proof holds.
- **pil_cards / probe_bench / components_v2** — **M each**, special handling; each
  wants its own slice and an owner call on render-only-vs-full and the golden strategy.

**Suggested landing order:** Slice 0 → embeds → (mintable wings, any order) →
special wings last (and only if the owner wants full fidelity).

**Recommended stopping point.** Because the surface is admin-only + zero-write with
*honest* refusals already shipping, a clean, defensible stop is **Slice 0 + embeds as
proof**: it demonstrates the foundation works, re-derives the home literal (a real
correctness win independent of the wings), and converts one wing — then **park the
remaining eight behind explicit owner priority**. The mintable five are cheap to pick
up later; the special three are the only genuine new engineering and may never clear
the bar against the resilience/observability tracks.

## Open questions for the owner

1. **Is a dev-only diagnostic surface worth porting at all right now?** ux_lab is
   admin-only and zero-write; the wings front honest refusals, so nothing is broken.
   Does the "last visible port surface" pull justify the effort over the
   resilience/observability lanes (D4 etc.), or does B8 stay parked as declared-refused
   (posture C)?
2. **Full port vs render-only for the three special wings?** For pil_cards /
   probe_bench / components_v2, is a **render-only** port (show the exhibit, leave the
   live action a declared refusal — posture B) acceptable, or do you want full-fidelity
   live behavior (image generation, live probes, channel-side CV2 send) inside the
   zero-write fence?
3. **Golden strategy for image / probe / CV2 output.** How should non-deterministic /
   binary output be pinned? Options: byte-exact goldens with frozen clock+version+PIL,
   shape-only goldens (assert an attachment named `X.png` exists, not its bytes), or
   deterministic injected sources (a `Clock`/version seam for probe_bench). This choice
   sizes the three special wings materially.
4. **Priority vs the resilience/observability tracks.** Where does B8 sit against the
   D1–D6 planning lanes? The recommendation is to build Slice 0 + embeds as a proof and
   let priority decide the tail — do you want even that proof now, or is B8 a
   later-quarter item?
5. **Registry home — spec leaf or domain data?** Should the ported pattern registry
   live in `sb/spec/*` (if a kernel/spec consumer must read `category_counts()`) or as
   `sb/domain/ux_lab/*` data (if only the ux_lab domain reads it)? The re-derived home
   `_EXHIBITS` line is the deciding consumer — it is rendered by the ux_lab panel
   provider, which argues for the domain band unless another surface needs the counts.
