# 2026-07-12 — live channel EFFECT adapters (SLICE 3 / live-guild-effects)

> **Status:** `complete`

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

- `sb/adapters/discord/channel_actions.py` (new) — the adapters on the reused
  `_GuildAllowList` base (via a slim `_ChannelGuildAllowList` that overrides
  `_require_discord` to guard THIS module's import-guarded `discord`), the hard
  test-guild allow-list raised BEFORE any Discord call:
  - `DiscordChannelStateActions` (`ChannelStateActions`, channel domain):
    - `set_slowmode` → `channel.edit(slowmode_delay=seconds, reason=)` (wire
      `edit_channel` / `rate_limit_per_user`). CHANNEL-scoped (cache fence).
    - `set_overwrite` → resolve the target off the fenced channel's guild cache
      (`target_type` 0 = role → `get_role`, 1 = member → `get_member`; a loud
      raise on unresolvable, the delete_role posture) →
      `channel.set_permissions(target, overwrite=discord.PermissionOverwrite.
      from_pair(discord.Permissions(allow), discord.Permissions(deny)),
      reason=)` (wire `edit_channel_permissions`). CHANNEL-scoped.
    - `create_text_channel` → allow-list-direct guild → map the
      `ChannelOverwrite` tuple to `{target: PermissionOverwrite}`, resolve the
      category from `parent_id` (or None) → `guild.create_text_channel(name=,
      overwrites=, category=, reason=)` → `.id`. ALWAYS creates
      (get-before-create is DOMAIN logic, D-0077). GUILD-scoped.
    - `delete_channel` → CHANNEL-scoped fence → `channel.delete(reason=)`
      swallowing `discord.NotFound` as SUCCESS (already-gone is the goal
      state, D-0077).
    - `create_invite` → CHANNEL-scoped fence → `channel.create_invite(max_age=,
      max_uses=, temporary=, unique=, reason=)` → `.url`. (The parity twin
      reproduces the capture-world `CaptureInviteParseError` artifact; a LIVE
      adapter simply returns the url, does not raise.)
  - `DiscordProofChannelActions` (proof_channel's OWN `ChannelPermActions` — a
    SEPARATE port, kept a DISTINCT adapter class): `lock_channel_for_winner`
    (hide @everyone / grant winner view+send / keep bot visible) and
    `unlock_channel` (everyone view-yes-send-no / bot visible), each the
    shipped `proof_channel_cog` `_lock_for_winner` / `_unlock` bulk
    `channel.edit(overwrites=…)` verbatim. Both carry `guild_id` →
    allow-list-direct.
  - `DiscordChannelLookup` (`install_channel_lookup` name leg) — the
    TextChannelConverter gateway-cache name resolve, test-guild-scoped (any
    other guild → None; a read never mutates).
- `sb/app/main.py` step 10a — under the SAME `moderation_test_guild(cfg)` gate,
  adjacent to moderation + role: `install_channel_actions`,
  `install_channel_lookup`, and proof_channel's `install_channel_actions`
  (imported `as install_proof_channel_actions` to avoid the name clash with the
  channel domain's identically-named installer), each constructed with
  `allowed_guild_id=test_guild_id`. Prod stays un-armed (no test-guild id) —
  the owner's CUT-3 gate.
- Tests: `tests/unit/band6/test_live_channel_adapters.py` (exact discord.py
  call + kwargs per ChannelStateActions method; delete swallows NotFound as
  success; create_text_channel maps overwrites + resolves category + returns
  the new id; the allow-list refusing a non-allowed guild AND a wrong-guild AND
  an unresolvable-guild channel — via a fake `discord` module so it runs in the
  discord-absent CI container); `tests/unit/band5/
  test_live_proof_channel_adapter.py` (lock/unlock overwrite sets verbatim; the
  allow-list refusing a non-allowed guild); `tests/unit/app/test_main_wiring.py
  ::TestChannelEffectPortsGate` (all three installs sit inside the test-guild
  gate block, each with the allow-list).

## Slice base

Stacks on PR #278 (`claude/live-role-adapters`, head `bae724a`) — SLICE 3 edits
the same `sb/app/main.py` step-10a region SLICE 1/2 install moderation + role
in, so it bases off #278's head branch rather than main (a separate main branch
would conflict). #278 in turn stacks on #263 (`claude/live-moderation-adapter`).
Reuses `GuildNotAllowedError` from #263's `moderation_actions.py` and the
`_GuildAllowList` base from #278's `role_actions.py`.

## Evidence

- `python3 -m pytest tests/` — **1767 passed, 8 skipped** (+17: 12 channel
  contract tests + 3 proof_channel contract tests + 2 wiring assertions; the 8
  skips are the pre-existing suite skips, unchanged).
- `python3 bootstrap.py check --strict` — the ONLY exit-affecting finding is
  the born-red HOLD on this card (by design; green on the flip to complete).
  Advisories (never exit-affecting): one pre-existing `owner-action-risk-class`
  on `control/status.md` (not in this diff) and a benign `claims-duplicate` —
  this claim, #278's and #263's all name `tests/unit/app/` (a legitimate
  three-slice stack, not a competing claim; each slice's claim is deleted at
  its own close-out).
- No golden-parity file touched; `import discord` stays inside
  `sb/adapters/discord/`.
- discord.py pinned at 2.7.1 (requirements.lock) — the mapped verbs
  (`channel.edit(slowmode_delay=)`, `channel.set_permissions` /
  `PermissionOverwrite.from_pair`, `guild.create_text_channel`,
  `channel.delete` / `discord.NotFound`, `channel.create_invite`,
  `channel.edit(overwrites=)`) match the 2.x API.

## Review fixes (post-review, substitute for rate-limited Codex)

Base merged forward first (`git merge origin/claude/live-role-adapters`, clean —
no conflict; brings slice-2's `GuildNotAllowedError(effect=…)` param + fixes).
Then 4 review findings, all in `sb/adapters/discord/channel_actions.py`:

1. **P2 — untranslated Discord exceptions bypassed the shipped error copy.**
   `set_slowmode` / `set_overwrite` raised raw `discord.HTTPException`, but the
   channel handlers catch only `RuntimeError`, so a live failure escaped to the
   generic envelope. FIX (the role slice's translate-in-adapter posture): wrap
   both Discord calls to translate `discord.HTTPException` → `RuntimeError`
   (`_as_runtime` helper), so the shipped `❌ Could not …: {exc}` branch renders.
   `create_invite` / `delete_channel` left as-is (already fine).
2. **P2 — `_overwrite_target` member branch was cache-only.** A delegated/
   uncached member would break `/setup-advanced` create. FIX: `guild.get_member`
   → `await guild.fetch_member` fallback (the proof adapter's `_member` posture,
   safely post-fence); `_overwrite_target` is now async, awaited at both sites.
3. **P3 — refusals inherited the "moderation/role" wording.** FIX: a per-class
   `_effect` (`"channel"` / `"proof_channel"`) overriding the base `_guild` +
   the channel fence, so a refusal reads "channel effect REFUSED" /
   "proof_channel effect REFUSED".
4. **P3 — `DiscordChannelLookup` guild fence had no test.** FIX: added a test
   asserting a non-allowed guild_id returns None WITHOUT touching
   `bot.get_guild` (plus a positive name-resolve test).

Tests extended in the two contract files + a handler-level end-to-end test
(install the live adapter with a raising fake channel, drive the real
`channel.slowmode` / `channel.lock` handler, assert the `❌ Could not …` copy —
not the generic envelope). Re-green: `pytest tests/` **1779 passed, 8 skipped**;
`bootstrap check --strict` all checks passed.

## Oracle used

`menno420/superbot` read-only for ONE genuinely-ambiguous mapping: the
proof_channel `ChannelPermActions` port declares only `lock_channel_for_winner`
/ `unlock_channel` with NO parity twin, NO golden, and no discord detail in the
domain, so the exact overwrite SET the live lock/unlock must write is not
recoverable from superbot-next alone. `disbot/cogs/proof_channel_cog.py`
`_lock_for_winner` / `_unlock` (lines 200-240) pin it: lock = `{default_role:
view_channel False, winner: view+send True, guild.me: view True}`, unlock =
`{default_role: view True/send False, guild.me: view True}`, both a bulk
`channel.edit(overwrites=…)`. Everything else (ChannelStateActions verbs, the
NotFound-as-success + get-before-create-is-domain contracts) was fully pinned
by the channel service docstring + the `ParityChannelStateActions` twin —
no oracle needed.

## 💡 Session idea

SLICE 2's card floated `_install_live_effect_ports(bot, cfg, test_guild_id)` to
collapse the now-three install blocks (moderation + role + channel) under one
gate into a single named call. With SLICE 3 landed, that block is ~55 lines of
install soup under one `if test_guild_id is not None:` guard — the refactor is
now due at its FINAL shape: a `sb/app/live_effects.py` helper owning ALL the
gated installs (the four seams' `install_*` calls + their adapter constructions
+ the one ARMED log line), so `run_app` names ONE call and the gate stays a
single audited line. Deferred out of this slice deliberately: it is a pure
composition-root refactor with no behavior change, so it should land as its own
reviewable diff (and after the three stacked PRs merge to main, so it rebases
once, not three times).

## ⟲ Previous-session review

SLICE 2's card set the template this slice followed almost verbatim and, acting
on its own **system-improvement** note, tagged each unarmed port with its
allow-list SHAPE — which paid off immediately: ChannelStateActions turned out
to be MIXED (four channel-scoped methods needing the cache-only fence,
`create_text_channel` guild-scoped needing the direct compare), and the SHAPE
tag made that a lookup, not a rediscovery. The one genuinely-new decision this
slice owned: `set_overwrite` / `create_text_channel` need a REAL Role/Member
object (discord.py's `set_permissions` / `create_text_channel` reject a bare
`discord.Object` — it carries no role-vs-member type), so the overwrite target
is resolved off the fenced guild cache with a loud raise on unresolvable —
unlike SLICE 2's role methods which pass a bare snowflake. What SLICE 2
under-specified for a successor: it did not flag that a port method whose name
COLLIDES across two domains' service modules (`install_channel_actions` exists
in BOTH `channel.service` and `proof_channel.service`) forces an import alias at
the composition root. **System improvement:** a live-effect card's
successor-naming line should flag installer-name COLLISIONS across the ports a
slice arms (next to the allow-list SHAPE tag), so the next builder reaches for
the `as`-alias by design rather than discovering the clash at wire time.
