# 2026-07-12 — live moderation guild-action adapter (D-0049 live successor, SLICE 1 / live-guild-effects)

> **Status:** `in-progress`

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

_(filled at close-out)_

## Evidence

_(filled at close-out)_

## 💡 Session idea

_(filled at close-out)_

## ⟲ Previous-session review

_(filled at close-out)_
