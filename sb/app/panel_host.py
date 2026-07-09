"""Composition-root wiring for the panel runtime (K8/S9b).

`install_panel_runtime()` arms the three seams in one call:
  1. the resolver's OPEN_PANEL port → the kernel panel engine;
  2. the engine's presenter port → the discord adapter (only when discord
     is importable — headless/CI environments keep the not-installed
     default, which classifies as a BUG envelope if reached);
  3. the render layer's hub resolver (FOLLOW_PARENT → the subsystem's
     CURRENT parent_hub), fed by the manifest snapshot when hubs exist.

Boot order home: preflight → install_owner_config → install_secret_presence
→ boot gate leg A → db.init → build_registry → start_health_server →
build_runtime → **install_panel_runtime()** → register_error_handlers →
lifecycle STARTING → gateway connect → RUNNING → poll supervisor.
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Callable

from sb.kernel.interaction.resolve import install_panel_engine
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.render import install_hub_resolver

logger = logging.getLogger("sb.app.panel_host")

__all__ = ["install_panel_runtime", "register_manifest_panels"]


def register_manifest_panels(manifests: list) -> int:
    """Register every manifest-DECLARED PanelSpec with the K8 panel registry
    (fences run at registration; identical re-registration is a no-op).

    The composition-root obligation the manifest imports cannot carry: most
    manifests only CONSTRUCT their PanelSpecs (``panels=(...,)``) — without
    this call ``get_panel`` raises ``LookupError`` for every PanelRef-routed
    command (settings.hub, help.home, diagnostic.hub, setup.hub, ...) the
    moment a command dispatches. Returns the number of panels registered."""
    from sb.kernel.panels.registry import register_panel

    count = 0
    for manifest in manifests:
        for spec in getattr(manifest, "panels", ()) or ():
            register_panel(spec)
            count += 1
    return count


def install_panel_runtime(*, hub_resolver: Callable[[str], str | None] | None = None) -> None:
    install_panel_engine(panel_engine.open_panel)
    if hub_resolver is not None:
        install_hub_resolver(hub_resolver)
    if importlib.util.find_spec("discord") is None:
        logger.info("discord not importable — panel presenter left uninstalled")
        return
    from sb.adapters.discord.panel_view import DiscordPanelPresenter

    panel_engine.install_panel_presenter(DiscordPanelPresenter())
