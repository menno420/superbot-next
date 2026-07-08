"""The setup hub panel (band 1) — projected from the section registry
(the shipped hub derived its buttons from the registry; the projection
survives, the bespoke view does not)."""

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

__all__ = ["ensure_setup_refs", "install_setup_panels", "setup_hub_spec"]

_SECTIONS_PROVIDER = "setup.sections_index"


def _ensure_sections_provider() -> ProviderRef:
    ref = ProviderRef(_SECTIONS_PROVIDER)
    if not is_registered(ref):
        @provider(_SECTIONS_PROVIDER)
        async def sections_index(ctx: object):
            from sb.domain.setup.sections import REGISTRY, register_shipped_sections

            register_shipped_sections()
            rows = []
            for s in REGISTRY.ordered():
                title = f"{s.emoji + ' ' if s.emoji else ''}{s.label}"
                state = "ready" if s.route is not None else "declared (flow ports later)"
                ops = f" · stages: {', '.join(s.op_kinds)}" if s.op_kinds else ""
                rows.append((title, f"{state}{ops}"))
            return tuple(rows)
    return ref


def setup_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="setup.hub",
        subsystem="setup",
        title="Server setup",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The setup wizard's sections, ordered by the registry "
                      "(A-9). Interactive flows arm per-section as they port."),
            FieldsBlock(provider=_ensure_sections_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("setup.hub")
def _hub_factory() -> PanelSpec:
    return setup_hub_spec()


def install_setup_panels() -> PanelSpec:
    spec = setup_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_setup_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_sections_provider()
    if not _is(PanelRef("setup.hub")):
        _panel("setup.hub")(_hub_factory)
