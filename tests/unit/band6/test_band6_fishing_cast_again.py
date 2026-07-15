"""Fishing Cast-again continuation (review-doc gap 3): the cast
TERMINALS open the ``fishing.cast_result`` card whose single green
🎣 Cast again button re-runs the FULL cast path (oracle
disbot/views/fishing/cast_view.py ``_FishingDoneView`` @bbc524e,
doc-pinned :545/:562) — attached on the committed catch AND the
click-driven failures (premature spook / too-slow / fight snap), NEVER
on the timer-driven ignored-window terminals; never pre-disabled;
author-only; a refused re-cast (active line / no energy) answers the
guard's ephemeral error and the card stays untouched."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from tests.unit.band6.test_band6_fishing_minigame_timing import (
    GID,
    NOW,
    P1,
    ScriptRng,
    _arm_rng,
    _capture_result_panel,
    _commit_spy,
    _disarm_rng,
    _entry,
    _FakeReq,
    _freeze_clock,
    _no_commit,
    _reel_req,
    _route,
)

run = asyncio.run


# --- the spec: the oracle _FishingDoneView button, declaratively ---------------------


def test_cast_result_spec_declares_the_oracle_cast_again_button():
    """One green 🎣 Cast again action routing to fishing.cast_open (the
    oracle fishing_done:cast_again re-runs the full cast path), on an
    invoker-locked session panel — the cast panel's gating posture."""
    from sb.domain.fishing.panels import (
        CAST_RESULT_PANEL_ID,
        cast_result_spec,
        cast_spec,
    )
    from sb.spec.panels import ActionStyle, AnchorPolicy, Audience
    from sb.spec.refs import HandlerRef

    spec = cast_result_spec()
    assert spec.panel_id == CAST_RESULT_PANEL_ID
    assert spec.subsystem == "fishing"
    assert spec.session_lifecycle is True
    # the card opens off a click and must be a fresh, click-targetable
    # channel message (the blackjack-tournament CHANNEL_ANCHOR seam).
    assert spec.anchor_policy is AnchorPolicy.CHANNEL_ANCHOR
    (action,) = spec.actions
    assert action.action_id == "fishing_cast_again"
    assert action.label == "Cast again"
    assert action.emoji == "🎣"
    assert action.style is ActionStyle.SUCCESS
    assert action.handler == HandlerRef("fishing.cast_open")
    # author-only: the same invoker audience the cast panel locks on.
    assert spec.audience is Audience.INVOKER
    assert cast_spec().audience is Audience.INVOKER


def test_render_cast_result_composes_tone_and_never_disables(monkeypatch):
    """The renderer paints the handler-composed title/description with
    the terminal's tone and keeps the Cast again button ENABLED (the
    oracle view is never pre-disabled — gating happens at click time
    inside the cast path). Invoker lock rides the grammar render."""
    from sb.domain.fishing import panels
    from sb.domain.fishing.panels import cast_result_spec
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    def ctx(params):
        return PanelContext(
            bot=None, guild_id=GID, actor=SimpleNamespace(user_id=P1),
            channel_id=9, origin=PanelOrigin.INTERACTION,
            audience=Audience.INVOKER, locale=LocaleContext(),
            params=params)

    caught = run(panels._render_cast_result(cast_result_spec(), ctx({
        "result_title": "🎣 Caught it!",
        "result_desc": "You reeled in 🐟 a **Minnow**!",
        "result_style": "green"})))
    assert caught.embed.title == "🎣 Caught it!"
    assert caught.embed.description == "You reeled in 🐟 a **Minnow**!"
    assert caught.embed.style_token == "green"
    assert caught.invoker_lock == P1            # author-only
    (button,) = caught.components
    assert button.label == "Cast again"
    assert button.style == "success"
    assert button.disabled is False             # never pre-disabled

    failed = run(panels._render_cast_result(cast_result_spec(), ctx({
        "result_title": "",
        "result_desc": "🌀 You reeled too early — the fish darted off. "
                       "*Hold your nerve!*",
        "result_style": "red"})))
    assert failed.embed.title == ""
    assert failed.embed.style_token == "red"
    (button,) = failed.components
    assert button.disabled is False


# --- the terminals open (or don't open) the continuation card ------------------------


def test_catch_terminal_opens_the_result_card_with_cast_again(
        monkeypatch):
    """An in-window commit answers the SUCCESS-tone result card: the
    leg's after["message"] splits title-line / description onto the
    card params (the oracle _finish_caught embed + _FishingDoneView)."""
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import CAST_RESULT_PANEL_ID
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 5.0)      # bite 4.0, window 2.5

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome=SUCCESS, user_message=None,
            after={"cast": {"message": "🎣 Caught it!\nYou reeled in 🐟 "
                                       "a **Minnow**!"}})

    monkeypatch.setattr(engine, "run", fake_run)
    opened = _capture_result_panel(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is SUCCESS and reply.user_message is None
    assert opened == [(CAST_RESULT_PANEL_ID, {
        "result_title": "🎣 Caught it!",
        "result_desc": "You reeled in 🐟 a **Minnow**!",
        "result_style": "green"})]
    service.reset_pending_casts_for_tests()


def test_click_failure_terminal_opens_the_error_tone_card(monkeypatch):
    """A premature spook (a CLICK failure) opens the card in the error
    tone — the oracle attached the done view on exactly these."""
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import CAST_RESULT_PANEL_ID
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 0.5)      # pre-bite, grace 0
    _no_commit(monkeypatch)
    opened = _capture_result_panel(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is SUCCESS and reply.user_message is None
    assert opened == [(CAST_RESULT_PANEL_ID, {
        "result_title": "",
        "result_desc": ("🌀 You reeled too early — the fish darted off. "
                        "*Hold your nerve!*"),
        "result_style": "red"})]
    service.reset_pending_casts_for_tests()


def test_timer_expiry_never_opens_the_continuation_card(monkeypatch):
    """The TIMER-driven got-away (the unprompted window expiry) stays
    disable-only — the oracle attached NO done view on an ignored
    window; the terminal edit rides the push seam, never open_panel."""
    from sb.domain.fishing import service

    opened = _capture_result_panel(monkeypatch)

    async def main():
        entry = _entry(cast_at_f=0.0, bite_at_f=0.02,
                       reaction_window=0.02)
        entry["panel_key"] = "424242"
        entry["guild_id"] = GID
        service._PENDING_CASTS[(P1, GID)] = entry
        service._arm_bite_timers((P1, GID), entry)
        await asyncio.sleep(0.3)
        assert (P1, GID) not in service._PENDING_CASTS

    run(main())
    assert opened == []                        # no continuation card
    service.reset_pending_casts_for_tests()


def test_stale_line_click_stays_a_text_terminal(monkeypatch):
    """A dead-line Reel (the 45 s timed-out / replaced cast) is the
    ignored-window terminal — text only, no continuation card."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 46.0)
    _no_commit(monkeypatch)
    opened = _capture_result_panel(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...the line goes slack. The fish got away.*")
    assert opened == []
    service.reset_pending_casts_for_tests()


# --- the Cast again click: the full cast path re-runs, guards intact ----------------


def _cast_route():
    from sb.domain.fishing import service
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    return resolve(HandlerRef("fishing.cast_open"))


def test_cast_again_click_reruns_cast_open_with_a_fresh_cast(
        monkeypatch):
    """The continuation flow: reel a catch (the result card opens),
    then the Cast again click — the card's HandlerRef routes straight
    to fishing.cast_open — parks a FRESH pending cast (new token, new
    rolls) and opens a new cast panel."""
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import CAST_PANEL_ID
    from sb.spec.outcomes import SUCCESS
    from tests.unit.band6.test_band6_fishing_cast_wiring import (
        _install_world,
    )

    reel = _route()                             # resets pending casts
    _freeze_clock(monkeypatch, NOW + 5.0)
    seen = _commit_spy(monkeypatch)
    opened = _capture_result_panel(monkeypatch)
    first = _entry(token=7)                     # a mid-session cast id
    service._PENDING_CASTS[(P1, GID)] = first
    reply = run(reel(_reel_req(token=7)))
    assert reply.outcome is SUCCESS
    assert opened[0][0] == "fishing.cast_result"
    assert len(seen) == 1
    assert (P1, GID) not in service._PENDING_CASTS
    # …the Cast again click (the minted binding routes to cast_open).
    cast = _cast_route()
    _install_world(monkeypatch)
    rng = ScriptRng(randoms=[0.99], uniforms=[1.0, 5.0])
    _arm_rng(rng)
    try:
        again = run(cast(_FakeReq(args={"session_action":
                                        "fishing_cast_again"})))
    finally:
        _disarm_rng()
    assert again.outcome is SUCCESS
    fresh = service._PENDING_CASTS[(P1, GID)]
    assert fresh is not first
    assert fresh["token"] != first["token"]     # a fresh cast, new token
    assert opened[-1][0] == CAST_PANEL_ID       # a new cast panel opened
    service.reset_pending_casts_for_tests()


def test_gated_cast_again_click_errors_without_killing_the_card(
        monkeypatch):
    """The oracle click-time gating: a Cast again refused by cast_open's
    own guards (a line already in the water / out of energy) answers
    the guard's error reply and neither opens a new panel nor touches
    the live result-card session (cast_open never edits/expires it)."""
    from sb.domain.fishing import service
    from sb.kernel.panels import engine as panels_engine
    from sb.spec.outcomes import BLOCKED
    from tests.unit.band6.test_band6_fishing_cast_wiring import (
        _install_world,
    )

    cast = _cast_route()
    service.reset_pending_casts_for_tests()
    _freeze_clock(monkeypatch, NOW)
    opened = _capture_result_panel(monkeypatch)
    sessions_before = dict(panels_engine._sessions)

    # guard 1: a line already in the water.
    _install_world(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry(rolled_at=NOW)
    busy = run(cast(_FakeReq()))
    assert busy.outcome is BLOCKED
    assert busy.user_message == (
        "🎣 You've already got a line in the water — reel that one in "
        "first!")

    # guard 2: out of energy (fresh slot, drained bar).
    service.reset_pending_casts_for_tests()
    _install_world(monkeypatch, energy=(0, NOW))
    broke = run(cast(_FakeReq()))
    assert broke.outcome is BLOCKED
    assert broke.user_message.startswith(
        "🎣 You're out of energy — let the line rest.")

    assert opened == []                        # no panel opened either way
    assert dict(panels_engine._sessions) == sessions_before  # card intact
    service.reset_pending_casts_for_tests()
