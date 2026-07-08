"""K9/S10 — the C-2 draft / preview / confirm / apply pipeline (frozen L0
spec 06). Producer-agnostic: one pipe, N producers (human setup, AI
orchestration, presets, release-test, repair).

Layer map:
  sb/spec/draft.py       — the grammar leaf (Producer/DraftStatus/Draft/…)
  sb/kernel/db/draft.py  — the DB primitive (append-by-op_seq, CAS status)
  store.py               — the domain store over the primitive
  registry.py            — the fail-closed OpKindRegistry (no binding ⇒
                           un-draftable, not cosmetically "unavailable")
  preview.py             — batch preview/confirm shapes over K7 preview()
  accept.py              — accept authority (AND over every DISTINCT op ref)
  apply.py               — sequenced per-op-atomic idempotent apply over K7
                           run(spec, ctx) PER-OP (PIN-2 — EFFECT-bearing
                           draft ops are structurally outside run_ref's
                           atomic_db_only fence)
  pipeline.py            — the DraftPipeline facade + error types
  janitor.py             — ExpiryJanitorLane (hosted on 09's PollSupervisor)
"""
