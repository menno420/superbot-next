"""Unit tests for the shared BrowserView engine (K8/S9b — D-0034): the pure
sort / filter / paging algebra, the state codec (custom_id ⇄ BrowseState),
the control descriptors + bounds-disable, and the custom_id grammar
conformance."""

from __future__ import annotations

from sb.kernel.panels import browserview as bv
from sb.kernel.panels.browserview import (
    ALL_FILTER,
    BROWSE_ID_PREFIX,
    BrowseState,
    browse_page,
    decode,
    encode,
    filter_items,
    paginate,
    sort_items,
)
from sb.spec.panels import ListBlock, ListSpec, PageSpec, LayoutSpec, PanelSpec

# --- fixtures -------------------------------------------------------------------

ROWS = (
    {"name": "Axe", "type": "Tools", "quantity": 3, "rarity": 2},
    {"name": "Copper", "type": "Mining", "quantity": 40, "rarity": 1},
    {"name": "Diamond", "type": "Mining", "quantity": 1, "rarity": 5},
    {"name": "Bread", "type": "Food", "quantity": 12, "rarity": 1},
    {"name": "Rod", "type": "Tools", "quantity": 2, "rarity": 3},
)

LS = ListSpec(
    page_size=2,
    sort_options=("name", "quantity", "-rarity"),
    filter_options=("Tools", "Mining", "Food"),
    default_sort="name")


def _panel(list_spec=LS, panel_id="inv.cat_tools"):
    return PanelSpec(
        panel_id=panel_id, subsystem="inventory", title="Cat",
        body=(ListBlock(list_spec=list_spec),),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)))


# --- sort (each declared key, stable) -------------------------------------------

def test_sort_by_name_ascending():
    out = sort_items(ROWS, "name")
    assert [r["name"] for r in out] == ["Axe", "Bread", "Copper", "Diamond", "Rod"]


def test_sort_by_quantity_ascending():
    out = sort_items(ROWS, "quantity")
    assert [r["quantity"] for r in out] == [1, 2, 3, 12, 40]


def test_sort_descending_marker():
    out = sort_items(ROWS, "-rarity")
    assert [r["rarity"] for r in out] == [5, 3, 2, 1, 1]


def test_sort_is_stable_on_ties():
    # two rarity==1 rows (Copper then Bread by input order) keep their order
    # under a rarity sort (stable).
    out = sort_items(ROWS, "rarity")
    ties = [r["name"] for r in out if r["rarity"] == 1]
    assert ties == ["Copper", "Bread"]


def test_sort_empty_key_is_identity():
    assert sort_items(ROWS, "") == list(ROWS)


def test_sort_none_values_trail():
    rows = ({"k": 2}, {"k": None}, {"k": 1})
    assert [r["k"] for r in sort_items(rows, "k")] == [1, 2, None]


# --- filter (each declared option + all) ----------------------------------------

def test_filter_each_declared_option():
    assert {r["name"] for r in filter_items(ROWS, "Tools")} == {"Axe", "Rod"}
    assert {r["name"] for r in filter_items(ROWS, "Mining")} == {"Copper", "Diamond"}
    assert {r["name"] for r in filter_items(ROWS, "Food")} == {"Bread"}


def test_filter_all_is_passthrough():
    assert filter_items(ROWS, ALL_FILTER) == list(ROWS)
    assert filter_items(ROWS, "") == list(ROWS)


def test_filter_unmatched_is_empty():
    assert filter_items(ROWS, "Nonexistent") == []


# --- paging (first / middle / last / single / empty, bounds) --------------------

def test_paginate_first_page():
    page, count, idx = paginate(ROWS, 2, 0)
    assert count == 3 and idx == 0 and [r["name"] for r in page] == ["Axe", "Copper"]


def test_paginate_middle_page():
    page, count, idx = paginate(ROWS, 2, 1)
    assert count == 3 and idx == 1 and [r["name"] for r in page] == ["Diamond", "Bread"]


def test_paginate_last_page_partial():
    page, count, idx = paginate(ROWS, 2, 2)
    assert count == 3 and idx == 2 and [r["name"] for r in page] == ["Rod"]


def test_paginate_out_of_range_clamps_to_last():
    page, count, idx = paginate(ROWS, 2, 99)
    assert idx == 2 and [r["name"] for r in page] == ["Rod"]


def test_paginate_negative_clamps_to_first():
    _, _, idx = paginate(ROWS, 2, -5)
    assert idx == 0


def test_paginate_single_page():
    page, count, idx = paginate(ROWS, 50, 0)
    assert count == 1 and idx == 0 and len(page) == 5


def test_paginate_empty():
    page, count, idx = paginate((), 2, 0)
    assert page == [] and count == 1 and idx == 0


# --- browse_page (filter → sort → paginate, deterministic) ----------------------

def test_browse_page_filter_then_sort_then_page():
    state = BrowseState("inv.cat_tools", 0, sort="quantity", filter="Mining", page=0)
    page, count, idx = browse_page(ROWS, LS, state)
    # Mining = {Copper q40, Diamond q1}; sorted by quantity asc; page_size 2.
    assert count == 1 and [r["name"] for r in page] == ["Diamond", "Copper"]


def test_browse_page_uses_default_sort_when_unset():
    state = BrowseState("inv.cat_tools", 0, sort="", filter=ALL_FILTER, page=0)
    page, _, _ = browse_page(ROWS, LS, state)
    # default_sort="name" → first page is Axe, Bread
    assert [r["name"] for r in page] == ["Axe", "Bread"]


# --- state encode / decode round-trip -------------------------------------------

def test_encode_grammar_conformance():
    state = BrowseState("inv.cat_tools", 0, sort="quantity", filter="Mining", page=2)
    cid = encode("next", state, LS)
    assert cid == "nav:browse:next:inv.cat_tools:0:1:1:2"
    assert cid.startswith(BROWSE_ID_PREFIX)
    # colon-delimited, panel_id carries no colon.
    assert cid[len(BROWSE_ID_PREFIX):].split(":") == \
        ["next", "inv.cat_tools", "0", "1", "1", "2"]


def test_encode_default_sort_and_all_filter_are_negative_one():
    state = BrowseState("inv.cat_tools", 0, sort="", filter=ALL_FILTER, page=0)
    cid = encode("sort", state, LS)
    assert cid == "nav:browse:sort:inv.cat_tools:0:-1:-1:0"


def test_decode_round_trip():
    spec = _panel()
    state = BrowseState("inv.cat_tools", 0, sort="-rarity", filter="Food", page=1)
    cid = encode("prev", state, LS)
    control, block, decoded = decode(cid, spec)
    assert control == "prev" and block == 0
    assert decoded == state


def test_decode_default_sort_resolves_from_spec():
    spec = _panel()
    cid = "nav:browse:sort:inv.cat_tools:0:-1:-1:0"
    _, _, decoded = decode(cid, spec)
    assert decoded.sort == "name"          # the declared default_sort
    assert decoded.filter == ALL_FILTER


def test_decode_rejects_malformed():
    spec = _panel()
    assert decode("nav:browse:sort:inv.cat_tools:0:1:1", spec) is None   # 5 parts
    assert decode("nav:browse:bogus:inv.cat_tools:0:1:1:0", spec) is None  # bad control
    assert decode("nav:browse:sort:inv.cat_tools:0:x:1:0", spec) is None   # non-int
    assert decode("totally_unrelated_id", spec) is None


def test_decode_rejects_unbrowsable_block():
    spec = _panel()
    # block index 3 does not exist in body
    assert decode("nav:browse:sort:inv.cat_tools:3:0:0:0", spec) is None


def test_panel_id_of():
    assert bv.panel_id_of("nav:browse:next:inv.cat_tools:0:1:1:2") == "inv.cat_tools"
    assert bv.panel_id_of("nope") is None


def test_is_browse_id():
    assert bv.is_browse_id("nav:browse:sort:p:0:0:0:0")
    assert not bv.is_browse_id("nav:page:p:1")
    assert not bv.is_browse_id("p.action")


# --- apply_delta (the click's state transition) ---------------------------------

def test_apply_delta_sort_resets_page():
    state = BrowseState("p", 0, sort="name", filter="Tools", page=3)
    new = bv.apply_delta("sort", state, LS, values=("quantity",))
    assert new.sort == "quantity" and new.filter == "Tools" and new.page == 0


def test_apply_delta_filter_resets_page():
    state = BrowseState("p", 0, sort="name", filter="Tools", page=3)
    new = bv.apply_delta("filter", state, LS, values=(ALL_FILTER,))
    assert new.filter == ALL_FILTER and new.page == 0 and new.sort == "name"


def test_apply_delta_next_and_prev_step_page():
    state = BrowseState("p", 0, sort="name", filter="Tools", page=1)
    assert bv.apply_delta("next", state, LS, None).page == 2
    assert bv.apply_delta("prev", state, LS, None).page == 0
    # prev clamps at zero
    zero = BrowseState("p", 0, page=0)
    assert bv.apply_delta("prev", zero, LS, None).page == 0


# --- control descriptors + bounds-disable ---------------------------------------

def _controls(state, page_count):
    return bv.browse_controls(LS, state, page_count)


def test_controls_expose_declared_sort_and_filter_choices():
    state = BrowseState("inv.cat_tools", 0, sort="name", filter=ALL_FILTER, page=0)
    controls = _controls(state, 3)
    selectors = [c for c in controls if c.kind == "selector"]
    assert len(selectors) == 2
    sort_sel, filter_sel = selectors
    assert [o["value"] for o in sort_sel.options] == ["name", "quantity", "-rarity"]
    # descending marker is stripped from the label, never the value
    assert dict(zip((o["value"] for o in sort_sel.options),
                    (o["label"] for o in sort_sel.options)))["-rarity"] == "rarity"
    # filter select leads with the All pseudo-option, then the declared options
    assert [o["value"] for o in filter_sel.options] == \
        [ALL_FILTER, "Tools", "Mining", "Food"]


def test_controls_mark_current_selection_default():
    state = BrowseState("inv.cat_tools", 0, sort="quantity", filter="Mining", page=0)
    controls = _controls(state, 3)
    sort_sel, filter_sel = [c for c in controls if c.kind == "selector"]
    assert {o["value"]: o["default"] for o in sort_sel.options}["quantity"] is True
    assert {o["value"]: o["default"] for o in filter_sel.options}["Mining"] is True


def test_controls_disable_prev_on_first_page():
    controls = _controls(BrowseState("p", 0, page=0), 3)
    buttons = {c.label: c for c in controls if c.kind == "button"}
    assert buttons["◀"].disabled is True
    assert buttons["▶"].disabled is False


def test_controls_disable_next_on_last_page():
    controls = _controls(BrowseState("p", 0, page=2), 3)
    buttons = {c.label: c for c in controls if c.kind == "button"}
    assert buttons["◀"].disabled is False
    assert buttons["▶"].disabled is True


def test_controls_single_page_disables_both_nav():
    controls = _controls(BrowseState("p", 0, page=0), 1)
    buttons = {c.label: c for c in controls if c.kind == "button"}
    assert buttons["◀"].disabled is True
    assert buttons["▶"].disabled is True


def test_controls_page_indicator_disabled_and_labelled():
    controls = _controls(BrowseState("p", 0, page=1), 3)
    indicator = next(c for c in controls if c.label == "Page 2/3")
    assert indicator.disabled is True and indicator.kind == "button"


def test_controls_omit_filter_select_when_no_filter_options():
    ls = ListSpec(page_size=2, sort_options=("name",), filter_options=())
    controls = bv.browse_controls(ls, BrowseState("p", 0, sort="name"), 1)
    assert [c.kind for c in controls if c.kind == "selector"] == ["selector"]  # sort only


def test_default_browse_state_arms_the_declared_block():
    # a spec whose first browsable block declares an algebra opens on its
    # default_sort, no filter, page 0 — the render path's arming hook.
    state = bv.default_browse_state(_panel())
    assert state == BrowseState(
        panel_id="inv.cat_tools", block=0, sort="name", filter=ALL_FILTER, page=0)


def test_default_browse_state_is_none_without_a_browse_block():
    # no ListSpec algebra ⇒ None ⇒ the byte-identical static render (no surface
    # changes until it DECLARES options).
    plain = ListSpec(page_size=2)      # no sort_options / filter_options
    assert bv.default_browse_state(_panel(list_spec=plain)) is None


def test_controls_button_custom_ids_carry_current_state():
    state = BrowseState("inv.cat_tools", 0, sort="quantity", filter="Mining", page=1)
    controls = _controls(state, 3)
    prev = next(c for c in controls if c.label == "◀")
    nxt = next(c for c in controls if c.label == "▶")
    assert prev.custom_id == "nav:browse:prev:inv.cat_tools:0:1:1:1"
    assert nxt.custom_id == "nav:browse:next:inv.cat_tools:0:1:1:1"
