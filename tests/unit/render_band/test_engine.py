"""Unit tests for the D1 render band (`sb/kernel/render/`).

Three concerns, per D1 § "What tests DO assert" — bytes are NEVER golden-pinned,
so nothing here asserts on PNG *content*, only on structure/behaviour:

  1. Pure helpers (initials / image_safe / mix) and the skin registry — run
     everywhere, no Pillow needed.
  2. The graceful-degradation contract — `new_canvas` returns `None` and
     `pillow_available()` is `False` when Pillow can't be imported. Exercised
     deterministically by blocking the PIL import, so it runs (and passes) in
     CI's no-runtime-deps `code-quality` gate too.
  3. The engine primitives — `importorskip("PIL")`, so they run in the jobs that
     install the lock (and locally) and skip cleanly where Pillow is absent.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from sb.kernel import render
from sb.kernel.render import (
    DEFAULT_THEME,
    THEMES,
    Theme,
    get_theme,
    image_safe,
    initials,
    mix,
    new_canvas,
    pillow_available,
)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8"


def _block_pil(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force any `import PIL[...]` to fail — simulates a Pillow-less host."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # noqa: ANN001, ANN202
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("PIL blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


# --------------------------------------------------------------------------- #
# 1. Pure helpers — no Pillow needed                                          #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Jane Doe", "JA"),
        ("j", "J"),
        ("", "?"),
        ("!!!", "?"),          # no alnum → sentinel
        ("🎉hello", "HE"),      # emoji is not alnum, skipped
        ("a1b2", "A1"),
        ("étienne", "ÉT"),     # unicode alnum counts
    ],
)
def test_initials(name: str, expected: str) -> None:
    assert initials(name) == expected


def test_image_safe_strips_emoji_and_collapses() -> None:
    assert image_safe("🏆 XP Leaderboard") == "XP Leaderboard"
    assert image_safe("8,473 🪙") == "8,473"
    # A dead-verbatim string with nothing to strip is returned unchanged
    # (identity, so intentional spacing survives).
    plain = "level  7   ·  next"
    assert image_safe(plain) is plain


def test_image_safe_preserves_drawable_punctuation() -> None:
    # → (U+2192), · (U+00B7), … (U+2026) sit outside the stripped ranges.
    s = "rank → 3 · top … tier"
    assert image_safe(s) == s


@pytest.mark.parametrize(
    ("t", "expected"),
    [
        (0.0, (0, 0, 0)),
        (1.0, (10, 20, 30)),
        (0.5, (5, 10, 15)),
        (-1.0, (0, 0, 0)),      # clamped low → a
        (2.0, (10, 20, 30)),    # clamped high → b
    ],
)
def test_mix_clamps(t: float, expected: tuple[int, int, int]) -> None:
    assert mix((0, 0, 0), (10, 20, 30), t) == expected


# --------------------------------------------------------------------------- #
# 2. Skin registry + the skin-typo guard                                      #
# --------------------------------------------------------------------------- #

def test_default_theme_is_registered() -> None:
    assert DEFAULT_THEME in THEMES
    assert isinstance(THEMES[DEFAULT_THEME], Theme)


def test_registry_keys_match_theme_self_name() -> None:
    # The skin-typo guard: a registry key whose Theme.name disagrees is a silent
    # mis-skin waiting to happen (get_theme resolves by key but code/tests may
    # read .name). Pin key == name for every declared skin.
    for key, theme in THEMES.items():
        assert theme.name == key, f"skin {key!r} declares name {theme.name!r}"


def test_get_theme_silent_fallback() -> None:
    # None and an unknown/typo'd key both resolve to the default — never raise.
    assert get_theme(None) is THEMES[DEFAULT_THEME]
    assert get_theme("no-such-skin-typo") is THEMES[DEFAULT_THEME]
    assert get_theme(DEFAULT_THEME) is THEMES[DEFAULT_THEME]


def test_theme_is_frozen_and_hashable() -> None:
    theme = THEMES[DEFAULT_THEME]
    with pytest.raises(Exception):
        theme.name = "mutated"  # type: ignore[misc]  # frozen dataclass
    assert isinstance(hash(theme), int)  # hashable → cache-safe


# --------------------------------------------------------------------------- #
# 3. Graceful degradation — the None / text-embed fallback path               #
# --------------------------------------------------------------------------- #

def test_new_canvas_none_without_pillow(monkeypatch: pytest.MonkeyPatch) -> None:
    _block_pil(monkeypatch)
    assert new_canvas(64, 32, get_theme(None)) is None


def test_pillow_available_false_without_pillow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _block_pil(monkeypatch)
    assert pillow_available() is False


def test_pure_helpers_work_without_pillow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The layout-only surface must stay importable/usable with no Pillow.
    _block_pil(monkeypatch)
    assert initials("Ada") == "AD"
    assert image_safe("🚀go") == "go"
    assert mix((0, 0, 0), (4, 4, 4), 0.5) == (2, 2, 2)


# --------------------------------------------------------------------------- #
# 4. Bundled fonts — assets present on the package path                       #
# --------------------------------------------------------------------------- #

def test_bundled_fonts_present() -> None:
    for path in (render.BUNDLED_BOLD, render.BUNDLED_REGULAR):
        p = Path(path)
        assert p.exists(), f"bundled font missing: {path}"
        assert p.suffix == ".ttf"
        assert p.stat().st_size > 0


def test_default_candidates_lead_with_bundle() -> None:
    assert render.DEFAULT_BOLD_CANDIDATES[0] == render.BUNDLED_BOLD
    assert render.DEFAULT_REGULAR_CANDIDATES[0] == render.BUNDLED_REGULAR


# --------------------------------------------------------------------------- #
# 5. Engine primitives — require Pillow                                        #
# --------------------------------------------------------------------------- #

def _canvas(w: int = 200, h: int = 80):  # noqa: ANN202
    c = new_canvas(w, h, get_theme("midnight"))
    assert c is not None
    return c


def test_new_canvas_dimensions_and_png_export() -> None:
    pytest.importorskip("PIL")
    c = _canvas(240, 96)
    assert c.width == 240
    assert c.height == 96
    png = c.to_png()
    assert png.startswith(_PNG_MAGIC)
    assert len(png) > len(_PNG_MAGIC)


def test_jpeg_export() -> None:
    pytest.importorskip("PIL")
    jpeg = _canvas().to_jpeg()
    assert jpeg.startswith(_JPEG_MAGIC)


@pytest.mark.parametrize("fraction", [-5.0, 0.0, 0.001, 0.5, 1.0, 3.0])
def test_progress_bar_clamps_and_renders(fraction: float) -> None:
    pytest.importorskip("PIL")
    c = _canvas()
    # Any fraction — in or out of [0,1] — must render without raising an
    # invalid-rectangle error and still export a valid PNG.
    c.progress_bar((10, 30, 190, 50), fraction)
    assert c.to_png().startswith(_PNG_MAGIC)


def test_text_and_panel_primitives_render() -> None:
    pytest.importorskip("PIL")
    c = _canvas()
    c.header_band(24)
    c.panel((8, 30, 120, 70))
    c.text((12, 4), "A very long display name that should be ellipsised",
            size=18, bold=True, max_width=100)
    c.text((12, 40), "plain", size=14)
    assert c.to_png().startswith(_PNG_MAGIC)


def test_initials_disc_renders() -> None:
    pytest.importorskip("PIL")
    c = _canvas(120, 120)
    c.initials_disc((60, 60), 40, initials("Grace Hopper"))
    assert c.to_png().startswith(_PNG_MAGIC)


def test_avatar_disc_fallback_on_bad_bytes() -> None:
    pytest.importorskip("PIL")
    c = _canvas(120, 120)
    # Undecodable bytes → False, so a renderer falls back to initials_disc and
    # never ships a broken card.
    assert c.avatar_disc((60, 60), 40, b"not-a-png") is False


def test_avatar_disc_composites_valid_png() -> None:
    PIL = pytest.importorskip("PIL")  # noqa: N806
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    c = _canvas(120, 120)
    assert c.avatar_disc((60, 60), 40, buf.getvalue()) is True
    assert c.to_png().startswith(_PNG_MAGIC)


def test_load_font_never_raises_on_bogus_candidates() -> None:
    pytest.importorskip("PIL")
    # An exhausted candidate list falls back to Pillow's bitmap default.
    font = render.load_font(("/no/such/font.ttf",), 16)
    assert font is not None
