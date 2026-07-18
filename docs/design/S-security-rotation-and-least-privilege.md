# S — Security: secret rotation (zero-downtime) + startup fail-closed + least-privilege

> **Status:** `plan`
>
> A forward design proposal opened as a NEW **production-readiness** track
> beyond the D1–D6 planning lanes. This is a PLAN, not built work — the owner
> reacts and prioritizes; the code and `docs/decisions.md` win once slices
> land. Evidence citations are `file:line` at HEAD `cae15f8` unless noted.
> **No secret VALUE appears in this doc — env-var NAMES only.**

## TL;DR

superbot-next already ships most of the *machinery* a secure-secret posture
needs — a resumable rotation phase ledger, a typed fail-closed config
preflight, and a closed revocation vocabulary — but the machinery is **built
and deliberately un-armed**, so the production-readiness gaps here are seams,
runbooks, and one honest audit, not missing subsystems:

- **Rotation** has a full crash-safe executor (`sb/kernel/credentials/rotation.py`)
  whose `RotationProvider` port is un-installed by design (CUT-1) — and the two
  secrets a leak would force an *emergency* swap of
  (`DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`) are exactly the ones the
  cadence detector never arms. There is no minutes-scale rotation runbook for
  them.
- **Startup** already fails closed on an *absent* required FAIL_FAST secret
  (preflight refuses boot). The residual gap is the *malformed* opaque secret:
  a corrupt token passes coercion unchanged and only trips much later at
  gateway connect, and there is no reviewed manifest of "required-at-boot".
- **Least-privilege** is the widest-open of the three: `Intents.default()`
  turns on every non-privileged gateway intent regardless of the feeds the boot
  path actually arms, and the DB connect role is whatever the DSN embeds — the
  same role that runs migrations, so it holds DDL the steady-state worker never
  needs. No audit of held-vs-needed is recorded anywhere.

Each fix is a small, landable slice. The highest-value / smallest is the
startup fail-closed tightening; the rotation runbook and least-privilege audit
follow.

## Problem

Three concrete security gaps, each grounded in the current code.

### S1 — No documented zero-downtime rotation for the emergency-swap secrets

The rotation subsystem is real and resumable. `sb/kernel/credentials/rotation.py`
drives a distinguished externally-effecting durable one-shot through a phase
machine over the `sb_credential_rotation` ledger
(`sb/kernel/db/credentials.py:26`): `reserved` → `issued_pending_verify` →
`verified`, guarded by a horizon-stable `once()` key so a duplicate arm and a
boot-reconcile re-fire fold to the same guard row and RESUME rather than
re-issue (`rotation.py:111-172`). This is precisely the property a rotation
needs to survive its own restart, because swapping a `WORKER_ENV` credential is
a var change = redeploy = **restart of the very worker performing the swap**
(the runbook's Q-0193 note, `docs/operations/credential-lifecycle.md:19-25`).

But two structural facts make it inert for the emergency case today:

1. **The provider port is un-installed (CUT-1).** With `_PROVIDER is None` the
   executor takes the loud-fail branch: it sets the ledger phase to `failed`,
   records a `blocked` outcome, and emits an operator finding — never a silent
   pass (`rotation.py:135-148`). So *no* rotation actually executes in this
   repo; the arm exists, its ops wiring does not.

2. **The two emergency-swap secrets have no cadence path at all.** The cadence
   detector only arms `AUTONOMOUS` / `OWNER_PROMPT` postures and skips the rest
   (`cadence.py:59-61`). In the registry
   (`sb/spec/credentials.py`), `discord_prod_bot_token`
   (`DISCORD_BOT_TOKEN_PRODUCTION`) is `ON_COMPROMISE` with `cadence_days=None`,
   and `prod_dsn` (`DATABASE_URL`) is `MANAGED` — both skipped. These are the
   `BOT_PRESENCE` and `PROD_DATA` blast tiers, i.e. the ones a leak most needs
   rotated in minutes, and neither is reachable by the autonomous arm.

Compounding it, there is **no live re-read seam** to hot-swap a token into: the
composition root reads the frozen `Config` token exactly once, at gateway
connect (`cfg.DISCORD_BOT_TOKEN_PRODUCTION`, `sb/app/main.py:598`), and the DSN
once at `pool.init(cfg)` (`main.py:256`). `Config` is a frozen dataclass built
at preflight (`sb/kernel/config/__init__.py:125-171`). So "zero-downtime
rotation" cannot mean in-process hot-swap without a new seam — it must mean a
crash-safe **drain-and-reboot** the phase ledger already makes idempotent. The
existing runbook (`docs/operations/credential-lifecycle.md`) documents the
*compromise-recovery triage* and the phase table, but it does NOT give an
operator a step-by-step "rotate `DISCORD_BOT_TOKEN_PRODUCTION` in N minutes with
one bounded restart" procedure, nor name the acceptable-downtime target.

### S2 — Startup fails closed on absent, but not on malformed, required secrets

The good news first, because it narrows the gap: preflight **does** fail closed
on an absent required FAIL_FAST secret. `load_config` appends a `ConfigError`
("required but absent") for any `required` + `FAIL_FAST` field with no value and
raises an aggregate `StartupError` (`config/__init__.py:186-205`); the
composition root maps that to `FAILED_STARTUP` and returns a non-zero exit
before DB init, before the health bind, before gateway connect
(`main.py:218-221`). The three hard-required FAIL_FAST fields —
`DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`, `SB_DATA_PLANE`
(`sb/spec/config.py:124-125,207-208`) — therefore cannot half-boot when absent,
and `main.py`'s `finally` never leaves a zombie: each `_fail_startup` returns and
the process exits (`main.py:205-210,806-830`). The "zombie half-booted process"
risk is thus smaller than a first pass fears.

The residual gap is the **malformed** secret. A `SECRET`-typed field is opaque:
`_coerce`'s STR/SECRET branch returns the raw string unchanged, applying only a
`choices` check that secrets don't set (`config/__init__.py:118-122`). So a
truncated / whitespace-corrupted / wrong-format `DISCORD_BOT_TOKEN_PRODUCTION`
**passes preflight** and only trips much later, at gateway connect, where the
gateway rejects it and the root maps `GatewayConnectError` to `FAILED_STARTUP`
(`main.py:596-600`). That is still fail-closed — but *late* and *expensive*: it
happens after DB pool init, migrations, health bind, runtime build, and plugin
load, so a corrupt token burns the whole boot before failing, and the failure
reads as a gateway problem rather than a config problem. `DATABASE_URL` is the
counter-example that shows the fix is cheap and idiomatic: it is `DSN`-typed and
gets real *shape* validation at preflight (`parse_dsn` checks scheme/host/db and
raises `ConfigError` early, `config/__init__.py:83-98`) without connecting.
There is no equivalent cheap shape check for the opaque token, and no reviewed,
named manifest of which secrets are *required-at-boot* vs optional — the
posture assignments (`_FF` / `_DEG` / `_DOR` in `sb/spec/config.py:118-248`) are
correct but incidental, never audited as a set.

### S3 — No recorded least-privilege review of intents / permissions / DB role

**Discord intents.** The gateway builds intents as `Intents.default()` plus the
two privileged intents only when their approval envs assert approval
(`build_intents`, `sb/adapters/discord/gateway.py:54-58`). `Intents.default()`
is a broad *bundle* — it enables every non-privileged gateway intent (guilds,
guild messages, reactions, voice states, typing, integrations, webhooks,
invites, …) whether or not the bot consumes it. The boot path actually arms a
knowable, small set of feeds: the raw-reaction feed (reactions intent,
`sb/adapters/discord/reaction_feed.py:16`), the guild-join feed (guilds intent,
`main.py:709-717`), the message feed (guild messages + the privileged
`message_content`, `main.py:654-669`), and the members-gated join/leave lane
(privileged `members`, `sb/spec/config.py:261-264`). Nothing enumerates
`Intents.default()`'s bundle against that consumed set — voice/typing/invites
are on with no consumer. The two *privileged* intents are already correctly
gated and default-off (`SB_INTENT_MSGCONTENT_OK` / `SB_INTENT_MEMBERS_OK`,
`sb/spec/config.py:222-225`); it is the non-privileged bundle that is un-audited.

**Discord permissions.** The bot's *guild permission* surface (the OAuth bot
scope granted at invite time) is not expressed in this repo — there is no
permissions integer in code; the adapters only *read* effective perms at call
time (e.g. `channel.permissions_for(me)`,
`sb/adapters/discord/ai_operator_ports.py:52`; `me.guild_permissions`,
`sb/adapters/discord/moderation_actions.py:169`). So the granted permission set
lives entirely in the invite URL / developer-portal config and has never been
audited against the mutation ports the bot actually installs (kick/ban/timeout,
role add/remove/create/delete, channel state ops — all in `main.py:427-532`).

**DB role.** The worker connects with whatever role the `DATABASE_URL` DSN
embeds, and that same connection runs migrations at `pool.init(cfg)`
(`main.py:256`) — so the runtime role necessarily holds **DDL** (CREATE/ALTER)
that the steady-state request path never uses. There is no separate least-
privilege runtime role (DML-only) distinct from a migration role (DDL), and no
recorded review of the grants the worker holds vs needs.

## Proposed design

Three components, each respecting the layer rules (`sb/kernel/credentials`,
`sb/kernel/config` import spec/namespace only; the boot guard lives at the
composition root; adapters own the Discord seam).

### S.1 — Fail-closed startup guard (smallest, highest value — do first)

Tighten preflight so a *malformed* required secret fails at preflight, not at
gateway connect, and record the required-at-boot set as a reviewed manifest.

- Add an optional **shape validator** to `SecretSpec` — a pure predicate on the
  raw string (length floor / charset / structural sanity), applied in `_coerce`'s
  SECRET branch (`config/__init__.py:118-122`) so a corrupt
  `DISCORD_BOT_TOKEN_PRODUCTION` raises `ConfigError` early exactly as `parse_dsn`
  does for the DSN. The check must be *shape only* — never a value assertion,
  never a network call, never anything that could log a secret (redaction stays
  enforced by `Config.__repr__`, `config/__init__.py:132-140`).
- Emit the guard's refusal as a *config* finding at preflight (the already-wired
  `StartupError → FAILED_STARTUP` path, `main.py:218-221`) with a clear
  env-var-named reason ("`DISCORD_BOT_TOKEN_PRODUCTION`: malformed (fails shape
  check)") — never the value.
- Codify the **required-at-boot manifest** as a doc + a light CI assertion over
  `CONFIG_FIELDS` postures: exactly the intended set is `FAIL_FAST`, and every
  credential-bearing field's posture is deliberate. This turns the incidental
  posture assignments into a reviewed contract.

Size **S**. No new subsystem — one predicate field + one coercion branch + one
doc/assertion.

### S.2 — Documented zero-downtime rotation runbook (drain-and-reboot)

State plainly that hot-swap is *not* feasible without a new live-re-read seam
(the token is read once from a frozen `Config`, `main.py:598`), and design the
**drain-and-reboot** path the phase ledger already makes crash-safe:

- Write an ops runbook `docs/operations/secret-rotation-runbook.md` giving the
  minutes-scale procedure per emergency-swap secret: issue the replacement in the
  provider console → set the new env var → the `WORKER_ENV` swap triggers the
  Railway redeploy (bounded restart) → `/ready` gates traffic until gateway +
  DB + RUNNING (`main.py:602-603`, the existing readiness seam) → verify →
  revoke the leaked copy via the row's `revocation_ref` (closed vocabulary,
  `sb/spec/credentials.py`). "Zero-downtime" is met by the readiness gate + a
  single bounded restart, not by a live swap.
- For the secrets that CAN be autonomous, close the CUT-1 wiring: install a real
  `RotationProvider` (`rotation.py:59-85`) so the existing ledger executes
  instead of loud-failing. This is ops wiring behind the existing port — the
  kernel seam is already built and unchanged.
- Flag the **posture question** for the emergency-swap pair: whether
  `discord_prod_bot_token` should stay `ON_COMPROMISE` (no cadence) or gain a
  cadence, and whether `prod_dsn`'s `MANAGED` posture should be paired with a
  documented owner-driven rotation, so the two highest-blast secrets are not the
  only ones with no rotation lane.

Size **M** (runbook **S**; provider install **M**, ops-side).

### S.3 — Least-privilege audit (intents / permissions / DB role)

Record the held-vs-needed review the code has never had:

- **Intents:** replace `Intents.default()` with an *explicit* intent set built
  from the consumed feeds (guilds, guild messages, reactions, + the two gated
  privileged intents) in `build_intents` (`gateway.py:54-58`), dropping bundle
  members with no consumer (voice, typing, invites, …). Enumerate consumed-vs-
  held in the audit so the trim is evidence-backed, not guessed.
- **Permissions:** enumerate the Discord guild-permission bits the installed
  mutation ports require (kick/ban/timeout, manage roles, manage channels —
  `main.py:427-532`) and propose the minimal invite-scope permission set,
  recorded as an ops artifact (the grant lives in the portal, not the repo).
- **DB role:** propose splitting a **DDL migration role** (runs `pool.init`
  migrations) from a **DML-only runtime role** (the steady-state connection), so
  the worker's live `DATABASE_URL` role cannot CREATE/ALTER. Document the grant
  scope; the split is a deployment/ops change, not a kernel one.

Size **M** (intent trim **S**, code; permissions + DB-role review **M**,
mostly ops artifacts + owner decisions).

## Affected surfaces

| Surface | File(s) | Change |
|---|---|---|
| Secret shape validation | `sb/spec/config.py` (`SecretSpec`), `sb/kernel/config/__init__.py` (`_coerce`) | add optional shape predicate + fail-closed early (S.1) |
| Required-at-boot manifest | new doc + light CI over `CONFIG_FIELDS` postures | reviewed contract (S.1) |
| Rotation runbook | new `docs/operations/secret-rotation-runbook.md` | drain-and-reboot procedure (S.2) |
| Rotation provider wiring | `sb/kernel/credentials/rotation.py` (`RotationProvider` install, ops-side) | close CUT-1 so the ledger executes (S.2) |
| Credential postures | `sb/spec/credentials.py` (`CREDENTIAL_REGISTRY`) | owner call on the emergency-swap pair's posture (S.2) |
| Explicit intents | `sb/adapters/discord/gateway.py` (`build_intents`) | trim `Intents.default()` to consumed set (S.3) |
| Permission + DB-role audit | ops artifacts + `DATABASE_URL` grant | held-vs-needed review, DDL/DML role split (S.3) |

No `sb/` code changes in THIS doc — it is a plan. The layer rules hold: the
config/credentials changes stay in kernel bands importing spec only; the intent
change stays in the discord adapter; the runbook and role split are ops.

## Rough size + suggested PR slicing

| Slice | Component | Size | Rationale |
|---|---|---|---|
| 1 | S.1 fail-closed startup guard | **S** | smallest + highest value; one predicate + one coercion branch + a reviewed posture manifest — fails malformed secrets early, before the expensive boot legs |
| 2 | S.2 rotation runbook | **S** | docs-only ops procedure over the already-crash-safe phase ledger; unblocks a real emergency swap without waiting on provider wiring |
| 3 | S.2 provider install | **M** | ops-side CUT-1 wiring behind the existing `RotationProvider` port; makes the autonomous ledger actually execute |
| 4 | S.3 intent trim | **S** | replace `Intents.default()` with the explicit consumed set — contained adapter change, evidence-backed by the audit |
| 5 | S.3 permission + DB-role audit | **M** | held-vs-needed enumeration + the DDL/DML role split; mostly ops artifacts + owner decisions |

Suggested order: **1 → 2 → 4** are small, high-confidence, and independently
landable; **3 → 5** carry ops/owner dependencies (provider mechanism, DB role
provisioning) and follow.

## Open questions for the owner

1. **Secret store / rotation mechanism.** Are secrets in Railway env vars only,
   or is a vault/secret-manager in scope? The runbook's "set the new env var →
   redeploy" step and the `RotationProvider` install both depend on this.
2. **Acceptable rotation downtime.** What is the target for an emergency swap —
   is a single bounded Railway redeploy (drain-and-reboot behind `/ready`)
   acceptable, or is true zero-downtime hot-swap required (which needs a new
   live-re-read seam the frozen `Config` does not have today)?
3. **Required-at-boot set.** Confirm exactly which secrets must be present at
   boot (currently the FAIL_FAST trio: `DISCORD_BOT_TOKEN_PRODUCTION`,
   `DATABASE_URL`, `SB_DATA_PLANE`) vs which stay optional/DORMANT — this
   freezes the S.1 manifest.
4. **Emergency-swap posture.** Should `discord_prod_bot_token` (`ON_COMPROMISE`)
   and `prod_dsn` (`MANAGED`) keep their current no-cadence postures, or gain a
   documented rotation lane so the two highest-blast secrets aren't the only
   ones with no autonomous path?
5. **Discord permission trim.** Are we willing to re-scope the bot's invite
   permissions to the minimal set the installed mutation ports need, accepting a
   re-invite / portal change?
6. **DB least-privilege scope.** Approve splitting a DDL migration role from a
   DML-only runtime role for `DATABASE_URL`? This is a deployment change (two
   roles, two connection strings or a migration-time elevation), not a kernel
   one.
