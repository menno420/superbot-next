# 2026-07-12 — live channel EFFECT adapters (SLICE 3 / live-guild-effects)

> **Status:** `in-progress`

- **📊 Model:** builder-agent · high · feature build (SLICE 3 / live-guild-effects)

## What I'm about to do

Arm the LIVE, TEST-PLANE + TEST-GUILD-GATED channel adapters — the final slice
of the live-guild-effects lane, after SLICE 1 (moderation, #263) and SLICE 2
(role, #278). Two ports behind two SEPARATE seams:

- `ChannelStateActions` (sb/domain/channel/service.py) — `set_slowmode`,
  `set_overwrite`, `create_text_channel`, `delete_channel`, `create_invite`
  (the shipped `ChannelLifecycleService` Discord edits + the `!invite` re-home).
- `ChannelPermActions` (sb/domain/proof_channel/service.py — a SEPARATE port,
  NOT the channel domain's) — `lock_channel_for_winner`, `unlock_channel`
  (the shipped `proof_channel_cog` prize-access lock/unlock).

The channel/proof twin of the moderation + role adapters (D-0049): the domain
never touches `discord`, the composition root installs the concrete adapters,
and the not-installed defaults keep raising LOUDLY. Installed ONLY under
`SB_DATA_PLANE == "test"` AND an explicit `SB_APPCMD_SYNC_GUILD_ID` — the SAME
double gate + hard per-call test-guild allow-list SLICE 1/2 established. The
prod root stays unarmed (the owner's CUT-3 gate). No golden-parity row flips;
`import discord` stays inside `sb/adapters/discord/` only.

## Scope

- `sb/adapters/discord/channel_actions.py` (new) — `DiscordChannelStateActions`,
  `DiscordProofChannelActions`, `DiscordChannelLookup` (reusing the
  `_GuildAllowList` base from role_actions + `GuildNotAllowedError` from
  moderation_actions).
- `sb/app/main.py` step 10a — `install_channel_actions`,
  `install_channel_lookup`, and proof_channel's `install_channel_actions`,
  under the SAME `if test_guild_id is not None:` gate, adjacent to moderation +
  role.
- `tests/unit/band6/test_live_channel_adapters.py` (new) — the ChannelStateActions
  contract test (band6 is the channel hub's home).
- `tests/unit/band5/test_live_proof_channel_adapter.py` (new) — the
  proof_channel ChannelPermActions contract test (band5 is proof_channel's home).
- `tests/unit/app/test_main_wiring.py` — the channel gate assertions.

## Delivered

[[fill on green]]

## Slice base

Stacks on PR #278 (`claude/live-role-adapters`, head `bae724a`) — SLICE 3 edits
the same `sb/app/main.py` step-10a region SLICE 1/2 install moderation + role
in, so it bases off #278's head branch rather than main (a separate main branch
would conflict). #278 in turn stacks on #263 (`claude/live-moderation-adapter`).
Reuses `GuildNotAllowedError` from #263's `moderation_actions.py` and the
`_GuildAllowList` base from #278's `role_actions.py`.

## Evidence

- `python3 -m pytest` — [[fill on green]]
- `python3 bootstrap.py check --strict` — [[fill on green]]

## 💡 Session idea

[[fill on green]]

## ⟲ Previous-session review

[[fill on green]]
