"""SettingSpec · BindingSpec · ResourceRequirement — the §2.5 extended
shipped types (band 1; design-spec §2.5 + §4, frozen-l0-grammar Group 1).

Binding constraint 2, executed literally: these are the SHIPPED classes
(disbot `core/runtime/subsystem_schema.py:75/:109`,
`core/runtime/resource_specs.py:50/:64/:79`) carried with every existing
field name and semantic intact, plus ONLY additive fields, each with a
constructor default — a ported constructor call parses unchanged.

Two deliberate representation notes (D-0025):

* `value_type` accepts the shipped `type` object (`int`, `str`, `bool`,
  `float`) OR the G-2 list-variant strings ("list[int]", "list[str]", ...);
  it is canonicalized to the string form at construction so the manifest
  snapshot serializes cleanly (a raw `type` is callable and the compiler
  refuses callables in specs). `python_type()` gives the coercion type back.
* `validator` must be a REGISTERED PredicateRef (or None) — the design
  spec's "the compiler serializes it by registered ref and errors on
  unregistered callables", enforced by type rather than late error.

`Activation` (§4.4) is RE-HOMED here from sb/kernel/settings (the kernel
imports the spec leaf, never the reverse); sb.kernel.settings re-exports it
so existing imports keep working.

The §4.4/§2.5 compile fences live in `check_setting_spec` /
`check_binding_spec` / `validate_settings_facets` and run at manifest
registration (sb.kernel.settings.register_manifest_settings) and in CI via
the manifest compile's spec walk consumers.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from sb.spec.refs import PredicateRef
from sb.spec.roles import register_field_roles

__all__ = [
    "Activation",
    "BindingKind",
    "BindingSpec",
    "DomainPanelSpec",
    "PresetKind",
    "ProvisioningHint",
    "ProvisioningPriority",
    "ResourceKind",
    "ResourceRequirement",
    "ScopeDefault",
    "SettingGroupSpec",
    "SettingSpec",
    "SettingStorage",
    "TeardownPolicy",
    "check_binding_spec",
    "check_setting_spec",
    "validate_settings_facets",
]


# --- §4.4 activation (re-homed from sb/kernel/settings) -------------------------

class Activation(enum.Enum):
    """Design-spec §4.4 — the unset-terminus policy for bool settings."""

    ON_BY_DEFAULT = "on_by_default"
    ON_WHEN_BOUND = "on_when_bound"
    ON_WHEN_KEYED = "on_when_keyed"
    OFF_UNTIL_OPT_IN = "off_until_opt_in"


class SettingStorage(enum.Enum):
    """§4.3 — folds AI's typed `ai_guild_policy` columns into the one
    declaration path; the typed table stays the physical store."""

    KV = "kv"
    TYPED_COLUMN = "typed_column"


class ScopeDefault(enum.Enum):
    GUILD = "guild"
    GLOBAL = "global"


class PresetKind(enum.Enum):
    """Q-0070/Q-0215 — generalizes shipped numeric presets to authored text."""

    NONE = "none"
    NUMERIC = "numeric"
    TEXT = "text"


_SCALAR_TYPE_TOKENS = {"int", "str", "bool", "float"}
_LIST_TYPE_TOKENS = {"list[int]", "list[str]", "list[float]"}
_TYPE_TOKENS = _SCALAR_TYPE_TOKENS | _LIST_TYPE_TOKENS
_PY_TYPES = {"int": int, "str": str, "bool": bool, "float": float}


def _canonical_value_type(value_type: object) -> str:
    if isinstance(value_type, type):
        token = value_type.__name__
    else:
        token = str(value_type)
    if token not in _TYPE_TOKENS:
        raise ValueError(
            f"value_type {value_type!r} not in {sorted(_TYPE_TOKENS)} "
            f"(G-2 admits the three list variants; anything else is a "
            f"typed-column or escape-hatch shape)")
    return token


# --- SettingSpec -----------------------------------------------------------------

@dataclass(frozen=True)
class SettingSpec:
    """Shipped fields verbatim (`subsystem_schema.py:109`), incl. the
    :129-134 docstring invariant word-for-word: an empty
    `capability_required` is treated by the mutation pipelines as the
    ADMINISTRATOR FLOOR, not "no auth". Additive fields per §2.5."""

    # --- shipped, verbatim ---
    name: str                                   # [S] unique within subsystem
    value_type: object                          # [S] type|str -> canonical token (see module doc)
    default: Any = None                         # [S] static default (non-bool terminus)
    settings_key: str = ""                      # [S] canonical persisted key string (compat item 5)
    capability_required: str = ""               # [S] empty => ADMIN floor (mutation pipelines)
    hint: str = ""                              # [S] wizard copy
    validator: PredicateRef | None = None       # [S] registered ref only (never a bare callable)
    allowed_values: tuple = ()                  # [S] enum-shaped scalars render a select
    input_hint: str = ""                        # [S] edit-dispatch hint ("channel"/"role"/...)
    presets: tuple = ()                         # [S] preset values (see preset_kind)
    # --- additive (§2.5), every one defaulted ---
    activation: Activation | None = None        # [S] §4.4; REQUIRED (non-None) iff bool-typed
    external_side_effects: bool = False         # [S] True FORCES off_until_opt_in (fence)
    storage: SettingStorage = SettingStorage.KV  # [S] §4.3
    scope_default: ScopeDefault = ScopeDefault.GUILD  # [S]
    legacy_keys: tuple[str, ...] = ()           # [S] old KV keys this spec answers for (§4.5)
    keyed_secret: str = ""                      # [S] REQUIRED iff activation=ON_WHEN_KEYED (env name)
    bound_binding: str = ""                     # [S] REQUIRED iff activation=ON_WHEN_BOUND
    preset_kind: PresetKind = PresetKind.NONE   # [S] Q-0070/Q-0215
    bounds: tuple | None = None                 # [S] G-5 (lo, hi) numeric range / (max_len,) str
    group: str = ""                             # [A] settings-hub group membership (sim-assigned)
    advanced: bool = False                      # [A] primary-vs-advanced placement
    panel_order: int = 0                        # [A] order within its group
    edit_weight: float = 1.0                    # [O] grouping-sim seed
    co_edit_group: str = ""                     # [O] optional seed pair-group
    depends_on: tuple[str, ...] = ()            # [O] dependency-order constraint

    def __post_init__(self) -> None:
        object.__setattr__(self, "value_type", _canonical_value_type(self.value_type))

    @property
    def key(self) -> str:
        """The canonical persisted key (check_parity_depth / the namespace
        `setting_key` kind read this): the shipped `settings_key` string
        when declared (interface preserved — compat item 5), else the
        subsystem-agnostic spec name."""
        return self.settings_key or self.name

    @property
    def authority_ref(self) -> str:
        """Frozen Group 1 field 1 (six-type placement) — empty => ADMIN floor."""
        return self.capability_required

    def python_type(self) -> type:
        token = str(self.value_type)
        if token in _PY_TYPES:
            return _PY_TYPES[token]
        return list

    @property
    def is_bool(self) -> bool:
        return str(self.value_type) == "bool"

    @property
    def is_list(self) -> bool:
        return str(self.value_type) in _LIST_TYPE_TOKENS


@dataclass(frozen=True)
class SettingGroupSpec:
    """§2.5 — groups are DECLARED (identity/label/description hand-authored,
    [S]); the sim only ASSIGNS membership/order ([A] fields on SettingSpec)."""

    group_id: str                               # [S]
    label: str                                  # [S] semantic copy
    description: str = ""                       # [S] semantic copy


# --- BindingSpec -----------------------------------------------------------------

class BindingKind(enum.Enum):
    """Shipped verbatim (`subsystem_schema.py` BindingKind): ResourceKind
    plus MEMBER (bindable, never provisioned)."""

    CHANNEL = "channel"
    ROLE = "role"
    CATEGORY = "category"
    THREAD = "thread"
    MEMBER = "member"


@dataclass(frozen=True)
class BindingSpec:
    """Shipped fields verbatim (`subsystem_schema.py:75`); additive §2.5 /
    decision-3 fields. Binding rows are the ONLY route-truth for Discord
    pointers; legacy KV keys become declared read-aliases (§4.5)."""

    # --- shipped, verbatim ---
    name: str                                   # [S] unique within subsystem
    kind: BindingKind                           # [S]
    required: bool = False                      # [S] unbound+required => fatal completeness finding
    hint: str = ""                              # [S] wizard copy
    capability_required: str = ""               # [S] empty => ADMIN floor
    # --- additive ---
    legacy_settings_key_aliases: tuple[str, ...] = ()  # [S] the KV->binding alias map (decision 3)
    resource_link: str = ""                     # [S] names the ResourceRequirement it binds
    multiplicity: int = 1                       # [S] bounded list bindings
    group: str = ""                             # [A] membership across the declared pool
    bind_weight: float = 1.0                    # [O]

    @property
    def authority_ref(self) -> str:
        return self.capability_required


# --- ResourceRequirement -----------------------------------------------------------

class ResourceKind(enum.Enum):
    """Shipped verbatim (`resource_specs.py`)."""

    CHANNEL = "channel"
    ROLE = "role"
    CATEGORY = "category"
    THREAD = "thread"


class ProvisioningPriority(enum.Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class TeardownPolicy(enum.Enum):
    KEEP = "keep"
    ARCHIVE = "archive"
    DELETE_ON_CONFIRM = "delete_on_confirm"


@dataclass(frozen=True)
class ProvisioningHint:
    """Shipped verbatim (`resource_specs.py:64`)."""

    priority: ProvisioningPriority              # [S]
    suggested_name: str = ""                    # [S]
    suggested_category: str = ""                # [S]
    suggested_permissions: tuple[str, ...] = () # [S]


@dataclass(frozen=True)
class ResourceRequirement:
    """Shipped fields verbatim (`resource_specs.py:79`); additive §2.5.
    One type, the shipped one, extended — no separate "ResourceSpec"."""

    # --- shipped, verbatim ---
    kind: ResourceKind                          # [S]
    intent: str                                 # [S] e.g. "log_destination"
    provisioning: ProvisioningHint              # [S]
    binding_name: str = ""                      # [S] the BindingSpec cross-link
    description: str = ""                       # [S] wizard copy
    # --- additive ---
    offer_on_enable: bool = False               # [S] OFFER a provisioning preview, never create
    teardown_policy: TeardownPolicy = TeardownPolicy.KEEP  # [S]
    shareable: bool = True                      # [S]
    audit_intent: str = ""                      # [S] labels provisioning audit rows (mig-030)

    @property
    def authority_ref(self) -> str:
        return ""                               # ADMIN floor (provisioning lane)


@dataclass(frozen=True)
class DomainPanelSpec:
    """Shipped verbatim (`subsystem_schema.py` DomainPanelSpec) — a declared
    domain-configuration destination the Settings hub DISCOVERS; the
    destination stays the mutation owner."""

    name: str                                   # [S]
    description: str = ""                       # [S]
    capability_required: str = ""               # [S] informational; destination enforces


# --- the §4.4/§2.5 compile fences -------------------------------------------------

def check_setting_spec(subsystem: str, spec: SettingSpec) -> list[str]:
    """The conscious-choice fences (design-spec §2.5/§4.4). Returns problem
    strings; empty = clean."""
    problems: list[str] = []
    where = f"{subsystem}.{spec.name}"
    if spec.is_bool and spec.activation is None:
        problems.append(
            f"{where}: bool-typed SettingSpec must declare `activation` "
            f"(the §4.4 conscious-choice rule; the trilemma has no default)")
    if not spec.is_bool and spec.activation is not None:
        problems.append(
            f"{where}: non-bool SettingSpec must leave `activation` None "
            f"(the shipped static `default` governs)")
    if spec.external_side_effects and spec.activation is not Activation.OFF_UNTIL_OPT_IN:
        problems.append(
            f"{where}: external_side_effects=True FORCES "
            f"activation=off_until_opt_in (the image-moderation privacy gate as grammar)")
    if spec.activation is Activation.ON_WHEN_KEYED and not spec.keyed_secret:
        problems.append(f"{where}: ON_WHEN_KEYED requires keyed_secret")
    if spec.activation is Activation.ON_WHEN_BOUND and not spec.bound_binding:
        problems.append(f"{where}: ON_WHEN_BOUND requires bound_binding")
    if (str(spec.value_type) == "str" and spec.presets
            and spec.preset_kind is not PresetKind.TEXT):
        problems.append(
            f"{where}: a str-typed spec with presets must declare "
            f"preset_kind=text (else the presets are decorative/inert — Q-0215)")
    if spec.preset_kind is PresetKind.NUMERIC and str(spec.value_type) not in ("int", "float"):
        problems.append(f"{where}: preset_kind=numeric on a non-numeric spec")
    return problems


def check_binding_spec(subsystem: str, spec: BindingSpec,
                       declared_requirements: frozenset[str]) -> list[str]:
    problems: list[str] = []
    where = f"{subsystem}.{spec.name}"
    if spec.resource_link and spec.resource_link not in declared_requirements:
        problems.append(
            f"{where}: resource_link {spec.resource_link!r} names no declared "
            f"ResourceRequirement.binding_name (§4.2 cross-validation)")
    if spec.multiplicity < 1:
        problems.append(f"{where}: multiplicity must be >= 1")
    return problems


def validate_settings_facets(manifest: object) -> list[str]:
    """Cross-validate one SubsystemManifest's settings/bindings/resources
    facets. Duck-typed (facets may carry mixed spec kinds)."""
    key = str(getattr(manifest, "key", "?"))
    settings = tuple(getattr(manifest, "settings", ()) or ())
    setting_specs = [s for s in settings if isinstance(s, SettingSpec)]
    binding_specs = [s for s in settings if isinstance(s, BindingSpec)]
    requirements = frozenset(
        r.binding_name for r in settings if isinstance(r, ResourceRequirement)
        and r.binding_name)
    problems: list[str] = []
    seen: set[str] = set()
    for spec in setting_specs:
        problems.extend(check_setting_spec(key, spec))
        if spec.key in seen:
            problems.append(f"{key}: duplicate setting key {spec.key!r}")
        seen.add(spec.key)
    for spec in binding_specs:
        problems.extend(check_binding_spec(key, spec, requirements))
    return problems


register_field_roles(
    "SettingSpec",
    name="S", value_type="S", default="S", settings_key="S",
    capability_required="S", hint="S", validator="S", allowed_values="S",
    input_hint="S", presets="S", activation="S", external_side_effects="S",
    storage="S", scope_default="S", legacy_keys="S", keyed_secret="S",
    bound_binding="S", preset_kind="S", bounds="S",
    group="A", advanced="A", panel_order="A",
    edit_weight="O", co_edit_group="O", depends_on="O",
)
register_field_roles(
    "SettingGroupSpec",
    group_id="S", label="S", description="S",
)
register_field_roles(
    "BindingSpec",
    name="S", kind="S", required="S", hint="S", capability_required="S",
    legacy_settings_key_aliases="S", resource_link="S", multiplicity="S",
    group="A", bind_weight="O",
)
register_field_roles(
    "ProvisioningHint",
    priority="S", suggested_name="S", suggested_category="S",
    suggested_permissions="S",
)
register_field_roles(
    "ResourceRequirement",
    kind="S", intent="S", provisioning="S", binding_name="S", description="S",
    offer_on_enable="S", teardown_policy="S", shareable="S", audit_intent="S",
)
register_field_roles(
    "DomainPanelSpec",
    name="S", description="S", capability_required="S",
)
