"""Karma reads + the react-to-thank core (band 4).

``get_record`` is the shipped typed read (KarmaRecord). ``handle_reaction``
is the shipped on_raw_reaction_add flow as a headless core: the fast
policy gate (one settings read, bail unless enabled + the trigger emoji
matches), then the SAME audited ``karma.give`` op with source="reaction"
— blocked grants swallow silently (a reaction must never spam the
channel). The REACTION FEED that calls it (and the bot-author/self
pre-filters that need Discord message objects) arms with the message
band — the shipped cog kept those exact checks cog-side too.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["KarmaRecord", "get_record", "handle_reaction", "karma_card_text"]


@dataclass(frozen=True)
class KarmaRecord:
    """Typed read-only view of a member's karma standing (shipped)."""

    points: int
    received_count: int
    given_count: int
    rank: int | None


async def get_record(guild_id: int, user_id: int) -> KarmaRecord:
    """Zeros when no row exists; rank only for positive totals (shipped)."""
    from sb.domain.karma import store

    row = await store.get_karma(user_id, guild_id)
    points = int(row.get("karma_points", 0) or 0)
    rank = await store.karma_rank(user_id, guild_id) if points > 0 else None
    return KarmaRecord(
        points=points,
        received_count=int(row.get("received_count", 0) or 0),
        given_count=int(row.get("given_count", 0) or 0),
        rank=rank,
    )


def karma_card_text(user_id: int, record: KarmaRecord) -> str:
    """The shipped karma card, text-rendered (field set verbatim)."""
    rank_line = f"#{record.rank}" if record.rank is not None else "unranked"
    return (f"✨ **Karma — <@{user_id}>**\n"
            f"Karma: **{record.points}** ✨ · Rank: {rank_line}\n"
            f"Activity: received **{record.received_count}** · "
            f"given **{record.given_count}**\n"
            f"*Thank helpful members with `!thanks @user`*")


async def handle_reaction(*, guild_id: int, reactor_id: int,
                          author_id: int, emoji: str) -> object | None:
    """React-to-thank. Returns the WorkflowResult when a grant ran,
    ``None`` when the gate bailed or the grant was blocked (silent by
    design). Caller pre-filters bot reactors/authors (Discord objects)."""
    from types import SimpleNamespace

    from sb.domain.karma.policy import load_policy
    from sb.kernel.interaction.errors import ValidatorError
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    policy = await load_policy(guild_id)
    if not policy.enabled or not policy.reaction_emoji:
        return None
    if emoji != policy.reaction_emoji:
        return None
    if author_id == reactor_id:
        return None                      # skip the write path entirely

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=reactor_id, actor_type="user"),
        guild_id=guild_id,
        request_id=f"karma:reaction:{reactor_id}:{author_id}",
        confirmed=True,
        params={"target_id": author_id, "source": "reaction"})
    try:
        return await engine.run(WorkflowRef("karma.give"), ctx)
    except ValidatorError:
        return None                      # disabled/self/cooldown/cap — silent
