"""Project Moon (Limbus) knowledge domain (band 7).

Module map:
  data/        the committed Limbus structural fixtures (6 JSON files,
               file-for-file from oracle disbot/data/projmoon/limbus/)
  dataset.py   typed loader + resolver (verbatim)
  keywords.py  has_limbus_context detector (verbatim)
  context.py   build() — entity + roster grounding (verbatim)
  grounding.py names-only verifier + refusal (K10 verify registry)
  evals.py     the MINTED 12-probe A-17 corpus (oracle had none)
  ai_tasks.py  K10 registrations (projmoon.answer, probe order 110,
               gatherer, floor, contract, suite)
  service.py   the !pm browse/lookup views
  panels.py    projmoon.hub
"""
