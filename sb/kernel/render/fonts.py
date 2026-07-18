"""Bundled-font resolution for the D1 render band.

The engine ships its own DejaVu TTF pair under ``fonts/`` (the redistributable
Bitstream-Vera-licensed faces; see ``fonts/LICENSE``) so a card renders
**host-independently** — never relying on a system font path that varies across
CI images. Resolution order per face is: the bundled TTF first, then the common
system DejaVu install path, then Pillow's built-in bitmap default
(:func:`load_font`'s final fallback). Dropping a branded ``.ttf`` in here and
naming it first in a :class:`~sb.kernel.render.themes.Theme` is the whole
"custom font per skin" story — a reversible config drop, not new code (D-0093
keeps the brand-font swap open as a future product-identity call).

Contract: **lazy PIL import** — nothing here imports Pillow at module load, so
this module imports cleanly on a Pillow-less host; :func:`load_font` imports
``ImageFont`` only when actually asked to load a face. Font availability is
environmental, so :func:`load_font` never raises: a stripped image with neither
the bundle nor a system DejaVu still renders, just with Pillow's bitmap default.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_FONT_DIR = Path(__file__).resolve().parent / "fonts"

#: The bundled DejaVu faces, resolved by package path (host-independent).
BUNDLED_BOLD = str(_FONT_DIR / "DejaVuSans-Bold.ttf")
BUNDLED_REGULAR = str(_FONT_DIR / "DejaVuSans.ttf")

#: A common system install path — an ordered fallback if the bundle is stripped.
_SYSTEM_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_SYSTEM_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

#: The default candidate tuples a Theme carries when it names no custom face:
#: bundle first, system path second, bitmap default (in load_font) last.
DEFAULT_BOLD_CANDIDATES: tuple[str, ...] = (BUNDLED_BOLD, _SYSTEM_BOLD)
DEFAULT_REGULAR_CANDIDATES: tuple[str, ...] = (BUNDLED_REGULAR, _SYSTEM_REGULAR)


@lru_cache(maxsize=128)
def _load_font_path(path: str, size: int):  # noqa: ANN202 — PIL lazy types
    """Cached truetype load for one ``(path, size)``; raises on a missing file."""
    from PIL import ImageFont  # lazy: optional at import time

    return ImageFont.truetype(path, size)


def load_font(candidates: tuple[str, ...], size: int):  # noqa: ANN201
    """First loadable font among *candidates* at *size*, else the bitmap default.

    Never raises: each candidate is tried in order; a load failure just falls
    through to the next path, and an exhausted list yields Pillow's built-in
    ``load_default()`` font so a card always renders *something*.
    """
    from PIL import ImageFont  # lazy

    for path in candidates:
        try:
            return _load_font_path(path, size)
        except Exception:  # noqa: BLE001, S112 — just try the next candidate
            continue
    return ImageFont.load_default()


def dejavu_fonts(size_big: int, size_small: int):  # noqa: ANN201
    """A ``(bold-big, regular-small)`` bundled-DejaVu pair — the legacy
    ``_fonts()`` shape every ad-hoc renderer used to redeclare privately.
    """
    return (
        load_font(DEFAULT_BOLD_CANDIDATES, size_big),
        load_font(DEFAULT_REGULAR_CANDIDATES, size_small),
    )


__all__ = [
    "BUNDLED_BOLD",
    "BUNDLED_REGULAR",
    "DEFAULT_BOLD_CANDIDATES",
    "DEFAULT_REGULAR_CANDIDATES",
    "load_font",
    "dejavu_fonts",
]
