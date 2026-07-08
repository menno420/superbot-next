"""The wizard-section registry + the 10 shipped registrants (band 1).

Verbatim data source: disbot/views/setup/sections/*.py @7f7628e1 (slug,
label, emoji, order, op_kinds). Routes are None until each section's flow
ports (see package docstring)."""

from __future__ import annotations

from sb.spec.setup import WizardSectionSpec, check_wizard_section

__all__ = ["SECTIONS", "SectionRegistry", "REGISTRY", "register_shipped_sections"]


class SectionRegistry:
    """Ported shipped semantics: validate at register, refuse dup slugs,
    order by the `order` field (never import order)."""

    def __init__(self) -> None:
        self._sections: dict[str, WizardSectionSpec] = {}

    def register(self, spec: WizardSectionSpec) -> WizardSectionSpec:
        problems = check_wizard_section(spec)
        if problems:
            raise ValueError("; ".join(problems))
        prior = self._sections.get(spec.slug)
        if prior is not None and prior != spec:
            raise ValueError(f"WizardSectionSpec slug {spec.slug!r} already registered")
        self._sections[spec.slug] = spec
        return spec

    def ordered(self) -> tuple[WizardSectionSpec, ...]:
        return tuple(sorted(self._sections.values(),
                            key=lambda s: (s.order, s.slug)))

    def get(self, slug: str) -> WizardSectionSpec | None:
        return self._sections.get(slug)

    def clear_for_tests(self) -> None:
        self._sections.clear()


REGISTRY = SectionRegistry()

#: the 10 live registrants, shipped values verbatim (A-9(2) widened set)
SECTIONS: tuple[WizardSectionSpec, ...] = (
    WizardSectionSpec(slug="preset_select", label="Load preset",
                      emoji="🎛", order=25),
    WizardSectionSpec(slug="channels", label="Channels & log routing",
                      emoji="📡", order=40,
                      op_kinds=("bind_channel", "clear_binding")),
    WizardSectionSpec(slug="logging_presets", label="Logging presets",
                      emoji="📜", order=45),
    WizardSectionSpec(slug="roles", label="Auto roles (time & XP)",
                      emoji="🎖️", order=55,
                      op_kinds=("set_role_threshold",)),
    WizardSectionSpec(slug="role_templates", label="Role templates",
                      emoji="🧩", order=56,
                      op_kinds=("create_managed_role",)),
    WizardSectionSpec(slug="cleanup", label="Cleanup inheritance",
                      emoji="🧹", order=60,
                      op_kinds=("set_cleanup_policy",)),
    WizardSectionSpec(slug="moderation", label="Moderation",
                      emoji="🛡️", order=65),
    WizardSectionSpec(slug="cog_routing", label="Cog routing",
                      emoji="🧭", order=70,
                      op_kinds=("set_cog_routing",)),
    WizardSectionSpec(slug="ticket", label="Support Tickets",
                      emoji="🎫", order=72),
    WizardSectionSpec(slug="final_review", label="Final review",
                      order=90),
)


def register_shipped_sections() -> None:
    """Idempotent (identical re-registration is a no-op)."""
    for spec in SECTIONS:
        REGISTRY.register(spec)


register_shipped_sections()
