# 2026-07-12 — live role EFFECT adapters (SLICE 2 / live-guild-effects)

> **Status:** `in-progress`

- **📊 Model:** builder-agent · high · feature build (SLICE 2 / live-guild-effects)

## What I'm about to do

Arm three LIVE, TEST-PLANE + TEST-GUILD-GATED role adapters behind the role
EFFECT ports (`GuildRoleActions` / `RoleProvisioning` / `MessageOps`,
sb/domain/role/service.py). The role twin of SLICE 1's
`DiscordModerationActions` (D-0049): the domain never touches `discord`, the
composition root installs the concrete adapters, and the not-installed defaults
keep raising LOUDLY. Installed ONLY under `SB_DATA_PLANE == "test"` AND an
explicit `SB_APPCMD_SYNC_GUILD_ID` — the SAME double gate + hard per-call
test-guild allow-list SLICE 1 established. The prod root stays unarmed (the
owner's CUT-3 gate). Role only this slice (channel/proof_channel ports are
slice 3). No golden-parity row flips; no channel/proof_channel port touched.

## Scope

- `sb/adapters/discord/role_actions.py` (new) — `DiscordGuildRoleActions`,
  `DiscordRoleProvisioning`, `DiscordRoleMessageOps` (reusing
  `GuildNotAllowedError` from moderation_actions).
- `sb/app/main.py` step 10a — the three `install_*` calls adjacent to
  moderation's install, under the SAME `if test_guild_id is not None:` gate.
- `tests/unit/band5/test_live_role_adapters.py` (new) — the contract test.
- `tests/unit/app/test_main_wiring.py` — the gate assertion.

## Delivered

- `sb/adapters/discord/role_actions.py` (new) — three concrete adapters on a
  shared `_GuildAllowList` base (`bot` duck-types `get_guild`/`get_channel`,
  `import discord` import-guarded, hard test-guild allow-list raised BEFORE any
  Discord call):
  - `DiscordGuildRoleActions.add_role` / `remove_role` → resolve guild
    (allow-list) + member (`get_member` → `fetch_member`), then
    `member.add_roles(discord.Object(role_id), reason=reason)` /
    `member.remove_roles(...)` — a bare snowflake, no cached-Role round-trip.
  - `DiscordRoleProvisioning.create_guild_role` → allow-list guild →
    `guild.create_role(name=name, colour=discord.Colour(color), reason=reason)`,
    returns `role.id`. A-5 fence honoured: the method is `create_guild_role`,
    the discord.py verb (and captured golden verb) is `create_role` — the name
    split is intentional, not a rename.
  - `DiscordRoleProvisioning.delete_role` → allow-list guild →
    `guild.get_role(role_id)` (cache read, the shipped RoleConverter path) →
    `role.delete(reason=reason)`; a vanished role is a loud RuntimeError, never
    a silent no-op.
  - `DiscordRoleMessageOps.fetch_message` / `add_reaction` — CHANNEL-scoped:
    the guild is resolved from the channel's CACHE entry (`bot.get_channel`,
    never a REST fetch — resolving via REST would touch a possibly-prod channel
    before the allow-list). The allow-list is applied where a guild is
    resolvable; a channel whose guild is not the allowed test guild — or is not
    resolvable at all (DM/uncached) — is REFUSED, so a reaction-role bind stays
    test-guild-only. `fetch_message` reads the message (the oracle's
    `ctx.fetch_message` existence read, captured `get_message`);
    `add_reaction` fetches then `message.add_reaction(emoji)`.
- `sb/app/main.py` step 10a — under the SAME `moderation_test_guild(cfg)` gate,
  adjacent to moderation's install: `install_role_actions`,
  `install_role_provisioning`, `install_message_ops`, each constructed with
  `allowed_guild_id=test_guild_id`. Prod stays un-armed (no test-guild id) —
  commented as the owner's CUT-3 gate.
- Tests: `tests/unit/band5/test_live_role_adapters.py` (exact discord.py call +
  kwargs per port method; create_guild_role returns the new role id; delete
  loud on a vanished role; the allow-list refusing every non-allowed guild on
  every guild-scoped method; MessageOps refusing a wrong-guild AND an
  unresolvable-guild channel — via a fake `discord` module so it runs in the
  discord-absent CI container) +
  `tests/unit/app/test_main_wiring.py::TestRoleEffectPortsGate` (the three
  ports install only inside the test-guild gate block, each with the allow-list).

## Slice base

Stacks on PR #263 (`claude/live-moderation-adapter`, head `0594579`) — SLICE 2
edits the same `sb/app/main.py` step-10a region SLICE 1 installs moderation in,
so it bases off #263's head branch rather than main (a separate main branch
would conflict). Reuses `GuildNotAllowedError` from #263's
`moderation_actions.py`.

## Evidence

- `python3 -m pytest` — [[fill on green]]
- `python3 bootstrap.py check --strict` — [[fill on green]]
- No golden-parity file touched; no channel/proof_channel port touched.

## 💡 Session idea

[[fill at close]]
