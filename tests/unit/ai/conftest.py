"""Shared fixtures for the K10 AI-kernel suites.

ONE dir-wide AFTER-ONLY reset (the band-7 hygiene item; the band-6/7
per-suite idiom, consolidated): every K10 module-global registry an ai
suite can touch is cleared AFTER each test — never before — so a test
cleans up its own mutations instead of masking a neighbour's leak. The
single sanctioned exception is test_k10_orchestration.py's slim
pristine-baseline PRE-leg (the #156 defense against a prior suite's
Harness boot arming the catalogue at ``sb.manifest.ai`` import under
non-canonical selection orders); its after-leg lives HERE.

Because the manifest module stays cached, its import-time registration
can never re-fire: after the final clear the fixture re-arms the
manifest's idempotent ``ENSURE_REFS`` hook (when the module is already
imported) so later-listed composition-root suites find the world as the
boot left it — then resets the kernel plumbing (flags / gateway /
collector / policy reader) that must END un-armed either way.
"""

from __future__ import annotations

import sys

import pytest

from sb.kernel.ai import (
    conversation,
    evals,
    feature_facts,
    flags,
    instructions,
    memory,
    nl_engine,
    orchestration,
    policy,
    router,
    routing,
    tasks,
    tools_catalogue,
)
from sb.kernel.ai.diagnostics import reset_default_collector
from sb.kernel.ai.gateway import reset_default_gateway, reset_guild_policy_reader
from sb.kernel.ai.grounding import absence_guard, verify
from sb.kernel.config import preflight

BASE_ENV = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "x",
    "DATABASE_URL": "postgresql://u@localhost/db",
    "SB_DATA_PLANE": "test",
    "SB_TEST_DB_HOSTS": "localhost",
}


def make_config(**overrides: str):
    env = dict(BASE_ENV)
    env.update({k: v for k, v in overrides.items()})
    return preflight(env)


@pytest.fixture(autouse=True)
def _reset_ai_state():
    yield
    # the K10 registries the suites register into
    tools_catalogue.clear_tools_for_tests()
    orchestration.reset_profiles_for_tests()
    orchestration.reset_profile_key_reader_for_tests()
    orchestration.clear_answer_workflows_for_tests()
    verify.clear_verifiers_for_tests()
    absence_guard.clear_attributes_for_tests()
    policy.reset_policy_for_tests()
    conversation.reset_conversation_for_tests()
    router.clear_probes_for_tests()
    memory.reset_memory_ports_for_tests()
    instructions.clear_task_contracts_for_tests()
    instructions.reset_profile_reader_for_tests()
    feature_facts.clear_gatherers_for_tests()
    nl_engine.reset_nl_engine_for_tests()
    evals.clear_suites_for_tests()
    # re-arm the cached manifest's idempotent hook (docstring above)
    manifest = sys.modules.get("sb.manifest.ai")
    if manifest is not None:
        manifest.ENSURE_REFS()
    # kernel plumbing last — these end un-armed even after a re-arm
    flags.reset_flags_for_tests()
    routing.clear_overrides()
    tasks.clear_tasks_for_tests()
    reset_default_gateway()
    reset_default_collector()
    reset_guild_policy_reader()


@pytest.fixture
def ai_on_config():
    """A Config with the AI platform enabled (deterministic default)."""
    return make_config(AI_ENABLED="1")
