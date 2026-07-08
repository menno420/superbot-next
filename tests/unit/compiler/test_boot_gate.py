"""Boot-gate leg-A tests (S3; spec 01 §3.3-§3.4). Legs B/C arm at K8."""

import asyncio

from sb.app.boot_gate import (
    gate_recompile,
    run_boot_gate,
    snapshot_command_paths,
    snapshot_custom_ids,
    snapshot_event_names,
)
from sb.spec.manifest import SubsystemManifest
from tests.unit.compiler.conftest import CommandSpec, EventSpec
from tools.manifest_compile import compile_manifests


def test_gate_recompile_parity_and_drift():
    committed = compile_manifests().snapshot  # the real (empty) sb.manifest package
    assert gate_recompile(committed) == []
    tampered = dict(committed, stable_hash="sha256:beef")
    violations = gate_recompile(tampered)
    assert violations and violations[0].failure_class == "DRIFT"


def test_run_boot_gate_leg_a_only():
    committed = compile_manifests().snapshot
    report = asyncio.run(run_boot_gate(committed))
    assert report.recompile_ok and report.build_ok and report.remote is None


def test_snapshot_projections_shapes():
    m = SubsystemManifest(
        key="tickets",
        commands=(CommandSpec("close", surface="slash", group="ticket"),
                  CommandSpec("open", surface="prefix")),
        events=(EventSpec("ticket.closed"),),
    )
    snapshot = compile_manifests(manifests=[m]).snapshot
    assert snapshot_command_paths(snapshot) == {"ticket close"}  # slash only, qualified
    assert snapshot_event_names(snapshot) == {"ticket.closed"}
    assert snapshot_custom_ids(snapshot) == set()


class _FakeRuntime:
    def __init__(self, paths):
        self._paths = paths

    def command_paths(self):
        return self._paths

    def custom_ids(self):
        return set()

    def event_names(self):
        return set()

    def task_prefixes(self):
        return set()


def test_leg_b_mismatch_when_armed():
    committed = compile_manifests().snapshot
    report = asyncio.run(run_boot_gate(committed, runtime=_FakeRuntime({"ghost"})))
    assert not report.build_ok
    assert any(v.failure_class == "BUILD_MISMATCH" for v in report.violations)
