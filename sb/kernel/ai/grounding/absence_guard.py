"""False-absence contradiction guard (K10) — hoisted from shipped
``disbot/utils/btd6/absence_guard.py`` @7f7628e1 with the attribute table
turned into a REGISTRY (the shipped paragon-existence attribute is domain
data — band 7 registers it via :func:`register_existence_attribute`).

The positive faithfulness verifier catches ungrounded POSITIVES; this
catches the false NEGATIVE — a reply fluently asserting "<subject> has no
<attribute>" when the grounded haystack AFFIRMS it. By construction it
can never block a *true* negative: a true "no" has no contradicting
positive in the grounding, so nothing fires. A contradicted claim costs
one regeneration before the deterministic refusal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "ExistenceAttribute",
    "clear_attributes_for_tests",
    "contradicted_absence_claims",
    "register_existence_attribute",
    "registered_attributes",
]

# Sentence splitter — good enough for model prose.
_SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")


@dataclass(frozen=True)
class ExistenceAttribute:
    """One binary "does <subject> have <attribute>?" fact the gate checks.

    ``affirm_re`` reads, from the grounded haystack, the subject(s) the
    data AFFIRMS have the attribute (group 1 = the subject's proper name).
    ``deny_res``: a sentence matching any of these (case-insensitively)
    DENIES the attribute. ``exclude_qualifiers``: words that turn a "no
    <attr>" into a non-absence ("no SECOND paragon") — a sentence
    containing one is skipped even when a deny pattern matched.
    """

    name: str
    affirm_re: re.Pattern[str]
    deny_res: tuple[re.Pattern[str], ...]
    exclude_qualifiers: frozenset[str]
    owner_subsystem: str = "kernel"


_ATTRIBUTES: dict[str, ExistenceAttribute] = {}


def register_existence_attribute(attr: ExistenceAttribute) -> ExistenceAttribute:
    """Register an attribute (band 7 registers its domain table; each new
    attribute should be live-verified before trusting it — shipped
    Q-0105 caution). Differing re-registration raises."""
    prior = _ATTRIBUTES.get(attr.name)
    if prior is not None and prior != attr:
        raise ValueError(
            f"existence attribute {attr.name!r} already registered by "
            f"{prior.owner_subsystem!r}",
        )
    _ATTRIBUTES[attr.name] = attr
    return attr


def registered_attributes() -> tuple[ExistenceAttribute, ...]:
    return tuple(_ATTRIBUTES[k] for k in sorted(_ATTRIBUTES))


def clear_attributes_for_tests() -> None:
    _ATTRIBUTES.clear()


def contradicted_absence_claims(answer_text: str, haystack: str) -> tuple[str, ...]:
    """The reply sentences that deny an attribute the grounding affirms.

    Empty unless the reply makes a grounding-CONTRADICTED absence claim
    (a true "no", or any absence about a subject the grounding never
    affirmed, returns nothing). Shipped mechanics verbatim.
    """
    if not answer_text or not haystack:
        return ()

    offending: list[str] = []
    sentences = _SENTENCE_SPLIT.split(answer_text)
    for attr in registered_attributes():
        affirmed = {m.group(1).lower() for m in attr.affirm_re.finditer(haystack)}
        if not affirmed:
            continue
        for sentence in sentences:
            low = sentence.lower()
            if not any(pat.search(low) for pat in attr.deny_res):
                continue
            if any(q in low for q in attr.exclude_qualifiers):
                continue
            if any(subject in low for subject in affirmed):
                offending.append(sentence.strip())

    # Preserve order, drop duplicates.
    return tuple(dict.fromkeys(offending))
