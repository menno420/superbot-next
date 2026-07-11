"""AI panels (band 7) — the SHIPPED AI Platform surface byte-for-byte:

* ``ai.hub`` — the shipped AIPanelView (views/ai/panel.py @7f7628e1):
  the 💤/⚠️/✅ status embed over TWO shipped button rows on the verbatim
  persistent ``ai:<action>`` custom_ids (Refresh secondary + the primary
  diagnostics trio / the success settings quartet) plus the shipped
  standard nav row (``nav:help`` + ``nav:hub:admin`` "↩ Administration") —
  goldens/ai/sweep_ai + sweep_aimenu + sweep_slash_aimenu pin every byte.
  ``session_lifecycle=True`` with every component override-pinned: nothing
  is run-minted and no ``panel_anchors`` row is recorded (the goldens'
  db_delta carries none — the shipped sends were plain ``ctx.send``).
* ``ai.settings`` — the shipped SubsystemSettingsView page for the ai
  schema (views/settings/subsystem_view.py): the 🤖 blurple embed (schema
  description + tier line; Scalar settings / Bindings / Existing command
  panels fields; the dynamic ``guild_id=`` footer via renderer_override)
  over the shipped three component rows — the ↩ Back to Hub / 🪟 Open
  Panel buttons (verbatim ``settings_subsystem.*`` persistent ids) and
  the two RUN-MINTED windowed selects (the goldens pin ``<cid:1>`` /
  ``<cid:2>``) — goldens/ai/sweep_ai_settings pins every byte. This is
  an ai-owned port of the page the generic settings-mutation slice will
  eventually serve for every subsystem.
* ``ai.card`` — the generic one-embed reply card every ``!ai <sub>``
  view presents through (the projmoon.card/btd6.card pattern).

Click routes are golden-UNPINNED (no ai golden drives a click): the
shipped buttons EDITED the panel message in place; here each button opens
its view through the result/open-panel lane, and the shipped
policy/behavior/tools chooser PAGES land with their mutation slices
(declared honest pending terminals meanwhile).
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
    "ai_card_spec",
    "ai_hub_spec",
    "ai_settings_spec",
    "ensure_panel_refs",
    "install_ai_panels",
]


def _hub_action(action_id: str, label: str, style: ActionStyle,
                handler) -> PanelActionSpec:
    """One shipped AIPanelView button — no emoji field, the verbatim
    ``ai:<action>`` persistent custom_id. Action ids carry the ``ai_``
    prefix (bare ``refresh``/``settings`` collide with treasury/cleanup's
    K1 custom_id claims — the projmoon ``pm_`` precedent); the OVERRIDE
    keeps the shipped wire byte."""
    return PanelActionSpec(
        action_id=f"ai_{action_id}", label=label, style=style,
        audience_tier="staff", handler=handler,
        result_render=ResultRender.RESULT_CARD,
        custom_id_override=f"ai:{action_id}")


def ai_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.hub",
        subsystem="ai",
        title="💤 AI Platform",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            # row 0 — the shipped diagnostics quartet (Refresh secondary,
            # the rest primary/blurple).
            _hub_action("refresh", "Refresh", ActionStyle.SECONDARY,
                        PanelRef("ai.hub")),
            _hub_action("diagnostics", "Diagnostics", ActionStyle.PRIMARY,
                        HandlerRef("ai.diagnostics_view")),
            _hub_action("providers", "Providers", ActionStyle.PRIMARY,
                        HandlerRef("ai.providers_view")),
            _hub_action("routing", "Routing", ActionStyle.PRIMARY,
                        HandlerRef("ai.routing_view")),
            # row 1 — the shipped success (green) config quartet; the
            # chooser PAGES port with their mutation slices.
            _hub_action("settings", "Settings", ActionStyle.SUCCESS,
                        PanelRef("ai.settings")),
            _hub_action("policy", "Policy", ActionStyle.SUCCESS,
                        HandlerRef("ai.policy_chooser_pending")),
            _hub_action("behavior", "Behavior", ActionStyle.SUCCESS,
                        HandlerRef("ai.behavior_chooser_pending")),
            _hub_action("tools", "Tools", ActionStyle.SUCCESS,
                        HandlerRef("ai.tools_chooser_pending")),
        ),
        # the shipped standard nav row (PersistentView.attach_standard_nav:
        # 📚 Help + the parent-hub home — subsystem_registry pins
        # parent_hub="admin", the goldens pin "↩ Administration").
        navigation=NavigationSpec(home_hub="admin"),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_hub"),
        justification=(
            "the shipped overview embed is live-state-parameterized "
            "(views/ai/panel.py build_ai_panel_embed: the 💤/⚠️/✅ title "
            "emoji tracks enabled/degraded, six inline diagnostics fields "
            "over snapshot_for_cog, the degraded-only fallback field, and "
            "the '!ai status / …' footer literal) — inline fields and the "
            "footer literal sit outside the TextBlock/FooterMode grammar. "
            "The override delegates the component rows to the grammar "
            "renderer and replaces ONLY the embed (goldens/ai/sweep_ai + "
            "sweep_aimenu pin every byte; the projmoon/settings-hub "
            "precedent)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ai_refresh", "ai_diagnostics", "ai_providers", "ai_routing"),
            ("ai_settings", "ai_policy", "ai_behavior", "ai_tools"),)),)),
    )


def ai_card_spec() -> PanelSpec:
    """The generic one-embed reply card (the shipped ``ctx.send(embed=…)``)."""
    return PanelSpec(
        panel_id="ai.card",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_card"),
        justification=(
            "the shipped `!ai <sub>` replies are fully live-state-"
            "parameterized embeds built by sb/domain/ai/operator_cards.py "
            "(diagnostics snapshots, the readiness chain scan, the dual "
            "dry-run policy trace, the support-report draft — goldens/ai "
            "pins the bytes). Zero components; the renderer presents the "
            "handler-built RenderedEmbed verbatim (the projmoon.card "
            "precedent)."),
    )


def _settings_option_rosters():
    """(edit_options, reset_options) from the SHIPPED schema roster —
    labels/values are the shipped settings-key names, descriptions the
    shipped ``type=…`` / ``default=…`` strings (subsystem_view.py
    _attach_edit_select/_attach_reset_select verbatim)."""
    from sb.domain.ai.settings_schema import SHIPPED_SCHEMA_SETTINGS

    edit, reset = [], []
    for spec in SHIPPED_SCHEMA_SETTINGS:
        key = spec.settings_key
        edit.append({"label": key[:100], "value": key,
                     # SettingSpec canonicalizes value_type to its token
                     # ("bool"/"int"/"str") — the shipped
                     # value_type.__name__ string.
                     "description": f"type={spec.value_type}"[:100]})
        reset.append({"label": f"Reset {key}"[:100], "value": key,
                      "description": f"default={spec.default!r}"[:100]})
    return tuple(edit), tuple(reset)


async def _settings_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped page fields: Scalar settings (per-key current value +
    provenance + declared default + validity over THE K7 resolve seam),
    Bindings, Existing command panels."""
    from sb.kernel import settings as ksettings
    from sb.domain.ai.settings_schema import SHIPPED_SCHEMA_SETTINGS

    guild_id = int(ctx.guild_id or 0)
    lines = []
    for spec in SHIPPED_SCHEMA_SETTINGS:
        key = spec.settings_key
        try:
            value = await ksettings.resolve(guild_id, "ai", spec.name)
            explicit = await ksettings.is_explicitly_set(guild_id, "ai",
                                                         spec.name)
        except LookupError:
            lines.append(f"`{key}` — *(resolver returned None)*")
            continue
        # provenance vocabulary: explicit row → `guild`, else `default`
        # (the golden pins the all-defaults state).
        prov = "guild" if explicit else "default"
        valid = "valid"
        if spec.allowed_values and value not in spec.allowed_values:
            valid = "**invalid**"
        lines.append(f"`{key}` = `{value!r}` "
                     f"(`{prov}`, default=`{spec.default!r}`, {valid})")
    bindings = ("`audit_log_channel` — kind=`channel` (optional) "
                "cap=`ai.settings.configure`")
    return (("Scalar settings", "\n".join(lines)),
            ("Bindings", bindings),
            ("Existing command panels", "`!ai`, `!aimenu`"))


#: the shipped page description (subsystem_registry ai meta + the
#: tier/key line — build_subsystem_embed verbatim, double spaces included).
_SETTINGS_DESCRIPTION = (
    "_Read-only AI gateway diagnostics: provider state, feature flags, "
    "task routing, and request/failure counters. Does not own AI provider "
    "logic — that lives in core/runtime/ai/._\n"
    "visibility tier: `administrator`  ·  subsystem key: `ai`"
)

_EDIT_OPTIONS, _RESET_OPTIONS = _settings_option_rosters()


def ai_settings_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.settings",
        subsystem="ai",
        title="🤖 AI Platform",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_SETTINGS_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("ai.settings_fields"))),
        actions=(
            # row 0 — the shipped navigation pair (emoji as a SEPARATE
            # component field; verbatim persistent custom_ids).
            PanelActionSpec(
                action_id="back_to_hub", label="Back to Hub", emoji="↩",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=PanelRef("settings.hub"),
                custom_id_override="settings_subsystem.back_to_hub"),
            PanelActionSpec(
                action_id="open_panel", label="Open Panel", emoji="🪟",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=PanelRef("ai.hub"),
                custom_id_override="settings_subsystem.open_panel"),
        ),
        selectors=(
            # the shipped S6 windowed selects — RUN-MINTED session ids
            # (the golden pins <cid:1>/<cid:2>); the edit/reset WIDGETS
            # are the settings-mutation slice's port (pending terminals).
            SelectorSpec(
                selector_id="edit_setting", kind=SelectorKind.ENUM,
                options_source=_EDIT_OPTIONS,
                placeholder="Edit a setting…",
                audience_tier="staff",
                on_select=HandlerRef("ai.settings_edit_pending")),
            SelectorSpec(
                selector_id="reset_setting", kind=SelectorKind.ENUM,
                options_source=_RESET_OPTIONS,
                placeholder="Reset a setting to its default…",
                audience_tier="staff",
                on_select=HandlerRef("ai.settings_reset_pending")),
        ),
        # the shipped page carried NO standard nav row — the golden pins
        # exactly three component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_settings"),
        justification=(
            "the shipped page footer is the DYNAMIC 'Scalar edit + reset "
            "live · use the selects below.  guild_id=<id>' literal "
            "(views/settings/subsystem_view.py build_subsystem_embed "
            "set_footer) — guild-parameterized copy outside FooterMode's "
            "none/subsystem/provenance vocabulary (goldens/ai/"
            "sweep_ai_settings pins the byte; the settings-hub/access-"
            "explorer precedent). The override delegates to the grammar "
            "renderer and replaces ONLY the footer; body, fields, "
            "selectors, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("back_to_hub", "open_panel"),
            ("edit_setting",),
            ("reset_setting",),
        )),)),
    )


# --- renderer overrides ------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar-rendered components + the shipped live-state embed."""
    from sb.domain.ai import operator_cards
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=operator_cards.build_panel_embed())


async def _render_card(spec: PanelSpec, ctx) -> object:
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = (ctx.params or {}).get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_settings(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped dynamic guild_id footer."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = ctx.guild_id if ctx.guild_id is not None else "DM"
    footer = (f"Scalar edit + reset live · use the selects below.  "
              f"guild_id={gid}")
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=footer))


# --- pending select terminals -------------------------------------------------


async def _settings_edit_pending(req):
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS

    return Reply(SUCCESS,
                 "The scalar edit widgets (toggle/modal/preset buttons) "
                 "port with the settings-mutation slice — the declared "
                 "`ai.*` settings are readable here meanwhile.")


async def _settings_reset_pending(req):
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS

    return Reply(SUCCESS,
                 "The reset-to-default widget ports with the "
                 "settings-mutation slice.")


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------


_SPECS = {
    "ai.hub": ai_hub_spec,
    "ai.card": ai_card_spec,
    "ai.settings": ai_settings_spec,
}

_RENDERERS = {
    "ai.render_hub": _render_hub,
    "ai.render_card": _render_card,
    "ai.render_settings": _render_settings,
    "ai.settings_edit_pending": _settings_edit_pending,
    "ai.settings_reset_pending": _settings_reset_pending,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    if not is_registered(ProviderRef("ai.settings_fields")):
        provider("ai.settings_fields")(_settings_fields)


_register_refs()


def install_ai_panels() -> tuple[PanelSpec, ...]:
    out = []
    for factory in _SPECS.values():
        spec = factory()
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
