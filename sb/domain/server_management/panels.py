"""The SERVER MANAGEMENT hub panel (parity flip) — the shipped
``ServerManagementHubView`` (disbot/views/server_management/hub.py, PR14):
the 🧭 red embed (the shipped one-line entry-point blurb; the read-only
``Managers`` health-badge field + the ``Overall configuration health``
line — disbot/services/server_management_hub.py, the fail-safe badge
composer; the "Read-only summary · click a manager to open it" footer)
over the shipped manager rows — Moderation/Channels/Roles (blurple) +
Cleanup (grey) / Setup (green) + the row-2 utility quartet (Access Map /
Help Preview / Help editor / Refresh, grey) — every button carrying its
emoji INSIDE the label and its shipped PERSISTENT custom_id verbatim
(``server_management:<key>`` via ``custom_id_override``; the economy-hub
precedent). ``parity/goldens/servermanagement/
sweep_slash_server-management.json`` pins every byte of the slash twin
(the ephemeral type-4, flags 64); the sibling ``server_management`` row's
prefix golden pins the same panel on the message surface.

``session_lifecycle=True`` with every component override-pinned: nothing
is run-minted (the overrides survive verbatim — the engine's documented
custom_id_override rule), no ``panel_anchors`` row is recorded (the
shipped sweep goldens record none), and the never-strand fence takes the
session-view exemption the golden's exactly-three-rows shape demands (the
shipped hub carried NO nav row — it is the top-of-stack operator surface
with its own 🔄 Refresh recovery). The shipped PERSISTENT-view anchor
semantics (``panel_manager.get_or_render_panel``, restart restoration)
are the sibling prefix row's flip concern, carried there.

Deliberate under-port notes (parity beyond the golden):
* the shipped health badges are LIVE reads (bot permissions, role
  hierarchy feasibility, the cleanup/setup diagnostics report —
  services/server_management_hub.py); the specialised managers those
  reads belong to (moderation/roles/cleanup/setup) are their own port
  slices, so the golden-pinned badge literal ships here (the ux_lab
  Exhibits-line precedent) and re-derivation lands as each manager
  ports;
* Moderation/Roles/Cleanup/Access Map/Help Preview/Help editor clicks
  land on declared pending terminals; Channels forwards to the PORTED
  ``channel.hub`` panel and Setup to the band-1 ``setup.hub`` (the
  shipped hub routed into those managers).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "ensure_panel_refs",
    "install_server_management_panels",
    "server_management_hub_spec",
]

# the shipped hub copy (hub.py build_server_management_hub — the goldens
# pin every byte).
_DESCRIPTION = (
    "Your single entry point to the server's operator tools. Pick a "
    "manager below — the badges are a read-only health summary."
)

#: the shipped footer literal (hub.py set_footer) — outside FooterMode's
#: vocabulary, hence the renderer_override below (the utility/ux_lab/
#: channel precedent).
_FOOTER = "Read-only summary · click a manager to open it"

#: the shipped badge composer's rendering (services/server_management_hub
#: .py glyph+summary lines, verbatim as the goldens captured them in the
#: sweep guild) — a pinned literal until the manager slices port their
#: live reads (module-docstring under-port note; the ux_lab precedent).
_MANAGERS = (
    "🟢 🛡️ **Moderation** — Can ban, kick and timeout members\n"
    "🟢 📺 **Channels** — Can create, rename, move and delete channels\n"
    "🟡 🎭 **Roles** — No roles are below the bot — move its role higher\n"
    "🟢 🧹 **Cleanup** — No cleanup-policy issues detected\n"
    "🟡 🧩 **Setup** — Not configured yet — run setup"
)

_OVERALL = "🟢 No configuration issues need attention"


async def _hub_health(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped two health fields (Managers + Overall configuration
    health, verbatim)."""
    del ctx
    return (("Managers", _MANAGERS),
            ("Overall configuration health", _OVERALL))


def _pending(key: str, label: str, *,
             style: ActionStyle = ActionStyle.PRIMARY) -> PanelActionSpec:
    """One shipped manager button whose target is its own port slice —
    the click lands on the polite pending terminal (role/utility-band
    precedent); the shipped persistent custom_id survives verbatim."""
    return PanelActionSpec(
        action_id=key, label=label, style=style,
        audience_tier="administrator",       # the shipped admin floor
        handler=HandlerRef(f"server_management.{key}_pending"),
        custom_id_override=f"server_management:{key}")


def server_management_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="server_management.hub",
        subsystem="server_management",
        title="🧭 Server Management Hub",
        # the shipped slash twin answered EPHEMERAL (the golden's type-4
        # data carries flags 64) — the grammar's INVOKER audience.
        audience=Audience.INVOKER,
        # the shipped hub accent — discord.Color.red() (ERROR_COLOR token).
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("server_management.hub_health"))),
        actions=(
            # row 0 — the shipped blurple manager trio.
            _pending("moderation", "🛡️ Moderation"),
            PanelActionSpec(
                action_id="channels", label="📺 Channels",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                # the shipped hub routed into the channel manager view —
                # the PORTED channel.hub panel (#131).
                handler=PanelRef("channel.hub"),
                custom_id_override="server_management:channels"),
            _pending("roles", "🎭 Roles"),
            # row 1 — grey Cleanup + the green Setup wizard entry.
            _pending("cleanup", "🧹 Cleanup", style=ActionStyle.SECONDARY),
            PanelActionSpec(
                action_id="setup", label="🧩 Setup",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                # the shipped hub's own wizard entry — the band-1 setup hub.
                handler=PanelRef("setup.hub"),
                custom_id_override="server_management:setup"),
            # row 2 — the shipped grey utility quartet.
            _pending("access_map", "🔓 Access Map",
                     style=ActionStyle.SECONDARY),
            _pending("help_preview", "👁 Help Preview",
                     style=ActionStyle.SECONDARY),
            _pending("help_editor", "✏️ Help editor",
                     style=ActionStyle.SECONDARY),
            PanelActionSpec(
                # K1 custom_id claims are repo-global on action_id —
                # treasury owns bare "refresh" (the general_overview
                # precedent); the shipped wire id survives via override.
                action_id="sm_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("server_management.hub"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="server_management:refresh"),
        ),
        # the shipped hub carried NO nav row (top-of-stack operator
        # surface; 🔄 Refresh is its recovery) — the goldens pin exactly
        # three component rows; see the module docstring for the
        # session-lifecycle rationale.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("server_management.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Read-only summary · "
            "click a manager to open it' (hub.py set_footer) — outside "
            "FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/servermanagement + goldens/server_management pin "
            "the byte; the utility/ux_lab/channel precedent). The "
            "override delegates to the grammar renderer and replaces "
            "ONLY the footer; body, fields, actions and layout stay "
            "declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("moderation", "channels", "roles"),
            ("cleanup", "setup"),
            ("access_map", "help_preview", "help_editor", "sm_refresh"),
        )),)),
    )


# --- renderer override ------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed, footer=_FOOTER))


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("server_management.hub")):
        panel("server_management.hub")(server_management_hub_spec)
    if not is_registered(HandlerRef("server_management.render_hub")):
        handler("server_management.render_hub")(_render_hub)
    if not is_registered(ProviderRef("server_management.hub_health")):
        provider("server_management.hub_health")(_hub_health)


_register_refs()


def install_server_management_panels() -> tuple[PanelSpec, ...]:
    spec = server_management_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    _register_refs()
