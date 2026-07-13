# 2026-07-13 — night: native channel-recommender port (ORDER 019 item 5c)

> **Status:** `complete`

- **📊 Model:** `Fable (Claude 5 family)` · night lane worker · mandate: ORDER 019 item 5(c) — native channel-recommender port (perms-bearing snapshot), surviving setup-wizard follow-up per `docs/status/completeness-table-2026-07-13.md` setup row · claim: `control/claims/night-setup-followups-windowed-select.md` (PR #431)

## Scope

Port the oracle's channel recommender natively: pure scoring service
(`disbot/services/channel_recommender.py` @bbc524e — `recommend(intent_slug,
snapshot)` with reasons), a perms-bearing guild-channel snapshot type at the
right layer, the discord adapter fill, and the setup channels section
rendering "likely #channel (confidence)" + reasons like the oracle
(`disbot/views/setup/sections/channels.py::_recommendation_for`). Shared
heuristic `disbot/utils/channel_classify.py::classify_channel_name` also
powers cleanup profiles + cog_routing_profiles. Table-driven scorer tests;
section render tests per setup_band conventions. True up the completeness
table setup row.

## Previous-session review

`2026-07-13-night-onready-resume.md` (PR #437) — a clean three-seam land
(kernel boot hooks + anchored-panel editor + the resume sweep) whose 16b
`run_boot_hooks()` wiring and "uninstalled port degrades, never crashes"
posture this session leaned on directly; its evidence-first close-out
(exact test counts, per-decision flags) was the template worth copying.

## What shipped

PR #446, branch `claude/night-channel-recommender` (implementation commit
3a0abd1). The recommender, oracle-verbatim
(`disbot/services/channel_recommender.py` +
`disbot/utils/channel_classify.py` +
`disbot/views/setup/sections/channels.py` @bbc524e4dbdc8d6e994d6fd72d63c727fdd82a3d):

- `sb/domain/setup/recommender.py` (new, PURE — no port, no I/O): the
  10-intent catalogue, scoring tiers (+50 tag / +25 keyword-hint / +20
  full-perms / +10 partial / −10 send-blocked, view-less hard-excluded,
  non-positive dropped), confidence buckets (≥60 high / ≥30 medium),
  `ChannelRecommendation` + `recommend`/`top_pick`/`recommend_all` and the
  oracle `_BINDING_TO_INTENT` map — reason strings byte-verbatim. The FULL
  11-tag `channel_classify` pattern table rides along PRIVATELY
  (`_classify_channel_name`): the package's public `classify_channel_name`
  stays cleanup.py's consumed 4-tag subset (test-pinned bytes; shadowing
  guard rule 2), ledgered in-module.
- the perms-bearing snapshot: ALREADY COMPILED at
  `sb/domain/platform/guild_snapshot.py` (`ChannelMeta.bot_can_view/
  bot_can_send/bot_can_embed` — the oracle privacy-vetted GuildSnapshot);
  what was missing was a handler-side read. Added the guild-id-keyed
  source seam (`install_snapshot_source` / `snapshot_for`, reset extended)
  — uninstalled it degrades to None, never a crash.
- `sb/adapters/discord/setup_reads.py` (new): the live fill —
  `bot.get_guild → guild_snapshot.collect` for the snapshot source PLUS
  the deterministic advisor's channel index (`plan.install_channel_index`,
  previously parity-only: the live wizard's advisor hints now have data).
  Wired in `sb/app/main.py` step 14b³ (after READY, the
  ai_operator_ports precedent).
- `sb/domain/setup/channels.py`: `_recommendations` now recommender-first
  (per declared binding: `intent_for_binding` → `top_pick`, folded onto
  the advisor's `SetupRecommendation` shape with reason = `reasons[0]`,
  the oracle embed's "strongest single reason"), deterministic-advisor
  FALLBACK when the snapshot source is unarmed (parity harness + existing
  tests unchanged); embed line renders the oracle bytes
  ("✅ likely `#mod-log` (high — Name matches `likely_mod_log` pattern)")
  and Apply Recommended keeps the high-only auto-stage semantics. Ledger
  bullet flipped from flagged-follow-up to landed.
- Tests: `tests/unit/setup_band/test_channel_recommender.py` (35 cases —
  classifier table incl. subset-agreement guard, every scorer tier +
  exclusion + the (−score, name) ranking, seam round-trip/reset,
  channels-lane recs/embed bytes/high-only ops/medium-skip/advisor
  fallback, adapter fill perms fidelity + unknown-guild degrade).
- Verification: full suite **2965 passed / 15 skipped** (35 of them the
  new suite); `bootstrap.py check --strict` — my diff adds ZERO
  findings (the 2 doc findings on the fleet-cleanup audit + 4 claims
  advisories pre-exist on origin/main @5385442; this card's own born-red
  hold flips in this commit); all four guards clean
  (shadowing/namespace/no-skip/config).
- Completeness table setup row: recommender follow-up struck **DONE** in
  both the row and the §2 follow-up list.

## Guard recipe

`recommended_channel_ops` now has TWO sources with different reason
grammars: the recommender's "Name matches `tag` pattern" vs the advisor's
"channel name `x` matches token `y`". Any future test asserting reason
bytes must first pin WHICH lane is armed (install the snapshot source or
`plan.install_channel_index`, never both blind) — the autouse reset in
`test_channel_recommender.py::_fresh_ports` is the pattern (test:
`test_channels_fall_back_to_the_advisor_without_a_snapshot`).

## 💡 Session idea

Three guild-read ports now each carry a private duck-typed
`bot.get_guild` walk (`ai_operator_ports`, `setup_reads`, the utility
guild directory) that re-derive per-channel perms independently. A single
`sb/adapters/discord/guild_reads.py` with one perms-triple helper
(`view/send/embed` off `permissions_for`) would make the next
guild-snapshot consumer a three-line install and keep the perms semantics
from drifting between adapters — worth doing when the SectionRecoveryView
ride (the next setup follow-up touching these seams) lands.
