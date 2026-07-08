"""The chokepoint's fixed order (spec 02 §3.2) + the absorption edits."""

import asyncio

import sb.kernel.lifecycle as lifecycle
from sb.kernel.authority import owner as owner_mod
from sb.kernel.authority.channel_access import CommandAccessSnapshot
from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.interaction.request import ActorRef, Surface
from sb.kernel.interaction.resolve import (
    install_access_policy_reader,
    install_panel_engine,
    install_transparency_sink,
    install_visibility_reader,
    resolve,
)
from sb.spec.outcomes import (
    BLOCKED,
    SUCCESS,
    DeferMode,
    DenialReason,
    ErrorClass,
    ReplyVisibility,
)
from sb.spec.refs import HandlerRef, PanelRef, clear_ref_table, handler
from tests.unit.interaction.conftest import FakeResponder, Spec, make_request


def _run(req):
    return asyncio.run(resolve(req))


def test_step0_draining_is_silent_every_surface():
    lifecycle.set_phase(lifecycle.Phase.DRAINING)
    for surface in (Surface.SLASH, Surface.PREFIX, Surface.COMPONENT,
                    Surface.MODAL, Surface.NL_INTENT):
        responder = FakeResponder(surface)
        result = _run(make_request(Spec(), surface=surface, responder=responder))
        assert result.outcome == BLOCKED
        assert result.reason is DenialReason.DRAINING
        assert result.reply_visibility is ReplyVisibility.SILENT
        assert result.user_message is None
        assert not responder.denials and not responder.acks    # NO ack


def test_step1_authority_denial_is_preack_ephemeral_with_engine_copy():
    responder = FakeResponder()
    result = _run(make_request(Spec(authority_ref="administrator"),
                               actor=ActorRef(1, False, False, False,
                                              member_tier="user"),
                               responder=responder))
    assert result.reason is DenialReason.AUTHORITY
    assert result.error_class is ErrorClass.DENIED
    # RC-14: the copy IS the K6 engine-generated denial_message.
    assert responder.denials == [(
        "You need the **administrator** role (or higher) to use this.", True)]
    assert not responder.acks                                   # denial IS the ack


def test_step2_enabled_when_gate_denies_disabled():
    result = _run(make_request(Spec(enabled_when="flag:beta")))
    assert result.reason is DenialReason.DISABLED   # flag reader default-closed


def test_step2_visibility_gate():
    async def hidden(guild_id, subsystem):
        return False
    install_visibility_reader(hidden)
    result = _run(make_request(Spec()))
    assert result.reason is DenialReason.VISIBILITY


def test_step2_channel_access_threads_owner_override_rc4():
    async def policy(guild_id):
        return CommandAccessSnapshot(mode="disabled_except_bootstrap")
    install_access_policy_reader(policy)

    denied = _run(make_request(Spec()))
    assert denied.reason is DenialReason.CHANNEL

    class Cfg:
        BOT_OWNER_USER_ID = 1
        EXTRA_OWNER_USER_IDS = ()
    owner_mod.install_owner_config(Cfg())          # actor user_id=1 IS the owner

    emitted = []

    class Sink:
        async def emit(self, audit):
            emitted.append(audit)

        async def flush_digest(self):
            return None

    install_transparency_sink(Sink())
    allowed = _run(make_request(Spec()))           # L-12: override bypasses ANY restriction
    assert allowed.outcome == BLOCKED or allowed.outcome == SUCCESS
    assert allowed.reason is not DenialReason.CHANNEL
    # RC-5: the channel leg's would-deny fires the transparency audit.
    assert len(emitted) == 1
    assert emitted[0].would_deny_reason is DenialReason.CHANNEL


def test_step2b_argument_validation_user_error():
    def validator(args):
        raise ValidatorError("amount")
    result = _run(make_request(Spec(validate_args=validator)))
    assert result.reason is DenialReason.USER_ERROR
    assert result.error_class is ErrorClass.USER_ERROR
    assert result.retryable


def test_step3_cooldown_denies_with_retry_after():
    spec = Spec(cooldown=60.0)
    first = _run(make_request(spec))
    assert first.reason is not DenialReason.COOLDOWN
    second = _run(make_request(spec))
    assert second.reason is DenialReason.COOLDOWN
    assert second.retryable and "try again" in second.user_message


def test_ack_boundary_commits_lane_default_visibility():
    clear_ref_table()

    @handler("probe.read")
    async def _read(req):
        return None

    # TIER lane ("user") => PUBLIC default; SLASH + HandlerRef => AUTO defer.
    responder = FakeResponder()
    result = _run(make_request(Spec(authority_ref="user",
                                    route=HandlerRef("probe.read")),
                               responder=responder))
    assert responder.acks == [False]               # deferred PUBLIC (not ephemeral)
    assert result.reply_visibility is ReplyVisibility.PUBLIC
    # CAPABILITY lane ("") => EPHEMERAL default.
    responder2 = FakeResponder()
    _run(make_request(Spec(route=HandlerRef("probe.read")), responder=responder2))
    assert responder2.acks == [True]
    clear_ref_table()


def test_defer_mode_none_for_panel_and_prefix():
    clear_ref_table()
    opened = []

    async def panel_engine(ref, req):
        opened.append(ref.name)
    install_panel_engine(panel_engine)

    responder = FakeResponder()
    result = _run(make_request(Spec(route=PanelRef("home")), responder=responder))
    assert not responder.acks                      # panel render IS the ack
    assert opened == ["home"] and result.outcome == SUCCESS
    clear_ref_table()


def test_explicit_defer_mode_modal():
    responder = FakeResponder()
    _run(make_request(Spec(defer_mode=DeferMode.MODAL), responder=responder))
    assert len(responder.modals) == 1
