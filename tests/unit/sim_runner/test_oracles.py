"""V-3 oracle tests: the Q-0235 navigation engine + the two sibling oracles
+ the registry."""

from __future__ import annotations

import pytest

from sim.oracles import clear_oracles_for_tests, get_oracle, registered_oracles
from sim.oracles.dense_panel import DensePanelOracle
from sim.oracles.navigation import (
    NavGraph,
    NavNode,
    NavTask,
    NavigationOracle,
    install_naive_user_model,
    reset_navigation_ports_for_tests,
    tasks_from_graph,
    walk_task,
)
from sim.oracles.settings_grouping import SettingsGroupingOracle
from sim.space import UsageSnapshot


def _usage(counts=None, pairs=None, provenance="telemetry(30d)"):
    return UsageSnapshot(
        provenance=provenance, capture_window="30d",
        session_definition="s", counts=counts or {}, pairs=pairs or {},
    )


def _graph(deep=False):
    """hub -> {economy, games}; economy -> shop; games -> blackjack.
    deep=True buries shop one hop further under a mislabeled node."""
    nodes = {
        "hub": NavNode("hub", "Main Hub", ("economy", "games")),
        "economy": NavNode("economy", "Economy", ("shop",) if not deep else ("misc",)),
        "games": NavNode("games", "Games", ("blackjack",)),
        "shop": NavNode("shop", "Item Shop", ()),
        "blackjack": NavNode("blackjack", "Blackjack Table", ()),
    }
    if deep:
        nodes["misc"] = NavNode("misc", "Miscellaneous", ("shop",))
    return NavGraph(root="hub", nodes=nodes)


class TestNavigationWalk:
    def test_label_match_reaches_target(self):
        result = walk_task(_graph(), NavTask("find the item shop", "shop"))
        assert result.success
        assert result.path == ("hub", "economy", "shop")
        assert result.wrong_turns == 0  # every hop reduced distance to target

    def test_deterministic_tiebreak(self):
        r1 = walk_task(_graph(), NavTask("zzz nothing matches", "blackjack"))
        r2 = walk_task(_graph(), NavTask("zzz nothing matches", "blackjack"))
        assert r1 == r2  # ties break by namespace-id sort, never randomness

    def test_tasks_minted_from_graph_labels(self):
        tasks = tasks_from_graph(_graph())
        assert NavTask("find Item Shop", "shop") in tasks
        assert all(t.target != "hub" for t in tasks)

    def test_oracle_prefers_shallow_topology(self):
        oracle = NavigationOracle()
        tasks = tasks_from_graph(_graph())  # SAME corpus for both candidates
        shallow = oracle.score(_graph(), {"tasks": tasks})
        deep = oracle.score(_graph(deep=True), {"tasks": tasks})
        assert shallow.total > deep.total
        assert 0.0 <= shallow.terms["task_success_rate"] <= 1.0

    def test_usage_weighting_and_confidence(self):
        oracle = NavigationOracle()
        usage = _usage(counts={"shop": 100.0})
        score = oracle.score(_graph(), {"usage": usage})
        assert score.confidence == "measured"

    def test_naive_user_port_is_optional(self):
        reset_navigation_ports_for_tests()
        install_naive_user_model(lambda g, t: ["hub"])
        # the deterministic model is unaffected — the port is advisory only
        assert walk_task(_graph(), NavTask("find Item Shop", "shop")).success
        reset_navigation_ports_for_tests()


class TestSettingsGroupingOracle:
    def test_cohesion_rewards_intra_group_pairs(self):
        oracle = SettingsGroupingOracle()
        pairs = {"co_edit|xp.rate|xp.cap": 10.0}
        together = (("xp", ("xp.rate", "xp.cap")), ("misc", ("log.level",)))
        apart = (("a", ("xp.rate", "log.level")), ("b", ("xp.cap",)))
        ctx = {"pairs": pairs}
        assert oracle.score(together, ctx).total > oracle.score(apart, ctx).total

    def test_neutral_prior_without_signal(self):
        oracle = SettingsGroupingOracle()
        score = oracle.score((("g", ("a", "b")),), {})
        assert score.terms["group_cohesion"] == 0.5
        assert score.confidence == "low"

    def test_scroll_cost_prefers_hot_settings_first(self):
        oracle = SettingsGroupingOracle()
        usage = _usage(counts={"hot.key": 50.0})
        first = (("g", ("hot.key", "cold.key")),)
        last = (("g", ("cold.key", "hot.key")),)
        assert (
            oracle.score(first, {"usage": usage}).total
            > oracle.score(last, {"usage": usage}).total
        )


class TestDensePanelOracle:
    def test_hot_components_belong_early(self):
        oracle = DensePanelOracle()
        usage = _usage(counts={"hot": 50.0})
        hot_first = ((("hot", "b"), ("c", "d")),)
        hot_last = ((("c", "d"), ("b", "hot")),)
        assert (
            oracle.score(hot_first, {"usage": usage}).total
            > oracle.score(hot_last, {"usage": usage}).total
        )

    def test_co_use_pairs_prefer_proximity(self):
        oracle = DensePanelOracle()
        usage = _usage(pairs={"co_use|a|b": 10.0})
        adjacent = ((("a", "b"), ("c",)),)
        split = ((("a", "c"),), (("b",),))  # different pages
        assert (
            oracle.score(adjacent, {"usage": usage}).total
            > oracle.score(split, {"usage": usage}).total
        )


class TestRegistry:
    def test_three_named_oracles_registered(self):
        assert registered_oracles() == ("dense_panel", "navigation", "settings_grouping")

    def test_unknown_oracle_is_loud(self):
        with pytest.raises(KeyError):
            get_oracle("vibes")

    def test_clear_reregisters_named(self):
        clear_oracles_for_tests()
        assert "navigation" in registered_oracles()
