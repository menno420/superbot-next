"""Mining hub panel (band 6 / parity flip) — the SHIPPED surface
byte-for-byte: disbot/views/mining/main_panel.py ``MiningHubView`` +
its hub embed builder (the Option A six-button declutter + How-to).

``parity/goldens/mining/sweep_minemenu.json`` pins every byte: the
shipped PERSISTENT ``mining:<action>`` custom_ids (``custom_id_override``
on the ANCHORED open — the golden pins a ``panel_anchors`` row, so NO
``session_lifecycle``; static ids render straight through, the
games/community override lane), emoji IN the label (the shipped
decorator ``label="⛏️ Mine"`` form — trap 15a's in-label flavor), the
MINING_COLOR dark-grey embed (6323595, utils/ui_constants.py), the
``_ACTIONS_GUIDE`` description, the five INLINE live-overview fields
(📍 Location · 🧰 Tool · 💡 Light · 💰 Wealth · 🎒 Pack), the shared
invoker-lock footer literal, and the standard nav row (📚 Help +
↩ Games — ``home_hub="games"`` explicit, the farm/creature precedent).

Trap-24 drift check (mining row): the oracle current-head fragments
(views/mining/main_panel.py title f-string + _ACTIONS_GUIDE +
field builders `📍 Location`/`🧰 Tool`/`💡 Light`/`💰 Wealth`/`🎒 Pack`
+ pack "{used}/{cap} item types"; utils/mining/world.py
describe_position + BIOME maps; utils/ui_constants.py MINING_COLOR
dark_grey) match the corpus golden byte-for-byte — NO drift (corpus sha
7f7628e1).

Shipped click semantics (no mining golden drives a click): Harvest ran
the chop lane (REAL — routed to the ported ``mining.chop_route``);
Explore opened the open-world hub (REAL — ``games.world``); Mine opened
the grid navigator and Character/Gear/Workshop/How-to opened their
sub-hubs — all D-0043 deep-system surfaces, routed to honest pending
terminals (registered at import — never ensure-only, #111 doctrine).

Under-port ledger (no golden pins these corners):
* 🧰 Tool / 💡 Light render the shipped ``_gear_line`` EMPTY state
  ("—") unconditionally — the equipment/wear system (equipped slots +
  durability bars) is D-0043; the golden pins exactly "—".
* 💰 Wealth sums the resource/fish sell values only — the shipped
  ``items.total_value`` also valued tools/gear/treasures (the item
  catalog is D-0043); the golden pins the empty-pack **0**.
* the shipped pack/vault warning nudge lines (``capacity.pack_warning``)
  append only near the soft cap — unpinned, D-0043.
* the shipped hub buttons EDITED the panel message in place
  (``safe_edit`` redraws); the port opens result cards / child panels as
  fresh sends (the farm/creature open lane).

MONEY-RACE NOTE (#217 / coordinator ruling 2026-07-12): this module is
render-only — every read is the PLAIN (unlocked) ``get_mining_inventory``
/ ``get_depth`` read. The FOR UPDATE shapes live in
sb/domain/mining/store.py and are composed ONLY by the sell/sell_all/buy
K7 legs (sb/domain/mining/ops.py); this module touches none of them.
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

__all__ = [
    "CARD_PANEL_ID",
    "HUB_PANEL_ID",
    "VAULT_PANEL_ID",
    "FORGE_PANEL_ID",
    "SKILLS_PANEL_ID",
    "TITLES_PANEL_ID",
    "WORKSHOP_PANEL_ID",
    "HOME_PANEL_ID",
    "PACK_SOFT_CAP",
    "ensure_panel_refs",
    "install_mining_panels",
    "mining_card_spec",
    "mining_hub_spec",
    "mining_vault_spec",
    "mining_forge_spec",
    "mining_skills_spec",
    "mining_titles_spec",
    "mining_workshop_spec",
    "mining_home_spec",
]

HUB_PANEL_ID = "mining.hub"
CARD_PANEL_ID = "mining.card"
VAULT_PANEL_ID = "mining.vault"
FORGE_PANEL_ID = "mining.forge"
SKILLS_PANEL_ID = "mining.skills"
TITLES_PANEL_ID = "mining.titles"
WORKSHOP_PANEL_ID = "mining.workshop"
HOME_PANEL_ID = "mining.home"

#: the shipped shared author-locked nav-view footer literal (the
#: games/farm/community `_PANEL_FOOTER`).
_PANEL_FOOTER = "Only you can interact with this panel."

#: views/mining/main_panel.py ``_ACTIONS_GUIDE``, verbatim (the golden
#: pins the rendered description bytes).
_ACTIONS_GUIDE = (
    "**⛏️ Mine** — dig for ore, move between depths, explore for events\n"
    "**🌲 Harvest** — chop wood\n"
    "**🗺️ Explore** — the open-world explorer (fishing, roam, quests — "
    "early)\n"
    "**🧍 Character** — you: overview · inventory · stats · skills · "
    "vault · home\n"
    "**🧰 Gear** — equip your best tools, lights, and combat gear\n"
    "**🔨 Workshop** — craft & build · repair · 🔥 forge · 🛒 market "
    "(all here)\n"
    "**📖 How-to** — new here? the whole mining loop on one screen"
)

#: the shipped ``capacity.PACK_SOFT_CAP`` (the 🎒 Pack field's "/40" —
#: goldens/mining/sweep_minemenu pins the byte).
PACK_SOFT_CAP = 40

#: the shipped ``_gear_line`` empty state (no item in the slot) — the
#: only state the pre-equipment port can be in (D-0043).
_GEAR_EMPTY = "—"

_D0043_TAIL = ("the deep mining port is named successor work (D-0043); "
               "the core loop (mine/chop/explore/sell/buy) is live.")


def _pending_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminals for the hub's D-0043 sub-surfaces — registered
    at IMPORT (module bottom), never ensure-only (#111 doctrine)."""
    from sb.domain.operator_spine import pending_handler

    return {
        "grid": pending_handler(
            "mining.grid_view_pending",
            "⛏️ The grid Mine navigator needs the mining world-grid "
            "system — " + _D0043_TAIL),
        "how_to": pending_handler(
            "mining.how_to_pending",
            "📖 The mining How-to guide rides the deep-system hub port — "
            + _D0043_TAIL),
    }


def mining_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="mining",
        # the override appends the shipped "— {display name}" suffix.
        title="⛏️ Mining Hub",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py);
        # the five live fields + the footer literal ride the override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_ACTIONS_GUIDE),),
        actions=(
            # K1 claims action_ids bare and repo-global — the mi_ prefix
            # keeps the namespace clean (wire bytes are the overrides).
            PanelActionSpec(
                action_id="mi_mine", label="⛏️ Mine",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.grid_view_pending"),
                custom_id_override="mining:mine"),
            PanelActionSpec(
                action_id="mi_harvest", label="🌲 Harvest",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.chop_route"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:harvest"),
            PanelActionSpec(
                action_id="mi_explore_hub", label="🗺️ Explore",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("games.world"),
                custom_id_override="mining:explore_hub"),
            PanelActionSpec(
                action_id="mi_character", label="🧍 Character",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.character_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:character"),
            PanelActionSpec(
                action_id="mi_gear", label="🧰 Gear",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gear_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:gear"),
            PanelActionSpec(
                action_id="mi_workshop", label="🔨 Workshop",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef(WORKSHOP_PANEL_ID),
                custom_id_override="mining:workshop"),
            PanelActionSpec(
                action_id="mi_how_to", label="📖 How-to",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.how_to_pending"),
                custom_id_override="mining:how_to"),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_hub"),
        justification=(
            "three shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/mining/sweep_minemenu pins all three): (1) the "
            "TITLE interpolates the invoker's display name ('⛏️ Mining "
            "Hub — {name}', views/mining/main_panel.py title f-string — "
            "read through the guild-directory port, the world-card "
            "precedent); (2) the five FIELDS interpolate the invoker's "
            "LIVE overview — 📍 Location (depth band), 🧰 Tool / "
            "💡 Light (gear lines), 💰 Wealth (inventory net worth), "
            "🎒 Pack (type count vs soft cap) — all with the shipped "
            "inline=True flags, read-parameterized state outside the "
            "static TextBlock/FieldsBlock vocabulary (the farm 'Coop' "
            "precedent); (3) the FOOTER is the shared invoker-lock "
            "literal 'Only you can interact with this panel.' — outside "
            "FooterMode's vocabulary (the games/community/casino "
            "precedent). Description, color and every component stay "
            "grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("mi_mine", "mi_harvest", "mi_explore_hub"),
            ("mi_character", "mi_gear", "mi_workshop"),
            ("mi_how_to",),
        )),)),
    )


def mining_card_spec() -> PanelSpec:
    """The generic one-embed reply card (the shipped ``ctx.send(embed=…)``)
    — the ai.card/karma.card pattern for the mining read views
    (``!market`` / ``!minestats``)."""
    return PanelSpec(
        panel_id=CARD_PANEL_ID,
        subsystem="mining",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("mining.render_card"),
        justification=(
            "the shipped `!market` / `!minestats` replies are fully "
            "live-state-parameterized embeds built in the handler "
            "(mining_cog.py market_cmd's shop/sellables listing + dynamic "
            "balance footer; the stats command's location/level/net-worth "
            "fields — goldens/mining/sweep_market + sweep_minestats pin "
            "the bytes). Zero components; the renderer presents the "
            "handler-built RenderedEmbed verbatim (the ai.card/karma.card "
            "precedent)."),
    )


async def _render_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — present the handler-built embed verbatim (the
    ai.card ``_render_card`` shape). When the handler set an ``_attachment``
    filename (the shipped ``!gear`` / ``!character`` paper-doll sends), the
    card carries a single ``RenderedAttachment`` — the parity transport
    collapses the whole payload to ``{"_files": [filename]}`` (the
    multipart-serializer information loss, goldens/mining/sweep_gear +
    sweep_character; the PNG bytes are never compared)."""
    from sb.kernel.panels.render import (
        RenderedAttachment,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    embed = params.get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    filename = params.get("_attachment")
    attachments = ((RenderedAttachment(filename=str(filename)),)
                   if filename else ())
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, attachments=attachments,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


def _vault_modal_handlers() -> dict[str, HandlerRef]:
    """Pending terminals for the vault's modal-driven move buttons — the
    📥 Deposit / 📤 Withdraw modals ride the deep-system panel port (D-0043);
    the LIVE command lane (`!stash` / `!unstash`) already carries the same
    audited move. Registered at IMPORT (module bottom), never ensure-only
    (#111 doctrine). No golden drives a vault click, so the terminal copy is
    unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "deposit": pending_handler(
            "mining.vault_deposit_pending",
            "📥 The vault deposit modal rides the deep-system panel port "
            "(D-0043) — deposit now with `!stash <item> [n]`."),
        "withdraw": pending_handler(
            "mining.vault_withdraw_pending",
            "📤 The vault withdraw modal rides the deep-system panel port "
            "(D-0043) — withdraw now with `!unstash <item> [n]`."),
    }


def _forge_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminal for the forge's 🔥 Build button — the structure BUILD
    write rides the deferred structures build system (the `!build` command stays
    a D-0043 pending terminal this slice); the ↩ Workshop button opens the
    now-live ``mining.workshop`` panel (slice 6). Registered
    at IMPORT (module bottom), never ensure-only (#111 doctrine). No golden drives
    a forge click, so the terminal copy is unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "build": pending_handler(
            "mining.forge_build_pending",
            "🔥 Building the forge rides the deep-system structures build port "
            "(D-0043) — " + _D0043_TAIL),
    }


def mining_forge_spec() -> PanelSpec:
    """The shipped 🔥 Forge panel (views/mining/forge_panel.py ``MiningForgeView``
    + ``build_forge_embed``) — an ephemeral (session) child of the mining hub:
    the two buttons mint session `<cid:N>` ids, and the live built-level /
    unlocked-tiers / next-cost embed rides a renderer override
    (goldens/mining/sweep_forge.json pins every byte: the MINING_COLOR dark-grey
    frame, the Level / Unlocks / Next fields, the build-prompt footer, the
    🔥 Build + ↩ Workshop row and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=FORGE_PANEL_ID,
        subsystem="mining",
        title="🔥 Forge",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + build-prompt footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="fo_build", label="🔥 Build",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.forge_build_pending")),
            PanelActionSpec(
                action_id="fo_workshop", label="↩ Workshop",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(WORKSHOP_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_forge"),
        justification=(
            "the shipped `!forge` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/forge_panel.py "
            "build_forge_embed: the Level `{level_name} ({level}/{max})` line, "
            "the Unlocks tiers list, the Next-cost field "
            "`{materials} + {coins} 🪙`, and the built/maxed footer — "
            "goldens/mining/sweep_forge.json pins the not-built bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault live-overview precedent). Every "
            "component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("fo_build", "fo_workshop"),
        )),)),
    )


async def _render_forge(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live forge embed
    (built-level line, unlocked-tiers list, next-build cost / maxed state, and
    the build-prompt footer; see justification). Reads get_structures → the
    forge's built level (a fresh player reads level 0 off the store's no-row
    default → the not-built card goldens/mining/sweep_forge.json pins)."""
    from sb.domain.mining import store, structures, workshop
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    built = await store.get_structures(uid, gid)
    level = built.get(structures.FORGE, 0)
    fields: list[tuple[str, str, bool]] = [
        ("Level",
         f"**{structures.forge_level_name(level)}** "
         f"({level}/{structures.MAX_FORGE_LEVEL})", False)]
    unlocked = structures.tiers_unlocked_at(level)
    unlocked_text = ", ".join(t.title() for t in unlocked) if unlocked else "—"
    fields.append((
        "Unlocks (beyond free tiers)",
        f"{unlocked_text}\nBronze · Iron · Silver gear, tools, and structures "
        "craft without a forge.", False))
    cost = structures.forge_build_cost(level)
    if cost is None:
        fields.append((
            "Maxed",
            "Your forge is at its highest level — it unlocks every gear tier.",
            False))
        footer = "↩ Mining Hub"
    else:
        nxt = structures.forge_level_name(level + 1)
        nxt_tiers = structures.tiers_unlocked_at(level + 1)
        gain = [t for t in nxt_tiers if t not in unlocked]
        gain_text = f" → unlocks **{gain[-1]}-tier** gear" if gain else ""
        fields.append((
            f"Next: {nxt}{gain_text}",
            f"{workshop.describe_materials(cost.materials)} + "
            f"**{cost.coins}** 🪙", False))
        footer = "🔥 Build  •  ↩ Mining Hub"
    embed = _dc_replace(rendered.embed, title="🔥 Forge",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


def _skills_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminals for the skill-tree panel's spend/respec buttons — the
    per-branch point spend and the ♻ Respec (coin-bearing) refund ride the
    deferred panel port (D-0043); the LIVE command lane `!skill <branch>` is the
    named successor for the audited allocate. Registered at IMPORT (module
    bottom), never ensure-only (#111 doctrine). No golden drives a skills-panel
    click, so the terminal copy is unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "spend": pending_handler(
            "mining.skill_spend_pending",
            "🌳 Spending a skill point from the panel rides the deep-system "
            "panel port (D-0043) — spend now with `!skill <branch>` (mining, "
            "combat, fortune, crafting)."),
        "respec": pending_handler(
            "mining.skill_respec_pending",
            "♻ Respec (the level-scaled coin refund) rides the deep-system "
            "panel port (D-0043) — " + _D0043_TAIL),
    }


def mining_skills_spec() -> PanelSpec:
    """The shipped 🌳 Skill Tree panel (views/mining/skills_panel.py
    ``MiningSkillsView`` + ``build_skills_embed``) — an ephemeral (session)
    child of the mining hub: the four branch buttons + ♻ Respec / 🏆 Titles /
    ↩ Mining Hub mint session `<cid:N>` ids, and the live points / per-branch
    allocation embed rides a renderer override (goldens/mining/sweep_skills.json
    pins every byte: the MINING_COLOR dark-grey frame, the Points field, the four
    branch fields, the respec-cost footer, the 2×(4,3) button rows and the
    standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=SKILLS_PANEL_ID,
        subsystem="mining",
        title="🌳 Skill Tree",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + respec-cost footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="sk_mining", label="⛏️ Mining",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_combat", label="⚔️ Combat",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_fortune", label="🍀 Fortune",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_crafting", label="🛠️ Crafting",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_respec", label="♻ Respec",
                style=ActionStyle.DANGER, audience_tier="user",
                handler=HandlerRef("mining.skill_respec_pending")),
            PanelActionSpec(
                action_id="sk_titles", label="🏆 Titles",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=PanelRef(TITLES_PANEL_ID)),
            PanelActionSpec(
                action_id="sk_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_skills"),
        justification=(
            "the shipped `!skills` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/skills_panel.py "
            "build_skills_embed: the Points `{avail} available · {spent} spent` "
            "line + the `Game level {level}` cap note, the four branch "
            "`{blurb}  ({points}/{cap})` fields with their describe_stats "
            "previews, and the `♻ Respec refunds all for {cost} 🪙` footer — "
            "goldens/mining/sweep_skills.json pins the fresh-player bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault / forge live-overview "
            "precedent). Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("sk_mining", "sk_combat", "sk_fortune", "sk_crafting"),
            ("sk_respec", "sk_titles", "sk_hub"),
        )),)),
    )


async def _render_skills(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live skill-tree embed
    (points line, per-branch allocation + describe_stats preview, respec-cost
    footer; see justification). Reads the shared game level + get_skills → a
    fresh player reads level 0 / no allocation → the 0-available card
    goldens/mining/sweep_skills.json pins."""
    from sb.domain.games.xp import shared_level
    from sb.domain.mining import equipment as _eq
    from sb.domain.mining import skills, store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    level, _ = await shared_level(uid, gid)
    alloc = await store.get_skills(uid, gid)
    spent = skills.total_spent(alloc)
    avail = max(0, min(level, skills.SOFT_TOTAL_CAP) - spent)
    fields: list[tuple[str, str, bool]] = [
        ("Points",
         f"**{avail}** available · {spent} spent\n"
         f"Game level **{level}** (points cap at **{skills.SOFT_TOTAL_CAP}** "
         "— you can't max every branch, so specialize).", False)]
    for branch in skills.BRANCHES:
        points = alloc.get(branch, 0)
        bonus = _eq.describe_stats(skills.branch_stats(branch, points))
        bonus_text = ", ".join(f"+{v} {label}" for label, v in bonus) or "—"
        fields.append(
            (f"{skills.BRANCH_LABELS[branch]}  "
             f"({points}/{skills.PER_BRANCH_CAP})", bonus_text, False))
    footer = ("Tap a branch to spend a point  •  "
              f"♻ Respec refunds all for {skills.respec_cost(level)} 🪙")
    embed = _dc_replace(rendered.embed, title="🌳 Skill Tree",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


def mining_titles_spec() -> PanelSpec:
    """The shipped 🏆 Titles panel (views/mining/titles_panel.py
    ``MiningTitlesView`` + ``build_titles_embed``) — an ephemeral (session)
    child of the skill-tree panel: the single ↩ Mining Hub button mints a session
    `<cid:N>` id, and the live equipped/earned/locked embed rides a renderer
    override (goldens/mining/sweep_titles.json pins every byte: the MINING_COLOR
    dark-grey frame, the Equipped + 🔒 Locked (9) fields, the earn-guidance footer,
    the single ↩ Mining Hub button and the standard nav row 📚 Help + ↩ Games).

    A fresh player has NO earned titles, so the earned-title display Select (the
    equip WRITE lane) is absent from the view — the equipped-title write rides the
    deferred panel port (D-0043); no golden drives it. Below the 4-action
    auto-exempt sim floor (1 action), so no legacy-seed overlay is needed."""
    return PanelSpec(
        panel_id=TITLES_PANEL_ID,
        subsystem="mining",
        title="🏆 Titles",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live equipped/earned/locked fields ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="ti_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_titles"),
        justification=(
            "the shipped `!titles` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/titles_panel.py "
            "build_titles_embed: the Equipped title line, the optional "
            "`Earned ({n})` list, and the `🔒 Locked ({n})` list of "
            "`{emoji} {label} — {requirement}` lines derived from the player's "
            "skills / max-depth / level — goldens/mining/sweep_titles.json pins "
            "the fresh-player Equipped `— none —` + 🔒 Locked (9) bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / skills-panel live-overview precedent). "
            "Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ti_hub",),
        )),)),
    )


async def _render_titles(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live titles embed
    (equipped title, optional earned list, locked list with earn requirements;
    see justification). Earned titles are DERIVED from the player's skills /
    max-depth / level (sb/domain/mining/titles.py) — a fresh player earns none →
    Equipped `— none —` + all 9 locked, the bytes goldens/mining/sweep_titles.json
    pins. The equipped title is gated on still being earned (a post-respec choice
    silently un-displays)."""
    from sb.domain.games.xp import shared_level
    from sb.domain.mining import store, titles
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    alloc = await store.get_skills(uid, gid)
    max_depth = await store.get_max_depth(uid, gid)
    level, _ = await shared_level(uid, gid)
    tctx = titles.TitleContext(skills=alloc, max_depth=max_depth, level=level)
    earned = titles.earned_titles(tctx)
    equipped = titles.get_title(await store.get_equipped_title(uid, gid))
    if equipped is not None and not titles.is_earned(equipped.id, tctx):
        equipped = None
    fields: list[tuple[str, str, bool]] = [
        ("Equipped",
         titles.display(equipped) if equipped else "— none —", False)]
    if earned:
        fields.append((
            f"Earned ({len(earned)})",
            "\n".join(titles.display(t) for t in earned), False))
    locked = tuple(t for t in titles.ALL_TITLES
                   if not titles.is_earned(t.id, tctx))
    if locked:
        fields.append((
            f"🔒 Locked ({len(locked)})",
            "\n".join(f"{t.emoji} {t.label} — {t.requirement}" for t in locked),
            False))
    footer = ("Earn titles by mastering skill branches, descending, and "
              "levelling up.")
    embed = _dc_replace(rendered.embed, title="🏆 Titles",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


#: the craft-select options provider id (registered at import in _register_refs).
_WORKSHOP_CRAFT_OPTIONS = "mining.workshop_craft_options"


def _ensure_workshop_craft_provider() -> ProviderRef:
    """The Workshop craft select's rich options — the shipped
    ``views/mining/workshop_panel.py`` ``_CraftSelect`` rows verbatim: the
    equippable recipes annotated craftable-now, sorted (craftable-first, then
    name), the top 25 rendered as ``{Name} — {materials}`` (a ``✅`` emoji only
    when the player can craft it now). A fresh player owns nothing → all 39
    gear recipes are not-craftable → the first 25 alphabetically, no emoji
    (goldens/mining/sweep_workshop pins the 25 option bytes)."""
    ref = ProviderRef(_WORKSHOP_CRAFT_OPTIONS)
    if not is_registered(ref):
        @provider(_WORKSHOP_CRAFT_OPTIONS)
        async def workshop_craft_options(ctx: object):
            from sb.domain.mining import store, workshop
            from sb.domain.mining.recipes import load_recipes

            uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
            gid = int(getattr(ctx, "guild_id", 0) or 0)
            inventory = await store.get_mining_inventory(uid, gid)
            options = []
            for g in sorted(workshop.craftable_gear(load_recipes(), inventory),
                            key=lambda g: (not g.craftable, g.name)):
                opt = {
                    "label": (f"{g.name.title()} — "
                              f"{workshop.describe_materials(g.materials)}")[:100],
                    "value": g.name,
                }
                if g.craftable:
                    opt["emoji"] = "✅"
                options.append(opt)
            return tuple(options)
    return ref


def _workshop_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminals for the Workshop panel's deferred lanes — the craft
    select's material→product write and the ↩ Workshop sub-hub ride the deferred
    structures/panel port (D-0043); the LIVE lanes (`!repair`, `!quickcraft`,
    the 🔁 Quick-craft button) already carry the audited moves. Registered at
    IMPORT (module bottom), never ensure-only (#111 doctrine). No golden drives
    a workshop click, so the terminal copy is unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "craft": pending_handler(
            "mining.workshop_craft_pending",
            "🛠️ Crafting gear from the dropdown rides the deep-system panel "
            "port (D-0043) — " + _D0043_TAIL),
        "hub": pending_handler(
            "mining.workshop_hub_pending",
            "🔧 The Workshop sub-hub rides the deep-system panel port (D-0043) "
            "— repair now with `!repair <item>`, or `!craft <item>`."),
    }


def mining_workshop_spec() -> PanelSpec:
    """The shipped 🔧 Workshop panel (views/mining/workshop_panel.py
    ``MiningWorkshopView`` + ``build_workshop_embed``) — an ephemeral (session)
    child of the mining hub: a provider-fed gear-craft select + 🔁 Quick-craft
    last broken + ↩ Workshop mint session `<cid:N>` ids, and the live
    equipped-gear / craftable-gear / balance embed rides a renderer override
    (goldens/mining/sweep_workshop.json pins every byte: the MINING_COLOR
    dark-grey frame, the 🧰 Equipped gear + 🛠️ Craft gear fields, the balance
    footer, the 25-option craft select, the disabled 🔁 Quick-craft + ↩ Workshop
    row, and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=WORKSHOP_PANEL_ID,
        subsystem="mining",
        title="🔧 Workshop",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + balance footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        selectors=(
            SelectorSpec(
                selector_id="ws_craft", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("mining.workshop_craft_pending"),
                options_source=_ensure_workshop_craft_provider(),
                placeholder="Craft gear from resources…",
                empty_state="Craft gear from resources…",
                audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="ws_quickcraft",
                label="🔁 Quick-craft last broken",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.quickcraft_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="ws_back", label="↩ Workshop",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.workshop_hub_pending")),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_workshop"),
        justification=(
            "the shipped `!workshop` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/workshop_panel.py "
            "build_workshop_embed: the 🧰 Equipped gear condition/repair lines, "
            "the 🛠️ Craft gear list + the `All {n} gear recipes` pointer, and "
            "the dynamic `Balance: {n} 🪙` footer — goldens/mining/"
            "sweep_workshop.json pins the fresh-player bytes), read-parameterized "
            "state outside the static TextBlock/FieldsBlock vocabulary (the "
            "mining hub / vault / forge live-overview precedent). The craft "
            "select's options ride the declared provider; the renderer patches "
            "only the embed and the 🔁 Quick-craft disabled flag (disabled with "
            "no last-broken item). Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ws_craft",),
            ("ws_quickcraft", "ws_back"),
        )),)),
    )


async def _render_workshop(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live workshop embed
    (equipped-gear condition/repair lines, craftable-gear list, balance footer;
    see justification) and the disabled-when-no-last-broken 🔁 Quick-craft
    button. A fresh player owns nothing / has nothing equipped / never broke a
    tool → `Nothing equipped yet.` + `▫️ Nothing craftable …` + `All 39 gear
    recipes` + `Balance: 0 🪙` and a DISABLED Quick-craft — the bytes
    goldens/mining/sweep_workshop.json pins."""
    from sb.domain.economy.store import get_coins
    from sb.domain.mining import equipment as _eq
    from sb.domain.mining import store, workshop
    from sb.domain.mining.recipes import load_recipes
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    inventory = await store.get_mining_inventory(uid, gid)
    equipped = await store.get_equipment(uid, gid)
    wear = await store.get_gear_wear(uid, gid)
    last_broken = await store.get_last_broken(uid, gid)
    balance = await get_coins(uid, gid)

    gear_lines: list[str] = []
    for slot in _eq.SLOTS:
        item = equipped.get(slot)
        if not item:
            continue
        maximum = _eq.max_durability(item)
        if maximum is None:
            gear_lines.append(f"**{item.title()}** — does not wear")
            continue
        remaining = wear.get(item, maximum)
        line = f"**{item.title()}** {workshop.durability_bar(remaining, maximum)}"
        cost = workshop.repair_cost(item, remaining)
        if cost is not None:
            line += f" — repair {cost} 🪙"
        gear_lines.append(line)
    fields: list[tuple[str, str, bool]] = [
        ("🧰 Equipped gear",
         "\n".join(gear_lines) if gear_lines else "Nothing equipped yet.",
         False)]
    if last_broken:
        fields.append((
            "💥 Last broken",
            f"**{last_broken.title()}** — hit 🔁 Quick-craft to replace it.",
            False))
    craftables = workshop.craftable_gear(load_recipes(), inventory)
    if craftables:
        ready = [g for g in craftables if g.craftable]
        lines = [f"✅ **{g.name.title()}** — "
                 f"{workshop.describe_materials(g.materials)}" for g in ready[:12]]
        if not ready:
            lines = ["▫️ Nothing craftable from your current resources."]
        lines.append(
            f"📖 All **{len(craftables)}** gear recipes: the Recipe browser "
            "(`!recipes`).")
        fields.append(("🛠️ Craft gear", "\n".join(lines), False))
    embed = _dc_replace(
        rendered.embed, title="🔧 Workshop", fields=tuple(fields),
        footer=(f"Balance: {balance} 🪙  •  !repair <item> · !craft <item> · "
                "!quickcraft"))
    components = tuple(
        _dc_replace(c, disabled=True)
        if (not last_broken
            and getattr(c, "custom_id", "").endswith(".ws_quickcraft"))
        else c
        for c in rendered.components)
    return _dc_replace(rendered, embed=embed, components=components)


def _home_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminal for the Home panel's 🏠 Build button — the structure
    BUILD write (coin + material sink → level raise) rides the deferred
    structures build port (D-0043). Registered at IMPORT (module bottom), never
    ensure-only (#111 doctrine). No golden drives a home click, so the terminal
    copy is unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "build": pending_handler(
            "mining.home_build_pending",
            "🏠 Building your Home rides the deep-system structures build port "
            "(D-0043) — " + _D0043_TAIL),
    }


def mining_home_spec() -> PanelSpec:
    """The shipped 🏠 Home panel (views/mining/home_panel.py ``MiningHomeView``
    + ``build_home_embed``) — an ephemeral (session) child of the mining hub:
    the 🏠 Build + ↩ Mining Hub buttons mint session `<cid:N>` ids, and the live
    built-level / backdrop-blurb / next-cost embed rides a renderer override
    (goldens/mining/sweep_home.json pins every byte: the MINING_COLOR dark-grey
    frame, the Level / What it does / Next fields, the build-prompt footer, the
    🏠 Build + ↩ Mining Hub row and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=HOME_PANEL_ID,
        subsystem="mining",
        title="🏠 Home",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + build-prompt footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="ho_build", label="🏠 Build",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.home_build_pending")),
            PanelActionSpec(
                action_id="ho_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_home"),
        justification=(
            "the shipped `!home` reply is a fully live-state-parameterized embed "
            "built in the view (views/mining/home_panel.py build_home_embed: the "
            "Level `{level_name} ({level}/{max})` line, the cosmetic-backdrop "
            "blurb, and the Next-cost `{materials} + {coins} 🪙` field / maxed "
            "state — goldens/mining/sweep_home.json pins the not-built bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault / forge live-overview precedent). "
            "Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ho_build", "ho_hub"),
        )),)),
    )


async def _render_home(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live home embed
    (built-level line, cosmetic-backdrop blurb, next-build cost / maxed state,
    and the build-prompt footer; see justification). Reads get_structures → the
    Home's built level (a fresh player reads level 0 off the store's no-row
    default → the not-built card goldens/mining/sweep_home.json pins)."""
    from sb.domain.mining import store, structures, workshop
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    built = await store.get_structures(uid, gid)
    level = built.get(structures.HOME, 0)
    fields: list[tuple[str, str, bool]] = [
        ("Level",
         f"**{structures.level_name(structures.HOME, level)}** "
         f"({level}/{structures.MAX_HOME_LEVEL})", False),
        ("What it does",
         "A built Home gives your **Character card** a personalized backdrop "
         "— each level a richer one. Purely cosmetic.", False)]
    cost = structures.build_cost(structures.HOME, level)
    if cost is None:
        fields.append((
            "Maxed",
            "Your Home is at its grandest — the Grand Hall backdrop is yours.",
            False))
        footer = "↩ Mining Hub"
    else:
        nxt = structures.level_name(structures.HOME, level + 1)
        fields.append((
            f"Next: {nxt}",
            f"{workshop.describe_materials(cost.materials)} + "
            f"**{cost.coins}** 🪙", False))
        footer = "🏠 Build  •  ↩ Mining Hub"
    embed = _dc_replace(rendered.embed, title="🏠 Home",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


def mining_vault_spec() -> PanelSpec:
    """The shipped 🏦 Mining Vault panel (views/mining/vault_panel.py
    ``MiningVaultView`` + ``build_vault_embed``) — an ephemeral (session)
    child of the mining hub: the five move buttons mint session `<cid:N>`
    ids (never the anchored `mining:<x>` overrides the hub carries), and the
    live capacity/stored-value/empty-state embed rides a renderer override
    (goldens/mining/sweep_vault pins every byte: the MINING_COLOR dark-grey
    frame, the 📦 Capacity + empty-state fields, the stored-value footer, the
    2×2+1 button rows and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=VAULT_PANEL_ID,
        subsystem="mining",
        title="🏦 Mining Vault",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + stored-value footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="va_deposit", label="📥 Deposit",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.vault_deposit_pending")),
            PanelActionSpec(
                action_id="va_withdraw", label="📤 Withdraw",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.vault_withdraw_pending")),
            PanelActionSpec(
                action_id="va_stash_all", label="📦 Stash All Ore",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.stash_all_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_upgrade", label="⬆️ Upgrade",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.vaultupgrade_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_vault"),
        justification=(
            "the shipped `!vault` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/vault_panel.py "
            "build_vault_embed: the 📦 Capacity `{used}/{cap} item types "
            "(tier {level})` line, the empty-state / grouped-stored fields, "
            "and the dynamic `Stored value: {n}` footer — "
            "goldens/mining/sweep_vault pins the bytes), read-parameterized "
            "state outside the static TextBlock/FieldsBlock vocabulary (the "
            "mining hub's own live-overview precedent). Every component stays "
            "grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("va_deposit", "va_withdraw"),
            ("va_stash_all", "va_upgrade"),
            ("va_hub",),
        )),)),
    )


async def _render_vault(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live vault embed
    (capacity line, empty-state / stored listing, stored-value footer; see
    justification). Stored value uses the resource/fish sell valuation (the
    same D-0043 item-catalog boundary the hub's 💰 Wealth field draws — the
    shipped ``items.total_value`` also valued tools/gear/treasure); the golden
    pins the empty-vault **0**. The grouped-by-kind listing rides the deferred
    item taxonomy, so a non-empty vault renders one flat 📦 Stored field."""
    from sb.domain.mining import capacity, market, store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    vault = await store.get_vault(uid, gid)
    level = await store.get_vault_level(uid, gid)
    status = capacity.vault_status(vault, level)
    fields: list[tuple[str, str, bool]] = [
        ("📦 Capacity",
         f"{status.used}/{status.cap} item types (tier {level})", False)]
    nudge = capacity.vault_warning(status)
    if nudge:
        fields.append(("​", nudge, False))
    if not vault:
        fields.append((
            "Your vault is empty",
            "A vault is a **safe stash** for your loot, kept separate from "
            "your mining pack.\nUse **📥 Deposit** (or `!stash <item> [n]`) "
            "to tuck something away.", False))
    else:
        fields.append((
            "📦 Stored",
            "\n".join(f"**{name.title()}** ×{qty}"
                      for name, qty in sorted(vault.items())), False))
    stored_value = sum(qty * (market.sell_price(item) or 0)
                       for item, qty in vault.items())
    embed = _dc_replace(
        rendered.embed, title="🏦 Mining Vault", fields=tuple(fields),
        footer=(f"Stored value: {stored_value}  •  📥 Deposit · "
                "📤 Withdraw · 📦 Stash All Ore · ⬆️ Upgrade"))
    return _dc_replace(rendered, embed=embed)


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped display-name
    title, live overview fields and footer literal (see justification)."""
    from sb.domain.mining import market, store
    from sb.domain.mining.world import describe_position
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    inventory = await store.get_mining_inventory(uid, gid)
    depth = await store.get_depth(uid, gid)
    name = await _display_name(uid, gid)
    # shipped net worth: items.total_value — resource/fish values here;
    # tool/gear/treasure values ride the D-0043 item catalog (ledgered
    # above); the golden pins the empty-pack 0.
    worth = sum(qty * (market.sell_price(item) or 0)
                for item, qty in inventory.items())
    embed = _dc_replace(
        rendered.embed,
        title=f"⛏️ Mining Hub — {name}" if name else "⛏️ Mining Hub",
        fields=(
            ("📍 Location", describe_position(depth), True),
            ("🧰 Tool", _GEAR_EMPTY, True),
            ("💡 Light", _GEAR_EMPTY, True),
            ("💰 Wealth", f"Net worth: **{worth}**", True),
            ("🎒 Pack", f"{len(inventory)}/{PACK_SOFT_CAP} item types",
             True),
        ),
        footer=_PANEL_FOOTER)
    return _dc_replace(rendered, embed=embed)


async def _display_name(user_id: int, guild_id: int) -> str:
    """Invoker display name through the guild-directory read port (the
    games world-card recipe); degrades to "" — the shipped no-name title
    branch, never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ bare title
        return ""
    return member.tag.rsplit("#", 1)[0]


@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return mining_hub_spec()


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return mining_card_spec()


@panel(VAULT_PANEL_ID)
def _vault_factory() -> PanelSpec:
    return mining_vault_spec()


@panel(FORGE_PANEL_ID)
def _forge_factory() -> PanelSpec:
    return mining_forge_spec()


@panel(SKILLS_PANEL_ID)
def _skills_factory() -> PanelSpec:
    return mining_skills_spec()


@panel(TITLES_PANEL_ID)
def _titles_factory() -> PanelSpec:
    return mining_titles_spec()


@panel(WORKSHOP_PANEL_ID)
def _workshop_factory() -> PanelSpec:
    return mining_workshop_spec()


@panel(HOME_PANEL_ID)
def _home_factory() -> PanelSpec:
    return mining_home_spec()


def _register_refs() -> None:
    from sb.spec.refs import handler

    _pending_button_handlers()
    _vault_modal_handlers()
    _forge_button_handlers()
    _skills_button_handlers()
    _workshop_button_handlers()
    _home_button_handlers()
    _ensure_workshop_craft_provider()
    if not is_registered(HandlerRef("mining.render_hub")):
        handler("mining.render_hub")(_render_hub)
    if not is_registered(HandlerRef("mining.render_card")):
        handler("mining.render_card")(_render_card)
    if not is_registered(HandlerRef("mining.render_vault")):
        handler("mining.render_vault")(_render_vault)
    if not is_registered(HandlerRef("mining.render_forge")):
        handler("mining.render_forge")(_render_forge)
    if not is_registered(HandlerRef("mining.render_skills")):
        handler("mining.render_skills")(_render_skills)
    if not is_registered(HandlerRef("mining.render_titles")):
        handler("mining.render_titles")(_render_titles)
    if not is_registered(HandlerRef("mining.render_workshop")):
        handler("mining.render_workshop")(_render_workshop)
    if not is_registered(HandlerRef("mining.render_home")):
        handler("mining.render_home")(_render_home)
    if not is_registered(PanelRef(HUB_PANEL_ID)):
        panel(HUB_PANEL_ID)(_hub_factory)
    if not is_registered(PanelRef(CARD_PANEL_ID)):
        panel(CARD_PANEL_ID)(_card_factory)
    if not is_registered(PanelRef(VAULT_PANEL_ID)):
        panel(VAULT_PANEL_ID)(_vault_factory)
    if not is_registered(PanelRef(FORGE_PANEL_ID)):
        panel(FORGE_PANEL_ID)(_forge_factory)
    if not is_registered(PanelRef(SKILLS_PANEL_ID)):
        panel(SKILLS_PANEL_ID)(_skills_factory)
    if not is_registered(PanelRef(TITLES_PANEL_ID)):
        panel(TITLES_PANEL_ID)(_titles_factory)
    if not is_registered(PanelRef(WORKSHOP_PANEL_ID)):
        panel(WORKSHOP_PANEL_ID)(_workshop_factory)
    if not is_registered(PanelRef(HOME_PANEL_ID)):
        panel(HOME_PANEL_ID)(_home_factory)


def install_mining_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (mining_hub_spec(), mining_card_spec(), mining_vault_spec(),
                 mining_forge_spec(), mining_skills_spec(),
                 mining_titles_spec(), mining_workshop_spec(),
                 mining_home_spec()):
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    _register_refs()


_register_refs()
