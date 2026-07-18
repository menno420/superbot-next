"""The card-render engine — a themed Pillow surface + the card primitives.

The shared substrate every image card draws through: themed text with width-fit
truncation, rounded panels, a header band, a clamped progress bar, a no-network
initials disc, a real circular-cropped avatar disc, and PNG/JPEG export. A
renderer written against :class:`CardCanvas` is automatically re-skinnable — pass
a different :class:`~sb.kernel.render.themes.Theme` and the same draw calls
produce a different look.

Contract (the load-bearing degradation story): **lazy PIL import**. :func:`new_canvas`
returns ``None`` when Pillow is unavailable, so a caller always keeps its
text-embed fallback and a card command never crashes on a Pillow-less host. The
pure layout helpers (:func:`initials`, :func:`image_safe`, :func:`mix`) touch no
pixels and import without Pillow.

Layering: this is a kernel band leaf — it imports stdlib + its sibling band
modules + optional Pillow only. It imports nothing from ``sb.domain`` /
``sb.adapters`` (no kernel→domain edge) and has no consumer yet; the two card
surfaces compose it in later D1 slices. It is pure rendering: plain values in,
``bytes | None`` out — no Discord, no DB, no network.
"""

from __future__ import annotations

import io
import re

from .fonts import load_font
from .themes import RGB, Theme


def mix(a: RGB, b: RGB, t: float) -> RGB:
    """Linear blend of two RGB colours at fraction *t* (0 → *a*, 1 → *b*).

    Pure colour math. *t* is clamped to ``[0, 1]`` so an out-of-range fraction
    can never produce an invalid channel value.
    """
    if t < 0:
        t = 0.0
    elif t > 1:
        t = 1.0
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def initials(name: str) -> str:
    """First two alphanumerics of *name*, upper-cased (``?`` if none).

    Pure — the no-network avatar label, shared by every card with an initials
    disc.
    """
    letters = [c for c in name if c.isalnum()]
    return ("".join(letters[:2]) or "?").upper()


# Codepoint ranges the bundled DejaVu fonts render as a missing-glyph "tofu" box
# (□): emoji, pictographs, dingbats, and their presentation/joiner modifiers.
# Renderable punctuation the cards actually draw ("→" U+2192, "·" U+00B7, "…"
# U+2026) sits outside these ranges and is deliberately preserved.
_EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001faff"  # emoji / pictographs / symbols
    "\U00002600-\U000026ff"  # miscellaneous symbols
    "\U00002700-\U000027bf"  # dingbats
    "\U00002b00-\U00002bff"  # misc symbols & arrows
    "\U0000fe00-\U0000fe0f"  # variation selectors (emoji/text presentation)
    "\U0000200d"  # zero-width joiner (multi-part emoji)
    "\U000020e3"  # combining enclosing keycap
    "]+",
)


def image_safe(text: str) -> str:
    """Drop emoji/pictographs the bundled fonts can't draw, tidying the gap.

    A Pillow card drawn with a plain text font cannot render colour emoji, so an
    emoji in a title / value / display-name would become a tofu □ box. Every
    card draws its text through this: readable characters are kept, the glyphs
    that would have been boxes are dropped, and any leftover doubled/edge
    whitespace is collapsed. Untouched text is returned verbatim so intentional
    spacing is preserved. Pure — no Pillow needed.
    """
    cleaned = _EMOJI_RE.sub("", text)
    if cleaned == text:
        return text
    return " ".join(cleaned.split())


class CardCanvas:
    """A themed Pillow surface with the card primitives.

    Build one with :func:`new_canvas` (which returns ``None`` when Pillow is
    missing). All colour defaults pull from the bound :class:`Theme`, so the
    same draw calls re-skin automatically under a different theme.
    """

    def __init__(self, img, draw, theme: Theme) -> None:  # noqa: ANN001 — PIL types
        self._img = img
        self._draw = draw
        self.theme = theme

    @property
    def width(self) -> int:
        return self._img.width

    @property
    def height(self) -> int:
        return self._img.height

    @property
    def draw(self):  # noqa: ANN201 — escape hatch for bespoke art
        return self._draw

    def font(self, size: int, *, bold: bool = False):  # noqa: ANN201
        cands = self.theme.font_bold if bold else self.theme.font_regular
        return load_font(cands, size)

    def fit(self, text: str, font, max_width: int) -> str:  # noqa: ANN001
        """Truncate *text* with an ellipsis until it fits ``max_width`` px.

        Display/server names are unbounded; this clamps any string to the
        drawable area so it can never run off the card edge.
        """
        if self._draw.textlength(text, font=font) <= max_width:
            return text
        ell = "…"
        while text and self._draw.textlength(text + ell, font=font) > max_width:
            text = text[:-1]
        return (text + ell) if text else ell

    def text(
        self,
        xy: tuple[int, int],
        text: str,
        *,
        size: int = 24,
        bold: bool = False,
        color: RGB | None = None,
        max_width: int | None = None,
        anchor: str | None = None,
    ) -> None:
        """Themed text. ``max_width`` ellipsises overflow; ``color`` defaults to
        the theme's body-text colour. Emoji the font can't draw are stripped
        (:func:`image_safe`) so a card never shows a tofu □ box.
        """
        text = image_safe(text)
        font = self.font(size, bold=bold)
        if max_width is not None:
            text = self.fit(text, font, max_width)
        self._draw.text(
            xy,
            text,
            font=font,
            fill=color or self.theme.text,
            anchor=anchor,
        )

    def panel(
        self,
        box: tuple[int, int, int, int],
        *,
        radius: int = 14,
        fill: RGB | None = None,
        outline: RGB | None = None,
        width: int = 1,
    ) -> None:
        """A rounded panel; defaults to the theme's panel fill."""
        self._draw.rounded_rectangle(
            box,
            radius=radius,
            fill=fill if fill is not None else self.theme.panel,
            outline=outline,
            width=width,
        )

    def header_band(self, height: int, *, fill: RGB | None = None) -> None:
        """A full-width band across the top (the card's title strip)."""
        self._draw.rectangle(
            (0, 0, self.width, height),
            fill=fill if fill is not None else self.theme.panel,
        )

    def progress_bar(
        self,
        box: tuple[int, int, int, int],
        fraction: float,
        *,
        radius: int | None = None,
        track: RGB | None = None,
        fill: RGB | None = None,
    ) -> None:
        """A rounded progress bar; *fraction* is clamped to ``[0, 1]``.

        Guards a zero/near-zero fill so a tiny fraction still shows a cap-width
        sliver rather than an invalid (x0 > x1) rectangle.
        """
        x0, y0, x1, y1 = box
        r = radius if radius is not None else (y1 - y0) // 2
        self._draw.rounded_rectangle(
            box,
            radius=r,
            fill=track if track is not None else self.theme.outline,
        )
        frac = 0.0 if fraction < 0 else 1.0 if fraction > 1 else fraction
        span = x1 - x0
        end = x0 + int(span * frac)
        min_w = 2 * r  # never narrower than the rounded caps want
        if frac > 0 and end - x0 < min_w:
            end = min(x0 + min_w, x1)
        if end > x0:
            self._draw.rounded_rectangle(
                (x0, y0, end, y1),
                radius=r,
                fill=fill if fill is not None else self.theme.accent,
            )

    def initials_disc(
        self,
        center: tuple[int, int],
        radius: int,
        text: str,
        *,
        ring: RGB | None = None,
        size: int | None = None,
    ) -> None:
        """The no-network avatar: accent ring + filled disc + centred initials.

        Real member avatars require a CDN fetch (can block/fail), so a card can
        always fall back to this content-free disc and never ship broken.
        """
        cx, cy = center
        ring_c = ring if ring is not None else self.theme.accent
        self._draw.ellipse(
            (cx - radius - 6, cy - radius - 6, cx + radius + 6, cy + radius + 6),
            outline=ring_c,
            width=6,
        )
        self._draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=self.theme.panel,
        )
        font = self.font(size or int(radius * 0.9), bold=True)
        self._draw.text(
            (cx, cy),
            text,
            font=font,
            fill=self.theme.text,
            anchor="mm",
        )

    def avatar_disc(
        self,
        center: tuple[int, int],
        radius: int,
        avatar_png: bytes,
        *,
        ring: RGB | None = None,
    ) -> bool:
        """Composite a real, circular-cropped avatar with an accent ring.

        The engine stays pure: a caller that *may* touch the network fetches the
        member's avatar bytes and passes them in. Returns ``True`` on success,
        or ``False`` when the bytes can't be decoded — so the renderer falls
        back to :meth:`initials_disc` and never ships a broken card.
        """
        try:
            from PIL import Image, ImageDraw  # lazy: optional at import time

            av = Image.open(io.BytesIO(avatar_png)).convert("RGBA")
        except Exception:  # noqa: BLE001 — any decode failure → initials fallback
            return False
        cx, cy = center
        diameter = radius * 2
        av = av.resize((diameter, diameter))
        mask = Image.new("L", (diameter, diameter), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
        ring_c = ring if ring is not None else self.theme.accent
        self._draw.ellipse(
            (cx - radius - 6, cy - radius - 6, cx + radius + 6, cy + radius + 6),
            outline=ring_c,
            width=6,
        )
        self._img.paste(av, (cx - radius, cy - radius), mask)
        return True

    def to_png(self) -> bytes:
        buf = io.BytesIO()
        self._img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    def to_jpeg(self, quality: int = 88) -> bytes:
        buf = io.BytesIO()
        self._img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue()


def new_canvas(
    width: int,
    height: int,
    theme: Theme,
    *,
    mode: str = "RGB",
) -> CardCanvas | None:
    """A themed :class:`CardCanvas`, or ``None`` if Pillow is unavailable.

    The single lazy-PIL gate for the engine: a caller that gets ``None`` keeps
    its embed/text fallback.
    """
    try:
        from PIL import Image, ImageDraw  # lazy: degrade gracefully
    except Exception:  # noqa: BLE001 — any import failure → graceful no-op
        return None
    img = Image.new(mode, (width, height), theme.bg)
    return CardCanvas(img, ImageDraw.Draw(img), theme)


def pillow_available() -> bool:
    """True when Pillow can be imported (image rendering is live)."""
    try:
        import PIL  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "mix",
    "initials",
    "image_safe",
    "CardCanvas",
    "new_canvas",
    "pillow_available",
]
