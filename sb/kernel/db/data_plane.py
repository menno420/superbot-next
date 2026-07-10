"""The 4th kernel rail — the data-plane guard (L-10, frozen L0 spec 05 §3.5).

Refuse boot on any DSN not provably safe for THIS bot. Runs inside
`preflight()`, before `db.init`. Reads only declared Config attributes (no raw
getenv — `check_config_usage` applies to this module too). Pure stdlib: no
asyncpg dependency, which is why it can land at K0/S1 while the rest of
`sb/kernel/db` lands at K3/S4.

Prod-attest custody note: `SB_PROD_ATTEST` is presence-gated (present =>
attested). The durable custody mechanism (plain env token vs sealed secret vs
OIDC claim) is owner-gated CUT-1 ops work — flagged for owner, not decided
here (spec 05 §9).
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlsplit

from sb.kernel.config import Config, ConfigError, StartupError
from sb.spec.config import DataPlane

logger = logging.getLogger("sb.db.data_plane")

PROD_SERVICE_NAME = "worker"  # the Railway-injected prod worker identity
_TEST_PLANE_MARKER = "test"   # DSN query marker: ?sb_plane=test


def assert_data_plane(cfg: Config, *, _accrue: list[ConfigError] | None = None) -> None:
    """Refuse boot on any DSN not provably safe for this bot (spec 05 §3.5).

    Rules:
      - cfg.data_plane is REQUIRED (SB_DATA_PLANE in {test,prod}; absence is
        already fail_fast in preflight's coercion step).
      - TEST  => the DB-host allowlist is OPTIONAL (owner directive Q-0263.1).
        When cfg.SB_TEST_DB_HOSTS is unset/empty, ANY host is accepted: boot
        proceeds and the connected host is logged once, loudly, one line —
        never a refusal, never an owner ask. The allowlist engages ONLY when
        the variable is deliberately set non-empty: then the DSN host must be
        in the allowlist OR the DSN carries the `?sb_plane=test` query
        marker; else RefuseBoot.
      - PROD  => requires cfg.SB_PROD_ATTEST PRESENT (presence IS the
        attestation; its value is never logged) AND the running image is the
        prod worker (cfg.RAILWAY_SERVICE_NAME == 'worker'); else RefuseBoot.
        Structural exclusion: an agent/dev container may carry the prod DSN
        (Q-0213) but NOT SB_PROD_ATTEST, so it cannot open prod by accident.

    RefuseBoot is a ConfigError accrued into StartupError -> FAILED_STARTUP.
    No data plane, no boot.
    """
    errors: list[ConfigError] = []
    plane = cfg.data_plane
    dsn = cfg.DATABASE_URL
    parts = urlsplit(dsn) if dsn else None

    if plane is DataPlane.TEST:
        host = parts.hostname if parts else None
        if not cfg.SB_TEST_DB_HOSTS:
            # Open mode (Q-0263.1): no allowlist deliberately set => any host
            # is acceptable on the test plane. Never refuse, never ask — just
            # announce the connected host once, loudly, one line.
            logger.warning(
                "test data plane: DB-host allowlist not set — accepting DSN host %r",
                host,
            )
        else:
            allowed = host is not None and host in cfg.SB_TEST_DB_HOSTS
            marker = False
            if parts is not None:
                query = parse_qs(parts.query)
                marker = query.get("sb_plane", []) == [_TEST_PLANE_MARKER]
            if not (allowed or marker):
                errors.append(ConfigError(
                    "DATABASE_URL",
                    f"test data plane refused: DSN host {host!r} not in "
                    "SB_TEST_DB_HOSTS and no ?sb_plane=test marker",
                ))
    elif plane is DataPlane.PROD:
        if not cfg.is_configured("SB_PROD_ATTEST"):
            errors.append(ConfigError(
                "SB_PROD_ATTEST",
                "prod data plane refused: SB_PROD_ATTEST absent (presence is the attestation)",
            ))
        if cfg.RAILWAY_SERVICE_NAME != PROD_SERVICE_NAME:
            errors.append(ConfigError(
                "RAILWAY_SERVICE_NAME",
                f"prod data plane refused: service name {cfg.RAILWAY_SERVICE_NAME!r} "
                f"is not the prod worker ({PROD_SERVICE_NAME!r})",
            ))

    if _accrue is not None:
        _accrue.extend(errors)
    elif errors:
        raise StartupError(errors)
