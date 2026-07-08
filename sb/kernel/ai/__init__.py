"""K10 — the AI invocation kernel (canonical plan §2.1 K10 row + §2.4 B-1).

The runtime seam that boots with the bot. Domain-agnostic by construction:
the three contaminations named by B-1 are cut here —

* the closed ``AITask`` enum → the domain-registered task registry
  (:mod:`sb.kernel.ai.tasks`);
* the hand-branched ``_gather_feature_facts`` if-chain → registry hooks
  (:mod:`sb.kernel.ai.feature_facts`, PR 2);
* the grounded-answer engine hoisted out of the btd6 namespace
  (:mod:`sb.kernel.ai.grounding`, PR 3).

Layout:

* ``tasks.py``        — task registry (replaces ``AITask``; legacy ids frozen)
* ``contracts.py``    — provider-neutral request/response/tool grammar
* ``flags.py``        — Config-installed feature gates (RC-10 discipline;
  no env reads outside ``sb/kernel/config``)
* ``routing.py``      — task → (provider, model, timeout) resolution
* ``safety.py``       — deterministic prechecks + untrusted-data containment
* ``diagnostics.py``  — in-process gateway diagnostics collector
* ``providers/``      — the ONLY modules permitted to import LLM SDKs
  (guarded imports; anthropic / openai / deterministic)
* ``gateway.py``      — the single never-raises chokepoint:
  flags→safety→redaction→routing→provider→metrics→degrade
* ``socket_guard.py`` — the A-17 socket-deny eval guard

Knowledge DOMAINS (btd6_*, projmoon_*, corpora, ingestion) stay L4 — they
port at band 7 ONTO these seams, never into them.
"""
