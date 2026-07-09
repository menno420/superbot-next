"""Multi-server governance templates (band 5) — governance/templates.py
(ISSUE-034) headless. apply_template routes EVERY override through the K7
lanes (INV-003: per-entry authority validation, transactional DB+audit,
per-entry events — N entries = N audit rows; failures raise without
rolling back earlier writes, shipped semantics).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sb.domain.governance import store

logger = logging.getLogger("sb.domain.governance.templates")

__all__ = [
    "GovernanceTemplate",
    "apply_template",
    "export_template",
    "load_template",
    "save_template",
]


@dataclass
class GovernanceTemplate:
    """Serializable governance configuration snapshot for one guild."""

    name: str = ""
    description: str = ""
    visibility_overrides: list[dict] = field(default_factory=list)
    cleanup_overrides: list[dict] = field(default_factory=list)
    source_guild_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "source_guild_id": self.source_guild_id,
            "visibility_overrides": self.visibility_overrides,
            "cleanup_overrides": self.cleanup_overrides,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GovernanceTemplate:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            visibility_overrides=data.get("visibility_overrides", []),
            cleanup_overrides=data.get("cleanup_overrides", []),
            source_guild_id=data.get("source_guild_id"),
        )


async def export_template(guild_id: int, name: str = "",
                          description: str = "") -> GovernanceTemplate:
    """Export the current governance overrides for a guild as a template."""
    vis_rows = await store.get_all_visibility_for_guild(guild_id)
    cleanup_rows = await store.get_all_cleanup_for_guild(guild_id)
    template = GovernanceTemplate(
        name=name or f"Guild {guild_id} export",
        description=description,
        visibility_overrides=[
            {"scope_type": r["scope_type"], "scope_id": r["scope_id"],
             "subsystem": r["subsystem"], "enabled": r["enabled"]}
            for r in vis_rows],
        cleanup_overrides=[
            {"scope_type": r["scope_type"], "scope_id": r["scope_id"],
             "delete_invalid_commands": r["delete_invalid_commands"],
             "delete_failed_commands": r.get("delete_failed_commands", True),
             "delete_after_seconds": r["delete_after_seconds"]}
            for r in cleanup_rows],
        source_guild_id=guild_id,
    )
    logger.info("Exported governance template from guild=%d: %d vis, "
                "%d cleanup overrides", guild_id,
                len(template.visibility_overrides),
                len(template.cleanup_overrides))
    return template


async def apply_template(ctx, template: GovernanceTemplate) -> int:
    """Apply a template via the K7 lanes — one audited mutation per entry
    (INV-003). ``ctx`` is a WorkflowContext factory-fresh per call; params
    are re-set per entry."""
    from sb.domain.governance import service

    count = 0
    for override in template.visibility_overrides:
        await service.set_subsystem_visibility(
            ctx, scope_type=override["scope_type"],
            scope_id=override["scope_id"], subsystem=override["subsystem"],
            enabled=override["enabled"])
        count += 1
    for policy in template.cleanup_overrides:
        await service.set_cleanup_policy_for_scope(
            ctx, scope_type=policy["scope_type"],
            scope_id=policy["scope_id"],
            delete_invalid_commands=policy.get("delete_invalid_commands", True),
            delete_failed_commands=policy.get("delete_failed_commands", True),
            delete_after_seconds=policy.get("delete_after_seconds", 5))
        count += 1
    logger.info("Applied governance template %r to guild=%s: %d overrides "
                "via the K7 lanes", template.name, ctx.guild_id, count)
    return count


async def save_template(template: GovernanceTemplate, *,
                        created_by_guild_id: int | None = None) -> int:
    """Persist a template. Returns the new template_id."""
    from sb.kernel.db.pool import transaction

    async with transaction() as conn:
        return await store.insert_template(
            conn, name=template.name, description=template.description,
            created_by_guild_id=created_by_guild_id,
            payload=template.to_dict())


async def load_template(template_id: int) -> GovernanceTemplate | None:
    row = await store.load_template_row(template_id)
    if row is None:
        return None
    payload = row["payload"]
    data = json.loads(payload) if isinstance(payload, str) else payload
    return GovernanceTemplate.from_dict(data)
