"""Fixture tests for the K1 oracle (S2, frozen L0 spec 03 §3.1-§3.7).

The fixture snapshots use the K1-REQUIRED node shape (spec 03 §4.2): both
surfaces carried, parent_group per node, subcommands expanded.
"""

import json

import pytest

from sb.namespace import (
    CommandScope,
    NamespaceKind,
    Origin,
    Surface,
    check_trigger,
    namespace_id,
    normalize,
    validate,
)


def _node(value, surface="slash", parent=None, subsystem="economy", source="x.py:1"):
    return {"value": value, "kind": "command", "surface": surface,
            "parent_group": parent, "subsystem": subsystem, "source": source}


def _snapshot(command_nodes=(), **other_kinds):
    ns = {"command": list(command_nodes)}
    ns.update({k: list(v) for k, v in other_kinds.items()})
    return {"projections": {"namespace": ns}}


def _write_origins(tmp_path, legacy=None, tombs=None):
    legacy_doc = legacy or {"reserved_prefix_owners": {"_internal": "core",
                                                       "system": "system",
                                                       "governance": "governance"},
                            "reservations": []}
    tomb_doc = tombs or {"tombstones": [], "bans": []}
    lp = tmp_path / "legacy.json"
    tp = tmp_path / "tombstones.json"
    lp.write_text(json.dumps(legacy_doc))
    tp.write_text(json.dumps(tomb_doc))
    return str(lp), str(tp)


# --- the worked collision cases (spec 03 §3.1 table) --------------------------

def test_subcommands_of_different_groups_never_false_collide(tmp_path):
    lp, tp = _write_origins(tmp_path)
    snap = _snapshot([
        _node("close", parent="ticket", subsystem="tickets"),
        _node("close", parent="thread", subsystem="threads"),
    ])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    assert report.ok


def test_surfaces_never_false_collide(tmp_path):
    lp, tp = _write_origins(tmp_path)
    snap = _snapshot([
        _node("karma", surface="prefix", subsystem="karma"),
        _node("karma", surface="slash", subsystem="karma"),
    ])
    assert validate(snap, legacy_path=lp, tombstone_path=tp).ok


def test_same_scope_duplicate_is_the_q0211_collision(tmp_path):
    lp, tp = _write_origins(tmp_path)
    snap = _snapshot([
        _node("give", subsystem="economy", source="economy.py:12"),
        _node("give", subsystem="inventory", source="inventory.py:40"),
    ])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    assert not report.ok
    (collision,) = report.collisions
    assert collision.value == "give"
    assert collision.scope == CommandScope(Surface.SLASH, None)
    assert "economy" in collision.claimant_a and "inventory" in collision.claimant_b


def test_custom_id_byte_exact_global_collision(tmp_path):
    lp, tp = _write_origins(tmp_path)
    node = {"value": "settings_audit.back", "subsystem": "settings", "source": "a.py:1"}
    other = {"value": "settings_audit.back", "subsystem": "audit", "source": "b.py:2"}
    snap = _snapshot([], custom_id=[node, other])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    assert len(report.collisions) == 1


def test_command_normalization_is_casefold(tmp_path):
    lp, tp = _write_origins(tmp_path)
    snap = _snapshot([_node("Give"), _node("give", subsystem="other")])
    assert not validate(snap, legacy_path=lp, tombstone_path=tp).ok
    assert normalize("Give", NamespaceKind.COMMAND) == "give"
    assert normalize("Byte.Exact", NamespaceKind.CUSTOM_ID) == "Byte.Exact"


# --- cross-origin rules --------------------------------------------------------

def test_manifest_may_claim_legacy_compat_iff_same_owner(tmp_path):
    legacy = {"reserved_prefix_owners": {}, "reservations": [
        {"kind": "command", "value": "balance",
         "scope": {"surface": "prefix", "parent_group": None},
         "owner": "economy", "compat": True, "source": "legacy_reservations.json"},
    ]}
    lp, tp = _write_origins(tmp_path, legacy=legacy)
    ok_snap = _snapshot([_node("balance", surface="prefix", subsystem="economy")])
    assert validate(ok_snap, legacy_path=lp, tombstone_path=tp).ok
    bad_snap = _snapshot([_node("balance", surface="prefix", subsystem="karma")])
    report = validate(bad_snap, legacy_path=lp, tombstone_path=tp)
    assert not report.ok
    assert report.collisions[0].detail == "legacy_owner_mismatch"


def test_manifest_vs_tombstone_and_ban(tmp_path):
    tombs = {"tombstones": [
        {"kind": "command", "value": "adminmenu",
         "scope": {"surface": "prefix", "parent_group": None},
         "renamed_to": "admin", "reason": "Q-0237f", "provenance": "Q-0237f"}],
        "bans": [
        {"kind": "command", "value": "the",
         "scope": {"surface": "prefix", "parent_group": None},
         "reason": "common-word blocklist", "provenance": "Q-0225"}]}
    lp, tp = _write_origins(tmp_path, tombs=tombs)
    snap = _snapshot([
        _node("adminmenu", surface="prefix", subsystem="admin"),
        _node("the", surface="prefix", subsystem="chat"),
    ])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    details = {c.detail for c in report.collisions}
    assert "reserved_tombstone (renamed to admin)" in details
    assert "banned_name" in details


# --- format checks (P3-owned capability identity) -------------------------------

def test_capability_format_and_reserved_prefix_owner(tmp_path):
    lp, tp = _write_origins(tmp_path)
    snap = _snapshot([], capability=[
        {"value": "economy.balance.read", "subsystem": "economy", "source": "e.py:1"},
        {"value": "not-three-part", "subsystem": "economy", "source": "e.py:2"},
        {"value": "governance.scope.write", "subsystem": "economy", "source": "e.py:3"},
        {"value": "governance.scope.read", "subsystem": "governance", "source": "g.py:1"},
    ])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    details = {(f.value, f.detail) for f in report.format_errors}
    assert ("not-three-part", "capability_not_3_part") in details
    assert ("governance.scope.write", "reserved_prefix_misuse") in details
    assert ("governance.scope.read", "reserved_prefix_misuse") not in details


# --- cap budget -----------------------------------------------------------------

def test_top_level_100_cap_counts_groups_once(tmp_path):
    lp, tp = _write_origins(tmp_path)
    nodes = [_node(f"cmd{i}", subsystem=f"s{i}") for i in range(100)]
    nodes.append(_node("sub", parent="cmd0", subsystem="s0"))  # grouped: no new top-level
    assert validate(_snapshot(nodes), legacy_path=lp, tombstone_path=tp).ok
    nodes.append(_node("cmd100", subsystem="s100"))  # the 101st
    report = validate(_snapshot(nodes), legacy_path=lp, tombstone_path=tp)
    assert any(v.cap == "top_level_100" for v in report.cap_violations)


def test_sub_25_cap(tmp_path):
    lp, tp = _write_origins(tmp_path)
    nodes = [_node(f"sub{i}", parent="grp", subsystem="s") for i in range(26)]
    report = validate(_snapshot(nodes), legacy_path=lp, tombstone_path=tp)
    assert any(v.cap == "sub_25" and v.locus == "grp" for v in report.cap_violations)


def test_nest_1_cap(tmp_path):
    lp, tp = _write_origins(tmp_path)
    nodes = [_node("leaf", parent="a.b.c", subsystem="s")]
    report = validate(_snapshot(nodes), legacy_path=lp, tombstone_path=tp)
    assert any(v.cap == "nest_1" for v in report.cap_violations)


def test_prefix_surface_is_uncapped(tmp_path):
    lp, tp = _write_origins(tmp_path)
    nodes = [_node(f"p{i}", surface="prefix", subsystem=f"s{i}") for i in range(150)]
    assert validate(_snapshot(nodes), legacy_path=lp, tombstone_path=tp).ok


# --- the runtime read surface + triggers ----------------------------------------

@pytest.fixture()
def built_index(tmp_path):
    tombs = {"tombstones": [
        {"kind": "command", "value": "oldname",
         "scope": {"surface": "prefix", "parent_group": None},
         "renamed_to": "newname", "reason": "renamed", "provenance": "Q-test"}],
        "bans": [
        {"kind": "command", "value": "the",
         "scope": {"surface": "prefix", "parent_group": None},
         "reason": "common word", "provenance": "Q-0225"}]}
    lp, tp = _write_origins(tmp_path, tombs=tombs)
    snap = _snapshot([
        _node("give", surface="slash", subsystem="economy"),
        _node("give", surface="prefix", subsystem="economy"),
        _node("close", parent="ticket", subsystem="tickets"),
    ])
    report = validate(snap, legacy_path=lp, tombstone_path=tp)
    assert report.ok
    return report.index


def test_is_reserved_point_query(built_index):
    hit = built_index.is_reserved("give", NamespaceKind.COMMAND)
    assert hit is not None and hit.origin is Origin.MANIFEST
    assert built_index.is_reserved("GIVE", NamespaceKind.COMMAND) is not None  # casefold
    # subcommand names are NOT top-level-reserved (parent=None default)
    assert built_index.is_reserved("close", NamespaceKind.COMMAND) is None
    assert built_index.is_reserved("close", NamespaceKind.COMMAND, parent="ticket") is not None


def test_resolve_command_and_corpus(built_index):
    rec = built_index.resolve_command("give", surface=Surface.SLASH)
    assert rec is not None and rec.owner == "economy"
    assert built_index.resolve_command("close", surface=Surface.SLASH) is None
    assert "give" in built_index.command_corpus(Surface.SLASH)
    assert "close" not in built_index.command_corpus(Surface.SLASH)  # not top-level


def test_check_trigger_reasons(built_index):
    assert check_trigger("free", index=built_index, min_len=3).available
    assert check_trigger("ab", index=built_index, min_len=3).reason == "too_short"
    assert check_trigger("give", index=built_index, min_len=3).reason == "reserved_command"
    assert check_trigger("oldname", index=built_index, min_len=3).reason == "tombstoned"
    banned = check_trigger("the", index=built_index, min_len=3)
    assert banned.reason == "banned_common_word"
    assert banned.conflict is not None and banned.conflict.origin is Origin.BAN
    # a subcommand verb stays available as a trigger (spec 03 decision 9)
    assert check_trigger("close", index=built_index, min_len=3).available


# --- determinism / identity keys -------------------------------------------------

def test_namespace_id_total_order():
    assert namespace_id("give", CommandScope(Surface.SLASH, None)) == "slash//give"
    assert namespace_id("close", CommandScope(Surface.SLASH, "ticket")) == "slash/ticket/close"
    assert namespace_id("evt", None) == "//evt"


def test_committed_seed_files_load_clean():
    """The committed legacy/tombstone seeds validate against an empty snapshot."""
    report = validate({"projections": {"namespace": {}}})
    assert report.ok
    hit = report.index.is_reserved("ActionSpec", NamespaceKind.CUSTOM_ID)
    assert hit is not None and hit.origin is Origin.BAN
