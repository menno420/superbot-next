# 2026-07-12 — live role EFFECT adapters (SLICE 2 / live-guild-effects)

> **Status:** `complete`

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

- `python3 -m pytest tests/` — **1750 passed, 8 skipped** (+12: 9 role
  contract tests + 3 wiring assertions; the 8 skips are the pre-existing
  suite skips, unchanged).
- `python3 bootstrap.py check --strict` — the ONLY exit-affecting finding is
  the born-red HOLD on this card (by design; green on the flip to complete).
  Advisories (never exit-affecting): one pre-existing
  `owner-action-risk-class` on `control/status.md` (not in this diff) and a
  benign `claims-duplicate` — this claim and #263's both name
  `tests/unit/app/` (a legitimate stack, not a competing claim; #263's claim
  is deleted at its own close-out).
- No golden-parity file touched; no channel/proof_channel port touched.
- discord.py pinned at 2.7.1 (requirements.lock) — the mapped verbs
  (`member.add_roles`/`remove_roles`, `guild.create_role` with `colour=`,
  `role.delete`, `channel.fetch_message`, `message.add_reaction`) match the
  2.x API.

## 💡 Session idea

SLICE 1's card floated `arm_test_plane_effect(cfg, *, install)` to collapse the
three copy-pasted `SB_DATA_PLANE=="test"` reads into one audited switch. SLICE 2
did NOT extract it (the moderation + role installs now share ONE
`if test_guild_id is not None:` block, so there is only one gate read, not
three) — but SLICE 3 (channel/proof_channel) will add a fourth install to the
same block. When it does, the block will be ~40 lines of install soup under one
gate; the better refactor is a small `_install_live_effect_ports(bot, cfg,
test_guild_id)` helper that owns ALL the gated installs, so `run_app` names one
call and the gate stays a single audited line. Deferred to slice 3 so the
refactor lands with its final shape, not mid-stack.

## ⟲ Previous-session review

SLICE 1's card (live-moderation-adapter, D-0049) set the template this slice
followed almost verbatim: the `*, allowed_guild_id` constructor, the
`GuildNotAllowedError`-before-any-Discord-call fence, the import-guarded
`discord`, and the `moderation_test_guild(cfg)` double gate made the port-home,
the wire-shape, and the safety-fence questions a lookup, not a debate — strong
precedent hygiene. It even pre-named the `arm_test_plane_effect` helper this
slice weighed (and deferred, above). What it under-specified for a successor:
it did not flag that the role MessageOps port is CHANNEL-scoped, not
guild-scoped — so the allow-list can't be a straight `guild_id` compare, it has
to resolve the guild from the channel's CACHE (never a REST fetch, or the
resolve itself would touch a possibly-prod channel before the fence). That was
the one genuinely new design decision this slice owned. **System improvement:**
a live-effect card's successor-naming line should tag each unarmed port with its
allow-list SHAPE (`guild-scoped` / `channel-scoped` / `member-scoped`) next to
the install-feasibility tag, so the next slice knows whether the safety fence is
a direct compare or a cache-resolve before it reads the port protocol.
