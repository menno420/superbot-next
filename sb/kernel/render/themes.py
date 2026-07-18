"""The named skin registry for the D1 render band.

A :class:`Theme` is a frozen palette + font-candidate value object; :data:`THEMES`
is the named registry so a new skin ("ember", "verdant", …) is **config, not
code** — the Dank-Memer "new season = art drop" property, in code. :func:`get_theme`
resolves by name with a **silent default fallback** so a bad theme key can never
take a card down; it just renders in the default skin.

Slice 1 ships the single default ``midnight`` skin (D1 § non-goals: "one default
``midnight`` skin lands first; more skins are config drops later"). Additional
skins and per-provider theming are later config drops — a registry with one entry
still exercises the whole mechanism (and the skin-typo guard).
"""

from __future__ import annotations

from dataclasses import dataclass

from .fonts import DEFAULT_BOLD_CANDIDATES, DEFAULT_REGULAR_CANDIDATES

#: An RGB colour triple (Pillow-native).
RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    """A card skin: palette + ordered font candidates.

    Frozen so it is hashable and safe to cache renders against. Colours are RGB
    tuples. ``font_bold`` / ``font_regular`` are ordered candidate paths — the
    first that loads wins, else the bitmap default. A new look is a new
    :class:`Theme` registered in :data:`THEMES`; the layout code never changes.
    """

    name: str
    bg: RGB
    panel: RGB
    accent: RGB
    accent_alt: RGB
    text: RGB
    subtle: RGB
    gold: RGB
    outline: RGB
    font_bold: tuple[str, ...] = DEFAULT_BOLD_CANDIDATES
    font_regular: tuple[str, ...] = DEFAULT_REGULAR_CANDIDATES


#: The named skin registry. ``midnight`` mirrors the oracle's dark-blurple
#: palette, so a card ported onto this engine looks identical to the shipped
#: look. Further skins are a few RGB tuples each — added as a later slice.
THEMES: dict[str, Theme] = {
    "midnight": Theme(
        name="midnight",
        bg=(24, 25, 31),
        panel=(32, 34, 42),
        accent=(88, 101, 242),  # blurple
        accent_alt=(120, 200, 255),
        text=(235, 236, 240),
        subtle=(148, 155, 164),
        gold=(240, 178, 50),
        outline=(16, 17, 21),
    ),
}

#: The skin used when a theme name is unknown or ``None``.
DEFAULT_THEME = "midnight"


def get_theme(name: str | None) -> Theme:
    """Resolve a theme by name, falling back to :data:`DEFAULT_THEME`.

    Never raises on an unknown name — a bad theme key must never take a card
    down; it just renders in the default skin. (The corollary risk — a *typo* in
    a declared skin name rendering the wrong theme silently — is what the
    render-band skin-typo guard pins.)
    """
    if name is None:
        return THEMES[DEFAULT_THEME]
    return THEMES.get(name, THEMES[DEFAULT_THEME])


__all__ = ["RGB", "Theme", "THEMES", "DEFAULT_THEME", "get_theme"]
