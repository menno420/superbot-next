"""BTD6 knowledge domain (band 7) — the mature L4 exemplar onto K10.

Module map:
  data/            the committed corpus (74 JSON files, file-for-file
                   from oracle disbot/data/btd6/ @7f7628e1)
  dataset.py       focused typed loader (towers/heroes/bloons/bosses)
                   + the read_blob/list_blob_names seam
  keywords.py      curated context keywords + degree cue (verbatim)
  difficulty_costs.py  Medium→any-difficulty pricing (verbatim)
  paragon_math.py  paragon catalogue + shorthand resolver + thresholds
  paragon_degrees.py   wiki degree-scaling formulas (verbatim scalars)
  stats.py         paragon stats files + per-tower paragon identity
  resolver.py      NL → ResolvedIntent (entity/alias/round extraction)
  interactions.py  damage-type/status interaction grounding (verbatim)
  context.py       build() — the grounding pipeline (focused passes)
  grounding.py     name index + validate reply + paragon existence attr
  evals.py         the 16-probe QA-accuracy corpus (A-17 suite)
  ai_tasks.py      K10 registrations (tasks/probe/gatherer/floor/
                   contract/suite)
  store.py         btd6_strategies (MEMBER_PII, anonymize erasure)
  ops.py           K7 lanes: submit_strategy / review_strategy / scrub
  service.py       routes + reference views + pending terminals
  panels.py        btd6.hub
"""
