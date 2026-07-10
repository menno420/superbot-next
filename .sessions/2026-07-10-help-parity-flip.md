# 2026-07-10 — help parity flip (ORDER-004 item 2: the first pending→ported row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build

## Scope

Drive `help` (post-#70 shape) to byte-parity against
`parity/goldens/help/*` and flip its `parity.yml` row pending→ported
through the A-16 door — the first green golden row, the byte-parity trust
anchor for every later flip. Process per the corpus contract: replay the
goldens locally against real Postgres (mirroring
`.github/workflows/golden-parity.yml`), fix the NEW code (the golden IS the
oracle), apply the ruled flag-13 dispositions where they bite, flip as the
deliberate LAST commit.

## What shipped

1. **Wire-shape parity in the present path** — embeds carry `"flags": 0` +
   the style-token color (`STYLE_TOKEN_COLORS`, one kernel map read by BOTH
   presenters); selects carry `"required"` + rich options
   (label/value/description/emoji, provider-fed through the render model);
   invoker-audience panels present ephemeral (`flags: 64`) on interaction
   surfaces in the parity transport exactly like the live presenter.
2. **`panel_anchors` persistence** (migration `0025`) — the shipped
   panel-message registry: the engine's new anchor-store port records every
   CHANNEL-sent panel (never ephemeral interaction responses); wired in
   both composition roots.
3. **Help home to the shipped shape** (oracle-pinned): title `📚 Help Menu`,
   the shipped copy/color, the verbatim legacy `help_categories:select` id
   (compat pin regenerated — one added legacy id), the 8 registry hubs with
   the staff gate (members see 6), field values `purpose + → \`!<hub>\``,
   select values = category keys.
4. **Disposition ref-renumbering** — the ruled drops consumed `<msg:N>`
   refs (the invoking delete minted `<msg:1>` on every command golden);
   `apply_dispositions` now finishes with a symmetric first-appearance
   renumbering so the accepted classes cannot leak id-noise
   (docs/parity/flag-13-disposition-2026-07-10.md § Ref renumbering).
5. **The flip**: `parity.yml` `help: ported` + the A-16 ratchet row
   (`help: {events: 1, tables: 3, settings: 0}`; declared surfaces are
   empty → R2 vacuously 100%, zero exemptions).

All three help goldens replay GREEN against real Postgres
(help.panel_open, sweep.help, sweep.slash_help). Parity dashboard moves
0 → 1 ported (of 49), 0 → 3 green goldens (of 465).

## 💡 Session idea

The flip exposed that `RenderedEmbed.style_token` had no consumer — every
shipped embed carries a color (262/262 goldens), so every band's flip will
need its token minted in `STYLE_TOKEN_COLORS`. A cheap pre-flip harvest:
grep the band's goldens for `"color":` values and mint the tokens + spec
`style_token`s in the SAME PR that ports the panels, before replay ever
runs — turns one whole diff class into a lookup table filled at authoring
time.

## ⟲ Previous-session review

The #105 session's disposition mechanism (symmetric drops, data in
parity.yml, mechanism in one module) held up exactly as designed — the help
flip needed zero new disposition CLASSES, and the three ruled ones applied
cleanly. What it under-delivered: the drops' interaction with the
Normalizer's first-appearance ref numbering was invisible until a real flip
tried to go green — the `<msg:N>` shift the invoking-delete drop leaves
behind would have made every panel-anchor golden permanently red. The
renumbering pass belongs to the same "id-noise must not cascade" rule the
harness already documents; it landed here as mechanism, not as a new
accepted difference.
