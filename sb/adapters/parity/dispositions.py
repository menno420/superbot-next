"""Corpus-red dispositions (flag 13 — ruled by ORDER 009 / Q-0262.3).

The three owner-accepted "old bot vs new bot output differs forever" classes
are applied HERE, at replay-diff time, to BOTH the stored golden and the
fresh capture — symmetrically, so the diff stays honest for every other
byte and a later behavior change on either side of a disposed surface still
cannot smuggle itself through (both docs get the same treatment).

Encodings live as data in ``parity/parity.yml`` (`dispositions:` section);
this module is the mechanism. The goldens themselves are NEVER rewritten
(parity/README.md integrity rule) and the imported harness stays verbatim.
Decision record: docs/parity/flag-13-disposition-2026-07-10.md.
"""

from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = ["apply_dispositions", "load_dispositions"]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PARITY_YML = _REPO_ROOT / "parity" / "parity.yml"


@lru_cache(maxsize=1)
def load_dispositions() -> dict[str, Any]:
    """The parity.yml `dispositions` section with kernel-scope indirection
    resolved (tables/events: `kernel` -> the kernel coverage-home lists)."""
    import yaml

    doc = yaml.safe_load(_PARITY_YML.read_text()) or {}
    dispositions = dict(doc.get("dispositions") or {})
    kernel = doc.get("kernel") or {}
    drift = dispositions.get("kernel-surface-drift")
    if drift:
        if drift.get("tables") == "kernel":
            drift["tables"] = list(kernel.get("tables") or [])
        if drift.get("events") == "kernel":
            drift["events"] = list(kernel.get("events") or [])
    return dispositions


def _drop_kernel_surfaces(doc: dict[str, Any], tables: list[str],
                          events: list[str]) -> None:
    delta = doc.get("db_delta")
    if isinstance(delta, dict):
        for table in tables:
            delta.pop(table, None)
    for step in doc.get("steps") or []:
        raw = step.get("events")
        if not isinstance(raw, list):
            continue
        kept = [e for e in raw if e.get("event") not in events]
        if kept:
            step["events"] = kept
        else:
            step.pop("events", None)


def _drop_alias_column(doc: dict[str, Any], table: str, column: str) -> None:
    entry = (doc.get("db_delta") or {}).get(table)
    if not isinstance(entry, dict):
        return
    for rows in entry.values():
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    row.pop(column, None)


def _drop_exempt_calls(doc: dict[str, Any], method: str,
                       reasonless_only: bool) -> None:
    for step in doc.get("steps") or []:
        calls = step.get("calls")
        if not isinstance(calls, list):
            continue
        step["calls"] = [
            c for c in calls
            if not (c.get("method") == method
                    and (not reasonless_only
                         or (c.get("args") or {}).get("reason") is None))
        ]


def apply_dispositions(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of a golden document with every ruled disposition
    applied. Call on BOTH expected and actual before diffing."""
    dispositions = load_dispositions()
    out = copy.deepcopy(doc)
    drift = dispositions.get("kernel-surface-drift")
    if drift and drift.get("encoding") == "normalizer":
        _drop_kernel_surfaces(out, list(drift.get("tables") or []),
                              list(drift.get("events") or []))
    alias = dispositions.get("xp-coins-alias")
    if alias and alias.get("encoding") == "normalizer":
        _drop_alias_column(out, str(alias.get("table") or "xp"),
                           str(alias.get("column") or "coins"))
    deletion = dispositions.get("invoking-message-deletion")
    if deletion and deletion.get("encoding") == "exemption":
        _drop_exempt_calls(out, str(deletion.get("method") or "delete_message"),
                           bool(deletion.get("reasonless_only", True)))
    return out
