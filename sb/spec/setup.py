"""WizardSectionSpec — the G-19 wizard-section facet, frozen at band 1
(canonical plan A-9(2): "freeze G-19 at the Gate-0 registry and widen its
consumers to all 10 live views/setup/sections registrants").

The shipped record (disbot services/setup_sections.py `SetupSection`) is
carried DECLARATIVE-FIELDS-VERBATIM: slug / label / emoji / order / step /
op_kinds, plus the caps the shipped registry enforced (slug<=64
lowercase/digits/underscore, label<=80 — Discord's Button.label limit).
The one non-declarative shipped field, the `run` async callback, becomes a
registered ROUTE (PanelRef | WorkflowRef | HandlerRef | None) — the §2.0
callable→registered-ref rule; the hub's kernel-generated callback resolves
authority before any section route runs (A-9's row-5a KEEP verdicts carry
here, not on a side clause).

`SubsystemManifest.wizard_sections` is the facet home (the G-19 note),
duck-typed by the compiler like every facet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sb.spec.roles import register_field_roles

__all__ = ["WizardSectionSpec", "check_wizard_section"]

_SLUG_MAX_LEN = 64
_LABEL_MAX_LEN = 80
_SLUG_RE = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class WizardSectionSpec:
    slug: str                                   # [S] registry key; custom_id suffix; session step marker
    label: str                                  # [S] semantic copy (Discord Button.label cap)
    route: object = None                        # [S] PanelRef | WorkflowRef | HandlerRef | None
    emoji: str = ""                             # [S]
    order: int = 0                              # [A] hub sort key (shipped: multiples of 10)
    step: str = ""                              # [S] session current_step override ("" => slug)
    op_kinds: tuple[str, ...] = ()              # [S] draft op kinds this section stages
    #     (empty = read-only section; setup_progress groups draft rows by these)
    style: str = "secondary"                    # [S] button style token

    @property
    def step_marker(self) -> str:
        return self.step or self.slug


def check_wizard_section(spec: WizardSectionSpec) -> list[str]:
    """The shipped registry validation, as a fence."""
    problems: list[str] = []
    if not spec.slug or len(spec.slug) > _SLUG_MAX_LEN or not _SLUG_RE.match(spec.slug):
        problems.append(
            f"wizard section slug {spec.slug!r}: lowercase/digits/underscore, "
            f"1..{_SLUG_MAX_LEN} chars")
    if not spec.label or len(spec.label) > _LABEL_MAX_LEN:
        problems.append(
            f"wizard section {spec.slug!r}: label 1..{_LABEL_MAX_LEN} chars "
            f"(Discord Button.label cap)")
    return problems


register_field_roles(
    "WizardSectionSpec",
    slug="S", label="S", route="S", emoji="S", order="A", step="S",
    op_kinds="S", style="S",
)
