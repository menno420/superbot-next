"""The rank-card attachment — send shape ported, pixels parked.

The shipped card (utils/rank_render.py over utils/card_render's theme
engine, PIL) rendered avatar disc + level/progress panels into the
attachment ``rank.png`` (services/xp_helpers.py ``RANK_CARD_FILENAME``)
and rode EVERY rank surface after the visual card-engine H3 rollout:
``!rank`` (#1401), the ``!xpmenu`` hub (#1413) and the stat toggles. The
goldens pin the SEND SHAPE only — discord.py put the whole message body
on the multipart wire, so the capture recorded exactly
``{"_files": ["rank.png"]}`` (xp/xp_chat_award, xp/sweep_xpmenu) and no
pixel or embed byte is pinned.

This module ships the send surface with a deliberate placeholder card: a
valid single-color PNG built with stdlib zlib/struct (the repo carries no
imaging dependency — the utility profile_card precedent). The themed
renderer (avatar disc, progress bar, provider skins) is the visual
card-engine slice's parked follow-up — honest waiting surface, never
invented content.
"""

from __future__ import annotations

import struct
import zlib

__all__ = ["RANK_CARD_FILENAME", "render_rank_card"]

#: the shipped attachment filename (services/xp_helpers.RANK_CARD_FILENAME).
RANK_CARD_FILENAME = "rank.png"

# placeholder card geometry — a small solid panel; nothing pins it.
_WIDTH = 128
_HEIGHT = 32
_RGB = (47, 49, 54)              # neutral dark panel


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def render_rank_card(user_id: int, guild_id: int, *,
                     stat: str = "both",
                     avatar_png: bytes | None = None) -> bytes:
    """→ PNG bytes for the placeholder card (deterministic; args are the
    future themed renderer's signature — the shipped build_rank_response
    took the member, the stat toggle and the fetched avatar bytes —
    unused by the placeholder)."""
    del user_id, guild_id, stat, avatar_png
    ihdr = struct.pack(">IIBBBBB", _WIDTH, _HEIGHT, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(_RGB) * _WIDTH          # filter 0 + RGB pixels
    idat = zlib.compress(row * _HEIGHT)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", idat)
            + _chunk(b"IEND", b""))
