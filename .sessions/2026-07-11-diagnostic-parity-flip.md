# 2026-07-11 — diagnostic parity flip (pending→ported, the thirty-third row; 37 goldens — the largest single flip)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `diagnostic` parity row pending→ported through the A-16 door —
the largest pending row: 37 goldens (`sweep_diagnostics`, `sweep_latency`,
`sweep_platform`, `sweep_slash_platform`, and 33 `sweep_platform_<sub>`
sweeps). Oracle: menno420/superbot `disbot/cogs/diagnostic/`
(platform_group.py, _backfill.py) + `disbot/services/`
(diagnostic_embeds.py, diagnostic_helpers.py, binding_backfill.py) +
`disbot/views/diagnostic/platform_panel.py` @ the corpus posture
(reconstructed via search_code fragments — full-file oracle reads stay
denied, playbook trap 3/15f). Pre-flip 0/37 → post **37/37 — green on
the FIRST isolation replay**.

## What shipped

1. **The golden-derived pinned-card lane at scale**
   (`sb/domain/diagnostic/platform_views.py`): 28 `!platform <view>`
   operator cards are CAPTURE-WORLD SNAPSHOT LITERALS — the shipped
   surfaces are process-introspection over the OLD bot's own runtime
   (its 43-subsystem governance registry, 19 SubsystemSchemas, the
   103-step migration ladder, 10 PersistentViews, the consistency
   collectors' 9-clean/2-warning tally), which the v1 kernel cannot
   reproduce byte-for-byte by introspecting itself — the trap-10a/20
   pinned-literal lane, one golden per surface. The ONLY non-literal
   bytes are the four world seams the goldens tokenize: channel mention
   (`<#<#general>>`), guild id (`<guild>`), ISO now (`<ts>`), invoker
   member tier (the access card's `owner`). The table was GENERATED
   from the goldens (zero transcription drift), reviewed, and documented
   per-seam. Live introspection over the new kernel is named successor
   work.
2. **The 🛰 Platform hub on BOTH surfaces** (`diagnostic.platform_hub`):
   four PERSISTENT-id category selects (`platform_hub.runtime/
   catalogues/resources/validation` — verbatim `custom_id_override`
   pins; the shipped view was sent as a plain session send, never
   anchored — neither golden carries a `panel_anchors` row) + the
   ↩ Overview / 🚩 Flag manager button row (`platform_hub.overview` /
   `platform_hub.flag_manager`). The slash twin costs ONE explicit
   posture: the front door is a HandlerRef (`diagnostic.pf_root` — it
   answers honest refusals for undeclared tokens), and slash+HandlerRef
   AUTO-defers by default, so the CommandSpec declares
   `DeferMode.NONE` for the golden's type-4 direct + flags-64 response
   (Audience.INVOKER). Select picks route to the SAME cards the typed
   subcommands render (`diagnostic.hub_open_view`).
3. **The shipped 🔧 Diagnostics Hub reshape** (`diagnostic.hub`,
   oracle-wins over the band-1 projection hub — the D-0067 lane): eight
   tool buttons (styles 1/1/1, 2/2/2, 4/2; run-minted ids → `<cid:N>`),
   the 8-inline-field overview embed, blue, the "Diagnostics Hub  •
   Admin only" footer. Only 📡 Latency routes a ported tool; the other
   seven land on the honest pending terminal (their command twins were
   capture-SKIPPED as nondeterministic process-state —
   `parity/goldens/_sweep_skips.json`).
4. **The 🚩 Flag Manager + 🤖 Automation panels**: flag_manager pins the
   shipped persistent `flag_manager:*` ids verbatim (the help:back
   precedent) over the capture world's pinned 8-flag option registry
   (v1 has no flag rollout pipeline — mutations land on the honest
   pending terminal); the automation panel is a true session view (all
   five ids → `<cid:N>`) with the no-rules placeholder option and the
   scheduler-not-registered snapshot line (true as a constant in BOTH
   worlds).
5. **The backfill dry-run WRITE lane** (`diagnostic.backfill_dry_run`,
   the row's one op): migration `0029_platform_migration_checkpoints`
   (the oracle's 026 DDL, NAME_STABLE, reconstructed by fragment —
   only `dry_run_complete` is golden-pinned), a new store
   (`sb/domain/diagnostic/store.py`, DataClass.NONE), and ONE audited
   DB leg writing the checkpoint row with the classification document
   (`summary_json`: the shipped two-entry homed-pointer catalog
   `xp_announce_channel`/`economy_log_channel`, classification computed
   from real binding reads + the structurally-None v1 legacy read —
   `both_absent`, the golden's bytes). `backfill apply` is NOT ported
   (no golden) — honest refusal. LEDGERED RECONSTRUCTION LIMIT: the
   shipped enum member for the legacy-absent/binding-present cell never
   surfaced through search_code; the port names it `binding_present`
   (live-only — no parity case can reach it from a truncated DB).
6. **Guard bytes handler-side (trap 22)**: `finding` (the "❓ Unknown
   action…" plain-content byte), `setting` (the red "⚙️ Unknown
   setting" card over `iter_declarations`, the shipped
   `{subsystem}.{name}` join), `latency` (the shipped
   `f"{ms:.2f} ms"` over `bot.latency` — the capture gateway never
   measured a heartbeat ⇒ the golden's `nan ms`; the live read arms via
   `install_ws_latency_reader`, unarmed in the harness by design).
7. **One additive kernel seam**: `RenderedEmbed.timestamp` (ISO-8601
   string) — the corpus's first embed-timestamp pin
   (sweep_platform_findings); the parity twin serializes it verbatim
   (`_embed_payload`), the live adapter parses it to the native
   datetime (`panel_view.build_embed`) — the trap-14b both-presenters
   rule.
8. **Manifest**: 35 new CommandSpecs (latency + platform BOTH + 33
   `group="platform"` subcommands, tier `administrator` — the shipped
   gate), 4 new panels + the hub reshape; `stores=(platform_migration_
   checkpoints,)` — carried by the backfill golden, so **ZERO depth
   exemptions, ZERO new reason classes, ZERO decision records**;
   the five capture-skipped process-state subcommands
   (health/runtime/slow/startup/status) are deliberately UNDECLARED
   (declaring them would mean inventing bytes) — the root handler
   answers the honest refusal. Compensator allowlist stays EMPTY (one
   reversible DB leg, no compensators). parity.yml: diagnostic ported
   (33/49); ratchet `diagnostic: {events: 1, tables: 3, settings: 0}`
   (raw covered-side, trap 14d).

## Ladder (serial — trap 25)

- goldens/diagnostic **37/37 green on the FIRST isolation replay**
  (importlib `_replay_corpus({"diagnostic"})`, trap 16e); full gate
  **212/212 across 33 ported** on real Postgres; report leg **249/465**
  green, 465/465 replayable; check_parity_depth OK — 49 subsystems (33
  ported), 465 goldens; check_sim_gate OK (1125 [A], 393 auto-exempt;
  47 legacy-seed rows amended ADDITIVELY into
  manifest/layout/diagnostic.lock.json); check_compat_frozen OK (+33
  command rows, +10 verbatim custom_id pins); check_namespace / egress /
  no_skip / slash_cap / intent_survival / migrations clean;
  manifest_compile green; unit suite **1374 passed, 2 skipped** local
  (canonical order; the one first-pass red was the store engine-ref
  re-arm, fixed as its own commit — plus a self-inflicted phantom from
  racing pytest against my own parity.yml scratch-learn, clean on the
  serial rerun).

## 💡 Session idea

The games-family tail (treasury/four_twenty/admin/casino/community/
community_spotlight/creature/farm/fishing/games/inventory/mining/role,
1–5 goldens each) should fall to the SAME three recipes this flip
exercised at scale: pinned snapshot cards (generate the literal table
FROM the goldens — zero transcription drift, and the generator doubles
as the review artifact), handler-owned guard bytes (trap 22), and the
`diagnostic.card` generic-card lane (ai.card clone) whenever a reply is
an embed. Before porting each row, grep `_sweep_skips.json` FIRST — a
listed skip means the subcommand must stay UNDECLARED, not refused-late
(the health/runtime/slow/startup/status precedent).

## ⟲ Previous-session review

(Covers the wave-8 flips #176/#178/#179.) Trap 26's two halves both
bound here: the type-4 empty-components omission held for the
`/platform` twin for free (the #178 fix), and the slash+PanelRef
DeferMode.NONE default was the INVERSE trap this time — the platform
front door is a HandlerRef, which AUTO-defers on slash, so the flip
needed the explicit `DeferMode.NONE` the counters card never did. The
#179 `PanelContext.surface` seam, predicted "likely useful for
diagnostic's twins", was NOT needed — both platform goldens pin
byte-identical payloads (modulo flags), so no surface-keyed rendering
exists on this row. Trap 25 (serial ladder) bit once anyway:
a background pytest raced my own parity.yml scratch-learn and produced
a phantom boot-gate red — clean serial rerun green; the trap covers
FILE mutation, not just the shared DB.
