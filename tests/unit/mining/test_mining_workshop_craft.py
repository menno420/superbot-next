"""Mining 🔧 Workshop gear-craft select (backlog B3) — the shipped
``_CraftSelect`` dropdown made a live handler that crafts the picked gear recipe
through the audited ``mining.craft`` op and re-renders the panel IN PLACE.

ORACLE (menno420/superbot): disbot/views/mining/workshop_panel.py
(``_CraftSelect.callback`` -> ``mining_workflow.craft`` -> ``_rerender`` — the
in-place ✅/❌ note re-render with the SUCCESS/ERROR frame) +
disbot/services/mining_workflow.py (``craft`` — recipe/forge/material
validation + the response strings, VERBATIM; ported to sb as
sb/domain/mining/ops.py ``_record_craft``).

The select runs the SAME audited op the LIVE `!craft <item>` / `!build <item>`
command lane carries (``mining.craft`` -> ``record_craft``), already byte-pinned
by goldens/mining/mining_craft_write.json + mining_craft_no_recipe.json via that
command lane. goldens/mining/mining_workshop_craft_write.json drives the
session-select click and freezes the ported select's in-place re-render wire
bytes; the FRESH-player plain-open shape stays pinned by
goldens/mining/sweep_workshop.json.

FAITHFUL to the oracle _rerender (the ``mining.titles_pick`` select precedent):
the panel re-renders in place with the ✅/❌ note + SUCCESS/ERROR frame — NOT the
RESULT_CARD divergence the workshop's BUTTON lanes (skill_spend) accept, because
this is a SELECT and the oracle _rerender is directly reproducible.

DB-free: the pick handler runs over a faked ``engine.run`` /
``refresh_session_view`` seam (the engine.run txn is the pg-walled seam the
command-lane goldens already cover) — the tests/unit/mining/test_title_equip.py
lineage.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run

UID, GID = 42, 1


def _req(args: dict | None = None, *, message_id: int = 555):
    return SimpleNamespace(
        args=dict(args or {}), guild_id=GID, channel_id=9,
        actor=SimpleNamespace(user_id=UID, actor_type="user"),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)),
        request_id="r1", confirmed=False, surface=None)


def _panel_ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=UID),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


# --- the spec: the select is wired to the LIVE pick handler ----------------------


def test_workshop_spec_declares_the_live_craft_select():
    from sb.domain.mining.panels import mining_workshop_spec
    from sb.spec.panels import SelectorKind

    spec = mining_workshop_spec()
    assert len(spec.selectors) == 1
    sel = spec.selectors[0]
    assert sel.selector_id == "ws_craft"
    assert sel.kind is SelectorKind.ENTITY
    assert sel.placeholder == "Craft gear from resources…"     # oracle byte
    assert sel.on_select.name == "mining.workshop_craft_pick"  # LIVE, not pending
    assert sel.audience_tier == "user"


def test_workshop_craft_pending_terminal_is_retired():
    from sb.domain.mining import panels
    from sb.spec.refs import HandlerRef, is_registered

    panels.ensure_panel_refs()
    assert is_registered(HandlerRef("mining.workshop_craft_pick"))
    assert not is_registered(HandlerRef("mining.workshop_craft_pending"))


# --- the pick handler: op dispatch + oracle note composition ---------------------


def test_pick_crafts_the_selected_recipe_and_paints_the_success_note(monkeypatch):
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine

    ran: list[tuple[str, dict]] = []

    async def fake_run(ref, ctx):
        ran.append((ref.name, dict(ctx.params)))
        return SimpleNamespace(
            outcome=SUCCESS, user_message=None,
            after={"record": {"item": "bronze boots",
                              "message": "Crafted **bronze boots**!"}})

    refreshes: list[dict] = []

    async def fake_refresh(req, *, message_key, params):
        refreshes.append({"key": message_key, **params})
        return True

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    out = run(panels._workshop_craft_pick(_req({"values": ("bronze boots",)})))
    # the picked recipe rides `item` into the SAME op the command lane runs.
    assert ran[-1][0] == "mining.craft"
    assert ran[-1][1]["item"] == "bronze boots"
    assert out.user_message is None                 # the edit IS the ack
    assert refreshes[-1]["workshop_note"] == "✅ Crafted **bronze boots**!"
    assert refreshes[-1]["workshop_tone"] == "success"


def test_pick_blocked_result_renders_the_verbatim_error_note(monkeypatch):
    # the op's short-on-materials refusal (D-0060 verbatim copy) surfaces as the
    # ❌ note + ERROR frame — the whole txn rolls back, a refused click writes
    # nothing (mining_workflow.craft _check_materials verbatim).
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome=BLOCKED, after=None,
            user_message=("You don't have enough **bronze** to craft "
                          "**bronze boots** (needs 2× bronze)."))

    refreshes: list[dict] = []

    async def fake_refresh(req, *, message_key, params):
        refreshes.append(dict(params))
        return True

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    out = run(panels._workshop_craft_pick(_req({"values": ("bronze boots",)})))
    assert out.user_message is None
    assert refreshes[-1]["workshop_note"] == (
        "❌ You don't have enough **bronze** to craft **bronze boots** "
        "(needs 2× bronze).")
    assert refreshes[-1]["workshop_tone"] == "error"


def test_pick_degrades_to_a_text_reply_on_refresh_miss(monkeypatch):
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome=SUCCESS, user_message=None,
            after={"record": {"message": "Crafted **bronze boots**!"}})

    async def fake_refresh(req, *, message_key, params):
        return False                                # restart / eviction

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    out = run(panels._workshop_craft_pick(_req({"values": ("bronze boots",)})))
    assert out.outcome is SUCCESS
    assert out.user_message == "✅ Crafted **bronze boots**!"


def test_pick_passes_a_blank_item_when_no_value(monkeypatch):
    # defensive: no select value -> a blank item, which the op refuses as its
    # verbatim `Name an item.` face; the pick handler stays a thin pass-through.
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine

    ran: list[dict] = []

    async def fake_run(ref, ctx):
        ran.append(dict(ctx.params))
        return SimpleNamespace(outcome=BLOCKED, after=None,
                               user_message="Name an item.")

    async def fake_refresh(req, *, message_key, params):
        return True

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    run(panels._workshop_craft_pick(_req({})))
    assert ran[-1]["item"] == ""


# --- the renderer: paints the note iff present, else byte-neutral ----------------


def _patch_workshop_reads(monkeypatch):
    """Fake the workshop renderer's live-state reads to the fresh-player shape
    (the sweep_workshop.json bytes: nothing owned/equipped/broken, 0 balance)."""
    from sb.domain.economy import store as econ_store
    from sb.domain.mining import store

    async def empty(uid, gid, conn=None):
        return {}

    async def none(uid, gid, conn=None):
        return None

    async def zero(uid, gid, conn=None):
        return 0

    monkeypatch.setattr(store, "get_mining_inventory", empty)
    monkeypatch.setattr(store, "get_equipment", empty)
    monkeypatch.setattr(store, "get_gear_wear", empty)
    monkeypatch.setattr(store, "get_last_broken", none)
    monkeypatch.setattr(econ_store, "get_coins", zero)


def test_renderer_plain_open_stays_dark_grey_and_note_free(monkeypatch):
    from sb.domain.mining import panels

    panels.ensure_panel_refs()
    _patch_workshop_reads(monkeypatch)
    rendered = run(panels._render_workshop(panels.mining_workshop_spec(),
                                           _panel_ctx()))
    assert rendered.embed.style_token == "dark_grey"   # sweep_workshop pinned
    assert not rendered.embed.description               # no note on plain open


def test_renderer_paints_the_success_note_and_green_frame(monkeypatch):
    from sb.domain.mining import panels

    panels.ensure_panel_refs()
    _patch_workshop_reads(monkeypatch)
    rendered = run(panels._render_workshop(
        panels.mining_workshop_spec(),
        _panel_ctx({"workshop_note": "✅ Crafted **bronze boots**!",
                    "workshop_tone": "success"})))
    assert rendered.embed.description == "✅ Crafted **bronze boots**!"
    assert rendered.embed.style_token == "green"


def test_renderer_paints_the_error_note_and_red_frame(monkeypatch):
    from sb.domain.mining import panels

    panels.ensure_panel_refs()
    _patch_workshop_reads(monkeypatch)
    rendered = run(panels._render_workshop(
        panels.mining_workshop_spec(),
        _panel_ctx({"workshop_note": "❌ You don't have enough **bronze** …",
                    "workshop_tone": "error"})))
    assert rendered.embed.description == "❌ You don't have enough **bronze** …"
    assert rendered.embed.style_token == "red"
