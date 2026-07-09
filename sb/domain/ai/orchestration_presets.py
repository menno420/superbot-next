"""Domain orchestration presets (band 7) — the shipped
``ai_orchestration_presets`` rows the kernel didn't seed
(compatible_default + balanced_helper are kernel seeds; D-0023):
btd6_grounded / btd6_grounded_strict / no_tools, VERBATIM copy +
toolset names."""

from __future__ import annotations

from sb.kernel.ai import orchestration
from sb.kernel.ai.contracts import AIToolBudget, AIToolChoice, ToolRequirementMode

__all__ = ["BTD6_FACTUAL_TOOLSETS", "register_domain_profiles"]

# The shipped toolset vocabulary (ai_tool_catalogue constants verbatim).
TOOLSET_BTD6_REFERENCE = "btd6_reference"
TOOLSET_BTD6_ROUNDS = "btd6_rounds"
TOOLSET_BTD6_COSTS = "btd6_costs"
TOOLSET_BTD6_PARAGON = "btd6_paragon"

BTD6_FACTUAL_TOOLSETS: tuple[str, ...] = (
    TOOLSET_BTD6_REFERENCE,
    TOOLSET_BTD6_ROUNDS,
    TOOLSET_BTD6_COSTS,
    TOOLSET_BTD6_PARAGON,
)


def register_domain_profiles() -> None:
    """Idempotent (register_profile tolerates identical rows)."""
    for profile in (
        orchestration.OrchestrationProfile(
            key="btd6_grounded",
            label="BTD6 grounded",
            description=(
                "Offer only the BTD6 factual toolsets (reference, rounds, "
                "costs, paragon). Automatic choice — the model may answer a "
                "social turn directly without forcing a tool. Best for "
                "BTD6-focused channels."
            ),
            enabled_toolsets=BTD6_FACTUAL_TOOLSETS,
            disabled_tools=(),
            tool_choice=AIToolChoice(mode=ToolRequirementMode.AUTO),
            tool_budget=AIToolBudget(max_hops=3, max_calls=4),
            workflow="analyze_execute_verify",
            answer_contract="concise_fact",
        ),
        orchestration.OrchestrationProfile(
            key="btd6_grounded_strict",
            label="BTD6 grounded (strict)",
            description=(
                "Offer only the BTD6 factual toolsets AND require at least "
                "one of them before answering (a hard grounding guarantee). "
                "Forces a tool on every turn — use for dedicated BTD6 expert "
                "channels, not general chat."
            ),
            enabled_toolsets=BTD6_FACTUAL_TOOLSETS,
            disabled_tools=(),
            tool_choice=AIToolChoice(
                mode=ToolRequirementMode.REQUIRED_GROUP,
                group_name="btd6_grounding",
            ),
            tool_budget=AIToolBudget(max_hops=3, max_calls=4),
            workflow="analyze_execute_verify",
            answer_contract="calculation_explained",
        ),
        orchestration.OrchestrationProfile(
            key="no_tools",
            label="No tools (conversational)",
            description=(
                "Offer no tools at all — a single-shot conversational "
                "answer. The model must not claim live, current, or private "
                "facts. Useful for social channels or strict cost control."
            ),
            enabled_toolsets=(),
            disabled_tools=(),
            tool_choice=AIToolChoice(mode=ToolRequirementMode.NONE),
            tool_budget=AIToolBudget(),
            workflow="direct_answer",
            answer_contract="concise_fact",
        ),
    ):
        try:
            orchestration.register_profile(profile)
        except ValueError:
            pass  # differing duplicate would raise in tests; identical is fine
