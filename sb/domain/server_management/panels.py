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

ANCHORED-PANEL SEMANTICS (the sibling prefix row's flip, PR after #178):
``session_lifecycle=False`` — the shipped hub was a panel-MANAGER panel
(``panel_manager.get_or_render_panel``): the PREFIX open sends a real
channel message and records a ``panel_anchors`` row
(goldens/server_management/sweep_servermanagement pins it), while the
slash twin's ephemeral type-4 records none (the engine's
``_record_anchor`` skips interaction surfaces — goldens/servermanagement
pins the empty delta). Every component stays override-pinned (overrides
render verbatim on non-session panels too — the moderation modmenu
precedent).

THE SHIPPED BACK-TO-HELP SPLIT: the shipped composition root wired a
help hook into ``get_or_render_panel`` (bot1.py → cogs/help_cog.py
``_attach_back_to_help_button``) that appended a ``↩ Back to Help``
button (persistent id ``help:back``, row 4, grey) to DIRECTLY-INVOKED
hubs on the MESSAGE path — the slash twin never passed through the
panel manager, so it carried exactly three rows. The port declares the
shipped button as a real routable action (``help_back``, override
``help:back``, routed to the ported ``help.home``) and the
renderer_override drops it on the ephemeral slash surface (surface-keyed
component-drop — the D-0068 lane over the new ``PanelContext.surface``
field). The never-strand fence is satisfied honestly by
``navigation.parent = help.home`` (the shipped escape IS Help); the
grammar's own injected ``nav:back:*`` button is dropped in the override
(the shipped hub never rendered a grammar nav row — both goldens pin
its absence; the declared ``help_back`` action carries the shipped
escape byte instead).

Ledgered unpinned corner (no golden drives it): a 🔄 Refresh click
re-renders on the COMPONENT surface, which keeps the ``help_back`` row
(matching the shipped ANCHORED panel's refresh, whose view kept the
appended button); the shipped slash-opened ephemeral's refresh stayed
three-row — that ephemeral-refresh corner renders four rows here until
a message-context signal ports (surface alone cannot split the two
refresh homes).

Deliberate under-port notes (parity beyond the golden):
* the shipped health badges are LIVE reads (bot permissions, role
  hierarchy feasibility, the cleanup/setup diagnostics report —
  services/server_management_hub.py); the specialised managers those
  reads belong to (moderation/roles/cleanup/setup) are their own port
  slices, so the golden-pinned badge literal ships here (the ux_lab
  Exhibits-line precedent) and re-derivation lands as each manager
  ports;
* Moderation/Roles/Cleanup/Help Preview/Help editor clicks land on
  declared pending terminals; Channels forwards to the PORTED
  ``channel.hub`` panel, Setup to the band-1 ``setup.hub``, and Access
  Map to the PORTED ``server_management.access_map`` subpanel (the
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
            # row 2 — the shipped grey utility quartet. Access Map is
            # PORTED (the P1C subpanel over the P1A projection —
            # access_map.py); the shipped wire id survives verbatim.
            PanelActionSpec(
                action_id="access_map", label="🔓 Access Map",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("server_management.access_map"),
                custom_id_override="server_management:access_map"),
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
            # row 3 — the shipped panel-manager back-to-help hook's button
            # (help_cog._attach_back_to_help_button: persistent id
            # "help:back", grey, appended on the MESSAGE path only — the
            # override drops it on the slash surface; module docstring).
            PanelActionSpec(
                action_id="help_back", label="↩ Back to Help",
                style=ActionStyle.SECONDARY,
                handler=PanelRef("help.home"),
                custom_id_override="help:back"),
        ),
        # the shipped hub carried NO grammar nav row (both goldens pin
        # its absence); parent=help.home satisfies the never-strand
        # fence honestly (the shipped escape IS Help — the declared
        # help_back action carries the shipped wire byte) and the
        # override drops the grammar's own nav:back button (module
        # docstring).
        navigation=NavigationSpec(parent=PanelRef("help.home"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef("server_management.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Read-only summary · "
            "click a manager to open it' (hub.py set_footer) — outside "
            "FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/servermanagement + goldens/server_management pin "
            "the byte; the utility/ux_lab/channel precedent). The "
            "override additionally adjusts TWO named component surfaces "
            "(the 12c lane): (1) it DROPS the grammar's injected "
            "nav:back:help.home button — the shipped hub never rendered "
            "a grammar nav row, both goldens pin exactly the declared "
            "rows; (2) it DROPS the declared help_back action on the "
            "slash surface — the shipped back-to-help hook appended the "
            "button on the panel-manager MESSAGE path only "
            "(goldens/server_management pins the 4-row prefix shape, "
            "goldens/servermanagement pins the 3-row slash shape). "
            "Body, fields, and every other action stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("moderation", "channels", "roles"),
            ("cleanup", "setup"),
            ("access_map", "help_preview", "help_editor", "sm_refresh"),
            ("help_back",),
        )),)),
    )


# --- renderer override ------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal + the two named
    component drops (see justification): the grammar's injected
    ``nav:back:*`` button always (the shipped hub had no grammar nav
    row), and the declared ``help_back`` action on the slash surface
    (the shipped hook appended it on the message path only)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    components = tuple(
        c for c in rendered.components
        if not str(c.custom_id).startswith("nav:back:")
        and not (c.custom_id == "help:back"
                 and getattr(ctx, "surface", None) == "slash"))
    return _dc_replace(rendered, components=components,
                       embed=_dc_replace(rendered.embed, footer=_FOOTER))


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
