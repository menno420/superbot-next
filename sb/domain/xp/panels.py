"""The XP hub panel (band 4) — the shipped `_XpHubView` declaratively:
the invoker's rank overview (provider-fed fields) + the admin action row
(Give XP / Reset XP as G-10 modals over the audited K7 ops; the shipped
`_GiveXpModal`/`_ResetXpModal` one-form flows). The shipped Both/XP/Coins
stat toggles are the `!rank <stat>` text routes (in-place attachment
swapping is presentation the live adapter owns — deviation ledgered).

Shipped XP-hub buttons carried no persistent custom_ids (view-local
decorators), so no `custom_id_override` pins are needed here.
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    ProviderRef,
    WorkflowRef,
    is_registered,
    panel,
    provider,
)

__all__ = ["ensure_panel_refs", "install_xp_panels", "xp_hub_spec"]

_HUB_PROVIDER = "xp.hub_overview"

GIVEXP_MODAL = ModalSpec(
    modal_id="xp.givexp_form",
    title="Give XP",                              # shipped modal title
    fields=(
        ModalFieldSpec(field_id="user", label="Member (mention or id)",
                       placeholder="@member or 123456789", required=True,
                       max_length=40),
        ModalFieldSpec(field_id="amount", label="Amount of XP",
                       placeholder="e.g. 100", required=True, max_length=10),
    ),
    on_submit=WorkflowRef("xp.award"),
)

RESETXP_MODAL = ModalSpec(
    modal_id="xp.resetxp_form",
    title="Reset a member's XP",                  # shipped modal title
    fields=(
        ModalFieldSpec(field_id="user", label="Member (mention or id)",
                       placeholder="@member or 123456789", required=True,
                       max_length=40),
    ),
    on_submit=WorkflowRef("xp.reset"),
)


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.xp import service, store
            from sb.domain.xp.levels import level_progress

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            fields = []
            if user_id:
                row = await store.get_xp(user_id, guild_id)
                level, current, needed = level_progress(int(row["xp"]))
                fields.append(("Your rank",
                               f"Level **{level}** · {row['xp']} XP · "
                               f"{current}/{needed} into the next level"))
                fields.append(("Messages", str(row["messages"])))
            xp_min, xp_max, cooldown = await service.xp_config(guild_id)
            fields.append(("Chat awards",
                           f"{xp_min}–{xp_max} XP per message · "
                           f"{cooldown}s cooldown"))
            channel_id = await service.bound_announce_channel(guild_id)
            fields.append(("Level-up channel",
                           f"<#{channel_id}>" if channel_id
                           else "*(same channel as the message)*"))
            return tuple(fields)
    return ref


def xp_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="xp.hub",
        subsystem="xp",
        title="🏆 XP Panel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Chat to earn XP and level up. `!rank` shows your "
                      "card; admins configure via the settings hub."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="rank", label="My Rank", emoji="📊",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("xp.rank_view")),
            PanelActionSpec(
                action_id="config", label="Configure", emoji="⚙️",
                audience_tier="",                 # ADMIN floor (shipped)
                handler=HandlerRef("xp.xpconfig_view")),
            PanelActionSpec(
                action_id="givexp", label="Give XP", emoji="🎁",
                audience_tier="",                 # ADMIN floor (shipped)
                defer_mode=DeferMode.MODAL,
                modal=GIVEXP_MODAL,
                handler=WorkflowRef("xp.award"),
                audit="xp.awarded"),
            PanelActionSpec(
                action_id="resetxp", label="Reset XP", emoji="🔄",
                style=ActionStyle.DANGER, audience_tier="",
                destructive=True,
                defer_mode=DeferMode.MODAL,
                modal=RESETXP_MODAL,
                confirm=ConfirmationSpec(reversibility="irreversible",
                                         challenge=Challenge.TYPED_PHRASE),
                handler=WorkflowRef("xp.reset"),
                audit="xp.reset"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("rank", "config"),
            ("givexp", "resetxp"),                # danger never row 0
        )),)),
    )


@panel("xp.hub")
def _hub_factory() -> PanelSpec:
    return xp_hub_spec()


def install_xp_panels() -> PanelSpec:
    spec = xp_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_provider()
    if not _is(_P("xp.hub")):
        _panel("xp.hub")(_hub_factory)
