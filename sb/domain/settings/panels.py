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
* the group SELECT NAVIGATES read-only (``settings.open_group``): it
  opens the group's read-only operator-spine hub when one is ensured
  (welcome/counters/security/automod/image_moderation — the shipped
  SettingsHubView group-select navigation, as a read subset), and lands
  on the honest pending terminal for every other group; the per-group
  scalar EDIT + reset (the ``SubsystemSettingsView`` mutation) stays the
  settings-mutation slice's port;
* the hub's remaining pending clicks (🕒 Recent changes, 🚪 Command
  access) land on a declared + honest pending terminal
  (sb/domain/settings/handlers.py) — the audit view and the Command
  Access panel (``settings_command_access.*`` family) are later slices'
  ports, as is the per-group mutation page (``settings_subsystem.*``).
  The EXPLORER'S six controls are ARMED (curation rows 82-87):
  subsystem/scope selects, Explain, Reset and the page-turn pair drive
  the governance diagnostic read seam
  (``governance.resolve_subsystem_state``) + the K7 ``SET_VISIBILITY``
  clear lane, byte-stable on the open golden. The three READ-ONLY
  diagnostic buttons are ARMED (settings-admin slice 1): 📋 Needs setup /
  ⚠️ Invalid settings / 🔗 Missing bindings open their shipped sub-panels
  (disbot/views/settings/{needs_setup,invalid_settings,missing_bindings}
  .py, copy verbatim) as declared PanelRef open-child terminals — the
  channel sub-panel precedent; the wire ``settings_hub.*`` custom_ids
  never move.
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
    "settings_invalid_spec",
    "settings_missing_bindings_spec",
    "settings_needs_setup_spec",
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
    # --- post-flip growth (NOT a shipped-roster byte): the D-0082 game
    # sections group (design §5) — routes to the games.sections settings
    # panel via settings.open_group; appended so the 19 shipped options
    # keep their golden order (goldens re-cut with the 20th option).
    ("games", "Games", "🎮",
     "Competitive games and channel activities"),
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


def _hub_button(action_id: str, label: str, emoji: str,
                target: PanelRef | None = None) -> PanelActionSpec:
    """One shipped grey diagnostic button — emoji as a SEPARATE component
    field; the shipped persistent custom_id survives verbatim. An armed
    button routes to its diagnostic sub-panel (*target* — the PanelRef
    open-child terminal, the channel-band precedent); the rest land on
    the polite pending terminal until their own slice ports them."""
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji,
        style=ActionStyle.SECONDARY,
        audience_tier="administrator",       # the shipped operator-hub gate
        handler=target or HandlerRef(f"settings.{action_id}_pending"),
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
                # the shipped SettingsHubView group select NAVIGATED
                # (read-only) to each group's page — armed to open the
                # group's read-only operator-spine hub when one exists
                # (settings.open_group), the pending terminal otherwise.
                # The wire custom_id is unchanged, so no golden churns.
                on_select=HandlerRef("settings.open_group"),
                custom_id_override="settings_hub.subsystem_select"),
        ),
        actions=(
            # row 1 — the shipped grey diagnostic quartet. The three
            # read-only diagnostics are ARMED (settings-admin slice 1) as
            # open-child PanelRef terminals; the audit view is slice 2.
            _hub_button("needs_setup", "Needs setup", "📋",
                        PanelRef("settings.needs_setup")),
            _hub_button("invalid", "Invalid settings", "⚠️",
                        PanelRef("settings.invalid")),
            _hub_button("missing_bindings", "Missing bindings", "🔗",
                        PanelRef("settings.missing_bindings")),
            _hub_button("audit", "Recent changes", "🕒"),
            # row 2 — the Command access door (PR-6's panel is the
            # command-access slice's port; pending terminal).
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


# --- the three armed diagnostic sub-panels (settings-admin slice 1) ------------------
#
# Oracle-verbatim ports of the shipped read-only diagnostics
# (disbot/views/settings/needs_setup.py / invalid_settings.py /
# missing_bindings.py — copy byte-verbatim, double spaces included):
#   * Needs setup   — declaration-only: required BindingSpec slots +
#     REQUIRED-priority ResourceRequirement intents per subsystem, read
#     from the ONE manifest inventory (the shipped subsystem-schema
#     registry's successor);
#   * Invalid settings — walks every declared SettingSpec through the K7
#     typed resolution (service.resolve_setting) and lists valid=False
#     rows (coercion/validator failure; resolver fell back to default);
#   * Missing bindings — every declared BindingSpec whose runtime status
#     is not `bound` (the subsystem_bindings store read; a declared slot
#     with no row is the shipped `unresolved`).
# Back to Hub is a PanelRef open-child terminal (the channel sub-panel
# precedent); its custom_id is run-minted — the shipped
# ``settings_needs_setup.back`` family ids are NOT in the compat freeze,
# and minting keeps compat/compat-frozen.json untouched (PL-001 flag).

_NEEDS_SETUP_DESCRIPTION = (
    "Subsystems whose schema declares **required** bindings or "
    "resource requirements.  This shows what _should_ be "
    "configured; the *bound vs unresolved* status of each slot "
    "lives in the **Missing bindings** view."
)

_INVALID_DESCRIPTION = (
    "Settings whose current KV value failed coercion or "
    "validation.  Resolver fell back to the declared default "
    "for runtime safety; fix the underlying KV row via the "
    "subsystem page's edit/reset control."
)

_MISSING_BINDINGS_DESCRIPTION = (
    "Declared bindings whose runtime status is not `bound`.  "
    "Includes unresolved slots (no row yet), targets that "
    "disappeared from Discord, and kind-drift cases.  Bind "
    "controls land alongside the setup wizard's binding "
    "section (planned)."
)

#: the shipped DM guards + empty states, verbatim.
_INVALID_DM = ("*Run this from within a guild — DM has no scalar values "
               "to resolve.*")
_MISSING_DM = ("*Run this from within a guild — DM has no per-guild "
               "binding state.*")
_NEEDS_SETUP_EMPTY = ("*No subsystem declares any required bindings or "
                      "resources.*")

#: the shipped S6 footer literal (invalid_settings.py set_footer) — kept
#: verbatim; the "edit flow" is the settings-mutation slice here.
_INVALID_FOOTER = "S6 introduces the edit flow that fixes these in place."


def _iter_settings_facets() -> tuple[tuple[str, object], ...]:
    """(subsystem key, manifest) in key order — the ONE manifest inventory
    walk (the ai_tasks.capabilities_overview / help command_inventory
    precedent). The shipped diagnostics read ``all_schemas()``; the
    compiled architecture's subsystem-schema truth is sb.manifest."""
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg

    pairs: list[tuple[str, object]] = []
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda i: i.name):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        for manifest in ([getattr(module, "MANIFEST", None)]
                         + list(getattr(module, "MANIFESTS", ()) or ())):
            if manifest is None:
                continue
            pairs.append((str(getattr(manifest, "key", info.name)), manifest))
    return tuple(sorted(pairs, key=lambda p: p[0]))


def _gather_required_bindings() -> dict[str, list[str]]:
    """``{subsystem: [required binding names]}`` (needs_setup.py verbatim,
    over the manifest settings facet — BindingSpecs ride the same tuple)."""
    from sb.spec.settings import BindingSpec

    out: dict[str, list[str]] = {}
    for key, manifest in _iter_settings_facets():
        required = [b.name for b in getattr(manifest, "settings", ()) or ()
                    if isinstance(b, BindingSpec) and b.required]
        if required:
            out[key] = required
    return out


def _gather_required_resources() -> dict[str, list[str]]:
    """``{subsystem: [required resource intents]}`` (needs_setup.py
    verbatim — ProvisioningPriority.REQUIRED only)."""
    from sb.spec.settings import ProvisioningPriority, ResourceRequirement

    out: dict[str, list[str]] = {}
    for key, manifest in _iter_settings_facets():
        required = [
            r.intent for r in getattr(manifest, "settings", ()) or ()
            if isinstance(r, ResourceRequirement)
            and r.provisioning.priority is ProvisioningPriority.REQUIRED]
        if required:
            out[key] = required
    return out


async def _needs_setup_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Needs-setup body (guild-independent — declarations
    only): the required-binding + required-resource rosters, or the
    shipped empty state."""
    del ctx  # guild-independent view — uses declarations only
    bindings = _gather_required_bindings()
    resources = _gather_required_resources()
    if not bindings and not resources:
        return (("Result", _NEEDS_SETUP_EMPTY),)
    fields: list[tuple[str, str]] = []
    if bindings:
        lines = [
            f"`{sub}` — required: {', '.join(f'`{b}`' for b in names)}"
            for sub, names in sorted(bindings.items())]
        fields.append(
            (f"Required bindings ({sum(len(v) for v in bindings.values())})",
             "\n".join(lines)[:1024]))
    if resources:
        lines = [
            f"`{sub}` — required: {', '.join(f'`{r}`' for r in names)}"
            for sub, names in sorted(resources.items())]
        fields.append(
            (f"Required resources ({sum(len(v) for v in resources.values())})",
             "\n".join(lines)[:1024]))
    return tuple(fields)


async def _invalid_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Invalid-settings body: every declared SettingSpec
    resolved through the K7 typed read (service.resolve_setting — the
    shipped settings_resolution port), rows with valid=False listed
    verbatim; per-row soft fail (invalid_settings.py)."""
    from sb.spec.settings import SettingSpec

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    if not guild_id:
        return (("Result", _INVALID_DM),)

    from sb.domain.settings import service as settings_service

    invalid: list[str] = []
    scanned = 0
    for sub_name, manifest in _iter_settings_facets():
        for spec in getattr(manifest, "settings", ()) or ():
            if not isinstance(spec, SettingSpec):
                continue
            scanned += 1
            try:
                resolution = await settings_service.resolve_setting(
                    guild_id, sub_name, spec.name, spec=spec)
            except Exception as exc:  # noqa: BLE001 — soft-fail per row
                invalid.append(
                    f"`{sub_name}.{spec.name}` — resolver raised "
                    f"{type(exc).__name__}")
                continue
            if resolution is None or resolution.valid:
                continue
            diag = (f" ({resolution.diagnostics[0]})"
                    if resolution.diagnostics else "")
            invalid.append(
                f"`{sub_name}.{spec.name}` = `{resolution.raw!r}` "
                f"→ fallback to `{resolution.default!r}`{diag}")
    if not invalid:
        return (("Result",
                 f"*✅ No invalid settings.  ({scanned} setting(s) "
                 f"scanned.)*"),)
    return ((f"Invalid settings ({len(invalid)} of {scanned} scanned)",
             "\n".join(invalid)[:1024]),)


async def _missing_bindings_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Missing-bindings body: every declared BindingSpec whose
    runtime status is not ``bound`` (missing_bindings.py) — the
    subsystem_bindings store read; a declared slot with no row is the
    shipped ``unresolved``."""
    from sb.spec.settings import BindingSpec

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    if not guild_id:
        return (("Result", _MISSING_DM),)

    from sb.kernel.db import settings as db_settings

    try:
        stored = {(str(row["subsystem"]), str(row["binding_name"])):
                  (row["target_id"], str(row["status"]))
                  for row in await db_settings.fetchall_bindings(guild_id)}
    except Exception as exc:  # noqa: BLE001 — the store read soft-fails
        return (("Result",
                 f"*Binding store read raised {type(exc).__name__} — "
                 f"try again.*"),)

    rows: list[str] = []
    scanned = 0
    for sub_name, manifest in _iter_settings_facets():
        for spec in getattr(manifest, "settings", ()) or ():
            if not isinstance(spec, BindingSpec):
                continue
            scanned += 1
            target_id, status = stored.get(
                (sub_name, spec.name), (None, "unresolved"))
            if status == "bound" and target_id is not None:
                continue
            required_marker = "**required**" if spec.required else "optional"
            rows.append(
                f"`{sub_name}.{spec.name}` ({required_marker}) — "
                f"status=`{status}` kind=`{spec.kind.value}`")
    if not rows:
        return (("Result",
                 f"*✅ Every binding is bound.  ({scanned} binding(s) "
                 f"scanned.)*"),)
    return ((f"Unbound or invalid bindings ({len(rows)} of {scanned} "
             f"scanned)", "\n".join(rows)[:1024]),)


def _diag_back_action(action_id: str) -> PanelActionSpec:
    """The shipped ↩ Back to Hub button (every diagnostic view carried
    one) — a PanelRef open-child terminal back to the hub (the channel
    sub-panel Cancel precedent). Run-minted custom_id: the shipped
    ``settings_*.back`` ids are not compat-frozen, so nothing is pinned.
    *action_id* is per-panel — the custom_id namespace admits ONE claimant
    per (kind, value) repo-wide (the bare `back` leaf is btd6's)."""
    return PanelActionSpec(
        action_id=action_id, label="Back to Hub", emoji="↩",
        style=ActionStyle.SECONDARY, audience_tier="administrator",
        handler=PanelRef("settings.hub"))


def settings_needs_setup_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.needs_setup",
        subsystem="settings",
        title="📋 Needs setup",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.gold().
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        body=(TextBlock(_NEEDS_SETUP_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("settings.needs_setup_fields"))),
        actions=(_diag_back_action("needs_setup_back"),),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("settings.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_needs_setup"),
        justification=(
            "the shipped Needs-setup footer is the DYNAMIC coverage count "
            "'N subsystem(s) with required bindings · N with required "
            "resources · N subsystems total.' (views/settings/"
            "needs_setup.py set_footer), rendered only when a requirement "
            "exists — count-keyed copy outside FooterMode's none/subsystem/"
            "provenance vocabulary (the settings-hub footer-literal "
            "precedent). The override delegates to the grammar renderer "
            "and replaces ONLY the footer; body, fields, actions and "
            "layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("needs_setup_back",),)),)),
    )


def settings_invalid_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.invalid",
        subsystem="settings",
        title="⚠️ Invalid settings",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.orange().
        frame=EmbedFrameSpec(style_token="orange",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_INVALID_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("settings.invalid_fields"))),
        actions=(_diag_back_action("invalid_back"),),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("settings.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_invalid"),
        justification=(
            "the shipped Invalid-settings footer ('S6 introduces the edit "
            "flow that fixes these in place.' — views/settings/"
            "invalid_settings.py set_footer) renders CONDITIONALLY, only "
            "when an invalid row exists — state-keyed presence outside "
            "FooterMode's none/subsystem/provenance vocabulary (the "
            "settings-hub footer-literal precedent). The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "footer; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("invalid_back",),)),)),
    )


def settings_missing_bindings_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.missing_bindings",
        subsystem="settings",
        title="🔗 Missing bindings",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.gold(); the shipped view set
        # no footer, so the plain grammar render carries every byte.
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        body=(TextBlock(_MISSING_BINDINGS_DESCRIPTION),
              FieldsBlock(
                  provider=ProviderRef("settings.missing_bindings_fields"))),
        actions=(_diag_back_action("missing_bindings_back"),),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("settings.hub")),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("missing_bindings_back",),)),)),
    )


async def _render_needs_setup(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped coverage-count footer (see
    justification) — declaration-only recompute, no store read; absent
    any requirement the shipped view set no footer (the early return)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    bindings = _gather_required_bindings()
    resources = _gather_required_resources()
    if not bindings and not resources:
        return rendered
    from sb.domain.governance.registry import SUBSYSTEM_META

    footer = (f"{len(bindings)} subsystem(s) with required bindings · "
              f"{len(resources)} with required resources · "
              f"{len(SUBSYSTEM_META)} subsystems total.")
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=footer))


async def _render_invalid(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped conditional footer (see justification):
    present exactly when an invalid row rendered — derived from the
    rendered field name, so the settings scan runs ONCE (in the fields
    provider), never twice."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    if not any(name.startswith("Invalid settings")
               for name, *_ in rendered.embed.fields):
        return rendered
    return _dc_replace(
        rendered, embed=_dc_replace(rendered.embed, footer=_INVALID_FOOTER))


# --- the access-explorer spec --------------------------------------------------------

#: the explorer's scope labels (the _ACCESS_SCOPES roster, keyed).
_ACCESS_SCOPE_LABELS = {
    "channel": "Channel (current)",
    "category": "Category (current)",
    "guild": "Guild (server-wide)",
}

_ACCESS_STATE_BADGES = {
    "enabled": "✅ Enabled",
    "disabled": "🚫 Disabled",
    "blocked_dep": "⛔ Blocked by dependency",
}


def _access_page2_options() -> tuple[dict, ...]:
    """The subsystem roster PAGE 2 — every governance-registered subsystem
    the pinned page-1 roster does not carry, in registry declaration order
    (the golden pins page 1 only; page 2 re-derives from the ONE registry
    truth, so it can never drift from what governance actually gates).
    Labels/emoji reuse the curated hub roster where a group exists; the
    rest fall back to a mechanical title-case (honest, unpinned bytes).
    Lazy governance import — the sections.py seam shape (PL-001)."""
    from sb.domain.governance.registry import SUBSYSTEM_META

    page1 = {value for value, _, _, _ in _ACCESS_SUBSYSTEMS}
    curated = {value: (label, emoji, description)
               for value, label, emoji, description in _HUB_GROUPS}
    options: list[dict] = []
    for key, meta in SUBSYSTEM_META.items():
        if key in page1:
            continue
        label, emoji, description = curated.get(
            key, (key.replace("_", " ").title(), "",
                  f"Visibility tier: {meta.get('visibility_tier', 'user')}"))
        option = {"value": key, "label": label, "description": description}
        if emoji:
            option["emoji"] = emoji
        options.append(option)
    return tuple(options[:25])


def access_page_count() -> int:
    return 2 if _access_page2_options() else 1


def _access_option_label(value: str) -> str:
    """Display label for a subsystem value across both roster pages."""
    for v, label, _, _ in _ACCESS_SUBSYSTEMS:
        if v == value:
            return label
    for option in _access_page2_options():
        if option["value"] == value:
            return str(option["label"])
    return value


def _access_axes(ctx_or_params, scope: str,
                 channel_id: int | None) -> dict:
    """Map the explorer's scope selection onto the resolver's context axes:
    guild = no channel/category override lane; category = category + guild;
    channel = the full chain (channel > category > guild)."""
    def _int(value) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    category_id = _int(ctx_or_params.get("category_id"))
    if scope == "guild":
        return {}
    if scope == "category":
        return {"category_id": category_id}
    return {"channel_id": _int(channel_id), "category_id": category_id}


async def _access_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped empty-selection state (the golden pins the two prompt
    fields; the renderer override marks them inline — the shipped
    add_field(inline=True) wire shape). With a session selection in
    ``ctx.params`` (the armed interaction slice), the fields render the
    RESOLVED state + provenance through the governance read seam
    (``resolve_subsystem_state`` — lazy import, the sections.py shape)."""
    params = dict(getattr(ctx, "params", {}) or {})
    subsystem = str(params.get("access_subsystem") or "")
    if not subsystem:
        return (("Subsystem", "_Pick from the first dropdown._"),
                ("Scope", "_Pick from the second dropdown._"))

    from sb.domain.governance import service as governance

    scope = str(params.get("access_scope") or "channel")
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    res = await governance.resolve_subsystem_state(
        guild_id, subsystem,
        **_access_axes(params, scope, getattr(ctx, "channel_id", None)))
    badge = _ACCESS_STATE_BADGES.get(res.state.value, res.state.value)
    if not res.known:
        provenance = "unregistered subsystem — fail-open (dispatch gate)"
    elif res.source.value == "registry_default":
        provenance = "registry default (no override)"
    elif res.source.value == "dependency_block":
        provenance = ("dependency block: "
                      + ", ".join(res.dependency_blocks))
    else:
        provenance = f"{res.source.value} override"
    subsystem_value = (f"{_access_option_label(subsystem)} (`{subsystem}`)\n"
                       f"{badge} — {provenance}")
    scope_value = (f"{_ACCESS_SCOPE_LABELS.get(scope, scope)}\n"
                   "_Press **Explain Access** for the decision chain._")
    return (("Subsystem", subsystem_value), ("Scope", scope_value))


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
                on_select=HandlerRef("settings.access_subsystem")),
            # the shipped PERSISTENT scope select (access:select_scope).
            SelectorSpec(
                selector_id="select_scope", kind=SelectorKind.ENUM,
                options_source=_ACCESS_SCOPES,
                placeholder="Choose a scope…",
                audience_tier="administrator",
                on_select=HandlerRef("settings.access_scope"),
                custom_id_override="access:select_scope"),
        ),
        actions=(
            # row 2 — the shipped action pair (emoji IN the labels).
            PanelActionSpec(
                action_id="explain", label="🔬 Explain Access",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_explain"),
                custom_id_override="access:explain"),
            PanelActionSpec(
                action_id="reset", label="🔄 Reset",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_reset"),
                custom_id_override="access:reset"),
            # row 3 — the shipped session page-turn pair (run-minted ids;
            # the golden pins <cid:2>/<cid:3>; Prev renders disabled on
            # page 1 via the renderer override).
            PanelActionSpec(
                action_id="access_prev", label="◀ Prev",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_page")),
            PanelActionSpec(
                action_id="access_next", label="Next ▶",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.access_page")),
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


def _mark_selected(options: tuple, value: str) -> tuple:
    """Move the ``default`` flag onto the selected option (re-render only —
    the open state never reaches here, so the golden bytes never move)."""
    return tuple({**dict(o), "default": dict(o).get("value") == value}
                 if isinstance(o, dict) else o for o in options)


async def _render_access(spec: PanelSpec, ctx) -> object:
    """Grammar render + the three shipped adjustments (see justification):
    the invoker-named footer, inline prompt fields, first-page ◀ Prev
    disabled. The invoker name arrives via the opening request's args
    (``settings.access_view`` — the economy author-display precedent).

    The armed interaction slice re-renders through the SAME override with
    the session selection in ``ctx.params`` (the engine's click-time
    re-resolution): ``access_page`` 2 swaps the subsystem roster onto the
    registry-derived page 2 (+ the honest ``page 2/2`` placeholder) and
    flips which page-turn button is disabled; a selected subsystem/scope
    moves the ``default`` flag on its select. With NO params (the golden's
    open state) every branch below reduces to the shipped bytes: page 1,
    ◀ Prev disabled, Next ▶ live, options untouched."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    name = str(ctx.params.get("invoker_name", "") or "") or "unknown"
    footer = f"Invoker: {name}. Only the invoker can interact with this panel."
    embed = _dc_replace(
        rendered.embed, footer=footer,
        fields=tuple((f[0], f[1], True) for f in rendered.embed.fields))
    try:
        page = int(ctx.params.get("access_page", 1) or 1)
    except (TypeError, ValueError):
        page = 1
    page_count = access_page_count()
    page = min(max(page, 1), page_count)
    selected_subsystem = str(ctx.params.get("access_subsystem") or "")
    selected_scope = str(ctx.params.get("access_scope") or "")
    components = []
    for c in rendered.components:
        if c.custom_id == f"{spec.panel_id}.access_prev":
            c = _dc_replace(c, disabled=page <= 1)
        elif c.custom_id == f"{spec.panel_id}.access_next":
            c = _dc_replace(c, disabled=page >= page_count)
        elif c.custom_id == f"{spec.panel_id}.subsystem":
            options = c.options
            if page > 1:
                options = _access_page2_options()
                c = _dc_replace(
                    c, options=options,
                    placeholder=f"Choose a subsystem… — page {page}/"
                                f"{page_count}")
            if selected_subsystem:
                c = _dc_replace(
                    c, options=_mark_selected(options, selected_subsystem))
        elif c.custom_id == "access:select_scope" and selected_scope:
            c = _dc_replace(
                c, options=_mark_selected(c.options, selected_scope))
        components.append(c)
    return _dc_replace(rendered, embed=embed, components=tuple(components))


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("settings.hub")):
        panel("settings.hub")(settings_hub_spec)
    if not is_registered(PanelRef("settings.access")):
        panel("settings.access")(settings_access_spec)
    if not is_registered(PanelRef("settings.needs_setup")):
        panel("settings.needs_setup")(settings_needs_setup_spec)
    if not is_registered(PanelRef("settings.invalid")):
        panel("settings.invalid")(settings_invalid_spec)
    if not is_registered(PanelRef("settings.missing_bindings")):
        panel("settings.missing_bindings")(settings_missing_bindings_spec)
    if not is_registered(HandlerRef("settings.render_hub")):
        handler("settings.render_hub")(_render_hub)
    if not is_registered(HandlerRef("settings.render_access")):
        handler("settings.render_access")(_render_access)
    if not is_registered(HandlerRef("settings.render_needs_setup")):
        handler("settings.render_needs_setup")(_render_needs_setup)
    if not is_registered(HandlerRef("settings.render_invalid")):
        handler("settings.render_invalid")(_render_invalid)
    if not is_registered(ProviderRef("settings.hub_fields")):
        provider("settings.hub_fields")(_hub_fields)
    if not is_registered(ProviderRef("settings.access_fields")):
        provider("settings.access_fields")(_access_fields)
    if not is_registered(ProviderRef("settings.needs_setup_fields")):
        provider("settings.needs_setup_fields")(_needs_setup_fields)
    if not is_registered(ProviderRef("settings.invalid_fields")):
        provider("settings.invalid_fields")(_invalid_fields)
    if not is_registered(ProviderRef("settings.missing_bindings_fields")):
        provider("settings.missing_bindings_fields")(_missing_bindings_fields)


_register_refs()


def install_settings_panels() -> PanelSpec:
    """Register the hub + explorer + the three armed diagnostics with the
    panels registry (fences run here); composition-root/boot call.
    Idempotent for identical specs. Returns the hub spec (the band-1
    contract shape)."""
    hub = settings_hub_spec()
    for spec in (hub, settings_access_spec(), settings_needs_setup_spec(),
                 settings_invalid_spec(), settings_missing_bindings_spec()):
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
    return hub


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()
