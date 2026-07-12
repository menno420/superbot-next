# LIVE-DRIVE RUNBOOK — the moderation / role / channel effect adapters

> **Status:** `reference` — the SLICE 4 live-drive ops runbook for the live guild
> effect adapters. Human-operator procedure only; there is NO automated CI
> live-drive (no gateway token in CI). Wiring of record: `sb/app/main.py` install
> block (`:409-501`) + adapters `sb/adapters/discord/{moderation,role,channel}_actions.py`.
> Line refs cite the `claude/live-channel-adapters` tip; re-verify if the lane advances.

**Lane:** `live-guild-effects` (SLICE 4 deliverable) · **Repo:** `menno420/superbot-next`
**Base:** `claude/live-channel-adapters` tip (SLICE 1 moderation + SLICE 2 role + SLICE 3 channel stacked; role/moderation Codex review-fixes merged forward)
**Test guild:** `MineSnakeBotTest` · id `1350952413737259151`
**Audience:** a human operator with the test bot's gateway token and a reachable Postgres. This is NOT a CI job.

---

## 0. TL;DR — verdict up front

- **Automated CI live-drive: NOT POSSIBLE.** No live Discord gateway token and none of the owner-provisioned prod/effect secrets exist in CI. The only Discord token literal anywhere in `.github/workflows` is the string `"verify-boot-placeholder"`, explicitly annotated *"never used: no gateway is built"* (`.github/workflows/restore-verify.yml:123`). CI cannot connect a gateway, therefore CI cannot drive a single live guild effect. Evidence in §1.
- **This document is a HUMAN-OPERATOR procedure** run against the test plane + the `MineSnakeBotTest` guild only.
- **The production root stays UNARMED throughout.** The effect ports install *only* under the test double-gate; a prod-plane boot (even attested) leaves every effect port un-installed by construction (§5).

---

## 1. Preconditions & honest scope

### 1.1 Why an automated live-drive is impossible (evidence)

A live guild effect requires the bot to be connected to the Discord gateway. `run_app()` connects with a real token at `sb/app/main.py:535-536`:

```python
gateway_task = await gw.connect_gateway(bot, cfg.DISCORD_BOT_TOKEN_PRODUCTION)
```

CI has no such token. Verified by grepping the whole `.github/` tree:

- The **only** `secrets.*` reference in any workflow is `secrets.DATABASE_PUBLIC_URL` (`.github/workflows/backup-db.yml:62,84`) — a backup-restore DSN, owner-gated behind `BACKUP_ENABLED`, never a gateway token.
- The **only** occurrence of `DISCORD_BOT_TOKEN_PRODUCTION` in any workflow is a hard-coded placeholder:
  `.github/workflows/restore-verify.yml:123` → `DISCORD_BOT_TOKEN_PRODUCTION: "verify-boot-placeholder"  # never used: no gateway is built`.
- Every workflow that boots the app does so with `SB_VERIFY_BOOT: "true"` + `SB_DATA_PLANE: "test"` (`restore-verify.yml:119-120`; also `golden-parity.yml:53-54,91-92`, `named-gates.yml:120-121`). `SB_VERIFY_BOOT=true` takes the side-effect-free branch at `sb/app/main.py:224-229` — it **returns before any gateway is built** (the whole step-10/11 block never runs).
- No `SB_APPCMD_SYNC_GUILD_ID`, no `SB_PROD_ATTEST`, no live `DATABASE_URL` is present as a CI secret or variable.

The owner-provisioned credential set that a real drive would need lives in `sb/spec/credentials.py::CREDENTIAL_REGISTRY` and is provisioned by the owner into the worker env / GitHub secrets, **not** exposed to PR/CI runs:

| Credential (registry name) | Env var | Store | BlastTier | In CI? |
|---|---|---|---|---|
| `discord_prod_bot_token` | `DISCORD_BOT_TOKEN_PRODUCTION` | `WORKER_ENV` | BOT_PRESENCE | ❌ |
| `discord_test_bot_token` | (container env) | `AGENT_CONTAINER_ENV` | TEST_ONLY | ❌ |
| `prod_dsn` | `DATABASE_URL` | `WORKER_ENV` | PROD_DATA | ❌ |
| `prod_attest_token` | `SB_PROD_ATTEST` | `WORKER_ENV` | PROD_DATA | ❌ |
| `database_public_url` | `DATABASE_PUBLIC_URL` | `GITHUB_ACTIONS_SECRET` | PROD_DATA | ✅ (backup only, `BACKUP_ENABLED`-gated) |
| `anthropic_api_key` | `ANTHROPIC_API_KEY` | `WORKER_ENV` | SPEND | ❌ |

(`sb/spec/credentials.py:136-181`.) The program review states the same posture: *"Live effect adapters unarmed for moderation, role grants, and channel permissions … verified in replay, not against live Discord"* (`docs/review/program-review-2026-07-12.md:258-260`), and that a prod boot expects `DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`, `SB_DATA_PLANE=prod`, and `SB_PROD_ATTEST`, *"and all live evidence to date is `SB_DATA_PLANE=test`"* (`program-review-2026-07-12.md:266-269`).

**Conclusion:** the effect adapters are a *replay-verified* subsystem. Live evidence can only be produced by a human operator who holds the test bot token and stands up a Postgres. There is no automated path from CI or the harness.

### 1.2 Operator preconditions

Before you begin you must have, on the machine that will run the bot:

1. The **test bot's** gateway token (the `MineSnakeBotTest` application). It is supplied through the env var `DISCORD_BOT_TOKEN_PRODUCTION` — that is the *only* token field the config declares (`sb/spec/config.py:124`); on the test plane you put the **test** bot's token value in it. The bot must be a member of `MineSnakeBotTest` (id `1350952413737259151`) with Manage Roles / Manage Channels / Kick / Ban / Moderate Members as needed, and a role positioned above the members/roles it will act on.
2. A reachable Postgres and its DSN in `DATABASE_URL`.
3. The `MineSnakeBotTest` guild, a throwaway member to act on, and a throwaway role/channel to mutate.

### 1.3 Scope guarantees

- Every mutation is fenced to guild `1350952413737259151` by a hard per-call allow-list (§4). A test-plane process still holds a real gateway token, so this fence is what stops a stray `!ban` from touching any other guild.
- The production root stays **UNARMED**: on the prod plane the effect ports never install (§5). Nothing in this procedure arms prod.

---

## 2. Arm on the test plane + the test guild

### 2.1 The double gate (both must be true)

The install block is gated at `sb/app/main.py:409-410`:

```python
test_guild_id = moderation_test_guild(cfg)
if test_guild_id is not None:
    ...   # installs moderation + role + channel effect ports
```

`moderation_test_guild(cfg)` returns `guild_sync_target(cfg)` (`sb/app/main.py:127-138`), and `guild_sync_target` (`sb/app/main.py:112-124`) returns non-`None` **only when BOTH**:

- `SB_APPCMD_SYNC_GUILD_ID` is set (a guild id), **AND**
- `SB_DATA_PLANE == "test"` (else it logs *"SB_APPCMD_SYNC_GUILD_ID set but SB_DATA_PLANE != test — guild sync NOT armed"* and returns `None`, `main.py:120-123`).

So the two env vars combine: `SB_DATA_PLANE=test` protects the DB (the 4th rail), and `SB_APPCMD_SYNC_GUILD_ID` names the single guild handed to every adapter as its hard allow-list. Reusing the app-command sync guild id keeps **one** test-guild identity for every test-plane live effect (`main.py:137`).

### 2.2 Exact env to arm each adapter

All three domains (moderation, role, channel) arm off the **same** `if test_guild_id is not None:` block, so this one env set arms all of them:

```bash
# --- the two gates that arm the effect ports ---
export SB_DATA_PLANE=test
export SB_APPCMD_SYNC_GUILD_ID=1350952413737259151   # MineSnakeBotTest

# --- the gateway token (test bot's token in the PRODUCTION-named field) ---
export DISCORD_BOT_TOKEN_PRODUCTION='<the MineSnakeBotTest bot gateway token>'

# --- a reachable Postgres ---
export DATABASE_URL='postgresql://<user>:<pw>@<host>:5432/<db>'
# optional test-plane DSN host allow-list; unset/empty => open mode (any host),
# the connected host is logged once (sb/spec/config.py:213-217)
# export SB_TEST_DB_HOSTS=localhost

# --- do NOT set SB_VERIFY_BOOT (it would take the no-gateway branch, main.py:224) ---
# --- do NOT set SB_DATA_PLANE=prod and do NOT set SB_PROD_ATTEST (that path never arms effects) ---
```

Notes that decide whether the block runs:
- **Both** `SB_DATA_PLANE=test` and `SB_APPCMD_SYNC_GUILD_ID=1350952413737259151` are mandatory. Drop either and `test_guild_id` is `None` and **no** effect port installs.
- To exercise prefix commands (`!ban`, `!slowmode`, …) the message feed must arm, which needs the `message_content` intent approved: set `SB_INTENT_MSGCONTENT_OK=true` (`sb/spec/config.py:222-223`, intent contract `:256-260`). Without it the `prefix` class degrades and the message feed is **not** armed (`main.py:596-607`) — you would then have to drive effects through slash/interaction surfaces instead.

### 2.3 Boot command

```bash
python3 -m sb          # == python3 -m sb.app.main → cli() → run_app()  (main.py:734-743)
```

### 2.4 Confirm the adapters installed

The gate emits one INFO log line per domain. On a correctly-armed boot you MUST see all three (`%d` = `1350952413737259151`):

- Moderation — `main.py:423-425`:
  `moderation guild-action port ARMED (test plane, guild 1350952413737259151 ONLY): live kick/ban/timeout/unban + guild.me readiness`
- Role — `main.py:463-466`:
  `role EFFECT ports ARMED (test plane, guild 1350952413737259151 ONLY): live add/remove role + create/delete role + reaction-role fetch_message/add_reaction + the gateway-cache guild view`
- Channel — `main.py:498-501`:
  `channel EFFECT ports ARMED (test plane, guild 1350952413737259151 ONLY): live slowmode/overwrite/create/delete/invite + channel-name lookup + proof-channel prize lock/unlock`

If you see **none** of these lines, `test_guild_id` was `None` — re-check §2.2 (usually a missing `SB_DATA_PLANE=test` or a missing/zero `SB_APPCMD_SYNC_GUILD_ID`); look for the `main.py:121-122` warning. Also confirm boot reached `RUNNING` (`main.py:541`) and the audit canary line `boot complete: RUNNING (canary enqueued …)` (`main.py:665`) — the canary proves the audit→outbox→bus relay is live so your effect audit rows will actually be delivered.

---

## 3. Drive each effect

For every effect below: run the command in a `MineSnakeBotTest` channel, observe the Discord state change, read the ack the bot posts, then verify the audit row (§4). All command names are the shipped prefix verbs; ack copy is pinned to the shipped oracle (superbot `disbot/`), so the strings below are the live acks the goldens hold.

### 3.1 Moderation (`subsystem = "moderation"`, adapter `sb/adapters/discord/moderation_actions.py`)

| Command | Discord state change | Expected ack copy | Expected audit row (`subsystem` / `mutation_type` / `target`) |
|---|---|---|---|
| `!ban @user <reason>` | Member banned; messages purged only if a purge window is configured (no-purge is pinned to `delete_message_seconds=0`, never omitted — `moderation_actions.py:114-127`) | `🚫 <@user> banned. Reason: <reason>` (`ops.py:297`) | `moderation` / `member_banned` / `moderation.ban` (`ops.py:499`, op `moderation.ban`) |
| `!kick @user <reason>` | Member kicked (`guild.kick(discord.Object(id))`, `moderation_actions.py:108-112`) | `👢 <@user> kicked. Reason: <reason>` (`ops.py:291`) | `moderation` / `member_kicked` / `moderation.kick` (`ops.py:489`) |
| `!timeout @user <minutes> <reason>` | Member timed out until `utcnow()+minutes` (`moderation_actions.py:99-106`) | `⏳ <@user> timed out for <minutes> minutes …` (`ops.py:200,265`) | `moderation` / `member_timed_out` / `moderation.timeout` (op `TIMEOUT`, `ops.py:482`) |
| `!unban <user_id>` | Ban lifted (`guild.unban(discord.Object(id))`, single-fetch; `moderation_actions.py:129-139`) | `✅ <@user> unbanned.` (`ops.py:307`) | `moderation` / `member_unbanned` / `moderation.unban` (`ops.py:502`) |

Sequencing note: `timeout` has **no** effect leg — its record leg runs the oracle's call-Discord-first order (`ops.py:482-487`), so a refused timeout aborts the txn and writes **no** row/event. `kick`/`ban`/`unban` carry compensators that un-write the DB row if Discord refuses (`ops.py:490-503`). Every moderation op also emits the best-effort `moderation.action_taken` event (`_EMITS`, `ops.py:436-437`).

### 3.2 Role (`subsystem = "role"` for K7 ops; adapters `sb/adapters/discord/role_actions.py`)

| Command | Discord state change | Expected ack copy | Expected audit row |
|---|---|---|---|
| `!createrole <name>` | Role created (`guild.create_role`, `role_actions.py:119-129`); returns the new role id | `✅ Created role **<name>**.` (`handlers.py:465`) | `role` / — (provisioning EFFECT leg; the create is a live effect, the DB record is the calling op's row — see note) |
| `!deleterole <name>` | Cached role deleted (`role.delete`, `role_actions.py:131-142`) | `🗑️ Deleted role **<name>**.` (`handlers.py:512`) | `role` (delete EFFECT via provisioning port) |
| `!temprole @user <role> <duration>` (assign, live add-role) | Role added to member (`member.add_roles(discord.Object(id))`, `role_actions.py:96-102`) via the `grant_temp_role` op's EFFECT leg | `⏳ <@user> holds <@&role> until …` (`handlers.py:317`) | `role` / `grant_temp_role` / `role.grant_temp_role` (`ops.py:363`, op `GRANT_TEMP_ROLE`, EFFECT leg `role.apply_grant_temp` + compensator) |
| `!reactroles <message_id> <emoji> <@role>` | Reaction added to the target message (`fetch_message` then `get_partial_message(...).add_reaction`, `role_actions.py:170-195`); binding stored | `✅ Reaction role set: reacting with <emoji> assigns **<role_name>**.` (`handlers.py:194-195`); if the reaction couldn't be added: `⚠️ Role saved, but I couldn't add the reaction …` (`handlers.py:183-187`) | `role` / `reaction_role_bound` / `role.bind_reaction` (`ops.py:328`, `_db_op("role.bind_reaction","reaction_role_bound",…)`) |
| reaction-role **runtime** (a member reacts / un-reacts on a bound message) | Role added/removed on the member (`add_role`/`remove_role`, `role_actions.py:96-109`) driven by `sb/domain/role/automation.py` | (no command ack — passive) | `role` audit fact from the automation seam (`sb/domain/role/automation.py`) |

Note on the guild-VIEW seam: the mutation ports above are **inert without** `DiscordGuildSource` (`role_actions.py:198-226`, installed at `main.py:461-462`). Without it `service.guild_view` returns `None` and `!deleterole` / `!assignroles` / XP role-sync short-circuit *before* reaching a mutation port (`role_actions.py:201-207`). It is armed inside the same block, so a correctly-armed boot has it. `!assignroles` itself is a **preflight/dry check** (`handlers.py:365-390`, ack via `format_role_check_result`), not a mutation — use it to confirm the bot's manage-roles readiness before driving `!temprole`.

### 3.3 Channel (`subsystem = "channel"`; adapters `sb/adapters/discord/channel_actions.py`)

> **Line-ref note (as of `c7f46fb`):** the SLICE-3 review-fix commit expanded
> `channel_actions.py`, so the `channel_actions.py:NNN` citations in this §3.3
> table and in §3.4 are **approximate** — they shifted ~+40 lines from the
> draft. The method *names* (`set_slowmode` / `set_overwrite` /
> `create_text_channel` / `delete_channel` / `create_invite`, and the proof
> `lock_channel_for_winner` / `unlock_channel`) are exact; grep by name if a
> line number is stale. The load-bearing fence (§4.3) and proof-channel class
> refs have been re-pinned to `c7f46fb`.

Channel effects audit through a **best-effort in-process** seam, `emit_channel_audit` (`sb/domain/channel/service.py:225-244`): `subsystem="channel"`, `mutation_type=f"channel_{operation}"`, plus a paired `channel.lifecycle_changed` advisory event (`service.py:247-263`). This is the shipped lifecycle-contracts twin, distinct from the K7 audit spine.

| Command | Discord state change | Expected ack copy | Expected audit row (`subsystem` / `mutation_type`) |
|---|---|---|---|
| `!slowmode #channel <seconds>` | `channel.edit(slowmode_delay=…)` (`channel_actions.py:141-148`) | `Slowmode set to **<seconds>s** in "<name>".` or, for 0, `Slowmode disabled in "<name>".` (`handlers.py:158-160`) | `channel` / `channel_set_slowmode` (`handlers.py:150,155`) |
| `!lock #channel` | `@everyone` send_messages denied via `set_permissions` (`channel_actions.py:150-162`) | `"<name>" locked.` (`handlers.py:102`, `past="locked"`) | `channel` / `channel_set_overwrite` (`handlers.py:95,100`) |
| `!unlock #channel` | `@everyone` send_messages restored | `"<name>" unlocked.` (`handlers.py:102`, `past="unlocked"`) | `channel` / `channel_set_overwrite` |
| channel create (setup/ensure lane) | `guild.create_text_channel(...)`, overwrites applied at creation (`channel_actions.py:164-185`); ALWAYS creates (get-before-create is domain logic, D-0077) | (per calling surface) | `channel` / `channel_<operation>` via `emit_channel_audit` |
| channel delete (setup/teardown lane) | `channel.delete(...)`; `discord.NotFound` treated as SUCCESS — already-gone is the goal state (`channel_actions.py:187-199`) | (per calling surface) | `channel` / `channel_<operation>` |
| `!invite [#channel]` | `channel.create_invite(...)` mints an invite; returns the URL (`channel_actions.py:201-213`) | the minted invite URL (shipped `!invite` copy) | `channel` / `channel_<operation>` |

### 3.4 Proof-channel prize lock/unlock (`subsystem = "proof_channel"`; adapter `DiscordProofChannelActions`, `channel_actions.py:258-313`)

This is a **separate** port from the channel domain (do not conflate). The verb is a bulk `channel.edit(overwrites=…)`, not the per-target `set_permissions` PUT.

| Command | Discord state change | Expected ack copy | Expected audit row |
|---|---|---|---|
| `!timedprize @winner <minutes>` (lock for winner) | Channel hidden from `@everyone`, winner granted view+send, bot kept visible (`channel_actions.py:286-300`) | `🔒 …` timed-grant copy (`handlers.py:53-55`) | `proof_channel` / `proof_access_granted` / `proof_channel.*` (`ops.py:226`) |
| unlock (auto on expiry, or the unlock surface) | Read-only for everyone restored, bot visible (`channel_actions.py:302-313`) | `🔓 …` / `<#cid>: no active timed prize lock.` (`handlers.py:115-117`) | `proof_channel` / `proof_access_revoked` / `proof_channel.*` (`ops.py:234,249`) |

---

## 4. Verify

### 4.1 How the audit rows are written

Every K7 compound op (all moderation + role ops) writes, **inside the step-4 txn**, exactly one `audit_log` DB row **and** one durable `audit.action_recorded` bus event, via `emit_central_audit` (`sb/kernel/workflow/audit.py:72-121`):

- `audit_log` columns: `mutation_id`, `subsystem = spec.domain`, `mutation_type = spec.audit_verb`, `target = spec.op_key`, `scope` (`"guild"` when `ctx.guild_id` set), `guild_id`, `prev_value`/`new_value` rollup, `actor_id`, `actor_type`, `occurred_at`, `detail` JSONB, `correlation_id` (`audit.py:94-105`).
- the bus twin rides the outbox durable enqueue `enqueue_audit_action(conn,…)` (AT_LEAST_ONCE, `audit.py:107-120`) and is delivered by the poll supervisor relay.
- `audit_log` sole writer is `kernel.workflow`, retention permanent, reader domains `server_logging`/`diagnostics` (`audit.py:40-56`).

Channel + proof-channel effects use the **best-effort** `emit_channel_audit` bus fact instead (`channel/service.py:225-244`) — a bus event, not an `audit_log` row.

### 4.2 Reading the rows

For the K7 domains (moderation, role), query the `audit_log` table directly against the same `DATABASE_URL`:

```sql
-- the rows your drive should have produced, newest first
SELECT occurred_at, subsystem, mutation_type, target, guild_id, actor_id, new_value
FROM audit_log
WHERE guild_id = 1350952413737259151
ORDER BY occurred_at DESC
LIMIT 20;
```

Confirm one row per effect with the expected `subsystem`/`mutation_type`/`target` from §3:
- `!ban` → `moderation` / `member_banned` / `moderation.ban`
- `!kick` → `moderation` / `member_kicked` / `moderation.kick`
- `!timeout` → `moderation` / `member_timed_out` / `moderation.timeout`
- `!unban` → `moderation` / `member_unbanned` / `moderation.unban`
- `!temprole` → `role` / `grant_temp_role` / `role.grant_temp_role`
- `!reactroles` → `role` / `reaction_role_bound` / `role.bind_reaction`

For channel + proof-channel effects there is **no** `audit_log` row (best-effort bus fact only). Verify those by (a) the Discord state change itself, (b) the ack copy, and (c) the `audit.action_recorded` / `channel.lifecycle_changed` log lines from `emit_channel_audit` / `emit_channel_lifecycle` in the process log. Cross-check the `boot_canary` row in `audit_log` first (`subsystem='platform'`, `mutation_type='boot_canary'`, `main.py:153-180`) to confirm the audit lane itself is delivering.

### 4.3 What a refusal on a NON-allowed guild looks like

Point any effect at a guild id **other than** `1350952413737259151` (e.g. a second guild the test bot happens to be in) and the adapter refuses **before any Discord call**:

- `_guild()` raises `GuildNotAllowedError` when `guild_id != allowed_guild_id` (`moderation_actions.py:83-91`; role via `_GuildAllowList._guild`, `role_actions.py:72-83`; channel via `_ChannelAllowList._channel` / `_ChannelGuildAllowList`, `channel_actions.py:79,110-133`).
- The exception message reads, e.g., `moderation effect REFUSED: guild <X> is not the allowed test guild 1350952413737259151 …` (`moderation_actions.py:57-61`); the role adapters pass `effect="role"` so the copy reads `role effect REFUSED …` (`role_actions.py:78-79`).
- The engine classifies this loud raise as **PARTIAL + operator finding** (the not-installed-port posture), **never a silent mutation** (`moderation_actions.py:39-50`). No member is kicked, no role changes, no channel is edited — the raise happens before the first Discord API call.
- Channel-scoped methods (only a `channel_id`) resolve the guild from the **cache** (`bot.get_channel`, never REST) and REFUSE any channel whose guild ≠ the allow-list, including unresolvable channels (DMs, uncached prod channels resolve to guild id 0 → refused, `channel_actions.py:119-133`; role MessageOps the same, `role_actions.py:155-168`).
- The role guild-VIEW read seam refuses softly: a non-allowed guild returns `None` (the effect stays blocked, the unarmed posture) rather than raising, because `guild_view` is a read the handlers branch on (`role_actions.py:222-225`). The mutation ports keep the hard `GuildNotAllowedError` raise as defense-in-depth.

Expected user-facing result of a refusal: the effect is blocked and the handler echoes the refusal (e.g. channel handlers surface `Could not <verb> "<name>": <exc>`), and there is **no** corresponding `audit_log` mutation row.

---

## 5. Safety checklist

- [ ] **Double gate confirmed.** Both `SB_DATA_PLANE=test` **and** `SB_APPCMD_SYNC_GUILD_ID=1350952413737259151` are set. `moderation_test_guild → guild_sync_target` returns non-`None` only when both hold (`main.py:112-138`). Either alone ⇒ ports do not install.
- [ ] **Per-call allow-list confirmed.** Every adapter was constructed with `allowed_guild_id=test_guild_id` (`main.py:420-497`); the fence refuses any other guild before a Discord call (§4.3). This is what protects real guilds from a test-plane process that still holds a real gateway token.
- [ ] **The three ARMED log lines are present** (`main.py:423-425`, `:463-466`, `:498-501`); no others.
- [ ] **`SB_VERIFY_BOOT` is unset** (setting it returns before the gateway, `main.py:224-229` — no live effects at all).
- [ ] **Prod stays UNARMED.** On the prod plane the effect ports are **never installed by this root**: `guild_sync_target` returns `None` when `SB_DATA_PLANE != "test"` (`main.py:120-123`), so `moderation_test_guild` returns `None`, so the entire `if test_guild_id is not None:` block is skipped (`main.py:410`). A live `!ban`/`!kick` on prod would write its DB row + ack but perform **NO** Discord mutation — the not-installed port raises loudly → PARTIAL (`main.py:400-408`, module docstring `moderation_actions.py:1-16`).

### The single CUT-3 owner switch that would arm prod

**Name: `SB_PROD_ATTEST`** — the opaque, human-set prod attestation token whose **presence** flips the data plane to attested-prod (`sb/spec/config.py:218-219`: *"opaque human-set prod token; PRESENCE => attested"*; registry `prod_attest_token`, `credentials.py:149-151`; review `program-review-2026-07-12.md:266-269`). Setting `SB_DATA_PLANE=prod` + `SB_PROD_ATTEST=<token>` is the owner's gate that authorizes a production data-plane boot.

**Honest caveat — read this before treating `SB_PROD_ATTEST` as an "arm prod effects" switch.** In the CUT-1 root, flipping to attested prod does **not** arm the effect adapters — it *disarms* them, because the effect ports install only under `SB_DATA_PLANE == "test"` (via `guild_sync_target`, `main.py:120-123`). There is **no env var in this root that arms live guild effects on the prod plane.** Arming prod effects is a deliberate **CUT-3 code change** the owner must land (relaxing the `== "test"` fence / installing the ports on the prod plane under a prod allow-list), gated behind `SB_DATA_PLANE=prod` + `SB_PROD_ATTEST`. The composition root is explicitly labelled the *"CUT-1 test-mode main()"* and the global command set *"is still the OLD bot's until CUT-3"* (`main.py:1,22-29`; review `program-review-2026-07-12.md:237-241`). This runbook does **not** perform that change and the owner should treat it as out of scope for a live-drive.

---

## 6. Rollback / disarm

The ports are installed only in-process at boot; there is no persistent "armed" state to unwind. To disarm:

1. **Stop the process** — SIGTERM/SIGINT triggers the clean shutdown path: `request_shutdown → DRAINING → drain outbox → SHUTTING_DOWN → gateway closed → STOPPED, exit 0` (`main.py:667-731`). This lets pending audit rows drain (`_drain_outbox`, `main.py:183-202`) before the gateway closes, so your effect evidence is not lost.
2. **Unset a gate and reboot** — remove **either** `SB_DATA_PLANE=test` (set nothing, or `prod`) **or** `SB_APPCMD_SYNC_GUILD_ID`. On the next boot `test_guild_id` is `None`, the `if test_guild_id is not None:` block is skipped, and none of the three ARMED lines appear — the effect ports are gone (`main.py:409-410`). A live command then writes its row + ack but performs no Discord mutation (the not-installed port raises loudly → PARTIAL).
3. **If a specific effect misbehaves mid-session**, the fastest safe disarm is step 1 (stop the process); re-check §2.2 before re-arming. Do not switch to the prod plane as a "disarm" — that is the CUT-3 path, not a rollback.
4. **Undo the effect on Discord manually** if needed (unban a member you banned, delete a role you created, `!unlock` a channel you locked) — the adapters offer no automatic teardown beyond the K7 compensators that fire only when Discord itself refused a leg.

---

*Every wiring claim above cites `file:line` at the `claude/live-channel-adapters` tip. If the lane advances, re-verify the `main.py` install block (`:409-501`) and the three ARMED log lines before running this procedure.*
