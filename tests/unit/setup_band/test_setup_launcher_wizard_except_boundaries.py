"""Characterization of the LAST uncovered setup-band except-boundary
sites — the ``launcher.py`` join/render/button swallows and the
``wizard.py`` gate/refresh/review swallows the moderation pin (#516), the
count/list soft-fail audit (#519) and the final_review + essential_steps
audit (#526) did not reach. This slice CLOSES backlog item C1 (the
setup-band except-density audit): every ``except Exception`` in the
setup band is now pinned to its intended boundary.

Each swallow is forced to RAISE and the observed boundary asserted:

* **fail-CLOSED** — the swallow surfaces a ``BLOCKED`` refusal (the
  launcher advisor read, the wizard deterministic-rerun read, the
  wizard staging write);
* **fail-SOFT / degrade** — the swallow degrades to a default: a
  session-read failure ⇒ the fresh launcher card / no prior pointers /
  the not-complete refusal, a channel-directory read failure ⇒ "no
  sendable channel" (``None``), the gate's owner-directory read failure
  ⇒ deny;
* **best-effort / logged-never-raised** — the swallow logs and
  continues; the surface still answers and NO write is masked (the
  launcher ``mark_in_progress`` marker, the launcher ``start_session``
  refresh, the wizard panel refresh).

**No fail-open.** None of these swallows masks a real write that then
falsely reports success: the fail-CLOSED arms refuse, the fail-SOFT arms
feed a display / resolve a target and take a non-destructive default,
and the best-effort arms guard a trailing marker/refresh/re-render whose
primary mutation already committed (or never ran). Additive, DB-free,
changes NO product behavior (mirrors
``test_setup_final_review_and_essential_except_boundaries.py`` /
``test_setup_moderation_except_boundaries.py`` /
``test_setup_softfail_boundaries.py``).

Already covered elsewhere, so NOT duplicated here: launcher L310
``ensure_setup_channel`` fail-SOFT + L423 handler isolation
(test_guild_join_launcher.py), wizard L391 gate session-read fail-CLOSED
+ L619 set_depth fail-CLOSED + L747 essential_save apply fail-CLOSED
(test_wizard_interior.py).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import wizard

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()


GID = 4242


def _event(**kw):
    from sb.kernel.interaction.guild_events import GuildJoinEvent

    defaults = dict(guild_id=GID, guild_name="Test Guild", owner_id=99,
                    system_channel_id=None)
    defaults.update(kw)
    return GuildJoinEvent(**defaults)


def _req(*, user_id=42, guild_id=99, operator=False, args=None, message_id=777):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=user_id, is_guild_operator=operator),
        guild_id=guild_id,
        args=dict(args or {}),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)),
        request_id="req-1",
        confirmed=False,
    )


@dataclass
class _DCReq:
    """A dataclass request for the ONE handler that calls
    ``dataclasses.replace(req, …)`` directly (launcher_suggestions) — a
    ``SimpleNamespace`` is not a dataclass and would raise TypeError at
    that seam."""

    actor: object
    guild_id: int
    args: dict = field(default_factory=dict)
    origin: object = None
    request_id: str = "req-1"
    confirmed: bool = False


def _resolve(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _rec(subsystem="logging", binding="audit_channel", confidence="high",
         target_id=1234, target_name="audit", mode="bind"):
    from sb.domain.setup.plan import SetupRecommendation

    return SetupRecommendation(
        subsystem=subsystem, binding_name=binding, target_kind="channel",
        target_id=target_id, target_name=target_name,
        confidence=confidence,
        reason=f"channel `{target_name}` matches token `{binding}` "
               f"({confidence})",
        mode=mode)


def _draft(*recs):
    from sb.domain.setup.plan import SetupPlanDraft

    return SetupPlanDraft(recommendations=tuple(recs))


class _Gate:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


# =======================================================================================
# launcher.py — the fail-SOFT degrade swallows
# =======================================================================================


def test_render_session_read_failure_degrades_to_the_fresh_card(monkeypatch):
    """L225 — the launcher render reads the session row to parameterize its
    description/accent; a failed read degrades ``session`` to ``None`` ⇒ the
    plain fresh card (no ``**Status:**`` suffix, blurple), never propagating."""
    from sb.domain.setup import launcher, store
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin

    async def boom(guild_id, conn=None):
        raise RuntimeError("session row unreadable")

    monkeypatch.setattr(store, "get_session_row", boom)
    spec = launcher.launcher_spec()
    ctx = PanelContext(bot=None, guild_id=GID, actor=launcher._join_actor(),
                       channel_id=1, origin=PanelOrigin.ANCHOR,
                       audience=spec.audience, locale=LocaleContext(),
                       params={}, surface=None)

    rendered = run(launcher._render_launcher(spec, ctx))

    assert rendered is not None
    # degraded to session=None ⇒ the fresh card, never the session suffixes.
    assert "**Status:**" not in rendered.embed.description
    assert rendered.embed.style_token == "blurple"


def test_join_session_read_failure_degrades_to_no_prior_pointers(monkeypatch):
    """L303 — the workspace path reads the prior session row to short-circuit
    a rejoin (keep the live launcher's ids, no double-post). A failed read
    degrades ``row`` to ``None`` ⇒ the short-circuit is skipped and the
    launcher posts fresh; the join lane still answers ``workspace`` and NEVER
    crashes the feed."""
    from sb.domain.setup import launcher, service, store
    from sb.kernel.panels import engine as panel_engine
    from sb.kernel.workflow import engine as workflow_engine

    async def read_boom(guild_id, conn=None):
        raise RuntimeError("session row unreadable")

    async def ensure(guild_id, invoker_id, delegated=()):
        return 555, False   # an EXISTING channel, NOT freshly created

    posts: list[int] = []

    async def post(ref, *, guild_id, channel_id, actor, params=None,
                   mention_user_ids=()):
        posts.append(channel_id)
        return 777

    async def wf(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS, ok=True, user_message=None)

    monkeypatch.setattr(store, "get_session_row", read_boom)
    monkeypatch.setattr(service, "ensure_setup_channel", ensure)
    monkeypatch.setattr(panel_engine, "post_anchored_panel", post)
    monkeypatch.setattr(workflow_engine, "run", wf)

    counts = run(launcher.handle_guild_join(_event()))

    # row=None ⇒ the rejoin short-circuit is skipped ⇒ a fresh post lands
    # (created=False ⇒ no owner-ping content); the surface still answers.
    assert posts == [555]
    assert counts["surface"] == "workspace"
    assert counts["channel_id"] == 555
    assert counts["message_id"] == 777


def test_pick_launcher_channel_directory_read_failure_degrades_to_none(
        monkeypatch):
    """L349 — the safest-channel ladder reads the channel-directory cache; a
    failed read degrades to ``None`` (no sendable channel), which routes the
    fallback into the honest "nothing was sendable" terminal, never raising."""
    from sb.domain.channel import service as channel_service
    from sb.domain.setup import launcher

    class _Dir:
        async def list_channels(self, guild_id):
            raise RuntimeError("gateway cache unreadable")

    monkeypatch.setattr(channel_service, "active_directory", lambda: _Dir())

    assert run(launcher._pick_launcher_channel(GID, None)) is None


def test_summary_session_read_failure_degrades_to_the_not_complete_refusal(
        monkeypatch):
    """L527 — View Summary (admin-gated) reads the session row to check for a
    complete setup; a failed read degrades ``row`` to ``None`` ⇒ the shipped
    not-complete refusal (BLOCKED). The conservative degrade: an unreadable
    session NEVER shows a summary, it refuses."""
    from sb.domain.setup import store

    async def boom(guild_id, conn=None):
        raise RuntimeError("session row unreadable")

    monkeypatch.setattr(store, "get_session_row", boom)

    reply = run(_resolve("setup.launcher_summary")(_req(operator=True)))

    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._view_summary).
    assert reply.user_message == (
        "Setup is not complete yet. Run **Start Setup** to finish the "
        "wizard before viewing the summary.")


# =======================================================================================
# launcher.py — the fail-CLOSED advisor read
# =======================================================================================


def test_suggestions_advisor_failure_fails_closed(monkeypatch):
    """L490 — Smart Suggestions (apply-gated) runs the deterministic advisor
    BEFORE opening the review panel; a raise fails CLOSED with the shipped
    refusal, never opens the panel and never stages anything."""
    from sb.domain.setup import plan, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def boom(guild_id):
        raise RuntimeError("advisor exploded")

    monkeypatch.setattr(plan, "suggest", boom)

    reply = run(_resolve("setup.launcher_suggestions")(
        _DCReq(actor=SimpleNamespace(user_id=42), guild_id=99)))

    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._suggestions advisor-failed).
    assert reply.user_message == (
        "Smart Suggestions failed. Run **Run Readiness Scan** for a "
        "deterministic baseline.")


# =======================================================================================
# launcher.py — the best-effort / logged-never-raised arms
# =======================================================================================


def test_suggestions_mark_in_progress_failure_is_logged_never_raised(
        monkeypatch):
    """L511 — after the review panel opens over a good draft, marking the
    session in-progress is best-effort: a K7 raise is logged and swallowed
    and the handler still returns ``None`` (the panel already opened; the
    marker is a trailing status write that masks nothing)."""
    from sb.domain.setup import plan, wizard
    from sb.kernel.panels import engine as panel_engine
    from sb.kernel.workflow import engine as workflow_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def good_draft(guild_id):
        return _draft(_rec())

    opened: list[str] = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    async def mark_boom(ref, ctx):
        raise RuntimeError("mark_in_progress op raised")

    monkeypatch.setattr(plan, "suggest", good_draft)
    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    monkeypatch.setattr(workflow_engine, "run", mark_boom)

    reply = run(_resolve("setup.launcher_suggestions")(
        _DCReq(actor=SimpleNamespace(user_id=42), guild_id=99)))

    # the panel opened; the marker raise was swallowed; no exception escapes.
    assert reply is None
    assert opened == ["setup.suggestions_card"]


def test_repost_start_session_refresh_failure_is_logged_never_raised(
        monkeypatch):
    """L570 — Repost launcher posts the card, then refreshes the session row
    (best-effort): a K7 raise is logged and swallowed and the shipped SUCCESS
    ack still answers (the launcher already posted; the refresh is a trailing
    pointer write that masks nothing)."""
    from sb.domain.setup import handlers as setup_handlers
    from sb.domain.setup import launcher
    from sb.kernel.workflow import engine as workflow_engine

    async def pick(guild_id, system_channel_id):
        return 31

    async def post(guild_id, channel_id, *, content=None, mention_user_ids=()):
        return 888

    async def identity(guild_id):
        return "Test Guild", 99

    async def refresh_boom(ref, ctx):
        raise RuntimeError("start_session refresh op raised")

    monkeypatch.setattr(launcher, "_pick_launcher_channel", pick)
    monkeypatch.setattr(launcher, "_post_launcher_panel", post)
    monkeypatch.setattr(setup_handlers, "_guild_identity", identity)
    monkeypatch.setattr(workflow_engine, "run", refresh_boom)

    reply = run(_resolve("setup.launcher_repost")(_req(operator=True)))

    assert reply.outcome == SUCCESS
    # shipped copy, verbatim ("Launcher reposted in {where}.").
    assert reply.user_message == "Launcher reposted in <#31>."


# =======================================================================================
# wizard.py — the gate's owner-directory read (fail-SOFT ⇒ deny)
# =======================================================================================


def test_gate_owner_directory_read_failure_degrades_to_deny(monkeypatch):
    """L404 — with no owner id on the session row, ``can_apply_setup`` falls
    back to the guild directory for the owner id; a failed read degrades
    ``owner_id`` to ``0`` ⇒ the gate DENIES (never widens access), never
    raising. The fail-SOFT that must stay conservative — an unreadable owner
    is a closed door."""
    from sb.domain.setup import store, wizard
    from sb.domain.utility import service as utility_service

    async def sessionless(guild_id, conn=None):
        return None      # readable but empty ⇒ no owner id on the row

    class _Dir:
        async def guild_info(self, guild_id):
            raise RuntimeError("headless directory")

    monkeypatch.setattr(store, "get_session_row", sessionless)
    monkeypatch.setattr(utility_service, "guild_directory", lambda: _Dir())

    # user 13 is neither platform owner nor delegated ⇒ the owner leg is the
    # only path, and the unreadable owner closes it.
    assert run(wizard.can_apply_setup(_req(user_id=13))) is False


# =======================================================================================
# wizard.py — the best-effort panel refresh
# =======================================================================================


def test_refresh_own_panel_failure_degrades_to_false(monkeypatch):
    """L552 — the clicked-panel in-place re-render is best-effort: a
    ``refresh_session_view`` raise is logged and swallowed, and the helper
    returns ``False`` so the caller's text reply still lands (the re-render
    is cosmetic; the click's own mutation already committed)."""
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panel_engine

    async def boom(req, *, message_key, params, expire=False):
        raise RuntimeError("live session missing")

    monkeypatch.setattr(panel_engine, "refresh_session_view", boom)

    assert run(wizard._refresh_own_panel(_req(), {"any": "param"})) is False


# =======================================================================================
# wizard.py — the fail-CLOSED review reads/writes
# =======================================================================================


def test_review_rerun_advisor_failure_fails_closed(monkeypatch):
    """L859 — Rerun deterministic-only re-runs the advisor and replaces the
    draft in place; a raise fails CLOSED with the shipped refusal and leaves
    the draft unchanged (never a partial swap)."""
    from sb.domain.setup import plan, wizard

    wizard.seed_review_state(99, 42, _draft(_rec()))

    async def boom(guild_id):
        raise RuntimeError("deterministic rerun exploded")

    monkeypatch.setattr(plan, "suggest", boom)

    reply = run(_resolve("setup.review_rerun")(_req()))

    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (main_panel._rerun_deterministic).
    assert reply.user_message == (
        "Deterministic rerun failed; the draft is unchanged.")


def test_review_stage_staging_failure_fails_closed(monkeypatch):
    """L897 — Stage & open Final review (apply-gated, at least one accept)
    writes the accepted set into the K9 draft; a staging raise fails CLOSED
    with the shipped refusal, never opening Final Review on an unstaged
    draft."""
    from sb.domain.setup import wizard

    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    state.add(_rec())        # at least one accept ⇒ past the empty guard
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def boom(guild_id, accepted):
        raise RuntimeError("draft store write failed")

    monkeypatch.setattr(wizard, "stage_accepted", boom)

    reply = run(_resolve("setup.review_stage")(_req()))

    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (main_panel._stage_final).
    assert reply.user_message == (
        "Could not stage the accepted suggestions — see logs.")
