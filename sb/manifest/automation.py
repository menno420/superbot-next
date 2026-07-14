"""AUTOMATION subsystem manifest — the MINIMAL rule-write seam (the K9
``add_automation_rule`` apply lane; setup compound-ops slice 2).

Deliberately store-and-op only: the oracle's automation subsystem
(disbot services/automation_{mutation,templates,registry,executor,
scheduler} @ f969b95) surfaces no commands or panels of its own inside
this slice — the setup wizard's preset flow is the sole producer of
``add_automation_rule`` draft rows (sb/domain/setup/preset_select.py),
and the Final-Review K9 apply is the sole consumer. The diagnostics
automation panel + the runtime scheduler/executor are the NAMED
SUCCESSOR (sb/domain/automation/__init__.py ledger).
"""

from __future__ import annotations

from sb.domain.automation import ops as _ops
from sb.domain.automation import store as _store
from sb.spec.manifest import SubsystemManifest

MANIFEST = SubsystemManifest(
    key="automation",
    version=1,
    commands=(), panels=(), settings=(),
    stores=(_store.AUTOMATION_RULES_STORE,),
    events=(), capabilities=(),
)

_ops.register_ops()


def _ensure_refs() -> None:
    _store.ensure_refs()
    _ops.ensure_ops_refs()


# module-attribute hook convention (D-0026)
ENSURE_REFS = _ensure_refs
