"""Operator-hub edits slice C (ORDER 017 item 1, Top-gaps 6): the admin
Cog Manager's interaction terminals go live — the cog select (pick
memory + the shipped 'Selected: cogs.<name>' footer swap + the
'← selected' roster marker) and the ◀ Prev / Next ▶ select windowing
(the shipped 3-page 25-option SelectWindow with edge-disable). The
Load/Unload/Reload trio stays the DELIBERATE by-design deploy-ops
terminal (docs/decisions.md — no compiled-architecture analog).

Golden safety: the bare `!coglist` open (page 0, no pick) must keep
every byte goldens/admin/sweep_coglist pins — asserted below on the
rendered surface (footer, placeholder, Prev disabled, first-25 window).
"""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

run = asyncio.run


def _ensure():
    import sb.manifest.admin as m

    m.ENSURE_REFS()


def _handler(name: str):
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    _ensure()
    return resolve_ref(HandlerRef(name))


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(default_factory=lambda: SimpleNamespace(
        user_id=7, member_tier="administrator"))


def _ctx(guild_id=42, user_id=7):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id,
        actor=SimpleNamespace(user_id=user_id,
                              member_tier="administrator"),
        channel_id=7, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


@pytest.fixture(autouse=True)
def _clean_memory(monkeypatch):
    from sb.domain.admin import cogmgr
    from sb.kernel.panels import engine as panels_engine

    cogmgr._cog_pick.clear()
    cogmgr._cog_page.clear()

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    yield
    cogmgr._cog_pick.clear()
    cogmgr._cog_page.clear()


def _render(ctx=None):
    from sb.domain.admin.cogmgr import cogmgr_spec
    from sb.spec.refs import HandlerRef, resolve

    _ensure()
    return run(resolve(HandlerRef("admin.cogmgr_render"))(
        cogmgr_spec(), ctx or _ctx()))


def _component(rendered, leaf: str):
    for c in rendered.components:
        if c.custom_id.rsplit(".", 1)[-1].rsplit(":", 1)[-1] == leaf:
            return c
    raise AssertionError(f"no component {leaf!r}")


# --- golden safety: the bare open bytes -------------------------------------------


def test_bare_open_keeps_the_pinned_bytes():
    """Page 0, no pick — the sweep_coglist world: initial footer, page-1
    placeholder, first-25 window, ◀ Prev disabled, Next ▶ enabled."""
    rendered = _render()
    assert rendered.embed.footer == "No cog selected."
    assert "← selected" not in rendered.embed.description
    select = _component(rendered, "cogmgr_select")
    assert select.placeholder == "Choose a cog… — page 1/3"
    assert len(select.options) == 25
    assert select.options[0]["value"] == "cogs.admin_cog"
    assert _component(rendered, "cogmgr_prev").disabled is True
    assert _component(rendered, "cogmgr_next").disabled is False
    # the deploy trio keeps its golden-pinned persistent ids.
    for leaf, cid in (("load", "admin:cogmgr:load"),
                      ("unload", "admin:cogmgr:unload"),
                      ("reload", "admin:cogmgr:reload")):
        assert any(c.custom_id == cid for c in rendered.components), cid


# --- the live select --------------------------------------------------------------


def test_select_stashes_the_pick_and_swaps_footer_and_marker():
    reply = run(_handler("admin.cogmgr_select")(
        Req(args={"values": ("cogs.karma_cog",)})))
    assert reply.outcome == "success"

    rendered = _render()
    # the shipped footer swap, verbatim (cog_manager.build_embed)
    assert rendered.embed.footer == "Selected: cogs.karma_cog"
    # the shipped roster marker, verbatim
    assert "✅ 🟢  `karma_cog`  ← selected" in rendered.embed.description
    assert rendered.embed.description.count("← selected") == 1


def test_select_empty_window_sentinel():
    reply = run(_handler("admin.cogmgr_select")(Req(args={"values": ()})))
    assert reply.outcome == "success"
    # the shipped empty-window sentinel reply, verbatim
    assert reply.user_message == "No cogs available."


def test_pick_is_keyed_per_guild_and_invoker():
    run(_handler("admin.cogmgr_select")(
        Req(args={"values": ("cogs.karma_cog",)})))
    other = _render(_ctx(guild_id=99, user_id=8))
    assert other.embed.footer == "No cog selected."


# --- the live window paging -------------------------------------------------------


def test_page_steps_window_the_select_with_edge_disable():
    from sb.domain.admin.cogmgr import _COGS

    nxt = _handler("admin.cogmgr_next")
    run(nxt(Req(args={})))
    rendered = _render()
    select = _component(rendered, "cogmgr_select")
    assert select.placeholder == "Choose a cog… — page 2/3"
    assert len(select.options) == 25
    assert select.options[0]["value"] == f"cogs.{_COGS[25]}"
    assert _component(rendered, "cogmgr_prev").disabled is False
    assert _component(rendered, "cogmgr_next").disabled is False

    run(nxt(Req(args={})))
    rendered = _render()
    select = _component(rendered, "cogmgr_select")
    assert select.placeholder == "Choose a cog… — page 3/3"
    assert len(select.options) == len(_COGS) - 50      # the 8-cog tail
    assert _component(rendered, "cogmgr_next").disabled is True

    # clamped at the last page (the shipped SelectWindow edge)
    run(nxt(Req(args={})))
    rendered = _render()
    assert _component(rendered, "cogmgr_select").placeholder == (
        "Choose a cog… — page 3/3")

    prev = _handler("admin.cogmgr_prev")
    run(prev(Req(args={})))
    run(prev(Req(args={})))
    run(prev(Req(args={})))                             # clamped at page 1
    rendered = _render()
    assert _component(rendered, "cogmgr_select").placeholder == (
        "Choose a cog… — page 1/3")
    assert _component(rendered, "cogmgr_prev").disabled is True


# --- the by-design deploy terminal ------------------------------------------------


def test_deploy_trio_stays_the_by_design_terminal():
    """NOT a gap: extension management has no compiled-architecture
    analog (docs/decisions.md) — the click answers final copy saying
    exactly that."""
    from sb.spec.outcomes import BLOCKED

    reply = run(_handler("admin.cogmgr_deploy_pending")(Req(args={})))
    assert reply.outcome == BLOCKED
    assert "deploy-ops in the compiled architecture" in reply.user_message
    assert "recompile at boot" in reply.user_message
