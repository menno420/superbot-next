"""FARM subsystem manifest (band 6, checkpoint family) — the shipped
!farm (chickenfarm/coop) idle game: pure accrual core verbatim, the
three audited K7 money lanes, the chicken_farm store."""

from __future__ import annotations

from sb.domain.farm import panels as _panels
from sb.domain.farm.ops import register_ops
from sb.domain.farm.store import CHICKEN_FARM_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="farm",
    version=1,
    commands=(
        CommandSpec(name="farm", kind=CommandKind.PREFIX,
                    aliases=("chickenfarm", "coop"),
                    route=PanelRef("farm.hub"),
                    audience_tier="user", capability="farm",
                    summary="Open your idle chicken farm — collect eggs, "
                            "buy hens, upgrade the coop.",
                    usage="!farm"),
    ),
    panels=(_panels.farm_hub_spec(),),
    settings=(),
    stores=(CHICKEN_FARM_STORE,),
    events=(),   # emits economy.balance_changed + game_xp.* (owners: economy/games)
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.farm import ops as _ops
    from sb.domain.farm import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
