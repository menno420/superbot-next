# 2026-07-12 — live-adapter landing: the #263→#278→#283 stack merged + the channel/read-seam fix pass

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · merge-train + fix pass (live-guild-effects landing)

## What I'm about to do

Take over the PARKED live-guild-effects stack — three review-hardened PRs
sitting stacked while main advanced (#293's runtime-smoke gate landed under
them) — and LAND it: rebase each branch forward, drive 6/6 required checks
green, squash-merge in order (#263 moderation → #278 role → #283 channel),
and ship a pre-merge FIX PASS on #283 for the gaps a fresh audit verified:

- **(A)** `DiscordChannelStateActions` implemented only 5 of the 9
  `ChannelStateActions` protocol methods (sb/domain/channel/service.py) —
  `rename_channel` / `set_topic` / `move_channel` / `clone_channel` were
  MISSING, so a live `!rename`/`!topic`/`!move`/`!clone` raised
  AttributeError past the handlers' `except RuntimeError` (a dispatcher
  failure, not the shipped `❌ Could not …` copy).
- **(B)** the `ChannelDirectory` READ seam was NOT armed — every
  directory-led channel lane (`!del` `!permissions` `!rename` `!topic`
  `!move` `!clone` `!channelinfo` `!list` `!bulkdelete` `!create`) refused
  at `_NoDirectory` BEFORE reaching the armed mutation port (the exact
  guild-view lesson Codex caught on #278, one seam over). Same family:
  utility's `install_guild_directory` (!serverinfo/!serverstats + the
  member cards) and diagnostic's `install_ws_latency_reader` (!latency)
  were unarmed — the ledgered §4.1 not-armed gap family.
- **(C)** the runbook hardcoded a RETIRED test guild (`MineSnakeBotTest`
  1350952413737259151) where the live allow-list is env-derived from
  `SB_APPCMD_SYNC_GUILD_ID` and the verified guild is `Superbot Admin`
  1522099141671653417 (.sessions/2026-07-10-band5-live-drive.md).
- **(D)** four Codex review threads on #278 were FIXED in the branch
  (commit "fix(role): address Codex review …") but never resolved on GitHub.
- **(E)** error-translation inconsistency in channel_actions.py —
  `create_text_channel` / `create_invite` / non-NotFound `delete_channel`
  failures escaped as raw `discord.HTTPException` where the slowmode/
  overwrite legs translate to RuntimeError.

NOT in scope: booting the bot / driving live Discord effects — the live-drive
proof is the named immediate next step, a separate session with the operator
runbook.

## Delivered

**Merge train (squash, repo precedent #290/#293; forward-only main):**

- #263 (moderation, SLICE 1) rebased onto main `3cc0426` (one telemetry
  append-conflict, both sides kept) → 11/12 checks green (`report`
  red-by-design) → merged `248d068`.
- #278 (role, SLICE 2) retargeted to main, rebased (role-only commits via
  `--onto`) → all green → merged `b7a0513`. The 4 unresolved Codex threads
  resolved via the API (all four fixed by the branch's Codex-review commit):
  NotFound→LookupError translation, guild-view wiring, partial-message
  react, role refusal copy.
- #283 (channel, SLICE 3 + this fix pass) retargeted to main, rebased,
  fix-pass commits added, merged — main history now shows all three.

**Fix pass on #283 (this session's code):**

- `sb/adapters/discord/channel_actions.py`:
  - the four missing protocol methods, the file's existing shape (cache
    fence → discord.py call → `_as_runtime` translation): `rename_channel` /
    `set_topic` (channel-edit PATCH; a topic CLEAR rides as explicit None),
    `move_channel` (edit `category=` resolved off the fenced cache guild;
    loud RuntimeError on an unresolvable category), `clone_channel`
    (guild-scoped allow-list direct; `channel.clone(name=…)` off the cached
    source — discord.py replicates the source option set, the sweep_clone
    wire shape).
  - `DiscordChannelDirectory` (new) — the live `ChannelDirectory` over the
    gateway cache (the parity `_WorldChannelDirectory` twin): list_channels
    in presentation order (sorted `(position, id)`), get_channel, list_roles;
    full `ChannelSnapshot` field mapping incl. the overwrite tuple (0=role /
    1=member typing via `isinstance(target, discord.Role)`). READ posture:
    a non-allowed or uncached guild reads as EMPTY (soft fence BEFORE
    `bot.get_guild`) — never a raise; the handlers keep their own not-found
    copy.
  - (E) `create_text_channel` / `delete_channel` (non-NotFound) /
    `create_invite` now translate `discord.HTTPException` → RuntimeError
    like their siblings.
- `sb/adapters/discord/utility_reads.py` (new) — `DiscordGuildDirectory`,
  the live utility `GuildDirectory` (the parity `_WorldGuildDirectory`
  twin): `guild_info` = the shipped cache census (bots per-member flag,
  online = `status != offline` — presence-intent dependent, 0 without it,
  the same degraded-but-truthful read the capture pinned; roles/channel
  counts), `member_info` = cache-first + ONE REST `fetch_member` fallback.
  Fence: a non-allowed/uncached guild raises `GuildDirectoryNotInstalled` —
  the polite NOT-ARMED refusal every consuming surface already renders, so
  non-test guilds keep the pre-arm behavior verbatim.
- `sb/app/main.py` step 10a — `install_channel_directory`,
  `install_guild_directory`, `install_ws_latency_reader(lambda:
  bot.latency)` armed INSIDE the same `if test_guild_id is not None:` block
  (the double gate is UNTOUCHED: `SB_DATA_PLANE=="test"` AND explicit
  `SB_APPCMD_SYNC_GUILD_ID`, per-call allow-list — CUT-1 posture preserved,
  prod root stays unarmed).
- `tests/unit/band6/test_live_channel_adapters.py` — +17 tests (the four
  methods: happy path, allow-list refusal, loud unresolvable-target,
  HTTP→RuntimeError translation; the (E) translation trio; the directory:
  presentation order, field mapping, soft fence before the cache read,
  uncached-guild empties).
- `tests/unit/band6/test_live_utility_reads.py` (new) — 5 tests (census
  mapping, member card cache hit + single-fetch fallback, the NOT-ARMED
  fence both ways).
- `tests/unit/app/test_main_wiring.py` — the exact-string wiring asserts
  extended for the three new installs (TestUtilityReadSeamsGate new).
- `docs/operations/live-drive-guild-effects.md` — (C) fixed: allow-list
  stated as ENV-DERIVED from `SB_APPCMD_SYNC_GUILD_ID`, current verified
  value `Superbot Admin` 1522099141671653417, `MineSnakeBotTest` marked
  retired; the armed-boot log-line roster extended with the new read seams.

## What is now LIVE-armed vs still refusal-stubbed (test plane + test guild only)

Armed (post-merge, pending live-drive proof): all moderation effects
(kick/ban/timeout/unban + readiness), all role effects (add/remove/create/
delete role, reaction-role, guild view), ALL NINE channel-state methods +
channel directory reads + name lookup + proof-channel prize lock/unlock +
the utility guild/member census + ws latency.

Still refusal-stubbed (named, unchanged): `install_bot_identity` (!botinfo),
`install_gateway_probe` (utility's ms probe), `install_message_purger`
(!clear) — same §4.1 family, clean follow-up candidates; the diagnostic
process views; D-0043/D-0047 successor ports.

## 💡 Session idea

The (B) gap repeated a pattern Codex already caught once on #278 (mutation
ports armed, read seam forgotten — guild view then, channel directory now).
A cheap structural guard: a wiring-time invariant in `check_runtime_smoke.py`
(or a unit test) that walks each domain service module for `install_*` seams
and asserts the composition root's gated block installs EVERY seam the
domain's handlers actually call — so "armed the writes, forgot the reads"
reds a gate instead of surfacing as live refusals. The still-stubbed utility
seams (`install_bot_identity`, `install_gateway_probe`,
`install_message_purger`) are the natural first fixture set.

## ⟲ Previous-session review

#293's card correction CONFIRMED and carried: the "11 known-red integration
tests under local Postgres" note from #290's card was local provisioning
state, not a stable fact — this session's provisioned cluster runs the full
suite green (counts in the PR body). Do not copy the known-red entry
forward.

## Next step (immediate)

LIVE-DRIVE PROOF — a human/operator session against the test plane + guild
1522099141671653417 per docs/operations/live-drive-guild-effects.md,
exercising each armed lane and filing findings. Explicitly NOT done here.
