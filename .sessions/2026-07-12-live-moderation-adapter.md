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
  - `ban_member` → `guild.ban(discord.Object(user_id), reason=reason,
    delete_message_seconds=days*86400)` — ALWAYS pins the kwarg (0 on the
    no-purge path). discord.py 2.x fills an OMITTED kwarg with 86400 (a
    full day), so "no purge" must be pinned to 0, never omitted (Codex P1).
  - `unban_member` → `guild.unban(discord.Object(user_id), reason=reason)`
    DIRECTLY — the DOMAIN (`ops.py`) already `fetch_user()`s the banned id
    first (the oracle's get_user→unban order), so the adapter does NOT
    re-fetch (one REST round-trip, not two — Codex P2).
  - `fetch_user` → `await bot.fetch_user(user_id)`;
    `dm_member` → fetch user, `await user.send(text)`.
  - HARD test-guild allow-list: `DiscordModerationActions(bot, *,
    allowed_guild_id)` refuses every guild-scoped effect
    (`GuildNotAllowedError`, raised BEFORE any Discord call) when
    `guild_id != allowed_guild_id` — the bot holds the PROD gateway token,
    so `SB_DATA_PLANE=test` alone (DB protection) could still mutate a real
    guild's members; the allow-list closes that (Codex P1 safety).
  - `DiscordModerationReadinessReader` — reads `guild.me` per the oracle
    `evaluate_moderation_readiness` contract byte-for-byte (admin implies
    every capability; `top_role_is_lowest == top_role.position == 0`);
    returns None when the guild/bot-member is uncached (the documented
    field-drop degrade, never a fabricated readiness).
- `sb/app/main.py` — `moderation_test_guild(cfg)` (returns the test-guild
  id via `guild_sync_target` → BOTH `SB_DATA_PLANE == "test"` AND an
  explicit `SB_APPCMD_SYNC_GUILD_ID`; None otherwise) + step 10a: under
  the gate, `install_moderation_actions(DiscordModerationActions(bot,
  allowed_guild_id=test_guild_id))` +
  `install_moderation_readiness(DiscordModerationReadinessReader(bot))`.
  Prod stays un-armed (no test-guild id) — commented as the owner's CUT-3
  gate. Reusing the app-command sync guild keeps ONE test-guild identity
  for every test-plane live effect.
- Tests: `tests/unit/band2/test_live_moderation_adapter.py` (exact
  discord.py call + kwargs per port method incl. ban-pins-0, unban-single-
  call-no-refetch, and the allow-list refusing every non-allowed guild —
  via a fake `discord` module so it runs in the discord-absent CI
  container) +
  `tests/unit/app/test_main_wiring.py::TestModerationTestGuildGate` (the
  gate yields the guild only on the test plane + explicit id; the install
  is guarded by it and passes the allow-list to the adapter).

## Codex review round (ORDER 010)

Codex left three valid findings on head `b6a06a9`; all three fixed here:
(1) P1 — `ban_member` now ALWAYS passes `delete_message_seconds` (0 on
no-purge), because discord.py 2.x defaults an omitted kwarg to a full-day
purge. (2) P2 — `unban_member` no longer re-fetches (the domain owns the
pre-fetch). (3) P1 SAFETY — the hard test-guild allow-list above, so a
test-plane process on the prod token can never action a prod-guild member.
The parity RECORDING twin (`ParityModerationActions`, transport.py) was
deliberately left unchanged — its omit-when-days==0 is a correct
wire-recording shape, distinct from the live effect.

## Evidence

- `python3 -m pytest tests/` — **1738 passed, 8 skipped** (the 8 are
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

