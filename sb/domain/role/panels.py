"""The role panels (band 5 + the parity flip) — the shipped
RoleHubPanelView (role_cog.py) as declared grammar: the 7-action
anchored hub with the persistent custom_ids pinned VERBATIM
(role:create … role:exemptions). Sub-surfaces render as RESULT_CARD
text views over the DB truth; 📝 Create opens the shipped
`RoleCreateModal` (G-10 ingress) over the live `!createrole` lane
(2026-07-13 operator-hub edits A — the pending terminal is retired).

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
    DeferMode,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
)
from sb.spec.refs import HandlerRef, ProviderRef, is_registered, provider

__all__ = ["INFO_CARD_PANEL_ID", "ensure_panel_refs", "info_card_spec",
           "install_role_panels", "role_hub_spec"]

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


# --- the shipped create modal (views/roles/creation_panel.py
# `RoleCreateModal`, the "✏️ Custom…" free-text form) — G-10 ingress over
# the LIVE `!createrole` lane (the moderation.hub.warn precedent). The
# name/colour fields are oracle-verbatim; the shipped hoist/mentionable
# fields ride the provisioning-port extension (the port's create verb
# carries name+color today — a named successor), and the preset-picker
# creation menu + 📦 Role Packs + the XP-automation follow-up stay the
# creation-menu slice's.
ROLE_CREATE_MODAL = ModalSpec(
    modal_id="role.create_form", title="Create Role",
    fields=(
        ModalFieldSpec(field_id="name", label="Role name",
                       required=True, max_length=100),
        ModalFieldSpec(field_id="color", label="Color (hex, e.g. #3498db)",
                       placeholder="#000000", required=False, max_length=7),
    ),
    on_submit=HandlerRef("role.create_form_submit"))


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
                defer_mode=DeferMode.MODAL, modal=ROLE_CREATE_MODAL,
                handler=HandlerRef("role.create_form_submit"),
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


INFO_CARD_PANEL_ID = "role.info_card"

#: the shipped notable-permission labels walked when a role is not an
#: administrator (utils/role_info summarize_role_permissions) — attribute
#: names against any duck permissions object.
_NOTABLE_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("manage_guild", "Manage Server"),
    ("manage_roles", "Manage Roles"),
    ("manage_channels", "Manage Channels"),
    ("manage_messages", "Manage Messages"),
    ("kick_members", "Kick Members"),
    ("ban_members", "Ban Members"),
    ("moderate_members", "Timeout Members"),
    ("mention_everyone", "Mention Everyone"),
)


def info_card_spec() -> PanelSpec:
    """The read-only role detail card (views/roles/role_info.py
    ``build_role_info_embed`` — a plain ``ctx.send(embed=...)``, never
    anchored: component-less session-lifecycle, the karma.card/welcome
    status-card recipe; goldens/role/sweep_roleinfo pins the bytes)."""
    return PanelSpec(
        panel_id=INFO_CARD_PANEL_ID,
        subsystem="role",
        title="Role Info",
        audience=Audience.INVOKER,
        # ROLE_COLOR teal — the shipped default when role.color is unset;
        # a colored role's own accent is a live-adapter successor (the
        # grammar carries style tokens, not raw colors) — no golden
        # reaches a colored role (the capture world's roles carry color 0).
        frame=EmbedFrameSpec(style_token="teal", footer_mode=FooterMode.NONE),
        body=(),
        actions=(),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("role.render_info_card"),
        justification=(
            "the shipped role detail card is state-parameterized end to "
            "end — every field value (mention, id, colour, live member "
            "count, position, snowflake creation date, hoist/mentionable/"
            "managed flags, the permission summary) and the title itself "
            "carry the TARGET ROLE's live guild state, and the footer "
            "carries the invoker's tag (`Requested by {member}`) — "
            "grammar TextBlocks are static. The card declares no "
            "components; the renderer only composes the embed "
            "(goldens/role/sweep_roleinfo pins the bytes)."),
        session_lifecycle=True,
    )


def _summarize_permissions(perms: object) -> str:
    """utils/role_info summarize_role_permissions verbatim (the
    administrator short-circuit byte is golden-pinned)."""
    if bool(getattr(perms, "administrator", False)):
        return "Administrator (all permissions)"
    held = [label for attr, label in _NOTABLE_PERMISSIONS
            if bool(getattr(perms, attr, False))]
    return ", ".join(held) if held else "No notable permissions"


async def _render_info_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — views/roles/role_info.build_role_info_embed
    verbatim: the ten add_field rows in shipped order (nine inline, the
    permission summary full-width), the `%Y-%m-%d` snowflake creation
    date, the `Requested by {tag}` footer."""
    from datetime import datetime, timezone

    from sb.domain.role import service
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    role_id = int(params.get("roleinfo_role_id", 0) or 0)
    guild = await service.guild_view(guild_id)
    role = (service.find_role(guild, str(role_id))
            if guild is not None else None)

    def _yes_no(flag: object) -> str:
        return "Yes" if bool(flag) else "No"

    name = str(getattr(role, "name", "?"))
    color_value = int(getattr(getattr(role, "color", None), "value",
                              getattr(role, "color_value", 0) or 0) or 0)
    created = datetime.fromtimestamp(
        ((role_id >> 22) + 1_420_070_400_000) / 1000, tz=timezone.utc)
    requested_by = "?"
    try:
        from sb.domain.utility.service import guild_directory

        info = await guild_directory().member_info(
            guild_id, int(getattr(ctx.actor, "user_id", 0) or 0))
        requested_by = str(info.tag)
    except Exception:  # noqa: BLE001 — headless ⇒ degraded footer
        pass
    embed = RenderedEmbed(
        title=f"Role Info — {name}",
        description="",
        fields=(
            ("Mention", f"<@&{role_id}>", True),
            ("ID", str(role_id), True),
            ("Colour",
             f"#{color_value:06x}" if color_value else "Default", True),
            ("Members",
             str(len(tuple(getattr(role, "members", ()) or ()))), True),
            ("Position", str(int(getattr(role, "position", 0) or 0)), True),
            ("Created", created.strftime("%Y-%m-%d"), True),
            ("Hoisted", _yes_no(getattr(role, "hoist", False)), True),
            ("Mentionable",
             _yes_no(getattr(role, "mentionable", False)), True),
            ("Managed", _yes_no(getattr(role, "managed", False)), True),
            ("Key Permissions",
             _summarize_permissions(getattr(role, "permissions", None)),
             False),
        ),
        footer=f"Requested by {requested_by}",
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


def install_role_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (role_hub_spec(), info_card_spec()):
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def _register_hub_render() -> None:
    from sb.spec.refs import handler

    if not is_registered(HandlerRef("role.render_hub")):
        handler("role.render_hub")(_render_hub)
    if not is_registered(HandlerRef("role.render_info_card")):
        handler("role.render_info_card")(_render_info_card)


def _register_info_card_factory() -> None:
    """Registered at MODULE IMPORT (#111 doctrine — the live root never
    runs ENSURE_REFS with zero plugins)."""
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import panel as _panel

    if not is_registered(_P(INFO_CARD_PANEL_ID)):
        @_panel(INFO_CARD_PANEL_ID)
        def _info_factory():
            return info_card_spec()


def _register_hub_factory() -> None:
    """Registered at MODULE IMPORT (#111 doctrine — the live root never
    runs ENSURE_REFS with zero plugins)."""
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import panel as _panel

    if not is_registered(_P("role.hub")):
        @_panel("role.hub")
        def _factory():
            return role_hub_spec()


_register_hub_render()
_register_info_card_factory()
_register_hub_factory()
# the live-count provider left the hub spec at the parity flip (the
# shipped hub renders static blurbs) but stays a registered read
# surface — at MODULE IMPORT, the composition-parity doctrine (#111).
_ensure_hub_provider()


def ensure_panel_refs() -> None:
    _ensure_hub_provider()
    _register_hub_render()
    _register_hub_factory()
    _register_info_card_factory()
