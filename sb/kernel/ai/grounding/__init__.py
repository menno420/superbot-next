"""The grounded-answer engine (K10) — B-1 contamination #3 cut.

HOISTED out of the btd6 namespace (shipped ``disbot/utils/btd6/
{grounding_format,name_guard,absence_guard}.py`` + the ``GroundingResult``
/ verify machinery of ``services/btd6_grounding_service.py`` — projmoon
already imported it cross-domain, proving it was never BTD6 code):

* ``format.py``       — grounding-line formatting (sanitise, provenance,
  relative freshness, the infinite-sentinel render rule)
* ``name_guard.py``   — common-word-safe proper-name + number matching
* ``absence_guard.py``— the false-absence contradiction guard (mechanics;
  existence attributes REGISTER per domain)
* ``verify.py``       — ``GroundingResult``, the per-task verifier
  registry, the do-not-state constraint builder, and the
  verify + regenerate-once loop

Domain DATA (name indexes, keyword corpora, attribute tables, refusal
copy) registers at band 7; the mechanics live here.
"""

from __future__ import annotations

from sb.kernel.ai.grounding.verify import (
    GroundingResult,
    build_grounding_constraint,
    clear_verifiers_for_tests,
    register_grounding_verifier,
    verify_and_regenerate_once,
    verify_reply,
)

__all__ = [
    "GroundingResult",
    "build_grounding_constraint",
    "clear_verifiers_for_tests",
    "register_grounding_verifier",
    "verify_and_regenerate_once",
    "verify_reply",
]
