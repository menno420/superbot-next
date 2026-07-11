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
* ``ai.policy_chooser`` / ``ai.behavior_chooser`` / ``ai.tools_chooser``
  — the shipped chooser PAGES (views/ai/policy/chooser.py,
  views/ai/behavior/chooser.py, views/ai/tools/chooser.py @7f7628e1):
  the intro embeds verbatim (title/description/fields + the
  "Administrator-only · ephemeral follow-up." footer) over the shipped
  button rows; the Behavior "Advanced" button routes to the policy
  chooser (the shipped punt) and every ↩ AI home back-route rebuilds the
  hub fresh. The POLICY chooser's scope pickers are LIVE (below), the
  BEHAVIOR preset pickers too (the behavior-preset slice, D-0071 —
  channel/category/preview + the preset picker below), and so are the
  TOOLS profile pickers (the orchestration-mutation slice, D-0072 —
  guild/channel/category/preview below); the behavior ROUTING-MATRIX
  picker (views/ai/routing/matrix.py) is the routing-matrix follow-up
  slice's port — an honest pending terminal meanwhile
  (settings_widgets.py `chooser_scope_pending`).
* ``ai.tools_guild_picker`` / ``ai.tools_channel_picker`` /
  ``ai.tools_category_picker`` / ``ai.tools_profile_picker`` /
  ``ai.tools_preview_picker`` — the shipped TOOLS profile pickers
  (views/ai/tools/{scope_view,preview_view}.py, the
  orchestration-mutation slice): guild picks a profile directly, channel/
  category pick a target then a profile (Clear (inherit) included), every
  write ONE audited ``ai.set_*_orchestration`` op, and the preview is the
  shipped dry-run analyzer (sb/domain/ai/orchestration_widgets.py owns
  the routes; D-0072 ledgers the engine-shape deviations).
* ``ai.policy_channel_picker`` / ``ai.policy_category_picker`` /
  ``ai.policy_role_picker`` / ``ai.policy_preview_picker`` /
  ``ai.policy_scope_edit`` / ``ai.policy_role_edit`` /
  ``ai.policy_list`` — the shipped policy SCOPE PICKERS
  (views/ai/policy/{channel,category,role,preview,list}_view.py
  @7f7628e1, the policy-mutation slice): pick → Edit… → the shipped
  scope modal → ONE audited ``ai.set_*_policy`` op; the dry-run preview
  and the paged override list (sb/domain/ai/policy_widgets.py owns the
  routes; D-0070 ledgers the engine-shape deviations).
* ``ai.settings_edit_presets`` / ``ai.settings_edit_enum`` /
  ``ai.settings_edit_text`` — the shipped S6/S7 edit WIDGETS
  (views/settings/edit_number_presets.py / edit_enum.py / edit_text.py +
  edit_number.py) as parameterized session pages: the settings page's
  "Edit a setting…" pick opens the right widget for the picked
  SettingSpec and each pick/click writes through the audited
  ``settings.set_scalar`` op (sb/domain/ai/settings_widgets.py). The
  free-form editors are G-10 declared forms (the modal-arming slice):
  the presets page's Override… and the text page's Edit… ISSUE the
  shipped NumberSettingModal/TextSettingModal twins and their submits
  re-enter through the frozen modal adapter.

Click routes are golden-UNPINNED (no ai golden drives a click): the
shipped buttons EDITED the panel message in place; on the component
surface these pages swap in place too (the presenter's deferred-update
edit), while the shipped ephemeral follow-up widgets render as pages of
the same anchor with a ↩ Back to Settings route (ledgered deviation).
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
    ModalFieldStyle,
    ModalSpec,
    NavRouteSpec,
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
    "ai_behavior_category_picker_spec",
    "ai_behavior_channel_picker_spec",
    "ai_behavior_chooser_spec",
    "ai_behavior_preset_picker_spec",
    "ai_behavior_preview_picker_spec",
    "ai_card_spec",
    "ai_hub_spec",
    "ai_policy_category_picker_spec",
    "ai_policy_channel_picker_spec",
    "ai_policy_chooser_spec",
    "ai_policy_list_spec",
    "ai_policy_preview_picker_spec",
    "ai_policy_role_edit_spec",
    "ai_policy_role_picker_spec",
    "ai_policy_scope_edit_spec",
    "ai_settings_edit_enum_spec",
    "ai_settings_edit_presets_spec",
    "ai_settings_edit_text_spec",
    "ai_settings_spec",
    "ai_tools_category_picker_spec",
    "ai_tools_channel_picker_spec",
    "ai_tools_chooser_spec",
    "ai_tools_guild_picker_spec",
    "ai_tools_preview_picker_spec",
    "ai_tools_profile_picker_spec",
    "ensure_panel_refs",
    "install_ai_panels",
]

#: the shipped chooser footer byte (every views/ai/* chooser set it).
_CHOOSER_FOOTER = "Administrator-only · ephemeral follow-up."


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
            # row 1 — the shipped success (green) config quartet; each
            # opens its shipped page (the shipped edit_message swap — the
            # component presenter's deferred-update edit is the same
            # in-place navigation).
            _hub_action("settings", "Settings", ActionStyle.SUCCESS,
                        PanelRef("ai.settings")),
            _hub_action("policy", "Policy", ActionStyle.SUCCESS,
                        PanelRef("ai.policy_chooser")),
            _hub_action("behavior", "Behavior", ActionStyle.SUCCESS,
                        PanelRef("ai.behavior_chooser")),
            _hub_action("tools", "Tools", ActionStyle.SUCCESS,
                        PanelRef("ai.tools_chooser")),
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


# --- the shipped chooser PAGES (views/ai/{policy,behavior,tools} @7f7628e1) -----


def _scope_action(action_id: str, label: str, style: ActionStyle,
                  handler=None) -> PanelActionSpec:
    """One chooser button — the shipped transient views carried NO
    persistent custom_ids (created per click, timeout 180), so every id
    is session-minted; scope pickers land on the shared pending terminal
    until their mutation slices."""
    return PanelActionSpec(
        action_id=action_id, label=label, style=style,
        audience_tier="staff",
        handler=handler or HandlerRef("ai.chooser_scope_pending"),
        result_render=ResultRender.RESULT_CARD)


async def _policy_chooser_fields(ctx):
    """The shipped build_chooser_embed field rows, verbatim."""
    return (
        ("Channel",
         "Pick a channel and set its mode "
         "(`inherit` / `always_reply` / `mention_only` / `disabled`)."),
        ("Category",
         "Same shape as channel; applies to every channel in the "
         "category."),
        ("Role",
         "Allow / deny / inherit and optional min-level override per "
         "role."),
        ("List overrides",
         "See every current override for this guild (paged)."),
    )


def ai_policy_chooser_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.policy_chooser",
        subsystem="ai",
        title="AI Policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
                  "Override the guild's AI policy for specific channels, "
                  "categories, or roles. Writes flow through "
                  "`services.ai_policy_mutation` and emit `ai.policy.*` "
                  "events; the natural-language stage picks up the new "
                  "rules on the next message."),
              FieldsBlock(provider=ProviderRef("ai.policy_chooser_fields"))),
        actions=(
            # the policy-mutation slice: every scope button opens its
            # shipped picker page (the shipped edit_message swap).
            _scope_action("policy_channel", "Channel", ActionStyle.PRIMARY,
                          handler=PanelRef("ai.policy_channel_picker")),
            _scope_action("policy_category", "Category",
                          ActionStyle.PRIMARY,
                          handler=PanelRef("ai.policy_category_picker")),
            _scope_action("policy_role", "Role", ActionStyle.PRIMARY,
                          handler=PanelRef("ai.policy_role_picker")),
            _scope_action("policy_preview", "Effective policy",
                          ActionStyle.SECONDARY,
                          handler=PanelRef("ai.policy_preview_picker")),
            _scope_action("policy_list", "List overrides",
                          ActionStyle.SECONDARY,
                          handler=HandlerRef("ai.policy_list_open")),
        ),
        # the shipped "↩ AI home" back button (views/ai/_nav.py
        # add_back_button, row 4) — an engine back-route rebuilding the
        # hub FRESH at click time; no standard help/hub nav row existed.
        navigation=NavigationSpec(
            show_help=False, show_home=False,
            extra_routes=(NavRouteSpec(label="↩ AI home",
                                       route=PanelRef("ai.hub")),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_chooser"),
        justification=(
            "the shipped chooser footer is the STATIC 'Administrator-only "
            "· ephemeral follow-up.' literal (views/ai/policy/chooser.py "
            "build_chooser_embed set_footer) — copy outside FooterMode's "
            "none/subsystem/provenance vocabulary. The override delegates "
            "everything to the grammar renderer and replaces ONLY the "
            "footer (the ai.settings precedent)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("policy_channel", "policy_category", "policy_role"),
            ("policy_preview", "policy_list"),
        )),)),
    )


async def _behavior_chooser_fields(ctx):
    """The shipped build_behavior_embed field rows, verbatim."""
    return (
        ("Channel", "Bind a preset to a single text channel."),
        ("Category",
         "Bind a preset to a category (applies to its channels)."),
        ("Preview (dry-run)",
         "See the precedence trace the resolver would produce for "
         "your own user in a channel — no audit, no cooldown."),
        ("Routing matrix",
         "Read-only diagnostic showing the dry-run resolver "
         "outcome for a channel — useful when an operator asks "
         "*why* a channel allows or denies."),
        ("Advanced",
         "Open the raw policy editor (mode / min_level / cooldown / "
         "profile). Sentinel-safe: untouched fields are preserved."),
    )


def ai_behavior_chooser_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.behavior_chooser",
        subsystem="ai",
        title="AI Behavior",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
                  "Pick **what the AI should do here**, then choose a "
                  "scope. Presets bind together a channel mode plus an "
                  "instruction profile. Use **Preview** to dry-run the "
                  "resolver against your own user before saving. "
                  "**Advanced** opens the raw policy editor."),
              FieldsBlock(
                  provider=ProviderRef("ai.behavior_chooser_fields"))),
        actions=(
            # the behavior-preset slice (D-0071): channel/category open
            # their shipped scope-picker pages, preview opens the shipped
            # PreviewChannelSelectView reuse under behavior page bytes.
            _scope_action("behavior_channel", "Channel",
                          ActionStyle.PRIMARY,
                          handler=PanelRef("ai.behavior_channel_picker")),
            _scope_action("behavior_category", "Category",
                          ActionStyle.PRIMARY,
                          handler=PanelRef("ai.behavior_category_picker")),
            _scope_action("behavior_preview", "Preview (dry-run)",
                          ActionStyle.SECONDARY,
                          handler=PanelRef("ai.behavior_preview_picker")),
            _scope_action("behavior_matrix", "Routing matrix",
                          ActionStyle.SECONDARY),
            # the shipped Advanced punt — swap to the RAW policy chooser
            # page (views/ai/behavior/chooser.py advanced_btn).
            _scope_action("behavior_advanced", "Advanced",
                          ActionStyle.SECONDARY,
                          handler=PanelRef("ai.policy_chooser")),
        ),
        navigation=NavigationSpec(
            show_help=False, show_home=False,
            extra_routes=(NavRouteSpec(label="↩ AI home",
                                       route=PanelRef("ai.hub")),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_chooser"),
        justification=(
            "the shipped chooser footer is the STATIC 'Administrator-only "
            "· ephemeral follow-up.' literal (views/ai/behavior/chooser.py "
            "build_behavior_embed set_footer) — copy outside FooterMode's "
            "vocabulary; the override replaces ONLY the footer."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("behavior_channel", "behavior_category"),
            ("behavior_preview", "behavior_matrix"),
            ("behavior_advanced",),
        )),)),
    )


async def _tools_chooser_fields(ctx):
    """The shipped build_tools_embed field rows + the best-effort
    "Current" decoration (the shipped panel entry read the
    ai_config_projection snapshot best-effort:
    ``orchestration.guild_profile_key`` + the channel/category override
    COUNTS — here the orchestration-mutation slice's real stores, the
    guild KV row + the typed columns' non-NULL counts; each read is
    per-part fail-soft so a DB-free root keeps the shipped fresh-guild
    bytes)."""
    fields = [
        ("Guild / Channel / Category",
         "Bind a built-in orchestration profile at a scope. Channel wins "
         "over category, category over the guild default."),
        ("Preview (dry-run)",
         "Pick a channel to see the resolved profile, the offered vs "
         "withheld tools (with reason codes), and the loop budget — no "
         "provider call."),
    ]
    from sb.domain.ai import policy_store, readers

    # the guild default EXACTLY as the K10 reader serves it (KV row when
    # ever written, band-1 fallback otherwise — the codex #187 P2: the
    # decoration must mirror the resolver, the shipped single-source
    # posture); the helper is fail-safe (None on any miss).
    guild_key = await readers.guild_orchestration_default(
        int(ctx.guild_id or 0))
    channels, categories = {}, {}
    try:
        channels, categories = await policy_store.load_orchestration_overlays(
            int(ctx.guild_id or 0))
    except Exception:  # noqa: BLE001 — a count miss keeps the shipped
        pass           # fresh-guild zeros
    key = str(guild_key) if guild_key else "compatible_default (today)"
    fields.append((
        "Current",
        f"guild default: `{key}`\n"
        f"overrides: {len(channels)} channel · {len(categories)} category"))
    return tuple(fields)


def ai_tools_chooser_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.tools_chooser",
        subsystem="ai",
        title="AI Tools & Workflows",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
                  "Choose **which tools the AI may use** here, "
                  "independently of its reply tone (Behavior) and who may "
                  "talk to it (Policy). A profile narrows the offered "
                  "toolset, sets the tool-choice requirement, and caps "
                  "the tool/loop budget. Writes flow through "
                  "`services.ai_orchestration_mutation`; the next message "
                  "picks up the new profile. Safe default: every scope "
                  "inherits today's behaviour until you set a profile."),
              FieldsBlock(provider=ProviderRef("ai.tools_chooser_fields"))),
        actions=(
            # the orchestration-mutation slice: every scope button opens
            # its shipped picker page (the shipped edit_message swap).
            _scope_action("tools_guild", "Guild", ActionStyle.PRIMARY,
                          handler=PanelRef("ai.tools_guild_picker")),
            _scope_action("tools_channel", "Channel", ActionStyle.PRIMARY,
                          handler=PanelRef("ai.tools_channel_picker")),
            _scope_action("tools_category", "Category",
                          ActionStyle.PRIMARY,
                          handler=PanelRef("ai.tools_category_picker")),
            _scope_action("tools_preview", "Preview (dry-run)",
                          ActionStyle.SECONDARY,
                          handler=PanelRef("ai.tools_preview_picker")),
        ),
        navigation=NavigationSpec(
            show_help=False, show_home=False,
            extra_routes=(NavRouteSpec(label="↩ AI home",
                                       route=PanelRef("ai.hub")),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_chooser"),
        justification=(
            "the shipped chooser footer is the STATIC 'Administrator-only "
            "· ephemeral follow-up.' literal (views/ai/tools/chooser.py "
            "build_tools_embed set_footer) — copy outside FooterMode's "
            "vocabulary; the override replaces ONLY the footer."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("tools_guild", "tools_channel", "tools_category"),
            ("tools_preview",),
        )),)),
    )


# --- the POLICY SCOPE PICKER pages (views/ai/policy/* @7f7628e1 — the
# --- policy-mutation slice; sb/domain/ai/policy_widgets.py owns the routes) -----

#: the shipped scope-page footer byte (chooser.py _scope_page_embed).
_POLICY_PAGE_FOOTER = "Administrator-only · in-place navigation."

#: every scope page's shipped "↩ AI Policy" back-route (_add_back_to_policy).
_BACK_TO_POLICY = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ AI Policy",
                               route=PanelRef("ai.policy_chooser")),))

#: the shipped ChannelPolicyModal / CategoryPolicyModal (channel_view.py /
#: category_view.py) as ONE G-10 declared form — identical field bytes;
#: the scope/target ride the kernel modal-args stash (the shipped per-open
#: dynamic title "AI policy · #<name>" is static-spec data here — the
#: D-0066 static-title class; the edit page's prompt carries the target).
_POLICY_MODE_MODAL = ModalSpec(
    modal_id="ai.policy_mode_form",
    title="AI policy",
    fields=(
        ModalFieldSpec(
            field_id="mode", label="Mode",
            placeholder="inherit | always_reply | mention_only | disabled",
            required=True, min_length=4, max_length=20),
        ModalFieldSpec(
            field_id="min_level", label="Min level (blank = inherit)",
            placeholder="0", required=False, max_length=4),
        ModalFieldSpec(
            field_id="cooldown_seconds",
            label="Cooldown seconds (blank = inherit)",
            placeholder="30", required=False, max_length=6),
    ))

#: the shipped RolePolicyModal (role_view.py) twin.
_POLICY_ROLE_MODAL = ModalSpec(
    modal_id="ai.policy_role_form",
    title="AI policy",
    fields=(
        ModalFieldSpec(
            field_id="decision", label="Decision",
            placeholder="allow | deny | inherit",
            required=True, min_length=4, max_length=10),
        ModalFieldSpec(
            field_id="min_level_override",
            label="Min level override (blank = inherit)",
            placeholder="0", required=False, max_length=4),
        ModalFieldSpec(
            field_id="bypass_cooldown", label="Bypass cooldown (yes/no)",
            placeholder="no", required=False, max_length=5),
    ))

_POLICY_PICKER_JUSTIFICATION = (
    "the shipped scope-page footer is the STATIC 'Administrator-only · "
    "in-place navigation.' literal (views/ai/policy/chooser.py "
    "_scope_page_embed set_footer) — copy outside FooterMode's "
    "none/subsystem/provenance vocabulary; the override delegates to the "
    "grammar renderer and replaces ONLY the footer (the ai.render_chooser "
    "precedent).")


def _policy_picker_spec(panel_id: str, *, title: str, instruction: str,
                        kind: SelectorKind, placeholder: str,
                        on_select: str, selector_id: str,
                        provider_name: str = "",
                        navigation: NavigationSpec | None = None) -> PanelSpec:
    """One shipped scope-picker page: the chooser's _scope_page_embed
    (title + instruction) over the scope's single pick-one select.
    ``selector_id`` is per-picker unique — K1 leaf-id claims are
    subsystem-wide (the ai_hub `ai_` prefix precedent). A CHANNEL-kind
    selector rides the Discord-NATIVE channel picker (wire type 8, the
    #167 LogChannelSelectView lane — the client supplies the options, the
    SHIPPED ChannelSelect shape exactly); category/role selects are
    roster-provider-fed string selects."""
    return PanelSpec(
        panel_id=panel_id,
        subsystem="ai",
        title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(instruction),),
        selectors=(
            SelectorSpec(
                selector_id=selector_id, kind=kind,
                options_source=(ProviderRef(provider_name)
                                if provider_name else ()),
                placeholder=placeholder,
                audience_tier="staff",
                on_select=HandlerRef(on_select)),
        ),
        navigation=navigation or _BACK_TO_POLICY,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_policy_picker"),
        justification=_POLICY_PICKER_JUSTIFICATION,
        layout=LayoutSpec(pages=(PageSpec(rows=((selector_id,),)),)),
    )


def ai_policy_channel_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.policy_channel_picker",
        title="Channel AI policy",
        instruction="Pick a channel to set its AI policy.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel to configure…",
        on_select="ai.policy_channel_pick",
        selector_id="policy_channel_pick")


def ai_policy_category_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.policy_category_picker",
        title="Category AI policy",
        instruction="Pick a category to set its AI policy.",
        kind=SelectorKind.ENTITY,
        provider_name="ai.policy_category_options",
        placeholder="Pick a category to configure…",
        on_select="ai.policy_category_pick",
        selector_id="policy_category_pick")


def ai_policy_role_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.policy_role_picker",
        title="Role AI policy",
        instruction="Pick a role to set its AI policy.",
        kind=SelectorKind.ROLE,
        provider_name="ai.policy_role_options",
        placeholder="Pick a role to configure…",
        on_select="ai.policy_role_pick",
        selector_id="policy_role_pick")


def ai_policy_preview_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.policy_preview_picker",
        title="Effective AI policy (dry-run)",
        instruction="Pick a channel to see the effective AI policy as "
                    "your user.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel to preview…",
        on_select="ai.policy_preview_pick",
        selector_id="policy_preview_pick")


_POLICY_EDIT_JUSTIFICATION = (
    "the shipped flow opened the scope modal DIRECTLY from the native "
    "select pick (views/ai/policy/channel_view.py _ChannelPickSelect."
    "callback response.send_modal) — a selector pick is AUTO-deferred on "
    "this engine so a modal can no longer be its first response; the Edit… "
    "button intermediates (the D-0054/D-0066 confirm-surface posture, "
    "ledgered in D-0070) and the page's prompt carries the PICKED target "
    "(per-open copy outside the static grammar). The override delegates "
    "to the grammar renderer and supplies ONLY the description + the "
    "shipped scope-page footer.")


def ai_policy_scope_edit_spec() -> PanelSpec:
    """The channel/category edit page — ONE page for the two scopes that
    share the shipped mode/min_level/cooldown form (the picked scope +
    target ride the session args)."""
    return PanelSpec(
        panel_id="ai.policy_scope_edit",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="edit_scope_policy", label="Edit…",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                defer_mode=DeferMode.MODAL, modal=_POLICY_MODE_MODAL,
                # the shipped safe_defer(..., ephemeral=True) flag on the
                # submit re-entry (PanelActionSpec.reply_visibility growth,
                # D-0073 — the forms' oracle twins all followed up ephemeral).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("ai.policy_mode_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_POLICY,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_policy_edit"),
        justification=_POLICY_EDIT_JUSTIFICATION,
        layout=LayoutSpec(pages=(PageSpec(rows=(("edit_scope_policy",),)),)),
    )


def ai_policy_role_edit_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.policy_role_edit",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="edit_role_policy", label="Edit…",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                defer_mode=DeferMode.MODAL, modal=_POLICY_ROLE_MODAL,
                # the shipped safe_defer(..., ephemeral=True) flag on the
                # submit re-entry (PanelActionSpec.reply_visibility growth,
                # D-0073 — the forms' oracle twins all followed up ephemeral).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("ai.policy_role_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_POLICY,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_policy_edit"),
        justification=_POLICY_EDIT_JUSTIFICATION,
        layout=LayoutSpec(pages=(PageSpec(rows=(("edit_role_policy",),)),)),
    )


def ai_policy_list_spec() -> PanelSpec:
    """The shipped paged override list (views/ai/policy/list_view.py):
    Prev/Next over the three typed tables, 10 per page."""
    return PanelSpec(
        panel_id="ai.policy_list",
        subsystem="ai",
        title="AI policy overrides",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="list_prev", label="Prev",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("ai.policy_list_page"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="list_next", label="Next",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("ai.policy_list_page"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_POLICY,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_policy_list"),
        justification=(
            "the shipped list embed is fully live-state-parameterized "
            "(views/ai/policy/list_view.py build_list_embed: the total-"
            "count description, one field per override row, the dynamic "
            "'Page p / t · administrator-only' footer, Prev/Next disabled "
            "at the edges) — per-render copy and component state outside "
            "the static grammar. The override delegates to the grammar "
            "renderer, replaces description/fields/footer from the typed-"
            "table reads and flips the edge buttons' disabled flags."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("list_prev", "list_next"),
        )),)),
    )


# --- the BEHAVIOR PRESET PICKER pages (views/ai/behavior/* — the
# --- behavior-preset slice, D-0071; sb/domain/ai/behavior_widgets.py owns
# --- the routes; the shipped page footer byte is the SAME
# --- 'Administrator-only · in-place navigation.' literal, so the pages
# --- ride ai.render_policy_picker) -------------------------------------------

#: every behavior page's shipped "↩ AI Behavior" back-route
#: (_add_back_to_behavior).
_BACK_TO_BEHAVIOR = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ AI Behavior",
                               route=PanelRef("ai.behavior_chooser")),))


def ai_behavior_channel_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.behavior_channel_picker",
        title="Behavior · channel",
        instruction="Pick a channel — the next step lists the available "
                    "presets.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel…",
        on_select="ai.behavior_channel_pick",
        selector_id="behavior_channel_pick",
        navigation=_BACK_TO_BEHAVIOR)


def ai_behavior_category_picker_spec() -> PanelSpec:
    """The shipped _BehaviorCategorySelect was a native category-typed
    ChannelSelect — the D-0070 ledgered engine lane renders it as the
    roster-fed string select capped at 25 (the policy category picker's
    exact deviation)."""
    return _policy_picker_spec(
        "ai.behavior_category_picker",
        title="Behavior · category",
        instruction="Pick a category — the next step lists the available "
                    "presets.",
        kind=SelectorKind.ENTITY,
        provider_name="ai.policy_category_options",
        placeholder="Pick a category…",
        on_select="ai.behavior_category_pick",
        selector_id="behavior_category_pick",
        navigation=_BACK_TO_BEHAVIOR)


def ai_behavior_preview_picker_spec() -> PanelSpec:
    """The shipped Behavior Preview button REUSED the policy chooser's
    PreviewChannelSelectView (behavior/chooser.py imports it) under its
    own page embed — same select, same dry-run callback
    (ai.policy_preview_pick), behavior page bytes + the behavior
    back-route."""
    return _policy_picker_spec(
        "ai.behavior_preview_picker",
        title="Behavior · preview (dry-run)",
        instruction="Pick a channel to preview the effective AI policy "
                    "as your user.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel to preview…",
        on_select="ai.policy_preview_pick",
        selector_id="behavior_preview_pick",
        navigation=_BACK_TO_BEHAVIOR)


def ai_behavior_preset_picker_spec() -> PanelSpec:
    """The shipped preset_picker.py page: the catalog embed (one field
    per preset) over the single pick-one preset select — the pick applies
    immediately (the shipped _PresetSelect.callback ran apply_preset from
    the pick; no modal, so no intermediating button is needed on this
    engine)."""
    return PanelSpec(
        panel_id="ai.behavior_preset_picker",
        subsystem="ai",
        title="Pick a Behavior preset",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            "Selecting a preset binds it to the picked scope and writes "
            "through the existing policy chokepoint. Existing min_level "
            "/ cooldown overrides for that scope are preserved."),),
        selectors=(
            SelectorSpec(
                selector_id="behavior_preset_pick",
                kind=SelectorKind.ENTITY,
                options_source=ProviderRef("ai.behavior_preset_options"),
                placeholder="Pick a preset…",
                audience_tier="staff",
                on_select=HandlerRef("ai.behavior_preset_pick")),
        ),
        navigation=_BACK_TO_BEHAVIOR,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_behavior_preset"),
        justification=(
            "the shipped build_preset_picker_embed is per-open "
            "parameterized (views/ai/behavior/preset_picker.py): the "
            "description interpolates the PICKED scope_label ('Selecting "
            "a preset binds it to **{scope_label}** and writes through "
            "the existing policy chokepoint…') and the field rows are "
            "catalog reads (name='`{key}` · mode=`{mode}`', "
            "value=headline) — per-render copy outside the static "
            "grammar. The override delegates to the grammar renderer and "
            "replaces ONLY description + fields."),
        layout=LayoutSpec(pages=(PageSpec(
            rows=(("behavior_preset_pick",),)),)),
    )


# --- the TOOLS PROFILE PICKER pages (views/ai/tools/* — the
# --- orchestration-mutation slice; sb/domain/ai/orchestration_widgets.py
# --- owns the routes; the shipped _tools_page_embed footer byte is the
# --- SAME 'Administrator-only · in-place navigation.' literal, so the
# --- pages ride ai.render_policy_picker) --------------------------------------

#: every tools page's shipped "↩ AI Tools" back-route
#: (chooser.py _add_back_to_tools, label verbatim).
_BACK_TO_TOOLS = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ AI Tools",
                               route=PanelRef("ai.tools_chooser")),))


def ai_tools_guild_picker_spec() -> PanelSpec:
    """The shipped GuildToolsProfileView page ("Tools · guild default"):
    the page IS the profile select — no target pick, NO clear option
    (the shipped ``_profile_options(include_clear=scope != "guild")``);
    the pick handler defaults to scope=guild / label "the guild"."""
    return _policy_picker_spec(
        "ai.tools_guild_picker",
        title="Tools · guild default",
        instruction="Pick the guild-default orchestration profile.",
        kind=SelectorKind.ENUM,
        provider_name="ai.orchestration_profile_options",
        placeholder="Pick an orchestration profile…",
        on_select="ai.tools_profile_pick",
        selector_id="tools_guild_profile_pick",
        navigation=_BACK_TO_TOOLS)


def ai_tools_channel_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.tools_channel_picker",
        title="Tools · channel",
        instruction="Pick a channel — the next step lists the "
                    "orchestration profiles.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel to configure…",
        on_select="ai.tools_channel_pick",
        selector_id="tools_channel_scope_pick",
        navigation=_BACK_TO_TOOLS)


def ai_tools_category_picker_spec() -> PanelSpec:
    """The shipped _CategoryPickSelect was a native category-typed
    ChannelSelect — the D-0070(a) ledgered engine lane renders it as the
    roster-fed string select capped at 25 (the policy/behavior category
    pickers' exact deviation)."""
    return _policy_picker_spec(
        "ai.tools_category_picker",
        title="Tools · category",
        instruction="Pick a category — the next step lists the "
                    "orchestration profiles.",
        kind=SelectorKind.ENTITY,
        provider_name="ai.policy_category_options",
        placeholder="Pick a category to configure…",
        on_select="ai.tools_category_pick",
        selector_id="tools_category_scope_pick",
        navigation=_BACK_TO_TOOLS)


def ai_tools_preview_picker_spec() -> PanelSpec:
    return _policy_picker_spec(
        "ai.tools_preview_picker",
        title="Tools · preview (dry-run)",
        instruction="Pick a channel to preview the resolved AI tool "
                    "orchestration.",
        kind=SelectorKind.CHANNEL,
        placeholder="Pick a channel to preview…",
        on_select="ai.tools_preview_pick",
        selector_id="tools_preview_pick",
        navigation=_BACK_TO_TOOLS)


def ai_tools_profile_picker_spec() -> PanelSpec:
    """The channel/category step-2 profile choice — the shipped
    _ProfileChoiceView was a plain ephemeral CONTENT message ("Pick an
    orchestration profile for {label}.") over the one select; the page's
    per-open prompt rides the renderer override (the D-0066 class) and
    the roster carries the shipped Clear (inherit) option."""
    return PanelSpec(
        panel_id="ai.tools_profile_picker",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="tools_profile_pick",
                kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "ai.orchestration_profile_options_clear"),
                placeholder="Pick an orchestration profile…",
                audience_tier="staff",
                on_select=HandlerRef("ai.tools_profile_pick")),
        ),
        navigation=_BACK_TO_TOOLS,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_tools_profile"),
        justification=(
            "the shipped profile choice carried a PER-OPEN prompt with "
            "the picked target ('Pick an orchestration profile for "
            "{label}.' — views/ai/tools/scope_view.py's send_message "
            "content) — per-render copy outside the static grammar. The "
            "override delegates to the grammar renderer and supplies "
            "ONLY the description + the shipped tools-page footer."),
        layout=LayoutSpec(pages=(PageSpec(
            rows=(("tools_profile_pick",),)),)),
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
        if explicit:
            # an explicit row arrives as the RAW KV string — the shipped
            # page rendered the COERCED typed value + the coercion-driven
            # validity flag (settings_resolution.resolve_setting; the
            # all-defaults golden state never reaches this branch).
            from sb.domain.settings.service import coerce_value

            value, ok, _diag = coerce_value(spec, str(value))
            valid = "valid" if ok else "**invalid**"
        else:
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
            # (the golden pins <cid:1>/<cid:2>); picks dispatch through
            # the shipped edit/reset routing (settings_widgets.py — the
            # settings-mutation slice's port).
            SelectorSpec(
                selector_id="edit_setting", kind=SelectorKind.ENUM,
                options_source=_EDIT_OPTIONS,
                placeholder="Edit a setting…",
                audience_tier="staff",
                on_select=HandlerRef("ai.settings_edit_route")),
            SelectorSpec(
                selector_id="reset_setting", kind=SelectorKind.ENUM,
                options_source=_RESET_OPTIONS,
                placeholder="Reset a setting to its default…",
                audience_tier="staff",
                on_select=HandlerRef("ai.settings_reset_route")),
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


# --- the shipped S6/S7 edit WIDGET pages -----------------------------------------

#: the widget pages' shared back-route (the shipped
#: attach_back_to_settings_button label, verbatim).
_BACK_TO_SETTINGS = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ Back to Settings",
                               route=PanelRef("ai.settings")),))

#: the widest shipped preset roster is 6 values (min-level / cooldown) —
#: six declared slots; the renderer relabels the picked setting's roster
#: onto them and DROPS the surplus (shipped: one button per preset,
#: five per row, current value highlighted primary).
_PRESET_SLOTS = 6

#: the shipped NumberSettingModal (views/settings/edit_number.py) as the
#: G-10 declared form — the presets page's "Override…" free-form input.
#: The shipped title/placeholder embedded the picked setting's name and
#: live current/default reprs; ModalSpec fields are static [S] data, so
#: the per-open readout rides the widget page's prompt instead (ledgered
#: deviation — the form itself is transient wire the corpus cannot pin,
#: D-0063). The label is the shipped byte verbatim: every presets-hinted
#: ai scalar is int. Submits re-enter through the modal adapter with the
#: kernel-stashed `setting` param (resolve()'s modal-issue stash).
_NUMBER_MODAL = ModalSpec(
    modal_id="ai.settings_number_form",
    title="Edit ai setting",
    fields=(ModalFieldSpec(
        field_id="new_value",
        label="New value (type: int)",       # shipped: value_type.__name__
        required=True, max_length=64),))

#: the shipped TextSettingModal (views/settings/edit_text.py) — the
#: free-form editor for str SettingSpecs without allowed_values
#: (ai_default_model, ai_guild_instruction_profile). Shipped shape
#: verbatim where static: multi-line paragraph style, optional (an empty
#: submit writes the empty string — "empty = routing default"), 2000 cap.
_TEXT_MODAL = ModalSpec(
    modal_id="ai.settings_text_form",
    title="Edit ai setting",
    fields=(ModalFieldSpec(
        field_id="new_value",
        label="New value (text)",            # shipped byte
        style=ModalFieldStyle.PARAGRAPH,
        required=False, max_length=2000),))


def ai_settings_edit_presets_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.settings_edit_presets",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        actions=(
            *(PanelActionSpec(
                action_id=f"preset_{i}", label=str(i),
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("ai.settings_preset_pick"),
                result_render=ResultRender.RESULT_CARD)
              for i in range(_PRESET_SLOTS)),
            # the shipped "Override…" free-form modal button (grey =
            # secondary): G-10 — the click ISSUES the number form, the
            # submit re-enters through the modal adapter and writes on the
            # audited settings.set_scalar lane (the modal-arming slice;
            # formerly the declared pending terminal).
            PanelActionSpec(
                action_id="override_btn", label="Override…",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                defer_mode=DeferMode.MODAL, modal=_NUMBER_MODAL,
                # the shipped safe_defer(..., ephemeral=True) flag on the
                # submit re-entry (PanelActionSpec.reply_visibility growth,
                # D-0073 — the forms' oracle twins all followed up ephemeral).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("ai.settings_number_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_SETTINGS,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_presets_widget"),
        justification=(
            "the shipped NumericPresetsView is fully runtime-"
            "parameterized: one button PER DECLARED PRESET VALUE labeled "
            "str(value) with the CURRENT value highlighted primary "
            "(views/settings/edit_number_presets.py), and the shipped "
            "dispatcher prompt carries the live current/default reprs — "
            "labels, styles, slot count and copy all depend on the picked "
            "SettingSpec at open time, outside the static grammar. The "
            "override delegates to the grammar renderer, then relabels/"
            "restyles the declared slots and drops the surplus."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("preset_0", "preset_1", "preset_2", "preset_3", "preset_4"),
            ("preset_5", "override_btn"),
        )),)),
    )


def ai_settings_edit_enum_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.settings_edit_enum",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="enum_value", kind=SelectorKind.ENUM,
                options_source=ProviderRef("ai.enum_edit_options"),
                placeholder="Pick a new value…",
                audience_tier="staff",
                on_select=HandlerRef("ai.settings_enum_pick")),
        ),
        navigation=_BACK_TO_SETTINGS,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_enum_widget"),
        justification=(
            "the shipped enum widget prompt + placeholder carry the picked "
            "setting's name ('Pick a new value for `ai.<name>`:' / 'Pick "
            "a new value for <name>…' — views/settings/subsystem_view.py "
            "dispatch_edit_setting + edit_enum.build_enum_select_view) — "
            "per-open copy outside the static grammar. The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "description and the select placeholder."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("enum_value",),)),)),
    )


def ai_settings_edit_text_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.settings_edit_text",
        subsystem="ai",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        actions=(
            # G-10: the click issues the shipped TextSettingModal twin;
            # the submit runs the write handler (surface=MODAL).
            PanelActionSpec(
                action_id="edit_value", label="Edit…",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                defer_mode=DeferMode.MODAL, modal=_TEXT_MODAL,
                # the shipped safe_defer(..., ephemeral=True) flag on the
                # submit re-entry (PanelActionSpec.reply_visibility growth,
                # D-0073 — the forms' oracle twins all followed up ephemeral).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("ai.settings_text_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_SETTINGS,
        session_lifecycle=True,
        renderer_override=HandlerRef("ai.render_text_widget"),
        justification=(
            "the shipped free-text edit had NO page: dispatch_edit_setting "
            "answered the select interaction with the TextSettingModal "
            "directly (views/settings/subsystem_view.py) — on this engine "
            "a selector pick is AUTO-deferred before its handler runs, so "
            "a modal can no longer be its first response; the Edit… button "
            "intermediates exactly like the D-0054 confirm surface's "
            "Confirm button (ledgered deviation). The prompt carries the "
            "picked setting's live current/default reprs (the shipped "
            "modal placeholder's readout) — per-open copy outside the "
            "static grammar; the override supplies ONLY the description."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("edit_value",),)),)),
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
    # message attachments (the shipped ``discord.File`` send — the
    # ``!aireview export`` JSON dump rides this seam).
    files = tuple(f for f in (ctx.params or {}).get("_card_files", ())
                  if f is not None)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, attachments=files,
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


async def _render_chooser(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped static chooser footer byte."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed,
                                         footer=_CHOOSER_FOOTER))


async def _render_presets_widget(spec: PanelSpec, ctx) -> object:
    """The shipped NumericPresetsView page: the dispatcher prompt as the
    description, the declared preset roster relabeled onto the slot
    buttons (current value primary, the rest secondary), surplus slots
    dropped."""
    from sb.domain.ai import settings_widgets as widgets
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    key = str((ctx.params or {}).get("setting") or "")
    sspec = widgets.spec_for_key(key)
    if sspec is None or not sspec.presets:   # defensive: never a crash
        return _dc_replace(rendered, embed=_dc_replace(
            rendered.embed, description=f"❌ Unknown setting `ai.{key}`."))
    current = await widgets._current_value(int(ctx.guild_id or 0), sspec)
    # the shipped dispatcher prompt byte (subsystem_view.py
    # dispatch_edit_setting, the numeric_presets branch).
    description = (f"Pick a value for `ai.{key}` "
                   f"(current=`{current!r}`, default=`{sspec.default!r}`):")
    presets = tuple(sspec.presets)
    components = []
    prefix = f"{spec.panel_id}.preset_"
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


async def _render_text_widget(spec: PanelSpec, ctx) -> object:
    """The free-text editor page: the presets-family prompt with the
    picked setting's live current/default reprs (the readout the shipped
    TextSettingModal carried in its placeholder — ModalSpec fields are
    static, so it rides the page instead)."""
    from sb.domain.ai import settings_widgets as widgets
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    key = str((ctx.params or {}).get("setting") or "")
    sspec = widgets.spec_for_key(key)
    if sspec is None:                        # defensive: never a crash
        return _dc_replace(rendered, embed=_dc_replace(
            rendered.embed, description=f"❌ Unknown setting `ai.{key}`."))
    current = await widgets._current_value(int(ctx.guild_id or 0), sspec)
    description = (f"Edit `ai.{key}` "
                   f"(current=`{current!r}`, default=`{sspec.default!r}`) "
                   "— **Edit…** opens the form.")
    return _dc_replace(
        rendered, embed=_dc_replace(rendered.embed, description=description))


async def _render_enum_widget(spec: PanelSpec, ctx) -> object:
    """The shipped enum widget page: the dispatcher prompt as the
    description + the shipped per-setting select placeholder."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    key = str((ctx.params or {}).get("setting") or "")
    description = f"Pick a new value for `ai.{key}`:"
    placeholder = f"Pick a new value for {key}…"
    components = tuple(
        _dc_replace(comp, placeholder=placeholder)
        if comp.custom_id == f"{spec.panel_id}.enum_value" else comp
        for comp in rendered.components)
    return _dc_replace(
        rendered, components=components,
        embed=_dc_replace(rendered.embed, description=description))


async def _render_policy_picker(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped static scope-page footer byte."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed,
                                         footer=_POLICY_PAGE_FOOTER))


async def _render_tools_profile(spec: PanelSpec, ctx) -> object:
    """The tools profile-choice page: the shipped per-open prompt ('Pick
    an orchestration profile for {label}.' — the _ProfileChoiceView
    content byte) + the shipped tools-page footer."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    label = str((ctx.params or {}).get("tools_target_label")
                or "the picked scope")
    description = f"Pick an orchestration profile for {label}."
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, description=description,
                          footer=_POLICY_PAGE_FOOTER))


async def _render_behavior_preset(spec: PanelSpec, ctx) -> object:
    """The shipped build_preset_picker_embed page: the scope_label
    description + one catalog field per preset (name='`{key}` ·
    mode=`{mode}`', value=headline, ≤25 — the shipped _MAX_OPTIONS
    cap)."""
    from sb.domain.ai import behavior_presets as presets
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    scope_label = str((ctx.params or {}).get("behavior_scope_label")
                      or "the picked scope")
    description = (
        f"Selecting a preset binds it to **{scope_label}** and "
        "writes through the existing policy chokepoint. Existing "
        "min_level / cooldown overrides for that scope are "
        "preserved.")
    try:
        rows = await presets.list_behavior_presets()
    except Exception:  # noqa: BLE001 — DB-free replay degrades to no fields
        rows = []
    fields = tuple(
        (f"`{p.key}` · mode=`{p.recommended_mode}`", p.headline, False)
        for p in rows[:25])
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, description=description,
                          fields=fields))


async def _render_policy_edit(spec: PanelSpec, ctx) -> object:
    """The scope edit page: the picked target's prompt (the shipped
    modal-title readout riding the page — the D-0066 class) + the shipped
    scope-page footer."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = ctx.params or {}
    target = str(params.get("policy_target") or "")
    label = str(params.get("policy_target_label") or target)
    scope = ("role" if spec.panel_id == "ai.policy_role_edit"
             else str(params.get("policy_scope") or "channel"))
    subject = f"category **{label}**" if scope == "category" else label
    description = (f"Edit AI policy for {subject} — "
                   "**Edit…** opens the form.")
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, description=description,
                          footer=_POLICY_PAGE_FOOTER))


async def _render_policy_list(spec: PanelSpec, ctx) -> object:
    """The shipped build_list_embed page: total-count description, one
    field per override row, the dynamic page footer, Prev/Next disabled
    at the edges."""
    from sb.domain.ai import policy_widgets as widgets
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    entries = await widgets.collect_entries(int(ctx.guild_id or 0))
    try:
        page = int((ctx.params or {}).get("policy_page") or 1)
    except (TypeError, ValueError):
        page = 1
    fields, page, total_pages = widgets.build_list_fields(entries, page=page)
    description = (f"{len(entries)} total override(s) across this guild "
                   "(channel + category + role).")
    footer = f"Page {page} / {total_pages} · administrator-only"
    components = []
    for comp in rendered.components:
        if comp.custom_id == f"{spec.panel_id}.list_prev":
            comp = _dc_replace(comp, disabled=page <= 1)
        elif comp.custom_id == f"{spec.panel_id}.list_next":
            comp = _dc_replace(comp, disabled=page >= total_pages)
        components.append(comp)
    return _dc_replace(
        rendered, components=tuple(components),
        embed=_dc_replace(rendered.embed, description=description,
                          fields=fields, footer=footer))


async def _enum_edit_options(ctx):
    """The shipped edit_enum option roster: one option per allowed value,
    the current value pre-marked (default=True + the 'current'
    description)."""
    from sb.domain.ai import settings_widgets as widgets

    key = str((ctx.params or {}).get("setting") or "")
    sspec = widgets.spec_for_key(key)
    if sspec is None or not sspec.allowed_values:
        return ()
    current = await widgets._current_value(int(ctx.guild_id or 0), sspec)
    options = []
    for value in sspec.allowed_values:
        label = str(value)[:100]
        is_current = value == current
        options.append({
            "label": label, "value": label,
            "default": is_current,
            "description": "current" if is_current else "",
        })
    return tuple(options)


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------


_SPECS = {
    "ai.hub": ai_hub_spec,
    "ai.card": ai_card_spec,
    "ai.settings": ai_settings_spec,
    "ai.policy_chooser": ai_policy_chooser_spec,
    "ai.behavior_chooser": ai_behavior_chooser_spec,
    "ai.tools_chooser": ai_tools_chooser_spec,
    "ai.settings_edit_presets": ai_settings_edit_presets_spec,
    "ai.settings_edit_enum": ai_settings_edit_enum_spec,
    "ai.settings_edit_text": ai_settings_edit_text_spec,
    # the policy-mutation slice: the shipped scope pickers + edit pages +
    # the paged override list (views/ai/policy/* @7f7628e1).
    "ai.policy_channel_picker": ai_policy_channel_picker_spec,
    "ai.policy_category_picker": ai_policy_category_picker_spec,
    "ai.policy_role_picker": ai_policy_role_picker_spec,
    "ai.policy_preview_picker": ai_policy_preview_picker_spec,
    "ai.policy_scope_edit": ai_policy_scope_edit_spec,
    "ai.policy_role_edit": ai_policy_role_edit_spec,
    "ai.policy_list": ai_policy_list_spec,
    # the behavior-preset slice (D-0071): the shipped scope pickers, the
    # preview reuse and the preset picker (views/ai/behavior/*).
    "ai.behavior_channel_picker": ai_behavior_channel_picker_spec,
    "ai.behavior_category_picker": ai_behavior_category_picker_spec,
    "ai.behavior_preview_picker": ai_behavior_preview_picker_spec,
    "ai.behavior_preset_picker": ai_behavior_preset_picker_spec,
    # the orchestration-mutation slice (D-0072): the shipped tools scope
    # pickers, the step-2 profile choice and the dry-run preview
    # (views/ai/tools/*).
    "ai.tools_guild_picker": ai_tools_guild_picker_spec,
    "ai.tools_channel_picker": ai_tools_channel_picker_spec,
    "ai.tools_category_picker": ai_tools_category_picker_spec,
    "ai.tools_profile_picker": ai_tools_profile_picker_spec,
    "ai.tools_preview_picker": ai_tools_preview_picker_spec,
}

_RENDERERS = {
    "ai.render_hub": _render_hub,
    "ai.render_card": _render_card,
    "ai.render_settings": _render_settings,
    "ai.render_chooser": _render_chooser,
    "ai.render_presets_widget": _render_presets_widget,
    "ai.render_enum_widget": _render_enum_widget,
    "ai.render_text_widget": _render_text_widget,
    "ai.render_policy_picker": _render_policy_picker,
    "ai.render_policy_edit": _render_policy_edit,
    "ai.render_policy_list": _render_policy_list,
    "ai.render_behavior_preset": _render_behavior_preset,
    "ai.render_tools_profile": _render_tools_profile,
}

_PROVIDERS = {
    "ai.settings_fields": _settings_fields,
    "ai.policy_chooser_fields": _policy_chooser_fields,
    "ai.behavior_chooser_fields": _behavior_chooser_fields,
    "ai.tools_chooser_fields": _tools_chooser_fields,
    "ai.enum_edit_options": _enum_edit_options,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for name, fn in _PROVIDERS.items():
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)


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
