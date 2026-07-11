"""The SETTINGS panels (parity flip) — the shipped Settings Manager hub
(disbot/views/settings/hub.py ``SettingsHubView`` + ``build_embed``) and
the shipped Access Policy Explorer (disbot/views/access/explorer.py,
``!settings access``), byte-for-byte as the goldens pin them
(parity/goldens/settings/: settings_hub_open, sweep_settings,
sweep_settings_access, sweep_slash_settings).

The hub: the ⚙️ blurple embed (the shipped two-paragraph blurb; the
Inventory + Customization-findings fields; the Tip footer) over the
shipped three component rows — the 19-group subsystem select, the four
grey diagnostic buttons (Needs setup / Invalid settings / Missing
bindings / Recent changes, emoji as a SEPARATE component field — the
shipped ``discord.ui.button(emoji=...)`` wire shape), and the Command
access door — every component carrying its shipped PERSISTENT custom_id
verbatim (the ``settings_hub.*`` family via ``custom_id_override``; the
economy-hub/server-management precedent). ``session_lifecycle=True``
with every component override-pinned: nothing is run-minted, no
``panel_anchors`` row is recorded (the goldens' db_delta carries none),
and the never-strand fence takes the session-view exemption the shipped
no-nav-row shape demands (the shipped hub carried NO standard nav row —
goldens pin exactly three component rows).

The explorer: the 🔍 blue read-only governance diagnostic — the paged
subsystem select (run-minted id; the shipped page-1/2 placeholder), the
``access:select_scope`` scope select (channel default), the
``access:explain`` / ``access:reset`` buttons (emoji IN the label), the
run-minted ◀ Prev (disabled on page 1) / Next ▶ pair, and the shipped
standard nav row (``nav:help`` + ``nav:hub:admin`` "↩ Administration").
The invoker-named author-lock footer is dynamic copy outside
FooterMode's vocabulary (renderer_override; the channel-panel
precedent).

Deliberate under-ports (parity beyond the goldens; in-code notes):
* the hub's Inventory/Customization-findings numbers are golden-pinned
  literals (the shipped ``services.customization_catalogue`` /
  ``settings_registry`` live reads belong to the settings-mutation
  panel slice — the servermanagement badge-literal precedent);
* both option rosters are pinned to the goldens' shipped inventory
  (19 actionable groups; the explorer's page-1 25) — re-derivation from
  the manifest inventory lands as the catalogue port arms;
* every click (group select, diagnostics, command access, explorer
  explain/reset/scope/paging) lands on a declared + honest pending
  terminal (sb/domain/settings/handlers.py) — the sub-panels
  (``settings_subsystem.*`` / ``settings_command_access.*`` families,
  ``governance.resolve_subsystem_state``) are their own port slices.
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
    "ensure_panel_refs",
    "install_settings_panels",
    "settings_access_spec",
    "settings_hub_spec",
]

# --- the shipped hub copy (views/settings/hub.py build_embed — the goldens
# pin every byte, double spaces included). ------------------------------------

_HUB_DESCRIPTION = (
    "Browse platform settings, bindings, resource requirements, and recent "
    "audit history.  The dropdown lists every group with something "
    "configurable (scalar edit + reset live on the group's page); use the "
    "buttons for cross-cutting diagnostics."
)

#: the shipped footer literal (hub.py set_footer) — outside FooterMode's
#: vocabulary, hence the renderer_override below (the utility/ux_lab/
#: channel/server_management precedent).
_HUB_FOOTER = ("Tip: `!platform customization` and `!platform "
               "settings-registry` expose the underlying catalogues.")

#: the shipped hub header fields, verbatim as the sweep guild captured them
#: (services read: settings_registry + customization_catalogue inventory) —
#: a pinned literal until the settings-mutation slice ports the live reads
#: (the server_management badge-literal precedent; module-docstring note).
_HUB_INVENTORY = ("`groups`: 19  ·  `subsystems`: 43  ·  `schemas`: 19\n"
                  "`settings`: 0  ·  `bindings`: 17  ·  `resources`: 15")
_HUB_FINDINGS = "*catalogue not built yet*"

#: the shipped actionable settings-group roster (value, label, emoji,
#: description) — customization_catalogue.actionable_settings_groups order,
#: verbatim; long descriptions carry the shipped 100-char SelectOption
#: truncation the goldens captured.
_HUB_GROUPS: tuple[tuple[str, str, str, str], ...] = (
    ("welcome", "Welcome", "👋",
     "Member greetings, farewells, and an optional entry role"),
    ("counters", "Server Counters", "📊",
     "Live member-count channels (total · humans · bots)"),
    ("security", "Server Security", "🛡️",
     "Raid detection + account-age screening on member join"),
    ("proof_channel", "Proof Channel", "📋",
     "Proof submission and exclusive access sessions"),
    ("role", "Roles", "🎭",
     "Time-based and XP-based automatic role assignment"),
    ("cleanup", "Cleanup", "🧹",
     "Prohibited words, command deletion, channel hygiene"),
    ("automod", "Automod", "🛡️",
     "Spam, invite links, excessive caps, and mass-mention filtering"),
    ("image_moderation", "Image moderation", "🖼️",
     "Scan uploaded images for sexual, violent, harassment, or hate content"),
    ("moderation", "Moderation", "🔨",
     "Warnings, timeouts, bans, mod logs"),
    ("logging", "Server Logging", "📝",
     "Per-guild moderation/cleanup event logging — channel selection, "
     "auto-create, and audit (S7)"),
    ("ai", "AI Platform", "🤖",
     "Read-only AI gateway diagnostics: provider state, feature flags, "
     "task routing, and request/failure c"),
    ("help", "Help", "📚",
     "Interactive help menu and command discovery"),
    ("economy", "Economy", "💰",
     "Daily coins, work, shop, balance"),
    ("xp", "XP & Levels", "⭐",
     "Experience points, levels, and leaderboards"),
    ("karma", "Karma", "✨",
     "Peer reputation — thank helpful members with !thanks"),
    ("blackjack", "Blackjack", "🃏",
     "Blackjack card game"),
    ("btd6", "BTD6 Assistant", "🐵",
     "Deterministic Bloons Tower Defense 6 assistant — tower/hero/map "
     "lookups, round threat summaries, and"),
    ("deathmatch", "Deathmatch", "⚔️",
     "1v1 duel battles"),
    ("rps_tournament", "Rock Paper Scissors", "✂️",
     "Rock Paper Scissors: quick play, PvP, bot matches, tournaments"),
)

# --- the shipped explorer copy (views/access/explorer.py — the golden pins
# every byte). -----------------------------------------------------------------

_ACCESS_DESCRIPTION = (
    "Read-only diagnostic for effective governance policy. Pick a subsystem "
    "and a scope, then press **Explain Access** to see the decision chain."
)

#: the shipped subsystem roster PAGE 1 (SUBSYSTEMS registration order, the
#: shipped 25-option page cap) — page 2 is unpinned by the golden and lands
#: with the explorer's own interaction slice (module-docstring note).
_ACCESS_SUBSYSTEMS: tuple[tuple[str, str, str, str], ...] = (
    ("help", "Help", "📚",
     "Interactive help menu and command discovery"),
    ("general", "General", "💬",
     "General bot commands and information"),
    ("four_twenty", "420", "🍃",
     "A leafy little easter-egg panel — wisdom and number trivia"),
    ("utility", "Utility", "🔧",
     "General utility commands"),
    ("economy", "Economy", "💰",
     "Daily coins, work, shop, balance"),
    ("inventory", "Inventory", "🎒",
     "Item management and crafting"),
    ("treasury", "Treasury", "🏛️",
     "Server-owned coin pool — contribute coins; managers disburse"),
    ("ticket", "Support Tickets", "🎫",
     "Private support tickets — open by command, panel, or the AI"),
    ("mining", "Mining", "⛏️",
     "Mining minigame and resource collection"),
    ("ux_lab", "UX Lab", "🧪",
     "Interface gallery — browse UI patterns, all fake & safe"),
    ("fishing", "Fishing", "🎣",
     "Fishing minigame — cast a line, build your collection"),
    ("creature", "Creatures", "🐾",
     "Catch original creatures and build your collection dex"),
    ("farm", "Chicken Farm", "🐔",
     "Idle egg farm — hens lay eggs over time; collect, sell, grow"),
    ("xp", "XP & Levels", "⭐",
     "Experience points, levels, and leaderboards"),
    ("karma", "Karma", "✨",
     "Peer reputation — thank helpful members with !thanks"),
    ("games", "Games", "🎮",
     "Competitive games and channel activities"),
    ("community", "Community", "🌱",
     "Progression, roles, and community activities"),
    ("community_spotlight", "Community Spotlight", "🌟",
     "Live server activity dashboard — leaders, level-ups, game stats"),
    ("blackjack", "Blackjack", "🃏",
     "Blackjack card game"),
    ("welcome", "Welcome", "👋",
     "Member greetings, farewells, and an optional entry role"),
    ("casino", "Casino", "🎰",
     "Group card games like multiplayer poker"),
    ("counters", "Server Counters", "📊",
     "Live member-count channels (total · humans · bots)"),
    ("btd6", "BTD6 Assistant", "🐵",
     "Deterministic Bloons Tower Defense 6 assistant — tower/hero/map "
     "lookups, round threat summaries, and"),
    ("deathmatch", "Deathmatch", "⚔️",
     "1v1 duel battles"),
    ("security", "Server Security", "🛡️",
     "Raid detection + account-age screening on member join"),
)

#: the shipped scope options (explorer.py — channel is the invoked-in
#: default; scope options carry no emoji).
_ACCESS_SCOPES: tuple[dict, ...] = (
    {"value": "channel", "label": "Channel (current)", "default": True,
     "description": "The channel this command was invoked in."},
    {"value": "category", "label": "Category (current)",
     "description": "The category that contains the channel."},
    {"value": "guild", "label": "Guild (server-wide)",
     "description": "Guild-level — no channel/category override."},
)


def _options(roster: tuple[tuple[str, str, str, str], ...]) -> tuple[dict, ...]:
    """(value, label, emoji, description) → the rich-option mapping shape
    the render grammar passes through verbatim."""
    return tuple(
        {"value": value, "label": label, "emoji": emoji,
         "description": description}
        for value, label, emoji, description in roster)


# --- the hub spec -------------------------------------------------------------------

async def _hub_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Inventory + Customization-findings header fields —
    golden-pinned literals (see the module-docstring under-port note)."""
    del ctx
    return (("Inventory", _HUB_INVENTORY),
            ("Customization findings", _HUB_FINDINGS))


def _hub_button(action_id: str, label: str, emoji: str) -> PanelActionSpec:
    """One shipped grey diagnostic button — emoji as a SEPARATE component
    field; the shipped persistent custom_id survives verbatim; the
    diagnostic sub-panels port with the settings-mutation slice, so every
    click lands on the polite pending terminal."""
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji,
        style=ActionStyle.SECONDARY,
        audience_tier="administrator",       # the shipped operator-hub gate
        handler=HandlerRef(f"settings.{action_id}_pending"),
        custom_id_override=f"settings_hub.{action_id}")


def settings_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.hub",
        subsystem="settings",
        title="⚙️ Settings Manager",
        # the shipped slash twin answered EPHEMERAL (goldens/settings/
        # sweep_slash_settings pins type-4 flags 64) — INVOKER audience.
        audience=Audience.INVOKER,
        # the shipped hub accent — discord.Color.blurple().
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_HUB_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("settings.hub_fields"))),
        selectors=(
            SelectorSpec(
                selector_id="subsystem_select", kind=SelectorKind.ENUM,
                options_source=_options(_HUB_GROUPS),
                placeholder="Open a settings group…",
                audience_tier="administrator",
                on_select=HandlerRef("settings.group_pending"),
                custom_id_override="settings_hub.subsystem_select"),
        ),
        actions=(
            # row 1 — the shipped grey diagnostic quartet.
            _hub_button("needs_setup", "Needs setup", "📋"),
            _hub_button("invalid", "Invalid settings", "⚠️"),
            _hub_button("missing_bindings", "Missing bindings", "🔗"),
            _hub_button("audit", "Recent changes", "🕒"),
            # row 2 — the Command access door (PR-6's panel is the
            # settings-mutation slice's port; pending terminal).
            _hub_button("command_access", "Command access", "🚪"),
        ),
        # the shipped hub carried NO standard nav row — the goldens pin
        # exactly three component rows; session_lifecycle takes the
        # never-strand exemption (the server_management-hub precedent:
        # every component override-pinned, nothing minted, no anchor).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Tip: `!platform "
            "customization` and `!platform settings-registry` expose the "
            "underlying catalogues.' (views/settings/hub.py build_embed "
            "set_footer) — outside FooterMode's none/subsystem/provenance "
            "vocabulary (goldens/settings pin the byte; the utility/ux_lab/"
            "channel/server_management precedent). The override delegates "
            "to the grammar renderer and replaces ONLY the footer; body, "
            "fields, selector, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("subsystem_select",),
            ("needs_setup", "invalid", "missing_bindings", "audit"),
            ("command_access",),
        )),)),
    )


# --- the access-explorer spec --------------------------------------------------------

async def _access_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped empty-selection state (the golden pins the two prompt
    fields; the renderer override marks them inline — the shipped
    add_field(inline=True) wire shape)."""
    del ctx
    return (("Subsystem", "_Pick from the first dropdown._"),
            ("Scope", "_Pick from the second dropdown._"))


def settings_access_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.access",
        subsystem="settings",
        title="🔍 Access Policy Explorer",
        # the shipped explorer was invoker-locked (the footer says so).
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blue().
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_ACCESS_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("settings.access_fields"))),
        selectors=(
            # the shipped paged subsystem select — a run-minted session id
            # (the golden pins <cid:1>) with the shipped page-1/2
            # placeholder; the 25-option page-1 roster is pinned, page 2
            # lands with the explorer's interaction slice.
            SelectorSpec(
                selector_id="subsystem", kind=SelectorKind.ENUM,
                options_source=_options(_ACCESS_SUBSYSTEMS),
                placeholder="Choose a subsystem… — page 1/2",
                audience_tier="administrator",
                on_select=HandlerRef("settings.access_subsystem_pending")),
            # the shipped PERSISTENT scope select (access:select_scope).
            SelectorSpec(
                selector_id="select_scope", kind=SelectorKind.ENUM,
                options_source=_ACCESS_SCOPES,
                placeholder="Choose a scope…",
                audience_tier="administrator",
                on_select=HandlerRef("settings.access_scope_pending"),
                custom_id_override="access:select_scope"),
        ),
        actions=(
            # row 2 — the shipped action pair (emoji IN the labels).
            PanelActionSpec(
                action_id="explain", label="🔬 Explain Access",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_explain_pending"),
                custom_id_override="access:explain"),
            PanelActionSpec(
                action_id="reset", label="🔄 Reset",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_reset_pending"),
                custom_id_override="access:reset"),
            # row 3 — the shipped session page-turn pair (run-minted ids;
            # the golden pins <cid:2>/<cid:3>; Prev renders disabled on
            # page 1 via the renderer override).
            PanelActionSpec(
                action_id="access_prev", label="◀ Prev",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_page_pending")),
            PanelActionSpec(
                action_id="access_next", label="Next ▶",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_page_pending")),
        ),
        # the shipped explorer carried the standard nav row — 📚 Help +
        # ↩ Administration (the shipped parent hub is `admin`, pinned
        # explicitly until the admin hub's own band installs a resolver —
        # the channel/ux_lab precedent).
        navigation=NavigationSpec(home_hub="admin"),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_access"),
        justification=(
            "the shipped explorer footer is the DYNAMIC author-lock notice "
            "'Invoker: <name>. Only the invoker can interact with this "
            "panel.' (views/access/explorer.py set_footer) — invoker-named "
            "copy outside FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/settings/sweep_settings_access pins the byte; the "
            "channel author-lock-footer precedent). The shipped selection "
            "prompt fields render inline=True and the first-page ◀ Prev "
            "button renders disabled — both outside the grammar's "
            "vocabulary (2-tuple fields render inline=False; actions carry "
            "no disabled state). The override delegates to the grammar "
            "renderer and adjusts ONLY those three surfaces; body, "
            "selectors, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("subsystem",),
            ("select_scope",),
            ("explain", "reset"),
            ("access_prev", "access_next"),
        )),)),
    )


# --- renderer overrides ---------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=_HUB_FOOTER))


async def _render_access(spec: PanelSpec, ctx) -> object:
    """Grammar render + the three shipped adjustments (see justification):
    the invoker-named footer, inline prompt fields, first-page ◀ Prev
    disabled. The invoker name arrives via the opening request's args
    (``settings.access_view`` — the economy author-display precedent)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    name = str(ctx.params.get("invoker_name", "") or "") or "unknown"
    footer = f"Invoker: {name}. Only the invoker can interact with this panel."
    embed = _dc_replace(
        rendered.embed, footer=footer,
        fields=tuple((f[0], f[1], True) for f in rendered.embed.fields))
    components = tuple(
        _dc_replace(c, disabled=True)
        if c.custom_id == f"{spec.panel_id}.access_prev" else c
        for c in rendered.components)
    return _dc_replace(rendered, embed=embed, components=components)


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("settings.hub")):
        panel("settings.hub")(settings_hub_spec)
    if not is_registered(PanelRef("settings.access")):
        panel("settings.access")(settings_access_spec)
    if not is_registered(HandlerRef("settings.render_hub")):
        handler("settings.render_hub")(_render_hub)
    if not is_registered(HandlerRef("settings.render_access")):
        handler("settings.render_access")(_render_access)
    if not is_registered(ProviderRef("settings.hub_fields")):
        provider("settings.hub_fields")(_hub_fields)
    if not is_registered(ProviderRef("settings.access_fields")):
        provider("settings.access_fields")(_access_fields)


_register_refs()


def install_settings_panels() -> PanelSpec:
    """Register the hub + explorer with the panels registry (fences run
    here); composition-root/boot call. Idempotent for identical specs.
    Returns the hub spec (the band-1 contract shape)."""
    hub = settings_hub_spec()
    for spec in (hub, settings_access_spec()):
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
    return hub


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()
