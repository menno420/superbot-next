# 2026-07-18 — D1 Slice 1: the sb/kernel/render card-engine scaffold

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD so the
> server-side lander can merge on green. First commit was this card alone (held
> the gate red); the render band + dep/lock + tests landed in the second
> commit; this flip is the last. The claim was landed first as its own
> control-only PR (#559, merged) before any build.

- **📊 Model:** opus-4.8 · high · kernel slice

## Goal

Land **Slice 1** of the D1 themed card renderer
(`docs/design/D1-themed-card-renderer.md` § Rough size, slice 1): a shared
kernel render band the two placeholder card surfaces (and future cards) will
later compose. Pure foundation — **no card surface changes, zero golden risk**.
Authorized ahead of time by the render-band decision (bundle the permissive
DejaVu TTFs + adopt Pillow as a hard runtime dep, both landing in this scaffold
slice alongside their first import site, not ahead of it). The `<12` bound the
decision named was forced up to `>=12.3.0,<13` by the security gate — see the
deviation ledger.

## Scope

New kernel-band leaf `sb/kernel/render/` — the ported oracle card engine,
re-homed into the project layering (kernel imports stdlib + optional Pillow
only; **no kernel→domain edge; no consumer yet**):

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
- `fonts/` — bundled `DejaVuSans-Bold.ttf` + `DejaVuSans.ttf` (redistributable
  Bitstream-Vera license, carried as `fonts/LICENSE`).

Plus the dependency adoption in the SAME PR as its first import site (the
adopt-freely rule): `Pillow>=11,<12` in `requirements.txt` + a freshly
regenerated `requirements.lock`. And the engine's own unit tests under
`tests/unit/render_band/` — primitives, the None/text-embed degradation path,
and the skin-typo guard. Bytes are never asserted (attachment bodies are
golden-unpinned by construction — structural/behavioural assertions only).

## Deliver

- `sb/kernel/render/__init__.py`, `fonts.py`, `themes.py`, `engine.py`
- `sb/kernel/render/fonts/DejaVuSans-Bold.ttf`, `DejaVuSans.ttf`, `LICENSE`
- `requirements.txt` (+ `Pillow>=12.3.0,<13`) + regenerated `requirements.lock`
  (adds `pillow==12.3.0`, hash-pinned; a leaf — no transitive additions)
- `tests/unit/render_band/test_engine.py` — 36 cases

## Verification

- `python3 -m pytest -q --ignore=examples` → **3481 passed, 29 skipped, 1
  warning in 74.41s** (the pre-existing `examples/` plugin-example collection
  gap is excluded per the standing note).
- Render-band file in isolation: **36 passed** with Pillow present; **23
  passed / 13 skipped** with Pillow *absent* — the CI `code-quality` gate
  scenario (installs no runtime deps): the band imports cleanly and the
  `importorskip("PIL")` primitive tests skip, while the pure-helper +
  degradation + skin-typo + font-presence tests still assert. The
  None/text-embed degradation is pinned deterministically by blocking the PIL
  import at runtime, so it runs and passes in *both* environments.
- `python3 tools/check_lockfile_fresh.py --regen` → `OK (34 pinned dists, 1102
  hashes, regen-verified)` — the lock is `pip-compile --generate-hashes
  --strip-extras` byte-for-byte reproducible.
- `pip-audit -r requirements.lock --require-hashes --disable-pip` → **"No known
  vulnerabilities found"** on `pillow==12.3.0` (the ci.yml security gate;
  11.x's 14 advisories are why the bound was forced up — see deviation ledger).
- Architecture + manifest gates clean: `check_symbol_shadowing`,
  `check_namespace`, `check_no_skip`, `check_config_usage`, `check_egress`,
  `check_escape_hatches`, `manifest_compile` (green, **no snapshot drift** —
  the band declares no manifest entries), `check_runtime_smoke` (boots), plus
  `check_schema_growth`, `check_amendments`, `check_metric_cardinality`,
  `check_money_race`.
- **Zero golden churn** — no card surface touched; the
  `{"_files": ["rank.png"]}` / `["profile.png"]` goldens are untouched.

## Deviation ledger

- **Themes: `midnight` only.** The oracle ships six skins; the D1 non-goal
  ("one default `midnight` skin lands first; more skins are config drops
  later") scopes Slice 1 to the single default. The registry mechanism is
  fully in place — adding a skin is a `Theme` tuple, not code. Decide-and-flag:
  ship the authorized minimum, defer the catalogue to a later slice.
- **Skin-typo guard is engine-level, not provider-level.** The oracle's
  invariant pins "every `RankProvider.card_theme` is a registered `THEMES`
  key" — but no provider→theme mapping exists in Slice 1 (no consumer). The
  guard here pins the applicable engine invariant: every registry key equals
  its `Theme.name`, `DEFAULT_THEME` is registered, and `get_theme` falls back
  silently on any unknown/typo'd key without raising. The provider-mapping
  guard belongs in Slice 2, where providers gain `card_theme` (see idea).
- **Fonts committed as real binaries** via git in the worktree (708 KB + 760
  KB TTFs) — no base64/MCP file API, per the task's binary-asset rule.
- **Pillow bound raised `<12` → `>=12.3.0,<13`** (deviation from the authorized
  render-band Pillow decision). The decision authorized `Pillow>=11,<12`, but
  every 11.x release carries 14 PYSEC advisories fixed only in `>=12.3.0`, and
  the mandatory `pip-audit -r requirements.lock --require-hashes` CI gate
  (ci.yml) hard-blocks them with no allowlist configured. `>=12.3.0` is the
  only bound that honors the decision's INTENT (adopt Pillow for the render
  band) while passing the security gate. 12 is a major bump; the engine's
  imaging surface (`Image.new/open/convert/resize`, `ImageDraw` primitives,
  `ImageFont.truetype/load_default`, `textlength`, PNG/JPEG save) re-verified
  green on 12.3.0 — no 11→12 API breakage. Fix landed as a follow-up commit
  after the flip (card stays complete; substrate-gate only holds while
  in-progress). Flag for the owner: the `<12` intent in the render-band
  decision no longer holds; `>=12.3.0` is forced by security, not preference.

## 💡 Session idea

When Slice 2 wires the rank card and providers gain a `card_theme` field,
port the oracle's stronger skin invariant as a real guard so a provider naming
an unregistered skin fails the build rather than silently rendering the default
(`get_theme`'s silent fallback is a feature for runtime resilience but a
footgun for declared config). **Guard recipe:** a test in
`tests/unit/render_band/` (or the invariants band) that iterates every
provider's declared `card_theme` and asserts membership in
`sb.kernel.render.THEMES` — anchor the provider registry the same way the
oracle's `test_provider_card_theme_registered.py` did, keyed off whatever
Slice 2 introduces as the provider→skin map.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-flip-mining-rows-route-settings.md` (the
`origin/main` HEAD at branch time, #558) — a docs-only slice that flipped two
stale B2/B3 mining rows OPEN→DONE and appended the missing per-group
edit-page owner-decision routing to `docs/question-router.md`. Same
born-red-first / flip-last discipline this card follows, and it models the
`📊 Model:` family-level line format (`opus-4.8 · medium · docs-only`) I mirror
here. Posture is the complement of this slice: #558 closed a
docs-reconciliation gap with no `sb/` code and no dep; this lands a new kernel
band + a runtime dependency. No overlap, nothing to reconcile — and its
careful "re-confirm every claim at HEAD before writing" habit is the same one
that made me re-verify no sibling render claim/branch existed before building.

## Close-out

- **PR #560** — https://github.com/menno420/superbot-next/pull/560 (branch
  `claude/d1-render-band-slice1`, base `main`).
- **Claim PR #559** — merged (control-only, `control/claims/d1-render-band-slice1.md`).
- Files: `sb/kernel/render/` (`__init__`, `fonts`, `themes`, `engine` +
  `fonts/` TTF pair + LICENSE), `tests/unit/render_band/test_engine.py`,
  `requirements.txt`, `requirements.lock`. Full `pytest --ignore=examples`
  green (3481 passed / 29 skipped); lock regen-verified; all architecture +
  manifest guards clean; zero golden touched.
- Server-side lander merges on green (the six required named gates).
