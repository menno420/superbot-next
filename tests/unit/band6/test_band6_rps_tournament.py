"""Band 6 — RPS tournament orchestration (the shipped registration →
bracket → champion loop, headless) + the ORDER-004 walking-skeleton drive:
boot the replay composition root, open registration through the REAL
pipeline (`!rpsregister` → the golden-pinned embed + Join button + the ✅
self-reaction primer), sign up by button AND by the kernel reaction seam,
start the bracket, click both matches through best-of scoring, and watch
the champion payout land on the audited lane.
"""

from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

# parity/harness/world.py constants (the skeleton's real world)
W_GUILD = 700_000_000_000_000_001
ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102
SECOND = 900_000_000_000_000_103
PERSONA = {ADMIN: "admin", MEMBER: "member", SECOND: "second_member"}


class FakeTournamentFlag:
    """In-memory guild_settings active_tournament twin."""

    def __init__(self):
        self.flags: dict[int, str] = {}

    def install(self, monkeypatch):
        from sb.domain.games import tournament_flag as tf

        async def set_active(conn, *, guild_id, game):
            self.flags[int(guild_id)] = str(game)

        async def clear_active(conn, *, guild_id):
            return 1 if self.flags.pop(int(guild_id), None) else 0

        async def get_active(guild_id, conn=None):
            return self.flags.get(int(guild_id))

        monkeypatch.setattr(tf, "set_active", set_active)
        monkeypatch.setattr(tf, "clear_active", clear_active)
        monkeypatch.setattr(tf, "get_active", get_active)
        return self


# --- renderer: the golden-pinned registration embed --------------------------------


def _panel_ctx(params: dict, uid: int = ADMIN):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


def test_registration_render_pins_the_golden_bytes():
    from sb.domain.rps.panels import _render_registration, rps_registration_spec

    spec = rps_registration_spec()
    rendered = run(_render_registration(spec, _panel_ctx(
        {"entry_fee": 0, "mode_label": "Classic"})))
    assert rendered.embed.title == (
        "🎮 Rock Paper Scissors Tournament Registration 🎮")
    assert rendered.embed.description == (
        "React ✅ or click **Join** to sign up!\n"
        "Registration ends in 10 minutes.")
    assert rendered.embed.style_token == "blue"         # INFO_COLOR 3447003
    assert rendered.embed.fields == (("Entry Fee", "Free", True),
                                     ("Game Mode", "Classic", True))
    (join,) = rendered.components
    assert (join.label, join.style, join.emoji, join.disabled) == (
        "Join Tournament", "success", "✅", False)
    assert rendered.self_reactions == ("✅",)            # the shipped primer
    assert rendered.invoker_lock is None                # PUBLIC sign-up


def test_registration_render_paid_fee_field():
    from sb.domain.rps.panels import _render_registration, rps_registration_spec

    rendered = run(_render_registration(rps_registration_spec(), _panel_ctx(
        {"entry_fee": 25, "mode_label": "Classic"})))
    assert rendered.embed.fields[0] == ("Entry Fee", "25 🪙", True)


def test_match_render_open_stage_keeps_shipped_lines():
    from sb.domain.rps.panels import _render_match, rps_match_spec

    rendered = run(_render_match(rps_match_spec(), _panel_ctx({
        "stage": "open", "match_id": "r1m1", "p1": ADMIN, "p2": MEMBER,
        "mode": "classic", "best_of": 3, "round": 1})))
    assert rendered.embed.description == (
        f"<@{ADMIN}> vs <@{MEMBER}>\n"
        "Game mode: Classic, Best of 3\n"
        "Please enter your move.")
    labels = [(c.label, c.emoji, c.disabled) for c in rendered.components]
    assert labels == [("Rock", "🪨", False), ("Paper", "📄", False),
                      ("Scissors", "✂️", False)]


def test_match_render_mode_subset_lizard_spock():
    from sb.domain.rps.panels import _render_match, rps_match_spec

    rendered = run(_render_match(rps_match_spec(), _panel_ctx({
        "stage": "open", "p1": 1, "p2": 2, "mode": "lizard_spock",
        "best_of": 3, "round": 1})))
    assert [c.label for c in rendered.components] == [
        "Rock", "Paper", "Scissors", "Lizard", "Spock"]


# --- the pure bracket core ----------------------------------------------------------


def test_bracket_pairs_scores_and_advances():
    import random

    from sb.domain.rps import tournament

    tournament.reset_tournaments_for_tests()
    state = tournament.get_state(1)
    state.players = [11, 22, 33]
    state.registration_active = True
    matches, byes = tournament.start_bracket(state, mode="classic",
                                             best_of=3,
                                             rng=random.Random(42))
    assert not state.registration_active and state.active
    assert len(matches) == 1 and len(byes) == 1
    (match,) = matches
    # best-of-3: first throw tie, then two decided throws
    out = tournament.record_move(state, match.match_id, match.p1, "rock")
    assert out["stage"] == "waiting"
    out = tournament.record_move(state, match.match_id, match.p2, "rock")
    assert out["stage"] == "throw_tie" and match.moves == {}
    tournament.record_move(state, match.match_id, match.p1, "rock")
    out = tournament.record_move(state, match.match_id, match.p2, "scissors")
    assert out["stage"] == "throw_scored"
    assert out["throw_winner"] == match.p1
    tournament.record_move(state, match.match_id, match.p1, "paper")
    out = tournament.record_move(state, match.match_id, match.p2, "rock")
    assert out["stage"] == "match_done" and out["winner"] == match.p1
    assert match.loser() not in state.current_round
    advanced = tournament.advance_round(state)
    assert advanced["stage"] == "next_round" and advanced["round"] == 2
    assert len(advanced["matches"]) == 1 and advanced["byes"] == []
    tournament.reset_tournaments_for_tests()


def test_record_move_locks():
    from sb.domain.rps import tournament

    tournament.reset_tournaments_for_tests()
    state = tournament.get_state(1)
    state.players = [11, 22]
    matches, _ = tournament.start_bracket(state, mode="classic", best_of=1)
    (match,) = matches
    assert tournament.record_move(state, match.match_id, 99, "rock") == {
        "stage": "not_yours"}
    tournament.record_move(state, match.match_id, 11, "rock")
    assert tournament.record_move(
        state, match.match_id, 11, "paper")["stage"] == "already_picked"
    assert tournament.record_move(state, "nope", 11, "rock")["stage"] == (
        "expired")
    tournament.reset_tournaments_for_tests()


# --- ORDER-004 walking skeleton -----------------------------------------------------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams
    (the #124 fixture, plus the tournament flag twin)."""
    from sb.adapters.parity.boot import Harness

    economy = FakeEconomy().install(monkeypatch)
    games = FakeGamesStore().install(monkeypatch)
    flags = FakeTournamentFlag().install(monkeypatch)

    import contextlib

    from sb.kernel.db import pool
    from tests.unit.workflow.conftest import FakeConn

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)

    h = asyncio.run(Harness.start(require_db=False))

    from sb.domain.games.session import install_games_dispatcher
    from sb.domain.rps import tournament
    from sb.domain.rps.panels import register_rps_sessions

    tournament.reset_tournaments_for_tests()
    tournament.register_reaction_signup()
    register_rps_sessions()
    install_games_dispatcher()

    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h, economy, games, flags
    tournament.reset_tournaments_for_tests()
    asyncio.run(h.close())


def _components(call) -> list[dict]:
    out = []
    for row in call.payload.get("components", []):
        out.extend(row["components"])
    return out


def _match_players(embed_description: str) -> tuple[int, int]:
    first = embed_description.splitlines()[0]
    p1, p2 = re.findall(r"<@(\d+)>", first)
    return int(p1), int(p2)


def _play_match(harness, call, *, winner_move="rock", loser_move="scissors"):
    """Click a best-of-1 match to completion; returns (winner, calls)."""
    p1, p2 = _match_players(call.payload["embeds"][0]["description"])
    buttons = {b["label"]: b["custom_id"] for b in _components(call)}
    run(harness.click(message_id=call.response_id,
                      custom_id=buttons["Rock"], persona=PERSONA[p1]))
    harness.take_calls()
    run(harness.click(message_id=call.response_id,
                      custom_id=buttons["Scissors"], persona=PERSONA[p2]))
    return p1, harness.take_calls()


def test_walking_skeleton_rps_tournament_end_to_end(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament
    from sb.kernel.interaction.reactions import ReactionEvent, dispatch_reaction

    # 1. !rpsregister — the golden-pinned registration message + ✅ primer
    run(harness.send_command("!rpsregister", persona="admin"))
    calls = harness.take_calls()
    assert [c.method for c in calls] == ["send_message", "add_reaction"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == (
        "🎮 Rock Paper Scissors Tournament Registration 🎮")
    assert embed["color"] == 3447003                    # shipped INFO_COLOR
    assert embed["description"] == (
        "React ✅ or click **Join** to sign up!\n"
        "Registration ends in 10 minutes.")
    assert embed["fields"] == [
        {"inline": True, "name": "Entry Fee", "value": "Free"},
        {"inline": True, "name": "Game Mode", "value": "Classic"}]
    (join,) = _components(calls[0])
    assert (join["label"], join["style"]) == ("Join Tournament", 3)
    assert join["emoji"] == {"id": None, "name": "✅"}
    reg_message_id = calls[0].response_id
    assert calls[1].args == {"channel_id": harness.world.channels["general"],
                             "emoji": "✅", "message_id": reg_message_id}
    # the shipped ACTIVE_TOURNAMENT flag row (audited op)
    assert flags.flags[W_GUILD] == "rps"

    # 2. sign-ups: Join button (admin + member), reaction (second_member)
    run(harness.click(message_id=reg_message_id, custom_id=join["custom_id"],
                      persona="admin"))
    first_join = harness.take_calls()
    assert any("✅ Registered! (1 player(s) so far)" in str(c.payload)
               for c in first_join if c.payload)
    run(harness.click(message_id=reg_message_id, custom_id=join["custom_id"],
                      persona="member"))
    harness.take_calls()
    # duplicate join politely refused
    run(harness.click(message_id=reg_message_id, custom_id=join["custom_id"],
                      persona="member"))
    dup = harness.take_calls()
    assert any("already registered" in str(c.payload) for c in dup
               if c.payload)
    # the reaction path (the kernel seam — no wire calls, silent)
    run(dispatch_reaction(ReactionEvent(
        guild_id=W_GUILD, channel_id=harness.world.channels["general"],
        message_id=reg_message_id, user_id=SECOND, emoji="✅")))
    assert harness.take_calls() == []
    state = tournament.get_state(W_GUILD)
    assert state.players == [ADMIN, MEMBER, SECOND]

    # 3. !rpsstart during the window refuses with the shipped copy
    run(harness.send_command("!rpsstart", persona="admin"))
    early = harness.take_calls()
    assert any("Cannot start the tournament while registration is still "
               "active." in str(c.payload) for c in early if c.payload)
    assert state.registration_active

    # 4. window elapses (lazy close) → !rpsstart runs the bracket
    state.registration_opened_mono -= 601
    run(harness.send_command("!rpsstart classic 1", persona="admin"))
    calls = harness.take_calls()
    texts = [str((c.payload or {}).get("content")) for c in calls]
    assert any("3 players have registered for the tournament." in t
               for t in texts)
    assert any("Tournament started with game mode: classic, Best of 1"
               in t for t in texts)
    assert any("gets a bye this round." in t for t in texts)
    match_calls = [c for c in calls if (c.payload or {}).get("embeds")
                   and "Round 1" in c.payload["embeds"][0].get("title", "")]
    assert len(match_calls) == 1
    (bye_line,) = [t for t in texts if "bye" in t]
    bye = int(re.search(r"<@(\d+)>", bye_line).group(1))

    # 5. round 1: the paired players click it out (best of 1)
    r1_winner, done_calls = _play_match(harness, match_calls[0])
    # the final click edits the match view terminal, then opens round 2
    methods = [c.method for c in done_calls]
    assert methods[:2] == ["interaction_response", "edit_followup"]
    assert done_calls[0].payload == {"type": 6}
    (done_embed,) = done_calls[1].payload["embeds"]
    assert f"🏆 <@{r1_winner}> wins the match!" in done_embed["description"]
    assert all(b["disabled"] for b in _components(done_calls[1]))
    round2 = [c for c in done_calls if (c.payload or {}).get("embeds")
              and "Round 2" in c.payload["embeds"][0].get("title", "")]
    assert len(round2) == 1
    p1, p2 = _match_players(round2[0].payload["embeds"][0]["description"])
    assert {p1, p2} == {r1_winner, bye}
    # stats landed through the audited op (win + loss rows)
    # (rps_players rides FakeConn — asserted via the op result envelope
    # in the pure-core tests; here the wire + money stay the oracle.)

    # 6. round 2 → champion: free tournament pays the shipped 100 🪙
    champion, final_calls = _play_match(harness, round2[0])
    texts = [str((c.payload or {}).get("content")) for c in final_calls]
    assert any("has won the RPS Tournament! 🏆" in t for t in texts)
    assert not any("💰 Payout" in t for t in texts)     # free play: no pot line
    assert economy.balances[(champion, W_GUILD)] == 100
    assert [a["reason"] for a in economy.audit] == [
        "rps:tournament_free_reward"]
    # the flag row cleared in the payout txn; state torn down
    assert W_GUILD not in flags.flags
    assert tournament.state_or_none(W_GUILD) is None

    # 7. a late click on the finished round-2 view politely expires
    buttons = {b["label"]: b["custom_id"] for b in _components(round2[0])}
    run(harness.click(message_id=round2[0].response_id,
                      custom_id=buttons["Paper"], persona=PERSONA[champion]))
    late = harness.take_calls()
    assert any("expired" in str(c.payload).lower() for c in late
               if c.payload)


def test_walking_skeleton_entry_fee_and_pot(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament

    economy.balances[(ADMIN, W_GUILD)] = 100
    economy.balances[(MEMBER, W_GUILD)] = 100

    run(harness.send_command("!rpsregister 25", persona="admin"))
    calls = harness.take_calls()
    (embed,) = calls[0].payload["embeds"]
    assert embed["fields"][0] == {"inline": True, "name": "Entry Fee",
                                  "value": "25 🪙"}
    (join,) = _components(calls[0])
    reg_id = calls[0].response_id

    # a broke player is fee-gated with the shipped copy
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="second_member"))
    broke = harness.take_calls()
    assert any("❌ Need **25** 🪙 to enter (you have 0)." in str(c.payload)
               for c in broke if c.payload)

    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="admin"))
    harness.take_calls()
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="member"))
    harness.take_calls()
    assert economy.balances[(ADMIN, W_GUILD)] == 75
    assert economy.balances[(MEMBER, W_GUILD)] == 75
    assert [a["reason"] for a in economy.audit] == ["rps:entry_fee",
                                                    "rps:entry_fee"]
    # entry rows escrowed (recovery-refundable at boot)
    assert sorted(r["subsystem"] for r in games.rows.values()) == [
        "rps_tournament_entry", "rps_tournament_entry"]

    state = tournament.get_state(W_GUILD)
    state.registration_opened_mono -= 601
    run(harness.send_command("!rpsstart classic 1", persona="admin"))
    calls = harness.take_calls()
    match_calls = [c for c in calls if (c.payload or {}).get("embeds")]
    assert len(match_calls) == 1

    champion, final_calls = _play_match(harness, match_calls[0])
    texts = [str((c.payload or {}).get("content")) for c in final_calls]
    assert any("💰 Payout: **50** 🪙" in t for t in texts)
    assert economy.balances[(champion, W_GUILD)] == 75 + 50
    assert economy.audit[-1]["reason"] == "rps:tournament_win"
    assert not games.rows                       # entry rows consumed
    assert W_GUILD not in flags.flags


def test_start_without_players_aborts_and_refunds_nothing(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament

    run(harness.send_command("!rpsregister", persona="admin"))
    harness.take_calls()
    state = tournament.get_state(W_GUILD)
    state.registration_opened_mono -= 601
    run(harness.send_command("!rpsstart", persona="admin"))
    calls = harness.take_calls()
    assert any("Not enough players registered to start the tournament."
               in str(c.payload) for c in calls if c.payload)
    assert W_GUILD not in flags.flags           # shipped clear_active
    assert tournament.state_or_none(W_GUILD) is None
    assert not economy.audit


def test_rpsregister_refuses_when_a_foreign_tournament_is_active(skeleton):
    """The shipped cross-game guard (oracle `rps_tournament_cog.py`
    registration open: `existing = get_active(...); if existing: … return`),
    dropped in the port. Because the `active_tournament` flag row is SHARED
    by both games and the champion payout keys its settle-once check-and-set
    on the flag-row delete, letting `!rpsregister` open on top of a live
    *blackjack* tournament clobbers that game's flag — the second tournament
    to settle finds `clear_active()==0` and strands its pot. Registration
    must refuse instead, with the oracle copy verbatim."""
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament

    # a blackjack tournament already owns the shared flag row
    flags.flags[W_GUILD] = "blackjack"
    run(harness.send_command("!rpsregister", persona="admin"))
    calls = harness.take_calls()
    # oracle copy verbatim (menno420/superbot rps_tournament_cog.py /
    # blackjack actions.py): "A **{existing}** tournament is already
    # active in this server."
    assert any("A **blackjack** tournament is already active in this server."
               in str(c.payload) for c in calls if c.payload)
    # the foreign flag is untouched and NO rps tournament was opened
    assert flags.flags[W_GUILD] == "blackjack"
    assert tournament.state_or_none(W_GUILD) is None
    assert not economy.audit


def test_rpsregister_reclaims_a_stale_own_flag(skeleton):
    """A stale own `rps` flag (crash before settle — entries refunded at
    boot) stays reclaimable, mirroring the blackjack port's `!= own_game`
    guard and the boot flag-sweep posture — `!rpsregister` opens normally."""
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament

    flags.flags[W_GUILD] = "rps"                 # stale own-game flag
    run(harness.send_command("!rpsregister", persona="admin"))
    calls = harness.take_calls()
    assert not any("already active in this server" in str(c.payload)
                   for c in calls if c.payload)   # not refused
    assert flags.flags[W_GUILD] == "rps"          # its own flag, re-set
    assert tournament.state_or_none(W_GUILD) is not None


def test_rpsbot_mode_guard_and_matchup_guard(skeleton):
    harness, economy, games, flags = skeleton

    run(harness.send_command("!rpsbot test", persona="admin"))
    calls = harness.take_calls()
    assert any("Invalid game mode. Available modes: classic, lizard_spock, "
               "chess, elemental" in str(c.payload) for c in calls
               if c.payload)

    run(harness.send_command(f"!rpsmatchup <@{SECOND}> <@{SECOND}>",
                             persona="admin"))
    calls = harness.take_calls()
    assert any("Tournament is not active." in str(c.payload)
               for c in calls if c.payload)


def _texts(calls) -> list[str]:
    return [str((c.payload or {}).get("content")) for c in calls if c.payload]


def test_rpssettings_shipped_guards_and_update(skeleton, monkeypatch):
    """The shipped ``rps_settings`` command verbatim: the three guard
    copies (invalid setting — the sweep-pinned bytes — invalid mode,
    non-odd best_of) and the success copy; the valid write rides the
    band-1 `settings.set_scalar` op onto the declared persisted keys."""
    harness, economy, games, flags = skeleton
    # re-arm the band-1 settings op refs/spec (the ENSURE_REFS idiom the
    # skeleton already applies to the rps sessions/reaction consumer —
    # earlier suites may have cleared the registries this test dispatches
    # through; idempotent when they haven't)
    from sb.domain.settings import ops as settings_ops

    settings_ops.ensure_ops_refs()
    settings_ops.register_ops()

    # invalid setting — sweep.rpssettings' golden bytes
    run(harness.send_command("!rpssettings test test", persona="admin"))
    assert any("Invalid setting. Available settings: default_mode, "
               "default_best_of" in t for t in _texts(harness.take_calls()))

    # invalid mode value — shipped copy
    run(harness.send_command("!rpssettings default_mode banana",
                             persona="admin"))
    assert any("Invalid game mode. Available modes: classic, lizard_spock, "
               "chess, elemental" in t for t in _texts(harness.take_calls()))

    # even / non-numeric / non-positive best_of — shipped copy
    for bad in ("4", "abc", "0", "-3"):
        run(harness.send_command(f"!rpssettings default_best_of {bad}",
                                 persona="admin"))
        assert any("Please provide an odd positive integer for "
                   "default_best_of." in t
                   for t in _texts(harness.take_calls())), bad

    # valid updates: shipped success copy + ONE write path (§4.1 — the
    # band-1 scalar op against the declared persisted keys)
    from sb.kernel.db import settings as db_settings

    writes: list[tuple[int, str, str]] = []

    async def fake_upsert(conn, *, guild_id, key, value):
        writes.append((int(guild_id), str(key), str(value)))
        return None

    monkeypatch.setattr(db_settings, "upsert_setting", fake_upsert)
    run(harness.send_command("!rpssettings default_mode chess",
                             persona="admin"))
    assert any("Setting `default_mode` updated to `chess`." in t
               for t in _texts(harness.take_calls()))
    run(harness.send_command("!rpssettings default_best_of 5",
                             persona="admin"))
    assert any("Setting `default_best_of` updated to `5`." in t
               for t in _texts(harness.take_calls()))
    assert writes == [(W_GUILD, "rps_default_mode", "chess"),
                      (W_GUILD, "rps_default_best_of", "5")]
    assert not economy.audit                     # settings touch no money


def test_rpssettings_bare_shows_the_read_view(skeleton):
    """Bare `!rpssettings` keeps the read view (the shipped command
    required both args — MissingRequiredArgument fired; unpinned shape,
    ledgered deviation)."""
    harness, economy, games, flags = skeleton
    run(harness.send_command("!rpssettings", persona="admin"))
    texts = _texts(harness.take_calls())
    assert any("⚙️ **RPS settings**" in t and "default_mode: `classic`" in t
               for t in texts)


def test_champion_frame_renders_exactly_once_under_a_settled_race(skeleton):
    """The #133-review cosmetic race, rps side: if a racing final
    resolution already claimed the champion render (state.settled), the
    second resolution must not re-announce the champion or re-run the
    payout — the in-memory check-and-set twin of the op's flag-row
    guard."""
    harness, economy, games, flags = skeleton
    from sb.domain.rps import tournament

    run(harness.send_command("!rpsregister", persona="admin"))
    calls = harness.take_calls()
    (join,) = _components(calls[0])
    reg_message_id = calls[0].response_id
    for persona in ("admin", "member"):
        run(harness.click(message_id=reg_message_id,
                          custom_id=join["custom_id"], persona=persona))
        harness.take_calls()
    state = tournament.get_state(W_GUILD)
    state.registration_opened_mono -= 601
    run(harness.send_command("!rpsstart classic 1", persona="admin"))
    calls = harness.take_calls()
    (match_call,) = [c for c in calls if (c.payload or {}).get("embeds")
                     and "Round 1" in c.payload["embeds"][0].get("title", "")]

    # the racing winner claimed the render between the two resolutions
    state.settled = True
    _, final_calls = _play_match(harness, match_call)
    texts = _texts(final_calls)
    assert not any("has won the RPS Tournament!" in t for t in texts)
    assert not any("💰 Payout" in t for t in texts)
    # payout op never ran for the loser: no money row, flag intact,
    # state not torn down by the losing racer
    assert not [a for a in economy.audit
                if a["reason"].startswith("rps:tournament")]
    assert flags.flags.get(W_GUILD) == "rps"
    assert tournament.state_or_none(W_GUILD) is not None
