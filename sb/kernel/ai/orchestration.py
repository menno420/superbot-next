"""Tool-orchestration profiles + resolver + the plan→execute→verify
workflow registry (K10).

Ported from shipped ``disbot/services/ai_orchestration_presets.py`` +
``ai_orchestration_policy.py`` with the domain couplings cut:

* built-in presets stay CODE (immutable through guild mutation paths); a
  scope stores just a profile KEY. The shipped BTD6-narrowed presets move
  to band 7 via :func:`register_profile`; the kernel ships the
  compatibility default + the generic ``balanced_helper``;
* the per-guild profile-key read arrives through
  :func:`install_profile_key_reader` (settings band installs it);
* the ``workflow`` label dispatches through the ANSWER-WORKFLOW REGISTRY
  (:func:`register_answer_workflow`): the shipped deterministic
  round-cash plan→execute→verify workflow re-homes at band 7 as a
  registered runner emitting :class:`AIAnswerWithEvidence` — the template
  (label → runner(question, ctx) → typed evidence answer | None) is the
  K10 machinery.

Invariants carried verbatim: a profile only ever NARROWS what scope
already permits; an unknown persisted key degrades to the default (never
raises — this resolver sits on the live reply path); this resolver governs
HOW tools are offered, never WHETHER the bot replies (that is policy.py).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sb.kernel.ai.contracts import (
    AIAnswerWithEvidence,
    AIToolBudget,
    AIToolChoice,
    ToolRequirementMode,
)

__all__ = [
    "DEFAULT_PROFILE_KEY",
    "OrchestrationContext",
    "OrchestrationDecision",
    "OrchestrationProfile",
    "clear_answer_workflows_for_tests",
    "get_profile",
    "install_profile_key_reader",
    "register_answer_workflow",
    "register_profile",
    "registered_profiles",
    "reset_profiles_for_tests",
    "resolve_orchestration",
    "run_answer_workflow",
]

logger = logging.getLogger("sb.kernel.ai.orchestration")


@dataclass(frozen=True)
class OrchestrationProfile:
    """A named, immutable orchestration preset — the resolved tool policy.

    ``enabled_toolsets``: None = no restriction (offer every scope-allowed
    tool, the historical behaviour); a tuple narrows; () offers none.
    ``workflow`` selects the registered deterministic answer workflow;
    ``answer_contract`` is the declared answer-shape label.
    """

    key: str
    label: str
    description: str
    enabled_toolsets: tuple[str, ...] | None
    disabled_tools: tuple[str, ...]
    tool_choice: AIToolChoice
    tool_budget: AIToolBudget
    workflow: str
    answer_contract: str


DEFAULT_PROFILE_KEY = "compatible_default"

_PROFILES: dict[str, OrchestrationProfile] = {}


def register_profile(profile: OrchestrationProfile) -> OrchestrationProfile:
    prior = _PROFILES.get(profile.key)
    if prior is not None and prior != profile:
        raise ValueError(f"orchestration profile {profile.key!r} registered twice")
    _PROFILES[profile.key] = profile
    return profile


def _seed_kernel_profiles() -> None:
    register_profile(
        OrchestrationProfile(
            key=DEFAULT_PROFILE_KEY,
            label="Compatible (shipped behaviour)",
            description=(
                "Offer every tool the caller's scope allows, with automatic "
                "tool choice and the historical hop-bounded budget. The "
                "implicit default for any scope with no profile set."
            ),
            enabled_toolsets=None,
            disabled_tools=(),
            tool_choice=AIToolChoice(mode=ToolRequirementMode.AUTO),
            tool_budget=AIToolBudget(),
            workflow="analyze_execute_verify",
            answer_contract="concise_fact",
        ),
    )
    register_profile(
        OrchestrationProfile(
            key="balanced_helper",
            label="Balanced helper",
            description=(
                "General-purpose. Every scope-allowed tool with automatic "
                "choice, loop capped (3 hops / 4 tool calls) to keep trivial "
                "questions cheap."
            ),
            enabled_toolsets=None,
            disabled_tools=(),
            tool_choice=AIToolChoice(mode=ToolRequirementMode.AUTO),
            tool_budget=AIToolBudget(max_hops=3, max_calls=4),
            workflow="analyze_execute_verify",
            answer_contract="concise_fact",
        ),
    )


_seed_kernel_profiles()


def get_profile(key: str) -> OrchestrationProfile | None:
    return _PROFILES.get(key)


def registered_profiles() -> tuple[OrchestrationProfile, ...]:
    return tuple(_PROFILES[k] for k in sorted(_PROFILES))


def reset_profiles_for_tests() -> None:
    _PROFILES.clear()
    _seed_kernel_profiles()


# ---------------------------------------------------------------------------
# Installable per-scope profile-key reader.
# reader(guild_id, channel_id, category_id) -> most-specific key or None per
# scope, returned as (channel_key, category_key, guild_key) — the resolver
# applies most-specific-wins so admin previews can show "why".
# ---------------------------------------------------------------------------

ProfileKeyReader = Callable[
    [int, int, int | None],
    Awaitable[tuple[str | None, str | None, str | None]],
]

_key_reader: ProfileKeyReader | None = None


def install_profile_key_reader(reader: ProfileKeyReader) -> None:
    global _key_reader
    _key_reader = reader


def reset_profile_key_reader_for_tests() -> None:
    global _key_reader
    _key_reader = None


@dataclass(frozen=True)
class OrchestrationContext:
    guild_id: int
    channel_id: int
    category_id: int | None = None


@dataclass(frozen=True)
class OrchestrationDecision:
    """The resolved orchestration policy for one request (shipped shape).
    ``source_trace`` fills only under ``dry_run=True``."""

    profile_key: str
    source: str  # "channel" | "category" | "guild" | "default"
    enabled_toolsets: tuple[str, ...] | None
    disabled_tools: tuple[str, ...]
    tool_choice: AIToolChoice
    tool_budget: AIToolBudget
    workflow: str
    answer_contract: str
    source_trace: tuple[str, ...] = ()


async def resolve_orchestration(
    ctx: OrchestrationContext,
    *,
    dry_run: bool = False,
) -> OrchestrationDecision:
    """Resolve the orchestration profile for ``ctx``: most-specific
    non-NULL key wins (channel → category → guild → default). Pure read;
    read faults degrade to the compatible default (live reply path)."""
    trace: list[str] | None = [] if dry_run else None
    chan_key = cat_key = guild_key = None
    if _key_reader is not None:
        try:
            chan_key, cat_key, guild_key = await _key_reader(
                ctx.guild_id,
                ctx.channel_id,
                ctx.category_id,
            )
        except Exception:  # noqa: BLE001 — never break the reply on a read fault
            logger.debug("ai orchestration: key reader failed", exc_info=True)

    if chan_key:
        key, source = chan_key, "channel"
    elif cat_key:
        key, source = cat_key, "category"
    elif guild_key:
        key, source = guild_key, "guild"
    else:
        key, source = DEFAULT_PROFILE_KEY, "default"
    if trace is not None:
        trace.append(f"selected: key={key} source={source}")

    profile = _PROFILES.get(key)
    if profile is None:
        # A key persisted by an older build whose preset was removed:
        # degrade to the compatible default, never raise.
        profile = _PROFILES[DEFAULT_PROFILE_KEY]
        if trace is not None:
            trace.append(
                f"unknown_profile: {key!r} not registered → {profile.key} (default)",
            )
        source = "default"
        key = profile.key

    if trace is not None:
        toolsets = (
            "all"
            if profile.enabled_toolsets is None
            else (",".join(profile.enabled_toolsets) or "none")
        )
        trace.append(
            f"resolved: profile={key} source={source} toolsets={toolsets} "
            f"tool_choice={profile.tool_choice.mode.value} "
            f"budget(hops={profile.tool_budget.max_hops},"
            f"calls={profile.tool_budget.max_calls})",
        )

    return OrchestrationDecision(
        profile_key=key,
        source=source,
        enabled_toolsets=profile.enabled_toolsets,
        disabled_tools=profile.disabled_tools,
        tool_choice=profile.tool_choice,
        tool_budget=profile.tool_budget,
        workflow=profile.workflow,
        answer_contract=profile.answer_contract,
        source_trace=tuple(trace or ()),
    )


# ---------------------------------------------------------------------------
# Answer-workflow registry — the plan→execute→verify TEMPLATE. A runner
# recognises its question shape and returns a typed AIAnswerWithEvidence
# (deterministic repository calculators, never model arithmetic), or None
# to fall through to the normal model path. The shipped round-cash MVP
# re-homes at band 7 as the first registered runner (Q-0046/Q-0048).
# ---------------------------------------------------------------------------

WorkflowRunner = Callable[[str, object], Awaitable[AIAnswerWithEvidence | None]]

_WORKFLOWS: dict[str, tuple[str, WorkflowRunner]] = {}


def register_answer_workflow(
    label: str,
    runner: WorkflowRunner,
    *,
    owner_subsystem: str,
) -> None:
    prior = _WORKFLOWS.get(label)
    if prior is not None and prior != (owner_subsystem, runner):
        raise ValueError(
            f"answer workflow {label!r} already registered by {prior[0]!r}",
        )
    _WORKFLOWS[label] = (owner_subsystem, runner)


def clear_answer_workflows_for_tests() -> None:
    _WORKFLOWS.clear()


async def run_answer_workflow(
    label: str,
    question: str,
    ctx: object = None,
) -> AIAnswerWithEvidence | None:
    """Run the registered workflow for ``label`` (None when unregistered,
    unmatched, or faulting — the model path continues; never raises)."""
    entry = _WORKFLOWS.get(label)
    if entry is None:
        return None
    owner, runner = entry
    try:
        return await runner(question, ctx)
    except Exception:  # noqa: BLE001 — a workflow fault falls to the model path
        logger.warning(
            "ai orchestration: workflow %s (owner %s) raised",
            label,
            owner,
            exc_info=True,
        )
        return None
