"""D1 — the themed card-render band (`sb/kernel/render/`).

A shared kernel-band substrate for image cards: a themed Pillow surface plus the
primitives every hero card needs (themed text, rounded panels, header band,
clamped progress bar, initials disc, real-avatar disc, PNG/JPEG export), a named
skin registry, and bundled fonts. The two domain card surfaces (`sb/domain/xp`
rank card, `sb/domain/utility` profile card) and future cards compose it in later
D1 slices — this Slice 1 lands the engine + fonts + dependency only, with **no
consumer yet**.

Layer map (a clean kernel leaf — imports stdlib + optional Pillow only; no
kernel→domain edge; nothing above spec imported):
  fonts.py   — bundled DejaVu resolution + load_font (lazy PIL)
  themes.py  — RGB + Theme + THEMES registry + get_theme (silent default fallback)
  engine.py  — CardCanvas primitives + new_canvas (None without Pillow) + pure helpers

Graceful degradation is the load-bearing contract: `new_canvas` returns `None`
when Pillow is unavailable, so a caller always keeps its text-embed fallback and
a card command never crashes on a Pillow-less host. The pure helpers (`initials`,
`image_safe`, `mix`) and the registry import without Pillow.
"""

from __future__ import annotations

from .engine import (
    CardCanvas,
    image_safe,
    initials,
    mix,
    new_canvas,
    pillow_available,
)
from .fonts import (
    BUNDLED_BOLD,
    BUNDLED_REGULAR,
    DEFAULT_BOLD_CANDIDATES,
    DEFAULT_REGULAR_CANDIDATES,
    dejavu_fonts,
    load_font,
)
from .themes import DEFAULT_THEME, RGB, THEMES, Theme, get_theme

__all__ = [
    # themes
    "RGB",
    "Theme",
    "THEMES",
    "DEFAULT_THEME",
    "get_theme",
    # fonts
    "BUNDLED_BOLD",
    "BUNDLED_REGULAR",
    "DEFAULT_BOLD_CANDIDATES",
    "DEFAULT_REGULAR_CANDIDATES",
    "load_font",
    "dejavu_fonts",
    # engine
    "CardCanvas",
    "new_canvas",
    "pillow_available",
    "initials",
    "image_safe",
    "mix",
]
