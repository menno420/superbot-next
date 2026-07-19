"""`automation/store.py::_decode` — the JSONB round-trip tolerance guard.

`get_rule_by_name` / `list_rules_for_guild` push each rule's
``trigger_config`` / ``action_config`` column through `_decode`, which tolerates
the driver returning either a live dict or a JSON string, and fails closed to an
empty dict on anything malformed / off-shape (a JSON *list* is not a config map,
so it too collapses to ``{}``). No test referenced `automation.store`, so this
swallow was unexercised — dropping it would let a corrupt config row crash every
rule read. Behaviors verified against a live run before commit.
"""

from __future__ import annotations

from sb.domain.automation.store import _decode


def test_decode_dict_passes_through():
    cfg = {"kind": "keyword", "value": "hi"}
    assert _decode(cfg) is cfg


def test_decode_json_object_string_is_parsed():
    assert _decode('{"kind": "keyword"}') == {"kind": "keyword"}


def test_decode_json_object_bytes_is_parsed():
    assert _decode(b'{"kind": "keyword"}') == {"kind": "keyword"}


def test_decode_malformed_string_reverts_to_empty():
    assert _decode("not json") == {}


def test_decode_json_list_is_not_a_config_map():
    # Valid JSON but not an object -> not a config map -> {} (fails closed).
    assert _decode("[1, 2, 3]") == {}


def test_decode_non_str_non_dict_reverts_to_empty():
    # A bare int is neither dict nor str/bytes -> {}.
    assert _decode(5) == {}
