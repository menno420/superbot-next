"""PLATFORM subsystem manifest (band 5) — the essential control floor:
the command-access policy stores (old migration 050 — the K8 admission
resolver's DB truth), the guild-teardown registry, the consistency
report, introspection/snapshot reads, and the band-5 K10 task claims
(platform.explain_status / platform.explain_consistency /
code_context.explain, byte-identical legacy ids).

Importing this manifest FILLS the K8 waiting port
install_access_policy_reader (the real per-guild CommandAccessSnapshot
read — the resolver ran on the mode=None safe default since S9).
"""

from __future__ import annotations

import sb.domain.platform.consistency  # noqa: F401 — collector registry
import sb.domain.platform.guild_teardown  # noqa: F401 — hook registry
from sb.domain.platform import command_access
from sb.domain.platform.ai_tasks import register_platform_tasks
from sb.spec.manifest import SubsystemManifest

MANIFEST = SubsystemManifest(
    key="platform",
    version=1,
    commands=(),
    panels=(),
    settings=(),
    stores=(command_access.COMMAND_ACCESS_POLICY_STORE,
            command_access.COMMAND_ACCESS_CHANNELS_STORE,
            command_access.COMMAND_ACCESS_CHANNEL_ROLES_STORE),
    events=(),
    capabilities=(),
)

command_access.register_ops()
command_access.install_access_reader()
register_platform_tasks()


def _ensure_refs() -> None:
    command_access.ensure_refs()
    command_access.register_ops()
    command_access.install_access_reader()
    register_platform_tasks()


ENSURE_REFS = _ensure_refs
