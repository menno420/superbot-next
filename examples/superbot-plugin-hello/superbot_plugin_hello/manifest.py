"""HELLO subsystem manifest — the plugin-contract hello-world.

One command + one panel, declared OUT OF TREE and consumed by the
superbot-next host through the ``sb.plugins`` entry point (host side:
``sb/app/plugin_host.py``; contract: ``docs/game-plugin-contract.md`` in the
host repo). Pure declarations + ref registrations — the same shape as an
in-tree ``sb/manifest/<key>.py`` module:

  - importing this module IS reserving (the ``@panel`` registration below
    mirrors the in-tree decorator discipline);
  - the host pins this manifest's canonical hash in its committed
    ``plugins.lock.json`` and refuses drift at boot;
  - the v1 contract facets only: this manifest declares a command and a
    panel (stores / data_invariants / wizard_sections are host-owned).
"""

from __future__ import annotations

from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import (
    EmbedFrameSpec,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import PanelRef, is_registered, panel

PANEL_ID = "hello.home"


def hello_home_spec() -> PanelSpec:
    """The one panel — a static text body; the panel engine renders it and
    the engine-injected nav slots carry the never-strand routes."""
    return PanelSpec(
        panel_id=PANEL_ID,
        subsystem="hello",
        title="Hello from a plugin",
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock(
                "👋 This panel is declared in the **superbot-plugin-hello** "
                "repository — a separate repo from the bot — and registered "
                "through the `sb.plugins` entry point. It proves the "
                "game-plugin contract end-to-end: entry-point discovery, "
                "committed hash pin, joint compile, live dispatch."
            ),
        ),
        navigation=NavigationSpec(),
    )


def _ensure_refs() -> None:
    """Idempotent ref registration (the in-tree ``ENSURE_REFS`` discipline:
    decorators run at first import only; the compiler's test seam may clear
    the ref table without evicting module caches)."""
    if not is_registered(PanelRef(PANEL_ID)):
        panel(PANEL_ID)(hello_home_spec)


_ensure_refs()
ENSURE_REFS = _ensure_refs


MANIFEST = SubsystemManifest(
    key="hello",
    version=1,
    commands=(
        CommandSpec(
            name="hello",
            kind=CommandKind.BOTH,
            route=PanelRef(PANEL_ID),
            summary="Prove the game-plugin contract: open the hello panel.",
            usage="!hello",
            audience_tier="user",
            capability="hello",
        ),
    ),
    panels=(hello_home_spec(),),
)
