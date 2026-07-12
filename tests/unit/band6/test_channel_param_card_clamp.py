"""The channel param-card override enforces Discord's embed hard limits
(codex finding on #265): the override path bypasses the grammar
renderer's budget clamps, so the card clamps in place — 25-field cap,
name/value/title/description ellipsis truncation (render._clamp
semantics). The pinned goldens sit far under every limit, so the clamp
is byte-inert for them (goldens/channel/sweep_list, sweep_channelinfo)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.domain.channel.panels import _render_param_card, list_card_spec

run = asyncio.run


def _ctx(params: dict) -> SimpleNamespace:
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=42))


def test_oversized_fields_clamp_to_discord_limits():
    big = "\n".join(f" - channel-{i}" for i in range(200))   # > 1024 chars
    params = {
        "card_title": "T" * 300,
        "card_fields": tuple(
            (f"cat-{i}", big, False) for i in range(30)),    # > 25 fields
    }
    rendered = run(_render_param_card(list_card_spec(), _ctx(params)))
    assert len(rendered.embed.fields) == 25
    for name, value, _inline in rendered.embed.fields:
        assert len(value) <= 1024 and value.endswith("…")
        assert len(name) <= 256
    assert len(rendered.embed.title) == 256
    assert rendered.embed.title.endswith("…")


def test_pinned_size_fields_pass_through_byte_identical():
    params = {
        "card_title": "Categories and Channels",
        "card_fields": (("— Uncategorized —", " - test\n - general", False),),
    }
    rendered = run(_render_param_card(list_card_spec(), _ctx(params)))
    assert rendered.embed.title == "Categories and Channels"
    assert rendered.embed.fields == (
        ("— Uncategorized —", " - test\n - general", False),)
