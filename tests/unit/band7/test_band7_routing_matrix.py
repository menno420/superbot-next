"""Band 7 — the ORDER-004 walking-skeleton drive for the ai ROUTING
MATRIX picker (the routing-matrix follow-up slice D-0071 parked —
D-0074): boot the replay composition root (DB-free) and drive the
shipped views/ai/routing/matrix.py flow through the REAL pipeline —
behavior chooser click → the matrix page, channel pick → the dry-run
resolve card — asserting the shipped bytes (reconstructed via
search_code fragments @2c7d2de7; no golden pins these clicks).

The resolver reads ride an installed PolicyBundle twin (the DB-free
posture — deterministic allowed/denied decisions through the REAL
:func:`sb.kernel.ai.policy.resolve_policy` precedence port, never a
stubbed decision); the preset-key labels ride the migration-0030 seed
twin (the behavior-presets skeleton's fixture shape)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

BLURPLE = 5793266
GREEN = 3066993
RED = 15158332
PAGE_FOOTER = "Administrator-only · in-place navigation."

_CHANNEL_ID = 555
_CATEGORY_ID = 777

#: the migration-0030 seed twin (ids in the seed's insert order).
_SEED_ROWS = [
    {"id": 1, "guild_id": None, "name": "disabled", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 2, "guild_id": None, "name": "mention_only_helper", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 3, "guild_id": None, "name": "helpful_channel", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 4, "guild_id": None, "name": "btd6_focused", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
]


@pytest.fixture()
def seed_rows(monkeypatch):
    from sb.domain.ai import policy_store

    rows = sorted(_SEED_ROWS, key=lambda r: r["name"])

    async def _list(conn=None):
        return [dict(r) for r in rows]

    monkeypatch.setattr(policy_store, "list_preset_profiles", _list)
    return rows


@pytest.fixture()
def skeleton(seed_rows):
    from sb.adapters.parity.boot import Harness
    from sb.domain.ai.policy_widgets import (
        GuildScopeRoster,
        install_guild_scope_roster,
    )
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    async def _roster(guild_id):
        return GuildScopeRoster(
            text_channels=((_CHANNEL_ID, "general", _CATEGORY_ID),),
            categories=((_CATEGORY_ID, "Main"),),
            roles=())

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    install_guild_scope_roster(_roster)
    yield h
    install_guild_scope_roster(None)  # type: ignore[arg-type]
    run(h.close())


@pytest.fixture()
def bundle_reader():
    """Install a deterministic PolicyBundle and restore the previous
    reader after (the REAL resolve_policy runs over it)."""
    from sb.kernel.ai import policy

    previous = policy._bundle_reader  # noqa: SLF001 — restore seam
    installed: dict = {"bundle": policy.PolicyBundle(policy=None)}

    def _install(bundle) -> None:
        installed["bundle"] = bundle

    async def _read(guild_id: int):
        return installed["bundle"]

    policy.install_policy_bundle_reader(_read)
    yield _install
    policy.install_policy_bundle_reader(previous)  # type: ignore[arg-type]


def _allowed_bundle():
    from sb.kernel.ai import policy

    return policy.PolicyBundle(
        policy={"enabled": True, "natural_language_enabled": True,
                "minimum_level_default": 2, "cooldown_seconds": 30,
                "guild_instruction_profile_id": 4, "generation": 7},
        channel={_CHANNEL_ID: {"mode": "always_reply", "min_level": 1,
                               "cooldown_seconds": 10,
                               "instruction_profile_id": 3}})


def _panel_payload(calls):
    assert [c.method for c in calls] == ["interaction_response",
                                         "followup_send"]
    return calls[1].payload


def _rows(payload):
    return [[(c.get("label") or c.get("placeholder"), c.get("style"))
             for c in row["components"]]
            for row in payload["components"]]


def _button(payload, label: str) -> str:
    return next(c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == label)


def _select(payload) -> dict:
    return next(c for row in payload["components"]
                for c in row["components"] if c.get("type") in (3, 8))


def _open_matrix_page(skeleton, *, message_id: int):
    run(skeleton.send_command("!aimenu", persona="admin"))
    skeleton.take_calls()
    run(skeleton.click(message_id=940, custom_id="ai:behavior",
                       persona="admin"))
    chooser = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=message_id,
                       custom_id=_button(chooser, "Routing matrix"),
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


# --- the page (chooser.py matrix_btn's _behavior_page_embed bytes) ------------------


def test_matrix_page_shipped_bytes(skeleton):
    payload = _open_matrix_page(skeleton, message_id=941)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Behavior · routing matrix"
    assert embed["description"] == ("Pick a channel to dry-run the AI "
                                    "routing matrix.")
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    # the shipped _MatrixChannelSelect (native ChannelSelect, text only).
    assert select["type"] == 8
    assert select["channel_types"] == [0]
    assert "options" not in select
    assert select["placeholder"] == "Pick a channel to preview routing for…"
    assert _rows(payload)[-1] == [("↩ AI Behavior", 2)]


# --- the pick → the shipped 🧭 dry-run resolve card ----------------------------------


def test_pick_renders_allowed_card(skeleton, bundle_reader):
    bundle_reader(_allowed_bundle())
    payload = _open_matrix_page(skeleton, message_id=942)
    run(skeleton.click(message_id=943,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=[str(_CHANNEL_ID)],
                       persona="admin"))
    (card,) = skeleton.take_calls()[-1].payload["embeds"]
    assert card["title"] == "🧭 AI Routing matrix (dry-run)"
    # the shipped defaults render verbatim (matrix.py called the builder
    # with only guild/channel/user ids — user_level=5, roles=()).
    assert card["description"].startswith(f"channel=<#{_CHANNEL_ID}> · ")
    assert card["description"].endswith("user_level=5 · roles=—")
    assert card["color"] == GREEN
    fields = {f["name"]: f for f in card["fields"]}
    assert fields["Outcome"]["value"] == "✅ allowed"
    assert fields["Outcome"]["inline"] is False
    assert fields["Effective min_level"]["value"] == "1"
    assert fields["Effective min_level"]["inline"] is True
    assert fields["Effective cooldown"]["value"] == "10s"
    # id → preset-key labels (guild profile first, then channel).
    assert fields["Instruction profiles"]["value"] == (
        "`4` (btd6_focused), `3` (helpful_channel)")
    trace = fields["Precedence trace"]["value"]
    assert trace.startswith("• guild_ai_gate: AI enabled=true")
    assert "• final_decision: allowed min_level=1 cooldown=10s" in trace
    assert card["footer"]["text"].startswith("policy_snapshot=`")
    assert card["footer"]["text"].endswith(
        "` · dry-run only · no audit / no cooldown side-effects.")


def test_pick_renders_denied_card(skeleton, bundle_reader):
    from sb.kernel.ai import policy

    bundle_reader(policy.PolicyBundle(policy=None))
    payload = _open_matrix_page(skeleton, message_id=944)
    run(skeleton.click(message_id=945,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=[str(_CHANNEL_ID)],
                       persona="admin"))
    (card,) = skeleton.take_calls()[-1].payload["embeds"]
    assert card["color"] == RED
    fields = {f["name"]: f["value"] for f in card["fields"]}
    assert fields["Outcome"] == "❌ denied · `guild_not_configured`"
    assert fields["Effective min_level"] == "2"
    assert fields["Effective cooldown"] == "30s"
    assert "Instruction profiles" not in fields
    assert fields["Precedence trace"] == (
        "• guild_ai_gate: no ai_guild_policy row → deny "
        "GUILD_NOT_CONFIGURED")


# --- the builder + handler seams -----------------------------------------------------


def test_builder_is_read_only(bundle_reader):
    """The shipped 'No mutations.' contract: a dry-run resolve never
    touches cooldown bookkeeping."""
    from sb.domain.ai.routing_matrix import build_routing_matrix_embed
    from sb.kernel.ai import policy

    bundle_reader(_allowed_bundle())
    before = dict(policy._LAST_REPLY_AT)  # noqa: SLF001
    embed = run(build_routing_matrix_embed(
        guild_id=1, channel_id=_CHANNEL_ID, user_id=9))
    assert embed.style_token == "green"
    assert dict(policy._LAST_REPLY_AT) == before  # noqa: SLF001


def test_trace_caps_at_1000(monkeypatch):
    """The shipped 1000-char ellipsis cap on the trace field."""
    from sb.domain.ai import routing_matrix
    from sb.kernel.ai import policy

    async def _fake_resolve(ctx, *, dry_run=False):
        return policy.PolicyDecision(
            allowed=True, reason_code=policy.PolicyDenialReason.NONE,
            effective_min_level=0, effective_cooldown=0,
            precedence_trace=tuple(f"step {i} " + "x" * 60
                                   for i in range(20)))

    monkeypatch.setattr(policy, "resolve_policy", _fake_resolve)
    embed = run(routing_matrix.build_routing_matrix_embed(
        guild_id=1, channel_id=2, user_id=3))
    trace = dict((f[0], f[1]) for f in embed.fields)["Precedence trace"]
    assert len(trace) == 1000
    assert trace.endswith("…")


def test_pick_guard_needs_guild():
    """The shipped guild-guard byte (matrix.py's own copy — not the
    chooser family's 'Edit requires…')."""
    from sb.domain.ai.routing_matrix import routing_matrix_pick

    req = SimpleNamespace(guild_id=None, args={}, actor=None)
    reply = run(routing_matrix_pick(req))
    assert reply.user_message == "❌ This requires a guild context."


def test_preset_lookup_degrades_to_empty(monkeypatch):
    """The shipped defensive except: a catalog miss labels ids bare."""
    from sb.domain.ai import behavior_presets, routing_matrix

    async def _boom():
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(behavior_presets, "list_behavior_presets", _boom)
    assert run(routing_matrix._preset_lookup()) == {}
