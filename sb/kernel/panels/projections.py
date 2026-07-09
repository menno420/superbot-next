"""Generated panels (K8/S9b): settings-as-projection + help-as-projection.

Both are PROJECTIONS over declared data — never hand-built views:

- ``settings_panel_spec(subsystem)`` projects the K7 setting-declaration
  registry into a compile-clean ``PanelSpec`` whose FieldsBlock provider
  resolves each declared setting through THE read seam
  (``sb.kernel.settings.resolve``). v1 is the read view; the per-setting
  EDIT workflows are the band-1 scalar-lane port (kernel workflows
  parameterized per SettingSpec) — the panel grows actions, not shape.

- ``help_panel_spec(entries)`` projects a command inventory (subsystem →
  (name, summary) rows, e.g. from the RuntimeIndex / manifest snapshot)
  into the help hub panel — help is a projection FROM manifests, never a
  separately-maintained document (C-7 one-description-surface).

Providers register lazily under ``provider:sb.panels.*`` — kernel-owned
names (the `sb.` prefix keeps them out of any domain's namespace).
"""

from __future__ import annotations

from typing import Mapping, Sequence

from sb.kernel import settings as settings_mod
from sb.kernel.panels.context import PanelContext
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import ProviderRef, is_registered, provider

__all__ = ["help_panel_spec", "settings_panel_spec"]

_SETTINGS_PROVIDER = "sb.panels.settings_overview"
_HELP_PROVIDER = "sb.panels.help_index"

# help entries live module-side so the registered provider stays a stable
# singleton (ref re-registration is an error by design).
_help_entries: dict[str, tuple[tuple[str, str], ...]] = {}


def _ensure_settings_provider() -> ProviderRef:
    ref = ProviderRef(_SETTINGS_PROVIDER)
    if not is_registered(ref):
        @provider(_SETTINGS_PROVIDER)
        async def settings_overview(ctx: PanelContext):
            """(name, resolved value) per declared setting of ctx's subsystem —
            the subsystem rides the panel_id; we re-read it from the registry."""
            rows = []
            for decl in settings_mod.iter_declarations():
                value = await settings_mod.resolve(
                    ctx.guild_id or 0, decl.subsystem, decl.name)
                rows.append((decl.key, repr(value)))
            return tuple(rows)
    return ref


def settings_panel_spec(subsystem: str) -> PanelSpec:
    """The generated per-subsystem settings panel (read view, v1)."""
    ref = _ensure_settings_provider()
    return PanelSpec(
        panel_id=f"settings.{subsystem}",
        subsystem=subsystem,
        title=f"{subsystem} — settings",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Declared settings and their resolved values."),
            FieldsBlock(provider=ref),
        ),
        navigation=NavigationSpec(),   # help + FOLLOW_PARENT home
    )


def _ensure_help_provider() -> ProviderRef:
    ref = ProviderRef(_HELP_PROVIDER)
    if not is_registered(ref):
        @provider(_HELP_PROVIDER)
        async def help_index(ctx: PanelContext):
            rows = []
            for subsystem in sorted(_help_entries):
                lines = [f"`{name}` — {summary}" if summary else f"`{name}`"
                         for name, summary in _help_entries[subsystem]]
                rows.append((subsystem,
                             "\n".join(lines) or "No commands declared yet."))
            return tuple(rows)
    return ref


def help_panel_spec(
    entries: Mapping[str, Sequence[tuple[str, str]]],
) -> PanelSpec:
    """The help hub — a projection from the declared command inventory.
    ``entries``: subsystem → ((command_name, summary), ...)."""
    _help_entries.clear()
    _help_entries.update({k: tuple(v) for k, v in entries.items()})
    ref = _ensure_help_provider()
    return PanelSpec(
        panel_id="help.home",
        subsystem="help",
        title="Help",
        audience=Audience.PUBLIC,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Everything the bot can do, from its own manifests."),
            FieldsBlock(provider=ref),
        ),
        # the help hub IS home — no help slot on itself (render also guards
        # subsystem=="help"), home stays for the root hub when one exists.
        navigation=NavigationSpec(show_help=False),
    )
