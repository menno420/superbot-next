"""Boot preflight + the one typed, validated, frozen Config object (K0).

Built to frozen L0 spec 05 §3.2. `preflight()` runs FIRST in the composition
root, BEFORE gateway connect and BEFORE the manifest-compiler boot-gate legs.
12.1-factor: coerce + validate ALL env at boot, never lazily deep in a request.

The one accessor model (RC-10): `Config` exposes one typed, frozen attribute
per `ConfigSpec`, named verbatim by `env_var`. There is NO `.get(spec)` and no
sibling `Secrets` object; redaction is a field property (`redact=True`)
enforced by `Config.__repr__`/diagnostic serialization, which omit redacted
values and expose only presence via `is_configured()`.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from sb.spec.config import (
    CONFIG_FIELDS,
    INTENT_CONTRACT,
    ConfigPosture,
    ConfigSpec,
    ConfigType,
    DataPlane,
)

__all__ = [
    "Config",
    "ConfigError",
    "StartupError",
    "assert_intents",
    "load_config",
    "parse_bool",
    "parse_dsn",
    "preflight",
]

_TRUTHY = {"1", "true", "yes", "on", "y", "t"}
_FALSY = {"", "0", "false", "no", "off", "n", "f"}


class ConfigError(Exception):
    """One field failed to coerce/validate. Carries env_var + reason."""

    def __init__(self, env_var: str, reason: str) -> None:
        super().__init__(f"{env_var}: {reason}")
        self.env_var = env_var
        self.reason = reason


class StartupError(Exception):
    """Preflight aggregate — a LIST of ConfigError, raised once.

    The composition root maps this to the lifecycle FAILED_STARTUP phase.
    """

    def __init__(self, errors: Iterable[ConfigError]) -> None:
        self.errors: tuple[ConfigError, ...] = tuple(errors)
        lines = "; ".join(str(e) for e in self.errors)
        super().__init__(f"{len(self.errors)} config error(s): {lines}")


def parse_bool(raw: str, *, env_var: str) -> bool:
    """THE one boolean grammar. Case-insensitive after strip.

    Unknown token => ConfigError. Subsumes all three shipped grammars: every
    value they accepted maps identically here (spec 05 §3.2 / fork 2).
    """
    v = raw.strip().lower()
    if v in _TRUTHY:
        return True
    if v in _FALSY:
        return False
    raise ConfigError(env_var, f"not a boolean: {raw!r} (use one of {sorted(_TRUTHY | _FALSY)})")


def parse_dsn(raw: str, *, env_var: str) -> str:
    """DSN SHAPE validation (the preflight DSN coercion).

    urlsplit(raw) must yield scheme in {postgres, postgresql}, a non-empty
    host, and a non-empty path (db name); otherwise ConfigError. Does NOT
    connect — connection is db.init's job (spec 05 §3.4). Returns the raw DSN
    string unchanged on success.
    """
    parts = urlsplit(raw)
    if parts.scheme not in ("postgres", "postgresql"):
        raise ConfigError(env_var, f"DSN scheme must be postgres/postgresql, got {parts.scheme!r}")
    if not parts.hostname:
        raise ConfigError(env_var, "DSN has no host")
    if not parts.path or parts.path == "/":
        raise ConfigError(env_var, "DSN has no database name (empty path)")
    return raw


def _coerce(spec: ConfigSpec, raw: str) -> object:
    """Coerce one raw env string by the spec's declared type. Raises ConfigError."""
    t = spec.type
    if t is ConfigType.BOOL:
        return parse_bool(raw, env_var=spec.env_var)
    if t is ConfigType.DSN:
        return parse_dsn(raw, env_var=spec.env_var)
    if t is ConfigType.CSV:
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if t in (ConfigType.INT, ConfigType.FLOAT):
        try:
            value: float = int(raw) if t is ConfigType.INT else float(raw)
        except ValueError:
            raise ConfigError(spec.env_var, f"not a number: {raw!r}") from None
        if spec.min is not None and value < spec.min:
            raise ConfigError(spec.env_var, f"below declared minimum {spec.min}: {value}")
        return value
    # STR / SECRET
    value_s = raw
    if spec.choices and value_s not in spec.choices:
        raise ConfigError(spec.env_var, f"not in {spec.choices}: {value_s!r}")
    return value_s


def _make_config_class() -> type:
    """Build the frozen Config dataclass: one attribute per ConfigSpec (RC-10)."""
    fields = [
        (spec.env_var, object, dataclasses.field(default=None))
        for spec in CONFIG_FIELDS
    ]

    def __repr__(self: object) -> str:  # noqa: N807
        parts = []
        for spec in CONFIG_FIELDS:
            value = getattr(self, spec.env_var)
            if spec.redact:
                parts.append(f"{spec.env_var}=<redacted configured={value is not None}>")
            else:
                parts.append(f"{spec.env_var}={value!r}")
        return f"Config({', '.join(parts)})"

    def is_configured(self: object, env_var: str) -> bool:
        """Presence of a (possibly-redacted) field."""
        return getattr(self, env_var) is not None

    def iter_fields(self: object) -> Iterable[tuple[ConfigSpec, object]]:
        """Tooling / doc-generation iteration surface (redacted values included)."""
        return [(spec, getattr(self, spec.env_var)) for spec in CONFIG_FIELDS]

    def data_plane(self: object) -> DataPlane:
        return DataPlane(getattr(self, "SB_DATA_PLANE"))

    return dataclasses.make_dataclass(
        "Config",
        fields,
        frozen=True,
        namespace={
            "__doc__": (
                "The one typed, validated, frozen config object. ONE attribute per "
                "ConfigSpec, named verbatim by env_var. Redacted fields (SECRET, DSN) "
                "hold the real value but never appear in repr/diagnostics."
            ),
            "__repr__": __repr__,
            "is_configured": is_configured,
            "iter_fields": iter_fields,
            "data_plane": property(data_plane),
        },
    )


Config = _make_config_class()


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Coerce every declared field from `env` into a frozen Config.

    Pure load: no data-plane / intent asserts (those are `preflight`'s).
    Raises StartupError aggregating every ConfigError.
    """
    if env is None:
        env = os.environ
    errors: list[ConfigError] = []
    values: dict[str, object] = {}
    for spec in CONFIG_FIELDS:
        raw = env.get(spec.env_var)
        if raw is None or raw == "" and spec.type not in (ConfigType.STR, ConfigType.CSV):
            if spec.required:
                if spec.posture is ConfigPosture.FAIL_FAST:
                    errors.append(ConfigError(spec.env_var, "required but absent"))
                    continue
                # DEGRADE / DORMANT: record inactive and continue.
                values[spec.env_var] = None
                continue
            values[spec.env_var] = spec.default
            continue
        try:
            values[spec.env_var] = _coerce(spec, raw)
        except ConfigError as exc:
            if spec.required and spec.posture is not ConfigPosture.FAIL_FAST:
                values[spec.env_var] = None  # invalid + degrade/dormant => inactive
            else:
                errors.append(exc)
    if errors:
        raise StartupError(errors)
    return Config(**values)


def assert_intents(cfg: Config, *, _accrue: list[ConfigError] | None = None) -> None:
    """Gateway-intent preflight (L-17, spec 05 §3.2).

    For each required IntentSpec: when privileged, its approval_env BOOL field
    must be truthy (parse_bool grammar) in non-`test` data planes — a prod bot
    must not silently rely on an unapproved privileged intent. In the `test`
    plane the check is advisory (non-fatal). Raises StartupError unless an
    accumulator is supplied (preflight aggregates).
    """
    errors: list[ConfigError] = []
    plane = cfg.data_plane
    for intent in INTENT_CONTRACT:
        if not (intent.required and intent.privileged and intent.approval_env):
            continue
        approved = bool(getattr(cfg, intent.approval_env))
        if not approved and plane is not DataPlane.TEST:
            errors.append(ConfigError(
                intent.approval_env,
                f"privileged intent {intent.name!r} lacks declared Discord approval "
                f"in data plane {plane.value!r}",
            ))
    if _accrue is not None:
        _accrue.extend(errors)
    elif errors:
        raise StartupError(errors)


def preflight(env: Mapping[str, str] | None = None) -> Config:
    """Run FIRST in the composition root, BEFORE gateway connect and BEFORE
    the manifest-compiler boot_gate legs (spec 05 §3.2 / §6).

    1. Coerce + validate every ConfigSpec (load_config; collect-all).
    2. assert_data_plane() — the 4th kernel rail (spec 05 §3.5).
    3. assert_intents() — privileged-intent approval preflight.

    On any accrued error raise StartupError; on success return frozen Config.
    """
    cfg = load_config(env)  # raises StartupError on coercion failures
    errors: list[ConfigError] = []
    # Function-level import: sb.kernel.db.data_plane imports ConfigError from
    # this module (its errors ARE config errors); importing it at module level
    # would be circular. This is the one sanctioned deferred import.
    from sb.kernel.db.data_plane import assert_data_plane

    assert_data_plane(cfg, _accrue=errors)
    assert_intents(cfg, _accrue=errors)
    if errors:
        raise StartupError(errors)
    return cfg
