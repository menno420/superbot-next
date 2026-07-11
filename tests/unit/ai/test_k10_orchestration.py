"""K10 tool orchestration: catalogue registry, deterministic selection,
profiles + resolver, answer-workflow template."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.ai import orchestration, tools_catalogue
from sb.kernel.ai.contracts import (
    AIAnswerWithEvidence,
    AIScope,
    AIToolMetadata,
    AIToolSpec,
    ToolExclusionReason,
    ToolRequirementMode,
)


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _pristine_registries() -> None:
    tools_catalogue.clear_tools_for_tests()
    orchestration.reset_profiles_for_tests()
    orchestration.reset_profile_key_reader_for_tests()
    orchestration.clear_answer_workflows_for_tests()


@pytest.fixture(autouse=True)
def _pristine_baseline():
    """The dir's ONE sanctioned PRE-leg (the #156 defense): a prior
    suite's Harness boot arms these module-global registries at
    sb.manifest.ai import (the btd6 tool rows, domain profiles, the
    analyze_execute_verify runner), and under non-canonical selection
    orders that armed state breaks this suite's exact-set assertions and
    double-claim guards (the #141 defect family) — so establish the
    pristine baseline BEFORE each test. The AFTER leg — the clear + the
    idempotent ENSURE_REFS re-arm that lets later composition-root
    suites find the world as the boot left it — now lives in
    conftest.py's dir-wide after-only reset."""
    _pristine_registries()


def _tool(name, *, min_scope=AIScope.USER, toolsets=("base",), domain=None):
    return tools_catalogue.RegisteredTool(
        spec=AIToolSpec(name=name, description="d", parameters={}, min_scope=min_scope),
        metadata=AIToolMetadata(
            toolsets=frozenset(toolsets), grounding_domain=domain,
        ),
        owner_subsystem="test",
    )


class TestCatalogueRegistry:
    def test_register_and_derive_grounding(self):
        tools_catalogue.register_tool(_tool("a_lookup", domain="btd6"))
        tools_catalogue.register_tool(_tool("b_meta"))
        assert tools_catalogue.grounding_tool_names("btd6") == frozenset({"a_lookup"})
        assert tools_catalogue.known_toolsets() == frozenset({"base"})

    def test_double_claim_refused(self):
        tools_catalogue.register_tool(_tool("x"))
        with pytest.raises(ValueError):
            tools_catalogue.register_tool(
                _tool("x", toolsets=("other",)),
            )

    def test_scope_rank_total_order(self):
        assert tools_catalogue.scope_allows(AIScope.ADMIN, AIScope.USER)
        assert not tools_catalogue.scope_allows(AIScope.USER, AIScope.ADMIN)
        assert tools_catalogue.scope_allows(AIScope.SYSTEM, AIScope.PLATFORM_OWNER)


class TestSelection:
    def _specs(self):
        tools_catalogue.register_tool(_tool("user_tool"))
        tools_catalogue.register_tool(
            _tool("admin_tool", min_scope=AIScope.ADMIN, toolsets=("sensitive",)),
        )
        tools_catalogue.register_tool(_tool("other_tool", toolsets=("other",)))
        return [t.spec for t in tools_catalogue.registered_tools()]

    def test_scope_only_filter_is_default(self):
        decisions = tools_catalogue.select_tools(self._specs(), scope=AIScope.USER)
        by_name = {d.name: d for d in decisions}
        assert by_name["user_tool"].included
        assert by_name["other_tool"].included
        assert by_name["admin_tool"].reason is ToolExclusionReason.SCOPE_DENIED

    def test_explicit_disable_wins_over_toolset(self):
        decisions = tools_catalogue.select_tools(
            self._specs(),
            scope=AIScope.ADMIN,
            enabled_toolsets=("base", "sensitive"),
            disabled_tools=("user_tool",),
        )
        by_name = {d.name: d for d in decisions}
        assert by_name["user_tool"].reason is ToolExclusionReason.EXPLICITLY_DISABLED
        assert by_name["admin_tool"].included
        assert by_name["other_tool"].reason is ToolExclusionReason.TOOLSET_DISABLED

    def test_policy_never_widens_scope(self):
        decisions = tools_catalogue.select_tools(
            self._specs(),
            scope=AIScope.USER,
            enabled_toolsets=("sensitive",),
        )
        by_name = {d.name: d for d in decisions}
        # scope check precedes the (enabling) toolset filter
        assert by_name["admin_tool"].reason is ToolExclusionReason.SCOPE_DENIED

    def test_empty_toolsets_offers_nothing(self):
        decisions = tools_catalogue.select_tools(
            self._specs(), scope=AIScope.ADMIN, enabled_toolsets=(),
        )
        assert not any(d.included for d in decisions)


class TestProfilesAndResolver:
    def test_default_profile_is_compatible(self):
        decision = run(
            orchestration.resolve_orchestration(
                orchestration.OrchestrationContext(guild_id=1, channel_id=10),
            ),
        )
        assert decision.profile_key == orchestration.DEFAULT_PROFILE_KEY
        assert decision.source == "default"
        assert decision.enabled_toolsets is None
        assert decision.tool_choice.mode is ToolRequirementMode.AUTO
        assert decision.tool_budget.max_hops == 4

    def test_most_specific_key_wins(self):
        async def reader(guild_id, channel_id, category_id):
            return None, "balanced_helper", "compatible_default"

        orchestration.install_profile_key_reader(reader)
        decision = run(
            orchestration.resolve_orchestration(
                orchestration.OrchestrationContext(
                    guild_id=1, channel_id=10, category_id=20,
                ),
            ),
        )
        assert decision.profile_key == "balanced_helper"
        assert decision.source == "category"
        assert decision.tool_budget.max_calls == 4

    def test_unknown_persisted_key_degrades_to_default(self):
        async def reader(guild_id, channel_id, category_id):
            return "removed_preset", None, None

        orchestration.install_profile_key_reader(reader)
        decision = run(
            orchestration.resolve_orchestration(
                orchestration.OrchestrationContext(guild_id=1, channel_id=10),
                dry_run=True,
            ),
        )
        assert decision.profile_key == orchestration.DEFAULT_PROFILE_KEY
        assert decision.source == "default"
        assert any("unknown_profile" in step for step in decision.source_trace)

    def test_reader_fault_degrades(self):
        async def reader(guild_id, channel_id, category_id):
            raise RuntimeError("db down")

        orchestration.install_profile_key_reader(reader)
        decision = run(
            orchestration.resolve_orchestration(
                orchestration.OrchestrationContext(guild_id=1, channel_id=10),
            ),
        )
        assert decision.profile_key == orchestration.DEFAULT_PROFILE_KEY

    def test_domain_profile_registration(self):
        profile = orchestration.OrchestrationProfile(
            key="grounded_facts",
            label="Grounded",
            description="narrowed",
            enabled_toolsets=("btd6_reference",),
            disabled_tools=(),
            tool_choice=orchestration.AIToolChoice(
                mode=ToolRequirementMode.REQUIRED_ANY,
            ),
            tool_budget=orchestration.AIToolBudget(max_hops=2),
            workflow="analyze_execute_verify",
            answer_contract="concise_fact",
        )
        orchestration.register_profile(profile)
        assert orchestration.get_profile("grounded_facts") is profile


class TestAnswerWorkflowTemplate:
    def _answer(self):
        return AIAnswerWithEvidence(
            contract="calculation_explained",
            workflow="analyze_execute_verify",
            intent="round_cash_range",
            status="complete",
            result_text="R1-R10 yields $1,234",
            inclusive_range=True,
            evidence=(),
        )

    def test_unregistered_label_returns_none(self):
        assert run(orchestration.run_answer_workflow("nope", "q")) is None

    def test_registered_runner_dispatch(self):
        answer = self._answer()

        async def runner(question, ctx):
            return answer if "cash" in question else None

        orchestration.register_answer_workflow(
            "analyze_execute_verify", runner, owner_subsystem="btd6",
        )
        assert (
            run(orchestration.run_answer_workflow("analyze_execute_verify", "round cash?"))
            is answer
        )
        assert (
            run(orchestration.run_answer_workflow("analyze_execute_verify", "hello"))
            is None
        )

    def test_faulting_runner_falls_to_model_path(self):
        async def runner(question, ctx):
            raise RuntimeError("calculator broken")

        orchestration.register_answer_workflow(
            "analyze_execute_verify", runner, owner_subsystem="btd6",
        )
        assert (
            run(orchestration.run_answer_workflow("analyze_execute_verify", "q"))
            is None
        )
