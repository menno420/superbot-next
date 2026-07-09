"""Project Moon (Limbus) deterministic data loader — shipped
``services/projmoon_data_service.py`` @7f7628e1 VERBATIM over the
committed structural/lore fixtures (``sb/domain/projmoon/data/``): the
12 Sinners, 7 Sins, 3 damage types, 5 E.G.O grades, 13 mechanics, 8
statuses. The fragile exact-number StaticData ingest stays a named
successor lane (shipped plan Slice A item 1 — D-0047).

Stdlib-only; loading is synchronous, lazy, cached; ``reset_cache()`` is
the test seam."""

from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parent / "data"

# fixture filename -> the entity_kind it must declare.
_FILES: dict[str, str] = {
    "sinners.json": "sinner",
    "sins.json": "sin",
    "damage_types.json": "damage_type",
    "mechanics.json": "mechanic",
    "ego_grades.json": "ego_grade",
    "statuses.json": "status",
}

KIND_LABELS: dict[str, str] = {
    "sinner": "Sinners",
    "sin": "Sins",
    "damage_type": "Damage types",
    "mechanic": "Mechanics",
    "ego_grade": "E.G.O grades",
    "status": "Statuses",
}

_EXTRA_FIELDS: dict[str, tuple[str, ...]] = {
    "sinner": ("literary_origin",),
    "sin": ("color",),
    "ego_grade": ("rank",),
    "mechanic": ("category",),
}


class LimbusDataValidationError(ValueError):
    """Raised when a Limbus fixture file fails validation."""


@dataclass(frozen=True)
class LimbusEntry:
    """One typed Limbus fact (a Sinner, Sin, damage type, grade, status)."""

    id: str
    canonical: str
    aliases: tuple[str, ...]
    entity_kind: str
    description: str
    extra: dict[str, Any] = field(default_factory=dict)


_lock = threading.Lock()
_cache: dict[str, tuple[LimbusEntry, ...]] | None = None


def reset_cache() -> None:
    """Drop the cached datasets so the next accessor reloads from disk."""
    global _cache
    with _lock:
        _cache = None


def _load_file(filename: str, expected_kind: str) -> tuple[LimbusEntry, ...]:
    path = DATA_ROOT / filename
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise LimbusDataValidationError(f"missing fixture: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LimbusDataValidationError(f"invalid JSON in {filename}: {exc}") from exc

    for key in ("data_version", "game_version", "source", "entity_kind", "entries"):
        if key not in raw:
            raise LimbusDataValidationError(
                f"{filename}: missing top-level key {key!r}",
            )
    if raw["entity_kind"] != expected_kind:
        raise LimbusDataValidationError(
            f"{filename}: entity_kind {raw['entity_kind']!r} != "
            f"expected {expected_kind!r}",
        )

    entries: list[LimbusEntry] = []
    seen_canonical: dict[str, str] = {}
    seen_alias: dict[str, str] = {}
    for item in raw["entries"]:
        for key in ("id", "canonical", "description"):
            if not item.get(key):
                raise LimbusDataValidationError(
                    f"{filename}: entry {item.get('id', '?')!r} missing {key!r}",
                )
        canonical = item["canonical"]
        canon_key = canonical.casefold()
        if canon_key in seen_canonical:
            raise LimbusDataValidationError(
                f"{filename}: duplicate canonical {canonical!r}",
            )
        seen_canonical[canon_key] = canonical

        aliases = tuple(dict.fromkeys(a.casefold() for a in item.get("aliases", [])))
        for alias in aliases:
            if alias in seen_canonical or alias == canon_key:
                raise LimbusDataValidationError(
                    f"{filename}: alias {alias!r} collides with a canonical name",
                )
            if alias in seen_alias:
                raise LimbusDataValidationError(
                    f"{filename}: alias {alias!r} used by {seen_alias[alias]!r} "
                    f"and {canonical!r}",
                )
            seen_alias[alias] = canonical

        extra = {
            key: item[key]
            for key in _EXTRA_FIELDS.get(expected_kind, ())
            if key in item
        }
        origin = extra.get("literary_origin")
        if origin is not None and (
            not isinstance(origin, dict)
            or not origin.get("work")
            or not origin.get("author")
        ):
            raise LimbusDataValidationError(
                f"{filename}: entry {item['id']!r} literary_origin must be a "
                "mapping with non-empty 'work' and 'author'",
            )
        entries.append(
            LimbusEntry(
                id=item["id"],
                canonical=canonical,
                aliases=aliases,
                entity_kind=expected_kind,
                description=item["description"],
                extra=extra,
            ),
        )
    return tuple(entries)


def _datasets() -> dict[str, tuple[LimbusEntry, ...]]:
    global _cache
    with _lock:
        if _cache is None:
            _cache = {
                kind: _load_file(filename, kind)
                for filename, kind in _FILES.items()
            }
        return _cache


def entity_kinds() -> tuple[str, ...]:
    """The entity kinds this domain knows, in display order."""
    return tuple(_FILES.values())


def get_entries(kind: str) -> tuple[LimbusEntry, ...]:
    """All entries of ``kind`` (raises if the kind is unknown)."""
    datasets = _datasets()
    if kind not in datasets:
        raise KeyError(f"unknown Limbus entity kind: {kind!r}")
    return datasets[kind]


def all_entries() -> tuple[LimbusEntry, ...]:
    """Every Limbus entry across all kinds (kind order, then file order)."""
    datasets = _datasets()
    out: list[LimbusEntry] = []
    for kind in _FILES.values():
        out.extend(datasets[kind])
    return tuple(out)


@dataclass(frozen=True)
class SinnerOrigin:
    """A Sinner paired with the literary work it is drawn from."""

    canonical: str
    work: str
    author: str


def sinner_origins() -> tuple[SinnerOrigin, ...]:
    """The 12 Sinners paired with their source work + author."""
    out: list[SinnerOrigin] = []
    for entry in get_entries("sinner"):
        origin = entry.extra.get("literary_origin")
        if isinstance(origin, dict) and origin.get("work") and origin.get("author"):
            out.append(
                SinnerOrigin(
                    canonical=entry.canonical,
                    work=str(origin["work"]),
                    author=str(origin["author"]),
                ),
            )
    return tuple(out)


def resolve(text: str, *, kind: str | None = None) -> LimbusEntry | None:
    """Resolve free text to a single Limbus entry (whole-token; the
    longest matched token wins — "Don Quixote" beats a bare "don")."""
    needle = f" {text.casefold()} "
    candidates: Sequence[LimbusEntry] = (
        get_entries(kind) if kind is not None else all_entries()
    )
    best: LimbusEntry | None = None
    best_len = 0
    for entry in candidates:
        tokens = (entry.canonical.casefold(), *entry.aliases)
        for token in tokens:
            if f" {token} " in needle and len(token) > best_len:
                best, best_len = entry, len(token)
    return best


__all__ = [
    "DATA_ROOT",
    "KIND_LABELS",
    "LimbusDataValidationError",
    "LimbusEntry",
    "SinnerOrigin",
    "all_entries",
    "entity_kinds",
    "get_entries",
    "reset_cache",
    "resolve",
    "sinner_origins",
]
