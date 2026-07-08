"""sim/ — the layer-V arrangement simulator (V-3; design-spec §2.10, built
at canonical-plan §5 step 11).

**The manifest is the search space; the simulator is the search** (the
standing owner rule). This package is the SHARED harness — search-space
extraction, candidate generation, rank + drift-pin — hosting PLUGGABLE
per-surface scoring oracles:

  sim/space.py        [A]-field extraction from registered manifests (the
                      write surface is machine-derived from field roles,
                      never guessed), the telemetry sidecar loader, hard
                      constraints, candidate generation.
  sim/oracles/        the oracle registry + the three named oracles:
                      navigation (the Q-0235 instruction-driven engine —
                      the FIRST oracle, powering the hub-topology
                      ratification), settings_grouping (scroll-to-coverage
                      over the fallback DAG), dense_panel (ergonomic
                      interaction cost). Distinct oracles on one runner —
                      the navigation engine does NOT subsume the other two.
  sim/run.py          the deterministic runner CLI (`--space <sim_id>`):
                      exhaustive when small, fixed-seed annealing otherwise;
                      emits sim/records/<sim_id>-<date>.json — winner,
                      per-term breakdown, top-5 alternatives, input hashes,
                      seed: the auditable "why it won".
  sim/apply.py        the SOLE [A]-writer: manifest/layout/<subsystem>
                      .lock.json overlays addressed by namespace id, each
                      entry stamped SimRef(record_id, input_hash) or
                      Exempt(reason). The loader rejects any non-[A] key —
                      a simulator bug can corrupt layout but structurally
                      cannot corrupt semantics (§2.10.3).
  sim/navigation_walk.py
                      the A-3 navigation-completeness walker (drives the
                      REAL panel engine through every registered node;
                      consumed by the CI golden in
                      tests/unit/navigation_golden/).
  sim/usage.snapshot.json
                      the telemetry sidecar (§2.10.4). SEEDED-EMPTY at
                      birth: the sim never runs on invented data — a
                      feature with no telemetry runs on a neutral prior and
                      stays Exempt until real signal exists.

The gate: tools/check_sim_gate.py (sim-reviewed-or-exempt, design-spec §6
gate 4) pins every [A] assignment to provenance via the committed
sim/sim-gate-baseline.json.

Layer V sits OUTSIDE the boot chain: nothing under sb/ imports sim/.
"""
