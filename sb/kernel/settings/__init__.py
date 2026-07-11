"""K7 settings RESOLUTION — the read side ONLY (design-spec §4.1-§4.3;
homed in K7's PROVIDES per F-3.4).

There is NO public raw-KV API: the store read is a private installable port,
and every WRITE goes through the workflow engine's scalar lane (a
`CompoundOpSpec` — settings never writes). `resolve()` keeps the preserved
tri-state chain:

    per-guild explicit  →  global explicit  →  default terminus

Stored values are explicit-true / explicit-false / UNSET; an explicit stored
value ALWAYS wins. The `activation` axis (§4.4) is consulted ONLY at the
unset terminus, and only for bool settings:

  - ON_BY_DEFAULT      → True
  - OFF_UNTIL_OPT_IN   → False (forced by compile rule for
                          external_side_effects=True specs — that fence rides
                          the Gate-0 SettingSpec facet when it is cut)
  - ON_WHEN_KEYED      → resolved ONCE at boot from secret presence
                          (install_secret_presence(cfg) — Config.is_configured)
  - ON_WHEN_BOUND      → dynamic, re-evaluated per read against the binding
                          store's cached state (never persisted; flips with
                          the binding in both directions)

Non-bool settings terminate at their static default, unchanged.

`SettingDeclaration` is the KERNEL registration record — the Gate-0
`SettingSpec` manifest facet (with authority_ref/input_hint/storage etc.)
is NOT minted here; when the facet lands (band-1 port), the manifest build
registers each SettingSpec into this registry (one declaration path, §4.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

# Band 1 re-homed Activation to the spec leaf (sb/spec/settings.py — the
# Gate-0 facet home); re-exported here so pre-band-1 imports keep working.
from sb.spec.settings import Activation

__all__ = [
    "Activation",
    "SettingDeclaration",
    "clear_for_tests",
    "install_binding_probe",
    "install_secret_presence",
    "install_settings_reader",
    "is_explicitly_set",
    "iter_declarations",
    "register_manifest_settings",
    "register_setting",
    "resolve",
]

UNSET = object()   # the store's "no explicit row" sentinel


@dataclass(frozen=True)
class SettingDeclaration:
    """One declared setting (key = f"{subsystem}.{name}")."""

    subsystem: str
    name: str
    default: object = None                      # static default (non-bool terminus)
    activation: Activation | None = None        # bool settings only
    keyed_secret: str | None = None             # REQUIRED iff ON_WHEN_KEYED (env var name)
    bound_binding: str | None = None            # REQUIRED iff ON_WHEN_BOUND (binding name)

    @property
    def key(self) -> str:
        return f"{self.subsystem}.{self.name}"


_declarations: dict[str, SettingDeclaration] = {}

# (guild_id | None, key) -> explicit stored value, or UNSET. guild_id=None
# is the global row. Installed by the db band's typed accessor; the default
# reader sees an empty store (everything unset).
SettingsReader = Callable[[int | None, str], Awaitable[object]]
# binding name -> bound-for-guild? (the binding lane's cached state).
BindingProbe = Callable[[int, str], Awaitable[bool]]


async def _empty_reader(guild_id: int | None, key: str) -> object:
    return UNSET


async def _no_binding(guild_id: int, binding_name: str) -> bool:
    return False


_reader: SettingsReader = _empty_reader
_binding_probe: BindingProbe = _no_binding
_present_secrets: frozenset[str] = frozenset()


def register_setting(decl: SettingDeclaration) -> None:
    if decl.key in _declarations:
        raise ValueError(f"setting {decl.key!r} already declared (one owning spec per key)")
    if decl.activation is Activation.ON_WHEN_KEYED and not decl.keyed_secret:
        raise ValueError(f"{decl.key!r}: ON_WHEN_KEYED requires keyed_secret")
    if decl.activation is Activation.ON_WHEN_BOUND and not decl.bound_binding:
        raise ValueError(f"{decl.key!r}: ON_WHEN_BOUND requires bound_binding")
    _declarations[decl.key] = decl


def iter_declarations(subsystem: str | None = None) -> tuple[SettingDeclaration, ...]:
    """Read-only declaration inventory (the S9b generated-settings-panel
    projection + diagnostics read this; never a write path)."""
    decls = _declarations.values()
    if subsystem is not None:
        decls = (d for d in decls if d.subsystem == subsystem)
    return tuple(sorted(decls, key=lambda d: d.key))


def install_settings_reader(reader: SettingsReader) -> None:
    global _reader
    _reader = reader


def install_binding_probe(probe: BindingProbe) -> None:
    global _binding_probe
    _binding_probe = probe


def install_secret_presence(cfg: object) -> None:
    """Boot-time ON_WHEN_KEYED resolution: record which declared secrets the
    deployment carries (Config.is_configured — presence, never the value)."""
    global _present_secrets
    present = set()
    for decl in _declarations.values():
        if decl.keyed_secret:
            probe = getattr(cfg, "is_configured", None)
            if callable(probe) and probe(decl.keyed_secret):
                present.add(decl.keyed_secret)
    _present_secrets = frozenset(present)


def clear_for_tests() -> None:
    global _reader, _binding_probe, _present_secrets
    _declarations.clear()
    _persisted_keys.clear()
    _reader = _empty_reader
    _binding_probe = _no_binding
    _present_secrets = frozenset()


async def resolve(guild_id: int, subsystem: str, name: str) -> object:
    """THE read seam (design-spec §4.1) — tri-state + activation terminus."""
    key = f"{subsystem}.{name}"
    decl = _declarations.get(key)
    if decl is None:
        raise LookupError(f"setting {key!r} is not declared (no raw-KV reads)")

    per_guild = await _reader(guild_id, key)
    if per_guild is not UNSET:
        return per_guild
    global_row = await _reader(None, key)
    if global_row is not UNSET:
        return global_row

    if decl.activation is None:
        return decl.default
    if decl.activation is Activation.ON_BY_DEFAULT:
        return True
    if decl.activation is Activation.OFF_UNTIL_OPT_IN:
        return False
    if decl.activation is Activation.ON_WHEN_KEYED:
        return decl.keyed_secret in _present_secrets
    # ON_WHEN_BOUND — dynamic per read against the binding cache.
    return await _binding_probe(guild_id, decl.bound_binding or "")


async def is_explicitly_set(guild_id: int, subsystem: str, name: str) -> bool:
    """True iff a declared setting has an EXPLICIT stored row (per-guild or
    global) — the tri-state's "not default" leg exposed read-only.

    The shipped bot distinguished "operator configured this guild" from
    "everything at declared defaults" by the presence of the typed
    ``ai_guild_policy`` row; the KV port's equivalent is an explicit row
    under the declared key (band-7 ai uses this for the shipped
    GUILD_NOT_CONFIGURED semantics). Additive read helper — no write path,
    no activation semantics.
    """
    key = f"{subsystem}.{name}"
    if key not in _declarations:
        raise LookupError(f"setting {key!r} is not declared (no raw-KV reads)")
    if await _reader(guild_id, key) is not UNSET:
        return True
    return await _reader(None, key) is not UNSET


# --- the band-1 manifest bridge (design-spec §4.1: ONE declaration path) ---------

_persisted_keys: dict[str, str] = {}   # "{subsystem}.{name}" -> persisted KV key


def persisted_key(subsystem: str, name: str) -> str:
    """The canonical persisted key string for a declared setting (compat
    item 5: the shipped `settings_key` vocabulary stays the row key)."""
    return _persisted_keys.get(f"{subsystem}.{name}", f"{subsystem}.{name}")


def register_manifest_settings(manifest: object) -> tuple[SettingDeclaration, ...]:
    """Register every SettingSpec facet of one SubsystemManifest into THE
    declaration registry (band 1; runs the §4.4/§2.5 fences first).

    Returns the minted declarations. BindingSpec/ResourceRequirement facet
    entries are validated but not declared here (the binding lane owns them).
    """
    from sb.spec.settings import SettingSpec, validate_settings_facets

    problems = validate_settings_facets(manifest)
    if problems:
        raise ValueError("settings facet fences: " + "; ".join(problems))
    minted: list[SettingDeclaration] = []
    subsystem = str(getattr(manifest, "key"))
    for spec in getattr(manifest, "settings", ()) or ():
        if not isinstance(spec, SettingSpec):
            continue
        decl = SettingDeclaration(
            subsystem=subsystem,
            name=spec.name,
            default=spec.default,
            activation=spec.activation,
            keyed_secret=spec.keyed_secret or None,
            bound_binding=spec.bound_binding or None,
        )
        register_setting(decl)
        _persisted_keys[decl.key] = spec.key
        minted.append(decl)
    return tuple(minted)
