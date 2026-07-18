# D1 — Themed card renderer (rank / profile hero cards)

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the D1–D6 lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`). This is a PLAN,
> not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. `sb/` citations are `file:line` at
> HEAD `b39a37f`; oracle citations are read-only paths under `/workspace/superbot`.

## TL;DR

The `!rank` and `/myprofile` surfaces already ship the correct **send shape** —
a `discord.File` attachment (`rank.png` / `profile.png`) rides the panel, and
the parity goldens pin exactly that shape. But the pixels are a deliberate
stand-in: both renderers emit a 128×32 solid dark panel built from stdlib
`zlib`/`struct`, because the repo carries no imaging dependency yet
(`sb/domain/xp/rank_card.py:36-63`, `sb/domain/utility/profile_card.py:36-58`).
The oracle shipped a real, themed card engine — a shared `card_render` substrate
(palette + font + primitives) that `rank_render` and `profile_render` compose
into avatar-disc + stat-panel + progress-bar hero cards
(`disbot/utils/card_render.py`, `disbot/utils/rank_render.py`,
`disbot/utils/profile_render.py`). This doc proposes porting that engine as a
**kernel render band** (`sb/kernel/render/`) that the two domain card modules —
and future cards (ux_lab `pil_cards`, welcome, mining) — draw from.

The load-bearing enabler: **attachment bytes are never golden-pinned**. The
parity transport collapses any attachment-bearing panel to
`{"_files": [filename]}` (`sb/adapters/parity/transport.py:251-253`), so the PNG
body is invisible to parity. The renderer is therefore free to produce real
themed pixels with **zero golden churn** — the only pin is the filename, which
does not change. This makes D1 a low-parity-risk, additive slice, gated only on
adopting Pillow + bundling a font.

## Problem

### What ships today — honest placeholders, not themed cards

Both card modules are explicit that they are waiting surfaces:

- **Rank card.** `render_rank_card(user_id, guild_id, *, stat="both",
  avatar_png=None)` deletes all four arguments and returns a fixed 128×32 solid
  `(47, 49, 54)` panel (`sb/domain/xp/rank_card.py:42-63`). The docstring names
  the parked follow-up verbatim: *"The themed renderer (avatar disc, progress
  bar, provider skins) is the visual card-engine slice's parked follow-up"*
  (`sb/domain/xp/rank_card.py:15-20`). The caller already resolves the real data
  and even **fetches the avatar** before handing it to the placeholder that
  throws it away: `_attach_rank_card` reads `rank_target` / `rank_stat` from
  params, calls `service.fetch_avatar_png(user_id, guild_id)`, and passes
  `stat=` + `avatar_png=` into a renderer that `del`s them
  (`sb/domain/xp/panels.py:395-417`).
- **Profile card.** `render_profile_card(user_id, guild_id)` likewise `del`s its
  args and returns the same solid panel (`sb/domain/utility/profile_card.py:40-58`).
  `_render_profile_card` builds an empty-embed panel carrying only the
  attachment (`sb/domain/utility/panels.py:451-467`).

So the data plumbing (avatar bytes, stat toggle, user/guild) already reaches the
renderer through the exact signature the themed renderer wants — the pixels are
the only missing piece.

### The fidelity target — the oracle's shared card engine

The oracle solved this once, as a **single templated engine re-skinned per
theme** (its stated design goal: *"a new look is a config drop, not new code"*,
`disbot/utils/card_render.py:1-9`). The pieces:

- **`Theme`** — a frozen dataclass: palette (`bg`, `panel`, `accent`,
  `accent_alt`, `text`, `subtle`, `gold`, `outline`) + ordered font-candidate
  tuples, in a named `THEMES` registry (`midnight`, `ember`, …)
  (`disbot/utils/card_render.py:47-150`). `get_theme(name)` resolves by key with
  a **silent default fallback** on an unknown key (`:152-161`).
- **`CardCanvas`** — a themed wrapper over a Pillow `Image`+`ImageDraw` exposing
  the primitives every card needs: `text()` with width-fit truncation
  (`:305-330`), rounded `panel()` (`:332-348`), `header_band()` (`:350-355`),
  `progress_bar()` clamped to `[0,1]` (`:357-389`), `initials_disc()` — the
  no-network avatar (`:391-423`), `avatar_disc()` — a real circular-cropped
  avatar composite with an accent ring, returning `False` on decode failure so
  the card falls back to initials and never ships broken (`:425-460`), and
  `to_png()` / `to_jpeg()` export (`:462-471`).
- **Graceful degradation** — lazy PIL import; `new_canvas()` returns `None` when
  Pillow is unavailable, so a caller always keeps its text-embed fallback
  (`disbot/utils/card_render.py:19-23, 473-491`). Layout-only helpers
  (`initials()`) are pure and importable without Pillow.
- **The two feature cards compose it.** `rank_render.render_rank_card(*,
  display_name, subtitle, stats, progress, theme, footer, avatar_png)` lays a
  header + identity disc + a 3-column stat grid (up to six panels) + a level
  progress bar (`disbot/utils/rank_render.py:38-183`).
  `profile_render.render_profile_card(*, display_name, subtitle, stats,
  progress, theme, footer)` is the fixed four-panel hero-strip sibling
  (`disbot/utils/profile_render.py:29-140`). Note the **presentation-only
  contract**: pure values in, `bytes | None` out — no Discord, no DB, no network;
  the caller resolves data and (for rank) fetches the avatar bytes and passes
  them in.
- **A guard against silent skin typos.** The oracle pins that every
  `RankProvider.card_theme` is a registered `THEMES` key, because `get_theme`'s
  silent fallback would otherwise render the wrong skin without going red
  (`/workspace/superbot/tests/unit/invariants/test_provider_card_theme_registered.py`).

The gap is therefore not "invent a renderer" — it is **port a known, shipped
engine** into superbot-next's layering, adopt its one dependency, and re-wire
the two existing call sites that already hold the data.

## Goals / non-goals

**Goals**

- A single shared render band with the oracle's primitive surface (themed text,
  rounded panels, header band, progress bar, initials disc, real-avatar disc,
  PNG export) so rank + profile + future cards share one visual language.
- Real themed rank/profile cards at fidelity comparable to the oracle
  (avatar/initials disc, stat panels, progress bar, a named theme).
- **Zero golden churn** — the port must not move a single parity byte
  (attachment bodies are unpinned; see Determinism).
- Graceful degradation preserved — a Pillow-less or font-less host must still
  send a valid card (or fall back), never crash a command.
- A skin-registry + a typo guard so a provider/theme mismatch fails the build,
  matching the oracle's invariant.

**Non-goals**

- Byte-for-byte pixel parity with the oracle's PNGs. The goldens do not pin card
  pixels (`sb/adapters/parity/transport.py:251-253`), and matching Pillow output
  byte-exactly across versions is neither required nor sensible. "Themed &
  correct" is the bar — see open question Q4.
- Porting the full oracle theme catalogue (`ember`, `verdant`, provider skins)
  in slice 1. One default `midnight` skin lands first; more skins are config
  drops later.
- Wiring the ux_lab `pil_cards` gallery wing (it is a pending stub today,
  `sb/domain/ux_lab/handlers.py:56-57`). D1 gives it a foundation to build on;
  the gallery itself is a follow-up (tracked as B8, the ux_lab lane).
- Live-guild avatar-fetch hardening beyond what `service.fetch_avatar_png`
  already does (it already returns `None` on any failure,
  `sb/domain/xp/service.py:175-186`).

## Proposed design

### Module placement — a kernel render band (`sb/kernel/render/`), recommended

The engine must live somewhere both `sb/domain/xp` and `sb/domain/utility` (and
later ux_lab) can import. The layer rules (`.claude/CLAUDE.md` § Architecture)
are the deciding constraint:

> `sb/kernel` bands import spec/namespace and **never domain** — no
> kernel→domain import edge, ever; `sb/domain/<key>` subsystems import kernel +
> spec.

A shared helper cannot sit inside one domain (`sb/domain/xp/…`) and be imported
by another domain (`sb/domain/utility/…`) — that would be a domain→domain edge,
which the layering forbids as surely as kernel→domain. The two clean options:

| Option | Placement | Verdict |
|---|---|---|
| **A (recommended)** | `sb/kernel/render/` — a new kernel band: `engine.py` (Theme, CardCanvas, new_canvas, get_theme), `fonts.py` (bundled-font resolution). Domains import `from sb.kernel.render import ...`. | Matches the existing kernel-band shape (`sb/kernel/panels/` is the precedent — a kernel band the domains render through). The engine is pure presentation (no domain types, no DB, no Discord), so it imports nothing above spec — a clean kernel leaf. **Recommended.** |
| B | `sb/spec/` or `sb/namespace/` | Wrong: the engine is not a stdlib-only grammar leaf — it carries an optional Pillow import and real render logic. Rejected. |
| C | A `sb/domain/_shared/` sibling | No such band exists; inventing a cross-domain domain band muddies the "one key per subsystem behind an audited seam" rule. Rejected in favor of A. |

The **kernel render band** mirrors `sb/kernel/panels/` (the panel engine domains
already render through) and the oracle's own layering note (*"utils may import
stdlib + discord only … it is pure rendering"*,
`disbot/utils/card_render.py:25-27`) — in superbot-next that pure-rendering home
is a kernel band, not `utils`.

Proposed shape:

```
sb/kernel/render/
  __init__.py      # re-exports Theme, THEMES, get_theme, CardCanvas, new_canvas, initials
  engine.py        # the ported card_render engine (palette + primitives + export)
  fonts.py         # bundled-font path resolution (see Determinism)
  themes.py        # the named THEMES registry (midnight default; ember/… later)
```

### How a card composes it (unchanged public signatures)

The two domain card modules keep their **current public signatures** (so the
call sites in `xp/panels.py` and `utility/panels.py` need no change) and swap
their bodies from the solid-panel stand-in to an engine composition:

- `sb/domain/xp/rank_card.py` — `render_rank_card(user_id, guild_id, *,
  stat="both", avatar_png=None)` resolves the member's display name/subtitle/
  stat tuples from the data it is handed (or is extended to receive them; see
  Affected surfaces), then composes `sb.kernel.render` primitives exactly as
  `disbot/utils/rank_render.py:38-183` does — header band, `avatar_disc()` with
  `initials_disc()` fallback, a 3-column stat grid, the level progress bar — and
  returns `canvas.to_png()`, or the current solid-panel bytes when
  `new_canvas()` returns `None`.
- `sb/domain/utility/profile_card.py` — same pattern against
  `disbot/utils/profile_render.py:29-140` (fixed four-panel hero strip).

The engine stays pure: the **domain** module owns "turn user/guild/stat into
(display_name, stats, progress)" and (for rank) the avatar bytes already fetched
in `sb/domain/xp/panels.py:409-411`; the **kernel band** only turns those plain
values into pixels.

### Determinism, fonts, and parity/golden treatment

This is the crux, and it is favorable:

- **Attachment bytes are unpinned.** `rendered_panel_payload` collapses any
  attachment-bearing panel to `{"_files": [a.filename for a in attachments]}`
  (`sb/adapters/parity/transport.py:251-253`) — the PNG body never reaches a
  golden. The current placeholder is treated exactly this way (its docstrings:
  *"no pixel or embed byte is pinned"*, `sb/domain/xp/rank_card.py:9-13`). So the
  themed renderer inherits the same treatment: **it changes zero golden bytes**,
  because the only pinned thing (`rank.png` / `profile.png`) is unchanged. The
  renderer is *excluded from byte-parity by construction*, not by a new
  exclusion rule.
- **Fonts in CI.** DejaVu is present in this environment
  (`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` and `-Sans.ttf` both
  exist), which is exactly what the oracle's default theme points at
  (`disbot/utils/card_render.py:41-43`). But relying on a system font path is
  fragile across CI images. **Recommendation:** bundle the two DejaVu TTFs (or a
  chosen brand pair) under `sb/kernel/render/fonts/` and resolve them by package
  path, with the system path + Pillow's bitmap default as ordered fallbacks
  (the oracle's `load_font` already tries candidates in order,
  `disbot/utils/card_render.py:171-185`). Bundling makes the render
  host-independent. (Font licensing → open question Q1.)
- **Avatar in tests.** The renderer takes `avatar_png: bytes | None` and, on any
  decode failure or `None`, falls back to the network-free `initials_disc`
  (`avatar_disc` returns `False` → fallback, `disbot/utils/card_render.py:425-460`).
  Unit tests pass a tiny fixed PNG (or `None`) — **no network in tests**. The
  live avatar fetch is already isolated behind `service.fetch_avatar_png`, which
  returns `None` when no fetcher is installed (`sb/domain/xp/service.py:175-186`),
  so CI/parity runs render the initials path deterministically.
- **What tests DO assert.** Not bytes — structural properties, mirroring the
  oracle's `test_*_render.py` suite: `new_canvas` returns `None` without Pillow;
  a valid PNG signature/header when present; `progress_bar` fraction clamped;
  `initials()` purity; and the **skin-typo guard** (every declared card theme is
  a registered `THEMES` key), ported from
  `/workspace/superbot/tests/unit/invariants/test_provider_card_theme_registered.py`.

### Dependency

superbot-next carries **no imaging dependency today** (grep for `Pillow`/`PIL`
across the tree is empty; the placeholder docstrings say so explicitly). Adopting
the engine means adding `Pillow` to `requirements.txt` **and** regenerating
`requirements.lock` in the same PR (the repo's adopt-a-dep rule,
`requirements.txt:1-13`). The engine's lazy-import + `None` degradation means a
host that somehow lacks Pillow still runs — but the intent is to ship it as a
real runtime dep. (Adopt vs. keep-optional → open question Q2.)

## Affected surfaces

| Surface | Change |
|---|---|
| `sb/kernel/render/` (NEW band) | `engine.py` + `themes.py` + `fonts.py` + `__init__.py` — the ported card engine. New kernel leaf; imports stdlib + optional Pillow only. |
| `sb/kernel/render/fonts/` (NEW) | Bundled TTF font pair (determinism). |
| `sb/domain/xp/rank_card.py` | Body swapped placeholder→engine composition; **signature unchanged** (`render_rank_card(user_id, guild_id, *, stat, avatar_png)`), so `sb/domain/xp/panels.py:395-417` needs no edit. May need a small data-resolution helper to build `(display_name, subtitle, stats, progress)` from xp service reads. |
| `sb/domain/utility/profile_card.py` | Same body swap; signature `render_profile_card(user_id, guild_id)` unchanged, so `sb/domain/utility/panels.py:451-467` is untouched (or gains a stats-resolution read). |
| `requirements.txt` + `requirements.lock` | Add `Pillow` (+ regen lock, same PR). |
| Tests (NEW) | `tests/unit/render_band/` — engine primitive tests + degradation + the skin-typo guard; `tests/unit/xp/…` + `tests/unit/utility/…` extended for the composed cards (structural, not byte). |
| Parity goldens | **No change** — attachment bytes unpinned (`sb/adapters/parity/transport.py:251-253`). Confirm the existing `{"_files": ["rank.png"]}` / `{"_files": ["profile.png"]}` goldens stay green (they must, filenames unchanged). |
| `sb/domain/ux_lab/` (`pil_cards` wing) | Not wired here; the new band is the foundation the pending `pil_cards` gallery (`handlers.py:56-57`, B8 lane) later composes. Noted so the two efforts don't collide. |
| Provider skins (`stat`/theme) | Optional: a `RankProvider`-style theme-per-provider mapping + its registration guard, if provider skins are in scope (open question Q3). |

## Rough size — **L** (port a subsystem + adopt a dep), sliced into three PRs

L, because it introduces a new kernel band, adopts a runtime dependency (with a
lockfile regen), rewires two live card surfaces, and needs a font-bundling
decision — but each piece is independently landable:

1. **Slice 1 — render-band scaffold + dep (S–M).** `sb/kernel/render/` with the
   engine (Theme/THEMES/get_theme/CardCanvas/new_canvas/initials), bundled fonts,
   the `Pillow` dep + lock regen, and the engine's own unit tests (primitives,
   degradation, skin-typo guard). No card surface changes yet — pure foundation,
   zero golden risk.
2. **Slice 2 — rank card (M).** Swap `rank_card.py` to compose the engine
   (avatar disc + stat grid + progress bar), extend xp data resolution as needed,
   tests. Goldens confirmed unchanged.
3. **Slice 3 — profile card (S–M).** Swap `profile_card.py` (four-panel hero
   strip), tests. Goldens confirmed unchanged. Optionally fold in provider skins
   / the theme catalogue if Q3/Q4 land "yes".

## Open questions for the owner

1. **Which fonts do we bundle?** DejaVu (matches the oracle default, present in
   this env, permissive license) — or a **brand** font pair (a distinct
   SuperBot look)? Bundling is recommended either way for host-independence;
   the choice is DejaVu-for-fidelity vs. a brand identity. *(Licensing must
   allow redistribution in-repo.)*
2. **Adopt Pillow as a hard runtime dep, or keep it optional?** The engine
   degrades to `None`/text-embed without it, but shipping real cards means it is
   effectively required. Recommend adopting it (add to `requirements.txt` +
   regen lock); confirm that's acceptable given the pip-audit/lockfile hygiene
   rules.
3. **Provider skins / per-stat theming in scope?** The oracle themes rank cards
   per `RankProvider.card_theme` (with a registration guard). Do we port that
   provider-skin machinery in D1, or ship one default `midnight` skin now and
   defer provider skins?
4. **Is "themed & correct" enough, or is oracle visual parity required?** The
   goldens do NOT pin card pixels, so nothing forces byte-parity — but the owner
   may want the ported cards to *look like* the oracle's (same layout/palette)
   vs. a fresh SuperBot visual identity. This decides how faithfully slices 2–3
   copy the oracle geometry vs. redesign.
5. **Real avatars in production?** Rank already fetches avatar bytes
   (`sb/domain/xp/panels.py:409-411`) via a pluggable `fetch_avatar_png` that is
   `None`-safe. Confirm we want the live-avatar composite in prod (a CDN fetch
   per render) vs. always the network-free initials disc. Tests stay on the
   initials/fixed-PNG path regardless.
