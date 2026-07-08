"""Band-1 help subsystem: projection-from-manifests, panel, task claim."""

from __future__ import annotations


def test_command_inventory_is_generated_from_manifests():
    from sb.domain.help.service import command_inventory

    inventory = command_inventory()
    assert "settings" in inventory and "help" in inventory and "diagnostic" in inventory
    names = dict(inventory["help"])
    assert "help" in names


def test_help_panel_projects_inventory_and_registers():
    from sb.domain.help.service import build_help_panel, install_help

    spec = build_help_panel()
    assert spec.panel_id == "help.home" and spec.subsystem == "help"
    assert spec.navigation.show_help is False   # the help hub IS home
    assert install_help().panel_id == "help.home"


def test_help_answer_claimed_verbatim():
    from sb.domain.help.ai_tasks import register_ai_tasks
    from sb.kernel.ai import tasks

    register_ai_tasks()
    register_ai_tasks()
    assert tasks.get_task("help.answer").owner_subsystem == "help"


def test_help_manifest_compiles_in_isolation():
    import sb.manifest.help as m
    from tools.manifest_compile import compile_manifests

    m.ENSURE_REFS()
    result = compile_manifests(manifests=[m.MANIFEST])
    assert result.ok, [str(v) for v in result.violations]
