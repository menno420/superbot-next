"""The windowed-select engine (K8/S9b — the windowed-select grammar
successor, ORDER 019 item 7).

ONE generic, kernel-level engine that pages any declared string-select whose
option set exceeds Discord's 25-option cap: the shipped ``SelectWindow``
grammar (menno420/superbot ``views/paginated_select.py`` — the #1050 helper
that retired the #1040 ``options[:25]`` silent-drop class) made declarative.
A ``SelectorSpec`` opts in with ``windowed=True``; the render layer then
shows one ≤``page_size``-option window of the materialized options, carries
the window position in the select's placeholder (the shipped
``{placeholder} — page {p+1}/{n}`` byte shape), and injects ◀ Prev / Next ▶
nav buttons (the shipped ``_PageButton`` faces) — ONLY when the list spans
more than one window, so a short list stays a plain select (the shipped
``page_count > 1`` arming). Selection dispatch is untouched: the select
keeps its static ``<panel_id>.<selector_id>`` custom_id and its ``values``
round-trip, so ``on_select`` handlers see every option value regardless of
which window it was picked from.

State round-trips through the SAME custom-id grammar the rest of the panel
runtime uses (§3.4): the nav buttons live in the engine-injected ``nav:*``
family (the BrowserView precedent, D-0034) and are PARSED at click time —
the {selector × window} space is combinatorial, never pre-minted — but they
stay inside the nav namespace, not a parallel routing scheme.

Custom-id grammar (one control per id, the current window carried
verbatim)::

    nav:selwin:<control>:<panel_id>:<selector_id>:<window>

  * ``<control>`` ∈ {prev, next} — which nav button emitted the id (the
    window indicator rides the select's PLACEHOLDER, never a third button —
    two buttons keep a windowed select viable on a shared button row, the
    shipped ``nav_row`` row-budget posture);
  * ``<panel_id>`` / ``<selector_id>`` — the declared identity (neither
    carries a ``:``);
  * ``<window>`` — the current window index.

The two ad-hoc precedents this construct retires: the access_map feature
select and the setup 43-cog routing picker both showed only the first 25
options of a longer provider harvest (their module ledgers name this
successor).

Same-band leaf: imports only sibling kernel.panels modules + sb.spec.
"""

from __future__ import annotations

from dataclasses import dataclass, replace as _dc_replace

from sb.kernel.panels.browserview import paginate
from sb.kernel.panels.registry import NAV_ROW
from sb.kernel.panels.render import RenderedComponent
from sb.spec.panels import ActionStyle

__all__ = [
    "NEXT_LABEL",
    "PREV_LABEL",
    "SELWIN_ID_PREFIX",
    "SelectWindowState",
    "WINDOW_PARAM",
    "apply_window_delta",
    "decode_window",
    "encode_window",
    "is_selwin_id",
    "window_panel_id",
    "window_controls",
    "window_options",
    "windowed_placeholder",
]

# The engine-injected window-nav control family — a member of the ``nav:*``
# namespace (the BrowserView ``nav:browse:`` precedent), parsed at click time
# by the §3.4 router, dispatched through the ONE panel-engine seam.
SELWIN_ID_PREFIX = "nav:selwin:"

#: The reserved PanelContext.params key the engine uses to thread a window
#: state into a render — renderer_override panels that re-call
#: ``render_panel(spec, ctx)`` themselves (the cog_routing detail) inherit
#: the window through the context, no signature ripple.
WINDOW_PARAM = "__select_window__"

# The shipped nav-button faces (views/paginated_select.py ``_PageButton``).
PREV_LABEL = "◀ Prev"
NEXT_LABEL = "Next ▶"

# Discord's hard cap on select options — the maximum window size.
MAX_OPTIONS = 25

_CONTROLS = ("prev", "next")


@dataclass(frozen=True)
class SelectWindowState:
    """{panel, selector, window index} — the whole window position, carried
    verbatim in both nav buttons' custom_ids."""

    panel_id: str
    selector_id: str
    window: int = 0


# --- pure window algebra ---------------------------------------------------------

def window_size_of(selector_spec) -> int:
    """The effective window size: the declared page_size clamped to
    Discord's 25-option cap (floor 1)."""
    return max(1, min(int(getattr(selector_spec, "page_size", MAX_OPTIONS)
                          or MAX_OPTIONS), MAX_OPTIONS))


def window_options(options, page_size: int, window: int) -> tuple[list, int, int]:
    """(window slice, window_count, clamped window index) — the shared
    paging core (browserview.paginate): empty ⇒ one empty window,
    out-of-range windows clamp to the bounds."""
    return paginate(options, page_size, window)


def windowed_placeholder(placeholder: str, window: int, window_count: int) -> str:
    """The shipped ``_WindowSelect`` placeholder byte shape: the window
    position rides the placeholder (``{placeholder} — page {p+1}/{n}``,
    clamped to Discord's 150) — never a third nav button. A single window
    keeps the plain placeholder verbatim."""
    if window_count <= 1:
        return placeholder
    return f"{placeholder} — page {window + 1}/{window_count}"[:150]


# --- state codec (custom_id ⇄ SelectWindowState) ---------------------------------

def encode_window(control: str, state: SelectWindowState) -> str:
    """A nav button's custom_id carrying the CURRENT window verbatim."""
    return (f"{SELWIN_ID_PREFIX}{control}:{state.panel_id}:"
            f"{state.selector_id}:{state.window}")


def is_selwin_id(custom_id: str) -> bool:
    return custom_id.startswith(SELWIN_ID_PREFIX)


def _split(custom_id: str) -> tuple | None:
    if not custom_id.startswith(SELWIN_ID_PREFIX):
        return None
    parts = custom_id[len(SELWIN_ID_PREFIX):].split(":")
    if len(parts) != 4:
        return None
    if parts[0] not in _CONTROLS:
        return None
    return tuple(parts)


def window_panel_id(custom_id: str) -> str | None:
    """The panel identity from a selwin id — enough to look the spec up
    before the selector-aware full decode_window. None on a malformed id."""
    parsed = _split(custom_id)
    return parsed[1] if parsed else None


def decode_window(custom_id: str, spec) -> tuple[str, object, SelectWindowState] | None:
    """(control, the declared SelectorSpec, SelectWindowState) from a selwin
    id, resolved against the panel's declared selectors. None on a malformed
    id, an unknown selector, or a selector that is not declared ``windowed``
    (→ the router's polite expiry, never a crash)."""
    parts = _split(custom_id)
    if parts is None:
        return None
    control, panel_id, selector_id, window_s = parts
    try:
        window = int(window_s)
    except ValueError:
        return None
    selector = next(
        (s for s in getattr(spec, "selectors", ())
         if getattr(s, "selector_id", None) == selector_id), None)
    if selector is None or not getattr(selector, "windowed", False):
        return None
    return control, selector, SelectWindowState(
        panel_id=panel_id, selector_id=selector_id, window=window)


def apply_window_delta(control: str, state: SelectWindowState) -> SelectWindowState:
    """The new window a nav click lands on: prev steps back (clamped to 0),
    next steps forward (the upper bound clamps at render time, where the
    fresh option count is known — data re-resolves per click, §2.4)."""
    if control == "prev":
        return _dc_replace(state, window=max(state.window - 1, 0))
    if control == "next":
        return _dc_replace(state, window=state.window + 1)
    return state


# --- control rendering (RenderedComponent, disabled at the bounds) --------------

def window_controls(state: SelectWindowState, window_count: int,
                    resolver=None, locale=None) -> tuple[RenderedComponent, ...]:
    """The ◀ Prev / Next ▶ nav pair for one windowed select (the shipped
    ``_PageButton`` faces, secondary style, disabled at the bounds), riding
    the engine-injected nav row OUTSIDE the layout search space (§2.4).
    Injected ONLY when the options span more than one window — the shipped
    ``page_count > 1`` arming, so a short list renders zero nav bytes."""
    if window_count <= 1:
        return ()

    def copy(text: str) -> str:
        if resolver is None:
            return text
        return resolver.resolve(text, locale=locale)

    window = min(max(state.window, 0), window_count - 1)
    clamped = _dc_replace(state, window=window)
    return (
        RenderedComponent(
            kind="button", custom_id=encode_window("prev", clamped),
            label=copy(PREV_LABEL), row=NAV_ROW,
            style=ActionStyle.SECONDARY.value, disabled=window <= 0),
        RenderedComponent(
            kind="button", custom_id=encode_window("next", clamped),
            label=copy(NEXT_LABEL), row=NAV_ROW,
            style=ActionStyle.SECONDARY.value,
            disabled=window >= window_count - 1),
    )
