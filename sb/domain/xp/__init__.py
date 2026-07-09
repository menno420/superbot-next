"""XP domain (band 4) — chat progression: awards, levels, rank, import.

INV-G: every XP mutation rides the audited K7 seam (`xp.award` /
`xp.reset` / `xp.import_levels`); `sb/domain/xp/store.py` is the sole
writer of the `xp` table. The shipped `services/xp_service.py` event
vocabulary (`xp.awarded` / `xp.level_up` / `xp.reset`) is carried
verbatim as declared EventSpecs.
"""
