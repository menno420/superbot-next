# superbot-plugin-hello

The **game-plugin-contract hello-world** for
[superbot-next](https://github.com/menno420/superbot-next): one command
(`!hello` / `/hello`) + one panel (`hello.home`), declared in this repo and
consumed by the host bot as an installed plugin.

The full contract (what a plugin may declare, which kernel seams it gets,
what stays host-owned, the pin/boot lifecycle) lives in the host repo:
`docs/game-plugin-contract.md`. This repo is the minimal working example new
game repos (mining, exploration/D&D, …) copy from.

## Shape

```
pyproject.toml                      # dist metadata + the sb.plugins entry point
superbot_plugin_hello/
  manifest.py                       # MANIFEST = SubsystemManifest(...) + ref registrations
tests/test_manifest.py              # authoring-time checks (needs the host dep)
```

The load-bearing part is the entry point:

```toml
[project.entry-points."sb.plugins"]
hello = "superbot_plugin_hello.manifest"
```

The host imports that module (importing IS reserving — the `@panel`
registration runs) and reads its `MANIFEST` attribute.

## Developing

Standalone (outside a host checkout):

```bash
pip install -e .[host]      # pulls superbot-next from git for the sb package
python -m pytest tests/ -q
```

Inside the host's environment (the bot container / a host repo checkout):

```bash
pip install --no-deps .    # the host process already provides sb
```

## Shipping into the host

1. Install the plugin into the host environment (above).
2. In the **host repo**: `python3 tools/plugin_pin.py --write` — computes this
   plugin's canonical manifest hash, runs the joint compile (namespace +
   semantic predicates over host+plugin), and writes `plugins.lock.json`.
3. Commit the pin via a host PR. At boot the host discovers the entry point,
   verifies the hash against the committed pin (drift ⇒ FAILED_STARTUP), and
   registers the manifest on the same live seams in-tree subsystems use —
   dispatch index, settings lanes, panel registry, slash-command tree.

Any change to `manifest.py`'s declared surface changes the hash: re-run step
2 and land the new pin deliberately. That is the point.
