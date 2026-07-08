"""DIAGNOSTIC subsystem manifest (band 1) — the operator status surface.

The shipped deep-diagnostic fleet (platform_group.py subcommands:
consistency / caches / backfill / anchors / findings / health / ...) is
successor work; this slice lands the hub + the kernel-truth status service
+ the /ai diagnostics reads (D-0026)."""

from __future__ import annotations

from sb.domain.diagnostic import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="diagnostic",
    version=1,
    commands=(
        CommandSpec(
            name="diagnostics",
            kind=CommandKind.BOTH,           # shipped surface name, verbatim
            route=PanelRef("diagnostic.hub"),
            summary="Platform status: lifecycle, findings, declarations, AI health.",
            usage="/diagnostics",
            capability="diagnostic",
            slash_common=True,               # operators must reach this on slash
        ),
    ),
    panels=(_panels.diagnostic_hub_spec(),),
)


def _ensure_refs() -> None:
    _panels.ensure_diagnostic_refs()


# The P1 re-arm hook is a module ATTRIBUTE by convention (like MANIFEST):
# an assignment, so the per-module hook name never trips the namespace
# shadowing checkers (D-0026).
ENSURE_REFS = _ensure_refs
