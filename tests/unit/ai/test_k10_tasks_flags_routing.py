"""K10 task registry + flags + routing contracts."""

from __future__ import annotations

import pytest

from sb.kernel.ai import flags, routing, tasks
from tests.unit.ai.conftest import make_config


class TestTaskRegistry:
    def test_kernel_seed_registered(self):
        assert tasks.task_registered("general.nl_answer")
        spec = tasks.require_task("general.nl_answer")
        assert spec.owner_subsystem == "kernel"

    def test_legacy_ids_frozen_verbatim(self):
        # The 17 shipped AITask values, byte-stable (compat constraint).
        assert len(tasks.LEGACY_TASK_IDS) == 17
        assert "btd6.answer" in tasks.LEGACY_TASK_IDS
        assert "video.qa" in tasks.LEGACY_TASK_IDS

    def test_domain_registration_of_legacy_id_verbatim(self):
        spec = tasks.register_task(
            tasks.AITaskSpec(task_id="btd6.answer", owner_subsystem="btd6"),
        )
        assert tasks.get_task("btd6.answer") is spec

    def test_near_miss_of_legacy_id_refused(self):
        with pytest.raises(tasks.TaskIdInvalid):
            tasks.register_task(
                tasks.AITaskSpec(task_id="btd6.answers", owner_subsystem="x"),
            )

    def test_malformed_id_refused(self):
        for bad in ("BTD6.Answer", "noname", "a.", ".a", "a b.c"):
            with pytest.raises(tasks.TaskIdInvalid):
                tasks.register_task(
                    tasks.AITaskSpec(task_id=bad, owner_subsystem="x"),
                )

    def test_collision_refused_idempotent_ok(self):
        spec = tasks.AITaskSpec(task_id="mydomain.answer", owner_subsystem="mine")
        tasks.register_task(spec)
        tasks.register_task(spec)  # identical re-registration is fine
        with pytest.raises(tasks.TaskCollision):
            tasks.register_task(
                tasks.AITaskSpec(task_id="mydomain.answer", owner_subsystem="other"),
            )


class TestFlags:
    def test_fail_closed_without_install(self):
        flags.reset_flags_for_tests()
        assert flags.ai_enabled() is False
        assert flags.task_enabled("general.nl_answer") is False
        assert flags.ai_tools_enabled() is False
        assert flags.default_provider() == "deterministic"

    def test_global_gate_and_task_kill_switch(self):
        flags.install_ai_config(
            make_config(AI_ENABLED="1", AI_TASKS_DISABLED="btd6.answer"),
        )
        assert flags.ai_enabled() is True
        assert flags.task_enabled("general.nl_answer") is True
        assert flags.task_enabled("btd6.answer") is False

    def test_tools_layer_under_global(self):
        flags.install_ai_config(make_config(AI_TOOLS_ENABLED="1"))
        assert flags.ai_tools_enabled() is False  # AI_ENABLED still off
        flags.install_ai_config(make_config(AI_ENABLED="1", AI_TOOLS_ENABLED="1"))
        assert flags.ai_tools_enabled() is True
        assert flags.server_member_lookup_enabled() is False

    def test_api_key_from_config(self):
        flags.install_ai_config(make_config(ANTHROPIC_API_KEY="sk-test-abc"))
        assert flags.api_key_for("anthropic") == "sk-test-abc"
        assert flags.api_key_for("openai") == ""
        assert flags.api_key_for("deterministic") == ""

    def test_task_routing_entries_parse_and_skip_malformed(self):
        flags.install_ai_config(
            make_config(
                AI_TASK_ROUTING=(
                    "general.nl_answer=anthropic:claude-haiku-4-5,broken,x="
                ),
            ),
        )
        entries = flags.task_routing_entries()
        assert entries == {"general.nl_answer": "anthropic:claude-haiku-4-5"}


class TestRouting:
    def test_default_resolution_deterministic(self):
        target = routing.resolve("general.nl_answer")
        assert target.provider == "deterministic"

    def test_anthropic_model_tables_k10b_ruled_values(self):
        # OWNER RULING K10(b) (PR #30): bias hard toward Haiku; Sonnet is
        # reserved for the deeper-reasoning trio (D-0033).
        assert (
            routing.default_model_for("anthropic", "general.nl_answer")
            == "claude-haiku-4-5"
        )
        assert (
            routing.default_model_for("anthropic", "logs.triage")
            == "claude-haiku-4-5"          # ruled down from shipped Sonnet
        )
        assert (
            routing.default_model_for("anthropic", "settings.propose")
            == "claude-sonnet-4-6"         # the reserved deeper-reasoning set
        )
        assert (
            routing.default_model_for("anthropic", "moderation.assist")
            == "claude-sonnet-4-6"
        )
        assert routing.default_model_for("openai", "logs.triage") == "gpt-4o-mini"
        # Unknown task falls to the provider fallback model — Haiku per K10(b).
        assert (
            routing.default_model_for("anthropic", "newdomain.answer")
            == "claude-haiku-4-5"
        )

    def test_config_routing_entry_wins_over_default(self):
        flags.install_ai_config(
            make_config(
                AI_ENABLED="1",
                AI_TASK_ROUTING="general.nl_answer=openai:gpt-4o-mini",
            ),
        )
        target = routing.resolve("general.nl_answer")
        assert (target.provider, target.model) == ("openai", "gpt-4o-mini")

    def test_config_entry_cross_family_model_corrected(self):
        flags.install_ai_config(
            make_config(
                AI_ENABLED="1",
                AI_TASK_ROUTING="general.nl_answer=anthropic:gpt-4o-mini",
            ),
        )
        target = routing.resolve("general.nl_answer")
        assert target.provider == "anthropic"
        assert target.model == "claude-haiku-4-5"

    def test_override_wins_over_everything(self):
        routing.override(
            "general.nl_answer",
            routing.RoutingTarget("fake", "fake-model", 5.0),
        )
        target = routing.resolve("general.nl_answer")
        assert (target.provider, target.model) == ("fake", "fake-model")
