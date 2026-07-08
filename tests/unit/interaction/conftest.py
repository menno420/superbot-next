"""Shared fixtures for the K8 resolver tests: a recording FakeResponder, a
duck-typed target spec, and clean resolver/lifecycle/cooldown state."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import pytest

import sb.kernel.lifecycle as lifecycle
from sb.kernel.authority import owner as owner_mod
from sb.kernel.interaction import cooldown as cooldown_mod
from sb.kernel.interaction.adapters import reset_adapter_ports_for_tests
from sb.kernel.interaction.predicates import reset_predicate_ports_for_tests
from sb.kernel.interaction.request import ActorRef, ResolveRequest, Surface, TargetRef
from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests
from sb.spec.outcomes import ReplyVisibility


class FakeResponder:
    def __init__(self, surface: Surface = Surface.SLASH):
        self.surface = surface
        self.acks: list[bool] = []
        self.denials: list[tuple[str, bool]] = []
        self.confirms: list = []
        self.modals: list = []
        self.rendered: list = []
        self._committed: ReplyVisibility | None = None

    def is_acked(self) -> bool:
        return bool(self.acks)

    def committed_visibility(self):
        return self._committed

    async def ack(self, *, ephemeral: bool) -> None:
        self.acks.append(ephemeral)
        self._committed = (ReplyVisibility.EPHEMERAL if ephemeral
                           else ReplyVisibility.PUBLIC)

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        self.denials.append((message, ephemeral))

    async def open_modal(self, modal_ref) -> None:
        self.modals.append(modal_ref)

    async def open_confirm(self, prompt) -> None:
        self.confirms.append(prompt)

    async def render(self, result) -> None:
        self.rendered.append(result)


@dataclass
class Spec:
    """Duck-typed routable spec carrying the pinned §3.0 fields."""

    authority_ref: str = ""
    enabled_when: str = ""
    visible_when: str = ""
    reply_visibility: object = None
    defer_mode: object = None
    cooldown: object = None
    route: object = None
    confirm: object = None
    effect: str = "read"
    owner_subsystem: str | None = None
    validate_args: object = None
    extras: dict = dc_field(default_factory=dict)


def make_request(spec: Spec, *, surface=Surface.SLASH, actor=None, guild_id=42,
                 channel_id=7, args=None, responder=None, confirmed=False,
                 request_id=None) -> ResolveRequest:
    responder = responder or FakeResponder(surface)
    kwargs = dict(
        surface=surface,
        target=TargetRef(key="probe", spec=spec),
        actor=actor or ActorRef(user_id=1, is_guild_operator=False,
                                is_bot_owner=False, is_dm=False,
                                member_tier="administrator"),
        guild_id=guild_id, channel_id=channel_id,
        args=args or {}, responder=responder, origin=object(),
        confirmed=confirmed,
    )
    if request_id is not None:
        kwargs["request_id"] = request_id
    return ResolveRequest(**kwargs)


@pytest.fixture(autouse=True)
def _clean_k8_state():
    lifecycle.reset_for_tests()
    lifecycle.set_phase(lifecycle.Phase.RUNNING)
    owner_mod.reset_for_tests()
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()
    reset_adapter_ports_for_tests()
    yield
    lifecycle.reset_for_tests()
    owner_mod.reset_for_tests()
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()
    reset_adapter_ports_for_tests()
