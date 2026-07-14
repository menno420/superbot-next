"""The native channel-recommender port (the channel-recommender slice —
sb/domain/setup/recommender.py · sb/domain/platform/guild_snapshot.py's
snapshot-source seam · sb/adapters/discord/setup_reads.py · the
channels.py recommender lane).

DB-free like the sibling setup_band suites: the snapshot source is
installed as a test twin and the assertions pin the ORACLE bytes
(scoring constants, reason strings, confidence buckets — oracle
sources: disbot/services/channel_recommender.py,
disbot/utils/channel_classify.py,
disbot/views/setup/sections/channels.py @bbc524e)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


def _ch(cid, name, *, kind="text", view=True, send=True, embed=True):
    from sb.domain.platform.guild_snapshot import ChannelMeta

    return ChannelMeta(
        id=cid, name=name, type=kind, topic=None, parent_category=None,
        position=0, bot_can_view=view, bot_can_send=send,
        bot_can_embed=embed)


def _snap(*channels, guild_id=99):
    from sb.domain.platform.guild_snapshot import GuildSnapshot

    return GuildSnapshot(guild_id=guild_id, guild_name="g", owner_id=1,
                         channels=tuple(channels))


@pytest.fixture(autouse=True)
def _fresh_ports():
    from sb.domain.platform.guild_snapshot import (
        reset_snapshot_ports_for_tests,
    )
    from sb.domain.setup import plan

    reset_snapshot_ports_for_tests()
    plan.reset_plan_ports_for_tests()
    yield
    reset_snapshot_ports_for_tests()
    plan.reset_plan_ports_for_tests()


# --- the carried classifier (full oracle table, patterns verbatim) ---------------------------


@pytest.mark.parametrize(("name", "expected"), [
    ("mod-log", ("likely_log", "likely_mod", "likely_mod_log")),
    ("bot-commands", ("likely_bot_cmd",)),
    ("general", ("likely_general",)),
    ("welcome", ("likely_welcome",)),
    ("casino-night", ("likely_game",)),
    ("counting", ("likely_counting",)),
    ("mining-pit", ("likely_mining",)),
    ("proof", ("likely_proof",)),
    ("admin-chat", ("likely_admin", "likely_general")),
    ("staff-logs", ("likely_log", "likely_mod", "likely_mod_log")),
    ("random", ()),
    ("", ()),
])
def test_full_classifier_table(name, expected):
    from sb.domain.setup.recommender import _classify_channel_name

    assert _classify_channel_name(name) == expected


def test_full_classifier_is_a_superset_of_the_cleanup_subset():
    """The cleanup section carries the consumed 4-tag subset (its
    test-pinned public symbol); the recommender's private full table
    must agree wherever the subset speaks."""
    from sb.domain.setup.cleanup import classify_channel_name as subset
    from sb.domain.setup.recommender import _classify_channel_name as full

    for name in ("bot-commands", "cmds", "staff", "admin-chat",
                 "mod-logs", "general", "welcome", ""):
        assert set(subset(name)) <= set(full(name))


# --- the scorer (oracle tiers + reason strings, verbatim) -------------------------------------


def test_tag_match_with_full_perms_scores_high():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("mod_logs", _snap(_ch(1, "mod-log")))
    assert len(ranked) == 1
    rec = ranked[0]
    assert (rec.channel_id, rec.channel_name) == (1, "mod-log")
    assert rec.intent == "mod_logs"
    assert rec.score == 70
    assert rec.confidence == "high"
    assert rec.action == "bind"
    assert rec.reasons == ("Name matches `likely_mod_log` pattern",
                           "Bot has view + send + embed")


def test_keyword_hint_fallback_scores_medium():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("bot_commands", _snap(_ch(2, "bot-shenanigans")))
    assert len(ranked) == 1
    assert ranked[0].score == 45
    assert ranked[0].confidence == "medium"
    assert ranked[0].reasons == ("Name contains `bot`",
                                 "Bot has view + send + embed")


def test_unviewable_channel_is_hard_excluded():
    from sb.domain.setup.recommender import recommend

    assert recommend("mod_logs",
                     _snap(_ch(1, "mod-log", view=False))) == []


def test_non_text_channel_is_excluded():
    from sb.domain.setup.recommender import recommend

    assert recommend("mod_logs",
                     _snap(_ch(1, "mod-log", kind="voice"))) == []


def test_non_matching_channel_is_dropped():
    from sb.domain.setup.recommender import recommend

    assert recommend("mod_logs", _snap(_ch(1, "random-chat"))) == []


def test_send_without_embed_scores_the_partial_tier():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("mod_logs", _snap(_ch(1, "mod-log", embed=False)))
    assert ranked[0].score == 60
    assert ranked[0].confidence == "high"
    assert ranked[0].reasons[1] == "Bot can send but not embed"


def test_view_only_is_fine_for_a_no_send_intent():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("general",
                       _snap(_ch(1, "general", send=False, embed=False)))
    assert ranked[0].score == 60
    assert ranked[0].reasons[1] == \
        "Bot can view (intent does not require send)"


def test_view_only_penalised_for_a_send_requiring_intent():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("mod_logs",
                       _snap(_ch(1, "mod-log", send=False, embed=False)))
    assert ranked[0].score == 40
    assert ranked[0].confidence == "medium"
    assert ranked[0].reasons[1] == "Bot cannot send in this channel"


def test_keyword_only_view_only_lands_low():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("bot_commands",
                       _snap(_ch(1, "bot-shenanigans", send=False,
                                 embed=False)))
    assert ranked[0].score == 15
    assert ranked[0].confidence == "low"


def test_ranking_sorts_by_score_then_name():
    from sb.domain.setup.recommender import recommend

    ranked = recommend("logs", _snap(
        _ch(3, "backlog"),                    # keyword-only: 45
        _ch(2, "bot-log"),                    # tag hit: 70
        _ch(1, "audit"),                      # tag hit: 70 — name ties break
    ))
    assert [(r.channel_name, r.score) for r in ranked] == [
        ("audit", 70), ("bot-log", 70), ("backlog", 45)]


def test_unknown_intent_returns_empty():
    from sb.domain.setup.recommender import recommend

    assert recommend("nonsense", _snap(_ch(1, "mod-log"))) == []


def test_top_pick_and_recommend_all():
    from sb.domain.setup.recommender import (
        INTENTS,
        recommend_all,
        top_pick,
    )

    snap = _snap(_ch(1, "mod-log"), _ch(2, "general"))
    pick = top_pick("mod_logs", snap)
    assert pick is not None and pick.channel_id == 1
    assert top_pick("welcome", snap) is None
    everything = recommend_all(snap)
    assert set(everything) == set(INTENTS)
    assert [r.channel_id for r in everything["general"]] == [2]


def test_intent_for_binding_carries_the_oracle_mapping():
    from sb.domain.setup.recommender import intent_for_binding

    assert intent_for_binding("mod_channel") == "mod_logs"
    assert intent_for_binding("audit_channel") == "logs"
    assert intent_for_binding("log_channel") == "logs"
    assert intent_for_binding("announce_channel") == "general"
    assert intent_for_binding("welcome_channel") == "welcome"
    assert intent_for_binding("nonsense_channel") is None


# --- the snapshot-source seam ------------------------------------------------------------------


def test_snapshot_for_degrades_to_none_uninstalled():
    from sb.domain.platform.guild_snapshot import snapshot_for

    assert run(snapshot_for(99)) is None


def test_snapshot_source_round_trip_and_reset():
    from sb.domain.platform.guild_snapshot import (
        install_snapshot_source,
        reset_snapshot_ports_for_tests,
        snapshot_for,
    )

    snap = _snap(_ch(1, "mod-log"))
    seen = []

    async def source(guild_id):
        seen.append(guild_id)
        return snap

    install_snapshot_source(source)
    assert run(snapshot_for(99)) is snap
    assert seen == [99]
    reset_snapshot_ports_for_tests()
    assert run(snapshot_for(99)) is None


# --- the channels-section recommender lane ------------------------------------------------------


def _install_snapshot(snap):
    from sb.domain.platform.guild_snapshot import install_snapshot_source

    async def source(guild_id):
        del guild_id
        return snap

    install_snapshot_source(source)


def test_channels_recommendations_ride_the_recommender_when_armed():
    import sb.manifest.setup as m
    from sb.domain.setup.channels import _recommendations

    m.ENSURE_REFS()
    _install_snapshot(_snap(_ch(1, "mod-log")))
    recs = run(_recommendations(99))
    rec = recs[("logging", "mod_channel")]
    assert rec.target_id == 1
    assert rec.target_name == "mod-log"
    assert rec.confidence == "high"
    # the oracle embed's "strongest single reason for compactness".
    assert rec.reason == "Name matches `likely_mod_log` pattern"
    # the logs-intent slots read the same likely_log tag hit.
    assert ("logging", "audit_channel") in recs
    assert ("economy", "log_channel") in recs


def test_channels_embed_field_renders_the_oracle_recommendation_line():
    import sb.manifest.setup as m
    from sb.domain.setup.channels import (
        _recommendations,
        all_channel_bindings,
        build_channels_embed_fields,
    )

    m.ENSURE_REFS()
    _install_snapshot(_snap(_ch(1, "mod-log")))
    fields = build_channels_embed_fields(all_channel_bindings(),
                                         run(_recommendations(99)))
    logging_body = next(body for name, body, _inline in fields
                        if name == "logging")
    # glyph + likely + (confidence — reason), the oracle embed bytes.
    assert ("• `mod_channel` · ✅ likely `#mod-log` (high — "
            "Name matches `likely_mod_log` pattern)") in logging_body


def test_recommended_ops_stage_every_high_recommender_pick():
    import sb.manifest.setup as m
    from sb.domain.setup.channels import (
        all_channel_bindings,
        recommended_channel_ops,
    )
    from sb.domain.setup.recommender import intent_for_binding

    m.ENSURE_REFS()
    _install_snapshot(_snap(_ch(1, "mod-log")))
    ops = run(recommended_channel_ops(99))
    # `mod-log` is a tag hit for BOTH the mod_logs intent and the logs
    # intent — every declared binding mapped onto either stages high.
    expected = {(sub, name) for sub, name, _r, _h in all_channel_bindings()
                if intent_for_binding(name) in {"logs", "mod_logs"}}
    assert {(o.subsystem, o.payload["name"]) for o in ops} == expected
    for op in ops:
        assert op.op_kind == "bind_channel"
        assert op.payload["resource_id"] == 1
        assert op.payload["target_name"] == "mod-log"


def test_recommended_ops_skip_medium_recommender_picks():
    import sb.manifest.setup as m
    from sb.domain.setup.channels import recommended_channel_ops

    m.ENSURE_REFS()
    # `backlog` only keyword-hints the logs intent (45, medium) — the
    # oracle builder never auto-stages below high.
    _install_snapshot(_snap(_ch(7, "backlog")))
    assert run(recommended_channel_ops(99)) == []


def test_channels_fall_back_to_the_advisor_without_a_snapshot():
    import sb.manifest.setup as m
    from sb.domain.setup.channels import _recommendations
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    m.ENSURE_REFS()

    async def index(guild_id):
        del guild_id
        return (GuildChannel(id=5, name="mod-log"),)

    install_channel_index(index)
    recs = run(_recommendations(99))
    rec = recs[("logging", "mod_channel")]
    assert rec.target_id == 5
    # the advisor's reason line, not the recommender's.
    assert "matches token" in rec.reason


# --- the live adapter fill -----------------------------------------------------------------------


def _fake_bot():
    perms_by_channel = {
        10: SimpleNamespace(view_channel=True, send_messages=True,
                            embed_links=True),
        11: SimpleNamespace(view_channel=True, send_messages=False,
                            embed_links=False),
    }

    def _text(cid, name):
        return SimpleNamespace(
            id=cid, name=name, topic=None, category=None, position=0,
            permissions_for=lambda me, _cid=cid: perms_by_channel[_cid])

    guild = SimpleNamespace(
        id=99, name="g", owner_id=1, me=object(),
        text_channels=[_text(10, "mod-log"), _text(11, "secret-log")],
        voice_channels=[], stage_channels=[], categories=[], roles=[])
    return SimpleNamespace(get_guild=lambda gid: guild if gid == 99
                           else None)


def test_setup_reads_install_a_perms_bearing_snapshot():
    from sb.adapters.discord.setup_reads import install_setup_read_ports
    from sb.domain.platform.guild_snapshot import snapshot_for

    install_setup_read_ports(_fake_bot())
    snap = run(snapshot_for(99))
    assert snap is not None
    by_name = {c.name: c for c in snap.channels}
    assert by_name["mod-log"].bot_can_view
    assert by_name["mod-log"].bot_can_send
    assert by_name["mod-log"].bot_can_embed
    assert by_name["secret-log"].bot_can_view
    assert not by_name["secret-log"].bot_can_send
    assert not by_name["secret-log"].bot_can_embed
    assert run(snapshot_for(12345)) is None      # unknown guild degrades


def test_setup_reads_install_the_advisor_channel_index():
    from sb.adapters.discord.setup_reads import install_setup_read_ports
    from sb.domain.setup import plan

    install_setup_read_ports(_fake_bot())
    channels = run(plan._channel_index(99))
    assert [(c.id, c.name) for c in channels] == [
        (10, "mod-log"), (11, "secret-log")]
    assert run(plan._channel_index(12345)) == ()
