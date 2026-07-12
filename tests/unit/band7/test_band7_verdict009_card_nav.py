"""Band 7 — VERDICT 009 AIP-02 consumption drive (sim-lab
sims/owner-001-superbot-next-settings-ux @055245e9): operator cards
opened from a COMPONENT interaction replace the panel message in place,
so they must carry the family ``↩ AI home`` back-route (``ai.card_nav``)
— the shipped flow kept the full AIPanelView attached
(views/ai/panel.py ``edit_message(view=self)``). Command ingress stays
byte-parity bare: goldens/ai pins every ``!ai <sub>`` reply at ZERO
components.

Boots the replay composition root (DB-free) and drives the REAL
pipeline: prefix command → bare card; hub button click → nav card;
``↩ AI home`` click → the hub again. Plus the AIP-03 single-spelling
rule: the toggle ack prints the bare settings_key — the SAME string the
page's select option value carries (never the doubled ``ai.ai_*``).
"""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

_HOME_LABEL = "↩ AI home"


@pytest.fixture()
def skeleton():
    from sb.adapters.parity.boot import Harness
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h
    run(h.close())


def _labels(payload) -> list[str]:
    return [c.get("label") for row in payload.get("components", ())
            for c in row["components"]]


def _button(payload, label: str) -> str:
    return next(c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == label)


def _last_embed_payload(calls):
    """The last embed-carrying document (followup_send carries embeds
    top-level; interaction_response nests them under ``data``)."""
    for call in reversed(calls):
        doc = call.payload
        if not doc.get("embeds"):
            doc = doc.get("data") or {}
        if doc.get("embeds"):
            return doc
    raise AssertionError("no embed-carrying call")


def test_prefix_command_card_stays_bare(skeleton):
    """`!ai status` — the shipped ctx.send(embed=…) reply: ZERO
    components (goldens/ai/sweep_ai_status byte-parity preserved)."""
    run(skeleton.send_command("!ai status", persona="admin"))
    payload = _last_embed_payload(skeleton.take_calls())
    assert not payload.get("components")


def test_hub_button_card_carries_home_route(skeleton):
    """Hub → Diagnostics: the COMPONENT-ingress card renders as
    ai.card_nav with the family ↩ AI home back-route."""
    run(skeleton.send_command("!aimenu", persona="admin"))
    skeleton.take_calls()
    run(skeleton.click(message_id=940, custom_id="ai:diagnostics",
                       persona="admin"))
    payload = _last_embed_payload(skeleton.take_calls())
    assert _labels(payload) == [_HOME_LABEL]


def test_home_route_reopens_the_hub(skeleton):
    """↩ AI home on the card rebuilds the hub (the never-strand exit)."""
    run(skeleton.send_command("!aimenu", persona="admin"))
    skeleton.take_calls()
    run(skeleton.click(message_id=950, custom_id="ai:routing",
                       persona="admin"))
    card = _last_embed_payload(skeleton.take_calls())
    run(skeleton.click(message_id=951,
                       custom_id=_button(card, _HOME_LABEL),
                       persona="admin"))
    hub = _last_embed_payload(skeleton.take_calls())
    labels = _labels(hub)
    assert "Diagnostics" in labels and "Settings" in labels


def test_toggle_ack_prints_the_single_spelling(skeleton):
    """AIP-03: the toggle ack echoes the bare settings_key — byte-equal
    to the select option value the page renders (`ai_enabled`, never
    `ai.ai_enabled`)."""
    async def _write(req, spec, value):  # the K7 op is DB-backed — stub
        class _R:
            outcome = __import__("sb.spec.outcomes",
                                 fromlist=["SUCCESS"]).SUCCESS
            user_message = ""
        return _R()

    from sb.domain.ai import settings_widgets

    original = settings_widgets._write_setting
    settings_widgets._write_setting = _write
    try:
        run(skeleton.send_command("!ai settings", persona="admin"))
        page = _last_embed_payload(skeleton.take_calls())
        select = next(c for row in page["components"]
                      for c in row["components"] if c.get("type") == 3)
        option = select["options"][0]
        assert option["value"] == "ai_enabled"      # golden-pinned byte
        run(skeleton.click(message_id=960, custom_id=select["custom_id"],
                           component_type=3, values=["ai_enabled"],
                           persona="admin"))
        contents = [c.payload.get("content")
                    for c in skeleton.take_calls()
                    if c.payload.get("content")]
        ack = next(t for t in contents if t.startswith("✅ Toggled"))
        assert ack == "✅ Toggled `ai_enabled` → `True`."
        assert "`ai.ai_enabled`" not in ack
    finally:
        settings_widgets._write_setting = original
