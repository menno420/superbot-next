"""Band-1 setup skeleton: G-19 spec fences, the registry, the 10 verbatim
registrants, hub panel, task claims, manifest compile."""

from __future__ import annotations

import pytest

from sb.domain.setup.sections import REGISTRY, SECTIONS, register_shipped_sections
from sb.spec.setup import WizardSectionSpec, check_wizard_section


def test_g19_fences():
    assert check_wizard_section(WizardSectionSpec(slug="ok_1", label="Fine")) == []
    assert check_wizard_section(WizardSectionSpec(slug="Bad-Slug", label="x"))
    assert check_wizard_section(WizardSectionSpec(slug="ok", label="y" * 81))


def test_all_ten_shipped_registrants_verbatim():
    register_shipped_sections()   # idempotent
    ordered = REGISTRY.ordered()
    assert [s.slug for s in ordered] == [
        "preset_select", "channels", "logging_presets", "roles",
        "role_templates", "cleanup", "moderation", "cog_routing",
        "ticket", "final_review",
    ]
    assert REGISTRY.get("channels").op_kinds == ("bind_channel", "clear_binding")
    assert REGISTRY.get("roles").label == "Auto roles (time & XP)"
    assert REGISTRY.get("final_review").order == 90
    assert len(SECTIONS) == 10


def test_registry_refuses_differing_dup():
    with pytest.raises(ValueError, match="already registered"):
        REGISTRY.register(WizardSectionSpec(slug="channels", label="Other"))


def test_setup_panel_and_manifest():
    import sb.manifest.setup as m
    from sb.domain.setup.panels import install_setup_panels
    from tools.manifest_compile import compile_manifests

    assert install_setup_panels().panel_id == "setup.hub"
    m.ENSURE_REFS()
    result = compile_manifests(manifests=[m.MANIFEST])
    assert result.ok, [str(v) for v in result.violations]
    assert len(m.MANIFEST.wizard_sections) == 10


def test_setup_task_claims():
    from sb.domain.setup.ai_tasks import register_ai_tasks
    from sb.kernel.ai import tasks

    register_ai_tasks()
    register_ai_tasks()
    assert tasks.get_task("setup.suggest").owner_subsystem == "setup"
    assert tasks.get_task("setup.explain").owner_subsystem == "setup"
