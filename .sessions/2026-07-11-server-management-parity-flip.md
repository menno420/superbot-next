# 2026-07-11 — server_management parity flip (pending→ported, the thirty-second row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `server_management` parity row (the #132 slash flip's PREFIX
sibling) pending→ported through the A-16 door. Oracle: menno420/superbot
`disbot/core/runtime/panel_manager.py` (the back-to-help hook seam) +
`disbot/cogs/help_cog.py` (`_attach_back_to_help_button` — persistent id
`help:back`, label `↩ Back to Help`, grey, row 4) + `disbot/bot1.py`
(the composition-root wiring) at the CORPUS sha 7f7628e1 (search_code
fragments). Golden: `parity/goldens/server_management/
sweep_servermanagement.json` — the `!servermanagement` admin sweep:
the SAME shipped hub as the slash twin but PUBLIC, ANCHORED
(`panel_anchors` row) and carrying a FOURTH component row (`help:back`).
Pre-flip 0/1 (2 diffs, exactly the two the #132 record predicted) →
post 1/1 AND the already-ported slash golden stays green. Wave-8 flip
3 of 3 (image_moderation #176 → counters #178 → server_management).

## What shipped

1. **Anchored panel-manager semantics**: `server_management.hub` flips
   `session_lifecycle=True → False` — the engine's `_record_anchor`
   already carries the whole surface split (message surfaces anchor,
   interaction surfaces never do — the moderation modmenu precedent),
   so the prefix open records the golden-pinned `panel_anchors` row and
   the slash twin's empty delta is untouched. Every component stays
   override-pinned (overrides render verbatim on non-session panels).
2. **The shipped back-to-help split**: the shipped root appended
   `↩ Back to Help` (persistent id `help:back`) to directly-invoked
   hubs on the panel-manager MESSAGE path only — the slash twin carried
   exactly three rows. Ported as a REAL routable action (`help_back`,
   `custom_id_override="help:back"`, handler → the ported `help.home`)
   plus a surface-keyed component drop in the existing
   renderer_override (the D-0068 component-drop lane): dropped when
   `ctx.surface == "slash"`. The never-strand fence is satisfied
   honestly by `navigation.parent = help.home` (the shipped escape IS
   Help); the grammar's injected `nav:back:*` button is dropped in the
   override (both goldens pin its absence) — both drops named in the
   justification (12c).
3. **NEW KERNEL SEAM (additive)**: `PanelContext` grew a defaulted
   `surface: str | None = None` field, set by the engine from
   `req.surface` — renderer overrides gain the surface dimension for
   surface-keyed rendering (this flip's split is its first consumer).
   No constructor elsewhere needed changes (defaulted tail field).
4. **compat pin amended in-PR** (`check_compat_frozen --write`): the
   `help:back` override joined `legacy_custom_ids` — the id the design
   spec's §2 hazard table already froze verbatim for exactly this
   button (rebuild-design-spec-2026-07-02 hazard 2). ZERO sim-gate lock
   churn (1055 [A] / 370 auto-exempt unchanged — the panel's rows stay
   below-floor semantics, overrides were already pinned).
5. **parity.yml**: server_management ported (32/49); ratchet
   `server_management: {events: 1, tables: 3, settings: 0}` (raw
   covered-side: xp.awarded; ai_decision_audit + panel_anchors + xp —
   trap 14d). **ZERO depth exemptions, ZERO new reason classes, ZERO
   decision records.** Compensator allowlist stays EMPTY (read-only
   hub; the manager clicks stay pending terminals/ported forwards).
6. **Tests**: the two band-6 hub tests that pinned the pre-flip
   session-lifecycle shape updated to the flipped shape (their own
   docstring deferred the prefix semantics to this flip), plus a NEW
   test pinning the slash-surface drop (net units 1357/2).

## Ledgered unpinned corner (in-code docstring)

A 🔄 Refresh click re-renders on the COMPONENT surface and keeps the
`help_back` row — matching the shipped ANCHORED panel's refresh; the
shipped slash-opened ephemeral's refresh stayed three-row, and that
ephemeral-refresh corner renders four rows here until a message-context
signal ports (surface alone cannot split the two refresh homes). No
golden drives either refresh path.

## Traps confirmed / new intel

- Trap 24 drift check: PASSED — the golden's `help:back` bytes match
  the oracle's `help_cog.py` fragments verbatim (label/style/id).
- The #132 flip record's "2 diffs from anchored-persistent-panel
  semantics" was exactly right — and BOTH diffs resolved with zero new
  reason classes: one spec flag + one declared action + one additive
  kernel context field.
- NEW: replay/report/pytest must NEVER run concurrently on the shared
  Postgres — a raced report mis-reported 142/465 and a raced isolation
  replay invented xp diffs (double-award shapes) during the counters
  flip; serial reruns were clean both times. Diagnose by re-running
  alone before believing any replay red that appears alongside another
  DB consumer.
- Traps 1 (scratch-learn/restore/hand-apply), 8 (not needed — the row's
  command was already grouped correctly), 14d, 16e confirmed.

## Verification

- goldens/server_management 1/1 green + goldens/servermanagement 1/1
  still green (isolation replay of BOTH rows); full gate **175/175
  across 32 ported** on real Postgres; report leg **212/465** green,
  465/465 replayable; check_parity_depth OK — 49 subsystems (32
  ported), 465 goldens; check_sim_gate OK (1055 [A], 370 auto-exempt);
  check_compat_frozen OK (pin amended in-PR); check_namespace / egress
  / no_skip clean; manifest_compile green; unit suite **1357 passed, 2
  skipped** local (canonical order).

## 💡 Session idea

The remaining pending map is now: diagnostic (37 goldens, the big one),
setup (PARKED, trap 17), quicksetup (BLOCKED, D-0030), four_twenty (1),
treasury (2), admin/casino/community/community_spotlight/creature/farm/
fishing/games/inventory/mining/role (game/band-successor rows), and
`_unmapped` (220). The `PanelContext.surface` seam this flip added is
likely diagnostic's friend too — its 37 goldens span prefix and slash
twins of the same panels.

## ⟲ Previous-session review

(Covers the counters flip, #178.) Its card predicted the slash twin
lane correctly and its type-4 components-drop fix held here untouched
(the slash hub golden still pins its 3 NON-empty rows — the drop-when-
empty filter proved surgical). Its "session idea" flagged
`GuildInfo.bots` live-arming — unchanged, still owed to the live
guild-directory arming slice. The DB-concurrency hazard it ledgered in
the PR body bit AGAIN this flip (the raced isolation replay) and is now
generalized in the new-intel entry above.
