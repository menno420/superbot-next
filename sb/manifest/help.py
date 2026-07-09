"""HELP subsystem manifest (band 1) — help is a PROJECTION from the
manifests (K8 help-as-projection): the panel's entries regenerate from the
live command inventory at install; this module declares only the entry
point + the projected panel."""

from __future__ import annotations

from sb.domain.help import ai_tasks as _ai_tasks
from sb.domain.help import service as _service
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="help",
    version=1,
    commands=(
        CommandSpec(
            name="help",
            kind=CommandKind.BOTH,           # shipped: !help + /help
            route=PanelRef("help.home"),
            summary="Everything the bot can do, generated from its manifests.",
            usage="/help",
            capability="help",
            audience_tier="user",            # domain lane: member-facing
            slash_common=True,               # D-5: discovery is essential
        ),
    ),
    panels=_service.build_help_panels(),
)

_ai_tasks.register_ai_tasks()


def _ensure_refs() -> None:
    """P1 re-arm hook (D-0025): the help provider/panel refs + task claim."""
    from sb.spec.refs import PanelRef as _P, is_registered, panel as _panel

    _service.build_help_panels()  # re-registers the provider/handler refs
    if not is_registered(_P("help.home")):
        _panel("help.home")(_service._help_home_factory)
    _ai_tasks.register_ai_tasks()


# The P1 re-arm hook is a module ATTRIBUTE by convention (like MANIFEST):
# an assignment, so the per-module hook name never trips the namespace
# shadowing checkers (D-0026).
ENSURE_REFS = _ensure_refs
