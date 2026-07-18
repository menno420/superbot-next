# 2026-07-18 — D1 Slice 1: the sb/kernel/render card-engine scaffold

> **Status:** `in-progress`
>
> Born-red first commit — this card + the claim-before-build convention hold
> the `substrate-gate` red so the server-side lander can't merge a half-done
> slice. The render-band code + dep/lock + tests land in the following commits;
> the `in-progress` → `complete` flip is the deliberate LAST step.

## Goal

Land **Slice 1** of the D1 themed card renderer
(`docs/design/D1-themed-card-renderer.md` § Rough size, slice 1): a shared
kernel render band that the two placeholder card surfaces (and future cards)
will later compose. Pure foundation — **no card surface changes, zero golden
risk**. Authorized ahead of time by the render-band decision (bundle the
permissive DejaVu TTFs + adopt `Pillow>=11,<12` as a hard runtime dep, both
landing in this scaffold slice alongside their first import site, not ahead of
it).

## Scope

New kernel-band leaf `sb/kernel/render/` — the ported oracle card engine,
re-homed into superbot-next's layering (kernel imports stdlib + optional Pillow
only; no kernel→domain edge; **no consumer yet**):

- `fonts.py` — bundled-DejaVu resolution (`load_font`, `dejavu_fonts`,
  candidate tuples); lazy PIL, host-independent.
- `themes.py` — `RGB` + frozen `Theme` + the `THEMES` registry (the single
  default `midnight` skin; more skins are later config drops per the D1
  non-goal) + `get_theme` with its silent default fallback.
- `engine.py` — `CardCanvas` primitives (themed text with width-fit, rounded
  panel, header band, clamped progress bar, initials disc, real-avatar disc,
  PNG/JPEG export), `new_canvas` (returns `None` without Pillow), and the pure
  helpers (`initials`, `image_safe`, `mix`).
- `__init__.py` — the public re-export surface.
- `fonts/` — the bundled `DejaVuSans-Bold.ttf` + `DejaVuSans.ttf` (redistributable
  Bitstream-Vera license, carried as `fonts/LICENSE`).

Plus the dependency adoption in the SAME PR as its first import site (the
adopt-freely rule): `Pillow>=11,<12` in `requirements.txt` + a freshly
regenerated `requirements.lock`. And the engine's own unit tests under
`tests/unit/render_band/` — primitives, the None/text-embed degradation path,
and the skin-typo guard. Bytes are never asserted (attachment bodies are
unpinned by construction — structural/behavioural assertions only).

## Plan

1. This born-red card (first commit) — holds the gate red.
2. The render band + bundled fonts + `Pillow` dep + regenerated lock + tests.
3. Flip to `complete` (last commit) once verification is captured.
