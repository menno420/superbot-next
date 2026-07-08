"""INVENTORY subsystem manifest (band 3) — the shipped `!inventory` (inv)
unified browser, projection-first over the coupled item namespace. No
stores of its own: the economy `inventory` table is band-3 slice 1's store
(sole writer economy.store); the shipped mining_inventory merge waits on
the band-6 extra-source port (sb/domain/inventory/service.py)."""

from __future__ import annotations

from sb.domain.inventory import handlers as _handlers
from sb.domain.inventory import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="inventory",
    version=1,
    commands=(
        CommandSpec(name="inventory", kind=CommandKind.PREFIX,
                    route=HandlerRef("inventory.view"), aliases=("inv",),
                    audience_tier="user", capability="inventory",
                    summary="Show your (or another user's) unified "
                            "inventory hub.",
                    usage="!inventory [@user]"),
    ),
    panels=(_panels.inventory_hub_spec(),),
    settings=(), stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
