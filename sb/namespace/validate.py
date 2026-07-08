"""The one shared CI <=> merge-tree <=> boot oracle (frozen L0 spec 03 §3.2).

`validate(snapshot) -> NamespaceReport` is a pure function of committed data:
the projected snapshot dict + `legacy_reservations.json` + `tombstones.json`.
CI (`tools/check_namespace.py`), the `git merge-tree` re-validation, and the
compiler's P3 pass at boot leg-A all call THIS function on the SAME data —
CI-green <=> boot-green by construction (Q-0120; the #763 false-green class).

Snapshot corpus shape (K1-REQUIRED on the compiler, spec 03 §4.2):
`snapshot["projections"]["namespace"]` maps kind -> list of nodes. Command
nodes carry `{value, kind: "command", surface in {prefix,slash},
parent_group: str|None, subsystem, source}`; both surfaces are carried and
subcommands are expanded. Non-command nodes carry `{value, subsystem, source}`.

Deterministic, collect-all: every violation is emitted with named claimants.
Imports neither sb/spec nor manifests — pure data in, report out.
"""

from __future__ import annotations

import json
from pathlib import Path

from sb.namespace.index import IndexKey, ReservationIndex
from sb.namespace.kinds import CommandScope, NamespaceKind, Origin, Surface, normalize
from sb.namespace.records import (
    CapViolation,
    Collision,
    FormatError,
    NamespaceReport,
    ReservationRecord,
)

_PKG_DIR = Path(__file__).resolve().parent
DEFAULT_LEGACY_PATH = str(_PKG_DIR / "legacy_reservations.json")
DEFAULT_TOMBSTONE_PATH = str(_PKG_DIR / "tombstones.json")

# Committed in legacy_reservations.json; loaded per-validate (kept here as the
# documented default so the rule is visible next to its enforcement).
_CAPABILITY_PARTS = 3

# Slash-surface caps (Discord): spec 03 §3.5. Context-menu caps are reserved
# but dormant (zero context-menu commands in the harvested corpus).
CAP_TOP_LEVEL = 100
CAP_SUB = 25
CAP_NEST = 1


def _scope_from_json(raw: dict | None) -> CommandScope | None:
    if not raw:
        return None
    return CommandScope(Surface(raw["surface"]), raw.get("parent_group"))


def _claim(
    by_key: dict[IndexKey, ReservationRecord],
    collisions: list[Collision],
    record: ReservationRecord,
) -> None:
    """Insert one reservation, applying the cross-origin collision rules."""
    key: IndexKey = (record.kind, record.value, record.scope)
    existing = by_key.get(key)
    if existing is None:
        by_key[key] = record
        return

    # Cross-origin rules (spec 03 §3.2 step 2):
    if record.origin is Origin.MANIFEST and existing.origin is Origin.LEGACY:
        if existing.owner == record.owner:
            by_key[key] = record  # compat claimable only by its recorded owner
            return
        detail = "legacy_owner_mismatch"
    elif record.origin is Origin.LEGACY and existing.origin is Origin.MANIFEST:
        if existing.owner == record.owner:
            return
        detail = "legacy_owner_mismatch"
    elif Origin.TOMBSTONE in (record.origin, existing.origin):
        tomb = record if record.origin is Origin.TOMBSTONE else existing
        renamed = f" (renamed to {tomb.renamed_to})" if tomb.renamed_to else ""
        detail = f"reserved_tombstone{renamed}"
    elif Origin.BAN in (record.origin, existing.origin):
        detail = "banned_name"
    else:
        detail = None  # plain duplicate claim (manifest x manifest, legacy x legacy)

    collisions.append(Collision(
        kind=record.kind,
        value=record.value,
        scope=record.scope,
        claimant_a=existing.source,
        claimant_b=record.source,
        detail=detail,
    ))


def _format_errors(
    by_key: dict[IndexKey, ReservationRecord],
    prefix_owners: dict[str, str],
) -> list[FormatError]:
    """P3-owned capability STRING identity checks (spec 03 §3.2 step 3).

    P3 owns format + reserved-prefix owner; the compiler's P4 owns lane
    resolution (the P3/P4 split, spec 03 decision 10).
    """
    errors: list[FormatError] = []
    for (kind, value, _scope), record in by_key.items():
        if kind is not NamespaceKind.CAPABILITY:
            continue
        parts = value.split(".")
        if len(parts) != _CAPABILITY_PARTS or not all(parts):
            errors.append(FormatError(kind, value, "capability_not_3_part"))
            continue
        head = parts[0]
        if head in prefix_owners and record.owner != prefix_owners[head]:
            errors.append(FormatError(kind, value, "reserved_prefix_misuse"))
    return errors


def _cap_violations(by_key: dict[IndexKey, ReservationRecord]) -> list[CapViolation]:
    """The compile guard: pure count-and-compare over the slash partition
    (spec 03 §3.5). Never auto-demotes, never reads a ranking field."""
    violations: list[CapViolation] = []
    top_level: set[str] = set()          # distinct top-level slash names (a group counts once)
    children: dict[str, set[str]] = {}   # group path -> direct children
    deep: list[str] = []                 # nest_1 violations

    for (kind, value, scope) in by_key:
        if kind is not NamespaceKind.COMMAND or scope is None or scope.surface is not Surface.SLASH:
            continue
        parent = scope.parent_group
        if parent is None:
            top_level.add(value)
        else:
            segments = parent.split(".")
            if len(segments) > 2:  # root -> group -> subgroup -> leaf = too deep
                deep.append(f"{parent}/{value}")
            top_level.add(segments[0])  # the grouped family counts as ONE top-level name
            children.setdefault(parent, set()).add(value)
            # a subcommand-group is itself a direct child of its parent group
            if len(segments) == 2:
                children.setdefault(segments[0], set()).add(segments[1])

    if len(top_level) > CAP_TOP_LEVEL:
        violations.append(CapViolation(
            cap="top_level_100", locus="", count=len(top_level), limit=CAP_TOP_LEVEL,
            members=tuple(sorted(top_level)),
        ))
    for group, kids in sorted(children.items()):
        if len(kids) > CAP_SUB:
            violations.append(CapViolation(
                cap="sub_25", locus=group, count=len(kids), limit=CAP_SUB,
                members=tuple(sorted(kids)),
            ))
    if deep:
        violations.append(CapViolation(
            cap="nest_1", locus="", count=len(deep), limit=CAP_NEST,
            members=tuple(sorted(deep)),
        ))
    return violations


def validate(
    snapshot: dict,
    *,
    legacy_path: str = DEFAULT_LEGACY_PATH,
    tombstone_path: str = DEFAULT_TOMBSTONE_PATH,
) -> NamespaceReport:
    """Build the index from the three pure-data origins and report every
    collision / cap violation / format error (deterministic, collect-all)."""
    by_key: dict[IndexKey, ReservationRecord] = {}
    collisions: list[Collision] = []

    # Origin 1: the frozen compat core (legacy), loaded first.
    legacy_doc = json.loads(Path(legacy_path).read_text(encoding="utf-8"))
    prefix_owners: dict[str, str] = legacy_doc.get("reserved_prefix_owners", {})
    for row in legacy_doc.get("reservations", []):
        kind = NamespaceKind(row["kind"])
        _claim(by_key, collisions, ReservationRecord(
            kind=kind,
            value=normalize(row["value"], kind),
            scope=_scope_from_json(row.get("scope")),
            origin=Origin.LEGACY,
            owner=row.get("owner"),
            spec_id=None,
            source=row.get("source", "legacy_reservations.json"),
        ))

    # Origin 2: tombstones + bans (append-only committed data).
    tomb_doc = json.loads(Path(tombstone_path).read_text(encoding="utf-8"))
    for section, origin in (("tombstones", Origin.TOMBSTONE), ("bans", Origin.BAN)):
        for row in tomb_doc.get(section, []):
            kind = NamespaceKind(row["kind"])
            _claim(by_key, collisions, ReservationRecord(
                kind=kind,
                value=normalize(row["value"], kind),
                scope=_scope_from_json(row.get("scope")),
                origin=origin,
                owner=None,
                spec_id=None,
                source=row.get("provenance", "tombstones.json"),
                renamed_to=row.get("renamed_to"),
                reason=row.get("reason"),
            ))

    # Origin 3: the manifest-derived corpus (the snapshot projection).
    namespace_proj = (snapshot.get("projections") or {}).get("namespace") or {}
    for kind_name, nodes in sorted(namespace_proj.items()):
        kind = NamespaceKind(kind_name)
        for node in nodes:
            scope = None
            if kind is NamespaceKind.COMMAND:
                scope = CommandScope(Surface(node["surface"]), node.get("parent_group"))
            _claim(by_key, collisions, ReservationRecord(
                kind=kind,
                value=normalize(node["value"], kind),
                scope=scope,
                origin=Origin.MANIFEST,
                owner=node.get("subsystem"),
                spec_id=node.get("spec_id"),
                source=f"{node.get('subsystem', '?')}@{node.get('source', '?')}",
            ))

    format_errors = _format_errors(by_key, prefix_owners)
    cap_violations = _cap_violations(by_key)
    index = ReservationIndex(by_key)
    ok = not collisions and not cap_violations and not format_errors
    return NamespaceReport(
        ok=ok,
        collisions=tuple(collisions),
        cap_violations=tuple(cap_violations),
        format_errors=tuple(format_errors),
        index=index,
    )
