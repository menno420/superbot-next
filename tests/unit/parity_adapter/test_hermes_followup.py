"""Hermes port + the followup_send wire shape (goldens/hermes).

The corpus's ``followup_send`` calls (hermes, karma, economy, setup) all
carry ``webhook_id: <@bot>`` (interaction.followup IS the application's
webhook) and discord.py's ``Webhook.send`` payload shape — ``content``
omitted when None, ``components`` omitted when no view. The type-4
interaction response keeps its own always-carries shape (goldens/help).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

GOLDENS = Path(__file__).resolve().parents[3] / "parity" / "goldens"


@pytest.fixture()
def harness():
    from sb.adapters.parity.boot import Harness

    h = asyncio.run(Harness.start(require_db=False))
    # ENSURE_REFS re-arms after a ref-table wipe by earlier suite tests
    # (compiler P1 contract — the band-6 walking-skeleton posture), and the
    # per-case reset pins the db-free resolver ports (_no_policy default).
    import sb.manifest.hermes as hermes_manifest

    hermes_manifest.ENSURE_REFS()
    h.reset_case_state()
    yield h
    asyncio.run(h.close())


def test_followup_payload_webhook_shape():
    from sb.adapters.parity.transport import _followup_args, _followup_payload

    assert _followup_payload(
        {"content": None, "tts": False, "embeds": [{"title": "t"}],
         "components": [], "flags": 64}) == {
        "tts": False, "embeds": [{"title": "t"}], "flags": 64}
    # a real content string / non-empty view stays on the wire
    kept = _followup_payload({"content": "hi", "components": [{"type": 1}]})
    assert kept == {"content": "hi", "components": [{"type": 1}]}
    from parity.harness.world import World

    assert _followup_args() == {"webhook_id": World.BOT_USER_ID}


def test_hermes_bridge_config_fails_closed():
    from sb.domain.hermes import service

    service.reset_for_tests()
    try:
        assert service.bridge_configured() is False  # uninstalled

        class _Cfg:
            CLAUDE_ROUTINE_FIRE_URL = ""

            def is_configured(self, env_var: str) -> bool:
                return False

        service.install_hermes_bridge_config(_Cfg())
        assert service.bridge_configured() is False  # keyless

        class _Keyed(_Cfg):
            CLAUDE_ROUTINE_FIRE_URL = "https://example.invalid/fire"

            def is_configured(self, env_var: str) -> bool:
                return env_var == "CLAUDE_ROUTINE_TOKEN"

        service.install_hermes_bridge_config(_Keyed())
        assert service.bridge_configured() is True
    finally:
        service.reset_for_tests()


def test_hermes_slash_defers_then_answers_missing_config(harness):
    """/bugreport on an unconfigured bridge: type-5 ephemeral ack, then the
    shipped red missing-config embed as a webhook followup — the exact
    calls goldens/hermes/sweep_slash_bugreport.json pins."""
    from parity.harness.world import World
    from sb.domain.hermes.service import MISSING_CONFIG_HELP

    asyncio.run(harness.invoke_slash(
        "bugreport",
        [{"name": "title", "type": 3, "value": "test"},
         {"name": "description", "type": 3, "value": "test"}],
        persona="admin"))
    calls = harness.take_calls()
    assert [c.method for c in calls] == ["interaction_response", "followup_send"]
    ack, followup = calls
    assert ack.payload == {"type": 5, "data": {"flags": 64}}
    assert followup.args == {"webhook_id": World.BOT_USER_ID}
    assert sorted(followup.payload) == ["embeds", "flags", "tts"]
    assert followup.payload["flags"] == 64
    (embed,) = followup.payload["embeds"]
    assert embed["title"] == "Hermes bridge not configured"
    assert embed["color"] == 15158332
    assert embed["description"] == MISSING_CONFIG_HELP
    assert "footer" not in embed


def test_missing_config_help_matches_golden_bytes():
    from sb.domain.hermes.service import MISSING_CONFIG_HELP

    doc = json.loads(
        (GOLDENS / "hermes" / "sweep_slash_bugreport.json").read_text())
    golden_embed = doc["steps"][0]["calls"][1]["payload"]["embeds"][0]
    assert golden_embed["description"] == MISSING_CONFIG_HELP
