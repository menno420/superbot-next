"""TREASURY subsystem manifest (band 3) — the shipped `!treasury` group
verbatim (aliases bank/pool; contribute: donate/deposit; grant:
disburse/payout), the contribute/disburse K7 lanes over ONE txn with the
economy ledger's treasury:* money trail, the guild_treasury store
(NAME_STABLE, bears_value ⇒ reverse-importable), and the pool⊄ledger
reconciliation invariant."""

from __future__ import annotations

from sb.domain.treasury import panels as _panels
from sb.domain.treasury.invariants import declare_treasury_invariants
from sb.domain.treasury.ops import register_ops
from sb.domain.treasury.store import GUILD_TREASURY_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef, WorkflowRef

MANIFEST = SubsystemManifest(
    key="treasury",
    version=1,
    commands=(
        CommandSpec(name="treasury", kind=CommandKind.PREFIX,
                    route=PanelRef("treasury.hub"), aliases=("bank", "pool"),
                    audience_tier="user", capability="treasury",
                    summary="Open the server treasury — view the pool and "
                            "contribute coins.",
                    usage="!treasury"),
        CommandSpec(name="contribute", kind=CommandKind.PREFIX,
                    group="treasury", aliases=("donate", "deposit"),
                    route=WorkflowRef("treasury.contribute"),
                    audience_tier="user", capability="treasury",
                    summary="Donate your own coins into the server "
                            "treasury.",
                    usage="!treasury contribute <amount>"),
        CommandSpec(name="grant", kind=CommandKind.PREFIX,
                    group="treasury", aliases=("disburse", "payout"),
                    route=WorkflowRef("treasury.disburse"),
                    audience_tier="staff",   # shipped manage_guild tier
                    capability="treasury",
                    summary="Disburse coins from the treasury to a member "
                            "(managers only).",
                    usage="!treasury grant @member <amount>"),
    ),
    panels=(_panels.treasury_hub_spec(),),
    settings=(),
    stores=(GUILD_TREASURY_STORE,),
    events=(),                        # emits economy.balance_changed (owner: economy)
    capabilities=(),
    data_invariants=(declare_treasury_invariants(),),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.treasury import invariants as _inv
    from sb.domain.treasury import ops as _ops
    from sb.domain.treasury import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _inv.ensure_invariant_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
