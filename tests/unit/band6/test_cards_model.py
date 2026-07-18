"""Band 6 casino — error / edge coverage for the pure card model
(`sb.domain.casino.cards`).

The happy paths (`card()` + `make_deck(shuffle=False)`) are pinned by
`test_band6_deathmatch_casino.py::test_cards_and_hand_evaluator`. This file
pins the module's REFUSAL branches and its ordering / round-trip contract:
- `parse_card` too-short / unknown-rank / unknown-suit refusals,
- `Suit.from_letter` unknown-letter refusal (and case-fold accept),
- `Card.__post_init__` rank-out-of-range refusal,
- the ace-high `order=True` comparison + `sorted()` behavior,
- the `.code` / `str()` round-trip (`parse_card(c.code) == c`).

Pure, stdlib-only, Discord-free — no DB, no bot boot, no golden parity.
"""

from __future__ import annotations

import pytest

from sb.domain.casino.cards import (
    RANK_NAMES,
    RANKS,
    SUITS,
    Card,
    Suit,
    card,
    make_deck,
    parse_card,
)

# --- parse_card refusal branches --------------------------------------------------


@pytest.mark.parametrize("code", ["", "A", "S", "1", " "])
def test_parse_card_too_short_raises(code):
    with pytest.raises(ValueError, match="card code too short"):
        parse_card(code)


def test_parse_card_too_short_message_shows_stripped_code():
    # A whitespace-padded single char is stripped first, then rejected on length.
    with pytest.raises(ValueError, match=r"card code too short: 'A'"):
        parse_card("  A  ")


@pytest.mark.parametrize("code", ["ZS", "1H", "0D", "XC", "150H"])
def test_parse_card_unknown_rank_raises(code):
    with pytest.raises(ValueError, match="unknown rank in card code"):
        parse_card(code)


@pytest.mark.parametrize("code", ["AX", "KZ", "10Q", "2G"])
def test_parse_card_unknown_suit_raises(code):
    # The unknown-suit refusal is raised through Suit.from_letter.
    with pytest.raises(ValueError, match="unknown suit letter"):
        parse_card(code)


def test_card_helper_is_parse_card_alias():
    assert card("AS") == parse_card("AS")


# --- Suit.from_letter -------------------------------------------------------------


@pytest.mark.parametrize(
    "letter,expected",
    [
        ("S", Suit.SPADES),
        ("H", Suit.HEARTS),
        ("D", Suit.DIAMONDS),
        ("C", Suit.CLUBS),
        ("s", Suit.SPADES),  # case-insensitive
        ("h", Suit.HEARTS),
    ],
)
def test_suit_from_letter_accepts(letter, expected):
    assert Suit.from_letter(letter) is expected


@pytest.mark.parametrize("letter", ["X", "Z", "1", "♠", ""])
def test_suit_from_letter_unknown_raises(letter):
    with pytest.raises(ValueError, match="unknown suit letter"):
        Suit.from_letter(letter)


def test_suit_letter_property_roundtrips():
    for suit in Suit:
        assert Suit.from_letter(suit.letter) is suit


# --- Card.__post_init__ rank guard ------------------------------------------------


@pytest.mark.parametrize("bad_rank", [0, 1, 15, 20, -1, 100])
def test_card_rank_out_of_range_raises(bad_rank):
    with pytest.raises(ValueError, match=r"rank must be 2\.\.14"):
        Card(rank=bad_rank, suit=Suit.SPADES)


@pytest.mark.parametrize("good_rank", list(RANKS))
def test_card_accepts_every_valid_rank(good_rank):
    c = Card(rank=good_rank, suit=Suit.SPADES)
    assert c.rank == good_rank


# --- ace-high ordering / sort (order=True) ----------------------------------------


def test_ace_sorts_high():
    ace = Card(rank=14, suit=Suit.SPADES)
    king = Card(rank=13, suit=Suit.SPADES)
    two = Card(rank=2, suit=Suit.SPADES)
    assert two < king < ace
    assert max(two, king, ace) is ace


def test_sort_orders_by_rank_then_suit():
    # order=True sorts by the field order (rank, then suit); Suit's declared
    # order is S < H < D < C, used only as a deterministic tiebreak.
    same_rank = [
        Card(rank=10, suit=Suit.CLUBS),
        Card(rank=10, suit=Suit.SPADES),
        Card(rank=10, suit=Suit.DIAMONDS),
        Card(rank=10, suit=Suit.HEARTS),
    ]
    assert sorted(same_rank) == [
        Card(rank=10, suit=Suit.SPADES),
        Card(rank=10, suit=Suit.HEARTS),
        Card(rank=10, suit=Suit.DIAMONDS),
        Card(rank=10, suit=Suit.CLUBS),
    ]


def test_sort_rank_dominates_suit():
    low_high_suit = Card(rank=2, suit=Suit.CLUBS)
    high_low_suit = Card(rank=14, suit=Suit.SPADES)
    # Rank leads, so the deuce sorts below the ace despite its "higher" suit.
    assert sorted([high_low_suit, low_high_suit]) == [low_high_suit, high_low_suit]


def test_suit_ordering_is_declaration_order():
    assert sorted(Suit) == [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]


def test_suit_compare_across_type_is_notimplemented():
    assert Suit.SPADES.__lt__("nope") is NotImplemented


# --- .code / str() round-trip -----------------------------------------------------


def test_code_roundtrips_across_full_deck():
    for c in make_deck(shuffle=False):
        assert parse_card(c.code) == c


def test_code_and_str_shapes():
    ten_h = Card(rank=10, suit=Suit.HEARTS)
    assert ten_h.code == "10H"
    assert str(ten_h) == "10♥"
    ace_s = Card(rank=14, suit=Suit.SPADES)
    assert ace_s.code == "AS"
    assert str(ace_s) == "A♠"


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("TD", Card(rank=10, suit=Suit.DIAMONDS)),  # "T" alias for ten
        ("td", Card(rank=10, suit=Suit.DIAMONDS)),  # lowercase rank + suit
        ("as", Card(rank=14, suit=Suit.SPADES)),
        ("kh", Card(rank=13, suit=Suit.HEARTS)),
    ],
)
def test_parse_card_accepts_aliases_and_lowercase(alias, expected):
    assert parse_card(alias) == expected


def test_rank_name_property_matches_table():
    for rank, name in RANK_NAMES.items():
        assert Card(rank=rank, suit=Suit.SPADES).rank_name == name


def test_make_deck_is_full_and_unique():
    deck = make_deck(shuffle=False)
    assert len(deck) == 52
    assert len(set(deck)) == 52
    assert {c.suit for c in deck} == set(SUITS)
