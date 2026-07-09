"""Governance subsystem registry (band 5) — the shipped
utils/subsystem_registry.py DATA harvested verbatim @7f7628e1, headless.

The compiled architecture's subsystem truth is the manifest registry
(sb/manifest/*); governance keeps the SHIPPED per-subsystem metadata the
manifests do not carry (visibility_tier, dependencies, soft deps, the
capability vocabulary) as compat-frozen data. As bands port, subsystems
whose manifests exist are live; rows for not-yet-ported subsystems stay
here so visibility overrides / capability strings stored in old-bot rows
keep resolving byte-identically across cutover.

REGISTRY_VERSION / REGISTRY_SCHEMA_VERSION carry the shipped values (1/2)
so ``governance_version`` comparisons behave identically.
"""

from __future__ import annotations

from sb.domain.governance.models import (
    CapabilityNamespaceError,
    CircularDependencyError,
    RegistryValidationError,
)
from sb.spec.authority import TIERS, is_tier_sufficient

__all__ = [
    "CAPABILITY_TO_SUBSYSTEM",
    "REGISTRY_SCHEMA_VERSION",
    "REGISTRY_VERSION",
    "SUBSYSTEM_META",
    "VISIBILITY_TIERS",
    "dependency_order",
    "get_subsystems_for_tier",
    "is_reserved_capability",
    "validate_registry",
]

REGISTRY_VERSION = 1
REGISTRY_SCHEMA_VERSION = 2

#: shipped visibility tier order (utils/visibility_rules.VISIBILITY_TIERS)
#: == sb.spec.authority.TIERS (RC-13 — one order, asserted by test).
VISIBILITY_TIERS: tuple[str, ...] = tuple(TIERS)

_RESERVED_CAPABILITY_PREFIXES: frozenset[str] = frozenset(
    {"_internal", "system", "governance"})

# name -> (visibility_tier, dependencies, soft_dependencies, capabilities)
# Harvested verbatim from the shipped SUBSYSTEMS dict (43 rows, all
# visibility_mode="normal", none hidden).
SUBSYSTEM_META: dict[str, dict] = {
    "admin": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
              "capabilities": ("admin.cog.load", "admin.cog.unload", "admin.cog.reload", "admin.server.stats")},
    "server_management": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                          "capabilities": ()},
    "moderation": {"visibility_tier": "moderator", "dependencies": (), "soft_dependencies": (),
                   "capabilities": ("moderation.warn.apply", "moderation.timeout.apply", "moderation.kick.apply",
                                    "moderation.ban.apply", "moderation.ban.remove", "moderation.log.view",
                                    "moderation.settings.configure")},
    "economy": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("economy.currency.view", "economy.currency.earn", "economy.shop.browse",
                                 "economy.shop.buy", "economy.settings.configure")},
    "inventory": {"visibility_tier": "user", "dependencies": ("economy",), "soft_dependencies": (),
                  "capabilities": ("inventory.item.view", "inventory.item.use", "inventory.craft.recipe")},
    "treasury": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": ("economy",),
                 "capabilities": ("treasury.pool.view", "treasury.pool.contribute", "treasury.pool.disburse")},
    "ticket": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
               "capabilities": ("ticket.ticket.open", "ticket.ticket.manage", "ticket.config.update")},
    "mining": {"visibility_tier": "user", "dependencies": ("economy",), "soft_dependencies": (),
               "capabilities": ("mining.resource.mine", "mining.resource.view")},
    "fishing": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("fishing.catch.fish", "fishing.collection.view")},
    "creature": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                 "capabilities": ("creature.catch.creature", "creature.collection.view")},
    "farm": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": ("economy",),
             "capabilities": ("farm.egg.collect", "farm.coop.manage")},
    "xp": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
           "capabilities": ("xp.rank.view", "xp.leaderboard.view", "xp.settings.configure")},
    "karma": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
              "capabilities": ("karma.card.view", "karma.grant.give", "karma.settings.configure")},
    "role": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
             "capabilities": ("role.settings.configure", "role.threshold.configure",
                              "role.assignment.manage", "role.reaction.manage")},
    "channel": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("channel.create.text", "channel.create.voice", "channel.delete.any",
                                 "channel.restrict.apply", "channel.visibility.configure")},
    "cleanup": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("cleanup.word.add", "cleanup.word.remove", "cleanup.history.scan",
                                 "cleanup.policy.configure")},
    "automod": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("automod.settings.configure",)},
    "image_moderation": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                         "capabilities": ("image_moderation.settings.configure",)},
    "games": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
              "capabilities": ("games.hub.view",)},
    "community": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                  "capabilities": ("community.hub.view",)},
    "community_spotlight": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                            "capabilities": ("community_spotlight.dashboard.view",)},
    "welcome": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("welcome.settings.configure",)},
    "counters": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                 "capabilities": ("counters.settings.configure",)},
    "security": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                 "capabilities": ("security.settings.configure",)},
    "blackjack": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": ("economy",),
                  "capabilities": ("blackjack.game.play", "blackjack.tournament.manage")},
    "casino": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
               "capabilities": ("casino.game.play",)},
    "btd6": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
             "capabilities": ("btd6.query.ask", "btd6.strategy.view", "btd6.diagnostics.view",
                              "btd6.settings.configure")},
    "project_moon": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                     "capabilities": ("project_moon.lookup.view",)},
    "deathmatch": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                   "capabilities": ("deathmatch.game.challenge", "deathmatch.stat.view")},
    "rps_tournament": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                       "capabilities": ("rps_tournament.game.join", "rps_tournament.tournament.manage")},
    "counting": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                 "capabilities": ("counting.game.play", "counting.game.configure")},
    "chain": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
              "capabilities": ("chain.game.play", "chain.game.configure")},
    "leaderboard": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                    "capabilities": ("leaderboard.xp.view", "leaderboard.economy.view")},
    "proof_channel": {"visibility_tier": "staff", "dependencies": (), "soft_dependencies": (),
                      "capabilities": ("proof_channel.access.grant", "proof_channel.access.revoke",
                                       "proof_channel.access.timed", "proof_channel.settings.configure")},
    "utility": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("utility.info.server", "utility.info.user", "utility.tool.ping")},
    "general": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("general.info.view", "general.community.interact")},
    "four_twenty": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
                    "capabilities": ("four_twenty.panel.view",)},
    "help": {"visibility_tier": "user", "dependencies": (), "soft_dependencies": (),
             "capabilities": ("help.menu.view", "help.settings.configure")},
    "diagnostic": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                   "capabilities": ("diagnostic.health.view", "diagnostic.latency.check")},
    "ux_lab": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
               "capabilities": ()},
    "ai": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
           "capabilities": ("ai.platform.view", "ai.diagnostics.view", "ai.provider.view",
                            "ai.routing.view", "ai.settings.configure", "ai.settings.view")},
    "settings": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                 "capabilities": ("settings.manager.view",)},
    "logging": {"visibility_tier": "administrator", "dependencies": (), "soft_dependencies": (),
                "capabilities": ("logging.settings.configure", "logging.channel.bind",
                                 "logging.channel.create")},
}

#: capability string -> owning subsystem (the shipped CAPABILITY_TO_SUBSYSTEM)
CAPABILITY_TO_SUBSYSTEM: dict[str, str] = {
    cap: name
    for name, meta in SUBSYSTEM_META.items()
    for cap in meta["capabilities"]
}


def is_reserved_capability(cap: str) -> bool:
    return cap.split(".")[0] in _RESERVED_CAPABILITY_PREFIXES


def get_subsystems_for_tier(member_tier: str) -> list[str]:
    """Subsystem names whose visibility_tier <= member_tier (shipped
    get_subsystems_for_tier; no internal/hidden rows exist in the data)."""
    return [
        name for name, meta in SUBSYSTEM_META.items()
        if is_tier_sufficient(member_tier, meta["visibility_tier"])
    ]


def dependency_order() -> list[str]:
    """Topological order over hard dependencies (deps before dependents).

    Raises CircularDependencyError on a cycle — the shipped boot-refusal.
    """
    order: list[str] = []
    state: dict[str, int] = {}  # 0=unvisited 1=in-stack 2=done

    def visit(node: str) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            raise CircularDependencyError(node, node)
        state[node] = 1
        for dep in SUBSYSTEM_META.get(node, {}).get("dependencies", ()):
            if state.get(dep) == 1:
                raise CircularDependencyError(node, dep)
            visit(dep)
        state[node] = 2
        order.append(node)

    for name in SUBSYSTEM_META:
        visit(name)
    return order


def validate_registry() -> None:
    """Startup integrity check (shipped validation, the checkable subset):
    capability format {subsystem}.{resource}.{action}, capability prefix
    owns-or-reserved, acyclic hard dependencies, deps resolve."""
    for name, meta in SUBSYSTEM_META.items():
        for cap in meta["capabilities"]:
            parts = cap.split(".")
            if len(parts) != 3 or not all(parts):
                raise CapabilityNamespaceError(
                    f"capability {cap!r} is not {{subsystem}}.{{resource}}.{{action}}")
            if is_reserved_capability(cap):
                raise CapabilityNamespaceError(
                    f"capability {cap!r} uses a reserved namespace prefix")
            if parts[0] != name:
                raise CapabilityNamespaceError(
                    f"capability {cap!r} declared by {name!r} but namespaced "
                    f"to {parts[0]!r}")
        for dep in meta["dependencies"]:
            if dep not in SUBSYSTEM_META:
                raise RegistryValidationError(
                    f"{name!r} depends on unknown subsystem {dep!r}")
    dependency_order()
