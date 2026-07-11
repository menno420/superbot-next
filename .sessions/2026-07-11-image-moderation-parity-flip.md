# 2026-07-11 — image_moderation parity flip (pending→ported, the thirtieth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `image_moderation` parity row pending→ported through the A-16
door. Oracle: menno420/superbot `disbot/cogs/image_moderation_cog.py`
at the CORPUS sha 7f7628e1 (reconstructed via search_code fragments —
full-file oracle reads stay denied, playbook trap 3/15f). Golden:
`parity/goldens/image_moderation/sweep_imagemod.json` — the R2-singleton
`!imagemod` admin sweep. Pre-flip 0/1 → post 1/1 (green on the FIRST
isolation replay). Wave-8 R2-singleton 1 of 2 (image_moderation →
counters), then the server_management prefix sibling.

## What shipped

1. **The shipped `!imagemod` policy embed** replaces the generic
   operator-spine hub route: `image_moderation.status`, a
   component-less session-lifecycle result card (the
   welcome/automod/security recipe verbatim — ZERO panel_anchors rows,
   ZERO sim-gate lock rows). The renderer_override composes the
   shipped embed: the Master `_flag` line, the live
   `**Action threshold:** ≥ {percent}% confidence` line (default 80,
   `DEFAULT_THRESHOLD_PERCENT` — owner decision Q-0108), the four
   category lines (`🔞 **Sexual**`, `🔪 **Violence**`,
   `😠 **Harassment**`, `🚫 **Hate**`), the two-sentence footer literal
   ("Configure in !settings → Image moderation. When on, flagged
   images are scanned via OpenAI; actions route through moderation."),
   MOD_COLOR = the existing `orange` style token (15105570, trap 12e
   held).
2. **CAPTURE-SHA DRIFT CHECK (mandatory pre-step, trap 24)**: the
   oracle's current-head fragments match the golden's seven lines
   EXACTLY at the default state — NO post-capture drift on this row
   (unlike automod's two extra rule lines). The shipped cog's
   exempt-role/exempt-channel tail is STATE-CONDITIONAL
   (`if policy.exempt_role_ids:` / `if policy.exempt_channel_ids:`) and
   absent at the golden's default state — not ported, ledgered in the
   module docstring (the exempt keys stay declared settings; the tail
   joins the card if a future corpus re-import pins its bytes).
3. **No new domain service**: image_moderation's reads are plain
   `kernel.settings.resolve` scalars (no bindings, no guild reads) —
   the renderer reads the seam directly, matching the shipped cog's
   policy-load-then-render shape (the automod precedent verbatim).
   NEW package `sb/domain/image_moderation/` (`__init__.py` +
   `panels.py`) — the band-2 manifest existed but had no domain dir.
4. **parity.yml**: image_moderation ported (30/49); ratchet
   `image_moderation: {events: 1, tables: 2, settings: 0}` (raw
   covered-side: xp.awarded; ai_decision_audit + xp — trap 14d).
   **ZERO depth exemptions, ZERO new classes, ZERO decision records**
   (`stores=()`/`events=()` declared; the scan listener arms with the
   message band + provider keys). Compensator allowlist stays EMPTY
   (read-only slice). The invoking-message delete tail is the ruled
   invoking-message-deletion disposition (trap 15c).

## Traps confirmed / new intel

- Trap 24 (capture-sha drift) confirmed as a MANDATORY pre-step that
  can pass: this row's fragments matched the golden exactly — the
  drift class stays automod-only so far.
- The `_policy_embed` status-card recipe is now six-for-six
  (karma.card → logging → welcome → automod → security →
  image_moderation) with zero recipe deltas; flip time again dominated
  by oracle reconstruction, not port work.
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 12d (session
  panels ⇒ zero lock/compat churn), 12e (STYLE_TOKEN_COLORS check),
  16e (importlib `_replay_corpus` — NOTE it is a coroutine; wrap in
  `asyncio.run`) confirmed as written.

## Verification

- goldens/image_moderation 1/1 green (isolation replay, first try);
  full gate **172/172 across 30 ported** on real Postgres; report leg
  **209/465** green, 465/465 replayable; check_parity_depth OK — 49
  subsystems (30 ported), 465 goldens; check_sim_gate OK (1052 [A],
  367 auto-exempt); check_compat_frozen OK; check_namespace / egress /
  no_skip clean; manifest_compile green; unit suite **1356 passed, 2
  skipped** local (canonical order).

## 💡 Session idea

The wave-7 card guessed four_twenty might share this recipe — its
golden should get the same footer/title search_code sweep before the
next singleton wave; counters (2 goldens incl. a slash twin) is next
and its slash twin will need the trap-14a AUTO+EPHEMERAL defer check
that the prefix-only singletons never exercised.

## ⟲ Previous-session review

(This previous-session review covers the security flip, #174.) The
security card's "NO capture-sha drift (checked as a mandatory
pre-step)" line became playbook trap 24 at this session's boot — this
flip executed it as written and it held. The wave-7 summary's claim
that the recipe covers the remaining R2 singletons held for
image_moderation with zero deltas; the security card's
state-carrying-field-name lane (renderer_override field names) was NOT
needed here — this row is automod-shaped (description lines only).
