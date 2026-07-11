# 2026-07-11 — automod parity flip (pending→ported, the twenty-eighth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `automod` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/automod_cog.py` (`_policy_embed`)
at the CORPUS sha 7f7628e1 (reconstructed via search_code fragments —
full-file oracle reads stay denied, playbook trap 3/15f). Golden:
`parity/goldens/automod/sweep_automod.json` — the R2-singleton
`!automod` admin sweep. Pre-flip 0/1 → post 1/1 (green on the FIRST
isolation replay). Wave-7 R2-singleton 2 of 3 (welcome ✅ → automod →
security).

## What shipped

1. **The shipped `!automod` policy embed** replaces the generic
   operator-spine hub route: `automod.status`, a component-less
   session-lifecycle result card (the welcome.status recipe verbatim —
   ZERO panel_anchors rows, ZERO sim-gate lock rows). The
   renderer_override composes `_policy_embed`: the Master `_flag` line,
   the four capture-time rule lines with their live threshold
   parameterizations (`🛑 **Spam** — {flag} (> {count} msgs / {window}s)`,
   `🔗 **Invite links** — {flag}`,
   `🔠 **Excessive caps** — {flag} (>= {percent}% uppercase)`,
   `📣 **Mass mentions** — {flag} (>= {count} mentions)`), the
   two-sentence footer literal ("Configure in !settings → Automod.
   Actions route through moderation (warn → escalation)."), MOD_COLOR =
   the existing `orange` style token (15105570 — STYLE_TOKEN_COLORS
   already carried it, trap 12e held).
2. **CAPTURE-SHA FIDELITY CALL (the flip's one real decision)**: the
   oracle's CURRENT head renders TWO MORE rule lines (`🌐 Cross-channel
   spam`, `🔁 Duplicate content`) that the imported golden does not
   carry — post-capture oracle drift, not conditionality (the current
   head's `lines = [...]` list is unconditional). Parity pins the
   corpus (@7f7628e1, parity.yml `source.sha`), so the card renders the
   capture-time four-rule set; the two later rules stay declared
   settings (the band-2 manifest already claimed the shipped keys) and
   are ledgered in the module docstring as the re-import successor. No
   depth impact — toggles are settings (dead dimension, trap 10c).
3. **No new domain service**: automod's reads are plain
   `kernel.settings.resolve` scalars (no bindings, no guild reads) —
   the renderer reads the seam directly, matching the shipped cog's
   policy-load-then-render shape.
4. **parity.yml**: automod ported (28/49); ratchet
   `automod: {events: 1, tables: 2, settings: 0}` (raw covered-side:
   xp.awarded; ai_decision_audit + xp — trap 14d). **ZERO depth
   exemptions, ZERO new classes, ZERO decision records** (`stores=()`/
   `events=()` declared; the on_message enforcement feed arms with the
   message band). Compensator allowlist stays EMPTY (read-only slice).
   The invoking-message delete tail is the ruled
   invoking-message-deletion disposition (trap 15c).

## Traps confirmed / new intel

- **NEW: post-capture ORACLE DRIFT is a real class** — search_code
  reconstructs the oracle's DEFAULT BRANCH, which can be ahead of the
  corpus sha (parity.yml `source.sha` 7f7628e1). When a reconstructed
  fragment renders MORE than the golden pins, diff against the golden
  FIRST and pin the corpus: the golden bytes are the capture-time
  truth, the extra surface is drift to ledger, not conditionality to
  invent. (The welcome/security fragments matched their goldens
  exactly; automod is the first drift bite.)
- The welcome status-card recipe held with zero deltas: same spec
  shape, same renderer skeleton, only the line vocabulary and style
  token changed. Flip time was dominated by oracle reconstruction, not
  port work.
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 12d (session
  panels ⇒ zero lock/compat churn), 12e (check STYLE_TOKEN_COLORS
  before minting), 16e (importlib `_replay_corpus`) confirmed as
  written.

## Verification

- goldens/automod 1/1 green (isolation replay, first try); full gate
  **170/170 across 28 ported** on real Postgres; report leg **207/465**
  green, 465/465 replayable; check_parity_depth OK — 49 subsystems (28
  ported), 465 goldens; check_sim_gate OK (1046 [A], 361 auto-exempt);
  check_compat_frozen OK; check_namespace / egress / no_skip clean;
  manifest_compile green; unit suite **1356 passed, 2 skipped** local
  (canonical order).

## 💡 Session idea

The four_twenty row (1 golden) and image_moderation row (1 golden) may
be the same status-card shape — the `Configure in !settings → Image
moderation.` footer already surfaced in the welcome-flip footer sweep;
a single search_code pass over each golden's pinned footer/title
literals would confirm whether the welcome/automod/security recipe
covers five R2 singletons instead of three.

## ⟲ Previous-session review

(This previous-session review covers the welcome flip, #172.) The
welcome card promised the recipe would port automod "with only the line
vocabulary and color changing" — that held exactly, including the
prediction to check STYLE_TOKEN_COLORS for MOD_COLOR before assuming a
new token (orange 15105570 was already pinned). What the welcome card
did NOT anticipate was the capture-sha drift bite this flip surfaced
(new-intel entry above); the security golden re-read confirms its
fragments match the corpus bytes, so the drift class is automod-only in
this wave.
