"""AI surface subsystem (band 7, final slice) — the operator surface of
K10 plus the last composition seams.

Module map:
  normalize.py     normalize_question (verbatim utils/ai_text_normalize)
  store.py         ai_review_log + ai_answer_presets (migration 0024)
  review.py        answer registry + record_unknown/record_correction
  ops.py           K7 lanes: record/resolve review entries, set/remove
                   presets, erasure bodies
  readers.py       install_ai_platform(): guild-policy overlay reader,
                   preset lookup, band-1 ai_readers, history scanner
  round_cash.py    the plan→execute→verify round-cash runner
                   (register_answer_workflow "analyze_execute_verify")
  orchestration_presets.py  btd6_grounded / strict / no_tools profiles
  tools.py         the btd6 factual tool rows (register_tool) with
                   handler factories over sb.domain.btd6
  service.py       !ai + !aireview routes/views; !aimenu
  panels.py        ai.hub
"""
