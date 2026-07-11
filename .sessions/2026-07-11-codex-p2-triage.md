# 2026-07-11 — Codex P2 triage: ticket alias scope + post-panel gate + karma followup

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · bug fix (Q-0194)

## Scope

Triage the three post-merge Codex P2 findings ledgered by heartbeat #158
(PR #154 review 4676723779 findings A/B; PR #157 review 4676836079),
Q-0120 posture: verify every claim against oracle source + goldens
before acting. Verdict: **all three real** — one PR, three minimal
fixes, zero golden-byte movement.

## Findings + fixes

1. **Ticket subcommand aliases were indexed unqualified** (PR #154 A —
   REAL). Oracle: `@ticket.command(name="new", aliases=["open",
   "create"])` (disbot/cogs/ticket_cog.py) — discord.py group aliases
   are GROUP-SCOPED: `!ticket open` routed ticket_new; bare `!open`
   never existed. Both dispatch indexers (`build_live_index`,
   parity boot `_build_index`) registered `cmd.aliases` verbatim, so
   `!ticket open <s>` fell back to the bare `ticket` hub and top-level
   `!open`/`!create` routes leaked — `create` SHADOWING the shipped
   channel op `!create` (sb/manifest/channel.py). Fix: ONE shared key
   truth `sb/spec/commands.py command_dispatch_keys()` — qualified name
   + group-scoped aliases — consumed by both indexers. Also corrects
   treasury contribute/grant (donate/deposit/disburse/payout), whose
   oracle registration was likewise group-scoped; treasury goldens are
   still pending rows, nothing pinned either way.
2. **`ticket_post_panel` missing the staff gate** (PR #154 B — REAL).
   Oracle (views/tickets/hub.py): `get_config` → `is_ticket_staff`
   (admin/manage_guild perms or the configured staff role) →
   `post_launcher`; refusal byte `"Only staff can post the ticket
   panel."` ephemeral. The port answered NOT_CONFIGURED to everyone. At
   the v1 config-absent epoch the cfg staff-role leg is vacuous, so the
   gate is exactly ActorRef.is_guild_operator (owner/administrator/
   manage_guild — the same shipped vocabulary). Fix in
   `sb/domain/ticket/handlers.py`: gate first (shipped byte verbatim),
   staff still land on the under-port NOT_CONFIGURED lane. Button stays
   user-tier visible (golden sweep_ticket.json pins it in the hub row;
   shipped gate was callback-side, not visibility).
3. **Live `/karma` panel landed on `edit_original_response`** (PR #157 —
   REAL). resolve()'s AUTO defer acks type-5; DiscordPanelPresenter's
   post-ack branch then PATCHed the deferred original, while the shipped
   bot (safe_defer + safe_followup) and the parity twin
   (transport.py: first response `interaction_response`, every later one
   `followup_send`; goldens/karma/karma_slash_card.json pins type-5
   flags-64 + followup embeds) send a webhook FOLLOWUP. Fix in
   `sb/adapters/discord/panel_view.py`: already-acked interactions ride
   `origin.followup.send(..., ephemeral=...)` — live-adapter only,
   parity replay path untouched.

## Proof

- `python3 -m pytest tests/ -q` — 1319 passed, 5 skipped (new:
  tests/unit/band8/test_band8_ticket.py gate tests; presenter routing
  tests in tests/unit/app/test_cut1_surfaces.py; group-scoped alias
  index tests in tests/unit/app/test_main_wiring.py).
- Full local parity gate on real Postgres: **GREEN — 143/143 goldens
  across 22 ported subsystems** (the alias change is parity-visible by
  construction; no golden invokes a grouped alias, so bytes hold).

## Constraints honored

No new exemption/disposition classes; compensator allowlist EMPTY;
band-6 game subsystems, sb/domain/role pending terminals,
control/status.md, parity.yml untouched.

## 💡 Session idea

(Backfilled 2026-07-11 in kit-upgrade PR #166, grammar-only: the original
session recorded no idea. Backfill exists so the strict session-gate's
newest-card-by-mtime pick cannot red CI on this card — see PR #166's card.)

## ⟲ Previous-session review

(Backfilled 2026-07-11 in kit-upgrade PR #166, grammar-only: the original
session recorded no previous-session review.)
