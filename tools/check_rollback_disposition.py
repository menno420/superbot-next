#!/usr/bin/env python3
"""check_rollback_disposition — the `rollback_class_resolved` +
reverse-importer-coverage fence (S14, frozen L0 spec 13 §2.5; sits beside
check_data_lifecycle over the same store walk).

Over EVERY registered StoreSpec (kernel constants + manifest `stores`):
  (a) rollback_class RESOLVES — the store declares a `forward_map_kind` or
      one is derivable (checkpoint_class==SESSION ⇒ COLLAPSE; a
      store_retirements.yml entry ⇒ DROP). Unresolved =
      SEMANTIC_VIOLATION("rollback_class_unresolved") — you cannot ship a
      store whose rollback-data disposition is unstated (T-4).
  (b) `replay_intent=True` only NARROWS: it is illegal on a store that is
      not otherwise REVERSE_IMPORTABLE (non-invertible or not value-bearing).
  (c) the reverse importer's covered set == the derived REVERSE_IMPORTABLE
      set, BOTH directions — a REVERSE_IMPORTABLE store the importer doesn't
      cover, or a covered store that isn't REVERSE_IMPORTABLE, is
      SEMANTIC_VIOLATION("reverse_importer_coverage_gap").

Exit 0 = clean.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# import the kernel store owners so their register_store calls run.
import sb.kernel.db.credentials  # noqa: E402,F401
import sb.kernel.db.draft  # noqa: E402,F401
import sb.kernel.db.idempotency  # noqa: E402,F401
import sb.kernel.db.invariants  # noqa: E402,F401
import sb.kernel.db.scheduler  # noqa: E402,F401
import sb.kernel.outbox.store  # noqa: E402,F401
import sb.kernel.workflow.audit  # noqa: E402,F401
from sb.spec.versioning import (  # noqa: E402
    INVERTIBLE_MAP_KINDS,
    RollbackClass,
    RollbackUnresolved,
    derive_rollback_class,
    registered_stores,
    resolve_forward_map_kind,
)
from tools.importer.reverse import reverse_importer_coverage  # noqa: E402

RETIREMENTS_PATH = REPO_ROOT / "sb" / "namespace" / "store_retirements.yml"


def _retired_tables() -> frozenset[str]:
    try:
        import yaml
        data = yaml.safe_load(RETIREMENTS_PATH.read_text()) or {}
        return frozenset(e["table"] for e in (data.get("retirements") or []))
    except FileNotFoundError:
        return frozenset()


def _load_manifest_stores() -> None:
    import sb.manifest as manifest_pkg
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        importlib.import_module(f"sb.manifest.{info.name}")


def check(stores=None, *, covered: frozenset[str] | None = None,
          retired_tables: frozenset[str] | None = None) -> list[str]:
    if stores is None:
        _load_manifest_stores()
        stores = registered_stores()
    if covered is None:
        covered = reverse_importer_coverage()
    if retired_tables is None:
        retired_tables = _retired_tables()
    problems: list[str] = []
    reverse_set: set[str] = set()
    for store in stores:
        # (a) rollback_class_resolved
        try:
            rc = derive_rollback_class(store, retired_tables=retired_tables)
        except RollbackUnresolved as exc:
            problems.append(str(exc))
            continue
        # (b) replay_intent only ever narrows
        kind = resolve_forward_map_kind(store, retired_tables=retired_tables)
        if store.replay_intent and (kind not in INVERTIBLE_MAP_KINDS
                                    or not store.bears_value):
            problems.append(
                f"{store.table}: replay_intent is a NARROWING override on an "
                f"otherwise-REVERSE_IMPORTABLE store only (kind="
                f"{kind.value if kind else None}, bears_value={store.bears_value})")
        if rc is RollbackClass.REVERSE_IMPORTABLE:
            reverse_set.add(store.table)
    # (c) coverage both directions
    for table in sorted(reverse_set - covered):
        problems.append(f"{table}: REVERSE_IMPORTABLE but no reverse importer "
                        f"registered (reverse_importer_coverage_gap)")
    for table in sorted(covered - reverse_set):
        problems.append(f"{table}: reverse importer registered but the store "
                        f"derives {'{'}not REVERSE_IMPORTABLE{'}'} "
                        f"(reverse_importer_coverage_gap)")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_rollback_disposition: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    stores = registered_stores()
    print(f"check_rollback_disposition: OK ({len(stores)} store(s) resolved; "
          f"{len(reverse_importer_coverage())} reverse-importer(s) covering the "
          f"derived REVERSE_IMPORTABLE set)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
