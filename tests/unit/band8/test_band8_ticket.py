"""Band 8 ticket slice — the shipped hub-control authority the goldens
don't carry: the "Post panel here" staff gate (views/tickets/hub.py ran
``is_ticket_staff`` BEFORE ``post_launcher``; at the v1 config-absent
epoch the cfg staff-role leg is vacuous, so the gate is exactly the
perms leg — ActorRef.is_guild_operator)."""

from __future__ import annotations

import asyncio

from sb.spec.outcomes import BLOCKED

run = asyncio.run


class FakeReq:
    def __init__(self, *, operator: bool, gid: int = 1, uid: int = 42):
        self.args = {}
        self.guild_id = gid
        self.channel_id = 9

        class _A:
            user_id = uid
            actor_type = "user"
            is_guild_operator = operator

        self.actor = _A()


def _post_panel():
    from sb.domain.ticket import handlers
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    return resolve(HandlerRef("ticket.post_panel"))


def test_post_panel_refuses_non_staff_with_the_shipped_byte():
    # shipped: any member can open the hub and SEE the button (the golden
    # pins it in sweep_ticket.json), but the callback re-checks staff —
    # "Only staff can post the ticket panel." (views/tickets/hub.py,
    # verbatim), never the not-configured lane.
    reply = run(_post_panel()(FakeReq(operator=False)))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Only staff can post the ticket panel."


def test_post_panel_staff_reaches_the_not_configured_lane():
    from sb.domain.ticket import service

    reply = run(_post_panel()(FakeReq(operator=True)))
    assert reply.outcome == BLOCKED
    assert reply.user_message == service.NOT_CONFIGURED_MSG
