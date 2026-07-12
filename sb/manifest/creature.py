"""CREATURE subsystem manifest (band 6 / parity flip) — the shipped
creature-game v1 (Q-0187) command names verbatim: !creatures opens the
shipped 🐾 hub panel; !dex/!dextop/!cbrecord/!cbattletop open the four
shipped embed cards; !cbattle sends the Accept/Decline challenge
(goldens/creature/ + the re-homed sweep_dextop pin every byte). !catch
(alias hunt) is DECLARED though sweep-skipped in the imported corpus
('unseeded private RNG in creature spawn selection' —
parity/goldens/_sweep_skips.json): the skip is a capture-DETERMINISM
artifact, not a no-analog D-0030 class (the treasury-grant /
admin-restart precedent) — the golden-pinned hub Catch button routes
the same audited lane and the golden-pinned dex/dextop copy advertises
`!catch` verbatim. The battle RESOLUTION engine
(utils/creatures/battle.py combat math) is successor-slice work:
Accept is a declared pending terminal; the audited record lane
(creature.record_battle_result) is live, waiting."""

from __future__ import annotations

from sb.domain.creature import panels as _panels
from sb.domain.creature import service as _service
from sb.domain.creature.ops import register_ops
from sb.domain.creature.store import (
    CREATURE_BATTLE_STORE,
    CREATURE_COLLECTION_STORE,
)
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

MANIFEST = SubsystemManifest(
    key="creature",
    version=1,
    commands=(
        CommandSpec(name="catch", kind=CommandKind.PREFIX,
                    aliases=("hunt",),
                    route=HandlerRef("creature.catch_route"),
                    audience_tier="user", capability="creature",
                    summary="Hunt a wild creature — rarity-weighted "
                            "encounter, level-nudged catch roll.",
                    usage="!catch"),
        CommandSpec(name="creatures", kind=CommandKind.PREFIX,
                    aliases=("creaturemenu", "pets"),
                    route=PanelRef("creature.hub"),
                    audience_tier="user", capability="creature",
                    summary="Open the creatures menu.",
                    usage="!creatures"),
        CommandSpec(name="dex", kind=CommandKind.PREFIX,
                    aliases=("collection",),
                    route=HandlerRef("creature.dex_view"),
                    audience_tier="user", capability="creature",
                    summary="Your creature collection log.",
                    usage="!dex"),
        CommandSpec(name="dextop", kind=CommandKind.PREFIX,
                    aliases=("topcatchers",),
                    route=HandlerRef("creature.dextop_view"),
                    audience_tier="user", capability="creature",
                    summary="Top collectors by total creatures caught.",
                    usage="!dextop"),
        CommandSpec(name="cbattle", kind=CommandKind.PREFIX,
                    aliases=("creaturebattle",),
                    route=HandlerRef("creature.cbattle_route"),
                    audience_tier="user", capability="creature",
                    summary="Challenge another member to a "
                            "level-normalized creature PvP battle.",
                    usage="!cbattle @player"),
        CommandSpec(name="cbrecord", kind=CommandKind.PREFIX,
                    aliases=("battlerecord",),
                    route=HandlerRef("creature.battle_record_view"),
                    audience_tier="user", capability="creature",
                    summary="Your creature battle record.",
                    usage="!cbrecord"),
        CommandSpec(name="cbattletop", kind=CommandKind.PREFIX,
                    aliases=("pvptop", "battletop"),
                    route=HandlerRef("creature.battletop_view"),
                    audience_tier="user", capability="creature",
                    summary="The creature battle leaderboard.",
                    usage="!cbattletop"),
    ),
    panels=(
        _panels.creature_hub_spec(),
        _panels.dex_card_spec(),
        _panels.collectors_card_spec(),
        _panels.record_card_spec(),
        _panels.battletop_card_spec(),
        _panels.challenge_spec(),
        _panels.rules_card_spec(),
    ),
    settings=(),
    stores=(CREATURE_COLLECTION_STORE, CREATURE_BATTLE_STORE),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.creature import ops as _ops
    from sb.domain.creature import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    _panels.ensure_panel_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
