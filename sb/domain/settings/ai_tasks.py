"""Band-1 legacy AI task-id claims + the manifest-generated capabilities
overview (the K10 band map: settings claims `settings.explain` /
`settings.propose` BYTE-IDENTICAL from tasks.LEGACY_TASK_IDS, and registers
the register_task_contract("") capabilities overview GENERATED FROM THE
MANIFEST — never hand-listed features)."""

from __future__ import annotations

from sb.kernel.ai import instructions, tasks

__all__ = ["capabilities_overview", "register_ai_tasks"]


def capabilities_overview() -> str:
    """The generated capabilities overview: walks every sb.manifest
    declaration (commands + summaries). Regenerates per call — the manifest
    is the single source; a hand-edited feature list can never drift."""
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg

    lines: list[str] = ["Server capabilities (generated from the manifest):"]
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda i: i.name):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        for manifest in ([getattr(module, "MANIFEST", None)]
                         + list(getattr(module, "MANIFESTS", ()) or ())):
            if manifest is None:
                continue
            for cmd in getattr(manifest, "commands", ()) or ():
                name = getattr(cmd, "name", "")
                summary = getattr(cmd, "summary", "")
                if name:
                    lines.append(f"- /{name}: {summary or '(no summary)'}")
    return "\n".join(lines)


def register_ai_tasks() -> None:
    """Idempotent (register_task tolerates identical re-registration)."""
    assert "settings.explain" in tasks.LEGACY_TASK_IDS
    assert "settings.propose" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="settings.explain",
        owner_subsystem="settings",
        description="Explain a guild setting: what it does, its current "
                    "resolved value and provenance.",
        realtime=True,
    ))
    tasks.register_task(tasks.AITaskSpec(
        task_id="settings.propose",
        owner_subsystem="settings",
        description="Propose a settings change as a previewed draft — "
                    "never a direct write.",
        realtime=True,
    ))
    # '' = every task; the text is generated from the manifest at
    # registration time (boot) — re-registration after a manifest change
    # appends the fresh generation (idempotent per (task, owner, text)).
    instructions.register_task_contract(
        "", owner_subsystem="settings", text=capabilities_overview())
