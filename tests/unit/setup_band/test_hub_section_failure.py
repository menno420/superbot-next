"""The hub per-section failure notice (night-tail-3 — the #444
deferral's shared catch seam, sb/domain/setup/panels.py
``_hub_section_dispatch``).

DB-free like the wizard-interior suite: the notice push + section
routes are monkeypatched at their module functions. The notice bytes
assert against the in-repo exemplar the #444 lane pinned
(test_section_recovery.test_notice_render_composes_the_pushed_embed:
title "⚠️ Section `channels` failed", description "See logs for
details.", style red) — the sizing source is the #444 card's ledgered
deferral (.sessions/2026-07-13-night-recovery-view.md)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_refs():
    import sb.manifest.setup as m

    m.ENSURE_REFS()
    yield


def _req(*, user_id=42, guild_id=99, args=None):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=user_id),
        guild_id=guild_id,
        args=dict(args or {}),
        request_id="req-1",
        confirmed=False,
    )


def _resolve(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


# --- wiring: every hub button routes through the seam --------------------------------------


def test_hub_buttons_route_through_the_catch_seam():
    """The hub spec's section buttons carry the wrapper refs while the
    wire bytes (``setup_section:{slug}`` custom_ids, labels, emoji,
    styles) stay exactly the #444-era hub."""
    from sb.domain.setup.panels import sections_hub_spec
    from sb.domain.setup.sections import SECTIONS

    spec = sections_hub_spec()
    by_id = {a.action_id: a for a in spec.actions}
    for s in SECTIONS:
        action = by_id[f"section_{s.slug}"]
        assert action.handler.name == f"setup.hub_open_section_{s.slug}"
        assert action.custom_id_override == f"setup_section:{s.slug}"
        assert action.label == s.label


def test_wrapper_registered_for_every_section():
    from sb.domain.setup.sections import SECTIONS

    for s in SECTIONS:
        assert callable(_resolve(f"setup.hub_open_section_{s.slug}"))


def test_seam_resolves_the_sections_own_route():
    """_resolve_section_open answers the registered
    ``setup.open_section_{slug}`` handler (the recovery.py
    ``_run_section_flow`` twin)."""
    from sb.domain.setup import panels

    assert (panels._resolve_section_open("channels")
            is _resolve("setup.open_section_channels"))


# --- the success path is untouched ----------------------------------------------------------


def test_success_passes_through_untouched(monkeypatch):
    from sb.domain.setup import notices, panels
    from sb.kernel.interaction.handler_kit import Reply

    sentinel = Reply(SUCCESS, "section opened")

    async def fake_section_open(req):
        return sentinel

    pushes = []

    async def fake_push(req, *, title, description, style_token="green"):
        pushes.append(title)
        return True

    monkeypatch.setattr(panels, "_resolve_section_open",
                        lambda slug: fake_section_open)
    monkeypatch.setattr(notices, "push_setup_notice", fake_push)
    out = run(_resolve("setup.hub_open_section_channels")(_req()))
    assert out is sentinel          # byte-untouched pass-through
    assert pushes == []             # no notice on success


def test_success_none_return_passes_through(monkeypatch):
    """Panel-opening sections answer None (the open_panel lane) — the
    seam must not wrap that into a reply."""
    from sb.domain.setup import notices, panels

    async def fake_section_open(req):
        return None

    pushes = []

    async def fake_push(req, *, title, description, style_token="green"):
        pushes.append(title)
        return True

    monkeypatch.setattr(panels, "_resolve_section_open",
                        lambda slug: fake_section_open)
    monkeypatch.setattr(notices, "push_setup_notice", fake_push)
    assert run(_resolve("setup.hub_open_section_roles")(_req())) is None
    assert pushes == []


# --- the failure path: durable record + BLOCKED ack -----------------------------------------


def test_failure_posts_the_notice_and_blocks(monkeypatch):
    from sb.domain.setup import notices, panels

    async def broken_section_open(req):
        raise RuntimeError("boom")

    pushes = []

    async def fake_push(req, *, title, description, style_token="green"):
        pushes.append((title, description, style_token))
        return True

    monkeypatch.setattr(panels, "_resolve_section_open",
                        lambda slug: broken_section_open)
    monkeypatch.setattr(notices, "push_setup_notice", fake_push)
    reply = run(_resolve("setup.hub_open_section_channels")(_req()))
    # the durable record — the #444 exemplar bytes.
    assert pushes == [("⚠️ Section `channels` failed",
                       "See logs for details.", "red")]
    # the click-level ack.
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ Opening **Channels & log routing** failed — see logs. "
        "Nothing was applied or skipped. A failure record was posted "
        "to the setup workspace.")


def test_failure_ack_drops_the_record_line_when_push_fails(monkeypatch):
    """The caller-decided ephemeral fallback (the notices.py bool
    contract): an unreachable workspace never makes the ack lie."""
    from sb.domain.setup import notices, panels

    async def broken_section_open(req):
        raise RuntimeError("boom")

    async def failed_push(req, *, title, description, style_token="green"):
        return False

    monkeypatch.setattr(panels, "_resolve_section_open",
                        lambda slug: broken_section_open)
    monkeypatch.setattr(notices, "push_setup_notice", failed_push)
    reply = run(_resolve("setup.hub_open_section_channels")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ Opening **Channels & log routing** failed — see logs. "
        "Nothing was applied or skipped.")


def test_unresolvable_section_route_is_caught_too(monkeypatch):
    """A missing ``setup.open_section_{slug}`` registration (resolve
    raises) rides the same seam — the notice still records it."""
    from sb.domain.setup import notices, panels

    def broken_resolve(slug):
        raise KeyError(f"setup.open_section_{slug}")

    pushes = []

    async def fake_push(req, *, title, description, style_token="green"):
        pushes.append((title, style_token))
        return True

    monkeypatch.setattr(panels, "_resolve_section_open", broken_resolve)
    monkeypatch.setattr(notices, "push_setup_notice", fake_push)
    reply = run(_resolve("setup.hub_open_section_ticket")(_req()))
    assert pushes == [("⚠️ Section `ticket` failed", "red")]
    assert reply.outcome == BLOCKED
