# 2026-07-18 — D1 themed card-renderer design doc

> **Status:** `in-progress`

- **📊 Model:** Opus 4 family · high · kernel/architecture design

## Goal

Open the **D1 — themed card renderer** lane of the 2026-07-18 planning-mode
design series with a fuller, evidence-first design doc the owner reacts to and
prioritizes. D1 was already a `planned` row in the design index
(`docs/design/README.md`); this slice turns it into the real proposal, a sibling to
the D4 observability doc that opened the series (#528).

## Scope

Docs-only planning artifact — **no `sb/` or test code changes**. The design
proposes porting the oracle's shared, themed card engine
(`disbot/utils/card_render.py` + `rank_render.py` + `profile_render.py`, read
read-only under `/workspace/superbot`) into superbot-next as a **kernel render
band** (`sb/kernel/render/`), replacing the two deliberate solid-panel PNG
stand-ins (`sb/domain/xp/rank_card.py`, `sb/domain/utility/profile_card.py`).
Grounded evidence-first in the ACTUAL code read this session, with `file:line`
citations at HEAD `b39a37f`.

## Deliver

- `docs/design/D1-themed-card-renderer.md` — the design doc: TL;DR, Problem
  (placeholder cards today vs. the oracle's shared engine, cited `file:line`),
  Goals / non-goals, Proposed design (a kernel render band justified against the
  layer rules — a domain-shared helper would be an illegal domain→domain edge;
  determinism via bundled fonts + `None`-safe avatar; the parity finding that
  attachment bytes are unpinned so the port is zero-golden-churn), Affected
  surfaces, Rough size (**L**, sliced band-scaffold → rank card → profile card),
  Open questions for the owner (fonts, Pillow adoption, provider skins, oracle
  visual parity, prod avatars). `> **Status:** \`plan\`` badge (valid docs-gate
  token).
- `docs/design/README.md` — flips the D1 row in the planning-mode series index
  from `planned` → **this PR**, linking the new doc (the same reachability path
  the D4 doc used). `> **Status:** \`reference\`` badge unchanged.

## Trail / verification

- Reachability (docs-gate orphan check): `python3 bootstrap.py check --strict` →
  `all checks passed`; the new doc is reachable via the design-index row link.
  The only advisory warnings are pre-existing and unrelated (never
  exit-affecting).
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  the substrate-gate is the expected sole hold on this born-red card until it
  flips complete.
- `python3 tools/check_compat_frozen.py` untouched (no compat surface changed).

## 💡 Session idea

The load-bearing finding of the grounding pass: **the port is nearly free of
parity risk, and the data already reaches the placeholder.** Two facts compound.
First, the parity transport collapses any attachment-bearing panel to
`{"_files": [filename]}` (`sb/adapters/parity/transport.py:251-253`), so the PNG
body is *never* golden-pinned — the current solid-panel stand-in is treated
exactly this way (its docstring: "no pixel or embed byte is pinned"), and a real
themed renderer inherits the same treatment with zero golden churn. Second, the
rank call site already fetches the avatar and passes `stat=` + `avatar_png=` into
a renderer that `del`s them (`sb/domain/xp/panels.py:409-417`,
`sb/domain/xp/rank_card.py:42-46`) — the data plumbing for the themed card is
*already wired to the placeholder's front door*. So D1 is not "build a renderer
from scratch under a parity constraint"; it is "port a known-shipped engine into
a kernel band, adopt Pillow, and let the pixels flow through the signature that
already exists." The recurring planning-series theme holds: the wiring is richer
than the surface — arm what exists rather than invent.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (#528, the newest
prior card), which **opened** this exact planning-mode design-doc series and
created its shared home (`docs/design/README.md` + the D1–D6/B8/B10 index). This
card is the series' second entry (D1), and it deliberately mirrors D4's method
and shape: read the real surfaces in source, cite `file:line` at HEAD, verdict
only on verified ground, one design-doc PR per lane, reachable via a design-index
row. D4's own closing insight — that superbot-next "declares far ahead of where
it wires," so the planning docs are mostly about ARMING what exists — recurs here
in a different key: the themed renderer's data path and its parity treatment both
already exist around a placeholder, so D1 is an arm-what-exists port, not a
green-field build. Where D4 left the D1 row as `planned`, this card fills it.
