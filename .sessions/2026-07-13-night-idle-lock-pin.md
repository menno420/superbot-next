# 2026-07-13 — night: host-side idle plugin pin (ORDER 019 item 6)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN cross-repo slice · mandate:
  ORDER 019 item 6 — host-side `plugins.lock.json` pin for the REAL
  out-of-tree superbot-idle plugin adapter, closing superbot-idle's
  live wiring gap per its `control/status.md` Next-3 item 1 @ `1f4d774`.

## Scope

Pin the real superbot-idle repo's `plugin/` adapter (dist
`superbot-idle-plugin`, entry point `idle = superbot_idle_plugin.manifest`)
in the committed pin registry `plugins.lock.json`, the way
`tools/plugin_pin.py --write` would write it — installed-but-unpinned is
the plugin twin of leg-A DRIFT (`sb/app/plugin_host.py:241-251`), so
without a host-side pin the real adapter boot-fails at step 9b.

Cross-repo read-only evidence source: menno420/superbot-idle (public),
shallow-cloned to the scratchpad; all writes land in this repo only.

## Verification (in progress)

- superbot-idle `control/status.md` Next-3 read at idle HEAD `a6906b9`
  (1f4d774 confirmed in history): "1. Host-side `plugins.lock.json` pin
  for the idle adapter (a superbot-next PR, via that lane)."
- Hash source: `sb/app/plugin_host.py` `manifest_stable_hash` — sha256
  over the canonical P8 serialization scoped to the plugin's manifests.

(Flip to `complete` with the verdict + evidence at close-out.)
