# D5 — End-to-end / live-guild test harness

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase — the second doc in
> the planning-mode design-doc series the completeness snapshot opened
> (`docs/status/completeness-table-2026-07-18.md`, #525; series home in
> `docs/design/README.md`). This is a PLAN, not built work — the owner reacts and
> prioritizes; the code and `docs/decisions.md` win once slices land. Evidence
> citations are `file:line` at HEAD `b39a37f` unless noted.

## TL;DR

The corpus proves a lot and one specific thing not at all. Golden-parity replays 525
recorded goldens through a **fake-HTTP/gateway transport** over the real interaction
pipeline (`tools/run_golden_parity.py:20-27`) — byte-level proof that a recorded input
still produces its recorded output. `check_runtime_smoke` proves the boot **wiring
graph** is intact (`tools/check_runtime_smoke.py`). Neither drives the ~19 real Discord
adapter modules (`sb/adapters/discord/*`) or the gateway→RUNNING composition path
(`sb/app/main.py` step 10/11) — the parity boot **deliberately skips "gateway anything"**
(`sb/adapters/parity/boot.py` docstring) and the smoke gate **dispatches nothing**
(`tools/check_runtime_smoke.py:66-68`). The only thing that has ever exercised the real
adapter + a live guild is **ad-hoc manual live-drive**, recorded as prose in testing
reports and as signed rows in the `verified_live` registry — a human running commands by
hand, not a repeatable harness. The proposal is a **tiered e2e harness**: (A) an
in-process adapter-level tier that drives the composition root through the real
`sb/adapters/discord/*` code against a fake/record gateway — the first repeatable thing
between "wiring graph" and "manual live drive", CI-able in a discord-installed job; and
(B) an optional **LIVE** tier that boots against the private test guild (Galaxy Bot),
runs a scripted command sweep, and asserts responses — on-demand/owner-run, because it
cannot run in headless CI by design. It **complements** golden-parity (recorded-replay of
the pipeline) — it does not duplicate it.

## Problem

Four concrete coverage gaps, each grounded in the current test surfaces.

### P1 — Golden-parity replays the pipeline but bypasses the real adapter + gateway

The golden-parity harness is real and deep: `run_gate()` / `run_report()` replay the
corpus and `check_parity_depth` reports **525 goldens across 50 ported subsystems**
green in CI (`docs/CAPABILITIES.md:118-121`). But the replay binding is explicit about
what it drives: the new bot's replay adapter is *"a fake-HTTP/gateway transport over
sb/'s real interaction pipeline"* (`tools/run_golden_parity.py:20-22`), and the replay
composition root spells out its own deviations — *"Deliberately skipped (ops, not
behavior … health server, poll supervisor lanes, boot-gate legs …, **gateway
anything**"* (`sb/adapters/parity/boot.py`, module docstring). The transport substitutes
for the entire Discord I/O shell: `ParityTransport`, `ParityPresenter`,
`ParityResponder`, `ParityChannelEmitter`, … stand in for the real adapter ports
(`sb/adapters/parity/boot.py:41-53`).

The consequence is a real blind spot. The `sb/adapters/discord/` band is ~19 modules —
`gateway.py`, `egress.py`, `command_tree.py`, `panel_view.py`, `component_feed.py`,
`message_feed.py`, `reaction_feed.py`, `modal_view.py`, `confirm_view.py`,
`responders.py`, `channel_actions.py`, `moderation_actions.py`, `role_actions.py`,
`guild_feed.py`, `member_tier.py`, `nl_shell.py`, `setup_reads.py`, `utility_reads.py`,
`ai_operator_ports.py`. A regression that lives ONLY in one of these — an egress
serialization bug, a component-custom-id parse change, a modal wire-type-5 boundary, a
panel-view render that diverges from the parity presenter — is **byte-invisible to all
525 goldens**, because the goldens never route through those modules. "525/525 green"
is a true statement about the interaction pipeline and a silent statement about the
adapter that carries it.

### P2 — The headless smoke proves wiring, not behavior

`check_runtime_smoke` is a genuine boot: it rides the same composition-root paths as
`sb.app.main` (boot-gate leg A, `load_live_manifests`, `build_runtime`,
`register_manifest_panels`, `arm_subscribe_roster`) and asserts the W1–W6 wiring graph —
every ref resolves, every panel is registered, every durable event has a subscriber
(`tools/check_runtime_smoke.py:1-52`). It is deliberately hermetic: *"no token, no guild,
no DB, no network"* (`tools/check_runtime_smoke.py:8-9`). But it is explicit about its
ceiling: *"Nothing is DISPATCHED end-to-end (no command exercised): this is the
boot-and-wire tier; the dispatch-tier live-boot job is the order's named follow-up"*
(`tools/check_runtime_smoke.py:66-68`). So between "the graph is wired" (smoke) and "a
recorded input replays byte-identically through the pipeline" (parity), there is **no
tier that boots and actually dispatches a command through the real adapter surface**.
The "dispatch-tier live-boot job" the smoke gate names as a follow-up is precisely this
D5 lane.

### P3 — The only real-adapter/live-guild coverage is manual and unrepeatable

The bot HAS been driven live — against the owner's test bot **Galaxy Bot#6724**
(id `1298426054636994611`) on the private guild **MineSnakeBotTest**, where it holds
ADMINISTRATOR (`docs/status/testing-report-2026-07-09.md:65,469`). The CUT-1 smoke's
runnable entrypoint was *"verified against a real Postgres 16 + the owner's test bot
(READY as Galaxy Bot#6724)"* (`docs/decisions.md:372`). Band-by-band live drives posted
real panels into `#bot-activity` and wrote real audit rows
(`docs/status/testing-report-2026-07-09.md:27,36`). This is real coverage — but it is a
**human at a keyboard**, transcribed into prose reports and into the `verified_live`
registry as **signed one-off facts** (`tools/check_verified_live.py:1-20`: V2 requires a
signer + `signed_at` + `build_sha` + linked evidence per record). The registry is a
*dashboard of past manual verifications*, not a harness that re-runs them: nothing replays
that command sweep on demand, so a regression in a surface last hand-verified three weeks
ago is caught only when a human next thinks to drive it again.

### P4 — Integration tests cover DB races, not adapter/gateway end-to-end

`tests/integration/` exists and runs against a real Postgres, but its remit is
**concurrency correctness at the data plane**, not the adapter: the files are
`test_farm_mining_money_race.py`, `test_mining_*_race.py`, `test_tournament_entry_race.py`,
`test_fishing_bait_consume_race.py`, `test_games_checkpoint_race.py`, … — the F-001/F-002
money-race regression class. The conftest is explicit that this directory needs asyncpg +
Postgres and runs in the `golden-parity` named gate's service-container job
(`tests/integration/conftest.py:1-13`). So the integration tier is orthogonal to D5: it
proves no two concurrent effects double-spend; it says nothing about whether a Discord
interaction reaches an effect through the real adapter at all.

## Proposed design

A **tiered** e2e harness. Each tier is independently landable and answers a different
question; higher tiers cost more and gate less often. All tiers respect the layer rules
in `.claude/CLAUDE.md`: the harness is test/tooling code (it may import everything, like
`sb/app`), the test-only fakes live beside it, and no `sb/` layer edge is added.

### D5.1 — In-process adapter-level tier (fake/record gateway → composition root)

The seam already exists in a proven shape. The parity harness boots the new bot
in-process and exposes a driving contract — `await Harness.start()` → `send_command` /
`invoke_slash` / `click` → `take_calls` / `take_events` → `await close()`
(`sb/adapters/parity/boot.py:3-7`). D5.1 is the **non-replay twin** of that harness: same
in-process boot, but instead of the parity transport that substitutes for the adapter, it
drives the composition root through the **real `sb/adapters/discord/*` modules** with a
**fake gateway** underneath — a test double that emits synthetic `discord`-shaped events
(a message, an interaction, a component click, a modal submit) into the same
`message_feed`/`component_feed`/`command_tree`/`egress` code paths the live gateway feeds,
and **records** the outbound calls (channel sends, interaction responses, panel edits) for
assertion.

- **What it exercises that parity does not:** the real egress serializer, the real
  component-custom-id round-trip, the real panel-view render, the real command-tree
  registration — the ~19 adapter modules that P1 shows are currently un-driven.
- **The `discord` import tension (flag).** The adapter band is import-guarded — *"discord
  is absent in CI containers by design"* (`sb/adapters/discord/gateway.py:20-31,8`), and
  `gateway.py` is *"the ONE module that instantiates the discord client"*
  (`sb/adapters/discord/gateway.py:4-6`). So a tier that drives the real adapter needs
  either (a) `discord.py` installed in a dedicated CI job — the same pattern the
  `golden-parity` job already uses to install the full hash-pinned lock + a Postgres
  service (`.github/workflows/named-gates.yml:134`), or (b) a **fake `discord` module**
  injected on `sys.path` so the guarded imports resolve to a test double. (a) exercises
  the real discord types end-to-end but couples the tier to the library; (b) stays
  hermetic like the smoke gate but only proves *our* code, not the library boundary. This
  is the tier's central design call (see Open Questions). A pragmatic split: drive the
  **feed/egress** seams (which take already-parsed sb types) with (b) for a hermetic CI
  gate, and reserve real-`discord` exercise for the LIVE tier below.
- **Where it gates:** a CI job — hermetic variant runs in the `checkers`/named-gates
  environment; the discord-installed variant rides the `golden-parity` job's fuller
  environment. Fast, deterministic, required-check-able.
- **Seams hooked:** `sb/adapters/discord/{message_feed,component_feed,command_tree,egress,
  panel_view,modal_view,confirm_view}.py` (driven), the composition root
  `sb/app/main.py` (booted, gateway-connect leg stubbed), and a new fake-gateway double.

### D5.2 — LIVE tier (scripted command sweep against the private test guild)

An **optional** tier that does the last mile parity structurally cannot: boot the REAL
bot with a REAL token against the REAL private test guild and assert real responses.

- **Target.** The owner's test bot — **Galaxy Bot** on the private **MineSnakeBotTest**
  guild, where the bot has ADMINISTRATOR and all commands are free to exercise
  (`docs/status/testing-report-2026-07-09.md:65,469`). The token is supplied by the
  environment (`cfg.DISCORD_BOT_TOKEN_PRODUCTION`, consumed at the gateway connect,
  `sb/app/main.py:597-598`) — **the design hardcodes no secret**; it names the env var
  the composition root already reads.
- **The fence already exists.** The live effect ports (moderation/role/channel) are armed
  ONLY under a double gate — `SB_DATA_PLANE == "test"` (DB protection) AND an explicit
  `SB_APPCMD_SYNC_GUILD_ID` handed to each adapter as a **hard per-call allow-list**
  (`sb/app/main.py:112-131,427-484`); with no test-guild id (prod) the effect ports stay
  un-installed. The LIVE tier runs **inside this existing fence** — it sets exactly the
  env the composition root already requires to arm a test guild, so the sweep can hit real
  effects on MineSnakeBotTest and nowhere else. No new bypass is introduced.
- **Shape.** Boot `python3 -m sb` (the `cli()` entrypoint, `sb/app/main.py:833`) to
  RUNNING — gateway READY + `/ready` 200 (`sb/app/main.py:602-603`) — then a scripted
  driver posts a curated command set into a test channel via a **second lightweight
  Discord client** (or a control channel the bot reads), waits bounded, and asserts on the
  responses. Teardown drains the outbox and exits clean (the CUT-1 smoke's own drain
  discipline, `docs/decisions.md:372`).
- **Assertion granularity (design call).** Two options, cheaper-first: assert on
  **structural shape** (a panel with N fields, an embed titled X, an audit row written) —
  robust to copy drift; or assert on **rendered bytes** (the exact exposition) — strict but
  brittle, and partly redundant with golden-parity's byte check. Recommendation: structural
  shape for the live sweep (it is a smoke/health signal, not a second byte oracle); leave
  byte-exactness to parity. See Open Questions.
- **Why it cannot be a headless CI gate (say it plainly).** It needs a real bot token, a
  real guild, and outbound Discord network — none of which exist in the headless CI
  containers where discord is absent by design (`sb/adapters/discord/gateway.py:8,20-31`),
  and the full parity `--gate` already shows the session/container window is too tight for
  long serial live work (`docs/CAPABILITIES.md:110-122`). So D5.2 is **on-demand / owner-
  run** (a manual workflow-dispatch job with the secret, or a local owner run), producing a
  `verified_live` record on success — turning the manual drive of P3 into a *repeatable
  script* whose output feeds the existing signed registry (`tools/check_verified_live.py`),
  rather than a new required gate.

### D5.3 — Optional: record/replay bridge (stretch)

A thin bridge so a LIVE sweep can **record** its synthetic-gateway event stream into the
D5.1 fixture format — a live run becomes a hermetic in-process regression the next CI run
replays. This is the natural convergence point with golden-parity (which minted its corpus
from recorded old-bot traffic) without duplicating it: parity replays *interaction-pipeline
outputs*; this would replay *adapter-surface* I/O. Stretch, not first-slice.

## Affected surfaces

| Band | Files / new artifacts | Tier |
|---|---|---|
| test harness (new) | `tests/e2e/` (in-process driver + assertions) OR `tools/run_e2e.py` (parity-style driver) | D5.1, D5.2 |
| test-only fakes (new) | a fake-gateway double emitting synthetic `discord`-shaped events; optionally a fake `discord` module for the hermetic variant | D5.1 |
| adapter / discord (driven, not edited) | `sb/adapters/discord/{message_feed,component_feed,command_tree,egress,panel_view,modal_view,confirm_view}.py` | D5.1 |
| composition root (booted, not edited) | `sb/app/main.py` (boot to RUNNING; gateway-connect leg stubbed in D5.1, real in D5.2) | D5.1, D5.2 |
| live driver (new) | a scripted command-sweep client + a curated command list; consumes `DISCORD_BOT_TOKEN_PRODUCTION` + `SB_APPCMD_SYNC_GUILD_ID` from env | D5.2 |
| CI (new job) | a hermetic D5.1 gate in named-gates/checkers; the discord-installed variant in the `golden-parity` job's environment; a manual `workflow_dispatch` for D5.2 | D5.1, D5.2 |
| verified_live registry (fed, not edited) | a D5.2 success mints a signed record via the existing `verification/verified_live` schema | D5.2 |

No `sb/` source edit is required to STAND UP the harness — every tier drives existing
composition + adapter code; the new code is test/tooling that (like `sb/app`) may import
everything. Any adapter seam that turns out to be undrivable without a hook (e.g. a port
that has no test-injection point) becomes a small, flagged adapter change at that slice.

## Rough size + suggested slicing

- **D5.1 — in-process adapter tier** — **M**. The boot seam is a proven pattern to clone
  (`sb/adapters/parity/boot.py`), but the fake gateway + the discord-import decision
  (hermetic fake vs installed library) is the real work. Land the **hermetic feed/egress
  variant first** (highest signal for the cost: it turns the ~19 un-driven adapter modules
  into a required gate) as one PR; the discord-installed variant is a follow-up.
- **D5.2 — LIVE tier** — **L**, and partly owner-gated (needs the token + a dedicated
  network-capable runner or a local owner run). The scripted sweep + structural assertions
  are M; the CI plumbing (a `workflow_dispatch` job holding the secret, or the owner's
  local runbook) is the owner-decision part. Land AFTER D5.1 — the fake-gateway event
  vocabulary D5.1 defines is what the live sweep scripts against.
- **D5.3 — record/replay bridge** — **S–M**, stretch. Only worth it once D5.1's fixture
  format and D5.2's sweep both exist.

**How it complements (not duplicates) golden-parity.** Parity answers *"does a recorded
input still produce its recorded bytes through the pipeline?"* (regression oracle, byte-
exact, 525 cases, CI-required). D5 answers *"does a command reach an effect through the
REAL adapter — in-process (D5.1) and in a real guild (D5.2)?"* (integration/health signal,
structural, few cases, gated less often). D5.1 covers the adapter modules parity's fake
transport skips; D5.2 covers the gateway + real-Discord boundary neither parity nor D5.1
can reach. No golden is re-checked; no adapter path is double-owned.

Suggested landing order: **D5.1 hermetic → D5.1 discord-installed → D5.2 sweep → D5.2 CI
plumbing → D5.3 bridge**.

## Decision-ready refinement (2026-07-18)

A follow-up pass that grounds the proposal in the actual adapter imports and
splits the 7 questions into **agent-decidable design picks — resolved here as
flagged decide-and-flag defaults** (PL-001) and **genuinely owner-gated bits —
routed** to `docs/question-router.md`. No `D-00NN` token is minted: this stays a
plan; a decision homes in `docs/decisions.md` when a slice lands. Evidence is
`file:line` at HEAD `a50d1d0` unless noted.

### The central pick (Q1) — resolved: land D5.1 **discord-installed first**, not hermetic-fake-first

The proposal above (D5.1 bullet + sizing) leaned toward *"land the hermetic
feed/egress variant first (highest signal for the cost)."* Grounding that against
the real imports **revises the lean** — the adapter band splits into two classes,
not one:

- **Duck-typed ingress feeds (no module-scope `discord`):** `message_feed.py`
  says so verbatim — *"Duck-typed against discord.py (no discord import — the
  objects arrive from the gateway at runtime) … the token match mirrors the
  parity harness's `send_command`"* (`sb/adapters/discord/message_feed.py:35-41`);
  `component_feed.py` likewise carries no module-scope discord import. These are
  drivable **hermetically** with a synthetic event double — no fake `discord`
  module needed.
- **discord-object-constructing modules (guarded `import discord`):** `egress.py`
  builds real `discord.AllowedMentions` / `discord.Object`
  (`sb/adapters/discord/egress.py:2,30-42`), and `command_tree.py`,
  `panel_view.py`, `modal_view.py`, `confirm_view.py`, `responders.py` each import
  `discord` under the CI-absent guard and construct `discord.ui` / `app_commands`
  types (`sb/adapters/discord/{command_tree.py:33-41,panel_view.py:23-25,
  modal_view.py:25-27,confirm_view.py:38-40,responders.py:19-20}`). With
  `DISCORD_AVAILABLE=False` their discord-touching code is unreachable; to make it
  **execute** hermetically you must supply a fake `discord` providing
  `AllowedMentions`/`Object`/`ui.View`/`app_commands` with enough fidelity to
  assert on.

That fidelity requirement is the crux the original framing skated past. A fake
`discord` faithful enough to exercise egress serialization + panel/modal render is
**functionally a second `ParityPresenter`/`ParityTransport`** — i.e. rebuilding
the substitute-for-the-adapter that parity already has (`sb/adapters/parity/
boot.py:41-53`). Faking the library *beneath* the adapter to test the adapter is
circular: it proves "our code against our fake of discord," structurally the same
blind spot P1 names. So:

| Approach | Adapter modules actually exercised | Verdict |
|---|---|---|
| Hermetic, **no** fake `discord` lib | 2 of ~19 (the duck-typed feeds only) | cheap + real, but **does not close P1** |
| Hermetic **with** a fake `discord` lib | more, but against a re-derived fake | circular — **re-creates P1's blind spot** |
| **discord-installed** (real lib) | all target modules against real types | **closes P1**, rides a proven CI env |

**Default (decide-and-flag): make the discord-installed in-process tier the
headline D5.1**, riding the `golden-parity` named-gate environment. That
environment already exists and is proven for this exact boot: the gate installs
the full hash-pinned lock (`pip install --require-hashes -r requirements.lock`,
`.github/workflows/named-gates.yml:134`), which **already ships discord**
(`requirements.lock:218` → `discord-py==2.7.1`), and `tests/integration/` already
boots the very same `Harness.start()` there against a real Postgres service
(`tests/integration/conftest.py` docstring + `boot_harness()`). D5.1's driver is
the **non-replay twin** of that harness, so it slots in with **no new infra, no
secret, no token** (the boot uses the placeholder token
`DISCORD_BOT_TOKEN_PRODUCTION="PARITY_PLACEHOLDER_TOKEN"`,
`sb/adapters/parity/boot.py` `_ENV_DEFAULTS`, gateway-connect leg stubbed). The
"couples the gate to the lib" cost is *exactly the coverage being bought* —
catching an egress-serialization / panel-render / command-tree drift that only
manifests against real `discord` types is the whole point of P1.

**Kept as a cheap add-on, not the headline:** a narrow **hermetic feed-ingress
smoke** (synthetic `on_message` / component-click → `dispatch_prefix` /
`component_feed` → assert the sb-level dispatch fired) runs even in the
pyyaml-only `checkers` environment because `message_feed`/`component_feed` are
duck-typed. Worth landing as a fast pre-filter, but it touches neither egress nor
panel render, so it is the bonus tier — not the thing that turns the ~19 un-driven
modules into a gate.

### The other agent-decidable questions — resolved as decide-and-flag defaults

- **Q3 (which command set the LIVE sweep scripts) — DEFAULT: the minimal CUT-1
  boot-health shape** (boot → `/ready` 200 → one command → clean drain,
  `docs/decisions.md:372`), with the full hub sweep as an **owner-expandable**
  scope. A bounded first sweep keeps the guild uncluttered; breadth is a dial the
  owner turns once the LIVE tier exists. (The *shape* is agent-decidable; the
  breadth interacts with guild pollution + cost, which ride the owner-gated LIVE
  bundle.)
- **Q4 (pass/fail thresholds) — DEFAULT: non-blocking degraded-health**, mirroring
  the `verified_live` debt-list model (report reds, never block a merge,
  `tools/check_verified_live.py:14-17`). This falls out of LIVE being on-demand /
  owner-run rather than a required gate: a single non-response is a **reported
  red**, not a hard CI fail. Response bound: a per-command wait comfortably under
  the gateway READY bound of 75s (`sb/adapters/discord/gateway.py:44`
  `READY_TIMEOUT_S`) — e.g. 15s — flagged as tunable.
- **Q5 (rendered bytes vs structural) — DEFAULT: structural shape**, ratifying the
  proposal's own recommendation. Byte-exactness is golden-parity's job (525-case
  byte oracle); the live sweep is a health signal, so assert on panel field count
  / embed title / audit-row presence — robust to copy drift, not a second byte
  oracle.
- **Q7 (guild hygiene) — DEFAULT: post to a fixed tolerated channel**
  (`#bot-activity`-style, `docs/status/testing-report-2026-07-09.md:27`) for the
  first sweep — it needs no channel-effect port armed. The self-cleaning ephemeral
  per-run channel (needs the channel port, `sb/app/main.py:499-527`) is a stretch
  that rides on the LIVE tier existing (owner-gated anyway).

### The genuinely owner-gated bits — routed

The LIVE tier (D5.2) is owner-gated at its root and is **not** resolved here:

- **Q2** — provisioning a real bot **token** as a CI secret + a network-capable
  runner, the **cadence** (dispatch / nightly / weekly), and the **cost/time
  budget** (the container/session window is too tight for long serial live work,
  `docs/CAPABILITIES.md:110-122`).
- **Q6** — the **signer identity** for an auto-minted `verified_live` record (V2
  requires a signer + `signed_at` + `build_sha`,
  `tools/check_verified_live.py:9-12`): a bot identity is a trust/authority call.
  Recommended default *pending that ruling*: an automated sweep writes to a
  **separate non-signed lane** and leaves signing to the owner — but whether a bot
  identity may sign at all is owner-only.

These are appended as **one crisp OPEN block** in `docs/question-router.md` with
the recommended default: **in-process tier now; LIVE tier deferred until there's a
token + a reason.**

### What the in-process tier costs / unblocks — and the executable-follow-up flag

- **Unblocks:** it turns the ~19 real `sb/adapters/discord/*` modules — invisible
  to all 525 goldens (P1) and un-dispatched by the smoke gate (P2) — into a
  required, fast, deterministic CI gate, catching egress / component-id / panel /
  command-tree regressions that are byte-invisible today.
- **Cost:** a fake-gateway synthetic-event double + a driver cloning
  `sb/adapters/parity/boot.py`'s `Harness` contract — **M**, test/tooling code
  only (no `sb/` layer edge; the harness may import everything like `sb/app`).

> **▶ Recommended executable follow-up (buildable now, NO owner input):** the
> discord-installed in-process adapter tier (D5.1) can be **built and landed
> today without any owner decision or new infrastructure.** Evidence: the CI
> environment already exists and is proven (the `golden-parity` job installs the
> lock that ships `discord-py==2.7.1` and already boots the same `Harness.start()`
> against Postgres — `.github/workflows/named-gates.yml:134`,
> `requirements.lock:218`, `tests/integration/conftest.py`); the boot needs only
> the placeholder token already in `_ENV_DEFAULTS`; the tier-A pick is now decided
> (installed-first, above); and the new code is test/tooling with no layer edge.
> **This is a greenlight-ready build, deliberately NOT built in this docs slice —**
> the owner or the next agent can approve the D5.1 build directly. Only the LIVE
> tier (D5.2) waits on the routed owner questions.

## Open questions for the owner

> **Triage (2026-07-18, see "Decision-ready refinement" above):** Q1 / Q3 / Q4 /
> Q5 / Q7 are **agent-decidable** and now resolved as flagged decide-and-flag
> defaults there. Only the LIVE-tier root — **Q2** (token / cadence / cost) and
> **Q6** (signer identity) — is genuinely owner-gated and is routed to
> `docs/question-router.md`. The questions are retained verbatim below for the
> record.

1. **In-process discord dependency (D5.1's central call).** Hermetic **fake `discord`
   module** (stays in the pyyaml-only CI environment, proves only our code) vs
   **`discord.py` installed** in a dedicated job like `golden-parity`'s
   (`.github/workflows/named-gates.yml:134`) (exercises real library types, couples the
   gate to the lib)? Or both, at different tiers as proposed?
2. **How does the LIVE tier run, and how often?** A GitHub `workflow_dispatch` job holding
   `DISCORD_BOT_TOKEN_PRODUCTION` as a secret on a network-capable runner, an owner-local
   runbook run, or a scheduled cadence (nightly/weekly)? The container/session window is too
   tight for long serial live work (`docs/CAPABILITIES.md:110-122`), so what is the budget?
3. **Which command set does the LIVE sweep script?** The full hub set
   (`!help`/`!settings`/`!diagnostics`/`!setup` + a minigame + a role/channel effect), or a
   minimal boot-health smoke (boot → `/ready` 200 → one command → clean drain, the CUT-1
   shape, `docs/decisions.md:372`)? A curated list keeps the sweep bounded and the guild
   uncluttered.
4. **Pass/fail thresholds.** Is a single non-response a hard fail, or is the live tier a
   *degraded-health* signal (report reds, never block a merge — the `verified_live`
   debt-list model, `tools/check_verified_live.py:14-17`)? What response latency bounds a
   "no answer" (the gateway READY bound is 75s, `sb/adapters/discord/gateway.py:44`)?
5. **Assert on rendered bytes or structural shape?** Structural (panel field count, embed
   title, audit-row presence — robust to copy drift, recommended for a health sweep) vs
   byte-exact (strict, but partly redundant with golden-parity's byte oracle)?
6. **Does a green LIVE run mint a `verified_live` record automatically?** If so, who/what
   is the signer for an automated run (V2 requires a signer + `signed_at` + `build_sha`,
   `tools/check_verified_live.py:9-12`) — a bot identity, or does an automated sweep write
   only to a separate non-signed lane and leave signing to the owner?
7. **Guild hygiene.** Should the sweep post into a dedicated ephemeral test channel it
   creates + deletes per run (self-cleaning, needs the channel-effect port armed —
   `sb/app/main.py:499-527`), or a fixed `#bot-activity`-style channel the owner tolerates
   accumulating in (`docs/status/testing-report-2026-07-09.md:27`)?
