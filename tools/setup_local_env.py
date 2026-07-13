#!/usr/bin/env python3
"""setup_local_env — idempotent local-Postgres provisioning for verification.

The NEXT-2 baton's "local-Postgres env-drift hygiene" item
(control/status.md @ 0a96960): local clusters drift — containers restart
and wipe them, sessions re-derive role/DB/env provisioning by hand and
misread the resulting failures as code regressions (the "11 known-red
integration tests" episode: .sessions/2026-07-12-live-adapter-landing.md
⟲ review). This script makes the local cluster match what CI declares,
so `pytest tests/` + `run_golden_parity.py --gate` + `pytest
tests/integration` behave the same locally as in the workflows.

Canonical values are DERIVED from the CI workflows (never invent here):

  * role `parity` / password `parity` / DB `parity_replay`
    — .github/workflows/golden-parity.yml:44-46 (and named-gates.yml's
    golden-parity job): POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB.
  * env DATABASE_URL / SB_DATA_PLANE=test / SB_TEST_DB_HOSTS=localhost
    — .github/workflows/golden-parity.yml:52-54; the same triple is the
    harness default (sb/adapters/parity/boot.py:68-70 _ENV_DEFAULTS).
  * role `superbot` / DB `superbot` — NOT a CI value: the local
    runtime-boot convention for live-drive / runtime-smoke sessions
    (.sessions/2026-07-12-order-016-runtime-smoke.md provisioned
    "parity/parity_replay/superbot"). Provisioned too so a runtime boot
    (docs/operations/live-drive-guild-effects.md) has a DSN target.

Guarantees:

  * IDEMPOTENT — safe to run any number of times; the second run is a
    no-op that reports "exists".
  * NEVER DESTRUCTIVE — no DROP of anything, ever. Existing roles, DBs
    and rows are left untouched. The ONLY mutation applied to a
    pre-existing object is `ALTER ROLE ... PASSWORD` and only when the
    canonical DSN fails to authenticate (announced when it happens).
  * Migrations are NOT applied here — the parity harness applies (and
    truncates) its own schema at boot; the runtime boot applies its own.

Run: python3 tools/setup_local_env.py         (provision + print exports)
     python3 tools/setup_local_env.py --check (report only, mutate nothing)

Exit 0 = cluster reachable + all four objects present + DSNs authenticate;
exit 1 = something could not be provisioned (message says what).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

# CI-canonical (golden-parity.yml:44-46,52-54 / named-gates.yml).
PARITY_ROLE = "parity"
PARITY_PASSWORD = "parity"  # CI service-container value; local-only cluster
PARITY_DB = "parity_replay"
PARITY_DSN = "postgresql://parity:parity@localhost:5432/parity_replay"

# Local runtime-boot convention (order-016 card; not a CI value).
RUNTIME_ROLE = "superbot"
RUNTIME_PASSWORD = "superbot"
RUNTIME_DB = "superbot"
RUNTIME_DSN = "postgresql://superbot:superbot@localhost:5432/superbot"

ENV_EXPORTS = f"""\
export DATABASE_URL='{PARITY_DSN}'
export SB_DATA_PLANE=test
export SB_TEST_DB_HOSTS=localhost"""


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd="/", **kw)


def _admin_psql(sql: str) -> subprocess.CompletedProcess:
    """Run SQL as the cluster superuser. Peer-auth via the postgres OS
    user (the stock Debian/Ubuntu cluster shape); plain `psql` when we
    already ARE postgres."""
    base = ["psql", "--no-psqlrc", "-qAt", "-v", "ON_ERROR_STOP=1", "-c", sql]
    try:
        import pwd
        am_postgres = pwd.getpwuid(os.geteuid()).pw_name == "postgres"
    except (ImportError, KeyError):
        am_postgres = False
    if am_postgres:
        return _run(base)
    if shutil.which("sudo"):
        return _run(["sudo", "-u", "postgres"] + base)
    return _run(base)  # last resort: current user may be a superuser


def cluster_reachable() -> bool:
    if not shutil.which("pg_isready"):
        return False
    return _run(["pg_isready", "-h", "localhost", "-p", "5432"]).returncode == 0


def try_start_cluster() -> None:
    """Best-effort start of a stopped Debian/Ubuntu cluster (the
    container-restart case the ORDER-004 card hit). Never fatal."""
    if not shutil.which("pg_lsclusters") or not shutil.which("pg_ctlcluster"):
        return
    out = _run(["pg_lsclusters", "--no-header"]).stdout
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 4 and cols[3] != "online":
            version, name = cols[0], cols[1]
            if re.fullmatch(r"[0-9]+", version) and re.fullmatch(r"\w+", name):
                print(f"setup_local_env: starting cluster {version}/{name} ...")
                cmd = ["pg_ctlcluster", version, name, "start"]
                if os.geteuid() != 0 and shutil.which("sudo"):
                    cmd = ["sudo"] + cmd
                res = _run(cmd)
                if res.returncode != 0:
                    print(f"setup_local_env: start failed: "
                          f"{res.stderr.strip()}", file=sys.stderr)


def _exists(sql: str) -> bool:
    res = _admin_psql(sql)
    if res.returncode != 0:
        raise RuntimeError(f"admin psql failed: {res.stderr.strip()}")
    return res.stdout.strip() == "1"


def role_exists(role: str) -> bool:
    return _exists(
        f"SELECT 1 FROM pg_roles WHERE rolname = '{role}'")


def db_exists(db: str) -> bool:
    return _exists(
        f"SELECT 1 FROM pg_database WHERE datname = '{db}'")


def dsn_authenticates(dsn: str) -> bool:
    return _run(["psql", "--no-psqlrc", "-qAt", dsn,
                 "-c", "SELECT 1"]).returncode == 0


def ensure(role: str, password: str, db: str, dsn: str, check_only: bool,
           problems: list[str]) -> None:
    """Create role+DB only if missing; align the password only if the
    canonical DSN cannot authenticate. Nothing is ever dropped."""
    if role_exists(role):
        print(f"setup_local_env: role {role!r} exists")
    elif check_only:
        problems.append(f"role {role!r} missing")
    else:
        res = _admin_psql(
            f"CREATE ROLE {role} LOGIN PASSWORD '{password}'")
        if res.returncode != 0:
            problems.append(f"CREATE ROLE {role} failed: {res.stderr.strip()}")
            return
        print(f"setup_local_env: role {role!r} CREATED")

    if db_exists(db):
        print(f"setup_local_env: database {db!r} exists")
    elif check_only:
        problems.append(f"database {db!r} missing")
    else:
        res = _admin_psql(f'CREATE DATABASE {db} OWNER {role}')
        if res.returncode != 0:
            problems.append(
                f"CREATE DATABASE {db} failed: {res.stderr.strip()}")
            return
        print(f"setup_local_env: database {db!r} CREATED (owner {role})")

    if db_exists(db) and not dsn_authenticates(dsn):
        if check_only:
            problems.append(f"DSN for {db!r} does not authenticate")
            return
        print(f"setup_local_env: DSN auth failed for {db!r} — aligning "
              f"role {role!r} password to the canonical value")
        res = _admin_psql(
            f"ALTER ROLE {role} WITH LOGIN PASSWORD '{password}'")
        if res.returncode != 0 or not dsn_authenticates(dsn):
            problems.append(
                f"DSN for {db!r} still does not authenticate "
                f"({res.stderr.strip() or 'after password align'})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="report state only; mutate nothing")
    args = ap.parse_args()

    if not shutil.which("psql"):
        print("setup_local_env: psql not found — install the postgresql "
              "client/server packages first", file=sys.stderr)
        return 1

    if not cluster_reachable():
        if not args.check:
            try_start_cluster()
        if not cluster_reachable():
            print("setup_local_env: no Postgres reachable on "
                  "localhost:5432 (pg_isready failed). Start your cluster "
                  "(Debian/Ubuntu: pg_ctlcluster <ver> main start) and "
                  "re-run.", file=sys.stderr)
            return 1
    print("setup_local_env: cluster reachable on localhost:5432")

    problems: list[str] = []
    ensure(PARITY_ROLE, PARITY_PASSWORD, PARITY_DB, PARITY_DSN,
           args.check, problems)
    ensure(RUNTIME_ROLE, RUNTIME_PASSWORD, RUNTIME_DB, RUNTIME_DSN,
           args.check, problems)

    if problems:
        for p in problems:
            print(f"setup_local_env: PROBLEM — {p}", file=sys.stderr)
        return 1

    print()
    print("setup_local_env: OK — parity + runtime targets provisioned and "
          "authenticating.")
    print("Env for the CI-shaped verification path "
          "(golden-parity.yml:52-54):")
    print()
    print(ENV_EXPORTS)
    print()
    print(f"# runtime-boot DSN (live-drive / runtime smoke): {RUNTIME_DSN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
