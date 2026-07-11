"""Flag-13 corpus-red dispositions (ORDER 009 / Q-0262.3) — the three
owner-accepted classes are applied at replay-diff time, symmetrically, and
NOTHING else changes: goldens stay byte-identical on disk, the imported
harness stays verbatim, and every non-disposed byte still diffs."""

from __future__ import annotations

import copy


def _doc():
    return {
        "harness_version": 1,
        "case_id": "sweep.example",
        "db_delta": {
            "audit_log": {"added": [{"mutation_id": "<uuid>", "verb": "x"}]},
            "event_outbox": {"added": [{"event": "audit.action_recorded"}]},
            "xp": {"added": [{"user_id": "<@admin>", "xp": 25, "coins": 0}]},
            "economy_audit_log": {"added": [{"user_id": "<@admin>",
                                             "delta": 10, "new_balance": 10,
                                             "reason": "daily",
                                             "mutation_id": "<uuid>"}]},
            "economy_balances": {"added": [{"user_id": "<@admin>",
                                            "coins": 10}]},
            "warnings": {"added": [{"user_id": "<@admin>", "count": 1}]},
        },
        "steps": [
            {
                "input": {"kind": "command", "content": "!warn"},
                "calls": [
                    {"method": "send_message",
                     "args": {"channel_id": "<#general>"}, "payload": {}},
                    {"method": "delete_message",
                     "args": {"channel_id": "<#general>",
                              "message_id": "<msg:1>", "reason": None}},
                    {"method": "delete_message",
                     "args": {"channel_id": "<#general>",
                              "message_id": "<msg:2>",
                              "reason": "cleanup purge"}},
                ],
                "events": [
                    {"event": "command.dispatched", "payload": {}},
                    {"event": "moderation.action_taken", "payload": {}},
                ],
            },
        ],
    }


def test_kernel_surfaces_dropped_from_both_tables_and_events():
    from sb.adapters.parity.dispositions import apply_dispositions

    out = apply_dispositions(_doc())
    assert "audit_log" not in out["db_delta"]
    assert "event_outbox" not in out["db_delta"]
    # domain surfaces stay
    assert "warnings" in out["db_delta"]
    events = out["steps"][0]["events"]
    assert [e["event"] for e in events] == ["moderation.action_taken"]


def test_events_key_dropped_when_only_kernel_events_remain():
    from sb.adapters.parity.dispositions import apply_dispositions

    doc = _doc()
    doc["steps"][0]["events"] = [{"event": "command.dispatched", "payload": {}}]
    out = apply_dispositions(doc)
    assert "events" not in out["steps"][0]


def test_xp_coins_alias_column_dropped():
    from sb.adapters.parity.dispositions import apply_dispositions

    out = apply_dispositions(_doc())
    rows = out["db_delta"]["xp"]["added"]
    assert rows == [{"user_id": "<@admin>", "xp": 25}]


def test_ledgered_coins_boundary_new_home_dropped_but_ledger_diffs():
    """Encoding completion (2026-07-10, blackjack flip PR): the boundary's
    NEW home (economy_balances — rows no old-bot golden can contain) is
    dropped from both docs; balance BEHAVIOR stays pinned through the
    economy_audit_log delta/new_balance bytes, which still diff."""
    from parity.harness.runner import _diff_docs

    from sb.adapters.parity.dispositions import apply_dispositions

    out = apply_dispositions(_doc())
    assert "economy_balances" not in out["db_delta"]
    assert "economy_audit_log" in out["db_delta"]
    other = _doc()
    other["db_delta"]["economy_audit_log"]["added"][0]["new_balance"] = 999
    assert _diff_docs(apply_dispositions(_doc()),
                      apply_dispositions(other)) != []


def test_kernel_mutation_id_column_dropped_from_domain_ledger_rows():
    """Encoding completion (2026-07-10): the kernel idempotency stamp on
    the DOMAIN ledger row (economy_audit_log.mutation_id) is the accepted
    kernel-drift class in column form; every domain byte still diffs."""
    from sb.adapters.parity.dispositions import apply_dispositions

    out = apply_dispositions(_doc())
    row = out["db_delta"]["economy_audit_log"]["added"][0]
    assert "mutation_id" not in row
    assert row["new_balance"] == 10 and row["reason"] == "daily"


def test_reasonless_invoking_delete_exempt_but_reasoned_delete_diffs():
    from sb.adapters.parity.dispositions import apply_dispositions

    out = apply_dispositions(_doc())
    methods = [c["method"] for c in out["steps"][0]["calls"]]
    # the reason-less invoking-message delete is gone; the reasoned
    # (real-behavior) delete survives and still diffs
    assert methods == ["send_message", "delete_message"]
    kept = [c for c in out["steps"][0]["calls"]
            if c["method"] == "delete_message"]
    assert kept[0]["args"]["reason"] == "cleanup purge"


def test_apply_is_pure_and_symmetric():
    from parity.harness.runner import _diff_docs

    from sb.adapters.parity.dispositions import apply_dispositions

    original = _doc()
    frozen = copy.deepcopy(original)
    out = apply_dispositions(original)
    assert original == frozen                # never mutates the input
    assert out is not original
    # symmetric application: two docs differing ONLY in disposed surfaces
    # diff clean; a non-disposed difference still reds
    other = _doc()
    other["db_delta"].pop("audit_log")
    other["db_delta"]["xp"]["added"][0]["coins"] = 999
    other["steps"][0]["calls"] = [
        c for c in other["steps"][0]["calls"]
        if not (c["method"] == "delete_message"
                and c["args"]["reason"] is None)]
    assert _diff_docs(apply_dispositions(original),
                      apply_dispositions(other)) == []
    other["db_delta"]["warnings"]["added"][0]["count"] = 2
    assert _diff_docs(apply_dispositions(original),
                      apply_dispositions(other)) != []


def test_minted_refs_renumber_after_drops():
    """The ruled drops consume symbolic refs (the reason-less invoking
    delete minted <msg:1> on every shipped command golden) — the disposition
    pass renumbers <msg:N> by first appearance in the DISPOSED doc,
    symmetrically, so the accepted classes cannot leak id-noise into every
    ref that follows one. Non-disposed bytes around a ref still diff."""
    from parity.harness.runner import _diff_docs

    from sb.adapters.parity.dispositions import apply_dispositions

    golden = _doc()
    # the shipped side: <msg:1> was the (dropped) invoking delete; the
    # surviving reasoned delete carries <msg:2>.
    fresh = _doc()
    fresh["steps"][0]["calls"] = [
        c for c in fresh["steps"][0]["calls"]
        if not (c["method"] == "delete_message"
                and c["args"]["reason"] is None)]
    # the new bot never allocated the invoking-delete ref: its reasoned
    # delete is <msg:1>.
    fresh["steps"][0]["calls"][1]["args"]["message_id"] = "<msg:1>"
    assert _diff_docs(apply_dispositions(golden), apply_dispositions(fresh)) == []
    # a real byte difference on the renumbered call still reds
    fresh["steps"][0]["calls"][1]["args"]["reason"] = "different purge"
    assert _diff_docs(apply_dispositions(golden), apply_dispositions(fresh)) != []


def test_dispositions_load_from_parity_yml():
    from sb.adapters.parity.dispositions import load_dispositions

    d = load_dispositions()
    assert set(d) == {"kernel-surface-drift", "xp-coins-alias",
                      "invoking-message-deletion"}
    drift = d["kernel-surface-drift"]
    assert drift["encoding"] == "normalizer"
    # kernel indirection resolved against the kernel coverage home
    assert "audit_log" in drift["tables"]
    assert "command.dispatched" in drift["events"]
    assert drift["columns"] == ["economy_audit_log.mutation_id",
                                "karma_audit_log.mutation_id"]
    assert d["xp-coins-alias"] == {"encoding": "normalizer",
                                   "table": "xp", "column": "coins",
                                   "new_home_table": "economy_balances"}
    deletion = d["invoking-message-deletion"]
    assert deletion["encoding"] == "exemption"
    assert deletion["reasonless_only"] is True
