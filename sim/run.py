"""The deterministic sim runner (design-spec §2.10.5).

`python3 -m sim.run --space <sim_id>` loads `manifest.snapshot.json` + the
telemetry sidecar (both hashed into the record), generates the space's
candidates under the hard constraints, scores with the space's STATED
oracle, searches exhaustively when small and by fixed-seed annealing
otherwise, and emits `sim/records/<sim_id>-<date>.json`: winning
arrangement, per-term score breakdown, top-5 alternatives, input hashes,
seed — the auditable "why it won".

Spaces are REGISTERED (port bands declare theirs); an unknown/empty space
is a loud exit, never an invented run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sim.oracles import ScoreBreakdown, get_oracle  # noqa: E402
from sim.space import (  # noqa: E402
    SIDECAR_PATH,
    SNAPSHOT_PATH,
    load_sidecar,
    stable_hash,
)

RECORDS_DIR = REPO_ROOT / "sim" / "records"
DEFAULT_SEED = 1420
ANNEAL_STEPS = 2000
TOP_ALTERNATIVES = 5

__all__ = [
    "SpaceDef",
    "clear_spaces_for_tests",
    "register_space",
    "registered_spaces",
    "run_space",
]


@dataclass(frozen=True)
class SpaceDef:
    """One searchable space. `candidates` yields admissible candidates
    (hard constraints already applied — sim.space helpers); `context`
    builds the oracle context (tasks/pairs/specs); `neighbour` enables
    annealing for large spaces (None = score the generated list only)."""

    sim_id: str
    oracle: str
    candidates: Callable[[dict[str, Any], int], list[Any]]
    context: Callable[[dict[str, Any]], dict[str, Any]]
    neighbour: Callable[[Any, random.Random], Any] | None = None


_SPACES: dict[str, SpaceDef] = {}


def register_space(space: SpaceDef) -> None:
    if space.sim_id in _SPACES:
        raise ValueError(f"space {space.sim_id!r} already registered")
    _SPACES[space.sim_id] = space


def registered_spaces() -> tuple[str, ...]:
    return tuple(sorted(_SPACES))


def clear_spaces_for_tests() -> None:
    _SPACES.clear()


def _score_all(
    oracle: Any, candidates: list[Any], context: dict[str, Any]
) -> list[tuple[Any, ScoreBreakdown]]:
    return [(c, oracle.score(c, context)) for c in candidates]


def _anneal(
    oracle: Any,
    start: Any,
    context: dict[str, Any],
    neighbour: Callable[[Any, random.Random], Any],
    rng: random.Random,
) -> list[tuple[Any, ScoreBreakdown]]:
    """Fixed-seed annealing: deterministic bit-for-bit for a given seed."""
    current = start
    current_score = oracle.score(current, context)
    seen: list[tuple[Any, ScoreBreakdown]] = [(current, current_score)]
    temperature = 1.0
    for step in range(ANNEAL_STEPS):
        temperature = max(0.01, 1.0 - step / ANNEAL_STEPS)
        candidate = neighbour(current, rng)
        candidate_score = oracle.score(candidate, context)
        seen.append((candidate, candidate_score))
        delta = candidate_score.total - current_score.total
        if delta >= 0 or rng.random() < temperature * 0.1:
            current, current_score = candidate, candidate_score
    return seen


def run_space(
    sim_id: str,
    *,
    seed: int = DEFAULT_SEED,
    records_dir: Path = RECORDS_DIR,
    sidecar_path: Path = SIDECAR_PATH,
    snapshot_path: Path = SNAPSHOT_PATH,
) -> Path:
    space = _SPACES.get(sim_id)
    if space is None:
        raise KeyError(f"no registered space {sim_id!r}; registered: {sorted(_SPACES)}")

    snapshot = json.loads(snapshot_path.read_text())
    usage = load_sidecar(sidecar_path)
    inputs = {"snapshot": snapshot, "sidecar": json.loads(sidecar_path.read_text())}

    context = space.context({"snapshot": snapshot, "usage": usage})
    context.setdefault("usage", usage)
    candidates = space.candidates(context, seed)
    if not candidates:
        raise ValueError(f"space {sim_id!r} generated zero admissible candidates")

    oracle = get_oracle(space.oracle)
    rng = random.Random(seed)
    scored = _score_all(oracle, candidates, context)
    if space.neighbour is not None and len(candidates) < 50:
        # small generated set + a neighbour function = anneal from the best
        best_start = max(scored, key=lambda cs: cs[1].total)[0]
        scored.extend(_anneal(oracle, best_start, context, space.neighbour, rng))

    scored.sort(key=lambda cs: (-cs[1].total, json.dumps(cs[0], default=str)))
    winner, winner_score = scored[0]
    alternatives = scored[1 : 1 + TOP_ALTERNATIVES]

    record = {
        "schema_version": 1,
        "sim_id": sim_id,
        "date": _dt.date.today().isoformat(),
        "seed": seed,
        "oracle": space.oracle,
        "input_hashes": {
            "snapshot": stable_hash(inputs["snapshot"]),
            "sidecar": stable_hash(inputs["sidecar"]),
        },
        "weights_provenance": usage.provenance,
        "confidence": winner_score.confidence,
        "winner": {
            "arrangement": winner,
            "total": winner_score.total,
            "terms": winner_score.terms,
            "notes": winner_score.notes,
        },
        "alternatives": [
            {"arrangement": alt, "total": s.total, "terms": s.terms}
            for alt, s in alternatives
        ],
        "candidates_scored": len(scored),
    }
    records_dir.mkdir(parents=True, exist_ok=True)
    out = records_dir / f"{sim_id}-{record['date']}.json"
    out.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sim.run")
    parser.add_argument("--space", required=True, help="registered sim_id")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    try:
        out = run_space(args.space, seed=args.seed)
    except KeyError as exc:
        print(f"sim.run: {exc}")
        print("Port bands register spaces via sim.run.register_space; none "
              "exist until manifests do (the manifest is the search space).")
        return 2
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
