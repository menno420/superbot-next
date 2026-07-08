"""Panel registration fences (K8/S9b — design-spec §2.3/§2.4/§2.6 compile
rules + the §3.4 custom-id scheme rules + the L-24 G-10 modal rules).

``check_panel(spec)`` raises ``PanelCompileError`` (failure-code constants
below) — run at registration time by ``sb.kernel.panels.registry``, the same
posture as the K7 workflow fences.
"""

from __future__ import annotations

import re

from sb.kernel.workflow.registry import REGISTRY as WORKFLOW_REGISTRY
from sb.kernel.workflow.result import IRREVERSIBLE
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    ModalSpec,
    PanelSpec,
)
from sb.spec.refs import WorkflowRef

__all__ = ["PanelCompileError", "check_panel"]

# Discord structural caps (§2.3 layout rules).
MAX_ROWS_PER_PAGE = 5
MAX_COMPONENTS_PER_ROW = 5
MAX_COMPONENTS_PER_PAGE = 25
MAX_MODAL_FIELDS = 5

# §3.4: a legacy custom_id_override may not begin with a scheme-version token.
_SCHEME_TOKEN_RE = re.compile(r"^[a-z]+\d+:")

# failure taxonomy
LAYOUT_COVERAGE = "layout_coverage"                 # missing/extra/duplicate component
LAYOUT_CAPS = "layout_caps"                          # Discord structural caps
PERSISTENT_TIMEOUT = "persistent_timeout"            # persistent ⇒ timeout_s None
DESTRUCTIVE_STYLE = "destructive_style"              # destructive ⇒ danger
DESTRUCTIVE_PLACEMENT = "destructive_placement"      # never row 0
MODAL_RULES = "modal_rules"                          # G-10 fences
CONFIRM_REQUIRED = "confirm_required"                # irreversible workflow ⇒ confirm
NEVER_STRAND = "never_strand"                        # unreachable-back panel
SCHEME_TOKEN_OVERRIDE = "scheme_token_override"      # legacy id collides with g<N>: family
ESCAPE_HATCH_JUSTIFICATION = "escape_hatch_justification"
COMPONENT_ID_DUP = "component_id_dup"


class PanelCompileError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code


def _check_modal(panel_id: str, owner: str, modal: ModalSpec) -> None:
    n = len(modal.fields)
    if not 1 <= n <= MAX_MODAL_FIELDS:
        raise PanelCompileError(
            MODAL_RULES,
            f"{panel_id}.{owner}: ModalSpec {modal.modal_id!r} has {n} fields "
            f"(Discord cap: 1..{MAX_MODAL_FIELDS})")
    field_ids = [f.field_id for f in modal.fields]
    if len(set(field_ids)) != len(field_ids):
        raise PanelCompileError(
            MODAL_RULES,
            f"{panel_id}.{owner}: ModalSpec {modal.modal_id!r} has duplicate field_ids")


def check_panel(spec: PanelSpec) -> None:  # noqa: PLR0912 — a fence enumerates its rules
    pid = spec.panel_id

    # component-id population (unique; the layout-addressable set).
    declared = spec.component_ids()
    if len(set(declared)) != len(declared):
        raise PanelCompileError(COMPONENT_ID_DUP, f"{pid}: duplicate component ids")
    declared_set = set(declared)

    # layout coverage: exhaustive AND exclusive over the union of pages.
    placed: list[str] = []
    for page_idx, page in enumerate(spec.layout.pages):
        if len(page.rows) > MAX_ROWS_PER_PAGE:
            raise PanelCompileError(
                LAYOUT_CAPS, f"{pid} page {page_idx}: {len(page.rows)} rows > {MAX_ROWS_PER_PAGE}")
        page_count = 0
        for row_idx, row in enumerate(page.rows):
            if len(row) > MAX_COMPONENTS_PER_ROW:
                raise PanelCompileError(
                    LAYOUT_CAPS,
                    f"{pid} page {page_idx} row {row_idx}: {len(row)} components "
                    f"> {MAX_COMPONENTS_PER_ROW}")
            page_count += len(row)
            placed.extend(row)
        if page_count > MAX_COMPONENTS_PER_PAGE:
            raise PanelCompileError(
                LAYOUT_CAPS,
                f"{pid} page {page_idx}: {page_count} components > {MAX_COMPONENTS_PER_PAGE}")
    placed_set = set(placed)
    if len(placed) != len(placed_set):
        dupes = sorted({c for c in placed if placed.count(c) > 1})
        raise PanelCompileError(LAYOUT_COVERAGE, f"{pid}: components placed twice: {dupes}")
    if declared_set - placed_set:
        raise PanelCompileError(
            LAYOUT_COVERAGE, f"{pid}: declared but unplaced: {sorted(declared_set - placed_set)}")
    if placed_set - declared_set:
        raise PanelCompileError(
            LAYOUT_COVERAGE, f"{pid}: placed but undeclared: {sorted(placed_set - declared_set)}")

    # persistent ⇒ timeout None (the shipped PersistentView contract).
    if spec.audience is Audience.PERSISTENT and spec.timeout_s is not None:
        raise PanelCompileError(
            PERSISTENT_TIMEOUT, f"{pid}: audience=persistent requires timeout_s=None")

    # escape hatches require justification (§2.9).
    if (spec.renderer_override is not None or spec.legacy_view is not None) \
            and not spec.justification:
        raise PanelCompileError(
            ESCAPE_HATCH_JUSTIFICATION,
            f"{pid}: renderer_override/legacy_view requires a non-empty justification")

    # never-strand (§2.4): a panel with no parent, no help, and no home fails
    # compile unless it is a session-lifecycle game view.
    nav = spec.navigation
    if (nav.parent is None and not nav.show_help and not nav.show_home
            and not spec.session_lifecycle):
        raise PanelCompileError(
            NEVER_STRAND,
            f"{pid}: no parent, no help, no home — unreachable back to Help/hub "
            f"(set session_lifecycle=True only for game session views)")

    # per-action rules.
    row0: set[str] = set()
    for page in spec.layout.pages:
        if page.rows:
            row0.update(page.rows[0])
    for action in spec.actions:
        aid = action.action_id
        if action.destructive and action.style is not ActionStyle.DANGER:
            raise PanelCompileError(
                DESTRUCTIVE_STYLE, f"{pid}.{aid}: destructive=True requires style=danger")
        if action.destructive and aid in row0:
            raise PanelCompileError(
                DESTRUCTIVE_PLACEMENT, f"{pid}.{aid}: destructive action may never sit in row 0")
        if action.defer_mode is DeferMode.MODAL and action.modal is None:
            raise PanelCompileError(
                MODAL_RULES, f"{pid}.{aid}: defer_mode=modal requires a ModalSpec (G-10)")
        if action.modal is not None:
            _check_modal(pid, aid, action.modal)
        if _SCHEME_TOKEN_RE.match(action.custom_id_override or ""):
            raise PanelCompileError(
                SCHEME_TOKEN_OVERRIDE,
                f"{pid}.{aid}: custom_id_override {action.custom_id_override!r} begins "
                f"with a scheme-version token (§3.4 — the id families must stay disjoint)")
        # irreversible workflow ⇒ confirm required (§2.6; checkable only once
        # the workflow is registered — unresolved refs are P2's failure, not ours).
        if isinstance(action.handler, WorkflowRef) and action.confirm is None:
            try:
                op = WORKFLOW_REGISTRY.resolve(action.handler)
            except LookupError:
                op = None   # unresolved refs are P2's failure surface, not this fence's
            if op is not None and getattr(op, "reversibility", None) == IRREVERSIBLE:
                raise PanelCompileError(
                    CONFIRM_REQUIRED,
                    f"{pid}.{aid}: handler {action.handler.name!r} is irreversible — "
                    f"a ConfirmationSpec is required")
    for selector in spec.selectors:
        if _SCHEME_TOKEN_RE.match(selector.custom_id_override or ""):
            raise PanelCompileError(
                SCHEME_TOKEN_OVERRIDE,
                f"{pid}.{selector.selector_id}: custom_id_override begins with a "
                f"scheme-version token (§3.4)")
