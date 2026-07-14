"""Unit + contract tests for the windowed-select engine (K8/S9b — the
windowed-select grammar successor, ORDER 019 item 7): the pure window
algebra, the state codec (custom_id ⇄ SelectWindowState), the shipped
control bytes (◀ Prev / Next ▶ faces, the placeholder page suffix), the
render-layer integration (a declared ``windowed=True`` selector pages its
provider options instead of front-truncating; undeclared selectors keep the
pre-successor truncation byte-verbatim), and the dispatch contract — a
selwin click rides the SAME ``dispatch_component`` → §3.4 router →
panel-engine seam every other nav slot uses."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.kernel.interaction.adapters.component import dispatch_component
from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels import selectwindow as sw
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.registry import NAV_ROW, register_panel
from sb.kernel.panels.render import RenderedPanel, render_panel
from sb.kernel.panels.selectwindow import (
    SELWIN_ID_PREFIX,
    SelectWindowState,
    apply_window_delta,
    decode_window,
    encode_window,
    window_controls,
    window_options,
    windowed_placeholder,
)
from sb.spec.panels import (
    Audience,
    LayoutSpec,
    PageSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
)
from sb.spec.refs import ProviderRef, clear_ref_table, provider

from tests.unit.panels.conftest import make_actor

run = asyncio.run

PANEL_ID = "setup.pick_many"
#: 30 options — spans two 25-option windows (25 + 5).
OPTIONS = tuple(f"cog_{i:02d}" for i in range(30))


@pytest.fixture(autouse=True)
def _clean_refs():
    clear_ref_table()
    yield
    clear_ref_table()


def _install_provider(options=OPTIONS):
    @provider("selwin.options")
    async def options_provider(ctx):
        return options


def _spec(*, windowed=True, page_size=25):
    return PanelSpec(
        panel_id=PANEL_ID, subsystem="setup", title="Pick",
        audience=Audience.INVOKER,
        selectors=(
            SelectorSpec(
                selector_id="pick", kind=SelectorKind.ENUM,
                options_source=ProviderRef("selwin.options"),
                placeholder="Pick one…",
                page_size=page_size, windowed=windowed),
        ),
        layout=LayoutSpec(pages=(PageSpec(rows=(("pick",),)),)))


def _ctx():
    return PanelContext(
        bot=None, guild_id=42, actor=make_actor(), channel_id=7,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
        locale=LocaleContext())


# --- pure window algebra ---------------------------------------------------------

def test_window_options_paging_math():
    page, count, idx = window_options(OPTIONS, 25, 0)
    assert count == 2 and idx == 0 and len(page) == 25
    assert page[0] == "cog_00" and page[-1] == "cog_24"
    page, count, idx = window_options(OPTIONS, 25, 1)
    assert count == 2 and idx == 1 and len(page) == 5
    assert page == list(OPTIONS[25:])


def test_window_options_clamps_out_of_range():
    _, _, idx = window_options(OPTIONS, 25, 99)
    assert idx == 1
    _, _, idx = window_options(OPTIONS, 25, -3)
    assert idx == 0


def test_windowed_placeholder_carries_the_shipped_page_suffix():
    # the shipped _WindowSelect byte shape (views/paginated_select.py):
    # "{placeholder} — page {p+1}/{n}".
    assert windowed_placeholder("Pick one…", 0, 2) == "Pick one… — page 1/2"
    assert windowed_placeholder("Pick one…", 1, 2) == "Pick one… — page 2/2"


def test_windowed_placeholder_single_window_is_verbatim():
    assert windowed_placeholder("Pick one…", 0, 1) == "Pick one…"


def test_windowed_placeholder_clamps_to_discord_150():
    long = "x" * 160
    assert len(windowed_placeholder(long, 0, 2)) == 150


# --- state codec -----------------------------------------------------------------

def test_encode_grammar_conformance():
    state = SelectWindowState(PANEL_ID, "pick", window=1)
    cid = encode_window("next", state)
    assert cid == "nav:selwin:next:setup.pick_many:pick:1"
    assert cid.startswith(SELWIN_ID_PREFIX)


def test_decode_round_trip():
    spec = _spec()
    state = SelectWindowState(PANEL_ID, "pick", window=1)
    control, selector, decoded = decode_window(encode_window("prev", state), spec)
    assert control == "prev"
    assert selector.selector_id == "pick"
    assert decoded == state


def test_decode_rejects_malformed():
    spec = _spec()
    assert decode_window("nav:selwin:next:p:pick", spec) is None          # 3 parts
    assert decode_window("nav:selwin:jump:p:pick:0", spec) is None        # bad control
    assert decode_window("nav:selwin:next:p:pick:x", spec) is None        # non-int
    assert decode_window("totally_unrelated", spec) is None


def test_decode_rejects_unknown_selector():
    assert decode_window("nav:selwin:next:setup.pick_many:nope:0", _spec()) is None


def test_decode_rejects_selector_not_declared_windowed():
    # a stale selwin id against a spec whose selector dropped windowed=True
    # decodes to None (→ the polite-expiry terminal), never a mis-render.
    spec = _spec(windowed=False)
    assert decode_window("nav:selwin:next:setup.pick_many:pick:0", spec) is None


def test_panel_id_of():
    assert sw.window_panel_id("nav:selwin:next:setup.pick_many:pick:1") == \
        "setup.pick_many"
    assert sw.window_panel_id("nope") is None


def test_apply_delta_steps_and_clamps():
    state = SelectWindowState("p", "pick", window=1)
    assert apply_window_delta("next", state).window == 2
    assert apply_window_delta("prev", state).window == 0
    assert apply_window_delta("prev", SelectWindowState("p", "pick", 0)).window == 0


# --- control bytes ---------------------------------------------------------------

def test_controls_carry_the_shipped_faces_and_state():
    state = SelectWindowState(PANEL_ID, "pick", window=0)
    prev_btn, next_btn = window_controls(state, 2)
    # the shipped _PageButton faces (views/paginated_select.py), verbatim.
    assert prev_btn.label == "◀ Prev" and next_btn.label == "Next ▶"
    assert prev_btn.kind == "button" and next_btn.kind == "button"
    assert prev_btn.row == NAV_ROW and next_btn.row == NAV_ROW
    assert prev_btn.custom_id == "nav:selwin:prev:setup.pick_many:pick:0"
    assert next_btn.custom_id == "nav:selwin:next:setup.pick_many:pick:0"


def test_controls_disable_at_the_bounds():
    prev_btn, next_btn = window_controls(
        SelectWindowState(PANEL_ID, "pick", 0), 2)
    assert prev_btn.disabled is True and next_btn.disabled is False
    prev_btn, next_btn = window_controls(
        SelectWindowState(PANEL_ID, "pick", 1), 2)
    assert prev_btn.disabled is False and next_btn.disabled is True


def test_controls_absent_on_a_single_window():
    # the shipped page_count > 1 arming: a short list renders zero nav bytes.
    assert window_controls(SelectWindowState(PANEL_ID, "pick", 0), 1) == ()


# --- render-layer integration -----------------------------------------------------

def _select_of(rendered):
    return next(c for c in rendered.components if c.kind == "selector")


def _nav_of(rendered):
    return [c for c in rendered.components
            if c.custom_id.startswith(SELWIN_ID_PREFIX)]


def test_render_windows_the_first_page_and_arms_nav():
    _install_provider()
    rendered = run(render_panel(_spec(), _ctx()))
    select = _select_of(rendered)
    assert len(select.options) == 25
    assert select.options[0] == "cog_00" and select.options[-1] == "cog_24"
    assert select.placeholder == "Pick one… — page 1/2"
    nav = _nav_of(rendered)
    assert [c.label for c in nav] == ["◀ Prev", "Next ▶"]
    assert [c.disabled for c in nav] == [True, False]


def test_render_second_window_shows_the_tail():
    # the whole point: option 26+ is REACHABLE (the #1040 class retired).
    _install_provider()
    state = SelectWindowState(PANEL_ID, "pick", window=1)
    rendered = run(render_panel(_spec(), _ctx(), window=state))
    select = _select_of(rendered)
    assert list(select.options) == [f"cog_{i:02d}" for i in range(25, 30)]
    assert select.placeholder == "Pick one… — page 2/2"
    assert [c.disabled for c in _nav_of(rendered)] == [False, True]


def test_render_window_state_rides_ctx_params():
    # the renderer_override thread: the engine stashes the window under the
    # reserved ctx.params key and render_panel picks it up (the cog_routing
    # detail re-calls render_panel(spec, ctx) itself).
    _install_provider()
    ctx = _ctx()
    ctx.params[sw.WINDOW_PARAM] = SelectWindowState(PANEL_ID, "pick", 1)
    rendered = run(render_panel(_spec(), ctx))
    assert _select_of(rendered).placeholder == "Pick one… — page 2/2"


def test_render_short_list_stays_a_plain_select():
    # ≤ one window: no placeholder suffix, no nav — a windowed declaration
    # costs a short list nothing (the shipped page_count > 1 arming).
    _install_provider(options=OPTIONS[:10])
    rendered = run(render_panel(_spec(), _ctx()))
    select = _select_of(rendered)
    assert len(select.options) == 10
    assert select.placeholder == "Pick one…"
    assert _nav_of(rendered) == []


def test_render_undeclared_selector_keeps_the_truncation_verbatim():
    # the non-churn guarantee: windowed=False keeps the pre-successor
    # first-25 truncation and renders zero selwin bytes.
    _install_provider()
    rendered = run(render_panel(_spec(windowed=False), _ctx()))
    select = _select_of(rendered)
    assert len(select.options) == 25
    assert select.options[-1] == "cog_24"
    assert select.placeholder == "Pick one…"
    assert _nav_of(rendered) == []


def test_render_clamps_multi_select_bounds_to_the_window():
    # the shipped per-window clamp: Discord rejects max_values above the
    # visible option count (the 5-option last window).
    _install_provider()
    spec = PanelSpec(
        panel_id=PANEL_ID, subsystem="setup", title="Pick",
        audience=Audience.INVOKER,
        selectors=(
            SelectorSpec(
                selector_id="pick", kind=SelectorKind.ENUM,
                options_source=ProviderRef("selwin.options"),
                placeholder="Pick many…", min_values=1, max_values=10,
                windowed=True),
        ),
        layout=LayoutSpec(pages=(PageSpec(rows=(("pick",),)),)))
    state = SelectWindowState(PANEL_ID, "pick", window=1)
    rendered = run(render_panel(spec, _ctx(), window=state))
    select = _select_of(rendered)
    assert len(select.options) == 5
    assert select.max_values == 5 and select.min_values == 1


# --- dispatch contract (mirrors test_browserview_contract) ------------------------

class FakeResponder:
    from sb.kernel.interaction.request import Surface as _S
    surface = _S.COMPONENT

    def __init__(self):
        self.denials: list = []
        self.acks: list = []

    def is_acked(self):
        return bool(self.acks)

    def committed_visibility(self):
        return None

    async def ack(self, *, ephemeral):
        self.acks.append(ephemeral)

    async def deny(self, message, *, ephemeral):
        self.denials.append(message)

    async def render(self, result):
        pass


class FakePresenter:
    def __init__(self):
        self.presented: list[RenderedPanel] = []
        self._next_id = 500

    async def __call__(self, rendered, req):
        self.presented.append(rendered)
        self._next_id += 1
        return self._next_id


class FakeInteraction:
    def __init__(self, custom_id, values=None, message=None):
        self.data = {"custom_id": custom_id}
        if values is not None:
            self.data["values"] = list(values)
        self.guild = None
        self.user = None
        self.channel_id = 7
        self.id = 1
        if message is not None:
            self.message = message


def _armed():
    _install_provider()
    register_panel(_spec())
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    return presenter


def test_selwin_id_routes_as_a_nav_binding():
    from sb.kernel.panels.registry import NavBinding
    from sb.kernel.panels.router import route as route_custom_id

    routed = route_custom_id("nav:selwin:next:setup.pick_many:pick:0")
    assert isinstance(routed, NavBinding) and routed.kind == "selwin"


def test_next_click_re_renders_the_second_window():
    presenter = _armed()
    responder = FakeResponder()
    run(dispatch_component(
        FakeInteraction("nav:selwin:next:setup.pick_many:pick:0"),
        responder=responder))
    assert not responder.denials
    select = _select_of(presenter.presented[-1])
    assert list(select.options) == [f"cog_{i:02d}" for i in range(25, 30)]
    assert select.placeholder == "Pick one… — page 2/2"


def test_rendered_nav_ids_round_trip_through_dispatch():
    # end-to-end: render arms the nav, and the Next button's own custom_id,
    # fed back through the SAME dispatch seam, advances the window — the
    # loop closes with no hand-built id.
    presenter = _armed()
    rendered = run(render_panel(_spec(), _ctx()))
    next_btn = next(c for c in rendered.components if c.label == "Next ▶")
    run(dispatch_component(FakeInteraction(next_btn.custom_id),
                           responder=FakeResponder()))
    assert _select_of(presenter.presented[-1]).options[0] == "cog_25"


def test_stale_or_malformed_selwin_click_lands_on_polite_expiry():
    presenter = _armed()
    responder = FakeResponder()
    # unknown selector on a registered panel → expiry, never a crash.
    run(dispatch_component(
        FakeInteraction("nav:selwin:next:setup.pick_many:ghost:0"),
        responder=responder))
    assert responder.denials and "expired" in responder.denials[0].lower()
    assert not presenter.presented


def test_selwin_click_refreshes_a_live_session_in_place():
    # a window flip on a message holding a live session EDITS it (the
    # shipped SelectWindow edited its own message — no second card).
    presenter = _armed()
    spec = _spec()
    req = SimpleNamespace(
        surface=None, target=None, actor=make_actor(), guild_id=42,
        channel_id=7, args={}, responder=FakeResponder(),
        origin=SimpleNamespace(), request_id="r1")
    key = run(panel_engine._render_and_present(spec, req))
    assert presenter.presented       # the opening render
    message = SimpleNamespace(id=key)
    run(dispatch_component(
        FakeInteraction("nav:selwin:next:setup.pick_many:pick:0",
                        message=message),
        responder=FakeResponder()))
    refreshed = presenter.presented[-1]
    # the refresh presents with edit_message_ref set — an in-place edit.
    assert refreshed.edit_message_ref is not None
    assert _select_of(refreshed).options[0] == "cog_25"
