# superbot-idle-plugin

The **idle-engine game plugin** for
[superbot-next](https://github.com/menno420/superbot-next): one command
(`!idle` / `/idle`) opening a status panel (`idle.status`), plus three
render-forwarding view commands (`idle status` / `idle shop` / `idle prestige`)
that forward the real idle-engine embed layer verbatim. It is the second
in-tree exemplar (after `examples/superbot-plugin-hello/`) and the first that
exercises live render forwarding — the coexistence proof that the host boots
more than one external plugin together with zero namespace collisions.

The full contract (what a plugin may declare, which kernel seams it gets, what
stays host-owned, the pin/boot lifecycle) lives in
`docs/game-plugin-contract.md`.

## Vendored — stopgap pending the split-out repo

This directory is **vendored from the `superbot-idle` repo's `main`** (its
`plugin/` adapter + the `idle_engine/` import closure the manifest pulls in),
mirroring how `superbot-plugin-hello` ships in-tree as the contract exemplar.
Specifically it tracks superbot-idle at the capability-3-part fix
(`superbot-idle` PR #85, commit `7814045`), which changed the manifest's
capability facet from the bare `("idle",)` to the host-required 3-part
`("idle.game.play",)`. The vendored `manifest.py` here **matches that fixed
copy** — that is the whole point of the fix: without it, the plugin cannot
compile against this host's namespace validator (`_CAPABILITY_PARTS=3`).

Once `superbot-idle`'s plugin is split into its own installable dist, this
in-tree vendored copy is replaced by a pip-installed dependency and this
directory is retired — same trajectory the hello exemplar sets for external
game repos.

## Shape

```
pyproject.toml                        # dist metadata + the sb.plugins entry point
superbot_idle_plugin/
  __init__.py
  manifest.py                         # MANIFEST = SubsystemManifest(...) + ref registrations
  render_forward.py                   # sb-free forwarders over idle_engine.render
idle_engine/                          # the vendored engine import closure (stdlib + PyYAML)
  __init__.py state.py achievements.py prestige.py upgrades.py
  engine.py theme.py economy.py render.py
```

The load-bearing part is the entry point:

```toml
[project.entry-points."sb.plugins"]
idle = "superbot_idle_plugin.manifest"
```

The host imports that module (importing IS reserving — the `@panel` / `@handler`
registrations run) and reads its `MANIFEST` attribute.

## Import closure

`manifest.py` → `render_forward.py` → `idle_engine.render`, and importing any
`idle_engine` submodule first imports `idle_engine/__init__` → `theme` →
`economy`. The vendored closure is the 9 modules above; `provisioning.py` and
`persistence.py` are NOT in the manifest's import closure and are deliberately
omitted. `idle_engine.theme` imports `PyYAML` (theme-pack loading) — a real
runtime dependency, satisfied by every host checkout (PyYAML is a core
superbot-next dependency) and declared in `pyproject.toml` for standalone use.

## Developing

Standalone (outside a host checkout):

```bash
pip install -e .[host]      # pulls superbot-next from git for the sb package
```

Inside the host's environment (the bot container / a host repo checkout):

```bash
pip install --no-deps .     # the host process already provides sb + PyYAML
```

## Shipping into the host

1. Install the plugin into the host environment (above).
2. In the **host repo**: `python3 tools/plugin_pin.py --write` — computes this
   plugin's canonical manifest hash, runs the joint compile (namespace +
   semantic predicates over host+plugins), and writes `plugins.lock.json`.
3. Commit the pin via a host PR. At boot the host discovers the entry point,
   verifies the hash against the committed pin (drift ⇒ FAILED_STARTUP), and
   registers the manifest on the same live seams in-tree subsystems use.

Any change to `manifest.py`'s declared surface changes the hash: re-run step 2
and land the new pin deliberately. That is the point.
