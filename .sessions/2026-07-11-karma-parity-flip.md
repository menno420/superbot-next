# 2026-07-11 — karma parity flip (pending→ported, the twenty-second row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `karma` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/karma_cog.py` +
`disbot/services/karma_service.py` + `disbot/utils/embeds.py` @7f7628e1.
Goldens: `parity/goldens/karma/` — karma_thanks_grant,
karma_repeat_cooldown, karma_self_grant_rejected, karma_slash_card,
sweep_karma, sweep_karma_add, sweep_slash_karma, sweep_thanks.
Pre-flip state: 0/8 green (band-4 domain existed; every reply was
text-rendered). Post: 8/8 on the third local replay.

## What shipped

1. **The shipped `_karma_card` standing embed** — `!karma [@user]` and
   the ephemeral `/karma` both send it: magenta accent
   (`STYLE_TOKEN_COLORS` gains `"magenta": 15277667` =
   `discord.Color.magenta()`, golden-cited), title
   `✨ Karma — {member.display_name}`, avatar thumbnail via the
   guild-directory port (`member_info` → economy wallet-card
   precedent), the INLINE Karma/Rank field pair (`**{n}** ✨`,
   `#{rank}`/`unranked`) + the non-inline Activity field
   (`received **N** · given **N**`), footer literal `Thank helpful
   members with !thanks @user`. Ported as `karma.card`: a
   component-less `session_lifecycle=True` result card with
   renderer_override (`sb/domain/karma/panels.py`), opened by the
   `karma.card_view` handler.
2. **`/karma` slash split** — the shipped
   `safe_defer(ephemeral=True)` + `safe_followup` pair (type-5
   `{"flags": 64}` then the flags-64 embed followup): the declared
   `ReplyVisibility.EPHEMERAL` already drove the type-5 defer
   pre-flip; only the followup body moved from text to the embed.
   No manifest defer change needed.
3. **The `utils/embeds.error` red refusal envelope** as
   `karma.error_card` (`❌ {message}`, ERROR_COLOR red, bare
   description embed — the corpus's FIRST ported red-error-envelope
   surface): the four typed grant refusals (self / disabled /
   cooldown / daily cap) render through it. Copy composition stays
   COG-side exactly like the shipped `karma_cog.py` except-arms —
   the cooldown copy interpolates `recipient.display_name` (directory
   port; the golden pins "OtherActor", never the mention) and
   `format_remaining(exc.retry_after)` where the shipped raise site
   passes the WHOLE window (`raise KarmaCooldownError(cooldown)` —
   karma_service.py verbatim; NEVER a computed remainder).
4. **Refusals cross the engine as DATA, not exceptions** — the K7
   engine classifies leg exceptions into frozen-five results
   (never re-raised), so typed class identity dies at `engine.run`.
   The leg marks the refusal structurally
   (`ctx.params["_karma_refusal"] = {kind, retry_after, target_id,
   cap}` — ctx.params is the SAME dict the handler passed) and the
   handler routes marked non-SUCCESS results to the error card,
   returning `Reply(BLOCKED, None)` (honest outcome, no extra text).
   `KarmaCooldownError`/`KarmaDailyCapError` also grow the shipped
   `retry_after`/`cap` attributes for headless catchers.
5. **`karma_audit_log.mutation_id`** joined the kernel-surface-drift
   `columns:` disposition encoding (the economy_audit_log twin — the
   SAME S14 ledger-reinsert idempotency column, blackjack-flip
   encoding-completion precedent, Q-0262.3); the disposition-loader
   test's pinned list grew in step. Every domain byte of the ledger
   row still diffs.
6. **Zero sim-gate / compat rows**: both cards are component-less
   run-minted session panels (auto-exempt below the floor); commands
   were already compat-pinned at band 4. `manifest.snapshot.json`
   recompiled (panels tuple).
7. **parity.yml**: karma ported; ratchet
   `{events: 2, tables: 4, settings: 0}` (raw covered-side counts —
   karma.granted + xp.awarded; ai_decision_audit + karma +
   karma_audit_log + xp). **ZERO depth.exemptions rows** — the
   manifest's two stores and one event are all golden-covered.

## Traps confirmed / new intel

- **Engine-swallows-typed-errors** (NEW, generalizes): a domain
  handler can NEVER `except TypedRefusal` around `engine.run` — legs
  must side-channel structured refusal data through `ctx.params`
  (the leg already mutates the shared params dict for `_from_user`
  etc.). First subsystem to need cog-side refusal copy composition.
- **Red error envelope** (NEW surface class): `em.error` bytes =
  bare description embed, `❌ ` prefix envelope-owned, color 15158332,
  content:null + components:[] + tts:false wire shape — satisfiable
  by a zero-component session panel; no kernel deny-path change
  needed (deny/plain-text path untouched for every other subsystem).
- **Cooldown copy pins the FULL window**: the oracle raise site
  passes `cooldown`, not remaining time — don't "improve" it to a
  remainder computation (parity would still pass under the frozen
  clock but semantics would drift).
- Trap 1 (ratchet scratch-learn/restore/hand-apply), trap 14a
  (slash defer), 14b/14h (thumbnail + directory display names),
  15c (invoking-message-deletion absorbs the delete tails) all
  confirmed exactly as written.

## Verification

- goldens/karma 8/8 green locally; full gate **132/132 across 22
  ported** on real Postgres; check_parity_depth OK; check_sim_gate
  OK (zero new rows); check_compat_frozen OK; check_namespace clean;
  **1302 passed, 5 skipped**.

## 💡 Session idea

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no idea. Backfill exists so the strict session-gate's
newest-card-by-mtime pick cannot red CI on this card — see PR #159's card.)

## ⟲ Previous-session review

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no previous-session review.)
