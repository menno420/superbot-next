"""Help projection service (band 1)."""

from __future__ import annotations

import importlib
import pkgutil

from sb.kernel.panels.projections import help_panel_spec
from sb.kernel.panels.registry import register_panel
from sb.spec.panels import PanelSpec

__all__ = ["build_help_panel", "command_inventory", "install_help"]


def command_inventory() -> dict[str, tuple[tuple[str, str], ...]]:
    """subsystem -> ((command name, summary), ...) — generated from EVERY
    sb.manifest declaration (the single source; help can never drift)."""
    import sb.manifest as manifest_pkg

    inventory: dict[str, list[tuple[str, str]]] = {}
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda i: i.name):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        for manifest in ([getattr(module, "MANIFEST", None)]
                         + list(getattr(module, "MANIFESTS", ()) or ())):
            if manifest is None:
                continue
            key = str(getattr(manifest, "key", info.name))
            for cmd in getattr(manifest, "commands", ()) or ():
                name = str(getattr(cmd, "name", "") or "")
                if name:
                    inventory.setdefault(key, []).append(
                        (name, str(getattr(cmd, "summary", "") or "")))
    return {k: tuple(v) for k, v in sorted(inventory.items())}


def build_help_panel() -> PanelSpec:
    """(Re)build the help hub from the live inventory (refreshes the
    module-side entries the registered provider reads)."""
    return help_panel_spec(command_inventory())


def install_help() -> PanelSpec:
    """Boot wiring: rebuild from the full inventory + register the panel
    (idempotent for the identical spec)."""
    spec = build_help_panel()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


# import-time ref registration (P2 resolves PanelRef("help.home"))
from sb.spec.refs import panel as _panel  # noqa: E402


@_panel("help.home")
def _help_home_factory() -> PanelSpec:
    return build_help_panel()
