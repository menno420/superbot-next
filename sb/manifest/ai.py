"""AI subsystem manifest (band 7, final slice) — the operator surface
of K10: the shipped !ai group (status/readiness/settings/policy/
diagnostics/providers/routing/why-no-response/forget/support-report) +
!aimenu, the shipped !aireview group (channel/off/list/export/resolve +
the preset add/from/list/remove family), the ai_review_log +
ai_answer_presets stores (migration 0024), and the DECLARED ai.*
SettingSpecs (the band-1/band-7 boundary, D-0022 note 2: band 1 built
the fail-closed readers over these keys; THIS manifest declares them —
legacy settings_keys verbatim from the shipped utils.settings_keys.ai
vocabulary carried in sb/domain/settings/keys.py).

Registrations at import + ENSURE_REFS: the domain orchestration
profiles, the round-cash answer workflow, the BTD6 factual tool rows,
and install_ai_platform() (guild-policy overlay + preset lookup +
band-1 readers)."""

from __future__ import annotations

from sb.domain.ai import behavior_widgets as _behavior_widgets
from sb.domain.ai import orchestration_presets as _presets
from sb.domain.ai import orchestration_widgets as _orchestration_widgets
from sb.domain.ai import panels as _panels
from sb.domain.ai import policy_widgets as _policy_widgets
from sb.domain.ai import readers as _readers
from sb.domain.ai import review as _review
from sb.domain.ai import round_cash as _round_cash
from sb.domain.ai import service as _service
from sb.domain.ai import settings_widgets as _widgets
from sb.domain.ai import tools as _tools
from sb.domain.ai.ops import register_ops
from sb.domain.ai.orchestration_ops import (
    EVT_ORCH_CATEGORY_CHANGED,
    EVT_ORCH_CHANNEL_CHANGED,
    EVT_ORCH_GUILD_CHANGED,
    register_orchestration_ops,
)
from sb.domain.ai.policy_ops import (
    EVT_POLICY_CATEGORY_CHANGED,
    EVT_POLICY_CHANNEL_CHANGED,
    EVT_POLICY_ROLE_CHANGED,
)
from sb.domain.ai.policy_ops import register_policy_ops
from sb.domain.ai.policy_store import (
    AI_CATEGORY_POLICY_STORE,
    AI_CHANNEL_POLICY_STORE,
    AI_INSTRUCTION_PROFILE_STORE,
    AI_ROLE_POLICY_STORE,
)
from sb.domain.ai.store import AI_ANSWER_PRESETS_STORE, AI_REVIEW_LOG_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import (
    DeliveryClass,
    EventSpec,
    FieldSpec,
    register_event_specs,
)
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.domain.ai.settings_schema import AI_SETTINGS_FACETS

_SETTINGS = AI_SETTINGS_FACETS


def _policy_event(name: str) -> EventSpec:
    """One shipped ai.policy.*_changed advisory (services/
    ai_policy_mutation._emit kwargs verbatim: guild_id + mutation_id;
    best-effort AFTER the committed write, subscriber-less by design —
    the shipped bus rows had none either)."""
    return EventSpec(
        name=name,
        payload_schema=(
            FieldSpec("guild_id", "int"),
            FieldSpec("mutation_id", "str", required=False),
        ),
        owner_subsystem="ai",
        delivery=DeliveryClass.BEST_EFFORT,
    )


AI_POLICY_EVENTS = (
    _policy_event(EVT_POLICY_CHANNEL_CHANGED),
    _policy_event(EVT_POLICY_CATEGORY_CHANGED),
    _policy_event(EVT_POLICY_ROLE_CHANGED),
)

#: the shipped ai.orchestration.*_changed advisories carry the SAME emit
#: kwargs (events_catalogue.py: "Payload: guild_id, mutation_id. Same
#: swallow-on-subscriber-failure contract as ai.policy.*") — the
#: orchestration-mutation slice, D-0072.
AI_ORCHESTRATION_EVENTS = (
    _policy_event(EVT_ORCH_GUILD_CHANGED),
    _policy_event(EVT_ORCH_CHANNEL_CHANGED),
    _policy_event(EVT_ORCH_CATEGORY_CHANGED),
)


def _ai(name: str, ref: str, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="ai",
                       route=HandlerRef(ref), audience_tier="staff",
                       capability="ai", summary=summary,
                       usage=f"!ai {name}")


def _rev(name: str, ref: str, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="aireview",
                       route=HandlerRef(ref), audience_tier="staff",
                       capability="ai", summary=summary,
                       usage=f"!aireview {name}")


MANIFEST = SubsystemManifest(
    key="ai",
    version=1,
    commands=(
        # the shipped bare `!ai` opened the AI Platform panel (ai_cog
        # ai_group invoke_without_command → build_ai_panel_embed +
        # AIPanelView) — goldens/ai/sweep_ai pins the panel bytes.
        CommandSpec(name="ai", kind=CommandKind.PREFIX,
                    route=PanelRef("ai.hub"),
                    audience_tier="staff", capability="ai",
                    summary="AI platform operator views.",
                    usage="!ai <status|readiness|settings|policy|"
                          "diagnostics|providers|routing|why-no-response|"
                          "forget|support-report>"),
        _ai("status", "ai.status_view", "Gateway status summary."),
        _ai("readiness", "ai.readiness_view",
            "Task/verifier/eval-suite readiness."),
        _ai("settings", "ai.settings_view",
            "Where the declared ai.* settings live."),
        _ai("policy", "ai.policy_view",
            "The resolved NL policy for this server."),
        _ai("diagnostics", "ai.diagnostics_view",
            "K10 diagnostics collector snapshot."),
        _ai("providers", "ai.providers_view",
            "Provider adapters + arm-up state."),
        _ai("routing", "ai.routing_view",
            "Per-task model routing (K10(b) tables)."),
        _ai("why-no-response", "ai.why_view",
            "Recent NL decisions for this server."),
        _ai("forget", "ai.forget_view",
            "Clear in-process conversation memory + throttles."),
        _ai("support-report", "ai.support_report_view",
            "One-shot AI support summary."),
        CommandSpec(name="aimenu", kind=CommandKind.PREFIX,
                    route=PanelRef("ai.hub"), audience_tier="staff",
                    capability="ai",
                    summary="Open the AI platform panel.",
                    usage="!aimenu"),
        # the shipped `/aimenu` slash twin — the SAME panel, ephemeral via
        # the panel's INVOKER audience (goldens/ai/sweep_slash_aimenu pins
        # the type-4 + flags 64; the /pm precedent). The grouped `/ai …`
        # app commands never resolved in the capture harness (their
        # goldens are empty), so only the top-level twin lands.
        CommandSpec(name="aimenu", kind=CommandKind.SLASH,
                    route=PanelRef("ai.hub"), audience_tier="staff",
                    capability="ai",
                    summary="Open the AI Platform panel.",
                    usage="/aimenu"),
        CommandSpec(name="aireview", kind=CommandKind.PREFIX,
                    route=HandlerRef("ai.review_usage_view"),
                    audience_tier="staff", capability="ai",
                    summary="The AI answer review loop.",
                    usage="!aireview <list|resolve|export|channel|off|"
                          "preset>"),
        _rev("list", "ai.review_list_view",
             "Recent review-log entries (optionally by kind)."),
        _rev("resolve", "ai.review_resolve_route",
             "Mark a review entry reviewed."),
        _rev("export", "ai.review_export_view",
             "Export the unreviewed backlog as a JSON file."),
        _rev("channel", "ai.review_channel_route",
             "Set the review feed channel."),
        _rev("off", "ai.review_off_route",
             "Clear the review feed channel (entries still recorded)."),
        CommandSpec(name="preset", kind=CommandKind.PREFIX,
                    group="aireview",
                    route=HandlerRef("ai.preset_usage_view"),
                    audience_tier="staff", capability="ai",
                    summary="Vetted answer presets (served with zero "
                            "model call).",
                    usage="!aireview preset <add|from|list|remove>"),
        CommandSpec(name="add", kind=CommandKind.PREFIX,
                    group="aireview.preset",
                    route=HandlerRef("ai.preset_add_route"),
                    audience_tier="staff", capability="ai",
                    summary="Store a vetted answer for an exact question.",
                    usage='!aireview preset add "<question>" <answer>'),
        CommandSpec(name="from", kind=CommandKind.PREFIX,
                    group="aireview.preset",
                    route=HandlerRef("ai.preset_from_route"),
                    audience_tier="staff", capability="ai",
                    summary="Vet a review-log entry's question with an "
                            "answer.",
                    usage="!aireview preset from <entry_id> <answer…>"),
        CommandSpec(name="list", kind=CommandKind.PREFIX,
                    group="aireview.preset",
                    route=HandlerRef("ai.preset_list_view"),
                    audience_tier="staff", capability="ai",
                    summary="List stored presets.",
                    usage="!aireview preset list"),
        CommandSpec(name="remove", kind=CommandKind.PREFIX,
                    group="aireview.preset",
                    route=HandlerRef("ai.preset_remove_route"),
                    audience_tier="staff", capability="ai",
                    summary="Remove a stored preset by id.",
                    usage="!aireview preset remove <id>"),
    ),
    panels=(_panels.ai_hub_spec(), _panels.ai_settings_spec(),
            _panels.ai_card_spec(),
            # the shipped chooser PAGES + the S6/S7 edit widget pages
            # (the settings-mutation slice — clicks are golden-unpinned).
            _panels.ai_policy_chooser_spec(),
            _panels.ai_behavior_chooser_spec(),
            _panels.ai_tools_chooser_spec(),
            _panels.ai_settings_edit_presets_spec(),
            _panels.ai_settings_edit_enum_spec(),
            # the free-text editor page (the modal-arming slice — its
            # Edit… button issues the G-10 TextSettingModal twin).
            _panels.ai_settings_edit_text_spec(),
            # the policy-mutation slice: the shipped scope pickers, the
            # shared/role edit pages, and the paged override list.
            _panels.ai_policy_channel_picker_spec(),
            _panels.ai_policy_category_picker_spec(),
            _panels.ai_policy_role_picker_spec(),
            _panels.ai_policy_preview_picker_spec(),
            _panels.ai_policy_scope_edit_spec(),
            _panels.ai_policy_role_edit_spec(),
            _panels.ai_policy_list_spec(),
            # the behavior-preset slice (D-0071): the shipped behavior
            # scope pickers, the preview reuse and the preset picker.
            _panels.ai_behavior_channel_picker_spec(),
            _panels.ai_behavior_category_picker_spec(),
            _panels.ai_behavior_preview_picker_spec(),
            _panels.ai_behavior_preset_picker_spec(),
            # the orchestration-mutation slice (D-0072): the shipped
            # tools scope pickers, the step-2 profile choice and the
            # dry-run preview.
            _panels.ai_tools_guild_picker_spec(),
            _panels.ai_tools_channel_picker_spec(),
            _panels.ai_tools_category_picker_spec(),
            _panels.ai_tools_profile_picker_spec(),
            _panels.ai_tools_preview_picker_spec()),
    settings=_SETTINGS,
    stores=(AI_REVIEW_LOG_STORE, AI_ANSWER_PRESETS_STORE,
            AI_CHANNEL_POLICY_STORE, AI_CATEGORY_POLICY_STORE,
            AI_ROLE_POLICY_STORE, AI_INSTRUCTION_PROFILE_STORE),
    events=AI_POLICY_EVENTS + AI_ORCHESTRATION_EVENTS,
    capabilities=(),
)

register_ops()
register_policy_ops()
register_orchestration_ops()
register_event_specs(AI_POLICY_EVENTS + AI_ORCHESTRATION_EVENTS)
_presets.register_domain_profiles()
_round_cash.register_round_cash_workflow()
_tools.register_btd6_tools()


def _ensure_refs() -> None:
    from sb.domain.ai import ops as _ops_mod
    from sb.domain.ai import orchestration_ops as _orch_ops_mod
    from sb.domain.ai import policy_ops as _policy_ops_mod
    from sb.domain.ai import policy_store as _policy_store_mod
    from sb.domain.ai import store as _store

    _store.ensure_refs()
    _policy_store_mod.ensure_policy_store_refs()
    _ops_mod.ensure_ops_refs()
    _policy_ops_mod.ensure_policy_ops_refs()
    _orch_ops_mod.ensure_orchestration_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    _widgets.ensure_widget_refs()
    _policy_widgets.ensure_policy_widget_refs()
    _behavior_widgets.ensure_behavior_widget_refs()
    _orchestration_widgets.ensure_orchestration_widget_refs()
    register_ops()
    register_policy_ops()
    register_orchestration_ops()
    register_event_specs(AI_POLICY_EVENTS + AI_ORCHESTRATION_EVENTS)
    _presets.register_domain_profiles()
    _round_cash.register_round_cash_workflow()
    _tools.register_btd6_tools()
    _readers.install_ai_platform()
    _review.register_review_listeners()


ENSURE_REFS = _ensure_refs
