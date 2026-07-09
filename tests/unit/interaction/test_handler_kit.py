"""ORDER 004 item 4 — the shared thin-handler kit replaces the 22× copied
Reply/_ctx_from_req boilerplate. Pins: the duck-shape, the request→context
mapping, and that NO domain module re-declares its own Reply."""

from __future__ import annotations

from pathlib import Path


def test_reply_is_the_frozen_duck_shape():
    import dataclasses

    from sb.kernel.interaction.handler_kit import Reply

    r = Reply("success", "done")
    assert (r.outcome, r.user_message) == ("success", "done")
    assert dataclasses.is_dataclass(Reply)
    try:
        r.outcome = "blocked"
        raise AssertionError("Reply must be frozen")
    except dataclasses.FrozenInstanceError:
        pass


def test_ctx_from_request_maps_the_resolve_request():
    from sb.kernel.interaction.handler_kit import ctx_from_request

    class _Actor:
        user_id = 7

    class _Req:
        actor = _Actor()
        guild_id = "42"
        request_id = "req-1"
        confirmed = True

    ctx = ctx_from_request(_Req(), {"key": "v"})
    assert ctx.guild_id == 42
    assert ctx.request_id == "req-1"
    assert ctx.confirmed is True
    assert dict(ctx.params) == {"key": "v"}
    assert ctx.actor.user_id == 7


def test_ctx_from_request_defaults_missing_guild_to_zero():
    from sb.kernel.interaction.handler_kit import ctx_from_request

    class _Req:
        actor = object()
        guild_id = None
        request_id = "req-2"
        confirmed = False

    assert ctx_from_request(_Req(), {}).guild_id == 0


def test_no_domain_module_redeclares_reply():
    """The collapse stays collapsed: sb/domain declares no local Reply and
    no local _ctx_from_req body (import-alias only)."""
    domain = Path(__file__).resolve().parents[3] / "sb" / "domain"
    offenders = []
    for path in domain.rglob("*.py"):
        src = path.read_text()
        if "class Reply" in src or "def _ctx_from_req" in src:
            offenders.append(str(path))
    assert offenders == []
