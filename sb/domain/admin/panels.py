"""The ADMIN hub panel (parity flip) — the shipped ``_AdminPanelView``
(disbot/cogs/admin_cog.py, the consolidated Server & Admin section from
the oracle's help-menu regrouping PR #1290): the ⚙️ red embed (the
"Loaded cogs: **58**" legend over the Tools / Configure & Operate /
Platform & Diagnostics sections; ADMIN_COLOR = discord.Color.red(); the
"Only you can interact with this panel." footer) over four button rows —
the Tools quartet (Server Stats / Cog List blurple, Reload All / Log
Level grey), the Configure & Operate quartet (Settings / Server
Management / Channels / AI blurple), the Platform & Diagnostics quintet
(Platform / Diagnostics / UX Lab / Logging / Cleanup blurple), and the
Help + ↩ Overview tail. ``parity/goldens/admin/sweep_adminmenu.json``
pins every byte of the prefix open; ``sweep_slash_admin.json`` pins the
``/admin`` ephemeral type-4 twin (flags 64 — the grammar's INVOKER
audience; slash+PanelRef resolves DeferMode.NONE).

SESSION-VIEW SEMANTICS: the shipped view was a timeout-bound session
view (``HubView`` family, invoker-locked), so ``session_lifecycle=True``
— custom_ids are run-minted (both goldens pin ``<cid:N>``-shaped ids),
no ``panel_anchors`` row is recorded (the prefix golden's db_delta
carries only the kernel ingress rows), and the never-strand fence takes
the session-view exemption (the goldens pin exactly the four declared
rows — no nav slots; the general.menu precedent).

CAPTURE-WORLD LITERAL (trap 10a): the shipped description interpolated
``len(bot.cogs)`` — the capture world's 58 loaded cogs. Both goldens pin
the one value, so the line ships as the pinned literal; the live
manifest-registry count (via ``admin.subsystems_view``) is the honest
successor read if a future golden pins a second value.

Trap-24 drift check (mandatory pre-step): the oracle's CURRENT-head
``admin_cog.py`` fragments (title, description sections, footer,
ADMIN_COLOR, the four-row button order incl. the row-3 "overview anchor
(rebuilds this panel in place)" comment) match the corpus goldens
byte-for-byte — NO drift on this row (corpus sha 7f7628e1).

Trap-28 check: ``parity/goldens/_sweep_skips.json`` lists the
admin-family ``force`` / ``loadall`` / ``unloadall`` / ``syncslash`` /
``restart`` / ``system_info`` captures as deliberately skipped — this
flip declares NONE of them anew (the pre-existing band-2 ``restart``
CommandSpec over the K5 lifecycle seam predates the flip and stays as
designed; ``cog``/``loadall``/``unloadall``/``syncslash`` remain
unported deploy-ops per the manifest header / D-0030).

Deliberate under-port notes (parity beyond the goldens — no golden
drives any click on this surface):
* the shipped Reload All reloaded every discord.py extension in-process
  (deploy-ops, the _sweep_skips ``unloadall`` class) — the click lands
  on a declared + honest pending terminal;
* the shipped Log Level button opened ``_LogLevelModal`` (a SET flow);
  the port routes the click to the ``admin.loglevel`` READ (shows the
  current sb level) — the modal SETTER is a successor slice on the
  armed G-10 lane (#165);
* the shipped navigation buttons routed into the sibling cog hubs via
  ``build_help_menu_view`` — every ported target routes for real
  (settings.hub / server_management.hub / channel.hub / ai.hub /
  diagnostic.platform_hub / diagnostic.hub / ux_lab.home / logging.hub /
  cleanup.hub / help.home); ↩ Overview rebuilds this panel in place
  (the shipped row-3 "overview anchor" — REFRESH_PANEL).
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
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "admin_hub_spec",
    "ensure_panel_refs",
    "install_admin_panels",
    "server_stats_spec",
]

#: the shipped embed description (admin_cog.py ``_panel_embed`` —
#: ``Loaded cogs: **{len(bot.cogs)}**`` interpolated 58 in the capture
#: world; both goldens pin the literal — module docstring, trap 10a).
_DESCRIPTION = (
    "Loaded cogs: **58**\n\n"
    "**Tools**\n"
    "📊 Server Stats · 📋 Cog List · 🔄 Reload All · 📝 Log Level\n\n"
    "**Configure & Operate**\n"
    "🛠 Settings · 🧭 Server Management · 📐 Channels · 🤖 AI\n\n"
    "**Platform & Diagnostics**\n"
    "🛰 Platform · 🩺 Diagnostics · 🧪 UX Lab · 📝 Logging · 🧹 Cleanup\n\n"
    "📚 Help"
)

#: the shipped footer literal (admin_cog.py ``set_footer`` — the shared
#: invoker-lock footer) — outside FooterMode's vocabulary, hence the
#: renderer_override below (the server_management/utility precedent).
_FOOTER = "Only you can interact with this panel."


def _nav(action_id: str, label: str, target: str) -> PanelActionSpec:
    """One shipped blurple navigation button routed to its PORTED panel
    (the shipped ``build_help_menu_view`` hop; K1 claims action_ids bare
    and repo-global, hence the ``admin_`` prefixes — the run-minted
    session ids never reach the wire, both goldens pin ``<cid:N>``)."""
    return PanelActionSpec(
        action_id=action_id, label=label, style=ActionStyle.PRIMARY,
        audience_tier="administrator",       # the shipped admin floor
        handler=PanelRef(target))


def admin_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="admin.hub",
        subsystem="admin",
        title="⚙️ Server & Admin",
        # invoker-locked session view; the slash twin's type-4 carries
        # flags 64 (goldens/admin/sweep_slash_admin).
        audience=Audience.INVOKER,
        # ADMIN_COLOR = discord.Color.red() (the shipped accent).
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock(_DESCRIPTION),),
        actions=(
            # row 0 — Tools (Server Stats / Cog List blurple; Reload All /
            # Log Level grey — the shipped styles, golden-pinned).
            PanelActionSpec(
                action_id="server_stats", label="📊 Server Stats",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("admin.serverstats_view")),
            # the shipped 📋 Cog List button opened the Cog Manager view
            # (admin_cog.py: `!coglist` — "the panel's 📋 Cog List
            # button") — routed for real since the sweep_coglist re-home
            # (sb/domain/admin/cogmgr.py; `admin.subsystems_view` stays
            # the honest manifest-registry read for successor slices).
            PanelActionSpec(
                action_id="cog_list", label="📋 Cog List",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=PanelRef("admin.cogmgr")),
            PanelActionSpec(
                action_id="reload_all", label="🔄 Reload All",
                audience_tier="administrator",
                handler=HandlerRef("admin.reload_all_pending")),
            PanelActionSpec(
                action_id="log_level", label="📝 Log Level",
                audience_tier="administrator",
                handler=HandlerRef("admin.loglevel")),
            # row 1 — Configure & Operate (all ported hubs).
            _nav("admin_settings", "🛠 Settings", "settings.hub"),
            _nav("admin_sm", "🧭 Server Management", "server_management.hub"),
            _nav("admin_channels", "📐 Channels", "channel.hub"),
            _nav("admin_ai", "🤖 AI", "ai.hub"),
            # row 2 — Platform & Diagnostics (all ported hubs).
            _nav("admin_platform", "🛰 Platform", "diagnostic.platform_hub"),
            _nav("admin_diagnostics", "🩺 Diagnostics", "diagnostic.hub"),
            _nav("admin_uxlab", "🧪 UX Lab", "ux_lab.home"),
            _nav("admin_logging", "📝 Logging", "logging.hub"),
            _nav("admin_cleanup", "🧹 Cleanup", "cleanup.hub"),
            # row 3 — Help + the shipped grey overview anchor ("rebuilds
            # this panel in place" — admin_cog.py row-3 comment).
            _nav("admin_help", "📚 Help", "help.home"),
            PanelActionSpec(
                action_id="admin_overview", label="↩ Overview",
                audience_tier="administrator",
                handler=PanelRef("admin.hub"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        # the shipped view carried ONLY its own buttons (session view, no
        # nav slots) — both goldens pin exactly four component rows, so
        # the never-strand fence takes the session-view exemption (the
        # general.menu precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("admin.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Only you can "
            "interact with this panel.' (admin_cog.py set_footer — the "
            "shared invoker-lock footer) — outside FooterMode's "
            "none/subsystem/provenance vocabulary "
            "(goldens/admin/sweep_adminmenu + sweep_slash_admin pin the "
            "byte; the server_management/utility precedent). The "
            "override adjusts ONLY the embed footer; body, title, color "
            "and every component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("server_stats", "cog_list", "reload_all", "log_level"),
            ("admin_settings", "admin_sm", "admin_channels", "admin_ai"),
            ("admin_platform", "admin_diagnostics", "admin_uxlab",
             "admin_logging", "admin_cleanup"),
            ("admin_help", "admin_overview"),
        )),)),
    )


# --- the serverstats card ---------------------------------------------------------

def server_stats_spec() -> PanelSpec:
    """The shipped ``!serverstats`` census embed (admin_cog.py
    ``server_stats``: ``f"Server Stats for {guild.name}"``, SUCCESS_COLOR
    green, the five inline census fields over the gateway guild cache —
    goldens/admin/sweep_serverstats pins the bytes). A component-less
    per-read result card (the utility ``_info_card_spec`` recipe): the
    shipped reply was a plain ``ctx.send(embed=...)`` — never minted,
    never anchored."""
    return PanelSpec(
        panel_id="admin.server_stats",
        subsystem="admin",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("admin.server_stats_render"),
        justification=(
            "the shipped embed copy is live-data-parameterized (the "
            "guild-census reads at send time — admin_cog.py "
            "server_stats); grammar TextBlocks are static. Zero "
            "components; the renderer composes only the embed."),
    )


# --- renderer overrides -----------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed,
                                                   footer=_FOOTER))


async def _render_server_stats(spec: PanelSpec, ctx) -> object:
    """The shipped serverstats embed — title over the live guild name,
    the five inline fields in the shipped order (admin_cog.py, verbatim;
    goldens/admin/sweep_serverstats)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    stats = dict((getattr(ctx, "params", {}) or {}).get("stats") or {})
    embed = RenderedEmbed(
        title=f"Server Stats for {stats.get('name', '')}",
        description="",
        fields=(
            ("Total Members", str(stats.get("member_count", 0)), True),
            ("Online Members", str(stats.get("online_members", 0)), True),
            ("Text Channels", str(stats.get("text_channels", 0)), True),
            ("Voice Channels", str(stats.get("voice_channels", 0)), True),
            ("Roles", str(stats.get("roles", 0)), True),
        ),
        style_token="green")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("admin.hub")):
        panel("admin.hub")(admin_hub_spec)
    if not is_registered(HandlerRef("admin.render_hub")):
        handler("admin.render_hub")(_render_hub)
    if not is_registered(PanelRef("admin.server_stats")):
        panel("admin.server_stats")(server_stats_spec)
    if not is_registered(HandlerRef("admin.server_stats_render")):
        handler("admin.server_stats_render")(_render_server_stats)


_register_refs()


def install_admin_panels() -> tuple[PanelSpec, ...]:
    spec = admin_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    _register_refs()
