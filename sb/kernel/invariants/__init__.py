"""S12 — data-integrity invariants (frozen L0 spec 11): the content-level
complement to spec 09's version-drift policy. Declared invariants →
scheduled dry-run sweep → audited repair / evidence-preserving quarantine;
the SAME sweep is the CUT-2 verify-import + CUT-3 verified-restore check.

  sb/spec/invariants.py — the grammar leaf + facet registry
  compile.py            — the invariant_coverage fence
  sweep.py              — InvariantSweepLane (a 09 PollLane) + SWEEP_ACTOR +
                          run_verify_import (the cutover seam)
  sb/kernel/db/invariants.py — sb_quarantine + sb_invariant_sweep_log CRUD
"""
