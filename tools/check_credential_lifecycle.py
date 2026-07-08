#!/usr/bin/env python3
"""check_credential_lifecycle — the class-13 N-1 credential-lifecycle gate
(S13, frozen L0 spec 12 §2.A; mirrors check_data_lifecycle).

Over the ONE flat CREDENTIAL_REGISTRY:
  (1) every `revocation_ref` is a RevocationRef member (enum-typed — a
      credential with no declared kill-path is unconstructible AND CI-red);
  (2) `cadence_days is not None ⟺ rotation ∈ {AUTONOMOUS, OWNER_PROMPT}`
      (the two our-scheduled postures) and
      `cadence_days is None ⟺ rotation ∈ {MANAGED, ON_COMPROMISE}`;
  (3) machine-completeness both directions: every non-None `config_ref`
      names an existing credential-bearing CONFIG_FIELDS entry (type SECRET
      or DSN), AND every credential-bearing CONFIG_FIELDS entry is named by
      exactly one WORKER_ENV row;
  (4) the partition invariant `store == WORKER_ENV ⟺ config_ref is not None`;
  (5) registry names are unique (ONE flat inventory, no double rows).

A new worker secret cannot be added without a lifecycle row; no lifecycle
row can dangle a config that doesn't exist. Exit 0 = clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sb.spec.config import CONFIG_FIELDS, ConfigType  # noqa: E402
from sb.spec.credentials import (  # noqa: E402
    CREDENTIAL_REGISTRY,
    CredentialStore,
    RevocationRef,
    RotationPosture,
)

_CADENCE_POSTURES = (RotationPosture.AUTONOMOUS, RotationPosture.OWNER_PROMPT)


def _credential_bearing_env_vars() -> set[str]:
    """The 'SecretSpec subset' of CONFIG_FIELDS (spec 12 §2.A rule 3), read
    as every credential-bearing field: type SECRET or DSN (DATABASE_URL is a
    DSN-typed ConfigSpec, not a SecretSpec subclass — same credential class,
    ledgered interpretation D-0016)."""
    return {
        spec.env_var for spec in CONFIG_FIELDS
        if spec.type in (ConfigType.SECRET, ConfigType.DSN)
    }


def check(registry=CREDENTIAL_REGISTRY, config_fields=None) -> list[str]:
    problems: list[str] = []
    env_vars = (_credential_bearing_env_vars() if config_fields is None
                else {s.env_var for s in config_fields
                      if s.type in (ConfigType.SECRET, ConfigType.DSN)})
    seen: set[str] = set()
    worker_refs: dict[str, str] = {}
    for cred in registry:
        # (5) unique names
        if cred.name in seen:
            problems.append(f"{cred.name}: duplicate registry row")
        seen.add(cred.name)
        # (1) closed kill-path vocabulary
        if not isinstance(cred.revocation_ref, RevocationRef):
            problems.append(f"{cred.name}: revocation_ref must be a RevocationRef "
                            f"member, got {cred.revocation_ref!r}")
        # (2) cadence ⟺ posture
        if cred.rotation in _CADENCE_POSTURES and cred.cadence_days is None:
            problems.append(f"{cred.name}: rotation={cred.rotation.value} needs a "
                            f"cadence_days horizon")
        if cred.rotation not in _CADENCE_POSTURES and cred.cadence_days is not None:
            problems.append(f"{cred.name}: rotation={cred.rotation.value} must not "
                            f"carry cadence_days (platform-owned / event-driven)")
        # (4) partition invariant
        is_worker = cred.store is CredentialStore.WORKER_ENV
        if is_worker != (cred.config_ref is not None):
            problems.append(f"{cred.name}: store==WORKER_ENV ⟺ config_ref is not "
                            f"None violated (store={cred.store.value}, "
                            f"config_ref={cred.config_ref!r})")
        # (3a) config_ref names an existing credential-bearing field, once
        if cred.config_ref is not None:
            if cred.config_ref not in env_vars:
                problems.append(f"{cred.name}: config_ref {cred.config_ref!r} names "
                                f"no credential-bearing CONFIG_FIELDS entry")
            elif cred.config_ref in worker_refs:
                problems.append(f"{cred.name}: config_ref {cred.config_ref!r} already "
                                f"claimed by {worker_refs[cred.config_ref]!r}")
            worker_refs.setdefault(cred.config_ref, cred.name)
    # (3b) every credential-bearing config field has exactly one WORKER_ENV row
    for env_var in sorted(env_vars - set(worker_refs)):
        problems.append(f"CONFIG_FIELDS.{env_var}: credential-bearing field with no "
                        f"CREDENTIAL_REGISTRY WORKER_ENV row (a worker secret cannot "
                        f"exist without a declared lifecycle)")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_credential_lifecycle: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"check_credential_lifecycle: OK ({len(CREDENTIAL_REGISTRY)} credentials, "
          f"{len(_credential_bearing_env_vars())} worker credential fields covered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
