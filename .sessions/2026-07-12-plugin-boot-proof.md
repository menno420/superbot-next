# 2026-07-12 — plugin-boot proof: a REAL external plugin booted headless + deterministically, and the stale hello pin refreshed

> **Status:** `complete`

- **📊 Model:** builder-agent · high · latent-bug fix + headless boot proof (Q-0194)

## Scope

The game-plugin contract (ORDER 002; `docs/game-plugin-contract.md`) has a
host (`sb/app/plugin_host.py`), an in-tree exemplar
(`examples/superbot-plugin-hello`), a committed pin registry
(`plugins.lock.json`), and a composition-root boot call (`sb/app/main.py`
step 9b). What it did NOT have was a gate that boots a REAL external plugin:
`tests/unit/app/test_plugin_host.py` is hermetic-by-design — synthetic
manifests + fake entry points, no committed pin, no real manifest — so a
stale pin or a real manifest the joint compile rejects sails straight
through it. `tools/check_runtime_smoke.py` (the ORDER 016 headless
boot-and-wire gate) boots the in-tree corpus but had ZERO plugin refs.

One bounded slice: prove a real external plugin boots headless +
deterministically against the committed pin, and fix the latent stale-pin
bug that boot proof surfaced.

## The stale-pin diagnosis (VERIFIED, not assumed)

The committed pin for `superbot-plugin-hello` was
`sha256:06023075…`; the real manifest hashes to `sha256:ff75b9eb…`
(`plugin_host.manifest_stable_hash`). So `load_plugins` reds the exemplar
with `manifest hash drift → FAILED_STARTUP` — a latent bug: the in-tree
exemplar cannot boot against its own committed pin.

WHY they diverged (not a deliberate freeze — re-pin is correct):

- `git log --oneline -- plugins.lock.json` and `-- examples/superbot-plugin-hello/`
  each show ONE commit: both files were BORN TOGETHER in `d71ed18` (#75,
  the contract v1 seed). Neither file has been touched since.
- At `d71ed18`, using #75's own code, the manifest hashed to
  `sha256:06023075…` — i.e. **the pin was CORRECT when it was committed.**
- The drift came LATER, from a legit spec-evolution commit that changed the
  serialized manifest surface without re-pinning the exemplar. Bisecting the
  hashing surface (`git log d71ed18..HEAD -- tools/manifest_compile.py
  sb/spec/{panels,commands,manifest,refs,roles}.py`) over three candidates,
  the hash flips at **`9b9a322` (#232, "band7: CommandSpec modal facet")**:
  parent `4024624` → `06023075…`; `9b9a322` → `ff75b9eb…`. #232 added the
  `modal: ModalSpec | None` field (plus `slash_common`/`defer_mode`/
  `cooldown`) to `CommandSpec`; `serialize_manifest` is duck-typed over
  declared fields, so the hello command's serialization grew the new field
  and the hash moved — the exemplar's pin was never refreshed.

This is unambiguously the NORMAL "manifest surface changed without a re-pin
→ re-pin is correct" case (an in-tree exemplar's pin frozen deliberately
would be nonsensical). Re-pinned; the pin is a pure function of the plugin's
own declared surface, not the process ref table (`manifest_stable_hash`
docstring), so the refresh is deterministic.

## Delivered

- `tests/unit/app/test_plugin_boot_real_exemplar.py` — the headless proof.
  Imports the REAL `superbot_plugin_hello.manifest` via a constructed
  `sb.plugins` entry point whose `.load()` imports the actual module (import
  == ref registration; only the transport is faked), reads the COMMITTED
  `plugins.lock.json` through `plugin_host.read_pins`, and runs the exact
  `load_plugins(load_live_manifests(), pins=committed, entry_points=(ep,))`
  the composition root makes at main.py step 9b (in-tree corpus armed FIRST
  — the leg-A order). Asserts: committed pin == real manifest hash; zero
  violations; the `hello` subsystem is admitted; and `hello.home` resolves
  through the live panel registry after `register_manifest_panels` (the
  register seam a dispatched `/hello` hits). Born RED against the stale pin
  (4/4 failed with the `manifest hash drift` violation), GREEN after re-pin.
- `plugins.lock.json` — re-pinned `superbot-plugin-hello` manifest_hash
  `06023075…` → `ff75b9eb…` via `python3 tools/plugin_pin.py --write` (the
  exemplar pip-installed editable so the tool's installed-set discovery
  finds it). Only the hash line changed; verify is green (1 plugin admitted).
- `tools/check_runtime_smoke.py` — extended the ORDER 016 headless gate:
  after the in-tree W-rules it now boots the real hello exemplar via a
  constructed entry point against the committed pin (`plugin_boot_problems`),
  asserting zero violations + `hello.home` registers. Appended AFTER the
  in-tree wiring — the main.py step-9b ordering — so the plugin's refs never
  leak into leg-A's corpus hash. This is the designated home for
  "static-green-but-boot-broken" catches.
- `docs/operations/plugin-proof-live-drive.md` — the operator runbook for
  the LIVE parts the headless proof cannot reach (pip-install the dist, boot
  with token+guild, confirm `/hello` slash-syncs, dispatch it). Owner-gated;
  not attempted here.

## Evidence

- born-red: `pytest tests/unit/app/test_plugin_boot_real_exemplar.py` →
  4 failed against the stale pin (each with the `manifest hash drift`
  violation). Committed red-first.
- green after re-pin: same file → 4 passed.
- pin verify: `python3 tools/plugin_pin.py` → green, 1 plugin admitted
  (`superbot-plugin-hello==0.1.0 [hello]`).
- smoke gate: `python3 tools/check_runtime_smoke.py` → clean, boots the
  hello exemplar with zero violations.
- full: `python3 bootstrap.py check --strict` + `pytest tests/ -q` — tails
  pasted in the PR body.

## Codex

Question posted on the PR head per the directive.

## 💡 Session idea

The re-pin was needed because a spec-facet change (#232's CommandSpec
`modal`) drifted the exemplar's manifest hash with no signal until someone
boots the plugin. A cheap guard: have the CommandSpec/PanelSpec facet-growth
checker (or a `plugin_pin` verify wired into a non-hermetic lane) flag when
the in-tree exemplar's committed pin diverges from a freshly-computed hash —
the exemplar is the one plugin the host repo can hash without an install, so
its pin can be verified in CI (this PR wires exactly that into the smoke
gate; the follow-up is generalizing it to any spec-surface change).

## ⟲ Previous-session review

The recon that framed this slice was precise: it named the stale hashes,
the host seams, and the born-red discipline up front, which made the build a
straight execution. What it left open — correctly, as a "confirm before
fixing" — was WHY the pin diverged; deriving that (born-correct at #75,
drifted by #232's facet growth, never re-pinned) is what confirmed re-pin
was the right move over freezing, and is now the diagnosis of record above.
