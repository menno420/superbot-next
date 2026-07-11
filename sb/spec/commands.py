"""CommandSpec — the frozen §2.2 routable entry-point facet (band 1).

Minted at band 1 (design-spec §2.2 + frozen-l0-grammar Group 1); until now
the compiler duck-typed the facet and only `cost_posture`/`quota_ref`
(sb/spec/cost.py, S11) and `slash_common` (sb/spec/governance.py, S15) had
registered roles. This module cuts the real dataclass, following the
sb/spec/panels.py precedent for the two-lane authority model: the SHIPPED
fields `capability_required`/`audience_tier` are carried verbatim and the
frozen `authority_ref` (Group 1 field 1 — the SOLE authority field the K6/K8
seams duck-read) is the derived property `capability beats tier; empty =>
ADMIN-floor CAPABILITY lane`.

Group-1 grammar amendments carried: `enabled_when` (field 2, PredicateRef
string form), `reply_visibility` (field 3), `defer_mode` (field 4, the
optional variant), `cooldown`/CooldownSpec (field 5, amendment family G-4),
`cost_posture`/`quota_ref` (fields 6-7, imported home sb/spec/cost.py),
`slash_common` (field 8, D-5 essential tag, home sb/spec/governance.py).

`capability` is the capability-grouping field check_intent_survival /
check_slash_cap duck-read (S15 note: "re-binds when band-1 mints a real
capability field" — this is that field; empty falls back to the spec name).

Stdlib + sb.spec leaves only.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sb.spec.cost import CostPosture
from sb.spec.outcomes import DeferMode, ReplyVisibility
from sb.spec.roles import register_field_roles

__all__ = [
    "CommandKind",
    "CommandSpec",
    "CooldownScope",
    "CooldownSpec",
]


class CommandKind(enum.StrEnum):
    """§2.2 `kind` — the namespace `command` pool is kind-partitioned
    (G-6: prefix `!karma` and slash `/karma` legitimately coexist).

    StrEnum ON PURPOSE: the compiler's `_project` duck-reads `cmd.kind`
    with string equality ("both") and `str(kind_field)` for the surface
    token — a plain Enum would leak "CommandKind.SLASH" into the
    namespace projection."""

    PREFIX = "prefix"
    SLASH = "slash"
    BOTH = "both"


class CooldownScope(enum.Enum):
    USER = "user"
    GUILD = "guild"
    CHANNEL = "channel"
    GLOBAL = "global"


@dataclass(frozen=True)
class CooldownSpec:
    """G-4 (linchpin spike 2026-07-02): the shipped `@commands.cooldown`
    rate limit as data. Charged at resolver step 3 for EVERY surface."""

    rate: int                                   # [S]
    per_s: float                                # [S]
    scope: CooldownScope = CooldownScope.USER   # [S]


@dataclass(frozen=True)
class CommandSpec:
    """The §2.2 entry-point facet (net-new declarations; legacy names are
    claimed verbatim through the K1 namespace kinds)."""

    name: str                                   # [S] reserved per-kind in namespace `command`
    kind: CommandKind                           # [S]
    group: str = ""                             # [S] parent group PATH (K1 parent_group; the
    #     compiler's P-namespace duck-read — "logging" makes this `logging <name>`)
    route: object = None                        # [S] PanelRef | WorkflowRef | HandlerRef | None
    #     (commands open panels by default; command-only = escape-hatch class)
    aliases: tuple[str, ...] = ()               # [S] each reserved individually
    summary: str = ""                           # [S] help-projection input
    usage: str = ""                             # [S] help-projection input
    capability_required: str = ""               # [S] config/governance lane (empty => ADMIN floor)
    audience_tier: str = ""                     # [S] domain lane (shipped visibility vocabulary)
    capability: str = ""                        # [S] owning capability group (survival checkers;
    #     empty falls back to the spec's own name — sb/spec/governance.py)
    enabled_when: str = ""                      # [S] PredicateRef string form ("" = constant-true)
    reply_visibility: ReplyVisibility | None = None  # [S] None => lane default (§3.4)
    defer_mode: DeferMode | None = None         # [S] None => surface-derived
    cooldown: CooldownSpec | None = None        # [S] G-4
    cost_posture: CostPosture = CostPosture.FREE  # [S] S11 home; role registered in cost.py
    quota_ref: str = ""                         # [S] S11 home
    slash_common: bool = False                  # [S] D-5 essential tag; role registered in governance.py
    help_section_order: int = 0                 # [A] order within the subsystem's help entry
    usage_weight: float = 1.0                   # [O] Phase-1 harvest seed; telemetry-updated

    @property
    def qualified_name(self) -> str:
        """The dispatch key: `<group> <name>` (RuntimeIndex/adapters read
        the same shape from the snapshot's parent_group)."""
        return f"{self.group.replace('.', ' ')} {self.name}" if self.group else self.name

    @property
    def authority_ref(self) -> str:
        """Duck-read by K6/K8 (frozen Group 1 field 1) — capability beats
        tier; empty => the ADMIN-floor CAPABILITY lane (shipped invariant)."""
        return self.capability_required or self.audience_tier or ""


def command_dispatch_keys(cmd: object) -> list[str]:
    """Every key a command answers to in the dispatch index (duck-typed —
    the parity boot and the live index share this ONE truth): the qualified
    name, then each alias GROUP-SCOPED, mirroring the shipped discord.py
    registration (``@group.command(aliases=[...])`` reserves the alias
    INSIDE the group — ``!ticket open`` routes ticket.new; bare ``!open``
    was never a top-level route)."""
    name = str(getattr(cmd, "name", "") or "")
    qualified = str(getattr(cmd, "qualified_name", "") or name)
    group_path = str(getattr(cmd, "group", "") or "").replace(".", " ")
    return [qualified] + [
        f"{group_path} {a}" if group_path else str(a)
        for a in (getattr(cmd, "aliases", ()) or ())]


register_field_roles(
    "CooldownSpec",
    rate="S", per_s="S", scope="S",
)
register_field_roles(
    "CommandSpec",
    name="S", kind="S", group="S", route="S", aliases="S", summary="S", usage="S",
    capability_required="S", audience_tier="S", capability="S",
    enabled_when="S", reply_visibility="S", defer_mode="S", cooldown="S",
    help_section_order="A", usage_weight="O",
    # cost_posture / quota_ref / slash_common: registered at their owning
    # modules (sb/spec/cost.py S11, sb/spec/governance.py S15).
)
