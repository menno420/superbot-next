"""UX_LAB subsystem manifest (band 6) — the shipped interface-gallery
workbench (disbot/cogs/ux_lab_cog.py): ``!uxlab`` (alias ``interfacelab``)
opens the shipped ``UxLabHomeView`` Home card. Admin-gated
(``admin_or_owner()``; subsystem_registry visibility_tier
``administrator``), zero-write by design — the lab exhibits patterns and
never touches the database. The wing browsers (buttons/selects/modals/
embeds/CV2/PIL/mock-studio/probe-bench/compare — disbot/views/ux_lab/)
join when their exhibit slice ports; the subsystem's single golden drives
the home entry point only. The slash twin (``/uxlab``) is the sibling
``uxlab`` parity row's flip.

No stores, no events, no settings: the shipped lab was CI-fenced
zero-write (AST fence, "the lab never writes to the database").
"""

from __future__ import annotations

from sb.domain.ux_lab import handlers as _handlers
from sb.domain.ux_lab import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="ux_lab",
    version=1,
    commands=(
        CommandSpec(name="uxlab", kind=CommandKind.PREFIX,
                    route=HandlerRef("ux_lab.home_view"),
                    aliases=("interfacelab",),
                    audience_tier="administrator", capability="ux_lab",
                    summary="Open the UX Lab — the interface gallery + "
                            "limit probe bench.",
                    usage="!uxlab"),
    ),
    panels=(_panels.ux_lab_home_spec(),),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
