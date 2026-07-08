#!/usr/bin/env python3
"""check_data_lifecycle — the class-12 retention/erasure gate (S11, frozen
L0 spec 10 §2.A).

Over EVERY registered StoreSpec (kernel constants + manifest `stores`
facets):
  (a) every `data_class != NONE` store carries a non-empty `retention` AND a
      non-empty `erasure_ref`;
  (b) every cache declares a `cache_scope`, and a member-data cache is
      GUILD-scoped (closes the B#34/X-3 cross-guild bleed by construction);
  (c) the `erasure_ref` is a WorkflowRef (a bare HandlerRef bypassing the
      audited seam is a SEMANTIC_VIOLATION — erasure IS an auditable
      mutation).

A member-data store with no erasure hook is CI-red. Exit 0 = clean.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# import the kernel store owners so their register_store calls run.
import sb.kernel.db.draft  # noqa: E402,F401
import sb.kernel.db.idempotency  # noqa: E402,F401
import sb.kernel.db.scheduler  # noqa: E402,F401
import sb.kernel.outbox.store  # noqa: E402,F401
import sb.kernel.workflow.audit  # noqa: E402,F401
from sb.spec.refs import WorkflowRef  # noqa: E402
from sb.spec.versioning import CacheScope, DataClass, registered_stores  # noqa: E402


def _load_manifest_stores() -> None:
    import sb.manifest as manifest_pkg
    for info in pkgutil.iter_modules(manifest_pkg.__path__):
        importlib.import_module(f"sb.manifest.{info.name}")


def check(stores=None) -> list[str]:
    if stores is None:
        _load_manifest_stores()
        stores = registered_stores()
    problems: list[str] = []
    for store in stores:
        member_data = store.data_class is not DataClass.NONE
        if member_data:
            if not store.retention:
                problems.append(f"{store.table}: data_class="
                                f"{store.data_class.value} with no retention window")
            if store.erasure_ref is None:
                problems.append(f"{store.table}: data_class="
                                f"{store.data_class.value} with no erasure_ref "
                                f"(un-erasable personal data is CI-red)")
            elif not isinstance(store.erasure_ref, WorkflowRef):
                problems.append(f"{store.table}: erasure_ref must be a WorkflowRef "
                                f"(the audited seam) — got "
                                f"{type(store.erasure_ref).__name__}")
        if store.is_cache:
            if store.cache_scope is None:
                problems.append(f"{store.table}: a cache must declare cache_scope")
            elif member_data and store.cache_scope is not CacheScope.GUILD:
                problems.append(f"{store.table}: a member-data cache must be "
                                f"GUILD-scoped (cross-guild bleed, X-3)")
        elif store.cache_scope is not None:
            problems.append(f"{store.table}: cache_scope declared on a non-cache "
                            f"(set is_cache=True or drop the scope)")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_data_lifecycle: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"check_data_lifecycle: clean ({len(registered_stores())} store(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
