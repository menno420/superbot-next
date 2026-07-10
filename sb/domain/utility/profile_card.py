"""The /myprofile hero-card attachment — send shape ported, pixels parked.

The shipped card (disbot/utils/profile_render.py over utils/card_render's
theme engine, PIL) rendered avatar disc + stat panels into the attachment
``profile.png`` (disbot/views/profile/profile_view.py `_CARD_FILENAME`).
The goldens pin the SEND SHAPE only — discord.py put the whole message
body on the multipart wire, so the capture recorded exactly
``{"_files": ["profile.png"]}`` (utility/sweep_myprofile,
utility/sweep_slash_myprofile) and no pixel or embed byte is pinned.

This module ships the send surface with a deliberate placeholder card: a
valid single-color PNG built with stdlib zlib/struct (the repo carries no
imaging dependency). The themed renderer + the participation-registry stat
card + the ProfileHomeView manage-settings hub are the profile band's
parked follow-up — honest waiting surface, never invented content (the
general-band empty-content-pool precedent).
"""

from __future__ import annotations

import struct
import zlib

__all__ = ["CARD_FILENAME", "render_profile_card"]

#: the shipped attachment filename (profile_view.py `_CARD_FILENAME`).
CARD_FILENAME = "profile.png"

# placeholder card geometry — a small solid panel; nothing pins it.
_WIDTH = 128
_HEIGHT = 32
_RGB = (47, 49, 54)              # neutral dark panel


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def render_profile_card(user_id: int, guild_id: int) -> bytes:
    """→ PNG bytes for the placeholder card (deterministic; args are the
    future themed renderer's signature, unused by the placeholder)."""
    del user_id, guild_id
    ihdr = struct.pack(">IIBBBBB", _WIDTH, _HEIGHT, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(_RGB) * _WIDTH          # filter 0 + RGB pixels
    idat = zlib.compress(row * _HEIGHT)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", idat)
            + _chunk(b"IEND", b""))
