"""SETUP subsystem manifest (band 1, A-9 skeleton) — the wizard promoted to
a first-class roster line: /setup entry point + the G-19 wizard_sections
facet (all 10 shipped registrants verbatim) + the hub projection."""

from __future__ import annotations

from sb.domain.setup import ai_tasks as _ai_tasks
from sb.domain.setup import panels as _panels
from sb.domain.setup.sections import SECTIONS
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="setup",
    version=1,
    commands=(
        CommandSpec(
            name="setup",
            kind=CommandKind.BOTH,
            route=PanelRef("setup.hub"),
            summary="Guided server setup: presets, channels, roles, "
                    "moderation, review.",
            usage="/setup",
            capability="setup",
            slash_common=True,               # config-lane, ADMIN floor
        ),
    ),
    panels=(_panels.setup_hub_spec(),),
    wizard_sections=SECTIONS,
)

_ai_tasks.register_ai_tasks()


def _ensure_refs() -> None:
    _panels.ensure_setup_refs()
    _ai_tasks.register_ai_tasks()


# module-attribute hook convention (D-0026)
ENSURE_REFS = _ensure_refs
