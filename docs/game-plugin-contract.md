# The game-plugin contract — out-of-tree games as installed plugins

> **Status:** `binding`
>
> Owner decision 2026-07-09 (fleet ORDER 002): each new game lives in its
> OWN repo as a plugin package the host consumes. This doc is the contract's
> one home (ledger: D-0056). Host side: `sb/app/plugin_host.py` +
> `tools/plugin_pin.py` + the committed `plugins.lock.json`. Working
> example: `examples/superbot-plugin-hello/` — the complete plugin package,
> seeded in-tree pending the owner-created `menno420/superbot-plugin-hello`
> repo (integration tokens cannot create repos; move it verbatim).

## 1. The shape of a plugin

A plugin is an installable Python distribution that exports **pure
declarations + ref registrations** — exactly the discipline of an in-tree
`sb/manifest/<key>.py` module (design-spec §1.1), just packaged out of tree:

```toml
# pyproject.toml (plugin repo)
[project.entry-points."sb.plugins"]
<name> = "<package>.manifest"        # the module the host imports
```

The module declares `MANIFEST = SubsystemManifest(...)` (or a `MANIFESTS`
tuple), registers every callable its specs reference through the
`sb.spec.refs` decorators (`@handler` / `@panel` / `@workflow` /
`@provider`), and exposes an idempotent `ENSURE_REFS` hook (the in-tree P1
re-arm contract). Importing the module IS reserving — the host performs the
import, never executes anything else from the plugin.

## 2. What a plugin may declare (v1)

Allowed `SubsystemManifest` facets: **commands, panels, settings
(+ bindings), events, capabilities.** They land on the same live seams the
in-tree subsystems use: the live dispatch index (prefix + slash, incl. the
test-guild slash sync), the K7 settings lanes and the settings hub, the K8
panel registry/engine, the ONE event bus.

Host-owned, refused at the gate in v1 (`plugin_gate` names the facet):

- **stores / data_invariants** — schema lives in the host's numbered
  migration chain and the S12 money lanes; a game needing its own table
  files a host PR (the out-of-tree store lane is a named successor).
- **wizard_sections** — the G-19 setup registry is host-curated.
- Also host-owned by construction: config fields (spec 05), hubs/operator
  spine, help **category mapping** (an unmapped plugin subsystem lands in
  the `Other 📦` help category — honest, never lost), adapters and the
  composition root, parity goldens (plugins have no shipped twin; the
  parity harness never loads plugins).

## 3. The kernel seams a plugin builds against

Import surfaces (all provided by the installed `sb` package):

- **Manifest grammar** — `sb.spec.manifest` / `commands` / `panels` /
  `settings` / `refs` / `confirmation`: the whole declarative surface.
- **Workflow spine** — route mutating commands at a `WorkflowRef` the
  plugin registers; the audited K7 engine (audit rows, outbox, confirm
  gates) is inherited, never reimplemented.
- **Economy** — the in-txn wager seams `sb/domain/games/wager.py`
  (`debit_floor_in_txn`, `escrow_pvp_in_txn`, `settle_pvp_in_txn`,
  `refund_pvp_in_txn`) and the economy service ports; balances/ledgers stay
  sole-writer host stores.
- **Game XP** — `sb/domain/games/xp.py` (`award_in_txn`, `shared_level`,
  the soft-cap rules).
- **Panels** — `PanelSpec` + `PanelRef` routes; the one kernel
  `PanelRuntimeView` renders plugin panels, nav slots included.
- **EffectiveStats** — named successor: the equipment/wear system it rides
  is a ledgered deferral (see the deathmatch/casino band entry); plugins get
  it when that port lands, nothing to import yet.

## 4. Packaging / import strategy

The host repo ships a `pyproject.toml` making the `sb` package
pip-installable (dist `superbot-next`; dependencies read dynamically from
`requirements.txt` — the lock stays the deployable truth). The documented
dependency pattern for plugin repos:

```
superbot-next @ git+https://github.com/menno420/superbot-next@<sha>
```

Pin a SHA/tag for reproducible dev. Inside the host's own environment
install the plugin with `pip install --no-deps <plugin>` (the host process
already provides `sb`). The installed dist supports manifest authoring and
unit tests; a full live boot still runs from a host-repo checkout
(migrations/, tools/, manifest.snapshot.json are deliberately unpackaged).

## 5. The pin lifecycle (hash-pinned like in-tree subsystems)

`plugins.lock.json` (repo root — the plugin twin of
`manifest.snapshot.json`) pins each plugin's canonical manifest hash
(sha256 over the same P8 serialization mechanics, scoped to the plugin).

1. Install the plugin into the host environment.
2. `python3 tools/plugin_pin.py --write` — validates (facet fence + ONE
   joint `compile_manifests` pass over host+plugins: namespace collisions,
   role tags, semantic predicates — same oracle, same failure taxonomy)
   and writes the pin. Commit it via a host PR: **the pin diff is the
   reviewable artifact.**
3. Boot (`sb/app/main.py` step 9b, deliberately AFTER boot-gate legs A/B —
   plugin refs must not leak into the in-tree recompile hash): entry-point
   discovery → pin verify → joint compile → registration on the live seams.

Verdicts: installed-but-unpinned or pin/installed **hash drift** ⇒
`FAILED_STARTUP (plugin_gate)` — the plugin twin of leg-A DRIFT.
Pinned-but-not-installed ⇒ warning + skip, never fatal (the registry is an
allowlist ceiling, not an install requirement — hermetic CI and plugin-free
containers boot unchanged). `python3 tools/plugin_pin.py` (no flag) gives
the same verdict as an ops CLI.

## 6. Successors (named, not started)

Out-of-tree store lane (per-plugin migrations under an owner-signed
disposition), typed slash options (inherited host successor), sim/layout
overlay lane for plugin panels, EffectiveStats (§3), version-range pins
(v1 pins one exact manifest hash — re-pin per release, deliberately).
