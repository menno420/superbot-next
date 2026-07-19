"""`counting/store.py::_decode` — the JSON round-trip tolerance guard.

`get_state` funnels the raw ``state`` column through `_decode`, which coerces a
malformed / off-type stored blob back to an empty dict rather than raising:
`None` (no row nuance), a real dict passthrough, a JSON string decode, and a
malformed string swallowed to ``{}``. The existing counting tests monkeypatch
`get_state` wholesale, so `_decode` itself is never exercised — removing its
`try/except (TypeError, ValueError)` would let a corrupt row crash every
counting read. Behaviors verified against a live run before commit.
"""

from __future__ import annotations

from sb.domain.counting.store import _decode


def test_decode_none_is_empty_dict():
    assert _decode(None) == {}


def test_decode_dict_passes_through():
    blob = {"channels": {"7": {"leaderboard": {"42": 3}}}}
    assert _decode(blob) is blob        # a live dict is returned as-is, not re-parsed


def test_decode_json_string_is_parsed():
    assert _decode('{"channels": {}}') == {"channels": {}}


def test_decode_malformed_string_reverts_to_empty():
    # int()/json ValueError swallowed -> {} rather than propagating the crash.
    assert _decode("not json at all") == {}
    assert _decode("") == {}


def test_decode_non_dict_non_str_reverts_to_empty():
    # A bare int/float is neither None, dict, nor JSON-parseable text -> {}.
    assert _decode(5) == {}
