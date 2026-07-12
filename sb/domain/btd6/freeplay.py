"""BTD6 freeplay MOAB scaling (band 7) — the focused port of the shipped
``services/btd6_data_service.py`` late-game/freeplay block: the
piecewise-linear MOAB-class health curve (``moab_class_health_multiplier``,
``bloon_health_at_round``) and the recursive spawn-tree RBE walk
(``bloon_rbe_at_round`` / ``_rbe_at_round``), plus the per-round helper
(``effective_round_rbe``) that ``round_rbe`` sums per spawn group.

This retires the ``oracle_cards.py`` deviation-ledger bullet "freeplay MOAB
scaling (effective RBE, rounds 81+) is not recomputed".

Oracle reconstruction (trap 24): fragments read via search_code at the
oracle default-branch head ``1ecc2113`` (capture/corpus pin stays
``7f7628e1``; the only goldens touching this surface pin PRE-scaling
round-3 bytes, so no capture-sha drift risk on pinned bytes). Sources:
``disbot/services/btd6_data_service.py`` (``HealthScalingBracket``,
``moab_class_health_multiplier``, ``bloon_health_at_round``,
``_rbe_at_round``, ``bloon_rbe_at_round``, ``_group_fortified``,
``_effective_round_rbe``) and ``disbot/data/btd6/bloon_scaling.json``
(byte-identical to the committed ``sb/domain/btd6/data/bloon_scaling.json``).
The walk is verified against the oracle's OWN anchors
(tests/unit/services/test_btd6_bloon_scaling.py + the 2026-06-23 session
card): v(100)=1.40, BAD r100 = 28,000 HP / 67,200 RBE (per-unit
MOAB 552 → BFB 3,188 → ZOMG 18,352, DDT 832), fortified BAD r140 =
200,000 HP, superceramic 68 (128 fortified).

Deviations, ledgered here (all on golden-UNPINNED paths):

* the oracle's ``RoundEntry``-typed round objects ride the D-0046
  validating parser — ``effective_round_rbe`` here takes the RAW round
  dict (``row["groups"]`` / ``row["round"]``) our ``read_blob`` pass
  serves, semantics identical;
* ``_bloon_base_rbe`` (consumed only by the oracle head's single-round
  ``breakdown`` key, a post-capture ``round_rbe`` addition our shipped
  contract never carried) is not ported;
* the head's ``roundset="alternate"``/ABR parameter on the freeplay
  surfaces is post-capture drift — our shipped default-set contract
  stands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sb.domain.btd6 import dataset

__all__ = [
    "HealthScalingBracket",
    "bloon_health_at_round",
    "bloon_rbe_at_round",
    "effective_round_rbe",
    "moab_class_health_multiplier",
]


@dataclass(frozen=True)
class HealthScalingBracket:
    """One piece of the MOAB-class late-game/freeplay health-multiplier
    curve (oracle ``HealthScalingBracket``, verbatim fields).

    ``multiplier(r) = base + (r - anchor_round) * per_round`` for any round
    ``r`` in ``[min_round, max_round]``. BTD6 ramps MOAB-class HP from
    round 81 (+2% of base/round); ``v(100) = 1.40`` so a BAD first spawns
    on round 100 at 28,000 HP."""

    min_round: int
    max_round: int
    anchor_round: int
    base: float
    per_round: float


@dataclass(frozen=True)
class FreeplayScaling:
    """The ``bloon_scaling.json`` fixture, parsed — mirrors the oracle
    dataset fields the freeplay walk reads (empty/0 when absent)."""

    # Round-relative MOAB-class health scaling: a shared curve keyed by
    # round, not a per-BloonEntry field. Empty when the fixture is absent.
    moab_health_scaling: tuple[HealthScalingBracket, ...] = ()
    moab_health_start_round: int = 0
    # Freeplay superceramic RBE (bloon_scaling.json ``freeplay``): from
    # round 81 every Ceramic is replaced by a Super Ceramic; used by the
    # spawn-tree walk to recompute MOAB-class trees. 0 when absent.
    freeplay_superceramic_rbe: int = 0
    freeplay_superceramic_rbe_fortified: int = 0


def _parse_health_bracket(raw: dict[str, Any]) -> HealthScalingBracket:
    return HealthScalingBracket(
        min_round=int(raw["min_round"]),
        max_round=int(raw["max_round"]),
        anchor_round=int(raw["anchor_round"]),
        base=float(raw["base"]),
        per_round=float(raw["per_round"]),
    )


def get_scaling() -> FreeplayScaling:
    """Parse (blob-cached via ``dataset.read_blob``) the committed
    ``bloon_scaling.json`` into the fields the walk consumes."""
    raw = dataset.read_blob("bloon_scaling.json")
    moab_health_block = (
        raw.get("moab_class_health", {}) or {} if raw is not None else {}
    )
    freeplay_block = raw.get("freeplay", {}) or {} if raw is not None else {}
    return FreeplayScaling(
        moab_health_scaling=tuple(
            _parse_health_bracket(b)
            for b in moab_health_block.get("brackets", [])
        ),
        moab_health_start_round=int(
            moab_health_block.get("start_round", 0) or 0
        ),
        freeplay_superceramic_rbe=int(
            freeplay_block.get("superceramic_rbe", 0) or 0
        ),
        freeplay_superceramic_rbe_fortified=int(
            freeplay_block.get("superceramic_rbe_fortified", 0) or 0
        ),
    )


def moab_class_health_multiplier(round_number: int) -> float | None:
    """The late-game/freeplay health multiplier applied to MOAB-class
    bloons on ``round_number``, or ``None`` when the
    ``bloon_scaling.json`` fixture is absent (oracle body verbatim).

    Regular (non-MOAB-class) bloons do not take this multiplier. Rounds
    below the first bracket are unscaled (``1.0``); rounds past the last
    clamp to its end."""
    brackets = get_scaling().moab_health_scaling
    if not brackets:
        return None
    for bracket in brackets:
        if bracket.min_round <= round_number <= bracket.max_round:
            value = (
                bracket.base
                + (round_number - bracket.anchor_round) * bracket.per_round
            )
            return round(value, 4)
    if round_number < brackets[0].min_round:
        return 1.0
    last = brackets[-1]
    return round(
        last.base + (last.max_round - last.anchor_round) * last.per_round, 4
    )


def bloon_health_at_round(
    bloon_id: str,
    round_number: int,
    *,
    fortified: bool = False,
) -> int | None:
    """A bloon's health on ``round_number`` — the stored base for regular
    bloons, the freeplay curve applied for MOAB-class (oracle body
    verbatim; ``None`` for unknown bloons or missing health)."""
    bloon = dataset.get_bloon(bloon_id)
    if bloon is None:
        return None
    base = bloon.health_fortified if fortified else bloon.health
    if not isinstance(base, int):
        return None
    if bloon.category != "moab_class":
        return base
    multiplier = moab_class_health_multiplier(round_number)
    if multiplier is None:
        return base
    return int(round(base * multiplier))


def _rbe_at_round(
    bloon_id: str,
    round_number: int,
    fortified: bool,
    multiplier: float | None,
    start: int,
    scaling: FreeplayScaling,
) -> int | None:
    """The recursive spawn-tree walk (oracle ``_rbe_at_round`` verbatim;
    the oracle passes its ``BTD6DataSet`` here — ours is the parsed
    ``FreeplayScaling``, same fields read). Bottoms out at Ceramic
    (→ Super Ceramic) and at any non-MOAB-class bloon (stored base RBE),
    so a MOAB-class tree always terminates."""
    bloon = dataset.get_bloon(bloon_id)
    if bloon is None:
        return None
    # No freeplay band (no fixture, or round ≤ 80) → the stored base RBE is exact.
    if multiplier is None or round_number < start:
        base_rbe = bloon.rbe_fortified if fortified else bloon.rbe
        return base_rbe if isinstance(base_rbe, int) else None
    # Ceramic → the freeplay Super Ceramic (the MOAB-class tree bottoms out here).
    if bloon.id == "ceramic":
        superc = (
            scaling.freeplay_superceramic_rbe_fortified
            if fortified
            else scaling.freeplay_superceramic_rbe
        )
        return superc or None
    # Any other non-MOAB-class bloon does not take the ramp → stored base RBE.
    if bloon.category != "moab_class":
        base_rbe = bloon.rbe_fortified if fortified else bloon.rbe
        return base_rbe if isinstance(base_rbe, int) else None
    base_health = bloon.health_fortified if fortified else bloon.health
    if not isinstance(base_health, int):
        return None
    total = int(round(base_health * multiplier))
    for child in bloon.children_list:
        cid = str(child.get("bloon_id", ""))
        count = int(child.get("count", 0))
        child_fort = fortified or "fortified" in (child.get("modifiers", ()) or ())
        child_rbe = _rbe_at_round(
            cid,
            round_number,
            child_fort,
            multiplier,
            start,
            scaling,
        )
        if child_rbe is None:
            return None
        total += count * child_rbe
    return total


def bloon_rbe_at_round(
    bloon_id: str,
    round_number: int,
    *,
    fortified: bool = False,
) -> int | None:
    """A bloon's freeplay-effective RBE on ``round_number``: its spawn
    tree recomputed with every MOAB-class layer's health ×
    :func:`moab_class_health_multiplier` and every ceramic leaf swapped
    to the Super Ceramic (oracle wrapper verbatim). Identical to the
    stored base RBE through round 80."""
    scaling = get_scaling()
    multiplier = moab_class_health_multiplier(round_number)
    start = scaling.moab_health_start_round or 81
    return _rbe_at_round(
        bloon_id, round_number, fortified, multiplier, start, scaling
    )


def _group_fortified(group: dict[str, Any]) -> bool:
    """Whether a round spawn group carries the ``fortified`` modifier."""
    mods = group.get("modifiers") or ()
    return any(str(m).lower() == "fortified" for m in mods)


def effective_round_rbe(row: dict[str, Any]) -> int | None:
    """A round's freeplay-scaled RBE: each group's count × the per-bloon
    scaled RBE at this round (:func:`bloon_rbe_at_round`). ``None`` if any
    group's bloon RBE is unknown (so the caller shows only the base
    figure, never a partial sum passed off as the whole). Identical to the
    stored ``rbe`` through round 80 — the sum reconstructs the stored base
    RBE exactly when no scaling applies, which is what makes the 81+
    divergence purely the freeplay rules. (Oracle ``_effective_round_rbe``
    verbatim, over the raw round dict our ``read_blob`` pass serves.)"""
    groups = row.get("groups") or ()
    if not groups:
        return None
    total = 0
    for group in groups:
        per = bloon_rbe_at_round(
            str(group.get("bloon_id")),
            int(row.get("round", -1)),
            fortified=_group_fortified(group),
        )
        if per is None:
            return None
        total += int(group.get("count", 0)) * per
    return total
