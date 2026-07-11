# 2026-07-11 — moderation parity flip (pending→ported, the twenty-third row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `moderation` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/moderation_cog.py` +
`services/{moderation_service,moderation_helpers}.py` +
`utils/{synonyms,command_resolution,moderation_feasibility}.py` +
`views/moderation/{main_panel,modals}.py` + `bot1.py:541-586` @7f7628e1.
Goldens: `parity/goldens/moderation/` — moderation_warn_flow, sweep_warn,
sweep_timeout, sweep_kick, sweep_ban, sweep_unban, sweep_modmenu,
sweep_slash_moderation. Pre-flip 0/8 → post 8/8 (first post-change replay).

## What shipped

1. **The shipped Moderation Panel** (`!modmenu` anchored + `/moderation`
   type-4 flags-64 ephemeral): seven modal-opening buttons with the
   PERSISTENT shipped ids via `custom_id_override` (`mod:warn` …
   `mod:clearwarn`; glyph-IN-label, shipped styles, 3/3/1 rows + the
   engine nav row's `nav:help`), orange embed via renderer_override
   (title `🔨 Moderation Panel`, the two-line description as grammar
   TextBlock, seven INLINE glossary fields, the dynamic non-inline
   `🤖 Bot readiness` field over a NEW guild.me read port
   (`install_moderation_readiness`; parity twin = the capture world's
   own truth: all perms, top role **Admin**), staff footer literal).
   G-10 ModalSpecs mirror `views/moderation/modals.py`; sim-gate lock
   gains the 3 layout rows (legacy-seed Exempt), compat pin gains the
   7 override ids + 7 modal ids.
2. **Timeout on the oracle's call-Discord-first sequencing** — the
   record leg calls the port BEFORE the row write; refusal aborts the
   txn (no row, NO event — a post-commit effect failure cannot un-emit
   the step-4e batch, so the old effect-leg+compensator shape was
   structurally unable to match). The parity twin reproduces the
   capture-world member-edit artifact (records `edit_member`, then
   raises `CaptureMemberEditParseError` — fake_http's canned PATCH
   response was unparseable to discord.py, so every captured `!timeout`
   died after the wire call). The command rides a HandlerRef wrapper:
   ctx.params side-channel marker (`_moderation_generic_error`, the
   karma `_karma_refusal` lane) → the shipped bot1.py literal
   "⚠️ An unexpected error occurred. Please try again." (sweep_timeout
   pins all of it: edit_member + error reply + zero-row/zero-event).
3. **Kick confirm OFF (D-0029 flip review → D-0065)**: the golden pins
   the shipped no-confirm immediate kick; the recovery posture survives
   as a compensatable effect leg + `compensate_kick` withdrawing the
   false history row on refusal (compensator allowlist stays EMPTY).
4. **Unban**: `fetch_user` before `unban` (shipped cog sequencing;
   sweep_unban pins `get_user` → `unban` → the ✅ ack).
5. **`moderation.action_taken` carries the shipped `mutation_id`**
   (oracle `_record_action` minted `str(uuid.uuid4())`; the K7 result's
   mutation_id carries it — additive EventSpec field, compat regen).
   NOT a disposition case: the golden pins the normalized `<uuid>` byte.
6. **`!warnings` retired; the shipped typo ladder ported** — the oracle
   never had a warnings command (warn_flow step 2 pins bot1.py's
   "❓ Unknown command `warnings`. Did you mean `!warn`?" — resolved via
   the `COMMAND_SYNONYMS` "warning" token → canonical `warn`); the
   SUGGEST half of the CommandNotFound ladder now lives in the kernel
   fuzzy adapter, armed by BOTH roots; mutating canonicals never
   auto-run (manifest-derived, not the shipped hand-list); the silent
   AUTO re-dispatch of reads is NAMED SUCCESSOR work.
7. **Capture-world config reseeded** — `CAPTURE_WORLD_SETTINGS` in the
   replay runner seeds `moderation_ban_delete_message_days=1` before the
   before-snapshot (sweep_ban pins `delete_message_seconds: 86400`;
   D-0029 called this class un-reseedable — it isn't).
8. **parity.yml**: moderation ported; ratchet
   `{events: 3, tables: 5, settings: 0}` (raw covered-side counts —
   audit.action_recorded + moderation.action_taken + xp.awarded;
   ai_decision_audit + mod_logs + panel_anchors + warnings + xp).
   **ZERO depth.exemptions rows**, zero new exemption/disposition
   classes; decision record D-0065.

## Traps confirmed / new intel

- **Effect-leg failure cannot suppress the op's domain event** (NEW,
  structural): engine step 4e builds the BEST_EFFORT batch in-txn and
  step 6 emits it after effect legs UNCONDITIONALLY — a golden pinning
  "external call happened, nothing recorded/emitted" forces the oracle's
  call-first sequencing INTO the DB leg (txn abort kills row + batch).
- **Capture twins may need to RAISE mid-flow** (11b extended): the
  member-edit route's canned fake_http response was unparseable AFTER
  recording — the twin reproduces the artifact (record then raise);
  bodyless-204 routes (kick/ban/unban) don't carry it.
- **Capture-world guild CONFIG is world state** (NEW): seed it in the
  replay runner before the before-snapshot; invisible to db_delta.
- **Fuzzy suggestions need the shipped SYNONYM tokens**: difflib over
  bare command names picks `clearwarnings` for "warnings"; the shipped
  ladder matched the synonym token "warning" → canonical `warn`.
- Trap 1 (ratchet scratch-learn/restore/hand-apply), 15a-wire-emoji
  inverse (glyph-in-label here), 14a (PanelRef slash type-4 direct +
  EPHEMERAL = flags-64, no anchor row), karma 16a side-channel, 16e
  (importlib `_replay_corpus`) all confirmed as written.

## Verification

- goldens/moderation 8/8 green; full gate **151/151 across 23 ported**
  on real Postgres; check_parity_depth OK (zero exemptions);
  check_sim_gate OK; check_compat_frozen OK; check_namespace/intent/
  slash_cap clean; **1313 passed, 5 skipped**.

## 💡 Session idea

(Backfilled 2026-07-11 in kit-upgrade PR #166, grammar-only: the original
session recorded no idea. Backfill exists so the strict session-gate's
newest-card-by-mtime pick cannot red CI on this card — see PR #166's card.)

## ⟲ Previous-session review

(Backfilled 2026-07-11 in kit-upgrade PR #166, grammar-only: the original
session recorded no previous-session review.)
