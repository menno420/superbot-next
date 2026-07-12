"""Mining world bands — the shipped ``utils/mining/world.py`` verbatim:
the depth↔biome display half (biome labels/emoji + ``describe_position``)
AND the pure descent-gating half (slice 2 — descend/ascend traversal).

Descent-gating decision (oracle brainstorm §6.8 P2): depth access is
gated by the already-shipped ``depth_access`` stat from equipped gear (a
torch grants access to depth 1 / Cavern, a lantern depth 2 / Deep) and is
persistent, not consumed per descent. A fresh gearless player reads
all-zero stats, so ``!descend`` refuses at the Surface — the byte
goldens/mining/sweep_descend pins. The x/y lateral grid seams
(pos_x/pos_y + fog of war) still ride the D-0043 grid-dig port (`!mine`).

The display half stays what the LIVE core loop renders:
goldens/mining/sweep_fastmine + sweep_explore + sweep_minemenu pin the
depth-0 byte ("🌳 Surface (depth 0/3)")."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sb.domain.mining.equipment import EffectiveStats

__all__ = [
    "BIOME_BANDS",
    "MAX_DEPTH",
    "clamp_depth",
    "describe_position",
    "max_accessible_depth",
    "can_descend",
    "can_ascend",
    "descend",
    "ascend",
    "descend_hint",
]

#: (emoji, label) per depth band — shipped BIOME_EMOJI + BIOME_LABELS
#: (disbot/utils/mining/world.py), verbatim.
BIOME_BANDS: tuple[tuple[str, str], ...] = (
    ("🌳", "Surface"),
    ("🪨", "Cavern"),
    ("💎", "the Deep"),
    ("🌋", "the Magma core"),
)

MAX_DEPTH = len(BIOME_BANDS) - 1  # 3 — shipped MAX_DEPTH


def clamp_depth(depth: int) -> int:
    return max(0, min(int(depth), MAX_DEPTH))


def describe_position(depth: int) -> str:
    """Human-readable ``"<emoji> <Label> (depth N/MAX)"`` — shipped
    ``describe_position`` verbatim."""
    emoji, label = BIOME_BANDS[clamp_depth(depth)]
    return f"{emoji} {label} (depth {clamp_depth(depth)}/{MAX_DEPTH})"


def max_accessible_depth(stats: EffectiveStats) -> int:
    """The deepest band *stats* (from equipped gear) unlocks — shipped
    ``max_accessible_depth`` verbatim.

    Surface (0) is always reachable; each point of light-driven
    ``depth_access`` unlocks one deeper band (torch → 1/Cavern, lantern →
    2/Deep). Clamped to the world's deepest band."""
    return clamp_depth(stats.depth_access)


def can_descend(depth: int, stats: EffectiveStats) -> bool:
    """True when the player can go one band deeper given their gear."""
    return depth < max_accessible_depth(stats)


def can_ascend(depth: int) -> bool:
    """True when the player is below the surface and can climb one band."""
    return depth > 0


def descend(depth: int, stats: EffectiveStats) -> int:
    """New depth after a descend attempt — unchanged if gear can't reach
    deeper. Shipped ``descend`` verbatim."""
    return (clamp_depth(depth + 1) if can_descend(depth, stats)
            else clamp_depth(depth))


def ascend(depth: int) -> int:
    """New depth after climbing one band — never above the surface.
    Shipped ``ascend`` verbatim."""
    return clamp_depth(depth - 1) if can_ascend(depth) else 0


def descend_hint(stats: EffectiveStats) -> str:
    """Why a descend is blocked / what unlocks the next band — shipped
    ``descend_hint`` verbatim (goldens/mining/sweep_descend pins the
    all-zero-stats byte: "Equip a brighter light to descend to Cavern
    (needs depth access 1).")."""
    reach = max_accessible_depth(stats)
    if reach >= MAX_DEPTH:
        return "You have the gear to reach the deepest bands."
    next_label = BIOME_BANDS[reach + 1][1]
    return (
        f"Equip a brighter light to descend to {next_label} "
        f"(needs depth access {reach + 1})."
    )
