# 2026-07-11 — security parity flip (pending→ported, the twenty-ninth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `security` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/security_cog.py`
(`_policy_embed`) + `disbot/services/security_config.py`
(`applies_raid_slowmode`) — reconstructed via search_code fragments
(full-file oracle reads stay denied, playbook trap 3/15f); every
fragment matches the imported golden byte-for-byte (NO capture-sha
drift on this row, unlike automod #173). Golden:
`parity/goldens/security/sweep_security.json` — the R2-singleton
`!security` admin sweep. Pre-flip 0/1 → post 1/1 (green on the FIRST
isolation replay). Wave-7 R2-singleton 3 of 3 (welcome #172 ✅ →
automod #173 ✅ → security).

## What shipped

1. **The shipped `!security` policy embed** replaces the generic
   operator-spine hub route: `security.status`, a component-less
   session-lifecycle result card (the welcome/automod recipe — ZERO
   panel_anchors rows, ZERO sim-gate lock rows). The renderer_override
   composes `_policy_embed` verbatim: the Master `_flag` line + the
   `📢 **Alert channel:**` binding mention (`*(unset)*` when unbound),
   the `🚨 Raid detection — {flag}` field ("Trigger: **{count}** joins /
   **{window}s**" + the shipped `applies_raid_slowmode` branch —
   slowmode channel bound AND slowmode seconds > 0 ⇒ "Lockdown:
   slowmode **{n}s** for **{m}s**", else the golden-pinned "Lockdown:
   alert-only (no slowmode channel set)" literal), the `⚠️ Account-age
   filter — {flag}` field ("Threshold: **{days}** days\nAction:
   **{action}**"), the "Configure in !settings → Security." footer,
   GENERAL_COLOR = the existing `green` style token. This card is the
   corpus's first STATE-CARRYING FIELD NAMES surface (the per-tier
   flags live in the field names, not values — named in the
   justification).
2. **Two binding reads** (`alert_channel`, `raid_slowmode_channel`)
   over the `subsystem_bindings` route-truth (`get_binding`, headless
   reads as unbound); the shipped `applies_raid_slowmode` property
   ported as its exact two-clause conjunction (security_config.py
   verbatim — channel bound AND seconds > 0).
3. **parity.yml**: security ported (29/49); ratchet
   `security: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp — trap 14d). **ZERO depth
   exemptions, ZERO new classes, ZERO decision records** (`stores=()`/
   `events=()`; the on_member_join screening feed arms with the member
   band). Compensator allowlist stays EMPTY (read-only slice). The
   invoking-message delete tail is the ruled invoking-message-deletion
   disposition (trap 15c).

## Traps confirmed / new intel

- **The three-flip R2-singleton wave confirms a recipe class**: the
  shipped `_policy_embed`-family status commands (welcome / automod /
  security — all `Configure in !settings → …` footers) port as
  component-less session-lifecycle cards with settings/binding-seam
  renderers, each with ZERO exemptions, ZERO lock/compat churn, and
  first-replay green. The variance across the three was exactly: line
  vocabulary, style token, binding count, and one capture-sha drift
  bite (automod).
- **State-carrying FIELD NAMES are renderer_override territory** like
  state-carrying descriptions/footers (#145 12c) — grammar field names
  are static; no schema growth, just name the surface in the
  justification.
- Traps 1, 12d, 15f, 16e confirmed as written; the automod drift class
  (new intel in the #173 card) did NOT bite here — fragments matched
  the golden exactly.

## Verification

- goldens/security 1/1 green (isolation replay, first try); full gate
  **171/171 across 29 ported** on real Postgres; report leg **208/465**
  green, 465/465 replayable; check_parity_depth OK — 49 subsystems (29
  ported), 465 goldens; check_sim_gate OK (1049 [A], 364 auto-exempt);
  check_compat_frozen OK; check_namespace / egress / no_skip clean;
  manifest_compile green; unit suite **1356 passed, 2 skipped** local
  (canonical order).

## 💡 Session idea

The remaining R2 singletons image_moderation (1 golden) and counters
(2 goldens incl. a slash twin) pin the same footer family ("Configure
in !settings → Image moderation." / "… → Counters.") — the recipe
should take both next wave; counters adds one new ingredient (the
live member/human/bot counts through the guild-directory port and a
`blurple` accent already in STYLE_TOKEN_COLORS) and its slash twin
follows the servermanagement/pm ephemeral type-4 pattern.

## ⟲ Previous-session review

(This previous-session review covers the automod flip, #173.) The
automod card's drift-class warning ("diff the fragments against the
golden FIRST") was applied here as a mandatory pre-step and the row
came back clean — the check cost one extra golden re-read and would
have caught a six-line security embed before any code was written. The
codex question on #173 (is the current-head cross-channel/duplicate
pair genuinely unconditional?) is still the open item that decides
whether automod's four-line card needs a gated successor; nothing in
this flip depends on its answer.
