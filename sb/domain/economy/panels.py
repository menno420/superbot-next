"""The economy panels (band 3) — the hub WITH its shipped action set (the
panel-action slice), the Job Center sub-panel (the shipped `_WorkSubView`
dropdown as a declared selector over the audited `economy.work` op), and the
Shop sub-panel (the shipped `_ShopSubView` item picker over `economy.buy`).

Shipped custom_ids (`economy:daily` … `economy:overview`) are pinned
VERBATIM via `custom_id_override` — the persistent-view click vocabulary the
old goldens replay. Back/nav ids are engine-owned (`nav:*`, the band-1
convention): the shipped `economy:back`/`economy:shop:back`/
`economy:work:back` closures are replaced by the §2.4 serializable nav —
ledgered deviation, D-0034."""

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
    ResultRender,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    WorkflowRef,
    handler,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "DAILY_CARD_PANEL_ID",
    "WALLET_CARD_PANEL_ID",
    "daily_card_spec",
    "economy_hub_spec",
    "ensure_panel_refs",
    "install_economy_panels",
    "jobcenter_spec",
    "shop_panel_spec",
    "wallet_card_spec",
]

DAILY_CARD_PANEL_ID = "economy.daily_card"
WALLET_CARD_PANEL_ID = "economy.wallet_card"

_HUB_PROVIDER = "economy.hub_overview"
_JOBCENTER_PROVIDER = "economy.jobcenter_overview"
_JOBS_PROVIDER = "economy.available_jobs"
_SHOP_PROVIDER = "economy.shop_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.economy import catalogue, service, store

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(ctx, "user_id", 0) or
                          getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            fields = [
                ("Jobs", f"{len(catalogue.JOBS)} jobs across 4 tiers — "
                         f"`!work <job>` (1h cooldown)"),
                ("Shop", ", ".join(
                    f"{d['emoji']} {name} ({d['price']:,})"
                    for name, d in catalogue.SHOP_ITEMS.items())),
                ("Daily", "`!daily` — streaks shift the reward odds upward"),
            ]
            if user_id:
                coins = await store.get_coins(user_id, guild_id)
                row = await store.read_economy(user_id, guild_id)
                fields.insert(0, ("Your wallet",
                                  f"🪙 {coins:,} · 🔥 streak "
                                  f"{row.get('daily_streak', 0)}"))
            log_channel = await service.bound_log_channel(guild_id)
            fields.append(("Log channel",
                           f"<#{log_channel}>" if log_channel
                           else "*(unbound — `!setlogchannel #channel`)*"))
            return tuple(fields)
    return ref


def _ensure_jobcenter_provider() -> ProviderRef:
    ref = ProviderRef(_JOBCENTER_PROVIDER)
    if not is_registered(ref):
        @provider(_JOBCENTER_PROVIDER)
        async def jobcenter_overview(ctx: object):
            from sb.domain.economy import service, store

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            level = await service.active_level_reader()(user_id, guild_id)
            coins = await store.get_coins(user_id, guild_id)
            return (
                ("Level", str(level)),
                ("Coins", f"{coins:,} 🪙"),
            )
    return ref


def _ensure_jobs_provider() -> ProviderRef:
    ref = ProviderRef(_JOBS_PROVIDER)
    if not is_registered(ref):
        @provider(_JOBS_PROVIDER)
        async def available_jobs_options(ctx: object):
            """Rich select options — the shipped ``_JobSelect`` rows
            verbatim (views/economy/work_panel.py: emoji+title label, the
            BASE-pay description line; goldens/economy/sweep_work pins the
            bytes)."""
            from sb.domain.economy import catalogue, service

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            available = await service.available_jobs(user_id, guild_id)
            return tuple(
                {"label": (f"{catalogue.JOBS[name]['emoji']} "
                           f"{name.replace('_', ' ').title()}"),
                 "value": name,
                 "description": (f"Base pay: {catalogue.JOBS[name]['pay']} 🪙"
                                 f"  |  +{catalogue.JOBS[name]['xp']} XP"
                                 f"  |  Tier {catalogue.JOBS[name]['tier']}")}
                for name in available)
    return ref


def _ensure_shop_provider() -> ProviderRef:
    ref = ProviderRef(_SHOP_PROVIDER)
    if not is_registered(ref):
        @provider(_SHOP_PROVIDER)
        async def shop_overview(ctx: object):
            from sb.domain.economy import catalogue

            return tuple(
                (f"{d['emoji']} {name.replace('_', ' ').title()} — "
                 f"{d['price']:,} 🪙",
                 d["desc"])
                for name, d in catalogue.SHOP_ITEMS.items())
    return ref


def economy_hub_spec() -> PanelSpec:
    # Button labels carry the shipped glyph INSIDE the label (the old
    # discord.ui.Button(label="🎁 Daily") form — no separate emoji field on
    # the wire; goldens/economy/sweep_economymenu pins the bytes).
    return PanelSpec(
        panel_id="economy.hub",
        subsystem="economy",
        title="💰 Economy Panel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Daily rewards, jobs, the item shop, and transfers — "
                      "every coin movement rides the audited seam and the "
                      "economy_audit_log money trail."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            # Row 0 — the shipped earn loop (main_panel.py, ids verbatim).
            PanelActionSpec(
                action_id="daily", label="🎁 Daily",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=WorkflowRef("economy.daily"),
                audit="economy.balance_changed",
                custom_id_override="economy:daily"),
            PanelActionSpec(
                action_id="work", label="💼 Work",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("economy.jobcenter"),
                custom_id_override="economy:work"),
            PanelActionSpec(
                action_id="shop", label="🛒 Shop",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("economy.shop_panel"),
                custom_id_override="economy:shop"),
            # Row 1 — the shipped read/browse set.
            PanelActionSpec(
                action_id="balance", label="💰 Balance",
                audience_tier="user",
                handler=HandlerRef("economy.balance_view"),
                custom_id_override="economy:balance"),
            PanelActionSpec(
                action_id="inventory", label="🎒 Inventory",
                audience_tier="user",
                handler=PanelRef("inventory.hub"),
                custom_id_override="economy:inventory"),
            PanelActionSpec(
                action_id="jobs", label="📋 Jobs",
                audience_tier="user",
                handler=HandlerRef("economy.joblist_view"),
                custom_id_override="economy:jobs"),
            PanelActionSpec(
                action_id="treasury", label="🏛️ Treasury",
                audience_tier="user",
                handler=PanelRef("treasury.hub"),
                custom_id_override="economy:treasury"),
            # Row 2 — the shipped refresh-to-overview control.
            PanelActionSpec(
                action_id="overview", label="↩ Overview",
                audience_tier="user",
                handler=PanelRef("economy.hub"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="economy:overview"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("daily", "work", "shop"),
            ("balance", "inventory", "jobs", "treasury"),
            ("overview",),
        )),)),
        renderer_override=HandlerRef("economy.render_hub"),
        justification=(
            "the shipped Economy Panel embed (services/economy_helpers.py "
            "_build_economy_embed) is state-dependent copy the grammar "
            "cannot express; the override delegates the COMPONENTS to "
            "render_panel (declared actions/nav untouched) and adjusts the "
            "EMBED surfaces only: the invoker author line "
            "(set_author(display_name, avatar)), the five INLINE stat "
            "fields (🪙 Coins / 🏆 Level / 🔥 Daily Streak and the "
            "cooldown-derived 🎁 Daily / 💼 Work '✅ Available!'-or-⏰ "
            "values), the footer literal ('Use the buttons below to take "
            "actions.'), and drops the grammar description (the shipped "
            "embed had none). The open ALSO runs the shipped "
            "ensure_and_get_economy read-that-writes (the goldens pin the "
            "zero-row economy db_delta on every hub open)."),
    )


def jobcenter_spec() -> PanelSpec:
    """The shipped Job Center (`_WorkView`): per-user eligible-job dropdown
    whose pick runs the audited `economy.work` op. ``session_lifecycle=True``
    — the shipped view was a timeout ``BaseView`` with a run-minted select
    id, never an anchored panel (goldens/economy/sweep_work pins the
    ``<cid:N>`` id and the no-anchor-row db_delta)."""
    return PanelSpec(
        panel_id="economy.jobcenter",
        subsystem="economy",
        title="💼 Job Center",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Choose a job below.\n"
                      "Pay increases **+1%** each time you work the same "
                      "job (max +100%)."),
            FieldsBlock(provider=_ensure_jobcenter_provider()),
        ),
        selectors=(
            SelectorSpec(
                selector_id="job_select", kind=SelectorKind.ENTITY,
                on_select=WorkflowRef("economy.work"),
                options_source=_ensure_jobs_provider(),
                placeholder="Choose a job to work…",
                empty_state="❌ No jobs available. Earn XP or buy items "
                            "from 🛒 Shop.",
                audience_tier="user"),
        ),
        # the shipped bare-!work view carried NO nav controls (the golden
        # pins the single select row); the hub's 💼 Work button re-opens
        # the hub via economy:overview, not a back button.
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("job_select",),)),)),
        renderer_override=HandlerRef("economy.render_jobcenter"),
        justification=(
            "the shipped Job Center embed (economy_cog.work) mixes grammar "
            "and non-grammar surfaces; the override delegates the "
            "COMPONENTS to render_panel (the declared selector, options "
            "provider untouched) and adjusts the EMBED only: the two INLINE "
            "stat fields (Level / Coins — grammar fields render "
            "non-inline), the footer literal ('Pick a job from the "
            "dropdown.'), keeping the grammar TextBlock description "
            "verbatim."),
        session_lifecycle=True,
    )


def shop_panel_spec() -> PanelSpec:
    """The shipped shop panel (`_ShopSubView`): static item picker whose
    pick runs the audited `economy.buy` op (Q-0071 — grant-first,
    audited-debit-second, raced clicks re-decided in-txn)."""
    from sb.domain.economy.catalogue import SHOP_ITEMS

    return PanelSpec(
        panel_id="economy.shop_panel",
        subsystem="economy",
        title="🛒 Item Shop",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Buy items to unlock higher-tier jobs. Purchases are "
                      "unique — one of each per member."),
            FieldsBlock(provider=_ensure_shop_provider()),
        ),
        selectors=(
            SelectorSpec(
                selector_id="item_select", kind=SelectorKind.ENTITY,
                on_select=WorkflowRef("economy.buy"),
                options_source=tuple(SHOP_ITEMS),
                placeholder="Select an item to buy…",
                empty_state="The shop is empty.",
                audience_tier="user"),
        ),
        navigation=NavigationSpec(parent=PanelRef("economy.hub")),
        layout=LayoutSpec(pages=(PageSpec(rows=(("item_select",),)),)),
    )


def daily_card_spec() -> PanelSpec:
    """The shipped Daily Reward embed (cogs/economy_cog.py `daily`) — a
    component-less per-claim result card. ``session_lifecycle=True`` because
    the shipped send was a transient result message, never a refreshable
    panel_anchors panel (and it has no components to re-bind anyway)."""
    return PanelSpec(
        panel_id=DAILY_CARD_PANEL_ID,
        subsystem="economy",
        title="🎁 Daily Reward",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("economy.render_daily_card"),
        justification=(
            "the shipped Daily Reward embed is claim-parameterized copy on "
            "every line (tier description, four inline stat fields, the "
            "streak-derived odds footer, the invoker author line — "
            "cogs/economy_cog.py); grammar TextBlocks are static. The card "
            "declares no components; the renderer only composes the embed."),
        session_lifecycle=True,
    )


def wallet_card_spec() -> PanelSpec:
    """The shipped `!balance` Wallet embed (cogs/economy_cog.py balance) —
    a component-less per-read result card, exactly the daily-card shape:
    ``session_lifecycle=True`` because the shipped send was a transient
    result message, never a refreshable panel_anchors panel."""
    return PanelSpec(
        panel_id=WALLET_CARD_PANEL_ID,
        subsystem="economy",
        title="💰 Wallet",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("economy.render_wallet_card"),
        justification=(
            "the shipped Wallet embed is read-parameterized on every "
            "surface (the target-member title '💰 <name>'s Wallet', the "
            "avatar thumbnail, two INLINE stat fields with the bolded "
            "coin count — cogs/economy_cog.py balance); grammar "
            "TextBlocks are static and grammar fields render non-inline. "
            "The card declares no components; the renderer only composes "
            "the embed."),
        session_lifecycle=True,
    )


async def _render_wallet_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped balance embed verbatim: the
    name-parameterized title, gold accent, avatar thumbnail, and the two
    inline fields (`**{coins:,}**` / level)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    name = str(params.get("wallet_name", "") or "")
    coins = int(params.get("coins", 0) or 0)
    embed = RenderedEmbed(
        title=f"💰 {name}'s Wallet",
        description="",
        fields=(
            ("🪙 Coins", f"**{coins:,}**", True),
            ("🏆 Level", str(params.get("level", 0)), True),
        ),
        style_token=spec.frame.style_token,
        thumbnail_ref=str(params.get("wallet_icon", "") or ""))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _member_display(user_id: int, guild_id: int) -> tuple[str, str]:
    """(display name, avatar url) through the guild-directory read port —
    the shipped ``user.display_name`` / ``user.display_avatar.url`` pair
    for renderer paths that carry no origin message. Degrades to an empty
    author line when no directory is armed (never invents data)."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ no author line
        return "", ""
    return member.tag.rsplit("#", 1)[0], member.display_avatar_url


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped Economy Panel embed verbatim
    (services/economy_helpers.py _build_economy_embed): author line, gold
    accent, five inline stat fields (two cooldown-derived), the footer
    literal. Components come from the grammar render untouched. The open
    runs the shipped ensure-and-read (a read that WRITES the missing
    tracking row — the oracle's ensure_and_get_economy posture)."""
    import dataclasses
    import time as _time

    from sb.domain.economy import catalogue, service, store
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    row = await store.ensure_tracking_row(uid, gid)
    coins = await store.get_coins(uid, gid)
    level = await service.active_level_reader()(uid, gid)
    now = int(_time.time())
    on_cd_daily, secs_daily = service.check_cooldown(
        int(row.get("last_daily", 0) or 0), catalogue.DAILY_COOLDOWN, now=now)
    on_cd_work, secs_work = service.check_cooldown(
        int(row.get("last_worked", 0) or 0), catalogue.WORK_COOLDOWN, now=now)
    name, icon = await _member_display(uid, gid)
    embed = RenderedEmbed(
        title=spec.title,
        description="",     # the shipped panel embed had no description
        fields=(
            ("🪙 Coins", f"{coins:,}", True),
            ("🏆 Level", str(level), True),
            ("🔥 Daily Streak", str(row.get("daily_streak", 0)), True),
            ("🎁 Daily",
             "✅ Available!" if not on_cd_daily
             else f"⏰ {service.format_remaining(secs_daily)}", True),
            ("💼 Work",
             "✅ Available!" if not on_cd_work
             else f"⏰ {service.format_remaining(secs_work)}", True),
        ),
        footer="Use the buttons below to take actions.",
        style_token=spec.frame.style_token,
        author_name=name, author_icon=icon)
    return dataclasses.replace(base, embed=embed)


async def _render_jobcenter(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped Job Center embed verbatim
    (economy_cog.work): blue accent, the grammar TextBlock description
    kept, two inline stat fields, the footer literal. Components (the job
    select) come from the grammar render untouched."""
    import dataclasses

    from sb.domain.economy import service, store
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    level = await service.active_level_reader()(uid, gid)
    coins = await store.get_coins(uid, gid)
    embed = RenderedEmbed(
        title=spec.title,
        description=base.embed.description,
        fields=(
            ("Level", str(level), True),
            # the shipped value is the raw int (no thousands separator —
            # economy_cog.work read xp_row['coins'] unformatted).
            ("Coins", f"{coins} 🪙", True),
        ),
        footer="Pick a job from the dropdown.",
        style_token=spec.frame.style_token)
    return dataclasses.replace(base, embed=embed)


async def _render_daily_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped daily embed verbatim: author line,
    gold accent, tier description, the four inline fields, the odds
    footer (`Current odds → <label>: <w:.1f>% · …`)."""
    from sb.domain.economy import catalogue
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    amount = int(params.get("amount", 0) or 0)
    balance = int(params.get("coins", 0) or 0)
    streak = int(params.get("streak", 0) or 0)
    claims = int(params.get("claims", 0) or 0)
    weights = catalogue.daily_weights(streak)
    odds = " · ".join(
        f"{tier[0]}: {weight:.1f}%"
        for tier, weight in zip(catalogue.DAILY_TIERS, weights, strict=True))
    embed = RenderedEmbed(
        title=spec.title,
        description=(f"{params.get('tier_emoji', '')} "
                     f"**{params.get('tier', '')}** reward!"),
        fields=(
            ("Coins earned", f"**+{amount}** 🪙", True),
            ("Balance", f"**{balance}** 🪙", True),
            ("Streak", f"🔥 **{streak}** days", True),
            ("Total claims", str(claims), True),
        ),
        footer=f"Current odds → {odds}",
        style_token=spec.frame.style_token,
        author_name=str(params.get("author_name", "") or ""),
        author_icon=str(params.get("author_icon", "") or ""))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel("economy.hub")
def _hub_factory() -> PanelSpec:
    return economy_hub_spec()


@panel("economy.jobcenter")
def _jobcenter_factory() -> PanelSpec:
    return jobcenter_spec()


@panel("economy.shop_panel")
def _shop_factory() -> PanelSpec:
    return shop_panel_spec()


@panel(DAILY_CARD_PANEL_ID)
def _daily_card_factory() -> PanelSpec:
    return daily_card_spec()


@panel(WALLET_CARD_PANEL_ID)
def _wallet_card_factory() -> PanelSpec:
    return wallet_card_spec()


handler("economy.render_daily_card")(_render_daily_card)
handler("economy.render_wallet_card")(_render_wallet_card)
handler("economy.render_hub")(_render_hub)
handler("economy.render_jobcenter")(_render_jobcenter)


def install_economy_panels() -> tuple[PanelSpec, ...]:
    specs = (economy_hub_spec(), jobcenter_spec(), shop_panel_spec(),
             daily_card_spec(), wallet_card_spec())
    out = []
    for spec in specs:
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    _ensure_jobcenter_provider()
    _ensure_jobs_provider()
    _ensure_shop_provider()
    for pid, factory in (("economy.hub", _hub_factory),
                         ("economy.jobcenter", _jobcenter_factory),
                         ("economy.shop_panel", _shop_factory),
                         (DAILY_CARD_PANEL_ID, _daily_card_factory),
                         (WALLET_CARD_PANEL_ID, _wallet_card_factory)):
        if not _is(_P(pid)):
            _panel(pid)(factory)
    for hid, fn in (("economy.render_daily_card", _render_daily_card),
                    ("economy.render_wallet_card", _render_wallet_card),
                    ("economy.render_hub", _render_hub),
                    ("economy.render_jobcenter", _render_jobcenter)):
        if not is_registered(HandlerRef(hid)):
            handler(hid)(fn)
