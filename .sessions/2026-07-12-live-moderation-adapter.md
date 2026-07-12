# 2026-07-12 — live moderation guild-action adapter (D-0049 live successor, SLICE 1 / live-guild-effects)

> **Status:** `complete`

- **📊 Model:** builder-agent · high · feature build (SLICE 1 / live-guild-effects)

## What I'm about to do

Arm a LIVE, TEST-PLANE-GATED `DiscordModerationActions` behind the
moderation guild-action port (`GuildModerationActions`,
sb/domain/moderation/service.py). The moderation twin of RC-21's
`DiscordChannelEmitter`: the domain never touches discord, the
composition root installs the concrete adapter, and the not-installed
default keeps raising LOUDLY. Installed ONLY under
`SB_DATA_PLANE == "test"` — the prod root stays unarmed (the owner's
CUT-3 gate). Moderation only this slice (role/channel/proof_channel
ports are slices 2/3). No golden-parity row flips — moderation stays
pending until full-corpus golden green through the A-16 door.

## Scope

- `sb/adapters/discord/moderation_actions.py` (new) —
  `DiscordModerationActions` implementing the 6-method port
  (timeout/kick/ban/unban/fetch_user/dm_member) + a
  `DiscordModerationReadinessReader` reading `guild.me` (the oracle's
  `evaluate_moderation_readiness` contract, byte-for-byte).
- `sb/app/main.py` step 10a — test-plane-gated install
  (`moderation_plane_armed(cfg)` → `SB_DATA_PLANE == "test"`), mirroring
  the `guild_sync_target` gate. Prod arming flagged as the owner's CUT-3
  gate.
- `tests/unit/band2/test_live_moderation_adapter.py` (new) — the live
  twin of the channel-ops capture contract test: each port method's
  exact discord.py call + kwargs.
- `tests/unit/app/test_main_wiring.py` — the gate assertion (live root
  arms moderation ONLY under the test plane).

## Delivered

- `sb/adapters/discord/moderation_actions.py` (new) —
  `DiscordModerationActions` implementing the 6-method
  `GuildModerationActions` port, modelled on `DiscordChannelEmitter`
  (import-guarded `discord`, `__init__(bot)`):
  - `timeout_member` → resolve guild + member, `member.timeout(until,
    reason=reason)` with `until = discord.utils.utcnow() +
    timedelta(minutes=minutes)` (never bare `datetime.now()`).
  - `kick_member` → `guild.kick(discord.Object(user_id), reason=reason)`.
  - `ban_member` → `guild.ban(discord.Object(user_id), reason=reason)`,
    adding `delete_message_seconds=days*86400` ONLY when `days > 0`
    (oracle default 0 = no purge — mirrors `transport.py:845-853`).
  - `unban_member` → `bot.fetch_user(user_id)` THEN
    `guild.unban(user, reason=reason)` (oracle fetch-then-unban).
  - `fetch_user` → `await bot.fetch_user(user_id)`;
    `dm_member` → fetch user, `await user.send(text)`.
  - `DiscordModerationReadinessReader` — reads `guild.me` per the oracle
    `evaluate_moderation_readiness` contract byte-for-byte (admin implies
    every capability; `top_role_is_lowest == top_role.position == 0`);
    returns None when the guild/bot-member is uncached (the documented
    field-drop degrade, never a fabricated readiness).
- `sb/app/main.py` — `moderation_plane_armed(cfg)` predicate (mirrors
  `guild_sync_target`'s single `SB_DATA_PLANE == "test"` switch) + step
  10a: under the gate, `install_moderation_actions(
  DiscordModerationActions(bot))` +
  `install_moderation_readiness(DiscordModerationReadinessReader(bot))`.
  Prod stays un-armed — commented as the owner's CUT-3 gate.
- Tests: `tests/unit/band2/test_live_moderation_adapter.py` (7 cases —
  exact discord.py call + kwargs per port method, via a fake `discord`
  module so it runs in the discord-absent CI container) +
  `tests/unit/app/test_main_wiring.py::TestModerationPlaneGate` (the gate
  opens only on the test plane; the install is guarded by it).

## Evidence

- `python3 -m pytest tests/` — **1736 passed, 8 skipped** (the 8 are
  the pre-existing suite skips, unchanged).
- `python3 bootstrap.py check --strict` — the ONLY exit-affecting
  finding was the born-red HOLD on this card (by design); one
  pre-existing advisory (`control/status.md` owner-action risk-class,
  never exit-affecting, not in this diff). Green on card flip → complete.
- No golden-parity file touched; the `report` job stays born-red by
  design (not a required check).

## Depth finding (for the flip lane)

Readiness WAS installed live (not deferred): `guild.me` is available at
readiness-read time via `bot.get_guild(guild_id)`, so the reader is a
real read, not a boot-time handle problem — no faking needed. The live
reader can't flip a golden: parity runs its own `_world_readiness`
through `sb/adapters/parity/boot.py`, isolated from this root's install.
The moderation goldens (sweep_timeout etc.) stay pending behind A-16 —
the live adapter simply does not raise where the capture twin's
`CaptureMemberEditParseError` did, which is exactly the D-0049 posture
the flip lane needs when the corpus is re-cut.

## 💡 Session idea

The three live-guild-effect adapters (moderation now, role + channel-perm
+ proof_channel next) all share one boot shape: a `<port>_plane_armed(cfg)`
predicate + a gated `install_*` block. Extract a tiny
`arm_test_plane_effect(cfg, *, install)` helper in `sb/app/main.py` so
slices 2/3 add one line each and the test-plane gate is asserted in ONE
place — the gate becomes a single audited switch instead of three
copy-pasted `SB_DATA_PLANE == "test"` reads that could drift.

## ⟲ Previous-session review

The channel-ops-adapter card (#? / D-0077) set the template this slice
followed almost verbatim — its "extend the existing port vs invent a
parallel protocol" resolution and its explicit parity-vs-live twin split
made the port-home and the capture-vs-live wire-shape questions a lookup,
not a debate; strong precedent hygiene. What it under-specified for a
successor: it named the moderation port as "still unarmed" but did not
flag that the LIVE readiness reader is trivially installable (guild.me is
a read-time handle, not a boot-time one) — this session had to confirm
that against the oracle to decide install-vs-defer. **System improvement:**
successor-naming lines in a card's status fold should carry a one-word
feasibility tag (`install-ready` / `boot-blocked`) next to each unarmed
port, so the next slice knows whether readiness is a lookup or a real
blocker before it reads the oracle.

