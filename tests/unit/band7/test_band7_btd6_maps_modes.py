"""Band 7 — btd6 resolver maps/modes matching (the #144 parked domain
item): the shipped ``btd6_resolver_service`` maps/modes alias matching,
the ``btd6_response_builder.for_map`` / ``for_mode`` answer cards, the
``btd6_ai_service.deterministic_answer`` shipped precedence order
(towers → heroes → maps → modes → rounds → bloons), and the test-intent
card's Maps/Modes rows over the matched canonicals.

Every semantic below is oracle-reconstructed via search_code fragments
(reconstruction refs d647b2e9 / 7349c8a7 — trap 24: the oracle default
branch is AHEAD of the corpus pin 7f7628e1; the fragments were diffed
against the goldens FIRST and the golden-pinned empty state is pinned
here too)."""

from __future__ import annotations

from sb.domain.btd6 import dataset, oracle_cards, resolver


# --- dataset typed accessors --------------------------------------------------------


def test_maps_accessor_loads_typed_entries():
    entries = dataset.maps()
    assert len(entries) == 86
    dark_castle = dataset.get_map("dark_castle")
    assert dark_castle is not None
    assert dark_castle.canonical == "Dark Castle"
    assert dark_castle.difficulty == "Expert"
    assert dark_castle.has_water is True
    # blank removables means "no data", never "none" (shipped curation note)
    assert dark_castle.removables == ""


def test_modes_accessor_none_cash_for_modifiers():
    chimps = dataset.get_mode("chimps")
    assert chimps is not None
    assert chimps.starting_cash == 650
    assert chimps.starting_lives == 1
    assert len(chimps.restrictions) == 6
    double_cash = dataset.get_mode("double_cash")
    assert double_cash is not None
    # modifiers carry no fixed cash/lives — their effect is relative (shipped)
    assert double_cash.starting_cash is None
    assert double_cash.starting_lives is None


# --- resolver matching (shipped alias-map discipline) -------------------------------


def test_resolves_chimps_mode_alias():
    # the oracle's own test_btd6_resolver_service pin, verbatim scenario
    intent = resolver.resolve("What's a good CHIMPS start?")
    assert any(m.id == "chimps" for m in intent.modes)


def test_resolves_multiword_map_canonical_as_substring():
    intent = resolver.resolve("how do I beat dark castle on hard?")
    assert any(m.id == "dark_castle" for m in intent.maps)
    # "hard" token-matches the Hard difficulty row — the shipped
    # common-word quirk, carried deliberately
    assert any(m.id == "hard" for m in intent.modes)


def test_single_word_map_alias_token_match():
    intent = resolver.resolve("what about the log map?")
    assert any(m.id == "logs" for m in intent.maps)


def test_maps_and_modes_raise_confidence():
    intent = resolver.resolve("dart monkey dark castle chimps")
    assert any(t.id for t in intent.towers)
    assert any(m.id == "dark_castle" for m in intent.maps)
    assert any(m.id == "chimps" for m in intent.modes)
    assert intent.confidence == 1.0  # 3+ matches cap the linear scale


def test_unmatched_text_stays_empty_and_zero():
    # the sweep_btd6_test-intent golden's world: "test" matches nothing
    intent = resolver.resolve("test")
    assert intent.maps == ()
    assert intent.modes == ()
    assert intent.confidence == 0.0


# --- response builders (btd6_response_builder.for_map / for_mode) -------------------


def test_for_map_card_bytes():
    card = oracle_cards.for_map(dataset.get_map("dark_castle"))
    assert card.title == "Dark Castle (Expert)"
    assert card.short_answer == "Expert map. Contains water."
    assert card.why_it_matters == (
        "Has water tiles — naval towers (Monkey Sub, Monkey Buccaneer) "
        "can be placed."
    )
    assert card.confidence == "high"
    assert card.follow_up == (
        "Pair with `!btd6 mode <name>` for mode-specific advice."
    )


def test_for_map_appends_curated_removables():
    skates = dataset.get_map("skates")
    assert skates is not None and skates.removables
    card = oracle_cards.for_map(skates)
    assert card.why_it_matters.endswith(
        f" Removable obstacles: {skates.removables}"
    )


def test_for_mode_card_bytes():
    card = oracle_cards.for_mode(dataset.get_mode("chimps"))
    assert card.title == "CHIMPS mode"
    assert card.why_it_matters == "Starting cash: 650. Starting lives: 1."
    assert card.recommended_options == dataset.get_mode("chimps").restrictions
    assert card.confidence == "high"


def test_for_mode_modifier_states_no_fixed_numbers():
    card = oracle_cards.for_mode(dataset.get_mode("double_cash"))
    assert card.title == "Double Cash Mode mode"
    assert card.why_it_matters == ""


# --- deterministic_answer shipped precedence order ----------------------------------


def test_answer_map_query_returns_map_card():
    intent = resolver.resolve("tell me about dark castle")
    card = oracle_cards.deterministic_answer(intent)
    assert card.title == "Dark Castle (Expert)"


def test_answer_mode_query_returns_mode_card():
    intent = resolver.resolve("what is impoppable like?")
    card = oracle_cards.deterministic_answer(intent)
    assert card.title == "Impoppable mode"


def test_answer_order_tower_beats_map():
    intent = resolver.resolve("dart monkey on logs")
    card = oracle_cards.deterministic_answer(intent)
    assert card.title == "Dart Monkey — overview"


def test_answer_order_map_beats_round():
    # shipped order: … → maps → modes → rounds → …
    intent = resolver.resolve("dark castle round 63")
    card = oracle_cards.deterministic_answer(intent)
    assert card.title == "Dark Castle (Expert)"


# --- the test-intent card rows (golden-pinned empty state + matched state) ----------


def test_test_intent_card_empty_state_is_golden_bytes():
    # sweep_btd6_test-intent pins exactly these six field values for "test"
    card = oracle_cards.test_intent_card("test")
    assert [(n, v) for n, v, _ in card.fields] == [
        ("Confidence", "0.00"),
        ("Towers", "—"),
        ("Heroes", "—"),
        ("Maps", "—"),
        ("Modes", "—"),
        ("Rounds", "—"),
    ]


def test_test_intent_card_renders_matched_canonicals():
    card = oracle_cards.test_intent_card("dark castle chimps")
    by_name = {n: v for n, v, _ in card.fields}
    assert by_name["Maps"] == "Dark Castle"
    assert by_name["Modes"] == "CHIMPS"
