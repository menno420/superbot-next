"""Headless boot proof for the game-plugin contract — the REAL in-tree
exemplar (``examples/superbot-plugin-hello``) booted deterministically
against the COMMITTED ``plugins.lock.json`` pin.

The sibling ``test_plugin_host.py`` is hermetic-by-design: synthetic
manifests + fake entry points, no real plugin, no committed pin. It proves
the host *mechanics* (discovery, the pin gate, the facet fence, the joint
compile) but NOTHING boots a real external plugin — a stale committed pin,
or a real manifest the joint compile rejects, sails straight through it.

This module closes that gap. It runs the SAME ``load_plugins`` call the
composition root makes at ``sb/app/main.py`` step 9b, minus a pip install:

  - the in-tree corpus is imported FIRST (``load_live_manifests`` — the
    leg-A order: importing a plugin before the host corpus is armed would
    invert the real boot sequence);
  - the plugin is a REAL ``sb.plugins`` entry point whose ``.load()``
    imports the actual ``superbot_plugin_hello.manifest`` module (import ==
    ref registration), exactly what ``importlib.metadata`` hands the host
    for the pip-installed dist — the transport is faked, the manifest and
    the committed pin are the genuine artifacts under test;
  - the pin is the COMMITTED registry read through
    ``plugin_host.read_pins`` — NOT a synthesized pin. Proving the checked-in
    ``plugins.lock.json`` matches the real manifest is the whole point (a
    stale pin reds ``test_committed_pin_matches_real_manifest`` and the boot
    below with a ``manifest hash drift`` violation).

The proof: the committed pin admits the real manifest with ZERO violations
(entry-point discovery + pin verify + v1 facet fence + the joint
host+plugin compile), the ``hello`` subsystem lands in the report, and the
panel the manifest declares (``hello.home``) resolves through the live
panel registry after ``register_manifest_panels`` — the register seam a
real dispatch of ``/hello`` hits.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXEMPLAR_ROOT = _REPO_ROOT / "examples" / "superbot-plugin-hello"

# The exemplar lives in-tree but is NOT an installed dist; put its package
# root on the path so ``superbot_plugin_hello`` imports (a conftest would do
# the same — kept in-module so the proof is self-contained and legible).
if str(_EXEMPLAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXEMPLAR_ROOT))

from sb.app import plugin_host  # noqa: E402
from sb.app.main import load_live_manifests  # noqa: E402
from sb.app.panel_host import register_manifest_panels  # noqa: E402
from sb.kernel.panels.registry import clear_panels_for_tests, get_panel  # noqa: E402

_HELLO_MODULE = "superbot_plugin_hello.manifest"
_HELLO_DIST = "superbot-plugin-hello"
_HELLO_VERSION = "0.1.0"
_HELLO_KEY = "hello"
_HELLO_PANEL = "hello.home"


class _RealDist:
    """The ``.dist`` shape ``importlib.metadata`` attaches to an entry
    point (name + version — the diagnostics the host reads)."""

    name = _HELLO_DIST
    version = _HELLO_VERSION


class _RealEntryPoint:
    """A REAL ``sb.plugins`` entry point for the in-tree exemplar: ``.load()``
    imports the actual manifest module (import == ref registration), exactly
    as ``importlib.metadata.entry_points(group="sb.plugins")`` would for the
    pip-installed dist. Only the *transport* is constructed — the module,
    its ``MANIFEST``, and the committed pin are the genuine artifacts."""

    name = _HELLO_KEY
    value = _HELLO_MODULE
    dist = _RealDist()

    def load(self):
        return importlib.import_module(_HELLO_MODULE)


def _hello_manifest_module():
    """Import the exemplar and re-arm its refs. ``ENSURE_REFS`` is idempotent
    and survives a test-seam ref-table clear (the module body's first-import
    registration would NOT re-run for the cached module, and the host's own
    re-arm hook only re-arms ``sb.manifest.*`` — not plugins)."""
    module = importlib.import_module(_HELLO_MODULE)
    ensure = getattr(module, "ENSURE_REFS", None)
    if callable(ensure):
        ensure()
    return module


def _committed_pins() -> dict:
    return plugin_host.read_pins(_REPO_ROOT / plugin_host.PINS_FILENAME)


@pytest.fixture(autouse=True)
def _clean_panel_registry():
    """The panel registry is process-global; keep this proof from leaking
    ``hello.home`` into a sibling test's inventory (and start clean)."""
    clear_panels_for_tests()
    yield
    clear_panels_for_tests()


@pytest.fixture
def boot_report() -> plugin_host.PluginReport:
    """The real step-9b boot: in-tree corpus armed FIRST, then the plugin
    loaded against the committed pin (main.py's exact ordering + call)."""
    host_manifests = load_live_manifests()
    _hello_manifest_module()
    return plugin_host.load_plugins(
        host_manifests,
        pins=_committed_pins(),
        entry_points=(_RealEntryPoint(),),
    )


def test_committed_pin_matches_real_manifest():
    """The committed ``plugins.lock.json`` hash IS the real manifest's
    canonical hash — the explicit, legible form of the boot proof (a stale
    pin, e.g. after a CommandSpec facet grows without a re-pin, reds here)."""
    module = _hello_manifest_module()
    pinned = _committed_pins()["plugins"][_HELLO_DIST]["manifest_hash"]
    actual = plugin_host.manifest_stable_hash((module.MANIFEST,))
    assert actual == pinned, (
        f"committed pin {pinned} != real manifest hash {actual} — the "
        "checked-in plugins.lock.json is stale; re-pin the exemplar "
        "(`python3 tools/plugin_pin.py --write` with it pip-installed)")


def test_real_exemplar_boots_headless_with_zero_violations(boot_report):
    """The genuine ``load_plugins`` verdict: the real entry point, the real
    manifest, the committed pin, and the joint host+plugin compile all admit
    the plugin with NO violations (the plugin twin of a green boot gate)."""
    assert boot_report.violations == (), boot_report.violations
    assert boot_report.loaded == (
        f"{_HELLO_DIST}=={_HELLO_VERSION} [{_HELLO_KEY}]",)
    assert boot_report.skipped == ()


def test_admitted_report_carries_the_hello_subsystem(boot_report):
    """The ``hello`` manifest is in the admitted set the composition root
    would fold into the live manifests."""
    keys = {getattr(m, "key", None) for m in boot_report.manifests}
    assert _HELLO_KEY in keys, keys


def test_plugin_panel_registers_and_resolves(boot_report):
    """Register proof: after ``register_manifest_panels`` (the step-9b seam),
    the panel the manifest declares resolves through the live registry — the
    exact lookup a dispatched ``/hello`` performs to open its panel."""
    assert boot_report.violations == (), boot_report.violations
    registered = register_manifest_panels(list(boot_report.manifests))
    assert registered >= 1
    panel = get_panel(_HELLO_PANEL)
    assert panel.panel_id == _HELLO_PANEL
    assert panel.subsystem == _HELLO_KEY
