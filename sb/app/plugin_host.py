"""The plugin host — out-of-tree game plugins join the live manifests
(ORDER 002 game-plugin contract, host side; docs/game-plugin-contract.md).

Each game lives in its OWN repo as an installable package exporting a
``SubsystemManifest`` through the ``sb.plugins`` entry-point group (owner
decision 2026-07-09). The host consumes it with the SAME discipline the
in-tree manifests get:

  - **declaring IS reserving**: loading the entry point imports the plugin's
    manifest module, so its ``@handler``/``@panel``/``@provider`` decorators
    register refs exactly like an ``sb.manifest.*`` import (design-spec §3.2);
  - **hash-pinned like in-tree subsystems**: the committed registry
    ``plugins.lock.json`` (repo root, the plugin twin of
    ``manifest.snapshot.json``) pins each plugin's canonical manifest hash;
    an installed-but-unpinned plugin or a pin/installed hash mismatch is
    the plugin twin of boot-gate leg-A DRIFT → FAILED_STARTUP;
  - **compiled like in-tree subsystems**: admitted plugin manifests run one
    JOINT ``compile_manifests(manifests=host+plugins)`` pass (P1–P8) so
    namespace collisions, role tags, and the semantic predicates hold over
    the union — same oracle, same failure taxonomy.

A plugin that is PINNED but not INSTALLED is skipped with a warning, never
fatal: the pin registry is an allowlist ceiling, not an install requirement
(hermetic CI and plugin-free containers must keep booting — the committed
snapshot/gates never depend on what happens to be pip-installed).

Boot-order contract (sb/app/main.py step 9b): plugins load AFTER boot-gate
legs A/B. Both legs hash the IN-TREE corpus, and the compiled snapshot's
``projections.refs`` section is the module-global ref table — importing a
plugin before the recompile would leak its refs into the hash and red a
green tree. v1 facet fence: plugins may declare commands / panels /
settings / events / capabilities; stores, data_invariants and
wizard_sections stay host-owned (migrations, S12 money lanes, and the G-19
setup registry have no out-of-tree lane yet — the contract doc names the
successors).

Like ``sb/app/boot_gate.py``, this is composition-root code (may import
tools/ machinery).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("sb.app.plugin_host")

__all__ = [
    "ALLOWED_FACETS",
    "DiscoveredPlugin",
    "HOST_ONLY_FACETS",
    "PINS_FILENAME",
    "PINS_SCHEMA_VERSION",
    "PLUGIN_GROUP",
    "PluginReport",
    "build_pins",
    "discover_plugins",
    "load_plugins",
    "manifest_stable_hash",
    "read_pins",
]

#: The entry-point group a plugin exports its manifest module through.
PLUGIN_GROUP = "sb.plugins"

#: The committed pin registry (repo root — the plugin twin of
#: manifest.snapshot.json). Written by ``tools/plugin_pin.py --write``.
PINS_FILENAME = "plugins.lock.json"
PINS_SCHEMA_VERSION = 1

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: v1 contract: the SubsystemManifest facets an out-of-tree plugin may
#: declare / the facets that stay host-owned (docs/game-plugin-contract.md).
ALLOWED_FACETS: tuple[str, ...] = (
    "commands", "panels", "settings", "events", "capabilities",
)
HOST_ONLY_FACETS: tuple[str, ...] = (
    "stores", "data_invariants", "wizard_sections",
)


@dataclass(frozen=True)
class DiscoveredPlugin:
    """One installed distribution advertising an ``sb.plugins`` entry point."""

    dist_name: str
    version: str
    entry_point: str                   # "name = module:attr" (diagnostics)
    manifests: tuple                   # its exported SubsystemManifest objects


@dataclass(frozen=True)
class PluginReport:
    """The load verdict the composition root consumes."""

    manifests: tuple                   # admitted manifest objects (key-sorted)
    loaded: tuple[str, ...]            # "dist==version [keys]" summaries
    skipped: tuple[str, ...]           # pinned-but-not-installed dist names
    violations: tuple[str, ...]        # any entry ⇒ FAILED_STARTUP


def read_pins(path: Path | None = None) -> dict:
    """The committed pin registry; a missing file is the empty registry."""
    pins_path = path if path is not None else _REPO_ROOT / PINS_FILENAME
    if not pins_path.exists():
        return {"schema_version": PINS_SCHEMA_VERSION, "plugins": {}}
    return json.loads(pins_path.read_text(encoding="utf-8"))


def manifest_stable_hash(manifests: tuple | list) -> str:
    """sha256 over the canonical serialization of the plugin's manifests.

    Deliberately NOT ``compile_manifests(...).stable_hash``: the full
    snapshot's ``projections.refs`` section is the module-global ref table,
    so that hash would drift with whatever else the process has imported.
    This hash is a pure function of the plugin's own declared surface —
    the same ``_serialize`` + ``canonical_json`` mechanics the in-tree
    snapshot pin uses, scoped to the plugin (spec 01 §5 determinism)."""
    from tools.manifest_compile import canonical_json, serialize_manifest

    body = {
        str(getattr(m, "key", "?")): serialize_manifest(m)
        for m in manifests
    }
    digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _entry_points(group: str):
    import importlib.metadata

    return importlib.metadata.entry_points(group=group)


def discover_plugins(entry_points=None, *,
                     errors: list[str] | None = None) -> tuple[DiscoveredPlugin, ...]:
    """Load every ``sb.plugins`` entry point (import = ref registration) and
    collect the exported MANIFEST / MANIFESTS objects. A raising entry point
    becomes a violation string in ``errors`` (never a crash — the caller
    decides the verdict), mirroring the compiler's P1 collect-all posture."""
    if entry_points is None:
        entry_points = _entry_points(PLUGIN_GROUP)
    found: list[DiscoveredPlugin] = []
    for ep in entry_points:
        ep_label = f"{getattr(ep, 'name', '?')} = {getattr(ep, 'value', '?')}"
        dist = getattr(ep, "dist", None)
        dist_name = str(getattr(dist, "name", None) or getattr(ep, "name", "?"))
        version = str(getattr(dist, "version", None) or "unknown")
        try:
            module = ep.load()
        except Exception as exc:  # noqa: BLE001 — a broken plugin is a verdict
            if errors is not None:
                errors.append(f"{dist_name}: entry point {ep_label!r} "
                              f"raised on load: {exc!r}")
            continue
        manifests: list = []
        declared = getattr(module, "MANIFEST", None)
        if declared is not None:
            manifests.append(declared)
        manifests.extend(getattr(module, "MANIFESTS", ()) or ())
        found.append(DiscoveredPlugin(
            dist_name=dist_name, version=version, entry_point=ep_label,
            manifests=tuple(manifests)))
    return tuple(sorted(found, key=lambda p: p.dist_name))


def _facet_violations(plugin: DiscoveredPlugin) -> list[str]:
    out: list[str] = []
    for manifest in plugin.manifests:
        key = getattr(manifest, "key", "?")
        for facet in HOST_ONLY_FACETS:
            if getattr(manifest, facet, ()) or ():
                out.append(
                    f"{plugin.dist_name}: manifest {key!r} declares the "
                    f"host-owned facet {facet!r} — v1 contract allows "
                    f"{', '.join(ALLOWED_FACETS)} only "
                    "(docs/game-plugin-contract.md)")
    return out


def build_pins(plugins: tuple[DiscoveredPlugin, ...]) -> dict:
    """The pin-registry document for an installed plugin set
    (``tools/plugin_pin.py --write`` renders + commits this)."""
    return {
        "schema_version": PINS_SCHEMA_VERSION,
        "plugins": {
            p.dist_name: {
                "version": p.version,
                "subsystems": sorted(str(getattr(m, "key", "?"))
                                     for m in p.manifests),
                "manifest_hash": manifest_stable_hash(p.manifests),
            }
            for p in plugins
        },
    }


def _arm_imported_host_refs() -> None:
    """Idempotently re-run ``ENSURE_REFS`` on every ALREADY-IMPORTED
    ``sb.manifest.*`` module — the P1 hook the injection-mode joint compile
    bypasses (several in-tree manifests register their refs only through
    it). Scans ``sys.modules`` and never imports: at boot the leg-A/leg-B
    package compiles already imported everything, and unit tests driving
    synthetic manifests stay hermetic (no manifest package import)."""
    import sys

    for name, module in list(sys.modules.items()):
        if not name.startswith("sb.manifest.") or module is None:
            continue
        hook = getattr(module, "ENSURE_REFS", None)
        if callable(hook):
            hook()


def load_plugins(host_manifests: list, *, pins: dict | None = None,
                 entry_points=None) -> PluginReport:
    """Discover, pin-verify, facet-fence, and jointly compile the installed
    plugin set against the host manifests. Any violation ⇒ the composition
    root fails startup (``plugin_gate``); zero installed plugins with zero
    pins is the vacuously-green path every plugin-free container takes."""
    violations: list[str] = []
    loaded: list[str] = []
    admitted: list = []

    pins_doc = pins if pins is not None else read_pins()
    pin_rows = dict(pins_doc.get("plugins") or {})
    discovered = discover_plugins(entry_points, errors=violations)

    for plugin in discovered:
        pin = pin_rows.pop(plugin.dist_name, None)
        if not plugin.manifests:
            violations.append(
                f"{plugin.dist_name}: entry point {plugin.entry_point!r} "
                "exports no MANIFEST/MANIFESTS")
            continue
        violations.extend(_facet_violations(plugin))
        if pin is None:
            violations.append(
                f"{plugin.dist_name}: installed but NOT pinned in "
                f"{PINS_FILENAME} — the plugin twin of leg-A DRIFT (run "
                "`python3 tools/plugin_pin.py --write` and commit the pin)")
            continue
        actual = manifest_stable_hash(plugin.manifests)
        pinned = pin.get("manifest_hash")
        if actual != pinned:
            violations.append(
                f"{plugin.dist_name}: manifest hash drift — pinned {pinned} "
                f"!= installed {actual} (re-pin deliberately: "
                "`python3 tools/plugin_pin.py --write`)")
            continue
        admitted.extend(plugin.manifests)
        keys = ", ".join(str(getattr(m, "key", "?")) for m in plugin.manifests)
        loaded.append(f"{plugin.dist_name}=={plugin.version} [{keys}]")

    skipped = tuple(sorted(pin_rows))

    if admitted and not violations:
        from tools.manifest_compile import compile_manifests

        _arm_imported_host_refs()
        result = compile_manifests(
            manifests=list(host_manifests) + list(admitted))
        for v in result.violations:
            violations.append(
                f"joint compile {v.failure_class} ({v.pass_name}) "
                f"{v.locus}: {v.detail}")

    admitted.sort(key=lambda m: str(getattr(m, "key", "")))
    return PluginReport(
        manifests=tuple(admitted) if not violations else (),
        loaded=tuple(loaded),
        skipped=skipped,
        violations=tuple(violations),
    )
