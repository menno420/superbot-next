"""The CLEANUP panels (parity flip) — the shipped Cleanup Hub
(disbot/cogs/cleanup/panel.py ``CleanupPanelView`` + its embed builder)
and the shipped Prohibited Words Manager (disbot/cogs/cleanup_cog.py's
word-menu view, ``!wordmenu``), byte-for-byte as the goldens pin them
(parity/goldens/cleanup/: sweep_cleanup, sweep_wordmenu).

The hub: the 🧹 red read-only router — the shipped two-sentence blurb,
the live ``Prohibited Words`` count field (``{n} configured`` /
``_None configured_`` — the shipped panel.py copy, inline=True) + the
``Auto-Delete`` policy blurb, the "Read-only summary." footer — over the
shipped rows: 🔤 Prohibited Words / 📝 Logging Status / ⚙️ Settings /
🧹 Cleanup Policies, the 🔄 Refresh row, and the shipped STANDARD nav
row (``nav:help`` + ``nav:hub:moderation`` "↩ Moderation"). Every
declared component carries its shipped PERSISTENT ``cleanup:*``
custom_id verbatim (``custom_id_override``; the settings-hub/
server-management precedent). ``session_lifecycle=True`` with every
declared id override-pinned: nothing is run-minted and no
``panel_anchors`` row is recorded (the golden's db_delta carries none).

The words manager: the 🔤 red session view — no description, the two
fields (``Current Words`` / ``🛡️ Anti-evasion matching``), the "Use
buttons below" footer — over the shipped button rows (➕ Add Word /
➖ Remove Word / 🔄 Refresh, then 🔍 Scan History / 🛡️ Anti-evasion).
The shipped view minted discord.py auto-ids (the golden pins
``<cid:1>``..``<cid:5>``) — no overrides, so ``_mint_ephemeral`` mints
run ids in declared order; the shipped view carried NO nav row, so the
never-strand fence takes the session-view exemption.

The 2026-07-13 residue port (the word-mutation + settings-mutation
leftovers, claim `completeness-remainders` item 2):
* the words manager's ``Current Words`` / ``🛡️ Anti-evasion matching``
  fields render LIVE (the shipped ``_word_cache`` read via
  ``service.get_words_cached`` + the migration-0053 strict flag; the
  shipped empty state — "No prohibited words are currently set." as the
  DESCRIPTION with no words field — rides the renderer override). The
  golden still pins ``Current Words: `test``` because the capture's
  alphabetical sweep leaked the ``!word add test`` cache write into
  ``!wordmenu``'s render — the parity runner reseeds that trajectory
  per observing case (runner.CAPTURE_WORLD_WORD_CACHE, the
  sweep.word_list precedent);
* 🛡️ Anti-evasion toggles for real: the click runs the audited
  ``cleanup.wordfilter_strict_op`` (the shipped
  ``set_wordfilter_strict`` service posture) and re-renders the panel
  in place (sb/domain/cleanup/handlers.py);
* the hub's ⚙️ Settings opens the PORTED ``cleanup.settings`` page (the
  shipped SubsystemSettingsView for `cleanup` — the ai.settings
  precedent), whose edit/reset selects drive the numeric-presets widget
  page + Override… G-10 form over the audited ``settings.set_scalar``
  lane (sb/domain/cleanup/settings_widgets.py);
* ONE remaining pending click: the hub's 🧹 Cleanup Policies sub-view
  (diagnostics + presets builder + remove flow,
  views/cleanup/policy_panel.py) stays the declared + honest terminal —
  its own slice (multi-view chained-select builder over the governance
  cleanup_policies lanes). Everything else routes for real:
  🔤 Prohibited Words opens the ported words manager, 📝 Logging Status
  opens the ported ``logging.hub`` (the server-logging slice landed),
  ➕/➖ open G-10 word modals whose submits run the audited
  ``cleanup.word_add_op``/``word_remove_op`` command twins (the
  moderation.hub.warn modal-ingress precedent), 🔄 refresh re-renders
  each panel in place, and 🔍 Scan History runs the live
  ``cleanup.history_scan`` handler (``!cleanuphistory``'s route).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import ReplyVisibility
from sb.spec.panels import (
    ActionStyle,
    Audience,
    DeferMode,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    NavRouteSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    SelectorKind,
    SelectorSpec,
)
from sb.spec.panels import TextBlock
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    WorkflowRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "cleanup_hub_spec",
    "cleanup_settings_edit_presets_spec",
    "cleanup_settings_spec",
    "cleanup_words_spec",
    "ensure_panel_refs",
    "install_cleanup_panels",
]

# --- the shipped hub copy (cogs/cleanup/panel.py — the golden pins every
# byte). -----------------------------------------------------------------------

_HUB_DESCRIPTION = (
    "Auto-moderation policies for command-style messages and prohibited "
    "content. Per-channel behaviour is configured under **Cleanup Policies** "
    "below."
)

#: the shipped footer literal (panel.py set_footer) — outside FooterMode's
#: vocabulary, hence the renderer_override below (the settings/
#: server_management precedent).
_HUB_FOOTER = "Read-only summary. Use the buttons below to manage policies."

#: the shipped Auto-Delete policy blurb (panel.py add_field, verbatim).
_HUB_AUTODELETE = (
    "Invalid/failed command-style messages are removed per the channel's "
    "cleanup policy (set a channel to **Off** to exempt it). Prohibited-word "
    "matches are removed with a brief warning."
)

# --- the shipped words-manager copy (cleanup_cog.py word-menu view). -----------

_WORDS_FOOTER = "Use buttons below to manage prohibited words."

#: the shipped empty state (cleanup_cog.py build_embed: no words → the
#: DESCRIPTION carries this byte and the Current Words field is absent).
_WORDS_EMPTY = "No prohibited words are currently set."

#: the shipped anti-evasion field literals (build_embed, verbatim).
_WORDS_ANTI_EVASION_ON = ("🟢 **On** — also catches leet, unicode "
                          "look-alikes, invisible characters, and "
                          "spaced-out letters")
_WORDS_ANTI_EVASION_OFF = "⚫ **Off** — exact word match only"


# --- the word-mutation prompt modals (the moderation.hub.warn G-10 ingress
# precedent: button → declared ModalSpec → the audited K7 command twin).
# The shipped view's per-button modals prompted for one word; field_id
# "word" feeds ops._word_from (ctx.params["word"]) directly, exactly like
# `!word add <word>` / `!word remove <word>` (goldens sweep_word_add /
# sweep_word_remove pin the reply copy the twins answer with).

_WORD_FIELD = ModalFieldSpec(
    field_id="word", label="Word or phrase",
    placeholder="e.g. badword", required=True, max_length=100)

WORD_ADD_MODAL = ModalSpec(
    modal_id="cleanup.word_add_form", title="Add Prohibited Word",
    fields=(_WORD_FIELD,),
    on_submit=WorkflowRef("cleanup.word_add_op"))
WORD_REMOVE_MODAL = ModalSpec(
    modal_id="cleanup.word_remove_form", title="Remove Prohibited Word",
    fields=(_WORD_FIELD,),
    on_submit=WorkflowRef("cleanup.word_remove_op"))


# --- field providers ---------------------------------------------------------------

async def _hub_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped hub fields: the LIVE prohibited-word count (panel.py:
    ``f"{word_count} configured" if word_count else "_None configured_"``)
    + the Auto-Delete literal. The renderer override marks the count field
    inline — the shipped ``add_field(inline=True)`` wire shape."""
    from sb.domain.cleanup import store

    try:
        words = await store.get_words(int(getattr(ctx, "guild_id", 0) or 0))
    except Exception:  # noqa: BLE001 — a headless/db-free read renders empty
        words = []
    count = len(words)
    value = f"{count} configured" if count else "_None configured_"
    return (("Prohibited Words", value),
            ("Auto-Delete", _HUB_AUTODELETE))


async def _words_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped words-manager fields, LIVE (cleanup_cog.py
    build_embed): the per-guild word-cache read (sorted backticks,
    1000-cap — ``service.get_words_cached``, the shipped ``_word_cache``
    shape; the parity runner reseeds the capture trajectory so the
    golden's leaked `test` still renders) + the migration-0053 strict
    flag. No words → NO Current Words field; the renderer override
    stamps the shipped empty-state description instead."""
    from sb.domain.cleanup import service, store

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    try:
        words = await service.get_words_cached(guild_id)
    except Exception:  # noqa: BLE001 — a headless/db-free read renders empty
        words = []
    try:
        strict = await store.get_wordfilter_strict(guild_id)
    except Exception:  # noqa: BLE001 — no row/no DB = the shipped default off
        strict = False
    anti = _WORDS_ANTI_EVASION_ON if strict else _WORDS_ANTI_EVASION_OFF
    if not words:
        return (("🛡️ Anti-evasion matching", anti),)
    current = ", ".join(f"`{w}`" for w in sorted(words))[:1000]
    return (("Current Words", current),
            ("🛡️ Anti-evasion matching", anti))


# --- the hub spec -------------------------------------------------------------------

def cleanup_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.hub",
        subsystem="cleanup",
        title="🧹 Cleanup Hub",
        audience=Audience.INVOKER,
        # the shipped hub accent — discord.Color.red() (ERROR_COLOR token).
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_HUB_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("cleanup.hub_fields"))),
        actions=(
            # row 0 — the shipped router quartet (emoji IN the labels;
            # blurple word/policy doors, grey read-only views).
            PanelActionSpec(
                action_id="words", label="🔤 Prohibited Words",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                # the shipped hub opened the words manager — the PORTED
                # cleanup.words panel below.
                handler=PanelRef("cleanup.words"),
                custom_id_override="cleanup:words"),
            PanelActionSpec(
                action_id="logging", label="📝 Logging Status",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                # the shipped hub opened the Logging Status view — its
                # successor slice (server-logging) landed, so the click
                # routes to the PORTED logging.hub (the admin.hub
                # `admin_logging` nav precedent).
                handler=PanelRef("logging.hub"),
                custom_id_override="cleanup:logging"),
            PanelActionSpec(
                action_id="settings", label="⚙️ Settings",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                # the shipped hub opened SubsystemSettingsView("cleanup")
                # — the PORTED cleanup.settings page below (the
                # ai.settings precedent).
                handler=PanelRef("cleanup.settings"),
                custom_id_override="cleanup:settings"),
            PanelActionSpec(
                action_id="policies", label="🧹 Cleanup Policies",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_pending"),
                custom_id_override="cleanup:policies"),
            # row 1 — the shipped grey in-place refresh (K1 custom_id
            # claims are repo-global on action_id — treasury owns bare
            # "refresh" (the sm_refresh/general_overview precedent); the
            # shipped wire id survives via the override).
            PanelActionSpec(
                action_id="cl_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("cleanup.hub"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="cleanup:refresh"),
        ),
        # the shipped hub carried the STANDARD nav row — 📚 Help +
        # ↩ Moderation (the shipped parent hub is `moderation`, pinned
        # explicitly until the moderation hub's own band installs a
        # resolver — the settings-explorer `admin` precedent).
        navigation=NavigationSpec(home_hub="moderation"),
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Read-only summary. Use "
            "the buttons below to manage policies.' (cogs/cleanup/panel.py "
            "set_footer) — outside FooterMode's none/subsystem/provenance "
            "vocabulary — and the shipped Prohibited Words count field "
            "renders inline=True (panel.py add_field(inline=True)) — "
            "outside the grammar's vocabulary (2-tuple fields render "
            "inline=False). goldens/cleanup/sweep_cleanup.json pins both "
            "bytes (the settings-hub/access precedent). The override "
            "delegates to the grammar renderer and adjusts ONLY those two "
            "surfaces; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("words", "logging", "settings", "policies"),
            ("cl_refresh",),
        )),)),
    )


# --- the words-manager spec -----------------------------------------------------------

def cleanup_words_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.words",
        subsystem="cleanup",
        title="🔤 Prohibited Words Manager",
        audience=Audience.INVOKER,
        # the shipped accent — ADMIN_COLOR == discord.Color.red().
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        # no description (the golden's embed carries no description key) —
        # the body is the two fields only.
        body=(FieldsBlock(provider=ProviderRef("cleanup.words_fields")),),
        actions=(
            # row 0 — the shipped word-mutation trio (run-minted auto-ids;
            # the golden pins <cid:1>..<cid:3>; emoji IN the labels).
            # ➕/➖ open the G-10 word modals whose submits run the audited
            # command twins (the moderation.hub.warn ingress precedent).
            PanelActionSpec(
                action_id="word_add", label="➕ Add Word",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=WORD_ADD_MODAL,
                handler=WorkflowRef("cleanup.word_add_op")),
            PanelActionSpec(
                action_id="word_remove", label="➖ Remove Word",
                style=ActionStyle.DANGER, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=WORD_REMOVE_MODAL,
                handler=WorkflowRef("cleanup.word_remove_op")),
            # the shipped grey in-place refresh (the hub's cl_refresh
            # pattern; the golden-pinned field literals re-render — the
            # live Current Words read stays the word-mutation slice's).
            PanelActionSpec(
                action_id="word_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("cleanup.words"),
                result_render=ResultRender.REFRESH_PANEL),
            # row 1 — the shipped scan/anti-evasion pair (<cid:4>/<cid:5>).
            # 🔍 runs the live history scan (`!cleanuphistory`'s handler —
            # the shipped button ran the same sweep, default args).
            PanelActionSpec(
                action_id="scan_history", label="🔍 Scan History",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.history_scan")),
            # 🛡️ toggles the migration-0053 strict flag on the audited
            # cleanup.wordfilter_strict_op and re-renders in place (the
            # shipped btn_strict flow — sb/domain/cleanup/handlers.py).
            PanelActionSpec(
                action_id="anti_evasion", label="🛡️ Anti-evasion",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.anti_evasion_toggle")),
        ),
        # the shipped word-menu view carried ONLY its own buttons (no nav
        # row; timeout session view) — the golden pins exactly two
        # component rows; the never-strand fence takes the session-view
        # exemption (the general-menu precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_words"),
        justification=(
            "the shipped words-manager footer is the literal 'Use buttons "
            "below to manage prohibited words.' (cleanup_cog.py set_footer) "
            "— outside FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/cleanup/sweep_wordmenu.json pins the byte; the "
            "settings/server_management footer precedent). The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "footer; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("word_add", "word_remove", "word_refresh"),
            ("scan_history", "anti_evasion"),
        )),)),
    )


# --- the settings page (the shipped SubsystemSettingsView for `cleanup` —
# views/settings/subsystem_view.py build_subsystem_embed + the S6 selects;
# the ai.settings precedent, sb/domain/ai/panels.py). Buttons/selects are
# run-minted session ids — the shipped persistent `settings_subsystem.*`
# roots are ai.settings' repo-global claim (K1), and these click routes
# are golden-unpinned (the #151 ledgered class).

#: the shipped page description (subsystem_registry cleanup meta + the
#: tier/key line — build_subsystem_embed verbatim, double spaces included).
_SETTINGS_DESCRIPTION = (
    "_Prohibited words, command deletion, channel hygiene_\n"
    "visibility tier: `administrator`  ·  subsystem key: `cleanup`"
)

#: the shipped Domain-configuration discovery field (cogs/cleanup/
#: schemas.py DomainPanelSpec, rendered `**{name}** — {description}`).
_SETTINGS_DOMAIN_PANELS = (
    "**Cleanup policies** — Prohibited words and message-cleanup behavior "
    "— configured in the dedicated cleanup panel (governance-audited); "
    "the Settings group routes there."
)

#: the shipped entry_points listing (subsystem_registry cleanup meta).
_SETTINGS_RELATED = "`!cleanup`, `!wordmenu`, `!cleanuphistory`"


def _settings_option_rosters() -> tuple[tuple, tuple]:
    """The shipped S6 select rosters: one Edit + one Reset option per
    declared SettingSpec (label = the shipped spec.name byte)."""
    from sb.domain.cleanup.settings_schema import SHIPPED_CLEANUP_SETTINGS

    edit, reset = [], []
    for spec in SHIPPED_CLEANUP_SETTINGS:
        name = spec.name
        edit.append({"label": name[:100], "value": name,
                     "description": f"type={spec.value_type}"[:100]})
        reset.append({"label": f"Reset {name}"[:100], "value": name,
                      "description": f"default={spec.default!r}"[:100]})
    return tuple(edit), tuple(reset)


async def _settings_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped page fields for the cleanup schema: Scalar settings
    (per-name current value + provenance + declared default + validity
    over THE K7 resolve seam), Domain configuration, Existing command
    panels. Cleanup declares no bindings/resources — the shipped page
    adds those fields only when present."""
    from sb.domain.cleanup.settings_schema import SHIPPED_CLEANUP_SETTINGS
    from sb.kernel import settings as ksettings

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    lines = []
    for spec in SHIPPED_CLEANUP_SETTINGS:
        try:
            value = await ksettings.resolve(guild_id, "cleanup", spec.name)
            explicit = await ksettings.is_explicitly_set(guild_id, "cleanup",
                                                         spec.name)
        except LookupError:
            lines.append(f"`{spec.name}` — *(resolver returned None)*")
            continue
        prov = "guild" if explicit else "default"
        if explicit:
            # an explicit row arrives as the RAW KV string — the shipped
            # page rendered the COERCED typed value + the coercion-driven
            # validity flag (settings_resolution.resolve_setting).
            from sb.domain.settings.service import coerce_value

            value, ok, _diag = coerce_value(spec, str(value))
            valid = "valid" if ok else "**invalid**"
        else:
            valid = "valid"
        lines.append(f"`{spec.name}` = `{value!r}` "
                     f"(`{prov}`, default=`{spec.default!r}`, {valid})")
    return (("Scalar settings", "\n".join(lines)),
            ("Domain configuration", _SETTINGS_DOMAIN_PANELS),
            ("Existing command panels", _SETTINGS_RELATED))


_EDIT_OPTIONS, _RESET_OPTIONS = _settings_option_rosters()

#: the shipped NumberSettingModal (views/settings/edit_number.py) as the
#: G-10 declared form — the presets page's "Override…" free-form input
#: (the ai.settings_number_form twin; the D-0063 static-form rule: the
#: per-open current/default readout rides the widget page's prompt).
_NUMBER_MODAL = ModalSpec(
    modal_id="cleanup.settings_number_form",
    title="Edit cleanup setting",
    fields=(ModalFieldSpec(
        field_id="new_value",
        label="New value (type: int)",       # shipped: value_type.__name__
        required=True, max_length=64),))

#: the widget page's back-route (the shipped attach_back_to_settings_button
#: label, verbatim).
_BACK_TO_SETTINGS = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ Back to Settings",
                               route=PanelRef("cleanup.settings")),))

#: the cleanup roster's widest preset set is 3 values (spam window
#: 10/15/30) — three declared slots; the renderer relabels the picked
#: setting's roster onto them (shipped: one button per preset, current
#: value highlighted primary).
_PRESET_SLOTS = 3


def cleanup_settings_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.settings",
        subsystem="cleanup",
        title="🧹 Cleanup",
        audience=Audience.INVOKER,
        # the shipped page accent — discord.Color.blurple()
        # (build_subsystem_embed).
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_SETTINGS_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("cleanup.settings_fields"))),
        actions=(
            # the shipped navigation pair (emoji as a SEPARATE component
            # field — the ai.settings shape); Open Panel routes to the
            # subsystem's own cog panel, the cleanup hub.
            PanelActionSpec(
                action_id="cl_back_to_hub", label="Back to Hub", emoji="↩",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=PanelRef("settings.hub")),
            PanelActionSpec(
                action_id="cl_open_panel", label="Open Panel", emoji="🪟",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=PanelRef("cleanup.hub")),
        ),
        selectors=(
            # the shipped S6 selects — picks dispatch through the shipped
            # edit/reset routing (sb/domain/cleanup/settings_widgets.py).
            SelectorSpec(
                selector_id="edit_setting", kind=SelectorKind.ENUM,
                options_source=_EDIT_OPTIONS,
                placeholder="Edit a setting…",
                audience_tier="staff",
                on_select=HandlerRef("cleanup.settings_edit_route")),
            SelectorSpec(
                selector_id="reset_setting", kind=SelectorKind.ENUM,
                options_source=_RESET_OPTIONS,
                placeholder="Reset a setting to its default…",
                audience_tier="staff",
                on_select=HandlerRef("cleanup.settings_reset_route")),
        ),
        # the shipped page carried NO standard nav row (the ai.settings
        # shape — exactly three component rows).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_settings"),
        justification=(
            "the shipped page footer is the DYNAMIC 'Scalar edit + reset "
            "live · use the selects below.  guild_id=<id>' literal "
            "(views/settings/subsystem_view.py build_subsystem_embed "
            "set_footer) — guild-parameterized copy outside FooterMode's "
            "none/subsystem/provenance vocabulary (the ai.settings "
            "precedent). The override delegates to the grammar renderer "
            "and replaces ONLY the footer; body, fields, selectors, "
            "actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cl_back_to_hub", "cl_open_panel"),
            ("edit_setting",),
            ("reset_setting",),
        )),)),
    )


def cleanup_settings_edit_presets_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.settings_edit_presets",
        subsystem="cleanup",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        actions=(
            *(PanelActionSpec(
                action_id=f"cl_preset_{i}", label=str(i),
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("cleanup.settings_preset_pick"),
                result_render=ResultRender.RESULT_CARD)
              for i in range(_PRESET_SLOTS)),
            # the shipped "Override…" free-form modal button (grey):
            # G-10 — the click ISSUES the number form, the submit
            # re-enters through the modal adapter and writes on the
            # audited settings.set_scalar lane (the ai widget shape).
            PanelActionSpec(
                action_id="cl_override_btn", label="Override…",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                defer_mode=DeferMode.MODAL, modal=_NUMBER_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("cleanup.settings_number_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_SETTINGS,
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_presets_widget"),
        justification=(
            "the shipped NumericPresetsView is fully runtime-"
            "parameterized: one button PER DECLARED PRESET VALUE labeled "
            "str(value) with the CURRENT value highlighted primary "
            "(views/settings/edit_number_presets.py), and the shipped "
            "dispatcher prompt carries the live current/default reprs — "
            "labels, styles and copy depend on the picked SettingSpec at "
            "open time, outside the static grammar (the ai."
            "settings_edit_presets precedent). The override delegates to "
            "the grammar renderer, then relabels/restyles the declared "
            "slots and drops the surplus."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cl_preset_0", "cl_preset_1", "cl_preset_2"),
            ("cl_override_btn",),
        )),)),
    )


# --- renderer overrides ---------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the two shipped adjustments (see justification):
    the footer literal and the inline Prohibited Words count field."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    fields = tuple(
        (f[0], f[1], True) if f[0] == "Prohibited Words" else f
        for f in rendered.embed.fields)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, footer=_HUB_FOOTER, fields=fields))


async def _render_words(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification) +
    the shipped EMPTY state: with no words configured the shipped view
    set ``embed.description`` and skipped the Current Words field
    (cleanup_cog.py build_embed) — the fields provider already dropped
    the field, the description rides here (dynamic per-guild copy,
    outside the static grammar)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    embed = _dc_replace(rendered.embed, footer=_WORDS_FOOTER)
    if not any(f[0] == "Current Words" for f in embed.fields):
        embed = _dc_replace(embed, description=_WORDS_EMPTY)
    return _dc_replace(rendered, embed=embed)


async def _render_settings(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped dynamic guild_id footer (see
    justification; the ai.settings override shape)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = ctx.guild_id if ctx.guild_id is not None else "DM"
    footer = (f"Scalar edit + reset live · use the selects below.  "
              f"guild_id={gid}")
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=footer))


async def _render_presets_widget(spec: PanelSpec, ctx) -> object:
    """The shipped NumericPresetsView page: the dispatcher prompt as the
    description, the declared preset roster relabeled onto the slot
    buttons (current value primary, the rest secondary), surplus slots
    dropped (the ai.render_presets_widget shape)."""
    from sb.domain.cleanup import settings_widgets as widgets
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    name = str((ctx.params or {}).get("setting") or "")
    sspec = widgets.spec_for_name(name)
    if sspec is None or not sspec.presets:   # defensive: never a crash
        return _dc_replace(rendered, embed=_dc_replace(
            rendered.embed, description=f"❌ Unknown setting `{name}`."))
    current = await widgets.current_value(int(ctx.guild_id or 0), sspec)
    # the shipped dispatcher prompt byte (subsystem_view.py
    # dispatch_edit_setting, the numeric_presets branch).
    description = (f"Pick a value for `{name}` "
                   f"(current=`{current!r}`, default=`{sspec.default!r}`):")
    presets = tuple(sspec.presets)
    components = []
    prefix = f"{spec.panel_id}.cl_preset_"
    for comp in rendered.components:
        if comp.custom_id.startswith(prefix):
            index = int(comp.custom_id[len(prefix):])
            if index >= len(presets):
                continue            # surplus slot — not rendered/minted
            value = presets[index]
            style = (ActionStyle.PRIMARY.value if value == current
                     else ActionStyle.SECONDARY.value)
            comp = _dc_replace(comp, label=str(value)[:80] or "(unset)",
                               style=style)
        components.append(comp)
    return _dc_replace(
        rendered, components=tuple(components),
        embed=_dc_replace(rendered.embed, description=description))


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("cleanup.hub")):
        panel("cleanup.hub")(cleanup_hub_spec)
    if not is_registered(PanelRef("cleanup.words")):
        panel("cleanup.words")(cleanup_words_spec)
    if not is_registered(PanelRef("cleanup.settings")):
        panel("cleanup.settings")(cleanup_settings_spec)
    if not is_registered(PanelRef("cleanup.settings_edit_presets")):
        panel("cleanup.settings_edit_presets")(
            cleanup_settings_edit_presets_spec)
    if not is_registered(HandlerRef("cleanup.render_hub")):
        handler("cleanup.render_hub")(_render_hub)
    if not is_registered(HandlerRef("cleanup.render_words")):
        handler("cleanup.render_words")(_render_words)
    if not is_registered(HandlerRef("cleanup.render_settings")):
        handler("cleanup.render_settings")(_render_settings)
    if not is_registered(HandlerRef("cleanup.render_presets_widget")):
        handler("cleanup.render_presets_widget")(_render_presets_widget)
    if not is_registered(ProviderRef("cleanup.hub_fields")):
        provider("cleanup.hub_fields")(_hub_fields)
    if not is_registered(ProviderRef("cleanup.words_fields")):
        provider("cleanup.words_fields")(_words_fields)
    if not is_registered(ProviderRef("cleanup.settings_fields")):
        provider("cleanup.settings_fields")(_settings_fields)


_register_refs()


def install_cleanup_panels() -> tuple[PanelSpec, ...]:
    """Register the panels with the panels registry (fences run here);
    composition-root/boot call. Idempotent for identical specs."""
    specs = (cleanup_hub_spec(), cleanup_words_spec(),
             cleanup_settings_spec(), cleanup_settings_edit_presets_spec())
    for spec in specs:
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
    return specs


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()
