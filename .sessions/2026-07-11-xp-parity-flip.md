# 2026-07-11 — xp parity flip (pending→ported, the fourteenth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `xp` parity row pending→ported through the A-16 door — the
first flip whose goldens pin a CDN asset read (`get_from_cdn`) and the
first pinning the shipped bot's GLOBAL command-error fallback copy.
Oracle: menno420/superbot `disbot/cogs/xp_cog.py` (`!rank` / `!xpmenu`)
+ `disbot/views/xp/main_panel.py` (`_XpHubView`, the visual card-engine
H3 hub) + `disbot/services/xp_helpers.py` (`RANK_CARD_FILENAME`,
`fetch_avatar_png`, `build_rank_response`); goldens: `parity/goldens/xp/`
— xp_chat_award (message-pipeline award + `!rank` card), sweep_rank
(`!rank test` — the generic-error path) and sweep_xpmenu (the hub send).
The band-4 manifest already carried the full command set, the audited
K7 award/reset seam, the chat hot path (already wired into the harness's
message feed — every prior flip's `xp.awarded` rows rode it) and a
text-rendered rank placeholder; this PR replaces the text placeholder
with the REAL shipped card-send surfaces.

## What shipped

1. **`!rank` sends the shipped rank image card** — the visual
   card-engine H3 surface (oracle PRs #1401/#1413): a new zero-action
   session panel `xp.rank_card` (sb/domain/xp/panels.py) whose renderer
   fetches the invoker's avatar through a NEW domain read port
   (`sb/domain/xp/service.py install_avatar_fetcher`/`fetch_avatar_png`
   — the shipped xp_helpers seam, ANY failure → None → initials
   fallback, never a refusal) and attaches `rank.png`
   (sb/domain/xp/rank_card.py — placeholder PNG bytes, the
   utility profile_card precedent; the goldens pin the multipart
   collapse `{"_files": ["rank.png"]}` + the preceding `get_from_cdn`,
   no pixel or embed byte). The parity capture twin
   (`ParityAvatarFetcher`, transport.py) records fake_http's ALIAS
   literal `{"url": "<cdn>"}` verbatim and answers its deterministic
   1×1 PNG; armed in boot's `_arm_capture_ports`, reset in close().
   The PR-G arg walk stays verbatim (stat/provider/mention-id).
2. **`!rank test` pins the oracle-in-harness error** — the shipped walk
   escalated non-mention tokens to `commands.MemberConverter`, whose
   name-lookup leg is a GATEWAY member query; the capture world has
   none, so the shipped command RAISED and bot1.py's global
   `on_command_error` sent "⚠️ An unexpected error occurred. Please try
   again." (sweep_rank pins the byte). The handler returns that copy
   with the in-code note; the live member-name search port is the
   follow-up slice (on live Discord the shipped walk swallowed
   BadArgument — the golden pins the HARNESS posture, the cleanup
   `_word_cache` precedent for capture-environment pins).
3. **`!xpmenu` opens the shipped hub WITH the card** — `xp.hub` becomes
   what the shipped `_XpHubView` was: a session-lifecycle view
   (ephemeral, timeout-based — views/xp/__init__.py; run-minted ids,
   NEVER in panel_anchors — the golden pins the no-anchor-row delta)
   whose renderer_override delegates to the grammar renderer and adds
   ONLY the rank-card attachment (avatar fetch + `rank.png` — H3 PR
   #1413's build_response). Declared embed/fields/actions stay — the
   multipart collapse leaves only the filename on the wire.
4. **Sim gate/compat** — manifest gains the `xp.rank_card` panel;
   snapshot recompiled (`manifest_compile.py --write`); zero new lock
   or compat rows needed (zero-action panel, no custom_id_overrides,
   no new commands — check_sim_gate + check_compat_frozen green
   untouched).
5. **The flip**: `parity.yml` `xp: ported` + the A-16 ratchet row
   `xp: {events: 1, tables: 2, settings: 0}` (xp + ai_decision_audit).
   R2 is NOT vacuous: xp declares three events its goldens only
   one-third exercise — two depth-exemption rows land under the
   EXISTING `covered-elsewhere` class: `event:xp.reset` (the sibling
   oracle goldens/_unmapped/sweep_resetxp.json carries the event
   itself) and `event:xp.level_up` (fires only from the audited
   xp.award op — pinned by xp_chat_award + sweep_givexp — but every
   capture awarded <100 XP at level 0, so no imported golden can carry
   it; the settings.changed wording precedent). No new classes.

Gate leg: 39/39 goldens across 14 ported subsystems GREEN against real
Postgres. Dashboard moves 13 → 14 ported (of 49). Full suite 1282
passed + the affected subsets re-run post-flip (204 passed).

## Notes

- **Deliberate under-ports (in-code notes):** the rank/hub card is a
  placeholder PNG — the themed renderer (avatar disc, progress bar,
  provider skins — utils/rank_render.py over card_render) is the visual
  card-engine slice's parked follow-up; nothing pins pixels. The
  provider-category ranks (`!rank mining` …) stay text (their thinner
  provider card is unpinned). The generic-error path is the
  capture-environment pin described above.
- The reasonless invoking-message deletes in all three goldens ride the
  ruled `invoking-message-deletion` disposition; the goldens' xp-row
  `coins` column rides the ruled `xp-coins-alias` disposition (both
  ORDER 009) — no new classes, and notably the flip needed ZERO new
  disposition work: both classes were already encoded symmetrically.
- New trap learned (playbook appended): a golden that pins a WIRE-VERB
  the new bot never performs (`get_from_cdn`) needs its capture twin to
  record the fake_http ALIAS LITERAL (`{"url": "<cdn>"}`), not the real
  URL — fake_http hardcoded the alias at record time, so a twin that
  records the concrete URL diffs forever.

## 💡 Session idea

The corpus's `_unmapped/` sweeps are load-bearing for R2
(`covered-elsewhere` citations now point at sweep_word_add,
sweep_setlogchannel, sweep_resetxp, sweep_givexp) but they replay in NO
gate — a regression in a cited sibling golden's lane stays invisible
until its own directory flips. A tiny "citation replay" leg (replay
exactly the goldens named in depth.exemptions reasons) would make every
exemption row self-verifying at ~4 goldens of cost.

## ⟲ Previous-session review

The cleanup card's Discord-READ port recipe (domain port + capture twin
+ arm/reset in boot) converted directly to the avatar fetch — zero
re-cycles on the port mechanics, and the R2 corpus-scan lesson found
both event citations in one grep. What it under-delivered: it framed
read-port posture as "uninstalled ⇒ raise ⇒ honest refusal"
(moderation-actions), but the avatar seam's SHIPPED posture is
any-failure→None (cosmetic fallback) — the honest port copies the
oracle's own degradation, not the strictest posture; the posture choice
belongs to the shipped semantics, not the recipe.
