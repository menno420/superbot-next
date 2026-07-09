"""The role panels (band 5) — the shipped RoleHubPanelView (role_cog.py)
as declared grammar: the 7-action hub with the persistent custom_ids
pinned VERBATIM (role:create … role:exemptions). Sub-surfaces render as
RESULT_CARD text views over the DB truth; Create stays a pending
terminal until the role-provisioning port arms (the band-2 honest-wait
precedent).
"""

from __future__ import annotations

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
    TextBlock,
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


def role_hub_spec() -> PanelSpec:
    """The shipped hub embed fields + 7 buttons (ids verbatim)."""
    return PanelSpec(
        panel_id="role.hub",
        subsystem="role",
        title="🎭 Role Hub",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Create, manage, and automate server roles — time "
                      "tiers, XP tiers, reaction roles, and exemptions."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="role_create", label="Create", emoji="📝",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=HandlerRef("role.create_pending"),
                custom_id_override="role:create"),
            PanelActionSpec(
                action_id="role_manage", label="Manage", emoji="🗂️",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("role.manage_view"),
                custom_id_override="role:manage"),
            PanelActionSpec(
                action_id="role_time", label="Time Roles", emoji="⏱️",
                audience_tier="administrator",
                handler=HandlerRef("role.time_roles_view"),
                custom_id_override="role:time"),
            PanelActionSpec(
                action_id="role_xp", label="XP Roles", emoji="⚡",
                audience_tier="administrator",
                handler=HandlerRef("role.xp_roles_view"),
                custom_id_override="role:xp"),
            PanelActionSpec(
                action_id="role_reaction", label="Reaction Roles", emoji="💬",
                audience_tier="administrator",
                handler=HandlerRef("role.reaction_view"),
                custom_id_override="role:reaction"),
            PanelActionSpec(
                action_id="role_diagnostics", label="Diagnostics", emoji="🔧",
                audience_tier="administrator",
                handler=HandlerRef("role.diagnostics_view"),
                custom_id_override="role:diagnostics"),
            PanelActionSpec(
                action_id="role_exemptions", label="Exemptions", emoji="🚫",
                audience_tier="administrator",
                handler=HandlerRef("role.exemptions_view"),
                custom_id_override="role:exemptions"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("role_create", "role_manage", "role_time"),
            ("role_xp", "role_reaction"),
            ("role_diagnostics", "role_exemptions"),
        )),)),
    )


def install_role_panels() -> tuple[PanelSpec, ...]:
    spec = role_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_provider()
    if not _is(_P("role.hub")):
        @_panel("role.hub")
        def _factory():
            return role_hub_spec()
