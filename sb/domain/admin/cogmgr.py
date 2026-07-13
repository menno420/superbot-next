"""The ADMIN Cog Manager panel (the sweep_coglist re-home) — the shipped
``CogManagerView`` (disbot/cogs/admin/cog_manager.py at the corpus sha):
the 📋 blue embed (the "**Pick a cog from the dropdown, then Load /
Unload / Reload.**" head, one ``✅ 🟢  `name``` status line per cog with
the 🛡 protected suffix, the four-glyph legend tail, the "No cog
selected." footer) over four component rows — the windowed cog select
(row 0, ``paginated_select.SelectWindow``: 25-option page-1 window,
"Choose a cog… — page 1/3" placeholder), the Load / Unload / Reload
action trio (row 1 — the shipped PERSISTENT ids ``admin:cogmgr:load`` /
``:unload`` / ``:reload``), 🔄 Refresh (row 2, ``admin:cogmgr:refresh``)
and the run-minted ◀ Prev / Next ▶ window pair (row 3, ``<cid:2>`` /
``<cid:3>`` — Prev disabled on page 1).
``parity/goldens/admin/sweep_coglist.json`` pins every wire byte of the
``!coglist`` open; the shipped admin hub's 📋 Cog List button opened the
SAME view (admin_cog.py: "the panel's 📋 Cog List button").

SESSION-VIEW SEMANTICS: the shipped view was a timeout session view that
MIXED auto-ids with explicit persistent custom_ids (the utility_cog
``utility:open:<child>`` precedent — goldens/utility/sweep_utilitymenu
pins the same mix), so ``session_lifecycle=True`` with
``custom_id_override`` on the four static ids: the golden pins minted
``<cid:N>`` ids for the select + Prev/Next and the verbatim
``admin:cogmgr:*`` ids for the rest; no ``panel_anchors`` row.

CAPTURE-WORLD LITERAL (trap 10a): the shipped roster enumerated the
capture world's 58 loaded discord.py extensions (``bot.extensions`` +
the cogs-dir scan — all loaded, all syntax-OK at capture time; the same
58 the admin hub's "Loaded cogs: **58**" line pins). The compiled
architecture has no extension registry — subsystems compile at boot —
so the roster ships as the golden-pinned capture literal (the admin hub
description precedent); the manifest registry (`admin.subsystems_view`)
is the honest successor read if a future golden pins a different
roster.

Interaction surface (operator-hub edits C — no golden drives any click,
so the bare open stays byte-identical):
* the cog SELECT is LIVE: it stashes the pick per (guild, invoker) and
  re-renders with the shipped ``← selected`` roster marker + the
  ``Selected: cogs.<name>`` footer swap (cog_manager.build_embed).
* ◀ Prev / Next ▶ are LIVE: the shipped SelectWindow page flip over the
  3-page 25-option roster windows, edge-disabled, with the shipped
  ``page N/3`` placeholder.
* Load / Unload / Reload reloaded discord.py extensions IN-PROCESS —
  deploy-ops, DELIBERATELY not ported (docs/decisions.md: extension
  management has no analog in the compiled architecture — subsystems
  are manifests, not runtime-loadable cogs); the clicks land on the
  declared BY-DESIGN terminal whose copy states exactly that (the
  hub's Reload All precedent). This is the surface's end state, not a
  pending port.
* 🔄 Refresh re-scanned the cogs dir and re-rendered; the port's
  refresh re-renders the panel in place (REFRESH_PANEL — an honest
  re-render over the pinned roster).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

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
    SelectorKind,
    SelectorSpec,
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

__all__ = ["cogmgr_spec", "ensure_cogmgr_refs"]

#: the capture world's 58 loaded cogs, alphabetical — the golden-pinned
#: roster literal (module docstring; goldens/admin/sweep_coglist).
_COGS: tuple[str, ...] = (
    "admin_cog", "ai_cog", "ai_review_cog", "automod_cog", "blackjack_cog",
    "bootstrap_access_cog", "btd6_cog", "btd6_events_cog", "btd6_ops_cog",
    "btd6_reference_cog", "btd6_strategy_cog", "casino_cog", "chain_cog",
    "channel_cog", "cleanup_cog", "community_cog", "community_spotlight_cog",
    "counters_cog", "counting_cog", "creature_battle_cog", "creature_cog",
    "deathmatch_cog", "diagnostic_cog", "economy_cog", "farm_cog",
    "fishing_cog", "four_twenty_cog", "games_cog", "general_cog",
    "health_maintenance_cog", "help_cog", "hermes_cog",
    "image_moderation_cog", "inventory_cog", "karma_cog", "leaderboard_cog",
    "logging_cog", "media_maintenance_cog", "mining_cog", "moderation_cog",
    "paragon_cog", "project_moon_cog", "proof_channel_cog", "quicksetup_cog",
    "role_cog", "role_grants_cog", "rps_tournament_cog", "security_cog",
    "server_management_cog", "settings_cog", "setup_cog", "starboard_cog",
    "ticket_cog", "treasury_cog", "utility_cog", "ux_lab_cog", "welcome_cog",
    "xp_cog",
)

#: the shipped PROTECTED_COGS set (panel unload denied — the 🛡 suffix;
#: the golden pins exactly these five).
_PROTECTED: frozenset[str] = frozenset((
    "admin_cog", "cleanup_cog", "help_cog", "logging_cog", "settings_cog",
))

#: the shipped protected-option description (cog_manager.py, verbatim).
_PROTECTED_NOTE = "Protected core cog — panel unload denied"

#: the shipped legend tail (cog_manager.py description_parts, verbatim —
#: every cog was loaded + syntax-OK in the capture world, so only the
#: ✅/🟢 glyphs appear in the roster lines).
_LEGEND = ("✅ Loaded  ❌ Unloaded  🟢 OK  🔴 Syntax error  "
           "🛡 Protected (panel unload denied — use `!cog unload <name>`)")

#: the shipped initial footer (selection-dependent copy — see the
#: renderer override / justification).
_FOOTER = "No cog selected."

#: the shipped select window size (paginated_select MAX_OPTIONS) and the
#: derived page count over the 58-cog roster (58 → 25/25/8 = 3 pages,
#: the golden-pinned "page 1/3" placeholder's denominator).
_PAGE_SIZE = 25
_PAGE_COUNT = (len(_COGS) + _PAGE_SIZE - 1) // _PAGE_SIZE


# --- the operator's pick/page memory (operator-hub edits C) -----------------------
#
# The shipped view kept `selected_module` + the SelectWindow page on the
# View instance; the port keys them per (guild, invoker), in-memory —
# the diagnostic `_flag_pick` precedent (#331). Never golden-rendered:
# no sweep clicked the select or the window nav, so golden runs never
# seed a pick/page (the bare `!coglist` open stays byte-identical).

_cog_pick: dict[tuple[int, int], str] = {}
_cog_page: dict[tuple[int, int], int] = {}


def _mem_key(guild_id, user_id) -> tuple[int, int]:
    return (int(guild_id or 0), int(user_id or 0))


def cog_pick_for(guild_id, user_id) -> str | None:
    """The renderer's read of the operator's current pick (the shipped
    ``selected_module`` — e.g. ``cogs.admin_cog``)."""
    return _cog_pick.get(_mem_key(guild_id, user_id))


def cog_page_for(guild_id, user_id) -> int:
    """The renderer's read of the select window page (0-based, clamped)."""
    return min(max(_cog_page.get(_mem_key(guild_id, user_id), 0), 0),
               _PAGE_COUNT - 1)


def _description(selected: str | None = None) -> str:
    """The shipped roster description; ``selected`` appends the shipped
    ``  ← selected`` marker to the picked line (cog_manager.build_embed —
    the bare open passes None and stays the golden-pinned bytes)."""
    picked = (selected or "").removeprefix("cogs.")
    lines = ["**Pick a cog from the dropdown, then Load / Unload / Reload.**",
             ""]
    for name in _COGS:
        suffix = " 🛡" if name in _PROTECTED else ""
        marker = "  ← selected" if name == picked else ""
        lines.append(f"✅ 🟢  `{name}`{suffix}{marker}")
    lines.extend(["", _LEGEND])
    return "\n".join(lines)


async def _cog_options(ctx) -> tuple[dict, ...]:
    """The select's option roster (the shipped ``_build_cog_options``):
    ``✅🟢[🛡] name`` labels over ``cogs.<name>`` values, the protected
    description on the 🛡 five; the grammar windows to the first 25 —
    exactly the shipped page-1 window the golden pins."""
    del ctx
    out = []
    for name in _COGS:
        shield = "🛡" if name in _PROTECTED else ""
        option: dict = {"label": f"✅🟢{shield} {name}",
                        "value": f"cogs.{name}"}
        if name in _PROTECTED:
            option["description"] = _PROTECTED_NOTE
        out.append(option)
    return tuple(out)


def cogmgr_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="admin.cogmgr",
        subsystem="admin",
        title="📋 Cog Manager",
        # invoker-locked timeout session view (the shipped HubView family).
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blue() (the golden's 3447003).
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(_description()),),
        selectors=(
            # the shipped windowed cog select — run-minted session id (the
            # golden pins <cid:1>) with the shipped page-1/3 placeholder;
            # pages 2/3 land with the manager's interaction slice.
            SelectorSpec(
                selector_id="cogmgr_select", kind=SelectorKind.ENUM,
                options_source=ProviderRef("admin.cogmgr_options"),
                placeholder="Choose a cog… — page 1/3",
                audience_tier="administrator",
                on_select=HandlerRef("admin.cogmgr_select")),
        ),
        actions=(
            # row 1 — the shipped deploy-ops trio (PERSISTENT custom_ids,
            # golden-pinned verbatim; K1 claims action_ids bare, hence the
            # cogmgr_ prefixes).
            PanelActionSpec(
                action_id="cogmgr_load", label="Load",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=HandlerRef("admin.cogmgr_deploy_pending"),
                custom_id_override="admin:cogmgr:load"),
            PanelActionSpec(
                action_id="cogmgr_unload", label="Unload",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=HandlerRef("admin.cogmgr_deploy_pending"),
                custom_id_override="admin:cogmgr:unload"),
            PanelActionSpec(
                action_id="cogmgr_reload", label="Reload",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("admin.cogmgr_deploy_pending"),
                custom_id_override="admin:cogmgr:reload"),
            # row 2 — the shipped grey refresh (persistent id; an honest
            # in-place re-render over the pinned roster).
            PanelActionSpec(
                action_id="cogmgr_refresh", label="🔄 Refresh",
                audience_tier="administrator",
                handler=PanelRef("admin.cogmgr"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="admin:cogmgr:refresh"),
            # row 3 — the shipped session window pair (run-minted ids; the
            # golden pins <cid:2>/<cid:3>; the edge pages render disabled
            # via the renderer override — operator-hub edits C armed the
            # page steps).
            PanelActionSpec(
                action_id="cogmgr_prev", label="◀ Prev",
                audience_tier="administrator",
                handler=HandlerRef("admin.cogmgr_prev")),
            PanelActionSpec(
                action_id="cogmgr_next", label="Next ▶",
                audience_tier="administrator",
                handler=HandlerRef("admin.cogmgr_next")),
        ),
        # the shipped view carried ONLY its own components (session view,
        # no nav slots) — the golden pins exactly four component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("admin.cogmgr_render"),
        justification=(
            "the shipped manager footer is the SELECTION-dependent copy "
            "('No cog selected.' until a pick — cog_manager.py set_footer) "
            "— state-keyed copy outside FooterMode's none/subsystem/"
            "provenance vocabulary, and the first-page ◀ Prev button "
            "renders disabled — outside the grammar's vocabulary (actions "
            "carry no disabled state) "
            "(goldens/admin/sweep_coglist pins both bytes; the "
            "settings.access precedent). The override delegates to the "
            "grammar renderer and adjusts ONLY those two surfaces; body, "
            "selector, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cogmgr_select",),
            ("cogmgr_load", "cogmgr_unload", "cogmgr_reload"),
            ("cogmgr_refresh",),
            ("cogmgr_prev", "cogmgr_next"),
        )),)),
    )


async def _render_cogmgr(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped state-keyed adjustments (see
    justification): the selection-dependent footer ('No cog selected.' /
    'Selected: cogs.<name>'), the ``← selected`` roster marker, the
    windowed select page (25-option windows, 'page N/3' placeholder) and
    the edge-disabled ◀ Prev / Next ▶ pair. Page 0 with no pick renders
    the golden-pinned bare-open bytes exactly (goldens/admin/
    sweep_coglist — the grammar's own first-25 window, Prev disabled,
    the initial footer)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = getattr(ctx, "guild_id", 0)
    uid = getattr(getattr(ctx, "actor", None), "user_id", 0)
    page = cog_page_for(gid, uid)
    picked = cog_pick_for(gid, uid)
    components = []
    for c in rendered.components:
        leaf = c.custom_id.rsplit(".", 1)[-1].rsplit(":", 1)[-1]
        if leaf == "cogmgr_prev":
            c = _dc_replace(c, disabled=(page == 0))
        elif leaf == "cogmgr_next":
            c = _dc_replace(c, disabled=(page == _PAGE_COUNT - 1))
        elif c.kind == "selector" and leaf == "cogmgr_select":
            options = tuple(await _cog_options(ctx))
            window = options[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]
            c = _dc_replace(
                c, options=window,
                placeholder=f"Choose a cog… — page {page + 1}/{_PAGE_COUNT}")
        components.append(c)
    embed = rendered.embed
    if picked:
        embed = _dc_replace(embed, description=_description(picked))
    footer = f"Selected: {picked}" if picked else _FOOTER
    return _dc_replace(
        rendered, components=tuple(components),
        embed=_dc_replace(embed, footer=footer))


def _register_refs() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.refs import handler

    if not is_registered(PanelRef("admin.cogmgr")):
        panel("admin.cogmgr")(cogmgr_spec)
    if not is_registered(HandlerRef("admin.cogmgr_render")):
        handler("admin.cogmgr_render")(_render_cogmgr)
    if not is_registered(ProviderRef("admin.cogmgr_options")):
        provider("admin.cogmgr_options")(_cog_options)
    pending_handler(
        "admin.cogmgr_deploy_pending",
        "📋 Extension load/unload/reload is deploy-ops in the compiled "
        "architecture — subsystems recompile at boot, not in-process "
        "(the Reload All / `!cog` class).")

    from sb.spec.outcomes import SUCCESS

    async def _reopen(req):
        import dataclasses

        from sb.kernel.panels.engine import open_panel

        await open_panel(PanelRef("admin.cogmgr"),
                         dataclasses.replace(req, args=dict(req.args)))
        return None

    def _req_key(req) -> tuple[int, int]:
        return _mem_key(req.guild_id,
                        getattr(req.actor, "user_id", 0))

    if not is_registered(HandlerRef("admin.cogmgr_select")):
        @handler("admin.cogmgr_select")
        async def cogmgr_select(req):
            """The windowed cog select (operator-hub edits C) — the
            shipped `_on_cog_selected`: stash the pick, re-render with
            the `← selected` marker + the 'Selected: cogs.<name>'
            footer (fresh re-open, the projmoon class). The deploy trio
            it arms stays the by-design deploy-ops terminal."""
            values = tuple(req.args.get("values") or ())
            if not values:
                # the shipped empty-window sentinel reply, verbatim.
                return Reply(SUCCESS, "No cogs available.")
            _cog_pick[_req_key(req)] = str(values[0])
            await _reopen(req)
            return Reply(SUCCESS, None)

        async def _page_step(req, delta: int):
            """◀/▶ — the shipped SelectWindow page flip, clamped to the
            3-page roster (the diagnostic cmdlist step precedent)."""
            key = _req_key(req)
            page = min(max(_cog_page.get(key, 0) + delta, 0),
                       _PAGE_COUNT - 1)
            _cog_page[key] = page
            await _reopen(req)
            return Reply(SUCCESS, None)

        @handler("admin.cogmgr_prev")
        async def cogmgr_prev(req):
            """◀ Prev on the cog select window."""
            return await _page_step(req, -1)

        @handler("admin.cogmgr_next")
        async def cogmgr_next(req):
            """Next ▶ on the cog select window."""
            return await _page_step(req, +1)


_register_refs()


def ensure_cogmgr_refs() -> None:
    _register_refs()
