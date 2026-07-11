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

from sb.domain.ai import orchestration_presets as _presets
from sb.domain.ai import panels as _panels
from sb.domain.ai import readers as _readers
from sb.domain.ai import round_cash as _round_cash
from sb.domain.ai import service as _service
from sb.domain.ai import tools as _tools
from sb.domain.ai.ops import register_ops
from sb.domain.ai.store import AI_ANSWER_PRESETS_STORE, AI_REVIEW_LOG_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.domain.ai.settings_schema import AI_SETTINGS_FACETS

_SETTINGS = AI_SETTINGS_FACETS


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
             "Export the unreviewed backlog."),
        _rev("channel", "ai.review_channel_view",
             "Where the review feed channel is configured."),
        _rev("off", "ai.review_channel_view",
             "Turn the review feed off (ai.review_channel = 0)."),
        CommandSpec(name="preset", kind=CommandKind.PREFIX,
                    group="aireview",
                    route=HandlerRef("ai.preset_list_view"),
                    audience_tier="staff", capability="ai",
                    summary="Vetted answer presets (served with zero "
                            "model call).",
                    usage="!aireview preset <add|from|list|remove>"),
        CommandSpec(name="add", kind=CommandKind.PREFIX,
                    group="aireview.preset",
                    route=HandlerRef("ai.preset_add_route"),
                    audience_tier="staff", capability="ai",
                    summary="Store a vetted answer: question | answer.",
                    usage="!aireview preset add <q> | <a>"),
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
                    summary="Remove a stored preset.",
                    usage="!aireview preset remove <question>"),
    ),
    panels=(_panels.ai_hub_spec(), _panels.ai_settings_spec(),
            _panels.ai_card_spec()),
    settings=_SETTINGS,
    stores=(AI_REVIEW_LOG_STORE, AI_ANSWER_PRESETS_STORE),
    events=(),
    capabilities=(),
)

register_ops()
_presets.register_domain_profiles()
_round_cash.register_round_cash_workflow()
_tools.register_btd6_tools()


def _ensure_refs() -> None:
    from sb.domain.ai import ops as _ops_mod
    from sb.domain.ai import store as _store

    _store.ensure_refs()
    _ops_mod.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    register_ops()
    _presets.register_domain_profiles()
    _round_cash.register_round_cash_workflow()
    _tools.register_btd6_tools()
    _readers.install_ai_platform()


ENSURE_REFS = _ensure_refs
