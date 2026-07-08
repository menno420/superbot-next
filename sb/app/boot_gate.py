"""The compiler boot gate — the three-way parity oracle (frozen L0 spec 01 §3.3-§3.4).

Three artifacts, three legs:
  A — recompile-parity: committed snapshot == in-process `compile_manifests()`
      re-run (all of P1..P9, by stable_hash). Boot: FAILED_STARTUP on divergence.
      P3/namespace runs ONCE, inside this leg — never a separate boot step.
  B — build-parity: `snapshot_*()` projections == the built runtime's realized
      sets. ARMS AT K8 (needs `build_runtime`); FAILED_STARTUP before connect.
  C — remote-parity: snapshot command paths vs Discord remote. ARMS AT K8
      (needs the gateway); NON-FATAL -> gated snapshot->Discord sync, lifting
      shipped `command_tree_sync._remote_paths` + `SyncOutcome` verbatim.

This module is composition-root code (may import tools/ machinery): the boot
gate is the ONE runtime consumer of the compiler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tools.manifest_compile import Violation, compile_manifests


class BuiltRuntime(Protocol):
    """The K8 builder contract (spec 01 §3.3): a pure structural function of
    the snapshot exposing its realized identity sets for leg B."""

    def command_paths(self) -> set[str]: ...
    def custom_ids(self) -> set[str]: ...
    def event_names(self) -> set[str]: ...
    def task_prefixes(self) -> set[str]: ...


@dataclass(frozen=True)
class ParityReport:
    recompile_ok: bool                 # leg A
    build_ok: bool                     # leg B (True while dormant — arms at K8)
    remote: object | None              # leg C — the shipped SyncOutcome type (arms at K8)
    violations: tuple[Violation, ...]


# --- the snapshot projections (mirror shipped `_local_paths` qualified shape) -----

def snapshot_command_paths(snapshot: dict) -> set[str]:
    """Qualified "group sub" paths, slash surface only (Discord's tree)."""
    paths: set[str] = set()
    nodes = ((snapshot.get("projections") or {}).get("namespace") or {}).get("command", [])
    for node in nodes:
        if node.get("surface") != "slash":
            continue
        parent = node.get("parent_group")
        qualified = f"{parent.replace('.', ' ')} {node['value']}" if parent else node["value"]
        paths.add(qualified)
    return paths


def snapshot_custom_ids(snapshot: dict) -> set[str]:
    nodes = ((snapshot.get("projections") or {}).get("namespace") or {}).get("custom_id", [])
    return {node["value"] for node in nodes}


def snapshot_event_names(snapshot: dict) -> set[str]:
    return set((snapshot.get("projections") or {}).get("events") or {})


def snapshot_task_prefixes(snapshot: dict) -> set[str]:
    nodes = ((snapshot.get("projections") or {}).get("namespace") or {}).get("task_prefix", [])
    return {node["value"] for node in nodes}


# --- leg A -------------------------------------------------------------------------

def gate_recompile(committed: dict) -> list[Violation]:
    """Leg A: recompile in-process (P1..P9) and compare stable_hash against the
    committed snapshot. Empty list == parity. The composition root converts a
    non-empty list to FAILED_STARTUP via K5's `fail_startup` seam (arms at K5)."""
    result = compile_manifests(committed_snapshot=committed)
    return list(result.violations)


async def run_boot_gate(
    committed: dict,
    runtime: BuiltRuntime | None = None,
    bot: object | None = None,
    *,
    sync_enabled: bool = False,
) -> ParityReport:
    """Run the boot legs. Legs B and C are DORMANT until K8 supplies
    `build_runtime` / the gateway (spec 01 §11 armed-later); passing
    runtime/bot arms them."""
    violations = gate_recompile(committed)
    recompile_ok = not violations

    build_ok = True
    if runtime is not None and recompile_ok:                      # leg B (arms at K8)
        checks = (
            ("command_paths", snapshot_command_paths(committed), runtime.command_paths()),
            ("custom_ids", snapshot_custom_ids(committed), runtime.custom_ids()),
            ("event_names", snapshot_event_names(committed), runtime.event_names()),
            ("task_prefixes", snapshot_task_prefixes(committed), runtime.task_prefixes()),
        )
        for name, expected, realized in checks:
            if expected != realized:
                build_ok = False
                missing = sorted(expected - realized)[:5]
                extra = sorted(realized - expected)[:5]
                violations.append(Violation(
                    "build_parity", "BUILD_MISMATCH", None, name,
                    f"snapshot != built runtime (missing={missing}, extra={extra})"))

    remote = None
    if bot is not None:                                           # leg C (armed at K8/S9)
        # snapshot->Discord, NON-FATAL (REMOTE_LAG): sync_remote never raises.
        from sb.app.tree_sync import sync_remote
        remote = await sync_remote(bot, committed, enabled=sync_enabled)

    return ParityReport(
        recompile_ok=recompile_ok,
        build_ok=build_ok,
        remote=remote,
        violations=tuple(violations),
    )
