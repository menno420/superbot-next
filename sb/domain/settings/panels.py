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
  SettingsHubView group-select navigation, as a read subset), the
  ``games`` dedicated panel, and — for every OTHER (non-hub) group — the
  ported per-group scalar EDIT page ``settings.group_edit`` (settings
  epic S0, owner ruling option A);
* the per-group EDIT page (``settings.group_edit``) is the ported
  ``SubsystemSettingsView`` frame (settings epic S0): the read embed +
  the windowed edit/reset selects + Back-to-Hub / Open-Panel nav; S0
  wires the S1 bool toggle end to end over the K7 ``settings.set_scalar``
  / ``clear_scalar`` lanes, with the per-type widgets (enum / number /
  text / channel / role / presets) landing as slices S2–S7. It replaces
  the retired ``settings.group_pending`` terminal for the non-hub groups.
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
  never move. The 🕒 Recent-changes AUDIT view is ARMED (settings-admin
  slice 2): the shipped audit_view.py last-10 read, ported over the K7
  central audit spine (``audit_log`` rows with ``subsystem='settings'``
  — the shipped ``settings_mutation_audit`` table's successor here).
  The 🚪 COMMAND ACCESS panel is ARMED (settings-admin slice 3 — the
  set's one WRITE surface): the shipped edit_command_access.py port
  (PR-6) whose mutations REUSE the live platform command-access K7
  lanes (``platform.set_access_mode`` / ``set_access_channels`` —
  sb/domain/platform/command_access.py, the setup-wizard step-8 seam);
  the oracle's ``delete_blocked_commands`` toggle has no seam in the
  policy store here (mode + channels only) — an honest under-port.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode, ReplyVisibility
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
    "settings_audit_spec",
    "settings_command_access_spec",
    "settings_group_edit_enum_spec",
    "settings_group_edit_number_spec",
    "settings_group_edit_spec",
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
            # row 1 — the shipped grey diagnostic quartet, all four ARMED
            # as open-child PanelRef terminals (the three read-only
            # diagnostics: settings-admin slice 1; the audit view:
            # slice 2).
            _hub_button("needs_setup", "Needs setup", "📋",
                        PanelRef("settings.needs_setup")),
            _hub_button("invalid", "Invalid settings", "⚠️",
                        PanelRef("settings.invalid")),
            _hub_button("missing_bindings", "Missing bindings", "🔗",
                        PanelRef("settings.missing_bindings")),
            _hub_button("audit", "Recent changes", "🕒",
                        PanelRef("settings.audit")),
            # row 2 — the Command access door, ARMED (settings-admin
            # slice 3): PR-6's shipped panel as a PanelRef open-child
            # terminal over the live platform K7 write lanes.
            _hub_button("command_access", "Command access", "🚪",
                        PanelRef("settings.command_access")),
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


# --- the armed audit sub-panel (settings-admin slice 2) ------------------------------
#
# Oracle-verbatim port of the shipped 🕒 Recent-changes view
# (disbot/views/settings/audit_view.py — the last 10 rows of the
# settings-mutation audit trail, DM guard + missing-table + empty-table
# degrades, copy verbatim where the machinery names allow). The shipped
# `settings_mutation_audit` table (SettingsMutationPipeline.set_value's
# write) maps onto the K7 central audit spine here: `audit_log` rows with
# `subsystem='settings'` — the workflow engine writes ONE row per settings
# compound op (set_scalar/clear_scalar/bind/unbind; sb/kernel/workflow/
# audit.py emit_central_audit), so the trail this panel reads covers the
# shipped scalar edits + resets AND the binding set/clear lane. Read via
# the K3 pool seam (the btd6 oracle_cards audit-spine read — the D-0046
# re-home precedent; diagnostics never write).

_AUDIT_DESCRIPTION = (
    "Most recent rows from `audit_log` (`subsystem = settings`).  "
    "Populated by every scalar edit + reset and binding set/clear "
    "routed through the K7 settings mutation ops "
    "(`settings.set_scalar` / `clear_scalar` / `bind` / `unbind` — "
    "the shipped `SettingsMutationPipeline.set_value` lane's "
    "successor)."
)

#: the shipped DM guard, verbatim (audit_view.py).
_AUDIT_DM = "*Run this from within a guild — DM has no audit history.*"

#: the shipped empty state, verbatim.
_AUDIT_EMPTY = "*No audit rows for this guild yet.*"

#: the shipped row cap (audit_view.py _RECENT_LIMIT), verbatim.
_AUDIT_RECENT_LIMIT = 10


def _audit_leg(text: object) -> dict | None:
    """One side of the engine's prev/new rollup (`{leg_name: before/after}`
    JSON text — sb/kernel/workflow/engine.py _rollup): the single leg's
    payload dict, or None when the text isn't that shape."""
    import json

    try:
        payload = json.loads(text) if text else None
    except (TypeError, ValueError):
        return None
    if isinstance(payload, dict) and payload:
        first = next(iter(payload.values()))
        if isinstance(first, dict):
            return first
    return None


def _audit_change(row: dict) -> tuple[str, str, str]:
    """(label, new, prev) for one audit_log row — the shipped line's
    `subsystem.name = new (was prev)` slots. Scalar legs carry
    ``{"key", "value"}`` (the persisted `subsystem.name` key, the shipped
    label verbatim); binding legs carry ``{"resource_id"}`` (label = the
    op target — the binding name lives in binding_audit_log, not the
    spine rollup: an honest under-render, not a second table read)."""
    new_leg = _audit_leg(row.get("new_value"))
    prev_leg = _audit_leg(row.get("prev_value"))
    label = str(row.get("target") or "?")
    for leg in (new_leg, prev_leg):
        if leg is not None and "key" in leg:
            label = str(leg["key"])
            break

    def _value(leg: dict | None, raw: object) -> str:
        if leg is not None:
            if "key" in leg:
                return repr(leg.get("value"))
            if "resource_id" in leg:
                return repr(leg.get("resource_id"))
        return repr(raw)[:60]

    return (label, _value(new_leg, row.get("new_value")),
            _value(prev_leg, row.get("prev_value")))


async def _audit_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Recent-changes body (audit_view.py build_audit_embed):
    DM guard → soft-fail store read → empty state → the last-10 lines,
    shape verbatim over the audit_log column mapping (occurred_at→at,
    mutation rollup→prev/new raw, actor_id/actor_type verbatim)."""
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    if not guild_id:
        return (("Result", _AUDIT_DM),)

    try:
        from sb.kernel.db.pool import fetchall

        rows = await fetchall(
            "SELECT mutation_type, target, prev_value, new_value, "
            "actor_id, actor_type, occurred_at FROM audit_log "
            "WHERE subsystem = 'settings' AND guild_id = $1 "
            "ORDER BY occurred_at DESC LIMIT "
            f"{_AUDIT_RECENT_LIMIT}", (guild_id,))
    except Exception as exc:  # noqa: BLE001 — soft-fail; usually missing table
        return (("Audit table",
                 f"*Could not read `audit_log` — "
                 f"`{type(exc).__name__}: {exc!s:.100}`.  "
                 "Migration 0003 may not have been applied yet.*"),)

    if not rows:
        return (("Result", _AUDIT_EMPTY),)

    lines: list[str] = []
    for row in rows:
        ts = row.get("occurred_at")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%SZ") if ts is not None else "—"
        label, new, prev = _audit_change(row)
        actor = row.get("actor_id")
        actor_type = row.get("actor_type") or "user"
        lines.append(
            f"`{ts_str}` `{label}` = `{new}` (was `{prev}`) "
            f"by `{actor_type}` `{actor}`")
    return ((f"Last {len(lines)} change(s)", "\n".join(lines)[:1024]),)


def settings_audit_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.audit",
        subsystem="settings",
        title="🕒 Recent settings changes",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blurple().
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_AUDIT_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("settings.audit_fields"))),
        actions=(_diag_back_action("audit_back"),),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("settings.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_audit"),
        justification=(
            "the shipped Recent-changes footer is the DYNAMIC "
            "'settings_mutation_audit · guild_id=<id>' provenance stamp "
            "(views/settings/audit_view.py set_footer), rendered only on "
            "the rows path (DM/error/empty states return early) — "
            "guild-keyed copy outside FooterMode's none/subsystem/"
            "provenance vocabulary (the settings-hub footer-literal "
            "precedent). The override delegates to the grammar renderer "
            "and replaces ONLY the footer; body, fields, actions and "
            "layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("audit_back",),)),)),
    )


async def _render_audit(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped guild-keyed footer (see justification):
    present exactly when the rows field rendered — derived from the
    rendered field name, so the spine read runs ONCE (in the fields
    provider), never twice. The table name maps honestly onto the spine
    (`audit_log · subsystem=settings`)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    if not any(name.startswith("Last ")
               for name, *_ in rendered.embed.fields):
        return rendered
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    footer = f"audit_log · subsystem=settings · guild_id={guild_id}"
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=footer))


# --- the armed Command Access panel (settings-admin slice 3) -------------------------
#
# Oracle-verbatim port of the shipped 🚪 Command Access panel (PR-6 —
# disbot/views/settings/edit_command_access.py: the three mode buttons
# all_channels / selected_channels / disabled_except_bootstrap, the
# multi-ChannelSelect allowlist replace, Back-to-Hub; copy verbatim,
# double spaces included). Every mutation routed through the shipped
# ``services.command_access_service`` (cache invalidation + audit in the
# canonical path) — here that canonical path is the LIVE platform
# command-access K7 lanes (``platform.set_access_mode`` /
# ``set_access_channels``, sb/domain/platform/command_access.py — the
# setup-wizard step-8 seam): audited compound ops on the administrator
# authority floor with the post-commit cache forget; the handlers
# (sb/domain/settings/handlers.py) REUSE them, no new write lane. The
# oracle's atomic ``replace_allowed_channels`` composite maps onto
# ``set_access_channels`` (full DELETE + re-INSERT in ONE leg; implies
# selected_channels when no policy row — the same shape). Deliberate
# under-port: the oracle's ``delete_blocked_commands`` toggle + embed
# field have NO seam here — the policy store carries mode + channels
# only (guild_command_access_policy / _channels) — so both stay out
# until that store column ports (honest absence, never a dead control).
# The panel's controls are run-minted per-panel leaves (the shipped
# ``settings_command_access.*`` ids are NOT in the compat freeze; the
# slice-1 back-button precedent — one claimant per custom_id leaf
# repo-wide).

_CA_DESCRIPTION = (
    "Configure where prefix and slash commands are allowed in "
    "this server.  Applies to **both** invocation surfaces — "
    "the same channels permit `!bj` and `/blackjack` alike.\n\n"
    "Bootstrap commands (`/setup`, `/help`, `/settings`, "
    "`/platform`, `/diagnostics`) always remain reachable "
    "for guild operators so you cannot lock yourself out."
)

#: the shipped mode labels (edit_command_access.py _MODE_LABELS), verbatim.
_CA_MODE_LABELS: dict[str, str] = {
    "all_channels": "All channels",
    "selected_channels": "Selected channels",
    "disabled_except_bootstrap": "Disabled except bootstrap",
}

#: the shipped mode descriptions (_MODE_DESCRIPTIONS), verbatim.
_CA_MODE_DESCRIPTIONS: dict[str, str] = {
    "all_channels": (
        "Normal prefix + slash commands work in every guild channel "
        "(subject to per-command permissions and governance)."
    ),
    "selected_channels": (
        "Normal commands only work in the channels you list below. "
        "Bootstrap commands (`/setup`, `/help`, `/settings`, etc.) "
        "still work everywhere for guild operators."
    ),
    "disabled_except_bootstrap": (
        "Normal commands are denied. Only bootstrap commands "
        "remain reachable so an operator can re-enable from "
        "`!setup` or this panel."
    ),
}

#: the shipped DM/no-guild placeholder + recovery copy, verbatim.
_CA_NO_GUILD = "*Guild context not available.*"
_CA_RECOVERY = (
    "Normal commands are currently denied.  Pick **All "
    "channels** or **Selected channels** above to re-enable, "
    "or run `!setup` to revisit onboarding."
)

#: the shipped footer literal (edit_command_access.py set_footer) — kept
#: verbatim; renders via the override (outside FooterMode's vocabulary).
_CA_FOOTER = ("Applies to prefix + slash commands.  "
              "Mode buttons + the channel selector are admin-only.")


def _format_channel_list(channel_ids: frozenset[int]) -> str:
    """The shipped allowlist rendering (edit_command_access.py
    _format_channel_list, verbatim): mention list, 950-char truncation
    with a trailing count so the 1024-cap field never fails."""
    if not channel_ids:
        return "*(none configured)*"
    rendered = " ".join(f"<#{cid}>" for cid in sorted(channel_ids))
    if len(rendered) > 950:
        head = " ".join(f"<#{cid}>" for cid in sorted(channel_ids)[:30])
        return f"{head} … (+{len(channel_ids) - 30} more)"
    return rendered


async def _command_access_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Command-Access body (build_command_access_embed):
    no-guild placeholder → the live policy read (the K8 reader's cached
    ``read_policy_snapshot`` — the write lanes forget the cache post-
    commit, so a refresh reads fresh) → Current mode + Allowed channels
    (+ the Recovery field in the disabled mode), copy verbatim. The
    shipped Delete-blocked-commands field is the ledgered under-port
    (no store column here — the section comment)."""
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    if not guild_id:
        return (("Current mode", _CA_NO_GUILD),)

    from sb.domain.platform import command_access

    snapshot = await command_access.read_policy_snapshot(guild_id)
    mode_label = (
        _CA_MODE_LABELS.get(snapshot.mode, snapshot.mode)
        if snapshot.mode is not None
        else "All channels (default — no policy row)")
    mode_description = (
        _CA_MODE_DESCRIPTIONS.get(snapshot.mode, "—")
        if snapshot.mode is not None
        else _CA_MODE_DESCRIPTIONS["all_channels"])
    fields = [
        ("Current mode", f"**{mode_label}**\n{mode_description}"),
        (f"Allowed channels ({len(snapshot.allowed_channels)})",
         _format_channel_list(snapshot.allowed_channels)),
    ]
    if snapshot.mode == "disabled_except_bootstrap":
        fields.append(("Recovery", _CA_RECOVERY))
    return tuple(fields)


def settings_command_access_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.command_access",
        subsystem="settings",
        title="🚪 Command Access",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blurple().
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_CA_DESCRIPTION),
              FieldsBlock(
                  provider=ProviderRef("settings.command_access_fields"))),
        selectors=(
            # the shipped multi-ChannelSelect (min 0 / max 25 — a blank
            # selection CLEARS the allowlist, the atomic replace).
            SelectorSpec(
                selector_id="ca_channels", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("settings.ca_channels"),
                min_values=0, max_values=25,
                placeholder="Set allowed channels (selected_channels "
                            "mode)…",
                audience_tier="administrator"),
        ),
        actions=(
            # the shipped mode-button trio (row 0: label/emoji/style
            # verbatim; ids run-minted — the section comment).
            PanelActionSpec(
                action_id="ca_all_channels", label="All channels",
                emoji="🌐", style=ActionStyle.SUCCESS,
                audience_tier="administrator",
                handler=HandlerRef("settings.ca_mode")),
            PanelActionSpec(
                action_id="ca_selected_channels",
                label="Selected channels", emoji="📋",
                style=ActionStyle.PRIMARY,
                audience_tier="administrator",
                handler=HandlerRef("settings.ca_mode")),
            PanelActionSpec(
                action_id="ca_disabled",
                label="Disabled except bootstrap", emoji="🚫",
                style=ActionStyle.DANGER,
                audience_tier="administrator",
                handler=HandlerRef("settings.ca_mode")),
            _diag_back_action("command_access_back"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("settings.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_command_access"),
        justification=(
            "the shipped Command-Access footer is the literal 'Applies "
            "to prefix + slash commands.  Mode buttons + the channel "
            "selector are admin-only.' (views/settings/"
            "edit_command_access.py build_command_access_embed "
            "set_footer) — outside FooterMode's none/subsystem/"
            "provenance vocabulary (the settings-hub footer-literal "
            "precedent). The override delegates to the grammar renderer "
            "and replaces ONLY the footer; body, fields, selector, "
            "actions and layout stay declared."),
        # the shipped rows: mode buttons (row 0), the channel select
        # (row 1), Back to Hub (the delete-blocked toggle's row 2 is the
        # ledgered under-port — the section comment).
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ca_all_channels", "ca_selected_channels", "ca_disabled"),
            ("ca_channels",),
            ("command_access_back",),
        )),)),
    )


async def _render_command_access(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=_CA_FOOTER))


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


# --- the ported per-group scalar EDIT page (settings epic S0) ------------------------
#
# Oracle-verbatim port of the shipped SubsystemSettingsView frame
# (disbot/views/settings/subsystem_view.py @ menno420/superbot f87fa508 —
# build_subsystem_embed + the S6 edit/reset windowed selects + the
# Back-to-Hub / Open-Panel nav). Owner ruling option A
# (docs/question-router.md → Answered, 2026-07-18): this page replaces the
# honest `settings.group_pending` terminal for the NON-HUB groups only; the
# 5 operator-spine hub groups keep their read-only `<group>.hub` and the
# `games` panel arm is untouched (settings.open_group's first two arms).
#
# The selected group rides the session-minted component args (the engine's
# `_mint_ephemeral` bakes the opening request's args onto every minted
# child) — the running selection needs no parallel session dict: it flows
# through ctx.params on open, and the refresh handler re-supplies it from
# the click's args. S0 wires ONLY the bool toggle (S1) end to end; every
# other value type degrades to an honest "widget ports in a later slice"
# terminal rather than a dead control (S2–S7 add the per-type widgets).

#: the shipped subsystem-page field-value cap (subsystem_view.py
#: _FIELD_VALUE_CAP), applied before the grammar's own 1024 clamp.
_GROUP_EDIT_FIELD_CAP = 1000

#: the running-selection param key (threaded through ctx.params on open and
#: the session refresh — the group is never a raw KV read, only a nav axis).
GROUP_EDIT_PARAM = "group_edit_group"

#: the enum-widget's setting-name axis (settings epic S2): the enum picker
#: (settings.group_edit_enum) is opened from the group_edit Edit select with
#: BOTH the group (GROUP_EDIT_PARAM) and the picked setting name baked onto
#: its session-minted child args, so a value click carries its (group, name)
#: page context — the S0 minted-child convention, one axis further.
GROUP_EDIT_SETTING_PARAM = "group_edit_setting"


def _truncate_group(text: str, *, limit: int = _GROUP_EDIT_FIELD_CAP) -> str:
    """The oracle _truncate (subsystem_view.py) — the shipped 1000-char cap
    with the trailing ellipsis (the grammar's 1024 clamp then never fires)."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _group_manifest(group: str):
    """The SubsystemManifest for a settings group key (the ONE manifest
    inventory walk — the _iter_settings_facets seam), or None."""
    for key, manifest in _iter_settings_facets():
        if key == group:
            return manifest
    return None


def _group_editable_specs(group: str) -> tuple:
    """The group's editable SettingSpecs — the oracle _editable_specs subset
    (those carrying a persisted settings_key), in declaration order."""
    from sb.spec.settings import SettingSpec

    manifest = _group_manifest(group)
    if manifest is None:
        return ()
    return tuple(s for s in getattr(manifest, "settings", ()) or ()
                 if isinstance(s, SettingSpec) and s.settings_key)


def _group_edit_spec(group: str, name: str):
    """The editable SettingSpec for (group, name), or None — the handlers'
    dispatch lookup (the oracle dispatch_edit_setting spec resolution)."""
    for spec in _group_editable_specs(group):
        if spec.name == name:
            return spec
    return None


def _group_meta(group: str) -> dict:
    """(emoji, display, description, tier) — the oracle SUBSYSTEMS meta read,
    re-sourced onto the port's two registries: the shipped hub roster
    (_HUB_GROUPS) carries emoji/label/description; the governance registry
    carries the visibility tier (the _access_page2_options precedent)."""
    curated = {value: (label, emoji, description)
               for value, label, emoji, description in _HUB_GROUPS}
    label, emoji, description = curated.get(
        group, (group.replace("_", " ").title(), "⚙️", ""))
    from sb.domain.governance.registry import SUBSYSTEM_META

    tier = str((SUBSYSTEM_META.get(group) or {}).get("visibility_tier", "—"))
    return {"emoji": emoji or "⚙️", "display": label,
            "description": description, "tier": tier}


async def _group_scalar_lines(guild_id: int | None, group: str) -> list[str]:
    """The oracle _resolve_settings_block: one rendered line per declared
    SettingSpec resolved through the K7 typed read (per-guild effective
    value + provenance + validity + default); DM shows the declared default
    only (the shipped no-guild-context line)."""
    from sb.spec.settings import SettingSpec

    manifest = _group_manifest(group)
    if manifest is None:
        return []
    specs = [s for s in getattr(manifest, "settings", ()) or ()
             if isinstance(s, SettingSpec)]
    if not specs:
        return []
    lines: list[str] = []
    if guild_id is None:
        for spec in specs:
            lines.append(
                f"`{spec.name}` — type=`{spec.value_type}` "
                f"default=`{spec.default!r}` *(no guild context)*")
        return lines
    from sb.domain.settings import service as settings_service

    for spec in specs:
        try:
            resolution = await settings_service.resolve_setting(
                guild_id, group, spec.name, spec=spec)
        except Exception as exc:  # noqa: BLE001 — fail-soft per panel field
            lines.append(f"`{spec.name}` — ❌ resolver raised "
                         f"{type(exc).__name__}: {exc!s:.80}")
            continue
        if resolution is None:
            lines.append(f"`{spec.name}` — *(resolver returned None)*")
            continue
        validity = "valid" if resolution.valid else "**invalid**"
        lines.append(
            f"`{spec.name}` = `{resolution.value!r}` "
            f"(`{resolution.provenance}`, "
            f"default=`{resolution.default!r}`, {validity})")
    return lines


def _group_binding_lines(group: str) -> list[str]:
    """The oracle _bindings_block: declared BindingSpecs (kind + required +
    capability), read-only — the bind control is a later slice."""
    from sb.spec.settings import BindingSpec

    manifest = _group_manifest(group)
    if manifest is None:
        return []
    out: list[str] = []
    for spec in getattr(manifest, "settings", ()) or ():
        if not isinstance(spec, BindingSpec):
            continue
        required = "required" if spec.required else "optional"
        cap = (f"cap=`{spec.capability_required}`"
               if getattr(spec, "capability_required", "") else "")
        out.append(
            f"`{spec.name}` — kind=`{spec.kind.value}` ({required}) "
            f"{cap}".rstrip())
    return out


def _group_resource_lines(group: str) -> list[str]:
    """The oracle _resources_block: declared ResourceRequirements (kind +
    priority + suggested name + binding cross-link), read-only."""
    from sb.spec.settings import ResourceRequirement

    manifest = _group_manifest(group)
    if manifest is None:
        return []
    out: list[str] = []
    for req in getattr(manifest, "settings", ()) or ():
        if not isinstance(req, ResourceRequirement):
            continue
        suggested = (f" → `{req.provisioning.suggested_name}`"
                     if getattr(req.provisioning, "suggested_name", "")
                     else "")
        out.append(
            f"`{req.intent}` — kind=`{req.kind.value}` "
            f"priority=`{req.provisioning.priority.value}`{suggested} "
            f"(binding=`{req.binding_name}`)")
    return out


async def _group_edit_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The oracle build_subsystem_embed body: the Scalar-settings block
    (declared SettingSpecs resolved per guild), then the declared Bindings
    and Provisionable-resources blocks. The group rides ctx.params (open) /
    the session refresh params; an expired session degrades honestly."""
    params = dict(getattr(ctx, "params", {}) or {})
    group = str(params.get(GROUP_EDIT_PARAM) or "")
    if not group:
        return (("Scalar settings",
                 "*session expired — reopen the group from `!settings`*"),)
    guild_id = int(getattr(ctx, "guild_id", 0) or 0) or None
    fields: list[tuple[str, str]] = []
    setting_lines = await _group_scalar_lines(guild_id, group)
    fields.append(
        ("Scalar settings",
         _truncate_group("\n".join(setting_lines)) if setting_lines
         else "*none declared*"))
    binding_lines = _group_binding_lines(group)
    if binding_lines:
        fields.append(("Bindings",
                       _truncate_group("\n".join(binding_lines))))
    resource_lines = _group_resource_lines(group)
    if resource_lines:
        fields.append(("Provisionable resources",
                       _truncate_group("\n".join(resource_lines))))
    return tuple(fields)


async def _group_edit_edit_options(ctx) -> tuple[dict, ...]:
    """The oracle _attach_edit_select options: one rich option per editable
    SettingSpec (label = the name, description = its value type). The group
    rides ctx.params; the windowed engine pages a >25-spec group."""
    group = str(dict(getattr(ctx, "params", {}) or {}).get(
        GROUP_EDIT_PARAM) or "")
    return tuple(
        {"value": spec.name, "label": spec.name[:100],
         "description": f"type={spec.value_type}"[:100]}
        for spec in _group_editable_specs(group))


async def _group_edit_reset_options(ctx) -> tuple[dict, ...]:
    """The oracle _attach_reset_select options: one rich option per editable
    SettingSpec (label = "Reset <name>", description = its declared
    default)."""
    group = str(dict(getattr(ctx, "params", {}) or {}).get(
        GROUP_EDIT_PARAM) or "")
    return tuple(
        {"value": spec.name, "label": f"Reset {spec.name}"[:100],
         "description": f"default={spec.default!r}"[:100]}
        for spec in _group_editable_specs(group))


# --- the ported enum-select edit widget (settings epic S2) --------------------------
#
# The oracle dispatch_edit_setting routed a `str` setting that declares
# `allowed_values` to build_enum_select_view (disbot/views/settings/
# edit_enum.py @ f87fa508): a windowed select of the allowed members with the
# current value pre-marked, whose pick wrote through the audited mutation
# pipeline. Here that select is its own session-view panel
# (settings.group_edit_enum), opened from the group_edit Edit select when the
# picked spec is enum-shaped; the group AND the picked setting name ride the
# session-minted child args (GROUP_EDIT_PARAM / GROUP_EDIT_SETTING_PARAM), so
# a value click carries its (group, name) context with no parallel session
# dict. The chosen member commits through the LIVE K7 settings.set_scalar lane
# (no new op) and the picker refreshes in place showing the new current.


def _is_enum_spec(spec) -> bool:
    """The oracle enum-dispatch predicate (dispatch_edit_setting): a `str`
    scalar that declares a non-empty `allowed_values` set renders a select."""
    return (spec is not None and str(spec.value_type) == "str"
            and bool(getattr(spec, "allowed_values", ())))


async def _group_edit_current(guild_id: int | None, group: str, name: str,
                              spec) -> object:
    """The setting's current effective value (the oracle dispatch_edit_setting
    `current = resolution.value` read): the per-guild resolved value through
    the K7 typed read seam, or the declared default in DM / on a resolver
    miss."""
    current = getattr(spec, "default", None)
    if guild_id is None:
        return current
    try:
        from sb.domain.settings import service as settings_service

        resolution = await settings_service.resolve_setting(
            guild_id, group, name, spec=spec)
    except Exception:  # noqa: BLE001 — fail-soft to the declared default
        return current
    if resolution is not None:
        return resolution.value
    return current


async def _group_edit_enum_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The enum picker's read block — names the setting under edit and its
    current effective value (the oracle ephemeral prompt copy: 'Pick a new
    value for `{subsystem}.{name}`'). An expired session degrades honestly."""
    params = dict(getattr(ctx, "params", {}) or {})
    group = str(params.get(GROUP_EDIT_PARAM) or "")
    name = str(params.get(GROUP_EDIT_SETTING_PARAM) or "")
    spec = _group_edit_spec(group, name)
    if not group or not name or spec is None:
        return (("Edit a setting",
                 "*session expired — reopen the group from `!settings`*"),)
    guild_id = int(getattr(ctx, "guild_id", 0) or 0) or None
    current = await _group_edit_current(guild_id, group, name, spec)
    return ((f"Editing `{group}.{name}`",
             f"current = `{current!r}`  ·  default = `{spec.default!r}`\n"
             f"Pick a new value from the select below."),)


async def _group_edit_enum_options(ctx) -> tuple[dict, ...]:
    """The oracle build_enum_select_view options: one option per declared
    allowed value, the current value pre-marked (`default=True`, description
    'current'). The group + setting ride ctx.params; the windowed engine pages
    an >25-member enum instead of front-truncating (the #1040 class)."""
    params = dict(getattr(ctx, "params", {}) or {})
    group = str(params.get(GROUP_EDIT_PARAM) or "")
    name = str(params.get(GROUP_EDIT_SETTING_PARAM) or "")
    spec = _group_edit_spec(group, name)
    if not _is_enum_spec(spec):
        return ()
    guild_id = int(getattr(ctx, "guild_id", 0) or 0) or None
    current = await _group_edit_current(guild_id, group, name, spec)
    options: list[dict] = []
    for value in spec.allowed_values:
        label = str(value)[:100]
        is_current = str(value) == str(current)
        option: dict = {"value": label, "label": label}
        if is_current:
            option["default"] = True
            option["description"] = "current"
        options.append(option)
    return tuple(options)


def settings_group_edit_enum_spec() -> PanelSpec:
    """The enum-select edit widget (settings epic S2) — a windowed select of a
    setting's declared `allowed_values`, opened from the group_edit Edit select
    for an enum-shaped scalar. A pick commits through settings.set_scalar; the
    Back button re-opens the group's edit page (the group rides its args)."""
    return PanelSpec(
        panel_id="settings.group_edit_enum",
        subsystem="settings",
        title="⚙️ Edit a setting",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blurple() (subsystem_view.py).
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(FieldsBlock(
            provider=ProviderRef("settings.group_edit_enum_fields")),),
        selectors=(
            # the shipped windowed enum select (edit_enum.py
            # build_enum_select_view over PaginatedSelectView): options are
            # the declared allowed_values (provider-fed, current pre-marked),
            # windowed past 25 (the #1040 class). A pick commits through
            # settings.set_scalar (settings.group_edit_enum_pick).
            SelectorSpec(
                selector_id="enum_select", kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "settings.group_edit_enum_options"),
                placeholder="Pick a new value…",
                empty_state="No choices declared for this setting…",
                audience_tier="administrator", windowed=True,
                on_select=HandlerRef("settings.group_edit_enum_pick")),
        ),
        actions=(
            # ↩ Back to the group's edit page — a handler re-open (the group
            # rides the click's args), never a strand.
            PanelActionSpec(
                action_id="enum_back", label="Back to settings", emoji="↩",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.group_edit_enum_back")),
        ),
        # the session-view exemption takes the never-strand fence (the
        # group_edit precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("enum_select",),
            ("enum_back",),
        )),)),
    )


# --- the ported number-modal edit widget (settings epic S3) -------------------------
#
# The oracle dispatch_edit_setting routed an `int` / `float` setting to the
# NumberSettingModal (disbot/views/settings/edit_number.py @ f87fa508): a
# one-input modal whose submit coerced + validated the typed value and wrote
# through the audited mutation pipeline. Here that modal is a G-10 declared
# ModalSpec on its OWN session-view child panel (settings.group_edit_number),
# opened from the group_edit Edit select when the picked spec is number-shaped.
# A selector pick is AUTO-deferred on this engine, so a button INTERMEDIATES and
# issues the modal (the D-0054 confirm-surface posture; the ai edit_text /
# edit_presets Override… precedent) — the submit re-enters through the frozen
# MODAL adapter with the (group, setting) restored from the kernel modal-args
# stash (the opening click's session-minted args: GROUP_EDIT_PARAM /
# GROUP_EDIT_SETTING_PARAM). The typed value coerces + range-validates against
# the SettingSpec through the SAME coerce_value seam the read path uses (bounds
# + type), then commits through the LIVE K7 settings.set_scalar lane (no new
# op); an invalid / out-of-range entry rejects without a write.

#: the shipped NumberSettingModal (edit_number.py) as the G-10 declared form.
#: The shipped title/label/placeholder embedded the picked setting's name and
#: live current/default reprs; ModalSpec fields are static [S] wire data (the
#: corpus cannot pin the transient form), so the per-open current/default/range
#: readout rides the widget page's prompt instead — the ai `_NUMBER_MODAL` /
#: starboard `THRESHOLD_MODAL` deviation precedent (D-0063/D-0085). int and
#: float both ride this one free-form numeric form.
_NUMBER_MODAL = ModalSpec(
    modal_id="settings.group_edit_number_form",
    title="Edit a setting",
    fields=(ModalFieldSpec(
        field_id="number_value",
        label="New value (a number)",        # shipped: "New value (type: <t>)"
        placeholder="e.g. 3",
        required=True, max_length=64),))


def _is_number_spec(spec) -> bool:
    """The oracle number-dispatch predicate (dispatch_edit_setting): an `int`
    or `float` scalar pops the free-form numeric modal."""
    return spec is not None and str(spec.value_type) in ("int", "float")


async def _group_edit_number_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The number widget's read block — names the setting under edit, its
    current effective value + declared default + type, and any declared numeric
    bounds (the oracle NumberSettingModal placeholder 'current=… · default=…'
    carried onto the page since the modal copy is static). An expired session
    degrades honestly."""
    params = dict(getattr(ctx, "params", {}) or {})
    group = str(params.get(GROUP_EDIT_PARAM) or "")
    name = str(params.get(GROUP_EDIT_SETTING_PARAM) or "")
    spec = _group_edit_spec(group, name)
    if not group or not name or spec is None:
        return (("Edit a setting",
                 "*session expired — reopen the group from `!settings`*"),)
    guild_id = int(getattr(ctx, "guild_id", 0) or 0) or None
    current = await _group_edit_current(guild_id, group, name, spec)
    bounds = getattr(spec, "bounds", None)
    range_line = (f"\nAllowed range: `{bounds[0]}` – `{bounds[1]}`."
                  if bounds and len(bounds) == 2 else "")
    return ((f"Editing `{group}.{name}`",
             f"current = `{current!r}`  ·  default = `{spec.default!r}`  ·  "
             f"type = `{spec.value_type}`{range_line}\n"
             f"Tap **Enter a number…** below to set a new value."),)


def settings_group_edit_number_spec() -> PanelSpec:
    """The number-modal edit widget (settings epic S3) — a session-view child
    whose single button ISSUES a numeric-input modal (the ported
    NumberSettingModal), opened from the group_edit Edit select for an int /
    float scalar. The submit coerces + range-validates then commits through
    settings.set_scalar; the Back button re-opens the group's edit page."""
    return PanelSpec(
        panel_id="settings.group_edit_number",
        subsystem="settings",
        title="⚙️ Edit a setting",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blurple() (subsystem_view.py).
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(FieldsBlock(
            provider=ProviderRef("settings.group_edit_number_fields")),),
        actions=(
            # G-10: the click ISSUES the number form; the submit re-enters
            # through the MODAL adapter and writes on the audited K7
            # settings.set_scalar lane (the ai edit_presets Override… /
            # starboard threshold precedent). The (group, setting) ride the
            # kernel modal-args stash restored at submit.
            PanelActionSpec(
                action_id="number_edit", label="Enter a number…",
                emoji="🔢", style=ActionStyle.PRIMARY,
                audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=_NUMBER_MODAL,
                # the shipped safe_defer(..., ephemeral=True) flag on the
                # submit re-entry (the ai/starboard forms all followed up
                # ephemeral).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("settings.group_edit_number_submit")),
            # ↩ Back to the group's edit page — a handler re-open (the group
            # rides the click's args), never a strand (the enum_back twin).
            PanelActionSpec(
                action_id="number_back", label="Back to settings", emoji="↩",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("settings.group_edit_number_back")),
        ),
        # the session-view exemption takes the never-strand fence (the
        # group_edit / enum precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("number_edit",),
            ("number_back",),
        )),)),
    )


def settings_group_edit_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.group_edit",
        subsystem="settings",
        # the per-group title (`{emoji} {display}`) is stamped by the
        # renderer override; this static title is the pre-group placeholder.
        title="⚙️ Settings",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.blurple().
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(FieldsBlock(provider=ProviderRef("settings.group_edit_fields")),),
        selectors=(
            # the shipped windowed "Edit a setting…" picker (#1040 class):
            # picking a setting dispatches by its value type
            # (settings.group_edit_pick). Options are provider-fed (the
            # editable-spec set is per-group), windowed past 25.
            SelectorSpec(
                selector_id="edit_select", kind=SelectorKind.ENUM,
                options_source=ProviderRef("settings.group_edit_edit_options"),
                placeholder="Edit a setting…",
                empty_state="No editable settings in this group…",
                audience_tier="administrator", windowed=True,
                on_select=HandlerRef("settings.group_edit_pick")),
            # the shipped windowed "Reset a setting…" picker.
            SelectorSpec(
                selector_id="reset_select", kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "settings.group_edit_reset_options"),
                placeholder="Reset a setting to its default…",
                empty_state="No settings to reset in this group…",
                audience_tier="administrator", windowed=True,
                on_select=HandlerRef("settings.group_edit_reset")),
        ),
        actions=(
            # the shipped Open-Panel button (subsystem_view.py
            # _OpenRelatedPanelButton) — the oracle's no-panel fallback
            # here (non-hub groups have no dedicated operator panel; the
            # dedicated route lands with the group's own panel slice).
            PanelActionSpec(
                action_id="group_open_panel", label="Open Panel",
                emoji="🪟", style=ActionStyle.PRIMARY,
                audience_tier="administrator",
                handler=HandlerRef("settings.group_open_panel")),
            # the shipped ↩ Back to Hub button — a PanelRef open-child
            # terminal back to the hub (the diagnostics' back precedent).
            PanelActionSpec(
                action_id="group_back", label="Back to Hub", emoji="↩",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("settings.hub")),
        ),
        # the shipped page carried no standard nav row; the session-view
        # exemption takes the never-strand fence (the hub precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("settings.render_group_edit"),
        justification=(
            "the shipped SubsystemSettingsView header is per-group DYNAMIC "
            "copy (subsystem_view.py build_subsystem_embed): the "
            "'{emoji} {display}' title, the '_desc_ · visibility tier · "
            "subsystem key' description, and the 'Scalar edit + reset "
            "live · use the selects below.  guild_id={id}' footer are all "
            "keyed on the selected group — outside the grammar's static "
            "title / FooterMode vocabulary (the settings-hub footer-literal "
            "precedent). The override delegates to the grammar renderer and "
            "stamps ONLY those three header surfaces; the scalar/binding/"
            "resource fields, selectors, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("edit_select",),
            ("reset_select",),
            ("group_open_panel", "group_back"),
        )),)),
    )


async def _render_group_edit(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped per-group header (see justification):
    the title, tier/key description, and guild-keyed footer, keyed on the
    selected group in ctx.params. With no group in params (a stranded
    render) the grammar bytes stand unchanged."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    group = str(dict(getattr(ctx, "params", {}) or {}).get(
        GROUP_EDIT_PARAM) or "")
    if not group:
        return rendered
    meta = _group_meta(group)
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    title = f"{meta['emoji']} {meta['display']}"
    description = (f"_{meta['description']}_\n"
                  f"visibility tier: `{meta['tier']}`  ·  "
                  f"subsystem key: `{group}`")
    footer = ("Scalar edit + reset live · use the selects below.  "
              f"guild_id={guild_id if guild_id else 'DM'}")
    return _dc_replace(rendered, embed=_dc_replace(
        rendered.embed, title=title, description=description, footer=footer))


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
    if not is_registered(PanelRef("settings.audit")):
        panel("settings.audit")(settings_audit_spec)
    if not is_registered(PanelRef("settings.command_access")):
        panel("settings.command_access")(settings_command_access_spec)
    if not is_registered(PanelRef("settings.group_edit")):
        panel("settings.group_edit")(settings_group_edit_spec)
    if not is_registered(PanelRef("settings.group_edit_enum")):
        panel("settings.group_edit_enum")(settings_group_edit_enum_spec)
    if not is_registered(PanelRef("settings.group_edit_number")):
        panel("settings.group_edit_number")(settings_group_edit_number_spec)
    if not is_registered(HandlerRef("settings.render_hub")):
        handler("settings.render_hub")(_render_hub)
    if not is_registered(HandlerRef("settings.render_access")):
        handler("settings.render_access")(_render_access)
    if not is_registered(HandlerRef("settings.render_needs_setup")):
        handler("settings.render_needs_setup")(_render_needs_setup)
    if not is_registered(HandlerRef("settings.render_invalid")):
        handler("settings.render_invalid")(_render_invalid)
    if not is_registered(HandlerRef("settings.render_audit")):
        handler("settings.render_audit")(_render_audit)
    if not is_registered(HandlerRef("settings.render_command_access")):
        handler("settings.render_command_access")(_render_command_access)
    if not is_registered(HandlerRef("settings.render_group_edit")):
        handler("settings.render_group_edit")(_render_group_edit)
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
    if not is_registered(ProviderRef("settings.audit_fields")):
        provider("settings.audit_fields")(_audit_fields)
    if not is_registered(ProviderRef("settings.command_access_fields")):
        provider("settings.command_access_fields")(_command_access_fields)
    if not is_registered(ProviderRef("settings.group_edit_fields")):
        provider("settings.group_edit_fields")(_group_edit_fields)
    if not is_registered(ProviderRef("settings.group_edit_edit_options")):
        provider("settings.group_edit_edit_options")(_group_edit_edit_options)
    if not is_registered(ProviderRef("settings.group_edit_reset_options")):
        provider("settings.group_edit_reset_options")(_group_edit_reset_options)
    if not is_registered(ProviderRef("settings.group_edit_enum_fields")):
        provider("settings.group_edit_enum_fields")(_group_edit_enum_fields)
    if not is_registered(ProviderRef("settings.group_edit_enum_options")):
        provider("settings.group_edit_enum_options")(_group_edit_enum_options)
    if not is_registered(ProviderRef("settings.group_edit_number_fields")):
        provider("settings.group_edit_number_fields")(_group_edit_number_fields)


_register_refs()


def install_settings_panels() -> PanelSpec:
    """Register the hub + explorer + the four armed diagnostics + the
    Command Access write panel with the panels registry (fences run
    here); composition-root/boot call. Idempotent for identical specs.
    Returns the hub spec (the band-1 contract shape)."""
    hub = settings_hub_spec()
    for spec in (hub, settings_access_spec(), settings_needs_setup_spec(),
                 settings_invalid_spec(), settings_missing_bindings_spec(),
                 settings_audit_spec(), settings_command_access_spec(),
                 settings_group_edit_spec(), settings_group_edit_enum_spec(),
                 settings_group_edit_number_spec()):
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
    return hub


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()
