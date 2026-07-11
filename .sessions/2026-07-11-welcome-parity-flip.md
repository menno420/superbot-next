# 2026-07-11 — welcome parity flip (pending→ported, the twenty-seventh row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `welcome` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/welcome_cog.py` (`_policy_embed`
+ `welcome_status`) + `disbot/services/welcome_config.py`
(`split_message_variants` / `render_template`) @227c220 (reconstructed
via search_code fragments — full-file oracle reads stay denied, playbook
trap 3/15f). Golden: `parity/goldens/welcome/sweep_welcome.json` — the
R2-singleton `!welcome` admin sweep. Pre-flip 0/1 → post 1/1 (green on
the FIRST isolation replay).

## What shipped

1. **The shipped `!welcome` policy embed** replaces the generic
   operator-spine hub route: `welcome.status`, a component-less
   session-lifecycle result card (the karma.card / #167 status-card
   precedent — the shipped send was a plain `ctx.send(embed=...)`, so
   ZERO `panel_anchors` rows and ZERO sim-gate lock rows, run-minted
   session panels are auto-exempt below-floor). The renderer_override
   composes `_policy_embed` verbatim: the `_flag` lines (Master /
   Greet-on-join / Farewell-on-leave / DM-on-join, `🟢 on`/`⚫ off`),
   the binding mentions (`📢 Channel` `<#id>` or `*(unset)*`,
   `🎟️ Entry role` `<@&id>` or `*(none)*`), the toggle-gated
   `🧹 Auto-delete` line, the ALWAYS-on "Join message preview" field
   (sample `@NewMember`) plus the toggle-gated Leave (sample
   `NewMember` — no `@`, shipped asymmetry) and DM preview fields, the
   ` (1 of N random variants)` suffix when the template splits on the
   shipped `---` separator, the "Configure in !settings → Welcome."
   footer, GENERAL_COLOR = the existing `green` style token (3066993).
2. **`sb/domain/welcome/service.py`** (new): `load_policy` through THE
   kernel settings seam (the declared defaults are the shipped
   welcome_config values verbatim — enabled False, join True, leave/DM
   False), `bound_channel`/`bound_entry_role` over the
   `subsystem_bindings` route-truth (`sb.kernel.db.settings.get_binding`
   — the server_logging posture, headless reads as unbound), and the
   shipped `split_message_variants` regex verbatim
   (`^\s*-{3,}\s*$` MULTILINE).
3. **Guild name + member count** ride the utility guild-directory read
   port (`guild_info` — "Parity Test Guild", member_count 4 = personas
   + bot in the capture world; the karma `_member_display` degradation
   posture: headless ⇒ empty name + count floor 1, never invented
   data). The preview renders the shipped
   `max(guild.member_count or 1, 1)` floor.
4. **parity.yml**: welcome ported (27/49); ratchet
   `welcome: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp — trap 14d). **ZERO depth
   exemptions, ZERO new classes, ZERO decision records**: the manifest
   declares `stores=() events=()` (the join/leave feeds arm with the
   member band) and the settings dimension is structurally empty (trap
   10c), so R2 has nothing to exempt. Compensator allowlist stays
   EMPTY (read-only slice, no ops). The invoking-message delete tail is
   the ruled invoking-message-deletion disposition (trap 15c) — no port
   needed, confirmed green.

## Traps confirmed / new intel

- **An R2 "settings-heavy" singleton can flip with ZERO exemptions**:
  trap 7 warns about depth.exemptions on settings-heavy rows, but
  welcome's heaviness is all SettingSpecs (dead dimension, trap 10c)
  and BindingSpecs (not a depth dimension) — with `stores=()`/
  `events=()` declared, the ratchet's raw covered-side counts are the
  whole story. Check the declaration shape BEFORE hunting exemption
  vocabulary.
- **The status-card recipe is now three-for-three** (karma.card → #167
  logging status → welcome.status): component-less
  `session_lifecycle=True` + renderer_override + `style_token` from
  STYLE_TOKEN_COLORS covers every shipped plain `ctx.send(embed=...)`
  policy/status surface; welcome needed zero kernel or transport work.
- **Route changes don't touch the compat pin** — compat pins
  `{name, group, aliases}` per command, so re-pointing `!welcome` from
  the hub to the status card is pin-invisible (check_compat_frozen OK
  with zero regen); the lock file's KEY set is likewise untouched
  (settings/binding rows only).
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 3/15f
  (search_code phrase reconstruction), 12d (session panels ⇒ zero
  lock/compat churn), 16e (importlib `_replay_corpus`) confirmed as
  written.

## Verification

- goldens/welcome 1/1 green (isolation replay, first try); full gate
  **169/169 across 27 ported** on real Postgres; report leg **206/465**
  green, 465/465 replayable; check_parity_depth OK — 49 subsystems (27
  ported), 465 goldens; check_sim_gate OK (1043 [A], 358 auto-exempt);
  check_compat_frozen OK; check_namespace / egress / no_skip clean;
  manifest_compile green; unit suite **1356 passed, 2 skipped** local
  (canonical order).

## 💡 Session idea

automod and security are the SAME shipped shape (`_policy_embed` +
status command, `_flag` lines, `Configure in !settings → …` footer —
the search_code sweep for the footer literal surfaced all three cogs at
once) and each has exactly one golden; the welcome recipe (service
load_policy + component-less status card) should port both with only
their line vocabularies and colors changing (automod/security use
MOD_COLOR — check STYLE_TOKEN_COLORS for the pinned int before assuming
a new token).

## ⟲ Previous-session review

(This previous-session review covers the chain flip, #170.) The chain
card's central lesson — guard bytes belong in the HANDLER, shipped-cog
style, never "let the K7 op raise" (4 of its 6 reds) — did not bind
here because the welcome slice is read-only with no ops at all; the
useful carry-over was procedural: pin the oracle embed builder
fragment-by-fragment FIRST, then write the renderer once against the
complete byte inventory. The trap-22/23 wording appended to the
playbook matched what the chain PR actually shipped.
