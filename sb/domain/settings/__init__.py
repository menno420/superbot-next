"""Band 1 — the SETTINGS subsystem (design-spec §4; port band 1 slice 1).

Layout:
  keys.py        the shipped utils.settings_keys vocabulary, verbatim (124
                 keys / 17 modules) — the canonical persisted key strings
  ops.py         the K7 scalar/binding mutation lane (CompoundOpSpecs)
  service.py     typed reads (coerce/validate over the K7 resolve seam),
                 guild config snapshot/export (A-15), the S15 platform
                 latch store install
  panels.py      the settings hub panel factory (@panel "settings.hub")
  ai_readers.py  the band-1 K10 seam installs (policy bundle / memory /
                 profile-key readers over declared ai.* legacy keys)
  ai_tasks.py    legacy task-id claims (settings.explain / settings.propose)
                 + the manifest-generated capabilities overview contract
"""
