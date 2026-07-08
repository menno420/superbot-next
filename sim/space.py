"""The search space (design-spec §2.10.1/§2.10.5).

Machine-derives the simulator's write surface from the grammar's own S/A/O
field roles: an assignment exists for every [A]-tagged field on every spec
node reachable from a registered manifest. Everything else is [S] and
invariant under simulation.

Also home to: the telemetry-sidecar loader (§2.10.4 — seed priors vs
measured pairs, provenance + confidence), the hard constraints (§2.10.5 —
Discord caps, destructive placement), and candidate generation for the
panel-layout mutation vocabulary.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDECAR_PATH = REPO_ROOT / "sim" / "usage.snapshot.json"
SNAPSHOT_PATH = REPO_ROOT / "manifest.snapshot.json"

# §2.10.5 hard constraints — Discord's caps.
MAX_ROWS_PER_PAGE = 5
MAX_PER_ROW = 5
MAX_COMPONENTS = 25
# Exhaustive-vs-annealing crossover (§2.10.5 "searches exhaustively when
# small and by fixed-seed annealing otherwise").
EXHAUSTIVE_LIMIT = 5000

_IDENTITY_ATTRS = (
    "panel_id", "action_id", "selector_id", "modal_id", "field_id",
    "key", "name", "table", "id",
)


# ------------------------------------------------------------- serialization
def _plain(value: Any) -> Any:
    """Spec value -> deterministic plain data (mirrors the compiler's rules)."""
    if isinstance(value, enum.Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: _plain(getattr(value, f.name))
            for f in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(v) for v in value)
    return value


def stable_hash(data: Any) -> str:
    blob = json.dumps(_plain(data), sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


# --------------------------------------------------------------- [A] fields
def a_tagged_fields() -> set[str]:
    """`SpecType.field` names role-tagged [A], from the grammar's own role
    registry (§2.10.1: 'the classification is the grammar's')."""
    import sb.spec.panels  # noqa: F401 - registrations run at import
    from sb.spec.roles import snapshot_field_roles

    return {k for k, v in snapshot_field_roles().items() if v == "A"}


def _node_identity(obj: Any) -> str | None:
    for attr in _IDENTITY_ATTRS:
        value = getattr(obj, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


def arrangement_assignments(manifests: Iterable[Any]) -> dict[str, Any]:
    """Every [A]-field assignment reachable from the given manifests,
    addressed by namespace id:

        "<subsystem>:<anchor-id>:<SpecType>.<field>[<path>]" -> plain value

    `anchor-id` is the nearest identified ancestor spec node (a panel id,
    action id, setting key, …) so overlay keys survive re-serialization.
    """
    a_fields = a_tagged_fields()
    assignments: dict[str, Any] = {}

    def walk(obj: Any, subsystem: str, anchor: str, path: str) -> None:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            identity = _node_identity(obj)
            here = identity or anchor
            type_name = type(obj).__name__
            for f in dataclasses.fields(obj):
                value = getattr(obj, f.name)
                child_path = f"{path}/{type_name}.{f.name}" if path else f"{type_name}.{f.name}"
                if f"{type_name}.{f.name}" in a_fields:
                    key = f"{subsystem}:{here}:{type_name}.{f.name}"
                    if key in assignments:
                        key = f"{subsystem}:{here}:{child_path}"
                    assignments[key] = _plain(value)
                walk(value, subsystem, here, child_path)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for item in obj:
                walk(item, subsystem, anchor, path)
        elif isinstance(obj, dict):
            for item in obj.values():
                walk(item, subsystem, anchor, path)

    for manifest in manifests:
        subsystem = str(getattr(manifest, "key", "") or "?")
        walk(manifest, subsystem, subsystem, "")
    return assignments


def registered_manifests() -> list[Any]:
    """The sb.manifest walk (the check_intent_survival pattern)."""
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg

    found: list[Any] = []
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        one = getattr(module, "MANIFEST", None)
        if one is not None:
            found.append(one)
        found.extend(getattr(module, "MANIFESTS", ()) or ())
    return found


# ------------------------------------------------------------------- sidecar
@dataclass(frozen=True)
class UsageSnapshot:
    """§2.10.4 — what the objectives actually read. `counts` are per-node
    usage weights keyed by namespace id; `pairs` the co-occurrence matrix
    keyed "kind|id_a|id_b" (settings co-edits, action co-clicks, panel
    co-opens). Declared co_*_group strings are seed priors ONLY; measured
    pairs override them the moment they exist."""

    provenance: str            # "seeded" | "telemetry(<period>)"
    capture_window: str | None
    session_definition: str
    counts: dict[str, float]
    pairs: dict[str, float]

    def weight(self, node_id: str) -> float:
        # neutral prior — the sim never runs on invented data (§2.10.4)
        return float(self.counts.get(node_id, 1.0))

    @property
    def confidence(self) -> str:
        return "low" if self.provenance == "seeded" else "measured"


def load_sidecar(path: Path = SIDECAR_PATH) -> UsageSnapshot:
    data = json.loads(path.read_text())
    header = data.get("header", {})
    return UsageSnapshot(
        provenance=header.get("provenance", "seeded"),
        capture_window=header.get("capture_window"),
        session_definition=header.get("session_definition", ""),
        counts={str(k): float(v) for k, v in (data.get("counts") or {}).items()},
        pairs={str(k): float(v) for k, v in (data.get("pairs") or {}).items()},
    )


# ---------------------------------------------------------- hard constraints
def hot_component_ids(component_weights: dict[str, float]) -> set[str]:
    """`hot` = top usage-weight quartile within the panel, ties broken by
    namespace-id sort (§2.10.4 — deterministic, never vibes)."""
    if not component_weights:
        return set()
    ordered = sorted(component_weights.items(), key=lambda kv: (-kv[1], kv[0]))
    quartile = max(1, len(ordered) // 4)
    return {cid for cid, _ in ordered[:quartile]}


def check_hard_constraints(
    layout: tuple[tuple[tuple[str, ...], ...], ...],
    *,
    destructive: set[str] = frozenset(),
    component_weights: dict[str, float] | None = None,
) -> list[str]:
    """§2.10.5: Discord 5-row/25-component caps + destructive placement —
    never row 0, never adjacent to a hot action (adjacent = neighbouring
    column in the same row, or the same column in a vertically neighbouring
    row). A violation list; empty = admissible. `layout` is pages -> rows ->
    component ids (the PageSpec.rows shape)."""
    problems: list[str] = []
    weights = component_weights or {}
    hot = hot_component_ids(weights)
    total = 0
    for p_idx, rows in enumerate(layout):
        if len(rows) > MAX_ROWS_PER_PAGE:
            problems.append(f"page {p_idx}: {len(rows)} rows > {MAX_ROWS_PER_PAGE}")
        for r_idx, row in enumerate(rows):
            total += len(row)
            if len(row) > MAX_PER_ROW:
                problems.append(
                    f"page {p_idx} row {r_idx}: {len(row)} components > {MAX_PER_ROW}"
                )
            for c_idx, cid in enumerate(row):
                if cid not in destructive:
                    continue
                if r_idx == 0:
                    problems.append(f"destructive {cid!r} on row 0 (page {p_idx})")
                neighbours: list[str] = []
                if c_idx > 0:
                    neighbours.append(row[c_idx - 1])
                if c_idx + 1 < len(row):
                    neighbours.append(row[c_idx + 1])
                for other_r in (r_idx - 1, r_idx + 1):
                    if 0 <= other_r < len(rows) and c_idx < len(rows[other_r]):
                        neighbours.append(rows[other_r][c_idx])
                for n in neighbours:
                    if n in hot:
                        problems.append(
                            f"destructive {cid!r} adjacent to hot {n!r} "
                            f"(page {p_idx} row {r_idx})"
                        )
    if total > MAX_COMPONENTS:
        problems.append(f"{total} components > {MAX_COMPONENTS}")
    return problems


# ------------------------------------------------------- candidate generation
def _chunk_layout(order: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """One deterministic pages->rows shape for an ordering: rows of
    MAX_PER_ROW, MAX_ROWS_PER_PAGE-1 rows per page (row 4 stays free for the
    engine-injected nav slots, which live OUTSIDE the searchable space)."""
    rows = [
        tuple(order[i:i + MAX_PER_ROW])
        for i in range(0, len(order), MAX_PER_ROW)
    ]
    per_page = MAX_ROWS_PER_PAGE - 1
    pages = tuple(
        tuple(rows[i:i + per_page]) for i in range(0, len(rows), per_page)
    )
    return pages


def generate_layout_candidates(
    component_ids: tuple[str, ...],
    *,
    seed: int,
    limit: int = EXHAUSTIVE_LIMIT,
) -> list[tuple[tuple[tuple[str, ...], ...], ...]]:
    """The panel-layout mutation vocabulary (§2.10.5: move component to
    row/page within LayoutSpec's coverage rules). Exhaustive over orderings
    when the space is small; fixed-seed sampled orderings otherwise. Every
    candidate covers exactly the declared population (coverage is exhaustive
    + exclusive by construction)."""
    n = len(component_ids)
    space = 1
    for i in range(2, n + 1):
        space *= i
        if space > limit:
            break
    if space <= limit:
        return [
            _chunk_layout(perm)
            for perm in itertools.permutations(component_ids)
        ]
    rng = random.Random(seed)
    seen: set[tuple[str, ...]] = set()
    candidates = []
    while len(candidates) < limit:
        order = list(component_ids)
        rng.shuffle(order)
        key = tuple(order)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(_chunk_layout(key))
    return candidates


def neighbour_layout(
    layout: tuple[tuple[tuple[str, ...], ...], ...],
    rng: random.Random,
) -> tuple[tuple[tuple[str, ...], ...], ...]:
    """Annealing neighbour: swap two components in the flattened order."""
    flat = [cid for page in layout for row in page for cid in row]
    if len(flat) < 2:
        return layout
    i, j = rng.sample(range(len(flat)), 2)
    flat[i], flat[j] = flat[j], flat[i]
    return _chunk_layout(tuple(flat))
