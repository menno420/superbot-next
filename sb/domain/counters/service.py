"""COUNTERS domain service (parity flip) — the shipped effective-policy
read set (disbot services/counter_config.py ``load_policy``) plus the
shipped count computation (services/counter_service.py
``compute_counts``) behind the kernel settings/binding seams and the
utility guild-directory port.

The v1 slice is READ-ONLY: ``!counters`` / ``/counters`` render the
effective policy + live values (cogs/counters_cog.py); the periodic
rename loop (``sync_guild`` over the ~10-min ``tasks.loop``) arms with
the channel-ops port — its templates and bindings already live in the
declared settings, so this module carries the whole read vocabulary now
and the rename effect later.
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.domain.counters import DEFAULT_TEMPLATES, render_counter_name

__all__ = [
    "KINDS",
    "CounterCounts",
    "CounterPolicy",
    "compute_counts",
    "load_policy",
    "render_counter_name",
]

#: The shipped kind vocabulary IN ORDER (services/counter_config.py
#: ``KINDS`` — the status embed renders rows in this order).
KINDS: tuple[str, ...] = ("total", "humans", "bots")


@dataclass(frozen=True)
class CounterPolicy:
    """The shipped effective counter policy (counter_config.CounterPolicy
    read set — the fields the status embed renders): the master flag
    plus one ``(channel_id, template)`` pair per kind."""

    enabled: bool
    total_channel_id: int | None
    humans_channel_id: int | None
    bots_channel_id: int | None
    total_template: str
    humans_template: str
    bots_template: str

    def channel_for(self, kind: str) -> int | None:
        return {
            "total": self.total_channel_id,
            "humans": self.humans_channel_id,
            "bots": self.bots_channel_id,
        }.get(kind)

    def template_for(self, kind: str) -> str:
        return {
            "total": self.total_template,
            "humans": self.humans_template,
            "bots": self.bots_template,
        }.get(kind) or DEFAULT_TEMPLATES[kind]


@dataclass(frozen=True)
class CounterCounts:
    """The shipped live member stats (counter_service.CounterCounts)."""

    total: int
    humans: int
    bots: int

    def for_kind(self, kind: str) -> int:
        """The count for a counter ``kind`` (0 for an unknown kind) —
        shipped ``CounterCounts.for_kind`` verbatim."""
        return {"total": self.total, "humans": self.humans,
                "bots": self.bots}.get(kind, 0)


def _as_bool(value: object, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return str(value).strip().lower() in ("1", "true", "yes", "on")


async def _bound(guild_id: int, name: str) -> int | None:
    """A counter channel binding (subsystem_bindings route-truth; the
    welcome ``bound_channel`` posture — headless reads as unbound,
    never a raise)."""
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "counters", name)
    except Exception:  # noqa: BLE001 — no DB (headless) reads as unbound
        return None


async def load_policy(guild_id: int) -> CounterPolicy:
    """Effective policy through THE kernel settings seam (declared
    defaults are the shipped defaults — sb/manifest/counters.py carries
    services/counter_config.py's templates verbatim)."""
    from sb.kernel.settings import resolve

    async def _template(name: str, kind: str) -> str:
        value = await resolve(guild_id, "counters", name)
        text = str(value).strip() if value is not None else ""
        return text or DEFAULT_TEMPLATES[kind]

    return CounterPolicy(
        enabled=_as_bool(await resolve(guild_id, "counters", "enabled"),
                         False),
        total_channel_id=await _bound(guild_id, "total_channel"),
        humans_channel_id=await _bound(guild_id, "humans_channel"),
        bots_channel_id=await _bound(guild_id, "bots_channel"),
        total_template=await _template("total_template", "total"),
        humans_template=await _template("humans_template", "humans"),
        bots_template=await _template("bots_template", "bots"),
    )


async def compute_counts(guild_id: int) -> CounterCounts:
    """The live member stats through the utility guild-directory port —
    shipped ``compute_counts`` semantics: ``total`` prefers
    ``guild.member_count``, ``bots`` comes from the member cache's bot
    flags, ``humans`` is the remainder (never negative)."""
    from sb.domain.utility.service import guild_directory

    info = await guild_directory().guild_info(guild_id)
    total = max(int(info.member_count or 0), 0)
    bots = max(int(getattr(info, "bots", 0) or 0), 0)
    return CounterCounts(total=total, humans=max(total - bots, 0), bots=bots)
