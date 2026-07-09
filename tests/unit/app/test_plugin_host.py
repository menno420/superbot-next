"""The plugin host (sb/app/plugin_host.py) — the game-plugin contract's
host side, hermetically: synthetic manifests + fake entry points only (no
plugin installed in CI, no ``sb.manifest`` package import — the roster-free
test discipline). Covers discovery, the pin gate (unpinned / drift /
pinned-but-absent), the v1 facet fence, the joint-compile collision fence,
and pin-hash determinism."""

from __future__ import annotations

import json
from types import SimpleNamespace

from sb.app import plugin_host
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.versioning import StoreSpec


def _manifest(key: str, command: str, *, stores: tuple = ()) -> SubsystemManifest:
    return SubsystemManifest(
        key=key,
        commands=(CommandSpec(name=command, kind=CommandKind.PREFIX,
                              summary=f"{key} test command"),),
        stores=stores,
    )


class _Dist:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version


class _EntryPoint:
    def __init__(self, name: str, value: str, module: object,
                 dist: _Dist | None = None,
                 raises: Exception | None = None) -> None:
        self.name = name
        self.value = value
        self.dist = dist
        self._module = module
        self._raises = raises

    def load(self) -> object:
        if self._raises is not None:
            raise self._raises
        return self._module


def _ep(dist_name: str, manifest: SubsystemManifest,
        version: str = "1.0.0") -> _EntryPoint:
    module = SimpleNamespace(MANIFEST=manifest)
    return _EntryPoint(dist_name.split("-")[-1],
                       f"{dist_name.replace('-', '_')}.manifest",
                       module, dist=_Dist(dist_name, version))


class TestDiscovery:
    def test_reads_manifest_and_manifests_exports(self):
        single = _manifest("plugdiscoa", "plugdiscoa")
        extra_a = _manifest("plugdiscob", "plugdiscob")
        extra_b = _manifest("plugdiscoc", "plugdiscoc")
        module = SimpleNamespace(MANIFEST=single, MANIFESTS=(extra_a, extra_b))
        ep = _EntryPoint("multi", "plug.manifest", module,
                         dist=_Dist("plug-multi", "2.0.0"))
        (found,) = plugin_host.discover_plugins((ep,))
        assert found.dist_name == "plug-multi"
        assert found.version == "2.0.0"
        assert found.manifests == (single, extra_a, extra_b)

    def test_a_raising_entry_point_is_a_collected_error_not_a_crash(self):
        errors: list[str] = []
        ep = _EntryPoint("boom", "plug.manifest", None,
                         dist=_Dist("plug-boom", "0.1"),
                         raises=RuntimeError("kaput"))
        assert plugin_host.discover_plugins((ep,), errors=errors) == ()
        assert len(errors) == 1 and "kaput" in errors[0]

    def test_sorted_by_dist_name(self):
        eps = (_ep("plug-zzz", _manifest("plugsortz", "plugsortz")),
               _ep("plug-aaa", _manifest("plugsorta", "plugsorta")))
        found = plugin_host.discover_plugins(eps)
        assert [p.dist_name for p in found] == ["plug-aaa", "plug-zzz"]


class TestPinGate:
    def test_no_plugins_no_pins_is_vacuously_green(self):
        report = plugin_host.load_plugins(
            [], pins={"schema_version": 1, "plugins": {}}, entry_points=())
        assert report.violations == ()
        assert report.manifests == ()
        assert report.loaded == () and report.skipped == ()

    def test_installed_but_unpinned_is_a_violation(self):
        ep = _ep("plug-unpinned", _manifest("plugunpin", "plugunpin"))
        report = plugin_host.load_plugins(
            [], pins={"schema_version": 1, "plugins": {}}, entry_points=(ep,))
        assert report.manifests == ()
        assert any("NOT pinned" in v for v in report.violations)

    def test_hash_drift_is_a_violation(self):
        manifest = _manifest("plugdrift", "plugdrift")
        ep = _ep("plug-drift", manifest)
        pins = {"schema_version": 1, "plugins": {
            "plug-drift": {"version": "1.0.0", "subsystems": ["plugdrift"],
                           "manifest_hash": "sha256:not-the-real-hash"}}}
        report = plugin_host.load_plugins([], pins=pins, entry_points=(ep,))
        assert report.manifests == ()
        assert any("hash drift" in v for v in report.violations)

    def test_pinned_but_not_installed_is_skipped_never_fatal(self):
        pins = {"schema_version": 1, "plugins": {
            "plug-ghost": {"version": "1.0.0", "subsystems": ["plugghost"],
                           "manifest_hash": "sha256:whatever"}}}
        report = plugin_host.load_plugins([], pins=pins, entry_points=())
        assert report.violations == ()
        assert report.skipped == ("plug-ghost",)

    def test_admitted_happy_path(self):
        manifest = _manifest("plughappy", "plughappy")
        ep = _ep("plug-happy", manifest)
        pins = plugin_host.build_pins(plugin_host.discover_plugins((ep,)))
        report = plugin_host.load_plugins([], pins=pins, entry_points=(ep,))
        assert report.violations == ()
        assert report.manifests == (manifest,)
        assert report.loaded == ("plug-happy==1.0.0 [plughappy]",)

    def test_empty_export_is_a_violation(self):
        ep = _EntryPoint("empty", "plug.manifest", SimpleNamespace(),
                         dist=_Dist("plug-empty", "1.0.0"))
        report = plugin_host.load_plugins(
            [], pins={"schema_version": 1, "plugins": {}}, entry_points=(ep,))
        assert any("no MANIFEST" in v for v in report.violations)


class TestContractFences:
    def test_host_owned_facet_is_refused(self):
        from sb.spec.refs import HandlerRef
        from sb.spec.versioning import CheckpointClass

        store = StoreSpec(table="plug_facet_rows",
                          sole_writer=HandlerRef("plugfacet.writer"),
                          retention="forever",
                          checkpoint_class=CheckpointClass.LEDGER,
                          invariant_tag="")
        manifest = _manifest("plugfacet", "plugfacet", stores=(store,))
        ep = _ep("plug-facet", manifest)
        pins = plugin_host.build_pins(plugin_host.discover_plugins((ep,)))
        report = plugin_host.load_plugins([], pins=pins, entry_points=(ep,))
        assert report.manifests == ()
        assert any("host-owned facet 'stores'" in v for v in report.violations)

    def test_joint_compile_catches_a_command_collision(self):
        host = _manifest("plughosta", "plugsharedcmd")
        plugin = _manifest("plugvisit", "plugsharedcmd")
        ep = _ep("plug-visit", plugin)
        pins = plugin_host.build_pins(plugin_host.discover_plugins((ep,)))
        report = plugin_host.load_plugins([host], pins=pins,
                                          entry_points=(ep,))
        assert report.manifests == ()
        assert any("COLLISION" in v for v in report.violations)

    def test_joint_compile_green_admits_the_union(self):
        host = _manifest("plughostb", "plughostbcmd")
        plugin = _manifest("plugguest", "plugguestcmd")
        ep = _ep("plug-guest", plugin)
        pins = plugin_host.build_pins(plugin_host.discover_plugins((ep,)))
        report = plugin_host.load_plugins([host], pins=pins,
                                          entry_points=(ep,))
        assert report.violations == ()
        assert report.manifests == (plugin,)


class TestPinHash:
    def test_deterministic(self):
        a = _manifest("plughash", "plughash")
        b = _manifest("plughash", "plughash")
        assert (plugin_host.manifest_stable_hash((a,))
                == plugin_host.manifest_stable_hash((b,)))

    def test_sensitive_to_the_declared_surface(self):
        base = _manifest("plughash", "plughash")
        changed = SubsystemManifest(
            key="plughash",
            commands=(CommandSpec(name="plughash", kind=CommandKind.PREFIX,
                                  summary="a DIFFERENT summary"),))
        assert (plugin_host.manifest_stable_hash((base,))
                != plugin_host.manifest_stable_hash((changed,)))

    def test_prefixed_sha256(self):
        digest = plugin_host.manifest_stable_hash(
            (_manifest("plughash", "plughash"),))
        assert digest.startswith("sha256:") and len(digest) == 71


class TestPinsFile:
    def test_missing_file_is_the_empty_registry(self, tmp_path):
        pins = plugin_host.read_pins(tmp_path / "absent.json")
        assert pins == {"schema_version": 1, "plugins": {}}

    def test_committed_registry_round_trips(self, tmp_path):
        ep = _ep("plug-file", _manifest("plugfile", "plugfile"))
        pins = plugin_host.build_pins(plugin_host.discover_plugins((ep,)))
        path = tmp_path / "plugins.lock.json"
        path.write_text(json.dumps(pins), encoding="utf-8")
        assert plugin_host.read_pins(path) == pins
