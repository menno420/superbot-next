"""The SubsystemManifest root record (K2; frozen at design-spec §2.1).

Deliberately MINIMAL at S3: the root record + its forward facet slots. The
per-facet grammar dataclasses (CommandSpec, PanelSpec, StoreSpec, SettingSpec,
EventSpec, ...) are minted by the Gate-0 fold + their owning K-steps and the
G-/R- amendment registry (docs/planning/rebuild-amendments.yml) — never here.
The compiler is duck-typed over facet objects (it reads declared fields; P5
reds any field without a registered role), so facets can grow without
compiler edits.

Each sb/manifest/<x>.py module declares `MANIFEST = SubsystemManifest(...)`
(pure declarations + handler registrations — design-spec §1.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.roles import register_field_roles


@dataclass(frozen=True)
class SubsystemManifest:
    key: str                        # [S] the subsystem_key (namespace-reserved, frozen-verbatim)
    version: int = 1                # [S] schema-version drift diagnostics
    commands: tuple = ()            # [S] CommandSpec facet (forward declaration — net-new vs shipped)
    panels: tuple = ()              # [S] PanelSpec facet
    settings: tuple = ()            # [S] SettingSpec facet
    stores: tuple = ()              # [S] StoreSpec facet (K3 derives the schema from these)
    events: tuple = ()              # [S] EventSpec facet (K4 derives KNOWN_EVENTS)
    capabilities: tuple = ()        # [S] capability strings ({sub}.{res}.{action}, K1-reserved)
    data_invariants: tuple = ()     # [S] InvariantSpec facet (S12 — spec 11 §2.1, sibling to stores)


register_field_roles(
    "SubsystemManifest",
    key="S", version="S", commands="S", panels="S", settings="S",
    stores="S", events="S", capabilities="S", data_invariants="S",
)
