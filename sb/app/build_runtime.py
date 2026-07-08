"""`build_runtime(snapshot)` — the K8 runtime builder that ARMS boot-gate
leg B (spec 01 §3.3: "a pure structural function of the snapshot exposing
its realized identity sets").

Builds the dispatch index (key → `TargetRef`) FROM the committed snapshot's
namespace projections + the ref table, installs it as the adapters'
target-index port, and realizes the `BuiltRuntime` sets from what it
actually built — so leg B compares snapshot-declared vs runtime-realized,
not snapshot vs itself (a missing ref registration or an event that failed
to register WILL diverge).
"""

from __future__ import annotations

from sb.kernel.interaction.adapters import install_target_index
from sb.kernel.interaction.request import Surface, TargetRef
from sb.spec.events import KNOWN_EVENTS

__all__ = ["RuntimeIndex", "build_runtime"]


class RuntimeIndex:
    """Satisfies sb.app.boot_gate.BuiltRuntime (leg B)."""

    def __init__(self, snapshot: dict) -> None:
        self._commands: dict[tuple[str, Surface], TargetRef] = {}
        self._custom_ids: set[str] = set()
        self._task_prefixes: set[str] = set()
        self._paths: set[str] = set()
        self._build(snapshot)

    # --- build ---------------------------------------------------------------

    def _build(self, snapshot: dict) -> None:
        projections = snapshot.get("projections") or {}
        namespace = projections.get("namespace") or {}
        subsystems = {s.get("key"): s for s in snapshot.get("subsystems", [])
                      if isinstance(s, dict)}

        for node in namespace.get("command", ()):  # realized command index
            surface = Surface.SLASH if node.get("surface") == "slash" else Surface.PREFIX
            key = node["value"]
            parent = node.get("parent_group")
            qualified = f"{parent.replace('.', ' ')} {key}" if parent else key
            spec = self._find_command_spec(subsystems.get(node.get("owner")), key)
            self._commands[(qualified, surface)] = TargetRef(key=qualified, spec=spec)
            if surface is Surface.SLASH:
                self._paths.add(qualified)

        for node in namespace.get("custom_id", ()):
            self._custom_ids.add(node["value"])
            self._commands[(node["value"], Surface.COMPONENT)] = TargetRef(
                key=node["value"], spec=self._find_action_spec(
                    subsystems.get(node.get("owner")), node["value"]))

        for node in namespace.get("task_prefix", ()):
            self._task_prefixes.add(node["value"])

    @staticmethod
    def _find_command_spec(subsystem: dict | None, name: str) -> object:
        for cmd in ((subsystem or {}).get("commands") or ()):
            if isinstance(cmd, dict) and cmd.get("name") == name:
                return _SnapshotSpec(cmd)
        return _SnapshotSpec({})

    @staticmethod
    def _find_action_spec(subsystem: dict | None, custom_id: str) -> object:
        for panel in ((subsystem or {}).get("panels") or ()):
            for action in (panel.get("actions") or () if isinstance(panel, dict) else ()):
                if isinstance(action, dict) and action.get("custom_id") == custom_id:
                    return _SnapshotSpec(action)
        return _SnapshotSpec({})

    # --- the adapters' target index -------------------------------------------

    def lookup(self, key: str, surface: Surface) -> TargetRef | None:
        return self._commands.get((key, surface))

    # --- BuiltRuntime (leg B) --------------------------------------------------

    def command_paths(self) -> set[str]:
        return set(self._paths)

    def custom_ids(self) -> set[str]:
        return set(self._custom_ids)

    _KERNEL_EVENT_OWNERS = ("kernel", "audit")   # the from-birth seeds

    def event_names(self) -> set[str]:
        # realized = the registered KNOWN_EVENTS minus the kernel-owned
        # from-birth seeds (audit.action_recorded owner="audit",
        # command.dispatched owner="kernel") — the snapshot projects
        # SUBSYSTEM-declared events only.
        return {name for name, spec in KNOWN_EVENTS.items()
                if getattr(spec, "owner_subsystem", None)
                not in self._KERNEL_EVENT_OWNERS}

    def task_prefixes(self) -> set[str]:
        return set(self._task_prefixes)


class _SnapshotSpec:
    """A snapshot-projected spec node exposed attribute-style (the resolver
    duck-reads authority_ref/enabled_when/… with the pinned defaults)."""

    def __init__(self, data: dict) -> None:
        self.__dict__.update(data or {})


def build_runtime(snapshot: dict) -> RuntimeIndex:
    runtime = RuntimeIndex(snapshot)
    install_target_index(runtime.lookup)
    return runtime
