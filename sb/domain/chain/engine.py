"""Chain rule core (band 6) — the shipped ``_process_chain_message``
decision made HEADLESS (state-in / decision-out, zero Discord types):
a configured channel allows only the chain word (case-insensitive,
whole message) and/or caps the word count. Copy is shipped-verbatim —
the warning strings are parity surface."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ChainDecision", "check_message"]


@dataclass(frozen=True)
class ChainDecision:
    """The feed's side-effects for one message in a chain channel."""

    delete_message: bool
    warning: str | None = None    # posted then auto-deleted (~5s) by the feed
    record_progress: bool = False  # increment chain_count (allowed message)


def check_message(*, content: str, author_mention: str,
                  word: str | None, word_limit: int | None) -> ChainDecision:
    """The shipped rule: exact allowed word (lowercased strip) and/or
    the word-count cap; allowed messages advance the chain."""
    allowed_word = word or None
    limit = word_limit or 0

    delete_message = False
    if allowed_word and content.strip().lower() != allowed_word.lower():
        delete_message = True
    if limit and len(content.strip().split()) > limit:
        delete_message = True

    if not delete_message:
        return ChainDecision(delete_message=False, record_progress=True)

    warning_message = f"{author_mention}, your message was deleted."
    if allowed_word and limit:
        warning_message += (
            f" Only the word `{allowed_word}` is allowed, and messages "
            f"must be at most {limit} words."
        )
    elif allowed_word:
        warning_message += (
            f" Only the word `{allowed_word}` is allowed in this channel."
        )
    elif limit:
        warning_message += f" Messages must be at most {limit} words."
    return ChainDecision(delete_message=True, warning=warning_message)
