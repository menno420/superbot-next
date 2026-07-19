"""Namespaced-predicate grammar tests (frozen L0 spec, `sb/spec/refs.py`).

Pins the two pure parsers that gate every `enabled_when` / `visible_when`
predicate string — `is_namespaced_predicate` (the whitelist gate) and
`parse_namespaced_predicate` (the `<kind>:<key>[=<value>]` splitter). These are
stdlib-only grammar leaves that never raise on a wrong *answer*, only on
malformed input, so the value tie-break and the empty-key asymmetry are the
assertions that earn their keep. Each was verified against a live run of the
real functions before being committed.
"""

from __future__ import annotations

import pytest

from sb.spec.refs import (
    NAMESPACED_PREDICATE_HEADS,
    PredicateRef,
    is_namespaced_predicate,
    parse_namespaced_predicate,
)


# --- the whitelist itself -------------------------------------------------

def test_heads_are_the_four_known_kinds() -> None:
    # The gate and the parser share this tuple; pin it verbatim so a silent
    # add/remove of a head is caught here rather than downstream.
    assert NAMESPACED_PREDICATE_HEADS == (
        "setting", "binding", "capability", "flag")


# --- is_namespaced_predicate: the gate ------------------------------------

def test_empty_string_is_the_constant_true_predicate() -> None:
    # "" short-circuits to True (the constant-true predicate) BEFORE any split.
    assert is_namespaced_predicate(PredicateRef("")) is True


@pytest.mark.parametrize("head", NAMESPACED_PREDICATE_HEADS)
def test_each_known_head_with_a_key_is_namespaced(head: str) -> None:
    assert is_namespaced_predicate(PredicateRef(f"{head}:some.key")) is True


def test_unknown_head_is_not_namespaced() -> None:
    # An unregistered head falls through to the registered-ref path, not parsed.
    assert is_namespaced_predicate(PredicateRef("mystery:x")) is False


def test_no_colon_is_not_namespaced() -> None:
    # No separator -> registered form (a bare handler-style name).
    assert is_namespaced_predicate(PredicateRef("setting")) is False


def test_leading_colon_empty_head_is_not_namespaced() -> None:
    # partition(":") yields head="" which is not in the whitelist.
    assert is_namespaced_predicate(PredicateRef(":foo")) is False


def test_head_match_is_case_sensitive() -> None:
    # "Setting" != "setting" — the whitelist is exact-case.
    assert is_namespaced_predicate(PredicateRef("Setting:foo")) is False


def test_gate_accepts_empty_key_even_though_parse_rejects_it() -> None:
    # The sharp asymmetry: the gate only checks (sep present AND head known),
    # so "setting:" passes the gate — but parse (below) raises on the empty key.
    # Pinned together with the parse-side raise so a refactor that "aligns" the
    # two cannot silently change which strings reach the parser.
    assert is_namespaced_predicate(PredicateRef("setting:")) is True


# --- parse_namespaced_predicate: the splitter -----------------------------

def test_parse_key_only_yields_none_value() -> None:
    # No "=" -> value is None (downstream: a truthiness-only check).
    assert parse_namespaced_predicate("setting:foo") == ("setting", "foo", None)


def test_parse_key_equals_value() -> None:
    assert parse_namespaced_predicate(
        "setting:foo=bar") == ("setting", "foo", "bar")


def test_trailing_equals_yields_empty_string_not_none() -> None:
    # THE tie-break: a trailing "=" means value == "" (compare-to-empty), which
    # is a DIFFERENT downstream semantic than a missing "=" (value None). A
    # `.split("=")` / `if "=" in rest` refactor would collapse the two.
    assert parse_namespaced_predicate(
        "setting:foo=") == ("setting", "foo", "")


def test_parse_splits_on_first_equals_only() -> None:
    # Later "=" characters stay in the value (partition, not split).
    assert parse_namespaced_predicate(
        "setting:foo=bar=baz") == ("setting", "foo", "bar=baz")


def test_parse_preserves_dotted_key_whole() -> None:
    # The key is returned intact; the subsystem.name split happens downstream.
    assert parse_namespaced_predicate(
        "setting:a.b.c=x") == ("setting", "a.b.c", "x")


@pytest.mark.parametrize("head", NAMESPACED_PREDICATE_HEADS)
def test_parse_accepts_every_known_head(head: str) -> None:
    assert parse_namespaced_predicate(f"{head}:k") == (head, "k", None)


@pytest.mark.parametrize("bad", ["", "setting", "mystery:x"])
def test_parse_rejects_non_namespaced(bad: str) -> None:
    # Empty string, bare head (no colon), and unknown head all fail the
    # head/sep check. Note "" is the CALLER's short-circuit — the parser itself
    # never silently accepts it.
    with pytest.raises(ValueError, match="not a namespaced predicate"):
        parse_namespaced_predicate(bad)


@pytest.mark.parametrize("bad", ["setting:", "setting:=bar"])
def test_parse_rejects_empty_key(bad: str) -> None:
    # "setting:" (nothing after the colon) and "setting:=bar" (empty key before
    # the "=") both raise — the key is mandatory even when a value is present.
    with pytest.raises(ValueError, match="empty key"):
        parse_namespaced_predicate(bad)
