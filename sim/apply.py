"""sim/apply.py — the SOLE machine [A]-writer (design-spec §2.10.3).

Writes `manifest/layout/<subsystem>.lock.json` overlays addressing [A]
fields BY NAMESPACE ID; manifest source is never machine-mutated. Provenance
lives IN the overlay, per [A]-field-group: each entry stamps
SimRef(record_id, input_hash) or Exempt(reason) — the overlay being the sole
[A] writer, provenance travels with exactly what it describes, and
check_sim_gate reads it deterministically (auto-generated below-threshold
Exempts persist here too).

The loader rejects any overlay key not tagged [A] — a simulator bug can
corrupt layout but structurally cannot corrupt semantics, custom_ids, or
capability strings (no custom_id is ever derived from an [A] field, §2.4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sim.space import REPO_ROOT, a_tagged_fields

OVERLAY_DIR = REPO_ROOT / "manifest" / "layout"

__all__ = [
    "Exempt",
    "OverlayKeyRejected",
    "SimRef",
    "load_overlay",
    "load_all_overlays",
    "overlay_path",
    "write_overlay",
]


class OverlayKeyRejected(ValueError):
    """An overlay key does not address an [A]-tagged field."""


@dataclass(frozen=True)
class SimRef:
    record_id: str      # sim/records/<record_id>.json
    input_hash: str     # the record's snapshot input hash at write time

    def to_json(self) -> dict[str, str]:
        return {"sim_ref": {"record_id": self.record_id, "input_hash": self.input_hash}}


@dataclass(frozen=True)
class Exempt:
    reason: str

    def to_json(self) -> dict[str, str]:
        return {"exempt": self.reason}


def overlay_path(subsystem: str, overlay_dir: Path = OVERLAY_DIR) -> Path:
    return overlay_dir / f"{subsystem}.lock.json"


def _field_token(assignment_key: str) -> str:
    """'<subsystem>:<anchor>:<SpecType>.<field>[/...]' -> 'SpecType.field'."""
    tail = assignment_key.split(":", 2)[-1]
    leaf = tail.split("/")[-1]
    return leaf


def _validate_keys(entries: dict[str, Any]) -> None:
    allowed = a_tagged_fields()
    for key in entries:
        if _field_token(key) not in allowed:
            raise OverlayKeyRejected(
                f"overlay key {key!r} addresses {_field_token(key)!r}, which "
                f"is not role-tagged [A] — the patch format cannot express a "
                f"semantic mutation (design-spec §2.10.3)"
            )


def write_overlay(
    subsystem: str,
    entries: dict[str, dict[str, Any]],
    *,
    overlay_dir: Path = OVERLAY_DIR,
) -> Path:
    """entries: assignment_key -> {"value": ..., "provenance": SimRef|Exempt
    (or their to_json dict form)}. Every entry MUST carry provenance."""
    normalized: dict[str, dict[str, Any]] = {}
    for key, entry in entries.items():
        provenance = entry.get("provenance")
        if isinstance(provenance, (SimRef, Exempt)):
            provenance = provenance.to_json()
        if not isinstance(provenance, dict) or not (
            "sim_ref" in provenance or "exempt" in provenance
        ):
            raise ValueError(
                f"overlay entry {key!r} lacks SimRef/Exempt provenance "
                f"(§2.10.3: provenance travels with exactly what it describes)"
            )
        normalized[key] = {"value": entry.get("value"), "provenance": provenance}
    _validate_keys(normalized)
    path = overlay_path(subsystem, overlay_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "subsystem": subsystem, "entries": normalized}
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    return path


def load_overlay(path: Path) -> dict[str, dict[str, Any]]:
    """Load one overlay, REJECTING non-[A] keys (the compile-loader
    contract; manifest_compile adopts this loader when overlays arm)."""
    data = json.loads(path.read_text())
    entries = data.get("entries") or {}
    _validate_keys(entries)
    return entries


def load_all_overlays(overlay_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    overlay_dir = overlay_dir if overlay_dir is not None else OVERLAY_DIR
    merged: dict[str, dict[str, Any]] = {}
    if not overlay_dir.exists():
        return merged
    for path in sorted(overlay_dir.glob("*.lock.json")):
        merged.update(load_overlay(path))
    return merged
