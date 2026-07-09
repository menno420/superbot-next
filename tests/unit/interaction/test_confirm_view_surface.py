"""The S9b confirm surface's kernel legs (frozen L0 spec 02 §3.2 step 3):
the Cancel control's DECLINED terminal, the cancelled-request fence on the
confirmed re-entry, and the rendered decline copy. Hermetic + roster-free —
duck-typed interactions, no discord import, no sb.manifest import."""

from __future__ import annotations

import asyncio

from sb.kernel.interaction.adapters import install_target_index
from sb.kernel.interaction.adapters.component import (
    CONFIRM_CANCEL_PREFIX,
    dispatch_component,
)
from sb.kernel.interaction.request import Surface, TargetRef
from sb.kernel.interaction.resolve import cancel_pending_confirm, resolve
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.outcomes import DECLINED, DenialReason
from sb.spec.refs import WorkflowRef, workflow
from tests.unit.interaction.conftest import FakeResponder, Spec, make_request


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _register_confirm_op(op_key: str) -> CompoundOpSpec:
    @workflow(f"{op_key}.leg")
    async def _leg(conn, ctx):  # pragma: no cover — never run here
        raise AssertionError("leg must not run")

    return REGISTRY.register(CompoundOpSpec(
        op_key=op_key, domain="probe", lane=WorkflowLane.DOMAIN,
        authority_ref="",
        legs=(LegSpec("leg", LegKind.DB, WorkflowRef(f"{op_key}.leg"),
                      "irreversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb="probe_confirmed",
        confirmation=ConfirmationSpec(reversibility="irreversible",
                                      challenge=Challenge.TYPED_PHRASE),
    ))


def _cancel_interaction(custom_id: str):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=777,
        data={"custom_id": custom_id},
        user=SimpleNamespace(id=1),
        guild=SimpleNamespace(id=42, owner_id=99),
        channel_id=7,
    )


class TestCancelTerminal:
    def test_cancel_click_is_the_declined_terminal(self):
        responder = FakeResponder(Surface.COMPONENT)
        result = run(dispatch_component(
            _cancel_interaction(f"{CONFIRM_CANCEL_PREFIX}probe:rid-1"),
            responder=responder))
        assert result.outcome == DECLINED
        assert result.reason is DenialReason.CONFIRM_DECLINED
        assert result.request_id == "rid-1"
        # the decline copy RENDERS (the click must answer)
        assert [r.user_message for r in responder.rendered] == [
            "Cancelled — nothing was done."]

    def test_confirm_click_after_cancel_declines_without_dispatch(self):
        _register_confirm_op("probe.cancel_fence_op")
        spec = Spec(route=WorkflowRef("probe.cancel_fence_op"))

        # 1. prompt (stashes args under the request_id)
        responder = FakeResponder(Surface.PREFIX)
        first = run(resolve(make_request(
            spec, surface=Surface.PREFIX, responder=responder,
            args={"argv": ("<@9>",)})))
        assert first.workflow is None and len(responder.confirms) == 1
        rid = responder.confirms[0].request_id

        # 2. Cancel clicked
        cancel_responder = FakeResponder(Surface.COMPONENT)
        run(dispatch_component(
            _cancel_interaction(f"{CONFIRM_CANCEL_PREFIX}probe:{rid}"),
            responder=cancel_responder))

        # 3. a late Confirm click gets DECLINED — the op leg never runs
        late = FakeResponder(Surface.COMPONENT)
        result = run(resolve(make_request(
            spec, surface=Surface.COMPONENT, confirmed=True,
            request_id=rid, responder=late)))
        assert result.outcome == DECLINED
        assert result.reason is DenialReason.CONFIRM_DECLINED
        assert [r.user_message for r in late.rendered] == [
            "This action was cancelled."]

    def test_cancel_pending_confirm_reports_whether_a_stash_existed(self):
        _register_confirm_op("probe.cancel_stash_op")
        spec = Spec(route=WorkflowRef("probe.cancel_stash_op"))
        responder = FakeResponder(Surface.PREFIX)
        run(resolve(make_request(
            spec, surface=Surface.PREFIX, responder=responder,
            args={"argv": ("x",)})))
        rid = responder.confirms[0].request_id
        assert cancel_pending_confirm(rid) is True
        assert cancel_pending_confirm(rid) is False       # idle re-cancel is fine
        assert cancel_pending_confirm("never-prompted") is False

    def test_double_confirm_renders_the_already_confirmed_copy(self, monkeypatch):
        from sb.kernel.workflow import engine as engine_mod
        from sb.kernel.workflow.result import WorkflowResult
        from sb.spec.authority import Lane

        _register_confirm_op("probe.double_click_op")
        ran: list[int] = []

        async def fake_run(route, ctx):
            ran.append(1)
            return WorkflowResult(
                mutation_id="m1", guild_id=ctx.guild_id, domain="probe",
                operation="probe.double_click_op", outcome="success",
                reversibility="irreversible", lane=Lane.TIER)

        monkeypatch.setattr(engine_mod, "run", fake_run)
        spec = Spec(route=WorkflowRef("probe.double_click_op"))
        responder = FakeResponder(Surface.PREFIX)
        run(resolve(make_request(
            spec, surface=Surface.PREFIX, responder=responder)))
        rid = responder.confirms[0].request_id

        first = FakeResponder(Surface.COMPONENT)
        assert run(resolve(make_request(
            spec, surface=Surface.COMPONENT, confirmed=True, request_id=rid,
            responder=first))).outcome == "success"
        assert ran == [1]

        second = FakeResponder(Surface.COMPONENT)
        result = run(resolve(make_request(
            spec, surface=Surface.COMPONENT, confirmed=True, request_id=rid,
            responder=second)))
        assert result.outcome == DECLINED and ran == [1]
        assert [r.user_message for r in second.rendered] == [
            "This action was already confirmed."]


class TestConfirmViewHelpers:
    """The pure (discord-free) confirm_view helpers."""

    def test_custom_id_grammar(self):
        from sb.adapters.discord import confirm_view as cv

        assert cv.confirm_custom_id("kick", "r1") == "sb.confirm:kick:r1"
        assert cv.open_custom_id("kick", "r1") == "sb.confirm.open:kick:r1"
        assert cv.cancel_custom_id("kick", "r1") == f"{CONFIRM_CANCEL_PREFIX}kick:r1"

    def test_expected_phrase_is_the_final_name_segment(self):
        from sb.adapters.discord import confirm_view as cv

        assert cv.expected_phrase("kick") == "kick"
        assert cv.expected_phrase("moderation.kick") == "kick"
        assert cv.phrase_matches("kick", " KICK ")
        assert not cv.phrase_matches("kick", "ban")
        assert not cv.phrase_matches("kick", None)

    def test_typed_challenges(self):
        from sb.adapters.discord import confirm_view as cv

        assert cv.is_typed_challenge(Challenge.TYPED_PHRASE)
        assert cv.is_typed_challenge(Challenge.TYPED_HASH)
        assert not cv.is_typed_challenge(Challenge.BUTTON)


class TestTextFallback:
    """Without the discord package the responders keep the v1 text prompt
    (the ledgered fallback — hermetic contexts still get a re-entry handle)."""

    def test_message_responder_falls_back_to_the_text_prompt(self, monkeypatch):
        from sb.adapters.discord import confirm_view as cv
        from sb.adapters.discord.responders import MessageResponder
        from sb.kernel.interaction.request import ConfirmPrompt

        monkeypatch.setattr(cv, "discord_ui", None)
        replies: list = []

        class Ctx:
            author = None

            async def reply(self, content=None, **kwargs):
                replies.append((content, kwargs))

        prompt = ConfirmPrompt(target_key="kick", request_id="r9",
                               challenge=Challenge.TYPED_PHRASE)
        run(MessageResponder(Ctx()).open_confirm(prompt))
        assert replies == [(
            "Are you sure? (confirm id: `sb.confirm:kick:r9`)", {})]

    def test_interaction_responder_falls_back_to_the_text_prompt(self, monkeypatch):
        from types import SimpleNamespace

        from sb.adapters.discord import confirm_view as cv
        from sb.adapters.discord.responders import InteractionResponder
        from sb.kernel.interaction.request import ConfirmPrompt

        monkeypatch.setattr(cv, "discord_ui", None)
        sent: list = []

        async def send_message(message, *, ephemeral=False, **kwargs):
            sent.append((message, ephemeral))

        interaction = SimpleNamespace(
            response=SimpleNamespace(send_message=send_message,
                                     is_done=lambda: False),
            user=SimpleNamespace(id=1))
        prompt = ConfirmPrompt(target_key="kick", request_id="r9",
                               challenge=Challenge.BUTTON)
        run(InteractionResponder(interaction).open_confirm(prompt))
        assert sent == [(
            "Are you sure? (confirm id: `sb.confirm:kick:r9`)", True)]


# keep the import referenced (roster-free hygiene: no manifest import rode in)
_ = (install_target_index, TargetRef)
