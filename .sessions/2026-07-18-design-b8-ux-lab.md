# 2026-07-18 — B8 ux_lab wings foundation-then-per-wing design doc

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · docs · B8 ux_lab wings foundation-then-per-wing design doc (born-red, holds substrate-gate)

## Scope

The completeness-reconciliation snapshot (`docs/status/completeness-table-2026-07-18.md`,
#525) found the user-facing port surface essentially exhausted and recommended
shifting the loop toward **PLANNING mode** — turning the D1–D6 forward lanes plus a
couple of decision-sized backlog items into fuller design docs the owner reacts to
and prioritizes. This slice is a member of that planning-mode design-doc series: the
**B8 ux_lab 9-wing** design doc, designing the PORT APPROACH (foundation-first, then
per-wing) for the last visible port surface — the 9 `*_wing` interiors that today
front honest pending refusals behind a fully-ported home panel.

It is a docs-only planning artifact — no `sb/` code changes. The design doc is
grounded evidence-first in the ACTUAL surfaces read this session
(`sb/domain/ux_lab/handlers.py`, `sb/domain/ux_lab/panels.py`,
`sb/kernel/panels/{browserview,selectwindow,render}.py`,
`tests/unit/band6/test_band6_ux_lab_home.py`, and the B8 row of the completeness
snapshot), with `file:line` citations at HEAD `b39a37f`.

## Deliver

- `docs/design/B8-ux-lab-wings.md` — the fuller design doc: Problem (9 honest-refusal
  wing interiors, admin-only + zero-write ⇒ LOW priority but the last visible port
  surface; the port/render-only/leave-refused decision framed), Proposed approach
  (FOUNDATION-first Slice 0 = port the `utils/ux_patterns` registry + the
  `ExhibitWingView` browser grammar into the panel engine, which also lets the home
  `_EXHIBITS` line re-derive; THEN per-wing slices easiest→hardest — embeds proof
  first, then the mintable renders, DEFER the 3 special wings), Affected surfaces,
  Rough size (S/M/L + a recommended stopping point), Open questions for the owner.
  `> **Status:** \`plan\`` badge (a valid docs-gate token).
- `docs/design/README.md` — the B8 planning-series row Status `planned` → link
  `[B8](B8-ux-lab-wings.md)`; no other row touched.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges valid +
  the doc reachable via the series table); the only red in CI is this card's own
  designed born-red hold on the substrate-gate until the card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The load-bearing grounding finding is that the panel engine **already ships most of
what `ExhibitWingView` needs**: a `BrowserView` engine with ◀▶ prev/next paging + a
disabled page indicator over a declared List/Table block, riding the `nav:browse:`
custom-id family (`sb/kernel/panels/browserview.py`); a `SelectWindow` windowed-select
engine (`sb/kernel/panels/selectwindow.py`); session-lifecycle edit-in-place refresh
and image/attachment carriers already on the render model
(`RenderedEmbed.image_url`, `RenderedAttachment`, `sb/kernel/panels/render.py:200,210`).
So the wings port is mostly ARMING an exhibit model over grammar that exists, not
building a browser from scratch — the same "declared ahead of wired" shape the D4 doc
found. Foundation-first (the registry + the exhibit-page grammar) unlocks every wing
independently AND re-derives the pinned `_EXHIBITS` literal
(`sb/domain/ux_lab/panels.py:77-81`), so it is the correct cheapest-first slice; the
3 special wings (image bytes+timing / discord.py-version+date+live-errors / channel-side
CV2 send + external CDN URLs) are the only genuine new work, and a render-only port
with the action left declared-refused is the honest cheap stopping point for them.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (#528), the first card of
the planning-mode design-doc series, which set the format this card mirrors: read the
real surfaces in source, cite `file:line` at HEAD, verdict only on verified ground,
badge `plan`, born-red on the substrate-gate until the card flips complete. This card
carries that method forward onto the B8 lane the completeness snapshot filed as the
one remaining LOW-priority larger surface, grounding every wing characterization in
the sb-side code + the snapshot's B8 row rather than inventing oracle internals.
