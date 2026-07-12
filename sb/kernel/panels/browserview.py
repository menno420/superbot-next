"""The shared BrowserView engine (K8/S9b — design-spec §2.3; D-0034).

ONE generic, kernel-level engine that renders interactive sort / filter /
paging controls for any Table/List block whose ``ListSpec``/``TableSpec``
declares ``sort_options`` / ``filter_options`` / a page size. It is
per-surface DECLARED, never hard-coded to a domain: given the block's items
plus its declared browse algebra plus the current browse state, it produces
the current page's slice AND the interactive controls (a sort select, a
filter select when filter_options present, prev/next page buttons + a
disabled page indicator), disabled appropriately at the paging bounds.

State round-trips through the SAME custom-id grammar the rest of the panel
runtime uses (§3.4): the controls live in the engine-injected ``nav:*``
family (the page-turn control's richer sibling), so every browse click
re-enters through the ONE component adapter → the §3.4 router → the panel
engine, exactly like ``nav:page:``. Because the {sort × filter × page}
state space is combinatorial it is PARSED at click time (like the ``g<N>:``
dynamic ids), never pre-minted into the static table — but it stays inside
the nav namespace, not a parallel routing scheme.

Custom-id grammar (one control per id, current state carried verbatim)::

    nav:browse:<control>:<panel_id>:<block>:<sort_idx>:<filter_idx>:<page>

  * ``<control>`` ∈ {sort, filter, prev, next, page} — which control emitted
    the id (decides how the click's delta applies);
  * ``<panel_id>`` — the panel identity (never carries a ``:``);
  * ``<block>`` — the index of the List/Table block in ``PanelSpec.body``
    (a panel may host more than one browse block);
  * ``<sort_idx>`` — index into ``sort_options`` (``-1`` = the declared
    ``default_sort`` / no explicit sort);
  * ``<filter_idx>`` — index into ``filter_options`` (``-1`` = the "All"
    pseudo-option — no filter);
  * ``<page>`` — the current page index.

A ``sort`` / ``filter`` click carries its NEW selection in the interaction's
``values`` array (the ordinary select round-trip — the id only pins the
OTHER dimensions + resets the page); a ``prev`` / ``next`` click carries no
values, so its target page is derived from the id.

Stdlib-only algebra leaf (the render-model dataclass it emits is the sole
sibling import). Direction: a ``sort_options`` entry may lead with ``-`` to
sort DESCENDING (e.g. ``"-quantity"`` = highest first); the leading ``-`` is
stripped for the field lookup and never shown to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from sb.kernel.panels.render import RenderedComponent
from sb.spec.panels import ActionStyle, ListBlock, TableBlock

__all__ = [
    "ALL_FILTER",
    "ALL_LABEL",
    "BROWSE_ID_PREFIX",
    "BrowseState",
    "browse_block_spec",
    "browse_controls",
    "browse_page",
    "decode",
    "encode",
    "filter_items",
    "is_browse_id",
    "paginate",
    "panel_id_of",
    "sort_items",
]

# The engine-injected browse control family — a member of the ``nav:*``
# namespace (registry.NAV_PAGE_ID_PREFIX's richer sibling), so browse clicks
# ride the SAME router → panel-engine seam as every other nav slot.
BROWSE_ID_PREFIX = "nav:browse:"

#: The "no filter" state — distinct from the empty string so an explicit
#: "show everything" selection round-trips through the select's value.
ALL_FILTER = "__all__"
#: The user-facing label for the "All" pseudo-option (semantic copy).
ALL_LABEL = "All"

_CONTROLS = ("sort", "filter", "prev", "next", "page")

# Discord allows one select per action row; the engine parks its controls on
# rows below the panel's own content components and above the standard nav
# row (registry.NAV_ROW == 4). A browse-armed surface is list-first by
# construction (its search space is the list, not a button grid).
SORT_ROW = 1
FILTER_ROW = 2
PAGE_ROW = 3


@dataclass(frozen=True)
class BrowseState:
    """{panel/list identity, sort key, filter value, page index} — the whole
    browse position, carried verbatim in every control's custom_id."""

    panel_id: str
    block: int = 0
    sort: str = ""
    filter: str = ALL_FILTER
    page: int = 0


# --- the declared browse algebra (block spec accessor) --------------------------

def browse_block_spec(spec, block: int):
    """The ``ListSpec`` | ``TableSpec`` at body index *block* — the declared
    browse algebra (sort_options / filter_options / default_sort / page_size)
    the engine interprets. Returns None when *block* is not a browsable
    block."""
    body = getattr(spec, "body", ())
    if not 0 <= block < len(body):
        return None
    blk = body[block]
    if isinstance(blk, ListBlock):
        return blk.list_spec
    if isinstance(blk, TableBlock):
        return blk.table
    return None


# --- pure sort / filter / paging cores (deterministic, stable) ------------------

def _field(item: object, key: str):
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)


def _direction(sort: str) -> tuple[str, bool]:
    """(field key, reverse) — a leading ``-`` declares DESCENDING."""
    if sort.startswith("-"):
        return sort[1:], True
    return sort, False


def sort_items(items, sort: str, *,
               sort_of: Callable[[object, str], object] = _field) -> list:
    """Stable sort by the declared key (``-key`` = descending). An empty key
    is identity (declared insertion order — the sim's first ordering)."""
    key, reverse = _direction(sort or "")
    ordered = list(items)
    if not key:
        return ordered
    # (None sorts last regardless of direction; equal keys keep input order —
    # Python's sort is stable, so the algebra is deterministic).
    ordered.sort(key=lambda it: _field_present(sort_of(it, key)), reverse=reverse)
    return ordered


def _field_present(value):
    # None always trails; otherwise compare on the raw value (a browse field
    # is same-typed by construction — a surface with mixed types declares a
    # sort_of that normalizes).
    return (value is None, value)


def _default_filter_of(item: object) -> frozenset:
    if isinstance(item, Mapping):
        return frozenset(str(v) for v in item.values())
    return frozenset({str(item)})


def filter_items(items, value: str, *,
                 filter_of: Callable[[object], frozenset] = _default_filter_of) -> list:
    """Keep items whose declared filter set contains *value*. The ``All``
    pseudo-value (or empty) is passthrough."""
    if not value or value == ALL_FILTER:
        return list(items)
    return [it for it in items if value in filter_of(it)]


def paginate(items, page_size: int, page: int) -> tuple[list, int, int]:
    """(page slice, page_count, clamped page). Empty ⇒ one empty page;
    out-of-range pages clamp to the bounds (never an IndexError)."""
    seq = list(items)
    size = max(int(page_size or 1), 1)
    page_count = max((len(seq) + size - 1) // size, 1)
    page = min(max(int(page), 0), page_count - 1)
    start = page * size
    return seq[start:start + size], page_count, page


def browse_page(items, block_spec, state: BrowseState, *,
                sort_of: Callable[[object, str], object] = _field,
                filter_of: Callable[[object], frozenset] = _default_filter_of
                ) -> tuple[list, int, int]:
    """filter → sort → paginate, in that fixed order — the current page's
    items plus (page_count, clamped page). Deterministic for a given
    (items, spec, state)."""
    filtered = filter_items(items, state.filter, filter_of=filter_of)
    sort = state.sort or getattr(block_spec, "default_sort", "") or ""
    ordered = sort_items(filtered, sort, sort_of=sort_of)
    return paginate(ordered, getattr(block_spec, "page_size", 10), state.page)


# --- state codec (custom_id ⇄ BrowseState) --------------------------------------

def _index(options: tuple, value: str) -> int:
    try:
        return options.index(value)
    except ValueError:
        return -1


def encode(control: str, state: BrowseState, block_spec) -> str:
    """A control's custom_id carrying the CURRENT browse state verbatim."""
    sort_idx = _index(getattr(block_spec, "sort_options", ()), state.sort)
    filter_idx = _index(getattr(block_spec, "filter_options", ()), state.filter)
    return (f"{BROWSE_ID_PREFIX}{control}:{state.panel_id}:{state.block}:"
            f"{sort_idx}:{filter_idx}:{state.page}")


def is_browse_id(custom_id: str) -> bool:
    return custom_id.startswith(BROWSE_ID_PREFIX)


def panel_id_of(custom_id: str) -> str | None:
    """The panel identity from a browse id — enough to look the spec up before
    the block-aware full decode. None on a malformed id."""
    parsed = _split(custom_id)
    return parsed[1] if parsed else None


def _split(custom_id: str) -> tuple | None:
    if not custom_id.startswith(BROWSE_ID_PREFIX):
        return None
    parts = custom_id[len(BROWSE_ID_PREFIX):].split(":")
    if len(parts) != 6:
        return None
    control = parts[0]
    if control not in _CONTROLS:
        return None
    return parts


def decode(custom_id: str, spec) -> tuple[str, int, BrowseState] | None:
    """(control, block index, BrowseState) from a browse id, resolving the
    sort/filter indices against the panel's declared block algebra. None on a
    malformed id or an id whose block is not browsable (→ the router's polite
    expiry, never a crash)."""
    parts = _split(custom_id)
    if parts is None:
        return None
    control, panel_id, block_s, sort_s, filter_s, page_s = parts
    try:
        block = int(block_s)
        sort_idx = int(sort_s)
        filter_idx = int(filter_s)
        page = int(page_s)
    except ValueError:
        return None
    block_spec = browse_block_spec(spec, block)
    if block_spec is None:
        return None
    sort_options = getattr(block_spec, "sort_options", ())
    filter_options = getattr(block_spec, "filter_options", ())
    sort = (sort_options[sort_idx] if 0 <= sort_idx < len(sort_options)
            else (getattr(block_spec, "default_sort", "") or ""))
    filt = (filter_options[filter_idx] if 0 <= filter_idx < len(filter_options)
            else ALL_FILTER)
    return control, block, BrowseState(
        panel_id=panel_id, block=block, sort=sort, filter=filt, page=page)


def apply_delta(control: str, state: BrowseState, block_spec,
                values: tuple | None) -> BrowseState:
    """The new browse state a click lands on: a ``sort`` / ``filter`` select
    applies its chosen value (from *values*) and resets to page 0; a
    ``prev`` / ``next`` button steps the page (clamped to 0)."""
    if control == "sort":
        chosen = values[0] if values else state.sort
        return BrowseState(state.panel_id, state.block, sort=str(chosen),
                           filter=state.filter, page=0)
    if control == "filter":
        chosen = values[0] if values else state.filter
        return BrowseState(state.panel_id, state.block, sort=state.sort,
                           filter=str(chosen), page=0)
    if control == "prev":
        return BrowseState(state.panel_id, state.block, sort=state.sort,
                           filter=state.filter, page=max(state.page - 1, 0))
    if control == "next":
        return BrowseState(state.panel_id, state.block, sort=state.sort,
                           filter=state.filter, page=state.page + 1)
    return state          # the disabled page indicator is never clicked


# --- control rendering (RenderedComponent, disabled at the bounds) --------------

def browse_controls(block_spec, state: BrowseState, page_count: int,
                    resolver=None, locale=None) -> tuple[RenderedComponent, ...]:
    """The interactive controls for one browse block: a sort select (when
    sort_options declared), a filter select (when filter_options declared,
    with the leading "All" pseudo-option), prev/next page buttons + a disabled
    page indicator — the buttons disabled at the paging bounds. Copy runs
    through *resolver* when supplied (the L-24 CopyResolver seam)."""
    def copy(text: str) -> str:
        if resolver is None:
            return text
        return resolver.resolve(text, locale=locale)

    out: list[RenderedComponent] = []
    sort_options = getattr(block_spec, "sort_options", ())
    filter_options = getattr(block_spec, "filter_options", ())

    if sort_options:
        current_sort = state.sort or getattr(block_spec, "default_sort", "") or ""
        out.append(RenderedComponent(
            kind="selector", custom_id=encode("sort", state, block_spec),
            label=copy("Sort"), row=SORT_ROW, placeholder=copy("Sort"),
            options=tuple(
                {"label": copy(_option_label(o)), "value": o,
                 "default": o == current_sort}
                for o in sort_options)))

    if filter_options:
        options = [{"label": copy(ALL_LABEL), "value": ALL_FILTER,
                    "default": state.filter in ("", ALL_FILTER)}]
        options.extend(
            {"label": copy(_option_label(o)), "value": o,
             "default": o == state.filter}
            for o in filter_options)
        out.append(RenderedComponent(
            kind="selector", custom_id=encode("filter", state, block_spec),
            label=copy("Filter"), row=FILTER_ROW, placeholder=copy("Filter"),
            options=tuple(options)))

    page = min(max(state.page, 0), max(page_count - 1, 0))
    out.append(RenderedComponent(
        kind="button", custom_id=encode("prev", state, block_spec),
        label="◀", row=PAGE_ROW, style=ActionStyle.SECONDARY.value,
        disabled=page <= 0))
    out.append(RenderedComponent(
        kind="button", custom_id=encode("page", state, block_spec),
        label=copy(f"Page {page + 1}/{page_count}"), row=PAGE_ROW,
        style=ActionStyle.SECONDARY.value, disabled=True))
    out.append(RenderedComponent(
        kind="button", custom_id=encode("next", state, block_spec),
        label="▶", row=PAGE_ROW, style=ActionStyle.SECONDARY.value,
        disabled=page >= page_count - 1))
    return tuple(out)


def _option_label(option: str) -> str:
    """The user-facing label for a sort/filter option value — the ``-key``
    descending marker never reaches the label."""
    return option[1:] if option.startswith("-") else option
