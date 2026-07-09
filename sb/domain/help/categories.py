"""The help CATEGORY map — the shipped mother-hub presentation, harvested
VERBATIM from disbot @7f7628e1 (utils/hub_registry.py HUBS + the
utils/subsystem_registry.py SUBSYSTEMS display metadata / parent_hub
assignments).

Why this lives here (ledgered, D-0055): the frozen design-spec §2.1 homes
hub placement on the manifest (`SubsystemManifest.parent_hub` [A], sim-owned;
hub presentation in a `HubSpec` facet) and makes hub topology the FIRST sim
pass — an owner-ratified arrangement decision (completion-report flag 21).
Until that ratification, this module carries the SHIPPED assignments as the
legacy seed (the same posture as the band-1 lock overlays: legacy-seed
Exempt), so the help projection can group without minting manifest schema
ahead of the owner's call. The COMMAND DATA never lives here — rosters are
computed from the live manifest inventory (anti-drift: a subsystem this map
does not know falls into the OTHER category instead of shedding).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CATEGORIES",
    "OTHER_CATEGORY",
    "SUBSYSTEM_PRESENTATION",
    "category_for_subsystem",
    "category_option",
    "category_rosters",
    "subsystem_option",
]


@dataclass(frozen=True)
class HelpCategory:
    """One mother-hub category (shipped HubEntry presentation fields)."""

    key: str
    display_name: str
    emoji: str
    purpose: str


#: shipped HUBS tuple order drives display order (hub_registry.py verbatim).
CATEGORIES: tuple[HelpCategory, ...] = (
    HelpCategory("games", "Games", "🎮", "Game flows and tournaments."),
    HelpCategory("btd6", "BTD6 Assistant", "🐵",
                 "Bloons Tower Defense 6 assistant — lookups, strategy "
                 "guidance, and round breakdowns."),
    HelpCategory("project_moon", "Project Moon", "🌑",
                 "Limbus Company knowledge — Sinners, Sins, status keywords, "
                 "damage types, and E.G.O grades."),
    HelpCategory("economy", "Economy", "💰",
                 "Currency, items, work, shop, and standings."),
    HelpCategory("moderation", "Moderation & Safety", "🛡️",
                 "Warnings, timeouts, bans, cleanup, audit logs."),
    HelpCategory("community", "Community", "🌱",
                 "Progression, roles, and community activities."),
    HelpCategory("utility", "Utility", "🧰",
                 "Info, tools, and discovery commands."),
    HelpCategory("admin", "Server & Admin", "⚙️",
                 "Settings, diagnostics, server management, channels, AI, "
                 "and ops."),
)

#: the projection's honesty valve: subsystems the shipped map never knew
#: group here instead of shedding (new-architecture keys land visibly).
OTHER_CATEGORY = HelpCategory("other", "Other", "📦",
                              "Everything not yet homed under a category.")

#: shipped parent_hub assignments (subsystem_registry.py verbatim; hub-host
#: subsystems belong to their own hub). Two non-shipped entries, ledgered in
#: D-0055: `projmoon` is the ported project_moon key; `setup` is a
#: new-architecture subsystem seeded under admin (the operator section).
_PARENT_HUB: dict[str, str] = {
    # games (roster order = shipped primary_children order)
    "games": "games", "blackjack": "games", "casino": "games",
    "deathmatch": "games", "rps_tournament": "games", "mining": "games",
    "counting": "games", "chain": "games", "fishing": "games",
    "creature": "games", "farm": "games",
    # btd6 / project_moon (hub hosts)
    "btd6": "btd6",
    "projmoon": "project_moon",
    # economy
    "economy": "economy", "inventory": "economy", "leaderboard": "economy",
    "treasury": "economy",
    # moderation
    "moderation": "moderation", "automod": "moderation",
    "image_moderation": "moderation", "cleanup": "moderation",
    "logging": "moderation", "proof_channel": "moderation",
    "security": "moderation",
    # community
    "community": "community", "xp": "community", "karma": "community",
    "community_spotlight": "community", "role": "community",
    "welcome": "community", "counters": "community", "ticket": "community",
    # utility
    "utility": "utility", "general": "utility", "four_twenty": "utility",
    # admin
    "admin": "admin", "ux_lab": "admin", "channel": "admin",
    "server_management": "admin", "ai": "admin", "settings": "admin",
    "diagnostic": "admin",
    "setup": "admin",              # new-architecture key (ledgered seed)
}

#: shipped roster order per hub (primary_children verbatim, host first) —
#: used to order subsystems inside a category; unknown keys append
#: alphabetically after the shipped ones.
_ROSTER_ORDER: dict[str, tuple[str, ...]] = {
    "games": ("games", "blackjack", "casino", "deathmatch", "rps_tournament",
              "mining", "counting", "chain", "fishing", "creature", "farm"),
    "btd6": ("btd6",),
    "project_moon": ("projmoon",),
    "economy": ("economy", "inventory", "leaderboard", "treasury"),
    "moderation": ("moderation", "automod", "image_moderation", "cleanup",
                   "logging", "proof_channel", "security"),
    "community": ("community", "xp", "karma", "community_spotlight", "role",
                  "welcome", "counters", "ticket"),
    "utility": ("utility", "general", "four_twenty"),
    "admin": ("admin", "ux_lab", "channel", "server_management", "ai",
              "settings", "diagnostic", "setup"),
}

#: shipped per-subsystem presentation (subsystem_registry.py display_name +
#: emoji, verbatim; `projmoon` carries the shipped project_moon entry).
#: An unmapped key renders as its bare manifest key — visible, never shed.
SUBSYSTEM_PRESENTATION: dict[str, tuple[str, str]] = {
    "admin": ("Administration", "⚙️"),
    "server_management": ("Server Management", "🧭"),
    "moderation": ("Moderation", "🔨"),
    "economy": ("Economy", "💰"),
    "inventory": ("Inventory", "🎒"),
    "treasury": ("Treasury", "🏛️"),
    "ticket": ("Support Tickets", "🎫"),
    "mining": ("Mining", "⛏️"),
    "fishing": ("Fishing", "🎣"),
    "creature": ("Creatures", "🐾"),
    "farm": ("Chicken Farm", "🐔"),
    "xp": ("XP & Levels", "⭐"),
    "karma": ("Karma", "✨"),
    "role": ("Roles", "🎭"),
    "channel": ("Channels", "📐"),
    "cleanup": ("Cleanup", "🧹"),
    "automod": ("Automod", "🛡️"),
    "image_moderation": ("Image moderation", "🖼️"),
    "games": ("Games", "🎮"),
    "community": ("Community", "🌱"),
    "community_spotlight": ("Community Spotlight", "🌟"),
    "welcome": ("Welcome", "👋"),
    "counters": ("Server Counters", "📊"),
    "security": ("Server Security", "🛡️"),
    "blackjack": ("Blackjack", "🃏"),
    "casino": ("Casino", "🎰"),
    "btd6": ("BTD6 Assistant", "🐵"),
    "projmoon": ("Project Moon", "🌑"),
    "deathmatch": ("Deathmatch", "⚔️"),
    "rps_tournament": ("Rock Paper Scissors", "✂️"),
    "counting": ("Counting", "🔢"),
    "chain": ("Word Chain", "🔗"),
    "leaderboard": ("Leaderboard", "🏆"),
    "proof_channel": ("Proof Channel", "📋"),
    "utility": ("Utility", "🔧"),
    "general": ("General", "💬"),
    "four_twenty": ("420", "🍃"),
    "help": ("Help", "📚"),
    "diagnostic": ("Diagnostics", "🩺"),
    "ux_lab": ("UX Lab", "🧪"),
    "ai": ("AI Platform", "🤖"),
    "settings": ("Settings Manager", "⚙️"),
    "logging": ("Server Logging", "📝"),
    "setup": ("Setup", "🧰"),      # new-architecture key (not shipped)
}

#: the shipped rule: Help itself never surfaces under any hub — the index
#: IS the help surface (hub_registry.py "Help itself stays top-level").
_EXCLUDED = frozenset({"help"})


def category_for_subsystem(key: str) -> str:
    return _PARENT_HUB.get(key, OTHER_CATEGORY.key)


def category_rosters(inventory_keys) -> dict[str, tuple[str, ...]]:
    """category key → ordered member subsystems, computed from the LIVE
    inventory (the anti-drift core: rosters are the parent_hub filter, never
    hand-listed data). Shipped roster order first, stragglers alphabetical;
    only non-empty categories appear."""
    members: dict[str, list[str]] = {}
    for key in inventory_keys:
        if key in _EXCLUDED:
            continue
        members.setdefault(category_for_subsystem(key), []).append(key)
    out: dict[str, tuple[str, ...]] = {}
    for cat in (*CATEGORIES, OTHER_CATEGORY):
        present = set(members.get(cat.key, ()))
        if not present:
            continue
        shipped = [k for k in _ROSTER_ORDER.get(cat.key, ()) if k in present]
        rest = sorted(present - set(shipped))
        out[cat.key] = tuple(shipped + rest)
    return out


def category_by_key(key: str) -> HelpCategory | None:
    for cat in (*CATEGORIES, OTHER_CATEGORY):
        if cat.key == key:
            return cat
    return None


def category_option(cat: HelpCategory) -> str:
    """The select-option string (label == value in the render grammar)."""
    return f"{cat.emoji} {cat.display_name}"


def category_for_option(option: str) -> HelpCategory | None:
    for cat in (*CATEGORIES, OTHER_CATEGORY):
        if option == category_option(cat):
            return cat
    return None


def subsystem_display(key: str) -> tuple[str, str]:
    """(display_name, emoji) — the bare key when the shipped map is silent."""
    return SUBSYSTEM_PRESENTATION.get(key, (key, "🔹"))


def subsystem_option(key: str) -> str:
    display, emoji = subsystem_display(key)
    return f"{emoji} {display}"


def subsystem_for_option(option: str, roster) -> str | None:
    for key in roster:
        if option == subsystem_option(key):
            return key
    return None
