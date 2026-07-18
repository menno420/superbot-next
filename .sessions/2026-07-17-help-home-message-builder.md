# 2026-07-17 — Port: Help Home-message builder (Q-0059)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red HOLD so the server-side lander
> can merge on green. The born-red first commit (26eafb0, this card + claim)
> held the gate red; the impl, golden, and merge-main landed after; this flip is
> the last step.

- **📊 Model:** Opus 4 family · high · port

## Scope

Port the Q-0059 Help Home-message builder, retiring the
`help.editor_home_message_pending` stub. The Help editor's "🏠 Home
message" button currently refuses with a pending stub; this slice gives it
a real builder that customizes the Help Home frame's title / body / accent
color with a mandatory preview before save, byte-faithful to the live bot.

## Plan

- Migration 0056 — add the Help home-message columns.
- HomeMessage read model in `sb/domain/help/overlay.py`.
- `help.set_home_message` write lane in `sb/domain/help/overlay_ops.py`.
- `editor_home_message` panel + 2 modals + ENUM color selector + handlers
  in `sb/domain/help/editor.py`.
- Live-wire `help.home` to consume the saved home message.
- Mint an oracle-verified golden for the new surface.

## Deviation ledger

- **Migration 0056 — additive only.** New Help home-message columns
  (`home_title` / `home_body` / `home_color`, all nullable) added; no column
  rewrite, no backfill. Existing overlay rows read as an empty home
  (title/body/color all `None`), so the migration is pure-forward and the
  empty-overlay goldens replay unchanged.
- **D1 — two-embed preview folded to a SINGLE builder embed.** The oracle's
  `HomeMessageBuilderView` paints the mandatory preview as a *second* embed
  beside the control embed (`edit_message(embeds=[builder, preview])`); the
  port's `RenderedPanel` carries ONE embed, so the preview folds into the
  single builder control embed. The builder embed IS the live surface: body =
  the shipped `build_builder_embed` instruction block, draft state renders as
  three verbatim FIELDS via `help.home_builder_fields` ("Draft title" / "Draft
  body" / "Draft color"), the embed ACCENT re-tints to the staged color (D2),
  and the FOOTER flips byte-for-byte between the shipped `_PREVIEW_REQUIRED_NOTE`
  ("Preview the draft to enable Save.") and its unlocked twin ("Previewed — Save
  is unlocked."). 💾 Save renders `disabled` until the current draft is
  previewed and any edit re-locks it (mirrors `_rebuild_items` →
  `_SaveButton(disabled=not previewed)`); 👁 Preview flips the `previewed` flag
  rather than painting a second embed. Implemented as domain `renderer_override`
  `help.render_home_builder` (`sb/domain/help/editor.py`), justification pinned
  on the panel spec. Cost: title/body appear as draft fields rather than a
  re-composed live frame; the staged accent is shown live so "preview is exact"
  still holds for color.
- **D2 — dynamic per-guild embed color via `renderer_override` + named style
  token.** `EmbedFrameSpec.style_token` is STATIC and `RenderedEmbed` carries
  only a token NAME, so a per-guild dynamic accent can only be a named token
  resolved through the shared kernel `STYLE_TOKEN_COLORS` table. The nine
  `HOME_NAMED_COLORS` (oracle ints verbatim) each map to a token;
  `home_color_token(color)` maps a stored int → token; the override sets that
  token on the embed (fishing/ticket override precedent). Three tokens
  pre-existed (`blurple`, `yellow`, `orange`); **five were added to
  `sb/kernel/panels/render.py::STYLE_TOKEN_COLORS`** — `brand_green` 0x57F287,
  `brand_red` 0xED4245, `fuchsia` 0xEB459E, `white` 0xFFFFFE, `brand_dark_grey`
  0x2C2F33. `Default (blue)` (None) → the existing `blue` token; an unknown
  stored int degrades to `blue` (no crash). **Justified benign:** the +5 is
  pure DATA in the shared color-RESOLUTION table read by BOTH presenters
  (`sb/adapters/parity/transport.py:96`, `sb/adapters/discord/panel_view.py:63`)
  under its documented growth rule (render.py:134) — dozens of prior ports grew
  it (fishing `dark_teal`, karma `magenta`, automod `orange`). NO kernel→domain
  import edge, NO help-aware kernel branch; `check_namespace` / `check_no_skip`
  green. Kept, not reverted — no domain override can substitute for a token the
  resolution table does not contain.
- **D3 — `help.home` live-wire is a GUARDED no-op when no home row exists.**
  `help.home` gains `renderer_override` `help.render_home`
  (`sb/domain/help/service.py`): it delegates to the grammar renderer, then if
  `overlay.home is None` returns the render UNCHANGED — this is the mandatory
  no-op guard that keeps the empty-overlay `parity/goldens/help/*.json` replays
  byte-identical (the one change touching golden-pinned bytes). Only when a home
  row exists does it re-frame title/body/accent via `home_embed_frame` (the same
  composer the builder preview uses — preview-is-exact), with mention
  suppression. Smoke-verified: empty overlay → title "📚 Help Menu", body "Pick
  a category from the dropdown below.", token "blue" (identical to the bare
  grammar render); custom row → mention-suppressed title + `brand_red` accent.
- **Layer-rule fix (in-scope):** the prior worker's `home_embed_frame` imported
  `discord.utils` inside `sb/domain/help/overlay.py` (domain must not import
  discord — `check_no_skip` was RED). Replaced with a stdlib `re` replication of
  `discord.utils.escape_mentions` (`_escape_mentions` / `_ESCAPE_MENTIONS_RE`),
  verified byte-identical to discord.py across everyone/here/id/markdown cases.
- **Pending terminal retired:** `help.editor_home_message_pending` deleted; the
  🏠 Home message button routes to `help.editor_open_home_message`
  (clear-draft-then-open, mirroring the shipped `from_current` fresh view);
  `test_pending_terminal_retired_and_teardown_registered` updated.
- **Golden — `help.home_message_save` full oracle byte-match.** Minted
  `parity/goldens/help/help_home_message_save.json` and cross-read every
  captured surface against ORACLE `disbot/views/help/home_builder.py` +
  `disbot/services/help_overlay.py`: builder embed title / description / three
  draft fields / footer lock-flip / Save `disabled` flip, the color select
  placeholder + all nine label+hex options, the title-modal stage
  (`Welcome to our server!`), and the `help_overlay.added` DB write
  (`home` row, title-only draft persisted, `updated_by=<@admin>`) — every
  surface a MATCH, no port fix required.
- **Merge-main count reconcile → 526.** Origin/main advanced twice while the
  branch was open (D4 observability doc #528, the mining backlog goldens, et
  al). The golden-count pins collided; reconciled as a TRUE UNION — this
  branch's `help_home_message_save` (+1) plus main's newly-landed
  `mining_workshop_craft_write` (+1) over the 524 merge-base — pinning the
  corpus at **526** in `parity/parity.yml` ("imported + minted − retired = 526",
  `minted_goldens: 64`) and the two count-pin tests, not either side's lone
  number.

## Close-out

- **PR #512** on branch `claude/help-home-message-builder`.
- **Commits:** `26eafb0` born-red (card + claim) → `47fe2f8` impl (migration
  0056 + read model + write lane + builder UI + live-wire) → `0326986` mint
  oracle-verified golden + recompile manifest snapshot → `7884181` merge
  origin/main → `0bb6c34` merge LATEST origin/main (count reconcile → 526) →
  the flip commit (this card + heartbeat) as the deliberate last step.
- **CI / gates:** pushed READY (not draft); lands on green via the server-side
  lander (no agent-side merge). Named-gates green — `check_namespace` /
  `check_no_skip` clean after the domain `discord.utils`→stdlib fix; manifest
  snapshot recompiled so `manifest-validate` does not drift on the new
  `help.editor_home_message` panel; full `run_golden_parity --gate` verifies in
  CI (the session-window wall — per-case `mint_golden` ORACLE-VERIFY only
  locally).
- **Corpus movement:** 524 → **526** (+1 mine `help_home_message_save`, +1
  main's `mining_workshop_craft_write`, reconciled as a union at merge). True
  count confirmed on disk via `parity/goldens/*/*.json` = 526 (matches the
  parity.yml pin).
- **Live-verify:** not run for this slice — the oracle byte-match golden pins the exact builder surface (embed/modal/save DB write); an interactive live-drive on the test bot would add only runtime-connect confidence, not byte-truth. Decide-and-flag skip.

## 💡 Session idea

💡 Guard recipe — **a merged golden-count pin is a UNION, and disk-count it
with the RIGHT glob.** When two branches each mint a golden, the merge conflict
in the `parity/parity.yml` count pin (and the two count-pin tests) must resolve
to *both* goldens added (524 + 1 mine + 1 theirs = 526), NEVER either side's
lone number — taking one side silently drops the other branch's golden and the
gate goes red in CI, not locally. Verify the reconciled number by counting
files on disk, but with the SUBSYSTEM glob `ls parity/goldens/*/*.json | wc -l`
(= 526), **not** `find parity/goldens -name '*.json' | wc -l` (= 527): the
`find` form overcounts by one because it catches the top-level
`parity/goldens/_sweep_skips.json` metadata file, which is not a subsystem
golden and is excluded from the corpus pin. Code anchors: the count pin +
"imported + minted − retired = 526" comment in `parity/parity.yml`, the two
count-pin tests in the `parity_adapter` / `parity_gate` suites, and the
`*/*.json` disk-count as the reconciliation oracle. Symptom-only tell to catch
it: a green local suite but a CI count-pin failure off by exactly the other
branch's mint delta.

## ⟲ Previous-session review

🔎 Prev-session review (`.sessions/2026-07-17-provisioning-unblock-record.md`,
`complete`, #511): that session corrected the HEAD record to establish that in
the project-default env DB provisioning runs autonomously —
`pg_ctlcluster 16 main start && python3 tools/setup_local_env.py` → exit 0 with
no classifier denial — and its 💡 idea named the one-line boot recovery that
makes a session port-capable (Postgres up + `parity`/`superbot` DBs
provisioned). This slice is the direct beneficiary: it is an oracle PORT whose
deliverable needed exactly one minted golden, and that mint requires a live DB.
Because the prior card had already de-risked provisioning as autonomous here (vs
the #510 "provisioning is walled" record it superseded), this session reached
straight for `python3 tools/setup_local_env.py` then `mint_golden.py
help.home_message_save --write` and got an oracle-verified byte-match without
re-litigating whether provisioning is possible — the prior close-out saved this
one the first-slice provisioning detour. The only wall left standing (the full
`run_golden_parity --gate` session-window timeout) was honored as CI-only, per
the CAPABILITIES ledger.
