"""[S]/[A]/[O] field-role metadata (K2, frozen L0 spec 01 §2 / design-spec §2.0).

Every field of every manifest spec type is tagged exactly one of:
  S — semantic (hand-authored meaning; the sim may never touch it)
  A — arrangement (sim-owned; layout locks may overlay it, spec 01 §5)
  O — operational (telemetry/weights; measured, never hand-tuned)

`snapshot_field_roles()` is the `field_roles` map the snapshot carries and
the arrangement-invariance test + sim read. P5 (`role_tag`) reds any spec
field without exactly one registered role. Stdlib-only leaf.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    S = "S"  # semantic
    A = "A"  # arrangement
    O = "O"  # operational  # noqa: E741


_FIELD_ROLES: dict[str, Role] = {}


def register_field_roles(type_name: str, **field_to_role: str) -> None:
    """Declare the role of each field of one spec type, at type-definition site.

    A re-registration with a DIFFERENT role is an error (roles are frozen
    metadata); an identical re-registration is a no-op (module re-import).
    """
    for field_name, role_token in field_to_role.items():
        key = f"{type_name}.{field_name}"
        role = Role(role_token)
        existing = _FIELD_ROLES.get(key)
        if existing is not None and existing is not role:
            raise ValueError(f"field role for {key} already registered as {existing.value}")
        _FIELD_ROLES[key] = role


def field_role(type_name: str, field_name: str) -> Role | None:
    """The metadata helper: role for `TypeName.field`, or None if untagged."""
    return _FIELD_ROLES.get(f"{type_name}.{field_name}")


def snapshot_field_roles() -> dict[str, str]:
    """The `field_roles` snapshot section — sorted, string-valued."""
    return {key: role.value for key, role in sorted(_FIELD_ROLES.items())}
