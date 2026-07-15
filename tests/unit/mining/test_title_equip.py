"""Mining title-equip write slice (ORDER 022 (a)3) — the 🏆 Titles panel's
state-derived earned-title select + the audited ``mining.equip_title`` /
``mining.unequip_title`` ops.

ORACLE (menno420/superbot @ bbc524e): disbot/views/mining/titles_panel.py
(``_TitleSelect`` — the ONLY equip ingress; no command form:
cogs/mining_cog.py ``titles_cmd`` opens the panel only) +
disbot/services/title_service.py (``equip`` / ``unequip`` — validation,
the one ``equipped_title`` write, response strings VERBATIM).

DB-free: legs run against monkeypatched store reads + a recording writer
(the ``_RecordingConn`` SQL-shape pin lineage,
tests/unit/mining/test_mining_energy_store.py); the panel provider /
renderer run over the same fakes. The wire bytes are pinned by
goldens/mining/mining_title_equip_write.json +
mining_title_equip_unearned_refusal.json; the FRESH-player selectless
shape stays pinned by goldens/mining/sweep_titles.json.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import WorkflowContext

run = asyncio.run

UID, GID = 42, 1


def _ctx(params: dict | None = None) -> WorkflowContext:
    return WorkflowContext(
        actor=SimpleNamespace(user_id=UID, actor_type="user"),
        guild_id=GID, request_id="req-1", params=dict(params or {}))


def _patch_progression(monkeypatch, *, skills=None, max_depth=0, level=0,
                       equipped=None):
    """Fake the derived-progression reads (skills / max_depth / level) and
    record the equipped-title write."""
    from sb.domain.games import xp as game_xp
    from sb.domain.mining import store

    writes: list[tuple[int, int, str | None]] = []

    async def get_skills(uid, gid, conn=None):
        return dict(skills or {})

    async def get_max_depth(uid, gid, conn=None):
        return max_depth

    async def shared_level(uid, gid):
        return level, 0

    async def get_equipped_title(uid, gid, conn=None):
        return equipped

    async def set_equipped_title(uid, gid, title_id, conn=None):
        writes.append((uid, gid, title_id))

    monkeypatch.setattr(store, "get_skills", get_skills)
    monkeypatch.setattr(store, "get_max_depth", get_max_depth)
    monkeypatch.setattr(store, "get_equipped_title", get_equipped_title)
    monkeypatch.setattr(store, "set_equipped_title", set_equipped_title)
    monkeypatch.setattr(game_xp, "shared_level", shared_level)
    return writes


# --- the op specs: audited seam shape -------------------------------------------


def test_title_ops_are_registered_user_tier_single_reversible_leg():
    from sb.domain.mining import ops
    from sb.kernel.workflow.spec import IdempotencyPosture, LegKind

    for op, verb, leg in (
            (ops.EQUIP_TITLE, "mining_title_equipped",
             "mining.record_equip_title"),
            (ops.UNEQUIP_TITLE, "mining_title_unequipped",
             "mining.record_unequip_title")):
        assert op.domain == "mining"
        assert op.authority_ref == "user"          # self-service, K6 user tier
        assert op.audit_verb == verb
        assert op.idempotency is IdempotencyPosture.NATURAL_KEY
        assert op.emits == ()                      # no coins, no XP — no events
        assert len(op.legs) == 1
        assert op.legs[0].kind is LegKind.DB
        assert op.legs[0].handler.name == leg
        assert op.legs[0].reversibility == "reversible"
    assert ops.EQUIP_TITLE.op_key == "mining.equip_title"
    assert ops.UNEQUIP_TITLE.op_key == "mining.unequip_title"


# --- the equip leg: title_service.equip verbatim ---------------------------------


def test_equip_leg_unknown_title_refuses_with_oracle_copy(monkeypatch):
    from sb.domain.mining.ops import _record_equip_title

    writes = _patch_progression(monkeypatch, max_depth=1)
    with pytest.raises(ValidatorError) as err:
        run(_record_equip_title(None, _ctx({"title_id": "not_a_title"})))
    # the D-0060 two-arg form: raise-site VERBATIM copy, never the
    # missing-argument wrap (the refusal golden pins the rendered byte).
    assert err.value.user_copy == (
        "That isn't a real title — open the 🏆 Titles panel to see yours.")
    assert writes == []


def test_equip_leg_unearned_title_refuses_with_oracle_copy(monkeypatch):
    from sb.domain.mining.ops import _record_equip_title

    writes = _patch_progression(monkeypatch, max_depth=1)  # only spelunker
    with pytest.raises(ValidatorError) as err:
        run(_record_equip_title(None, _ctx({"title_id": "legend"})))
    assert err.value.user_copy == (
        "You haven't earned **the Legend** yet — Reach game level 25.")
    assert writes == []


def test_equip_leg_earned_title_writes_and_replies_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_equip_title

    writes = _patch_progression(monkeypatch, max_depth=1)
    out = run(_record_equip_title(None, _ctx({"title_id": "spelunker"})))
    assert writes == [(UID, GID, "spelunker")]
    assert out.after["message"] == "Title set to 🪨 the Spelunker."
    assert out.after["title_id"] == "spelunker"


def test_equip_leg_normalizes_the_id_like_the_oracle(monkeypatch):
    # oracle: titles.get_title(title_id.strip().lower())
    from sb.domain.mining.ops import _record_equip_title

    writes = _patch_progression(monkeypatch, max_depth=1)
    run(_record_equip_title(None, _ctx({"title_id": "  SPELUNKER "})))
    assert writes == [(UID, GID, "spelunker")]


def test_unequip_leg_clears_and_replies_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_unequip_title

    writes = _patch_progression(monkeypatch, max_depth=1)
    out = run(_record_unequip_title(None, _ctx()))
    assert writes == [(UID, GID, None)]
    assert out.after["message"] == "Title cleared — none displayed."


# --- the store writer: SQL shape -------------------------------------------------


class _RecordingConn:
    def __init__(self):
        self.queries: list[str] = []
        self.params: list[tuple] = []

    async def execute(self, query: str, *params: object):
        self.queries.append(query)
        self.params.append(params)
        return "INSERT 0 1"


def test_set_equipped_title_upserts_the_one_column():
    from sb.domain.mining.store import set_equipped_title

    conn = _RecordingConn()
    run(set_equipped_title(UID, GID, "spelunker", conn=conn))
    run(set_equipped_title(UID, GID, None, conn=conn))
    assert len(conn.queries) == 2
    for q in conn.queries:
        assert "INSERT INTO mining_player_state" in q
        assert "ON CONFLICT (user_id, guild_id)" in q
        assert "DO UPDATE SET equipped_title=$3" in q
    # user_id is TEXT (the store's str() convention); None clears.
    assert conn.params[0] == (str(UID), GID, "spelunker")
    assert conn.params[1] == (str(UID), GID, None)


# --- the select options provider: _TitleSelect rows verbatim ---------------------


def _provider():
    from sb.domain.mining.panels import _ensure_titles_select_provider
    from sb.spec.refs import resolve as resolve_ref

    return resolve_ref(_ensure_titles_select_provider())


def _panel_ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=UID),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def test_provider_returns_empty_for_a_fresh_player(monkeypatch):
    _patch_progression(monkeypatch)          # nothing earned
    options = run(_provider()(_panel_ctx()))
    assert options == ()


def test_provider_rows_are_the_shipped_select_options(monkeypatch):
    _patch_progression(monkeypatch, max_depth=1)   # earns 🪨 the Spelunker
    options = run(_provider()(_panel_ctx()))
    assert options == (
        {"label": "(none)", "value": "__none__",
         "description": "Display no title", "default": True},
        {"label": "the Spelunker", "value": "spelunker", "emoji": "🪨",
         "default": False},
    )


def test_provider_marks_the_equipped_title_default(monkeypatch):
    _patch_progression(monkeypatch, max_depth=1, equipped="spelunker")
    options = run(_provider()(_panel_ctx()))
    assert options[0]["default"] is False          # (none) no longer default
    assert options[1]["default"] is True


def test_provider_ignores_a_no_longer_earned_equipped_choice(monkeypatch):
    # the post-respec gate: a stored un-earned choice stops displaying
    # (title_service.equipped_title), so (none) stays the default.
    _patch_progression(monkeypatch, max_depth=1, equipped="legend")
    options = run(_provider()(_panel_ctx()))
    assert options[0]["default"] is True


# --- the spec + renderer: select present iff earned ------------------------------


def test_titles_spec_declares_the_shipped_select():
    from sb.domain.mining.panels import mining_titles_spec
    from sb.spec.panels import SelectorKind

    spec = mining_titles_spec()
    assert len(spec.selectors) == 1
    sel = spec.selectors[0]
    assert sel.selector_id == "ti_select"
    assert sel.kind is SelectorKind.ENTITY
    assert sel.placeholder == "Choose a title to display…"   # oracle byte
    assert sel.on_select.name == "mining.titles_pick"
    assert sel.audience_tier == "user"
    assert sel.windowed is False        # 1+9 = 10 options max — no windowing
    assert spec.layout.pages[0].rows == (("ti_select",), ("ti_hub",))


def test_renderer_drops_the_select_for_a_fresh_player(monkeypatch):
    from sb.domain.mining import panels

    panels.ensure_panel_refs()
    _patch_progression(monkeypatch)          # nothing earned
    rendered = run(panels._render_titles(panels.mining_titles_spec(),
                                         _panel_ctx()))
    kinds = [getattr(c, "kind", "") for c in rendered.components]
    assert "selector" not in kinds           # sweep_titles.json stays pinned
    assert rendered.embed.style_token == "dark_grey"
    fields = {f[0] for f in rendered.embed.fields}
    assert "Equipped" in fields and "🔒 Locked (9)" in fields


def test_renderer_keeps_the_select_and_paints_the_note(monkeypatch):
    from sb.domain.mining import panels

    panels.ensure_panel_refs()
    _patch_progression(monkeypatch, max_depth=1, equipped="spelunker")
    rendered = run(panels._render_titles(
        panels.mining_titles_spec(),
        _panel_ctx({"titles_note": "✅ Title set to 🪨 the Spelunker.",
                    "titles_tone": "success"})))
    kinds = [getattr(c, "kind", "") for c in rendered.components]
    assert "selector" in kinds
    assert rendered.embed.description == "✅ Title set to 🪨 the Spelunker."
    assert rendered.embed.style_token == "green"
    fields = dict((f[0], f[1]) for f in rendered.embed.fields)
    assert fields["Equipped"] == "🪨 the Spelunker"
    assert fields["Earned (1)"] == "🪨 the Spelunker"


# --- the pick handler: op dispatch + oracle note composition ---------------------


def _req(args: dict | None = None, *, message_id: int = 555):
    return SimpleNamespace(
        args=dict(args or {}), guild_id=GID, channel_id=9,
        actor=SimpleNamespace(user_id=UID, actor_type="user"),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)),
        request_id="r1", confirmed=False, surface=None)


def test_pick_routes_none_to_unequip_and_titles_to_equip(monkeypatch):
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine
    from sb.spec.outcomes import SUCCESS

    ran: list[tuple[str, dict]] = []

    async def fake_run(ref, ctx):
        ran.append((ref.name, dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"record": {"message": "ok."}})

    refreshes: list[dict] = []

    async def fake_refresh(req, *, message_key, params):
        refreshes.append({"key": message_key, **params})
        return True

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    out = run(panels._titles_pick(_req({"values": ("spelunker",)})))
    assert ran[-1][0] == "mining.equip_title"
    assert ran[-1][1]["title_id"] == "spelunker"
    assert out.user_message is None            # the edit IS the ack
    assert refreshes[-1]["titles_note"] == "✅ ok."
    assert refreshes[-1]["titles_tone"] == "success"

    run(panels._titles_pick(_req({"values": ("__none__",)})))
    assert ran[-1][0] == "mining.unequip_title"


def test_pick_blocked_result_renders_the_error_note(monkeypatch):
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine
    from sb.spec.outcomes import BLOCKED

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome=BLOCKED, after=None,
            user_message=("You haven't earned **the Legend** yet — "
                          "Reach game level 25."))

    refreshes: list[dict] = []

    async def fake_refresh(req, *, message_key, params):
        refreshes.append(dict(params))
        return True

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    run(panels._titles_pick(_req({"values": ("legend",)})))
    assert refreshes[-1]["titles_note"] == (
        "❌ You haven't earned **the Legend** yet — Reach game level 25.")
    assert refreshes[-1]["titles_tone"] == "error"


def test_pick_degrades_to_a_text_reply_on_refresh_miss(monkeypatch):
    from sb.domain.mining import panels
    from sb.kernel.workflow import engine as wf_engine
    from sb.spec.outcomes import SUCCESS

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome=SUCCESS, user_message=None,
            after={"record": {"message": "Title cleared — none displayed."}})

    async def fake_refresh(req, *, message_key, params):
        return False                            # restart / eviction

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr("sb.kernel.panels.engine.refresh_session_view",
                        fake_refresh)

    out = run(panels._titles_pick(_req({"values": ("__none__",)})))
    assert out.user_message == "✅ Title cleared — none displayed."
