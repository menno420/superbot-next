"""Provider-neutral AI contracts (K10) — ported from shipped
``disbot/core/runtime/ai/contracts.py`` @7f7628e1 with ONE deliberate
change: the closed ``AITask`` enum is GONE (B-1 contamination #1). Every
``task`` field is the registered task-id STRING from
:mod:`sb.kernel.ai.tasks`; the gateway admits only registered ids.

Everything else (scopes, denial reasons, tool grammar, budgets, evidence
contracts, request/response shapes) carries the shipped field order and
semantics verbatim so band-7 ports and the eval harness re-bind 1:1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

__all__ = [
    "AIAnswerWithEvidence",
    "AIDiagnosticsSnapshot",
    "AIRequest",
    "AIRequestContext",
    "AIResponse",
    "AIResponseMode",
    "AIScope",
    "AISuggestion",
    "AISuggestionKind",
    "AIToolBudget",
    "AIToolChoice",
    "AIToolMetadata",
    "AIToolSpec",
    "CalculationEvidence",
    "Confidence",
    "PolicyDenialReason",
    "Severity",
    "ToolExclusionReason",
    "ToolRequirementMode",
]


class PolicyDenialReason(str, Enum):
    """Stable reason codes recorded on every ai_decision_audit row.

    Success rows (``decision IN ('allowed','replied')``) use the sentinel
    ``NONE``; denial rows pick the specific cause. Every code is safe to
    expose in admin diagnostics. Values verbatim from shipped source.
    """

    NONE = "none"
    AI_GLOBALLY_DISABLED = "ai_globally_disabled"
    AI_NL_DISABLED_FOR_GUILD = "ai_nl_disabled_for_guild"
    CHANNEL_DISABLED = "channel_disabled"
    CATEGORY_DISABLED = "category_disabled"
    ROLE_DENIED = "role_denied"
    BELOW_MIN_LEVEL = "below_min_level"
    COOLDOWN_ACTIVE = "cooldown_active"
    NO_MENTION_REQUIRED = "no_mention_required"
    NOT_A_QUESTION = "not_a_question"
    NO_ROUTE_MATCHED = "no_route_matched"
    EMPTY_MESSAGE = "empty_message"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    GROUNDING_FAILED = "grounding_failed"
    GUILD_NOT_CONFIGURED = "guild_not_configured"
    # NEW (registry replaces the closed enum): a request naming a task id
    # no band has registered degrades deterministically instead of being
    # unrepresentable.
    TASK_UNREGISTERED = "task_unregistered"


class AIScope(str, Enum):
    """Where an AI request is allowed to operate."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SERVER_OWNER = "server_owner"
    PLATFORM_OWNER = "platform_owner"
    SYSTEM = "system"


class AIResponseMode(str, Enum):
    """Expected response shape."""

    TEXT = "text"
    JSON = "json"
    SUGGESTIONS = "suggestions"


class AISuggestionKind(str, Enum):
    """Kinds of advisory suggestions AI services may produce."""

    EXPLANATION = "explanation"
    SETTING_CHANGE = "setting_change"
    BINDING_CHANGE = "binding_change"
    RESOURCE_PROVISION = "resource_provision"
    DIAGNOSTIC_NEXT_STEP = "diagnostic_next_step"
    HELP_NAVIGATION = "help_navigation"
    MODERATION_REVIEW = "moderation_review"


Confidence = Literal["high", "medium", "low"]
Severity = Literal["info", "warning", "error", "critical"]


@dataclass(frozen=True)
class AIRequestContext:
    """Low-risk metadata attached to an AI request.

    Do not store sensitive values here. Provider keys, raw tokens, and
    private environment values belong outside the request payload.
    ``task`` is a registered task id (:mod:`sb.kernel.ai.tasks`).
    """

    task: str
    scope: AIScope
    guild_id: int | None = None
    actor_id: int | None = None
    channel_id: int | None = None
    correlation_id: str | None = None
    source: str = "unknown"


@dataclass(frozen=True)
class AIToolSpec:
    """Provider-neutral declaration of a read-only tool the model may call.

    Specs are pure data (no handler); the live handler is supplied
    separately to the gateway via ``tool_handlers`` so this contract stays
    a clean, redaction-safe data object. ``parameters`` is a JSON-Schema
    object. ``min_scope`` is the least-privileged :class:`AIScope` allowed
    to be OFFERED this tool.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    min_scope: AIScope = AIScope.USER


class ToolExclusionReason(str, Enum):
    """Stable, deterministic reason a tool was withheld from a request's
    offered set. Authority (``scope_denied``) and runtime availability are
    checked first; toolset / explicit policy may only *narrow* the offered
    set, never widen it."""

    SCOPE_DENIED = "scope_denied"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    TASK_MISMATCH = "task_mismatch"
    TOOLSET_DISABLED = "toolset_disabled"
    EXPLICITLY_DISABLED = "explicitly_disabled"
    BUDGET_DISALLOWED = "budget_disallowed"
    FRESHNESS_DISALLOWED = "freshness_disallowed"


class ToolRequirementMode(str, Enum):
    """How strongly the model must call a tool this turn. Provider-neutral;
    each adapter maps these onto its own ``tool_choice`` semantics.
    ``REQUIRED_GROUP`` is a SuperBot rule: the resolver narrows the
    *offered* tools to the group, the adapter then uses "require any"."""

    NONE = "none"  # no model-visible tools (single-shot answer)
    AUTO = "auto"  # model may call zero or more (the historical default)
    REQUIRED_ANY = "required_any"  # at least one offered tool
    REQUIRED_GROUP = "required_group"  # at least one from a pre-narrowed group
    REQUIRED_TOOL = "required_tool"  # force one named tool


@dataclass(frozen=True)
class AIToolChoice:
    """Provider-neutral tool-choice policy for one request. AUTO reproduces
    the historical behaviour. ``tool_name`` is required for
    ``REQUIRED_TOOL``; ``group_name`` labels a ``REQUIRED_GROUP``."""

    mode: ToolRequirementMode = ToolRequirementMode.AUTO
    tool_name: str | None = None
    group_name: str | None = None


@dataclass(frozen=True)
class AIToolBudget:
    """Per-request bound on the model<->tool loop. Defaults are
    compatibility-preserving: hop-bounded only; ``None`` = no cap. A policy
    may tighten any field; the provider adapters enforce them."""

    max_hops: int = 4
    max_calls: int | None = None
    max_wall_seconds: float | None = None
    max_result_chars: int | None = None


@dataclass(frozen=True)
class AIToolMetadata:
    """Selection/UI metadata for one registered AI tool — the catalogue
    half, kept separate from its provider-facing :class:`AIToolSpec` and
    its live runtime handler. ``min_scope`` on the SPEC stays authoritative
    for authority; policy may only narrow. ``task_affinity`` holds
    registered task-id strings (was ``frozenset[AITask]``)."""

    toolsets: frozenset[str]
    task_affinity: frozenset[str] = frozenset()
    grounding_domain: str | None = None
    capability_tags: frozenset[str] = frozenset()
    cost_class: Literal["cheap", "normal", "expensive"] = "normal"
    freshness: Literal["static", "cached", "live"] = "static"
    parallel_safe: bool = True
    preflight_safe: bool = False
    result_contract: str = ""


@dataclass(frozen=True)
class CalculationEvidence:
    """One deterministic calculator result supporting an AI answer. A
    repository calculator (never the model) produced ``outputs`` from
    ``normalized_inputs`` under ``assumptions``. Answer renderers refer to
    ``evidence_id`` and must not alter the numeric outputs."""

    evidence_id: str
    calculator: str
    calculator_version: str
    normalized_inputs: dict[str, Any]
    assumptions: tuple[str, ...]
    outputs: dict[str, Any]
    warnings: tuple[str, ...] = ()
    data_version: str | None = None


@dataclass(frozen=True)
class AIAnswerWithEvidence:
    """Typed answer-with-evidence contract — the one contract the
    plan→execute→verify workflow emits (Q-0046). ``status`` distinguishes a
    complete answer from a precise *unsupported* refusal; an unsupported
    answer still carries evidence, never a fabricated number.
    ``inclusive_range`` carries the Q-0043 range semantics (ranges count
    BOTH endpoints)."""

    contract: str
    workflow: str
    intent: str
    status: Literal["complete", "unsupported"]
    result_text: str
    inclusive_range: bool
    evidence: tuple[CalculationEvidence, ...]
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AIRequest:
    """Provider-neutral request passed to the AI gateway."""

    context: AIRequestContext
    system_prompt: str
    payload: dict[str, Any]
    mode: AIResponseMode = AIResponseMode.TEXT
    response_schema: dict[str, Any] | None = None
    max_output_tokens: int = 1500
    timeout_seconds: float = 20.0
    tools: tuple[AIToolSpec, ...] = ()
    # Orchestration policy. Defaults reproduce the historical behaviour:
    # AUTO choice + hop-bounded loop. A resolver may set a tighter policy;
    # the provider adapters enforce it. Narrow-only, never widen.
    tool_choice: AIToolChoice = AIToolChoice()
    tool_budget: AIToolBudget = AIToolBudget()


@dataclass(frozen=True)
class AISuggestion:
    """Advisory suggestion returned by an AI service. Suggestions must
    remain advisory until converted into typed operations and validated by
    the deterministic service layer."""

    kind: AISuggestionKind
    title: str
    summary: str
    confidence: Confidence = "medium"
    severity: Severity = "info"
    subsystem: str | None = None
    target: str | None = None
    proposed_value: Any | None = None
    next_command: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    """Provider-neutral response returned by the AI gateway."""

    task: str
    provider: str
    model: str
    text: str | None = None
    data: dict[str, Any] | None = None
    suggestions: tuple[AISuggestion, ...] = ()
    latency_ms: float | None = None
    degraded: bool = False
    fallback_reason: str | None = None


@dataclass(frozen=True)
class AIDiagnosticsSnapshot:
    """Read-only snapshot for the operator ``ai status`` surface."""

    provider_requested: str
    provider_active: str
    model: str
    enabled: bool
    redaction_enabled: bool
    degraded: bool = False
    last_error_type: str | None = None
    last_fallback_reason: str | None = None
    requests_observed: int = 0
    failures_observed: int = 0
