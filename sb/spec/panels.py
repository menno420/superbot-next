"""The declarative panel grammar (K8/S9b — design-spec §2.3/§2.4/§2.6 +
the Gate-0 L-24 presentation riders §1/§4).

One kernel ``PanelRuntimeView`` (sb/kernel/panels + the discord adapter)
interprets these specs; no per-panel view class exists for
grammar-expressible panels. Arrangement lives in exactly ONE structure per
panel — ``PanelSpec.layout`` [A] — never scattered on the child specs;
nav slots and page-turn controls are engine-injected OUTSIDE the searchable
space (§2.4's permanent sim exemption).

L-24 riders landed here:
  - ``EmbedFrameSpec.alt_text`` (rider 1 — declared-field depth; the
    non-empty compile fence sequences with the render-layer build);
  - ``ModalSpec``/``ModalFieldSpec`` (rider 4 — amendment G-10
    ``ModalFormSpec``, in-spec: the declarative modal FORM BODY replacing
    the ``open_modal(modal_ref)`` escape hatch; NOT a new dispatch surface —
    submit re-enters through the frozen MODAL adapter → ``resolve()``).

Stdlib-only leaf (imports only sibling sb.spec leaves).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Union

from sb.spec.confirmation import ConfirmationSpec
from sb.spec.outcomes import DeferMode
from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, ViewRef, WorkflowRef
from sb.spec.roles import register_field_roles

__all__ = [
    "AnchorPolicy",
    "ActionStyle",
    "Audience",
    "BlockSpec",
    "ColumnSpec",
    "EmbedFrameSpec",
    "FOLLOW_PARENT",
    "FieldsBlock",
    "FooterMode",
    "LayoutSpec",
    "ListBlock",
    "ListSpec",
    "ModalFieldSpec",
    "ModalFieldStyle",
    "ModalSpec",
    "NavRouteSpec",
    "NavigationSpec",
    "PageSpec",
    "PanelActionSpec",
    "PanelSpec",
    "ResultCardSpec",
    "ResultRender",
    "SelectorKind",
    "SelectorSpec",
    "TableBlock",
    "TableSpec",
    "TextBlock",
]

# NavigationSpec.home_hub routing-RULE sentinel: resolve the subsystem's
# CURRENT parent_hub from the manifest at render/click time (§2.4) — home
# routing follows arrangement without BEING arrangement.
FOLLOW_PARENT = "__follow_parent__"


# --- frame + body blocks (§2.3) ------------------------------------------------

class FooterMode(enum.Enum):
    NONE = "none"
    SUBSYSTEM = "subsystem"
    PROVENANCE = "provenance"


@dataclass(frozen=True)
class EmbedFrameSpec:
    """clamp_embed + home_embed_frame + the ad-hoc builders folded into one
    budgeted renderer — the ENGINE enforces Discord's size limits (clamping
    is not a per-callsite courtesy)."""

    style_token: str = ""                       # [S]
    max_fields: int = 25                        # [S] Discord hard cap is 25
    field_budget_chars: int = 1024              # [S] per-field value budget
    footer_mode: FooterMode = FooterMode.SUBSYSTEM   # [S]
    thumbnail_ref: str = ""                     # [S]
    alt_text: str = ""                          # [S] L-24 rider 1 ("" = none)


@dataclass(frozen=True)
class TextBlock:
    text: str                                   # [S] semantic copy


@dataclass(frozen=True)
class FieldsBlock:
    provider: ProviderRef                       # [S] read-model provider, never inline queries


@dataclass(frozen=True)
class ColumnSpec:
    key: str                                    # [S] the row-dict key the provider emits
    label: str                                  # [S] semantic copy


@dataclass(frozen=True)
class TableSpec:
    """Bounded rendering — one shared BrowserView engine renders every
    inventory/dex/browser/leaderboard/audit list (§2.3)."""

    columns: tuple[ColumnSpec, ...]             # [S]
    page_size: int = 10                         # [S]
    max_pages: int = 10                         # [S]
    empty_state: str = "Nothing to show."       # [S] semantic copy
    sort_options: tuple[str, ...] = ()          # [S]
    filter_options: tuple[str, ...] = ()        # [S]
    default_sort: str = ""                      # [A] the sim may pick the first ordering


@dataclass(frozen=True)
class ListSpec:
    item_render_ref: HandlerRef | ProviderRef | None = None  # [S] row -> str renderer
    page_size: int = 10                         # [S]
    max_pages: int = 10                         # [S]
    empty_state: str = "Nothing to show."       # [S]
    sort_options: tuple[str, ...] = ()          # [S]
    filter_options: tuple[str, ...] = ()        # [S]
    default_sort: str = ""                      # [A]


@dataclass(frozen=True)
class TableBlock:
    table: TableSpec                            # [S]
    provider: ProviderRef | None = None         # [S] the rows source


@dataclass(frozen=True)
class ListBlock:
    list_spec: ListSpec                         # [S]
    provider: ProviderRef | None = None         # [S] the items source


BlockSpec = Union[TextBlock, FieldsBlock, TableBlock, ListBlock]


# --- layout (§2.3 LayoutSpec — THE one arrangement structure) -------------------

@dataclass(frozen=True)
class PageSpec:
    """One page: rows of component refs BY NAMESPACE ID (the panel's declared
    action_ids / selector_ids). Coverage is exhaustive and exclusive across
    the union of pages (compile rule, sb/kernel/panels/compile.py)."""

    rows: tuple[tuple[str, ...], ...]           # [A]


@dataclass(frozen=True)
class LayoutSpec:
    pages: tuple[PageSpec, ...]                 # [A] the sim's primary search space


# --- navigation (§2.4) ----------------------------------------------------------

@dataclass(frozen=True)
class NavRouteSpec:
    label: str                                  # [S] semantic copy
    route: PanelRef                             # [S]
    emoji: str = ""                             # [S]


@dataclass(frozen=True)
class NavigationSpec:
    """Serializable — kills the closure-backed BackTarget/chain_back stacks.
    Every route is re-resolved and capability-checked at click time; parents
    are rebuilt fresh, never captured."""

    parent: PanelRef | None = None              # [S]
    home_hub: str = FOLLOW_PARENT               # [S] the routing RULE, not a captured value
    show_help: bool = True                      # [S] the nav:help slot (custom_id verbatim)
    show_home: bool = True                      # [S] the nav:hub:<hub> slot (hub-keyed [S] mint)
    show_rules: bool = False                    # [S]
    extra_routes: tuple[NavRouteSpec, ...] = () # [S]


# --- selectors (§2.4) -----------------------------------------------------------

class SelectorKind(enum.Enum):
    CHANNEL = "channel"
    ROLE = "role"
    MEMBER = "member"
    SUBSYSTEM = "subsystem"
    ENUM = "enum"
    ENTITY = "entity"


@dataclass(frozen=True)
class SelectorSpec:
    selector_id: str                            # [S] namespaced within the panel
    kind: SelectorKind                          # [S]
    on_select: WorkflowRef | HandlerRef | None = None  # [S]
    options_source: tuple[str, ...] | ProviderRef = ()  # [S] static tuple | provider
    placeholder: str = ""                       # [S] semantic copy
    min_values: int = 1                         # [S]
    max_values: int = 1                         # [S] Q-0216: multi-valued targets default to multiplicity
    page_size: int = 25                         # [S] the engine paginates past Discord's cap
    empty_state: str = "No options available."  # [S]
    capability_required: str = ""               # [S] two-lane authority (§2.2)
    audience_tier: str = ""                     # [S]
    custom_id_override: str = ""                # [S] legacy verbatim pin (compat=True)
    usage_weight: float = 1.0                   # [O]

    @property
    def authority_ref(self) -> str:
        """The K6 ref the resolver duck-reads (capability beats tier; empty
        ⇒ K6's ADMIN-floor CAPABILITY lane)."""
        return self.capability_required or self.audience_tier or ""


# --- modal form body (L-24 rider 4 — amendment G-10, in-spec) -------------------

class ModalFieldStyle(enum.Enum):
    SHORT = "short"
    PARAGRAPH = "paragraph"


@dataclass(frozen=True)
class ModalFieldSpec:
    """One text-input row; ``field_id`` is the submitted-args key on
    surface=MODAL."""

    field_id: str                               # [S] namespaced
    label: str                                  # [S] semantic copy
    style: ModalFieldStyle = ModalFieldStyle.SHORT  # [S]
    required: bool = True                       # [S]
    min_length: int | None = None               # [S]
    max_length: int | None = None               # [S]
    placeholder: str = ""                       # [S] semantic copy
    default: str = ""                           # [S] pre-filled value


@dataclass(frozen=True)
class ModalSpec:
    """G-10 ModalFormSpec — the declarative modal FORM (not a dispatch
    surface). On submit the MODAL adapter builds a ResolveRequest with
    surface=MODAL, args = the field_id values, target.spec = the declaring
    PanelActionSpec — the form is data; C-1 guarantees are inherited."""

    modal_id: str                               # [S] namespace kind `modal`; the custom-id root
    title: str                                  # [S] semantic copy
    fields: tuple[ModalFieldSpec, ...]          # [S] 1..5 (Discord cap; compile-checked)
    on_submit: WorkflowRef | HandlerRef | None = None  # [S] returns WorkflowResult


# --- actions (§2.6 — the renamed action primitive, decision 1) ------------------

class ActionStyle(enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    LINK = "link"


class ResultRender(enum.Enum):
    TOAST = "toast"
    REFRESH_PANEL = "refresh_panel"
    RESULT_CARD = "result_card"
    NONE = "none"


@dataclass(frozen=True)
class ResultCardSpec:
    frame: EmbedFrameSpec = EmbedFrameSpec()    # [S]


@dataclass(frozen=True)
class PanelActionSpec:
    """The UI primitive (the shipped automation record ports separately as
    ``AutomationActionSpec``; the bare name ``ActionSpec`` is tombstoned).
    The kernel-generated callback is FIXED: authority → defer → confirm →
    handler → Result grammar → render; domains cannot reorder or omit."""

    action_id: str                              # [S] unique within its panel; custom-id leaf
    label: str                                  # [S] semantic copy
    emoji: str = ""                             # [S]
    style: ActionStyle = ActionStyle.SECONDARY  # [S] compile rule: destructive ⇒ DANGER
    capability_required: str = ""               # [S] config/governance lane (empty ⇒ ADMIN floor)
    audience_tier: str = ""                     # [S] domain lane
    defer_mode: DeferMode = DeferMode.AUTO      # [S]
    handler: WorkflowRef | HandlerRef | PanelRef | None = None  # [S] PanelRef = open-child (OPEN_PANEL terminal)
    modal: ModalSpec | None = None              # [S] G-10: defer_mode==MODAL ⇒ modal is not None
    confirm: ConfirmationSpec | None = None     # [S] compile rule: irreversible workflow ⇒ required
    result_render: ResultRender = ResultRender.RESULT_CARD  # [S]
    result_card: ResultCardSpec | None = None   # [S]
    audit: str = ""                             # [S] compile rule: mutating handlers name their audit event
    visible_when: str = ""                      # [S] PredicateRef string form
    custom_id_override: str = ""                # [S] legacy verbatim pin; may NOT start with a scheme token
    destructive: bool = False                   # [O]+safety: never row 0 (hard layout constraint)
    usage_weight: float = 1.0                   # [O]
    co_use_group: str = ""                      # [O]
    flow_stage: int = 0                         # [O]

    @property
    def authority_ref(self) -> str:
        """Duck-read by resolve() step 1 — capability beats tier; empty ⇒
        K6's ADMIN-floor CAPABILITY lane (the shipped invariant, verbatim)."""
        return self.capability_required or self.audience_tier or ""

    @property
    def route(self) -> WorkflowRef | HandlerRef | PanelRef | None:
        return self.handler


# --- the panel root (§2.3) ------------------------------------------------------

class Audience(enum.Enum):
    INVOKER = "invoker"          # invoker-locked ephemeral session
    PUBLIC = "public"            # shared panel
    PERSISTENT = "persistent"    # restart-safe anchored panel


class AnchorPolicy(enum.Enum):
    REPLY = "reply"
    CHANNEL_ANCHOR = "channel_anchor"
    DM = "dm"


@dataclass(frozen=True)
class PanelSpec:
    panel_id: str                               # [S] namespace kind `panel`; the custom-id root
    subsystem: str                              # [S] owner key
    title: str                                  # [S] semantic copy
    audience: Audience = Audience.INVOKER       # [S]
    anchor_policy: AnchorPolicy = AnchorPolicy.REPLY  # [S]
    timeout_s: int | None = 180                 # [S] compile rule: None required when persistent
    frame: EmbedFrameSpec = EmbedFrameSpec()    # [S]
    body: tuple[BlockSpec, ...] = ()            # [S] typed content blocks
    actions: tuple[PanelActionSpec, ...] = ()   # [S]
    selectors: tuple[SelectorSpec, ...] = ()    # [S]
    navigation: NavigationSpec = NavigationSpec()  # [S]
    layout: LayoutSpec = LayoutSpec(pages=())   # [A] the ONE arrangement structure
    renderer_override: HandlerRef | None = None # [S] escape hatch (§2.9); requires justification
    legacy_view: ViewRef | None = None          # [S] contingency lane (§2.9 tier-3)
    justification: str = ""                     # [S] required with renderer_override/legacy_view
    session_lifecycle: bool = False             # [S] the never-strand game-view exemption
    usage_weight: float = 1.0                   # [O]
    co_open_group: str = ""                     # [O]

    def component_ids(self) -> tuple[str, ...]:
        """The declared (layout-addressable) component population."""
        return tuple(a.action_id for a in self.actions) + tuple(
            s.selector_id for s in self.selectors)


# --- P5 role registrations (design-spec §2.0; A-2-ledgered same-PR) -------------

register_field_roles(
    "EmbedFrameSpec",
    style_token="S", max_fields="S", field_budget_chars="S",
    footer_mode="S", thumbnail_ref="S", alt_text="S",
)
register_field_roles("TextBlock", text="S")
register_field_roles("FieldsBlock", provider="S")
register_field_roles("ColumnSpec", key="S", label="S")
register_field_roles(
    "TableSpec",
    columns="S", page_size="S", max_pages="S", empty_state="S",
    sort_options="S", filter_options="S", default_sort="A",
)
register_field_roles(
    "ListSpec",
    item_render_ref="S", page_size="S", max_pages="S", empty_state="S",
    sort_options="S", filter_options="S", default_sort="A",
)
register_field_roles("TableBlock", table="S", provider="S")
register_field_roles("ListBlock", list_spec="S", provider="S")
register_field_roles("PageSpec", rows="A")
register_field_roles("LayoutSpec", pages="A")
register_field_roles("NavRouteSpec", label="S", route="S", emoji="S")
register_field_roles(
    "NavigationSpec",
    parent="S", home_hub="S", show_help="S", show_home="S",
    show_rules="S", extra_routes="S",
)
register_field_roles(
    "SelectorSpec",
    selector_id="S", kind="S", on_select="S", options_source="S",
    placeholder="S", min_values="S", max_values="S", page_size="S",
    empty_state="S", capability_required="S", audience_tier="S",
    custom_id_override="S", usage_weight="O",
)
register_field_roles(
    "ModalFieldSpec",
    field_id="S", label="S", style="S", required="S", min_length="S",
    max_length="S", placeholder="S", default="S",
)
register_field_roles("ModalSpec", modal_id="S", title="S", fields="S", on_submit="S")
register_field_roles("ResultCardSpec", frame="S")
register_field_roles(
    "PanelActionSpec",
    action_id="S", label="S", emoji="S", style="S", capability_required="S",
    audience_tier="S", defer_mode="S", handler="S", modal="S", confirm="S",
    result_render="S", result_card="S", audit="S", visible_when="S",
    custom_id_override="S", destructive="O", usage_weight="O",
    co_use_group="O", flow_stage="O",
)
register_field_roles(
    "PanelSpec",
    panel_id="S", subsystem="S", title="S", audience="S", anchor_policy="S",
    timeout_s="S", frame="S", body="S", actions="S", selectors="S",
    navigation="S", layout="A", renderer_override="S", legacy_view="S",
    justification="S", session_lifecycle="S", usage_weight="O",
    co_open_group="O",
)
