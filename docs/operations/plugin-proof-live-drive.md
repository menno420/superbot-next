# PLUGIN-PROOF LIVE-DRIVE RUNBOOK — the game-plugin contract, live seam

> **Status:** `reference` — the human-operator procedure for the LIVE parts of
> the game-plugin contract that a token + guild are required for. There is NO
> automated CI live-drive (no gateway token in CI). Wiring of record:
> `sb/app/plugin_host.py` (`load_plugins`) + `sb/app/main.py` step 9b
> (`:353-378`) + the contract `docs/game-plugin-contract.md`.
> Exemplar of record: `examples/superbot-plugin-hello`.

**Lane:** `plugin-boot-proof` · **Repo:** `menno420/superbot-next`
**Audience:** a human operator with the test bot's gateway token and a reachable
Postgres, driving the test plane + the single test guild named by
`SB_APPCMD_SYNC_GUILD_ID`. This is NOT a CI job.

---

## 0. TL;DR — what is proven WITHOUT a token, and what needs one

- **Proven headless, deterministically, in CI** (no token, no guild, no
  network): a REAL external plugin boots against the COMMITTED pin. The
  exemplar's manifest is discovered through a real `sb.plugins` entry point,
  pin-verified against `plugins.lock.json`, facet-fenced, joint-compiled with
  the in-tree corpus, and its `hello.home` panel registers. Coverage:
  - `tests/unit/app/test_plugin_boot_real_exemplar.py` (required via the
    `code-quality` pytest gate), and
  - `tools/check_runtime_smoke.py` (`plugin_boot_problems`, ORDER 016) — the
    same boot, run as the headless boot-and-wire gate.
- **NOT reachable without a live token** (this runbook's steps 1-4): actually
  pip-installing the plugin DIST into the live container, connecting the
  gateway, syncing the test guild's app-command tree, and dispatching
  `/hello` to see the panel render. These are owner/operator-gated: they need
  the test bot's gateway token (`AGENT_CONTAINER_ENV`, never in CI) and
  `SB_APPCMD_SYNC_GUILD_ID` set to the test guild. **Do not attempt them from
  an agent session** — there is no gateway token available to it.

The headless proof above and the live drive below are the SAME `load_plugins`
seam: the headless gate proves the manifest/pin/compile/register half
deterministically; the live drive below proves the last mile (real install +
slash-sync + dispatch) that only a connected gateway can exercise.

---

## 1. Pip-install the plugin dist into the live container

The headless proof loads the exemplar from the in-tree `examples/` path via a
constructed entry point. A LIVE boot instead discovers it through
`importlib.metadata.entry_points(group="sb.plugins")` — which requires the
dist to be actually INSTALLED in the container the bot runs in.

1. In the live container (test plane), install the plugin distribution:

   ```
   pip install superbot-plugin-hello        # or: pip install -e examples/superbot-plugin-hello
   ```

2. Confirm the entry point is discoverable (this is what `discover_plugins`
   reads at boot):

   ```
   python3 -c "import importlib.metadata as m; \
     print([ (e.name, e.value) for e in m.entry_points(group='sb.plugins') ])"
   # expect: [('hello', 'superbot_plugin_hello.manifest')]
   ```

3. Confirm the committed pin admits the INSTALLED dist (the exact boot-time
   `plugin_gate` verdict, run offline):

   ```
   python3 tools/plugin_pin.py
   # expect: "plugin_pin: green — 1 plugin(s) admitted: superbot-plugin-hello==0.1.0 [hello]"
   ```

   If this reds with a `manifest hash drift`, the installed dist's manifest
   diverges from the committed pin — STOP and re-pin deliberately
   (`python3 tools/plugin_pin.py --write`, review the one-line hash change,
   commit) before booting. (This is the exact latent bug the headless proof
   was built to catch.)

## 2. Boot with token + guild (test plane, double-gated)

4. Set the test-plane environment (the SAME double-gate `guild_sync_target`
   rides — `SB_DATA_PLANE == "test"` AND `SB_APPCMD_SYNC_GUILD_ID`):

   ```
   export SB_DATA_PLANE=test
   export SB_APPCMD_SYNC_GUILD_ID=<the test guild id>     # e.g. Superbot Admin
   export DISCORD_BOT_TOKEN_...=<the TEST bot gateway token>   # AGENT_CONTAINER_ENV; never CI
   # a reachable test-plane Postgres DSN as the app expects
   ```

   The production root stays UNARMED: a prod-plane boot leaves the guild
   sync target `None` by construction (`sb/app/main.py::guild_sync_target`).

5. Boot the app (`python3 -m sb.app.main` or the container entrypoint). Watch
   the step-9b plugin-host log line — it names the admitted plugin, the
   re-installed live index size, and the plugin panel count:

   ```
   plugin host: 1 plugin(s) admitted (superbot-plugin-hello==0.1.0 [hello]) —
     live index re-installed: N target(s), +1 plugin panel(s)
   ```

   A `plugin_gate` FAILED_STARTUP here means a pin/facet/compile violation —
   the boot refuses to connect the gateway (the plugin twin of a boot-gate
   leg-A failure). Resolve per §1 before retrying.

## 3. Confirm the test-guild slash-sync registers `/hello`

6. After the gateway connects and the app-command tree GUILD-syncs to
   `SB_APPCMD_SYNC_GUILD_ID`, confirm `/hello` appears in that guild's
   command list (Discord client → the test guild → type `/` → `hello` is
   present with the summary "Prove the game-plugin contract: open the hello
   panel."). The command originates from the plugin's `CommandSpec(name="hello",
   kind=CommandKind.BOTH, route=PanelRef("hello.home"))` — registered on the
   same live seam as every in-tree command because the joint compile folded
   it into the live manifests.

## 4. Dispatch `/hello` and see the `hello.home` panel

7. In the test guild, dispatch `/hello` (or the prefix form `!hello`). Expect
   the `hello.home` panel to render: title **"Hello from a plugin"** with the
   body confirming the plugin was declared out-of-tree and registered through
   the `sb.plugins` entry point. This is the live twin of the headless
   register proof (`get_panel("hello.home")` resolving after
   `register_manifest_panels`): here the panel engine actually renders it into
   the guild through the connected gateway.

8. Record the outcome (guild id, command list screenshot, panel render) in a
   session card, as the live-drive sessions do
   (`docs/operations/live-drive-guild-effects.md` precedent).

---

## 5. Honest scope

- Steps 1-4 need a LIVE gateway token (test bot) and a test guild — neither
  exists in CI (`docs/operations/live-drive-guild-effects.md` §1 enumerates
  the CI credential posture: no gateway token, `SB_VERIFY_BOOT` returns before
  any gateway is built). They are **owner/operator-gated**; an agent session
  must not attempt them.
- What an agent session CAN and DID prove is the headless half (§0): the real
  plugin boots against the committed pin and its panel registers, deterministically,
  in CI. The live drive above is the last mile a connected gateway alone can close.

---

## 6. The idle exemplar — coexistence + the three LIVE-ONLY seams

`examples/superbot-idle-plugin` (vendored from `superbot-idle`, see its
`README.md`) is the SECOND in-tree exemplar. Everything in §0's headless half
now proves it TOO, jointly with hello:

- `tests/unit/app/test_plugin_boot_real_exemplar.py::test_hello_and_idle_coexist`
  boots BOTH plugins in one `load_plugins` call against the committed pins
  (both rows of `plugins.lock.json`) and asserts `violations == ()`, both
  `hello` and `idle` admitted, and both panels (`hello.home`, `idle.status`)
  resolve after `register_manifest_panels`.
- `tools/check_runtime_smoke.py` (`plugin_boot_problems`) boots both exemplars
  together as the headless boot-and-wire gate.

That headless half proves **discovery + pin + facet-fence + joint compile +
panel register** for the two-plugin set. What it CANNOT prove — because idle,
unlike hello, forwards a live render layer, binds settings, and emits events —
are the three seams below. **All of §6 is owner/operator-gated: it needs the
test bot's gateway token + a reachable Postgres store + the test guild. Do NOT
attempt them from an agent session (no gateway token, no live store).** They
extend §1-§4 (install the `superbot-idle-plugin` dist, connect, guild-sync the
`/idle` command tree) — do those first for idle, then:

### 6a. Render forwarding — BLOCKED on an unbuilt host-side render state-injection adapter (Finding #2)

> **This seam is not merely operator-gated — it is host-code-BLOCKED.** The gap
> is NOT "a live render is the missing proof"; it is **missing host-side adapter
> code**. Do not treat §6a as attemptable once a gateway is available: even with
> a token, store, and guild, dispatching `/idle status` cannot render today,
> because the host lacks the adapter that builds `IdleRenderState` and calls the
> sync forwarder. This is **Finding #2 — host-owned, needs design.**

9. The idle view commands (`/idle status`, `/idle shop`, `/idle prestige`)
   route at `@handler` refs whose callables are the pure forwarders in
   `superbot_idle_plugin/render_forward.py`. Each is a **synchronous** function
   that takes an `IdleRenderState` handle — `(game_state, theme, now)`
   (`render_forward.py:56` `forward_status(state: IdleRenderState) -> dict`) —
   and returns a plain embed dict.

   **The blocker.** The host's `HandlerRef` dispatch path does not speak that
   signature. `sb/kernel/interaction/resolve.py:498-500` resolves the ref and
   does `await handler(req)`, passing a `ResolveRequest` and awaiting a
   workflow-result-shaped return. The idle forwarders are sync, take an
   `IdleRenderState` (not a `ResolveRequest`), and return a bare embed dict (not
   a workflow result). Nothing bridges the two. The missing piece is a
   **host-side render state-injection adapter** that (a) builds the
   `IdleRenderState` — the idle instance's `GameState` read off the host store,
   the resolved `Theme` pack, and the caller's unix `now` — and (b) adapts the
   sync forwarder's embed-dict return into what the resolve path expects. That
   adapter is **host-owned and UNBUILT**; idle's side (the byte-identical
   forwarder over `idle_engine.render`) is complete and is all idle can own.

   Until that adapter exists, live idle render dispatch is **blocked** — this
   step is not runnable, gateway or no gateway. Building the adapter is a
   host-side design task (Finding #2), out of scope for the plugin re-vendor.

10. (Deferred with step 9.) Once the Finding #2 adapter lands, this step covers
    `/idle shop` and `/idle prestige`: confirm each renders the engine's real
    view, or the documented empty-state when the loaded pack declares no
    `upgrades` / `prestige` block (the forwarder returns `None` — the host
    adapter must handle that, not the plugin).

### 6b. Settings live binding + persistence — the host store

11. The manifest declares four settings bound by `settings_key`:
    `idle.pack` (str theme-id) and the three ON-by-default bool toggles
    `idle.offline_progress` / `idle.upgrades` / `idle.prestige`. Live-set one
    (e.g. toggle `idle.upgrades` off) through the host's settings lane, then
    confirm it PERSISTS across a bot restart by reading it back. Persistence is
    HOST-OWNED — the plugin declares no `stores`/`data_invariants` (v1 facet
    fence), so this proves the host store binds and round-trips the plugin's
    setting keys. No headless test can prove round-trip through a live store.

### 6c. Event emission — the idle lifecycle

12. The manifest declares two observability-only events: `idle.tick` (payload
    `subsystem_key` / `now` / `elapsed_s`) and `idle.offline_return`
    (`subsystem_key` / `last_seen` / `now` / `gains`). With a live runtime
    driving the idle loop, confirm an `idle.tick` is emitted on a tick and an
    `idle.offline_return` on a returning player's offline-credit event, and
    that a subscriber on the live bus observes each with the declared payload
    shape. Emission requires the running idle loop + the live event bus —
    neither exists headless.

13. Record the outcome (guild id, the three seams' results, restart-persistence
    check) in a session card, as §4 step 8 does for hello.

### 6d. Honest scope (idle)

- §6b-§6c are idle-specific live seams that are **operator-gated**: like §1-§4
  they need a gateway token + a reachable store + the test guild, none of which
  exist in CI. An agent session must not attempt them, but they ARE runnable on
  a connected host.
- §6a is different: it is **host-code-blocked**, not merely operator-gated (see
  the callout at §6a). No gateway can run it until the host-side render
  state-injection adapter is built (Finding #2, host-owned, needs design).
- What an agent session CAN and DID prove for idle is the coexistence headless
  half: idle boots against its committed pin ALONGSIDE hello with zero
  violations, and `idle.status` registers. The settings store round-trip and the
  event emission are the last mile a connected gateway + live store can close;
  the render-forward *dispatch* additionally waits on the Finding #2 host adapter.

### 6e. Known live-boot blockers — idle source findings (as of the re-vendor)

Three findings were raised against idle's LIVE-boot path (all authentic, all
real, all live-path — idle's sb-free CI never exercised any of them). Their
status as of this re-vendor PR:

- **Finding #1 — events not registered (P2): FIXED at idle source.** The
  manifest declared `EVENTS = (idle.tick, idle.offline_return)` but never called
  `register_event_specs`, so they never entered `KNOWN_EVENTS` at runtime. Fixed
  by calling `register_event_specs(list(EVENTS))` at module import AND in
  `_ensure_refs` (mirroring `sb/manifest/xp.py:165,180`); idempotent. Vendored
  here via the byte-identical re-vendor + re-pin.
- **Finding #3 — `/idle` declared as BOTH a root command AND a group (P1): FIXED
  at idle source.** `register_app_commands` built both a standalone `idle` slash
  Command and an `idle` slash Group ⇒ discord.py `CommandAlreadyRegistered`,
  failing live startup before the gateway. Fixed by making the root `idle`
  command PREFIX-only, so the slash surface is exactly `/idle status|shop|prestige`
  and `!idle` + the panel are preserved. Vendored here.
- **Finding #2 — render-forward dispatch seam (host-owned): REMAINS, needs
  design.** The `HandlerRef`→forwarder state-injection adapter is host-side and
  UNBUILT (`resolve.py:498-500` awaits `handler(req)` with a `ResolveRequest`;
  the forwarders are sync and expect `IdleRenderState`, `render_forward.py:56`).
  This is NOT an idle-source bug and is NOT fixed here; see §6a. It blocks live
  idle render dispatch until the host builds the adapter.
