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
