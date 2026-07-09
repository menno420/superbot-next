"""Counting V/M/A decision core (band 6) — the shipped
``cogs/counting/handler.py`` ``compute_decision`` made HEADLESS: state-in
/ decision-out, mutates ``channel_data`` in place, zero Discord types
(the shipped module's own documented pure-ish shape, with the
``discord.Message`` parameter narrowed to ``content`` +
``author_mention``). The Discord side-effects (delete / reply /
reaction) are the MESSAGE FEED's job — ``apply_decision`` stays with the
live adapter (the moderation auto-delete routing rides the band-2
moderation seam there).

Copy is shipped-verbatim; the reply strings are part of the parity
surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sb.domain.counting import game_logic, parsing

__all__ = ["CountingDecision", "compute_decision", "reset_channel_data"]

# Modes that reset to 0 on a wrong count (everything in the bot today).
_RESET_TO_ZERO_MODES = (
    "normal",
    "random",
    "skip",
    "multiples",
    "prime",
    "fibonacci",
    "squares",
    "cubes",
    "factorials",
    "custom",
)

# Modes whose success path advances a sequence_index counter.
_SEQUENCE_MODES = ("fibonacci", "squares", "cubes", "factorials", "custom")


@dataclass(frozen=True)
class CountingDecision:
    """Side-effects for one counting message (applied by the feed)."""

    accepted: bool
    delete_message: bool = False
    reply: str | None = None
    add_reaction: str | None = None
    state_mutated: bool = False
    # Seconds before the bot's reply auto-deletes; ``None`` keeps it.
    # Random mode's range hints must persist so players can see the
    # current window between guesses.
    reply_delete_after: int | None = 5


def compute_decision(
    *,
    content: str,
    author_mention: str,
    channel_data: dict[str, Any],
    user_id: str,
) -> CountingDecision:
    """Validate the message, mutate ``channel_data`` in place, return a
    Decision. The caller owns the channel-state row (the K7 leg's txn is
    the lock the shipped scope_lock provided)."""
    mode = channel_data.get("mode", "normal")
    taking_turns = channel_data.get("taking_turns", False)
    current_count = channel_data.get("current_count", 0)
    last_user = channel_data.get("last_user")
    multiple = channel_data.get("multiple")
    reset_on_wrong = channel_data.get("reset_on_wrong_count", False)

    parsed = parsing.parse_message(content)
    if parsed is None:
        return CountingDecision(
            accepted=False,
            delete_message=True,
            reply=(
                f"{author_mention}, please send a valid number "
                f"or mathematical expression."
            ),
        )

    if mode == "random":
        return _decide_random(channel_data, parsed, user_id, author_mention)

    expected = game_logic.calculate_expected_count(
        channel_data, current_count, mode)

    if parsed != expected:
        if reset_on_wrong:
            reset_channel_data(channel_data, mode)
            return CountingDecision(
                accepted=False,
                delete_message=True,
                reply=(
                    f"{author_mention}, incorrect count! "
                    f"The count has been reset."
                ),
                state_mutated=True,
            )
        return CountingDecision(
            accepted=False,
            delete_message=True,
            reply=(
                f"{author_mention}, incorrect count! "
                f"The next number should be {expected}."
            ),
        )

    if taking_turns and user_id == last_user:
        return CountingDecision(
            accepted=False,
            delete_message=True,
            reply=f"{author_mention}, you cannot count twice in a row!",
        )

    if mode == "multiples" and multiple and parsed % multiple != 0:
        return CountingDecision(
            accepted=False,
            delete_message=True,
            reply=(
                f"{author_mention}, please count in multiples of {multiple}."
            ),
        )

    if mode == "prime" and not game_logic.is_prime(parsed):
        return CountingDecision(
            accepted=False,
            delete_message=True,
            reply=f"{author_mention}, please count prime numbers only.",
        )

    # Success — mutate channel_data in place.
    channel_data["current_count"] = parsed
    channel_data["last_user"] = user_id
    channel_data["last_count_time"] = datetime.now(
        tz=timezone.utc).timestamp()
    if mode in _SEQUENCE_MODES:
        channel_data["sequence_index"] = channel_data.get(
            "sequence_index", 0) + 1
    leaderboard = channel_data.get("leaderboard", {})
    leaderboard[user_id] = leaderboard.get(user_id, 0) + 1
    channel_data["leaderboard"] = leaderboard

    return CountingDecision(
        accepted=True,
        add_reaction="✅",
        state_mutated=True,
    )


def reset_channel_data(channel_data: dict[str, Any], mode: str) -> None:
    """Wipe channel_data to the start-of-match state, preserving config."""
    channel_data["current_count"] = (
        0 if mode in _RESET_TO_ZERO_MODES else 1000)
    channel_data["sequence_index"] = 0
    channel_data["last_user"] = None
    channel_data["leaderboard"] = {}
    channel_data["last_count_time"] = datetime.now(
        tz=timezone.utc).timestamp()


def _decide_random(
    channel_data: dict[str, Any],
    parsed: int,
    user_id: str,
    author_mention: str,
) -> CountingDecision:
    """Decision for ``random`` mode — a guess-the-secret-number game."""
    target = channel_data.get("next_expected")
    lo = channel_data.get("range_lo")
    hi = channel_data.get("range_hi")
    if not (isinstance(target, int) and isinstance(lo, int)
            and isinstance(hi, int)):
        # Legacy / missing state — (re)initialise a round so play continues.
        target, lo, hi = game_logic.start_random_round(
            int(channel_data.get("current_count", 0) or 0),
        )
        channel_data["next_expected"] = target
        channel_data["range_lo"], channel_data["range_hi"] = lo, hi

    if parsed == target:
        channel_data["current_count"] = parsed
        channel_data["last_user"] = user_id
        leaderboard = channel_data.get("leaderboard", {})
        leaderboard[user_id] = leaderboard.get(user_id, 0) + 1
        channel_data["leaderboard"] = leaderboard
        n_target, n_lo, n_hi = game_logic.start_random_round(parsed)
        channel_data["next_expected"] = n_target
        channel_data["range_lo"], channel_data["range_hi"] = n_lo, n_hi
        return CountingDecision(
            accepted=True,
            add_reaction="✅",
            state_mutated=True,
            reply=(
                f"✅ Correct — it was **{parsed}**! "
                f"Next secret number is between **{n_lo}–{n_hi}**."
            ),
            reply_delete_after=None,
        )

    n_lo, n_hi = game_logic.narrow_random_range(lo, hi, target)
    channel_data["range_lo"], channel_data["range_hi"] = n_lo, n_hi
    direction = "Higher" if parsed < target else "Lower"
    return CountingDecision(
        accepted=False,
        state_mutated=True,
        reply=(
            f"❌ Not **{parsed}**. {direction} — it's between "
            f"**{n_lo}–{n_hi}**."
        ),
        reply_delete_after=None,
    )
