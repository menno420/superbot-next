"""The diagnostic hub panel (band 1) — a read view over platform_status."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import ProviderRef, is_registered, panel, provider

__all__ = ["diagnostic_hub_spec", "ensure_diagnostic_refs", "install_diagnostic_panels"]

_STATUS_PROVIDER = "diagnostic.status_index"


def _ensure_status_provider() -> ProviderRef:
    ref = ProviderRef(_STATUS_PROVIDER)
    if not is_registered(ref):
        @provider(_STATUS_PROVIDER)
        async def status_index(ctx: object):
            from sb.domain.diagnostic.service import platform_status

            status = platform_status()
            rows = [
                ("phase", status["phase"]),
                ("declared settings", str(status["declared_settings"])),
                ("subsystems", ", ".join(status["declared_subsystems"]) or "—"),
                ("ai", f"provider={status['ai'].get('provider_active', 'n/a')}"),
            ]
            for f in status["recent_findings"][:6]:
                rows.append((f"finding [{f['severity']}]", f"{f['source']}: {f['summary']}"))
            return tuple(rows)
    return ref


def diagnostic_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="diagnostic.hub",
        subsystem="diagnostic",
        title="Diagnostics",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.PROVENANCE),
        body=(
            TextBlock("Platform status from the kernel truth sources "
                      "(lifecycle, findings ring, declaration registry, AI collector)."),
            FieldsBlock(provider=_ensure_status_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("diagnostic.hub")
def _hub_factory() -> PanelSpec:
    return diagnostic_hub_spec()


def install_diagnostic_panels() -> PanelSpec:
    spec = diagnostic_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_diagnostic_refs() -> None:
    """Idempotent re-arm (the ENSURE_REFS pattern, D-0025)."""
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_status_provider()
    if not _is(PanelRef("diagnostic.hub")):
        _panel("diagnostic.hub")(_hub_factory)
