"""Shared fixtures for the K10 AI-kernel suites."""

from __future__ import annotations

import pytest

from sb.kernel.ai import flags, routing, tasks
from sb.kernel.ai.diagnostics import reset_default_collector
from sb.kernel.ai.gateway import reset_default_gateway, reset_guild_policy_reader
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
