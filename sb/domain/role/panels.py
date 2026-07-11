"""The role panels (band 5 + the parity flip) — the shipped
RoleHubPanelView (role_cog.py) as declared grammar: the 7-action
anchored hub with the persistent custom_ids pinned VERBATIM
(role:create … role:exemptions). Sub-surfaces render as RESULT_CARD
text views over the DB truth; Create stays a pending terminal until the
role-provisioning port arms (the band-2 honest-wait precedent).

Parity-flip shape (``parity/goldens/role/sweep_rolemenu.json`` pins
every byte): the teal embed carries NO description and SEVEN static
inline-true blurb fields (role_cog.py's literal 3-tuple list — outside
the grammar's 2-tuple FieldsBlock vocabulary, which serializes
inline=false, hence the delegation renderer_override); the emoji live
IN the button labels ("📝 Create" — no separate wire emoji field); the
rows split 3/3/1; the nav row is the grammar's own ``nav:help`` +
``nav:hub:community`` slots ("📚 Help" + "↩ Community" —
``home_hub="community"`` explicit, the cleanup/ai/settings precedent,
label from HUB_NAV_LABELS). The hub is ANCHORED (panel-manager
semantics — the golden pins the ``panel_anchors`` row on the prefix
open; ``session_lifecycle`` stays False, the #179 server_management
surface split).

Trap-24 drift check: the oracle current-head role_cog.py field list
(the seven (name, blurb, True) tuples) matches the corpus golden
byte-for-byte — NO drift (corpus sha 7f7628e1). Trap-28: no
role-family entries in _sweep_skips.json.

Under-port note: the band-5 live-count hub provider
(``role.hub_overview`` — tier/binding/exemption counts) stays
registered but is no longer on the hub; the SHIPPED hub rendered the
static blurbs the golden pins. Three `_unmapped` sweeps
(sweep_roles / sweep_rolecreator / sweep_rolesettings) pin this same
view — re-home candidates (the #155 lane).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
)
from sb.spec.refs import HandlerRef, ProviderRef, is_registered, provider

__all__ = ["ensure_panel_refs", "install_role_panels", "role_hub_spec"]

_HUB_PROVIDER = "role.hub_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.role import store

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            thresholds = await store.get_thresholds(guild_id)
            bindings = await store.list_reaction_bindings(guild_id)
            menus = await store.list_menus(guild_id)
            exemptions = await store.get_exemptions(guild_id)
            time_rows = [t for t in thresholds if t["days_required"]]
            xp_rows = [t for t in thresholds if t.get("xp_auto_assign")]
            return (
                ("⏱️ Time Roles", f"{len(time_rows)} tier(s) configured"),
                ("⚡ XP Roles", f"{len(xp_rows)} tier(s) configured"),
                ("💬 Reaction Roles",
                 f"{len(bindings)} binding(s), {len(menus)} menu(s)"),
                ("🚫 Exemptions", f"{len(exemptions)} exempt role(s)"),
            )
    return ref


#: the shipped hub blurb fields (role_cog.py's literal (name, value,
#: inline=True) list, verbatim — the golden pins every byte).
_HUB_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("📝 Create", "Create a new server role", True),
    ("🗂️ Manage", "View, edit, or delete roles", True),
    ("⏱️ Time Roles", "Days-in-server auto-assignment", True),
    ("⚡ XP Roles", "Level-based auto-assignment", True),
    ("💬 Reaction Roles", "Emoji reaction role bindings", True),
    ("🔧 Diagnostics", "System status & debug tools", True),
    ("🚫 Exemptions", "Exempt roles from XP/time automation", True),
)


def role_hub_spec() -> PanelSpec:
    """The shipped hub embed fields + 7 buttons (ids verbatim)."""
    return PanelSpec(
        panel_id="role.hub",
        subsystem="role",
        title="🎭 Role Hub",
        audience=Audience.INVOKER,
        # the shipped teal accent (discord.Color.teal()); no footer.
        frame=EmbedFrameSpec(style_token="teal", footer_mode=FooterMode.NONE),
        body=(),
        actions=(
            # the shipped styles + emoji-in-label wire shape (the golden
            # pins no separate emoji field on any button).
            PanelActionSpec(
                action_id="role_create", label="📝 Create",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=HandlerRef("role.create_pending"),
                custom_id_override="role:create"),
            PanelActionSpec(
                action_id="role_manage", label="🗂️ Manage",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("role.manage_view"),
                custom_id_override="role:manage"),
            PanelActionSpec(
                action_id="role_time", label="⏱️ Time Roles",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("role.time_roles_view"),
                custom_id_override="role:time"),
            PanelActionSpec(
                action_id="role_xp", label="⚡ XP Roles",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("role.xp_roles_view"),
                custom_id_override="role:xp"),
            PanelActionSpec(
                action_id="role_reaction", label="💬 Reaction Roles",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("role.reaction_view"),
                custom_id_override="role:reaction"),
            PanelActionSpec(
                action_id="role_diagnostics", label="🔧 Diagnostics",
                audience_tier="administrator",
                handler=HandlerRef("role.diagnostics_view"),
                custom_id_override="role:diagnostics"),
            PanelActionSpec(
                action_id="role_exemptions", label="🚫 Exemptions",
                audience_tier="administrator",
                handler=HandlerRef("role.exemptions_view"),
                custom_id_override="role:exemptions"),
        ),
        # the shipped nav row: 📚 Help + ↩ Community (the grammar's own
        # nav:help / nav:hub:community slots — home_hub explicit, the
        # cleanup/ai/settings precedent; the golden pins both bytes).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="community"),
        renderer_override=HandlerRef("role.render_hub"),
        justification=(
            "the shipped hub embed carries SEVEN static inline-true "
            "blurb fields and no description (role_cog.py's literal "
            "(name, value, True) add_field list — "
            "goldens/role/sweep_rolemenu pins every byte incl. the "
            "inline flags); the grammar's FieldsBlock serializes "
            "2-tuples inline=false, so the override delegates to the "
            "grammar renderer for every component and replaces only "
            "the embed fields (the economy delegation recipe). Title, "
            "color and every component stay grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("role_create", "role_manage", "role_time"),
            ("role_xp", "role_reaction", "role_diagnostics"),
            ("role_exemptions",),
        )),)),
    )


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped static blurb fields (see
    justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, description="",
                                         fields=_HUB_FIELDS))


def install_role_panels() -> tuple[PanelSpec, ...]:
    spec = role_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def _register_hub_render() -> None:
    from sb.spec.refs import handler

    if not is_registered(HandlerRef("role.render_hub")):
        handler("role.render_hub")(_render_hub)


_register_hub_render()
# the live-count provider left the hub spec at the parity flip (the
# shipped hub renders static blurbs) but stays a registered read
# surface — at MODULE IMPORT, the composition-parity doctrine (#111).
_ensure_hub_provider()


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_provider()
    _register_hub_render()
    if not _is(_P("role.hub")):
        @_panel("role.hub")
        def _factory():
            return role_hub_spec()
