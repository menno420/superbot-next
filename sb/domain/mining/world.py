"""Mining world bands — the shipped ``utils/mining/world.py`` display
slice, verbatim (biome labels/emoji + ``describe_position``).

The full world module (descent gating off equipped ``depth_access``,
band clamping for ascend/descend, the x/y grid seams) rides the D-0043
deep-system successor port — this slice carries only what the LIVE core
loop renders: goldens/mining/sweep_fastmine + sweep_explore +
sweep_minemenu pin the depth-0 byte ("🌳 Surface (depth 0/3)")."""

from __future__ import annotations

__all__ = ["BIOME_BANDS", "MAX_DEPTH", "describe_position"]

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
