"""The Help overlay store + editor port (server_management projections
slice C — the D-0026 named-successor lane): the read model (cache /
fault-degrade / orphan report), the audited K7 lanes (bounds + final
copy + store-only-deviations), the editor panel family (ORACLE
disbot/views/help/editor.py, copy verbatim), the live-Help overlay
wiring (empty overlay = byte-identical defaults), and the hub flip.
"""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.help import editor as ed
    from sb.domain.help import overlay as ov

    ov.reset_overlay_cache_for_tests()
    ed._entity_pick.clear()
    ed._picker_page.clear()
    yield
    ov.reset_overlay_cache_for_tests()
    ed._entity_pick.clear()
    ed._picker_page.clear()


def _overlay(rows=(), gid=1):
    from sb.domain.help.overlay import GuildHelpOverlay

    return GuildHelpOverlay(guild_id=gid, rows=tuple(rows))


def _row(kind, key, hidden=None, name=None, desc=None):
    from sb.domain.help.overlay import HelpOverlayRow

    return HelpOverlayRow(entity_kind=kind, entity_key=key,
                          display_hidden=hidden, display_name=name,
                          description=desc)


def _patch_overlay(monkeypatch, overlay):
    from sb.domain.help import overlay as ov

    async def fake_get(guild_id):
        return overlay

    monkeypatch.setattr(ov, "get_guild_help_overlay", fake_get)


def _wctx(params, gid=1, uid=42):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params)


def _ctx(gid=1, uid=42):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=gid, actor=SimpleNamespace(user_id=uid),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={},
        surface="component")


@dataclasses.dataclass
class _Req:
    args: dict
    guild_id: int | None = 1
    channel_id: int | None = 2
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(
        default_factory=lambda: SimpleNamespace(user_id=42))


# --- the read model ------------------------------------------------------------------


def test_overlay_read_degrades_to_empty_on_fault(monkeypatch):
    """Help must never crash on the overlay path (shipped rule)."""
    from sb.domain.help import overlay as ov
    from sb.kernel.db import pool

    async def boom(*a, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(pool, "fetchall", boom)
    overlay = run(ov.get_guild_help_overlay(1))
    assert overlay.is_empty and overlay.guild_id == 1
    # DMs read the shared EMPTY overlay.
    assert run(ov.get_guild_help_overlay(None)) is ov.EMPTY_OVERLAY


def test_overlay_read_caches_and_invalidates(monkeypatch):
    from sb.domain.help import overlay as ov
    from sb.kernel.db import pool

    calls = []

    async def fake_fetchall(sql, params, conn=None):
        calls.append(params)
        return [{"entity_kind": "subsystem", "entity_key": "economy",
                 "display_hidden": True, "display_name": None,
                 "description": None}]

    monkeypatch.setattr(pool, "fetchall", fake_fetchall)
    first = run(ov.get_guild_help_overlay(7))
    second = run(ov.get_guild_help_overlay(7))
    assert first is second and len(calls) == 1
    assert first.hidden("subsystem", "economy")
    ov.invalidate_help_overlay_cache(7)
    run(ov.get_guild_help_overlay(7))
    assert len(calls) == 2


def test_known_entities_and_defaults():
    from sb.domain.help.overlay import entity_defaults, known_entities

    hubs = known_entities("hub")
    assert "games" in hubs and "admin" in hubs and "other" in hubs
    subs = known_entities("subsystem")
    assert "economy" in subs
    assert "help" not in subs           # Help never surfaces under a hub
    assert entity_defaults("hub", "games") == (
        "Games", "Game flows and tournaments.")
    name, _ = entity_defaults("subsystem", "economy")
    assert name == "Economy"


# --- the audited lanes -----------------------------------------------------------------


def _patch_leg_db(monkeypatch, current_row=None):
    """Capture the leg's SQL; serve ``current_row`` as the existing row."""
    from sb.domain.help import overlay_ops as ops

    executed = []

    async def fake_fetchone(sql, params, conn=None):
        if "COUNT(*)" in sql:
            return {"n": 3}
        return current_row

    async def fake_execute(sql, params, conn=None):
        executed.append((sql, params))

    monkeypatch.setattr(ops, "fetchone", fake_fetchone)
    monkeypatch.setattr(ops, "execute", fake_execute)
    return executed


def test_set_overlay_rejects_unknown_key(monkeypatch):
    from sb.domain.help.overlay_ops import _record_set_overlay_fields
    from sb.kernel.interaction.errors import ValidatorError

    _patch_leg_db(monkeypatch)
    with pytest.raises(ValidatorError) as err:
        run(_record_set_overlay_fields(None, _wctx({
            "entity_kind": "subsystem", "entity_key": "not_a_thing",
            "fields": {"display_hidden": True}})))
    assert "not a current Help feature" in str(err.value)


def test_set_overlay_rejects_empty_and_overlong_text(monkeypatch):
    from sb.domain.help.overlay_ops import _record_set_overlay_fields
    from sb.kernel.interaction.errors import ValidatorError

    _patch_leg_db(monkeypatch)
    with pytest.raises(ValidatorError) as err:
        run(_record_set_overlay_fields(None, _wctx({
            "entity_kind": "subsystem", "entity_key": "economy",
            "fields": {"display_name": "   "}})))
    assert "The name can't be empty — use ♻️ Reset name to return to " \
           "the default." in str(err.value)
    with pytest.raises(ValidatorError) as err:
        run(_record_set_overlay_fields(None, _wctx({
            "entity_kind": "subsystem", "entity_key": "economy",
            "fields": {"description": "x" * 101}})))
    assert "limited to 100 characters" in str(err.value)


def test_set_overlay_upserts_deviations(monkeypatch):
    from sb.domain.help.overlay_ops import _record_set_overlay_fields

    executed = _patch_leg_db(monkeypatch)
    outcome = run(_record_set_overlay_fields(None, _wctx({
        "entity_kind": "subsystem", "entity_key": "economy",
        "fields": {"display_name": "Coins"}})))
    (sql, params) = executed[-1]
    assert "INSERT INTO help_overlay" in sql and "ON CONFLICT" in sql
    assert params[:3] == (1, "subsystem", "economy")
    assert params[4] == "Coins"
    assert outcome.after == {"display_hidden": None,
                             "display_name": "Coins", "description": None}


def test_set_overlay_partial_edit_preserves_other_fields(monkeypatch):
    """UNSET semantics: a field absent from params stays; present-as-None
    resets (the shipped partial-edit contract)."""
    from sb.domain.help.overlay_ops import _record_set_overlay_fields

    executed = _patch_leg_db(monkeypatch, current_row={
        "display_hidden": True, "display_name": "Coins",
        "description": None})
    run(_record_set_overlay_fields(None, _wctx({
        "entity_kind": "subsystem", "entity_key": "economy",
        "fields": {"description": "All about coins"}})))
    (sql, params) = executed[-1]
    assert params[3] is True and params[4] == "Coins"
    assert params[5] == "All about coins"


def test_set_overlay_all_none_deletes_the_row(monkeypatch):
    """Store only deviations: an all-inherit row is deleted (shipped)."""
    from sb.domain.help.overlay_ops import _record_set_overlay_fields

    executed = _patch_leg_db(monkeypatch, current_row={
        "display_hidden": True, "display_name": None, "description": None})
    outcome = run(_record_set_overlay_fields(None, _wctx({
        "entity_kind": "subsystem", "entity_key": "economy",
        "fields": {"display_hidden": None}})))
    (sql, _params) = executed[-1]
    assert sql.startswith("DELETE FROM help_overlay")
    assert outcome.after == {}


def test_reset_overlay_deletes_guild_rows(monkeypatch):
    from sb.domain.help.overlay_ops import _record_reset_overlay

    executed = _patch_leg_db(monkeypatch)
    outcome = run(_record_reset_overlay(None, _wctx({})))
    (sql, params) = executed[-1]
    assert sql.startswith("DELETE FROM help_overlay") and params == (1,)
    assert outcome.before == {"rows": 3} and outcome.after == {"rows": 0}


def test_ops_registered_with_admin_floor():
    from sb.domain.help.overlay_ops import RESET_OVERLAY, SET_OVERLAY_FIELDS
    from sb.spec.refs import WorkflowRef, is_registered

    for op in (SET_OVERLAY_FIELDS, RESET_OVERLAY):
        assert op.authority_ref == "administrator"
        assert op.domain == "help"
        assert is_registered(WorkflowRef(op.op_key)), op.op_key
    assert SET_OVERLAY_FIELDS.audit_verb == "help_overlay_update"
    assert RESET_OVERLAY.audit_verb == "help_overlay_reset"


# --- the editor panels ---------------------------------------------------------------------


def test_editor_panels_compile_and_carry_the_shipped_copy():
    from sb.domain.help import editor as ed
    from sb.kernel.panels.compile import check_panel

    specs = {s.panel_id: s for s in ed.editor_panel_specs()}
    for spec in specs.values():
        check_panel(spec)
    home = specs["help.editor_home"]
    assert home.title == "✏️ Help appearance editor"
    assert "hidden from Help but still executable" in home.body[0].text
    assert "never to permissions or execution" in home.body[0].text
    by_id = {a.action_id: a for a in home.actions}
    assert by_id["eh_hubs"].label == "🏛 Hubs"
    assert by_id["eh_subsystems"].label == "🧩 Subsystems"
    assert by_id["eh_home_msg"].label == "🏠 Home message"
    assert by_id["eh_reset_all"].label == "🗑 Reset all…"

    pick_hub = specs["help.editor_pick_hub"]
    assert pick_hub.title == "✏️ Help editor — hubs"
    assert specs["help.editor_pick_sub"].title == "✏️ Help editor — subsystems"
    (sel,) = pick_hub.selectors
    assert sel.placeholder == "Pick a hub to edit…"

    entity = specs["help.editor_entity"]
    by_id = {a.action_id: a for a in entity.actions}
    assert by_id["ee_hide"].label == "🙈 Hide"
    assert by_id["ee_rename"].modal.modal_id == "help.editor_rename_form"
    assert by_id["ee_rename"].modal.title == "Rename in Help"
    assert by_id["ee_redescribe"].modal.modal_id == (
        "help.editor_redescribe_form")
    assert entity.layout.pages[0].rows == (
        ("ee_hide", "ee_rename", "ee_redescribe"),
        ("ee_reset_name", "ee_reset_desc", "ee_reset_entity"))

    confirm = specs["help.editor_reset_confirm"]
    assert confirm.title == "Reset ALL Help customizations?"
    assert "cannot be undone (the audit log keeps the history)" in (
        confirm.body[0].text)


def test_editor_home_fields_counts_and_orphans(monkeypatch):
    from sb.domain.help import editor as ed

    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "economy", hidden=True),
        _row("subsystem", "mining", name="Digging"),
        _row("hub", "games", desc="Play!"),
        _row("subsystem", "retired_thing", name="Ghost"),
    )))
    fields = run(ed._home_fields(_ctx()))
    assert fields[0] == (
        "Current overrides",
        "🙈 hidden: **1** · ✏️ renamed: **2** · 📝 re-described: **1**")
    name, value = fields[1]
    assert name == "⚠️ Orphaned overrides (1)"
    assert "`retired_thing`" in value and "**Reset all** clears them" in value


def test_editor_home_fields_empty_state(monkeypatch):
    from sb.domain.help import editor as ed

    _patch_overlay(monkeypatch, _overlay())
    fields = run(ed._home_fields(_ctx()))
    assert fields == (("Current overrides",
                       "*(none — Help renders its defaults)*"),)


def test_entity_fields_show_custom_default_and_key(monkeypatch):
    from sb.domain.help import editor as ed

    ed._entity_pick[(1, 42)] = ("subsystem", "economy")
    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "economy", hidden=True, name="Coins"),)))
    fields = dict(run(ed._entity_fields(_ctx())))
    assert fields["Name"] == "custom: **Coins**\ndefault: Economy"
    assert fields["Description"] == (
        "default: ***(none)*** *(no override)*")
    assert fields["Visibility"] == (
        "🙈 **Hidden** — hidden from Help but still executable")


def test_picker_options_window_and_annotate(monkeypatch):
    from sb.domain.help import editor as ed

    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "economy", hidden=True, name="Coins"),)))
    options = run(ed._picker_options_provider("subsystem")(_ctx()))
    assert len(options) <= 25
    economy = next(o for o in options if o["value"] == "economy")
    assert economy["label"] == "🙈 Coins"
    assert economy["description"] == "default: Economy · economy"
    # page 2 shows the tail of the 40+ inventory.
    ed._picker_page[(1, 42, "subsystem")] = 1
    page2 = run(ed._picker_options_provider("subsystem")(_ctx()))
    assert page2 and page2 != options


def test_entity_render_override_keys_title_footer_and_hide_label(
        monkeypatch):
    from sb.domain.help import editor as ed

    ed._entity_pick[(1, 42)] = ("subsystem", "economy")
    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "economy", hidden=True, name="Coins"),)))
    rendered = run(ed._render_editor_entity(ed.editor_entity_spec(), _ctx()))
    assert rendered.embed.title == "✏️ Coins"
    assert rendered.embed.description == (
        "Editing the **subsystem** `economy` — every field shows the "
        "custom value and the default it overrides.")
    assert rendered.embed.footer.endswith("· stable key: economy")
    hide = next(c for c in rendered.components
                if c.custom_id.endswith("ee_hide"))
    assert hide.label == "👁 Unhide" and hide.style == "success"


# --- the handlers -------------------------------------------------------------------------


def _patch_engine(monkeypatch, outcome="success"):
    from sb.kernel.workflow import engine

    runs = []

    async def fake_run(op, ctx):
        runs.append((getattr(op, "op_key", op), dict(ctx.params)))
        return SimpleNamespace(outcome=outcome, user_message=(
            None if outcome == "success" else "nope"))

    monkeypatch.setattr(engine, "run", fake_run)
    return runs


def _patch_open(monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req, **kw):
        opened.append(ref.name)
        return ""

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    return opened


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def test_pick_stashes_and_opens_entity(monkeypatch):
    from sb.domain.help import editor as ed

    opened = _patch_open(monkeypatch)
    reply = run(_handler("help.editor_pick_subsystem")(
        _Req(args={"values": ["economy"]})))
    assert reply.user_message is None
    assert ed.entity_pick_for(1, 42) == ("subsystem", "economy")
    assert opened == ["help.editor_entity"]
    # a stale/unknown key lands on the polite terminal.
    reply = run(_handler("help.editor_pick_subsystem")(
        _Req(args={"values": ["-"]})))
    assert reply.user_message == "That entry is no longer available."


def test_toggle_hide_runs_the_audited_op(monkeypatch):
    from sb.domain.help import editor as ed

    ed._entity_pick[(1, 42)] = ("subsystem", "economy")
    _patch_overlay(monkeypatch, _overlay())
    runs = _patch_engine(monkeypatch)
    opened = _patch_open(monkeypatch)
    reply = run(_handler("help.editor_toggle_hide")(_Req(args={})))
    assert reply.user_message is None
    (op_key, params) = runs[0]
    assert op_key == "help.set_overlay_fields"
    assert params == {"entity_kind": "subsystem", "entity_key": "economy",
                      "fields": {"display_hidden": True}}
    assert opened == ["help.editor_entity"]


def test_rename_submit_and_reset_entity(monkeypatch):
    from sb.domain.help import editor as ed

    ed._entity_pick[(1, 42)] = ("hub", "games")
    runs = _patch_engine(monkeypatch)
    _patch_open(monkeypatch)
    run(_handler("help.editor_rename")(_Req(args={"name": "Fun stuff"})))
    assert runs[-1][1]["fields"] == {"display_name": "Fun stuff"}
    run(_handler("help.editor_reset_entity")(_Req(args={})))
    assert runs[-1][1]["fields"] == {"display_hidden": None,
                                     "display_name": None,
                                     "description": None}


def test_edit_surfaces_the_ops_final_copy(monkeypatch):
    from sb.domain.help import editor as ed

    ed._entity_pick[(1, 42)] = ("subsystem", "economy")
    _patch_engine(monkeypatch, outcome="user_error")
    reply = run(_handler("help.editor_reset_name")(_Req(args={})))
    assert reply.outcome == "user_error" and reply.user_message == "nope"


def test_reset_all_runs_the_reset_op_and_returns_home(monkeypatch):
    runs = _patch_engine(monkeypatch)
    opened = _patch_open(monkeypatch)
    reply = run(_handler("help.editor_reset_all")(_Req(args={})))
    assert reply.user_message is None
    assert runs[0][0] == "help.reset_overlay"
    assert opened == ["help.editor_home"]


def test_evicted_pick_routes_back_politely(monkeypatch):
    reply = run(_handler("help.editor_toggle_hide")(_Req(args={})))
    assert reply.user_message == (
        "Pick a hub or subsystem from the editor first.")


# --- the live-Help overlay wiring -----------------------------------------------------------


def test_empty_overlay_renders_default_home_bytes(monkeypatch):
    from sb.domain.help import categories as cats
    from sb.domain.help import service

    _patch_overlay(monkeypatch, _overlay())
    service.build_help_panels()
    from sb.spec.refs import ProviderRef, resolve

    fields = run(resolve(ProviderRef("sb.panels.help_home_categories"))(
        _ctx()))
    expected = tuple(
        (f"{cat.emoji} {cat.display_name}",
         f"{cat.purpose}\n→ `{cat.hub_command}`")
        for cat in cats.CATEGORIES if not cat.staff_only)
    assert fields == expected


def test_overlay_hides_and_renames_on_the_home_index(monkeypatch):
    from sb.domain.help import service

    service.build_help_panels()
    _patch_overlay(monkeypatch, _overlay((
        _row("hub", "games", name="Fun stuff", desc="Play!"),
        _row("hub", "economy", hidden=True),
    )))
    from sb.spec.refs import ProviderRef, resolve

    fields = run(resolve(ProviderRef("sb.panels.help_home_categories"))(
        _ctx()))
    names = [n for n, _ in fields]
    assert "🎮 Fun stuff" in names
    assert not any("💰" in n for n in names)      # economy hub hidden
    games_value = dict(fields)["🎮 Fun stuff"]
    assert games_value.startswith("Play!\n")
    options = run(resolve(ProviderRef("sb.panels.help_home_options"))(
        _ctx()))
    games = next(o for o in options if o["value"] == "games")
    assert games["label"] == "Fun stuff" and games["description"] == "Play!"
    assert not any(o["value"] == "economy" for o in options)


def test_overlay_hides_and_renames_in_category_panels(monkeypatch):
    from sb.domain.help import service

    service.build_help_panels()
    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "blackjack", hidden=True),
        _row("subsystem", "mining", name="Digging"),
    )))
    from sb.spec.refs import ProviderRef, resolve

    fields = run(resolve(ProviderRef("sb.panels.help_cat_games"))(_ctx()))
    names = [n for n, _ in fields]
    assert "⛏️ Digging" in names
    assert not any("🃏" in n for n in names)       # blackjack hidden
    options = run(resolve(ProviderRef("sb.panels.help_cat_opts_games"))(
        _ctx()))
    assert "⛏️ Digging" in options
    assert not any("🃏" in o for o in options)


def test_open_subsystem_resolves_renamed_options(monkeypatch):
    import sb.kernel.panels.engine as engine
    from sb.domain.help import service

    service.build_help_panels()
    _patch_overlay(monkeypatch, _overlay((
        _row("subsystem", "mining", name="Digging"),)))
    opened = []

    async def fake_open(ref, req, **kw):
        opened.append(ref.name)

    monkeypatch.setattr(engine, "open_panel", fake_open)
    from sb.spec.refs import HandlerRef, resolve

    handler = resolve(HandlerRef("help.open_subsystem"))
    reply = run(handler(_Req(args={"values": ("⛏️ Digging",)})))
    assert reply is None
    assert opened == ["help.sub_mining"]


# --- the hub flip + manifest ------------------------------------------------------------------


def test_hub_help_editor_button_forwards_to_the_editor():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in server_management_hub_spec().actions}
    action = by_id["help_editor"]
    assert action.handler == PanelRef("help.editor_home")
    # the hub-open goldens stay byte-identical.
    assert action.label == "✏️ Help editor"
    assert action.style is ActionStyle.SECONDARY
    assert action.custom_id_override == "server_management:help_editor"


def test_help_manifest_declares_editor_panels_and_store():
    from sb.manifest.help import MANIFEST
    from sb.spec.refs import EngineRef

    ids = {p.panel_id for p in MANIFEST.panels}
    assert {"help.editor_home", "help.editor_pick_hub",
            "help.editor_pick_sub", "help.editor_entity",
            "help.editor_reset_confirm"} <= ids
    (store,) = MANIFEST.stores
    assert store.table == "help_overlay"
    assert store.sole_writer == EngineRef("help.overlay_store")


def test_pending_terminal_retired_and_teardown_registered():
    from sb.domain.platform.guild_teardown import registered_teardowns
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    import sb.domain.help.overlay_ops as ops
    import sb.domain.server_management.handlers  # noqa: F401

    assert not is_registered(
        HandlerRef("server_management.help_editor_pending"))
    # the Q-0059 home-message lane is LIVE now (its own slice) — the pending
    # terminal is retired and the builder panel + open handler are wired.
    import sb.domain.help.editor as _ed  # noqa: F401
    assert not is_registered(HandlerRef("help.editor_home_message_pending"))
    assert is_registered(PanelRef("help.editor_home_message"))
    assert is_registered(HandlerRef("help.editor_open_home_message"))
    # re-arm before asserting: a sibling test's reset_teardowns_for_tests
    # may have cleared the import-time registration (register_teardown is
    # idempotent by name).
    ops._register_teardown()
    assert "help_overlay" in registered_teardowns()
