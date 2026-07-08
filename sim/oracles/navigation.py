"""The instruction-driven navigation engine — the runner's FIRST oracle
(Q-0235; canonical plan §5 step 11). Powers the hub-topology ratification.

A deterministic label-match user model walks a candidate navigation graph
executing "find/do X" tasks; the score is task-success-rate / path-length /
wrong-turns. An OPTIONAL AI-naive-user model is an installable port —
advisory only, never part of the deterministic gate (design-spec §8 Q9
forbids required live-judge gates).

Corpus independence: navigation tasks are minted from the graph's own
declared labels (or hand-curated per space) and stay INDEPENDENT of the
NL-router eval corpus — the #1701 Goodhart caution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sim.oracles import ScoreBreakdown

__all__ = [
    "NavGraph",
    "NavNode",
    "NavTask",
    "NavigationOracle",
    "install_naive_user_model",
    "reset_navigation_ports_for_tests",
    "tasks_from_graph",
    "walk_task",
]

MAX_HOPS = 8

# Encoded objective weights — stated, not implied (§2.10.4).
W_SUCCESS = 1.0
W_PATH = 0.3
W_WRONG_TURNS = 0.2


@dataclass(frozen=True)
class NavNode:
    node_id: str
    label: str
    children: tuple[str, ...] = ()   # child node ids, arrangement-ordered


@dataclass(frozen=True)
class NavGraph:
    root: str
    nodes: dict[str, NavNode] = field(default_factory=dict)

    def shortest_hops(self, start: str, target: str) -> int | None:
        seen = {start}
        frontier = [(start, 0)]
        while frontier:
            node_id, hops = frontier.pop(0)
            if node_id == target:
                return hops
            for child in self.nodes[node_id].children:
                if child in self.nodes and child not in seen:
                    seen.add(child)
                    frontier.append((child, hops + 1))
        return None


@dataclass(frozen=True)
class NavTask:
    """'find/do X': reach `target` given `instruction`."""

    instruction: str
    target: str


def tasks_from_graph(graph: NavGraph) -> tuple[NavTask, ...]:
    """Mint one 'find X' task per non-root node from its own label."""
    return tuple(
        NavTask(instruction=f"find {node.label}", target=node.node_id)
        for node_id, node in sorted(graph.nodes.items())
        if node_id != graph.root
    )


def _tokens(text: str) -> set[str]:
    return {t for t in text.lower().split() if len(t) > 2}


def _label_match(instruction_tokens: set[str], label: str) -> int:
    return len(instruction_tokens & _tokens(label))


# Optional AI-naive-user port (advisory only; None = deterministic model).
_naive_user: Callable[[NavGraph, NavTask], list[str]] | None = None


def install_naive_user_model(model: Callable[[NavGraph, NavTask], list[str]]) -> None:
    global _naive_user
    _naive_user = model


def reset_navigation_ports_for_tests() -> None:
    global _naive_user
    _naive_user = None


@dataclass(frozen=True)
class WalkResult:
    success: bool
    path: tuple[str, ...]
    wrong_turns: int


def walk_task(graph: NavGraph, task: NavTask) -> WalkResult:
    """The deterministic label-match user: at each state pick the child
    whose label best matches the instruction tokens (ties broken by
    namespace-id sort — deterministic, never vibes); a wrong turn is a hop
    that does not reduce shortest-path distance to the target."""
    tokens = _tokens(task.instruction)
    current = graph.root
    path = [current]
    wrong_turns = 0
    for _ in range(MAX_HOPS):
        if current == task.target:
            return WalkResult(True, tuple(path), wrong_turns)
        node = graph.nodes[current]
        children = [c for c in node.children if c in graph.nodes]
        if not children:
            break
        before = graph.shortest_hops(current, task.target)
        best = max(
            sorted(children),
            key=lambda c: (_label_match(tokens, graph.nodes[c].label), c == task.target),
        )
        after = graph.shortest_hops(best, task.target)
        if before is not None and (after is None or after >= before):
            wrong_turns += 1
        path.append(best)
        current = best
    success = current == task.target
    return WalkResult(success, tuple(path), wrong_turns)


class NavigationOracle:
    """score(candidate: NavGraph, context) — context may carry `tasks`
    (hand-curated corpus) and `usage` (an sim.space.UsageSnapshot for
    task weighting + confidence)."""

    def score(self, candidate: Any, context: dict[str, Any]) -> ScoreBreakdown:
        graph: NavGraph = candidate
        tasks: tuple[NavTask, ...] = tuple(context.get("tasks") or ()) or tasks_from_graph(graph)
        usage = context.get("usage")
        if not tasks:
            return ScoreBreakdown(total=0.0, notes="empty task corpus")

        successes = 0.0
        path_hops = 0.0
        wrong_total = 0.0
        weight_total = 0.0
        for task in tasks:
            w = usage.weight(task.target) if usage is not None else 1.0
            weight_total += w
            result = walk_task(graph, task)
            if result.success:
                successes += w
                path_hops += w * (len(result.path) - 1)
            else:
                path_hops += w * MAX_HOPS  # a failed task costs the full budget
            wrong_total += w * result.wrong_turns

        success_rate = successes / weight_total
        # ABSOLUTE hop cost (normalized by the hop budget) — candidate
        # topologies are compared on real click depth, never each graph's
        # own shortest path (which would hide a deeper topology).
        mean_path_hops = (path_hops / weight_total) / MAX_HOPS
        mean_wrong = wrong_total / weight_total
        total = (
            W_SUCCESS * success_rate
            - W_PATH * mean_path_hops
            - W_WRONG_TURNS * mean_wrong
        )
        return ScoreBreakdown(
            total=total,
            terms={
                "task_success_rate": success_rate,
                "mean_path_hops": mean_path_hops,
                "mean_wrong_turns": mean_wrong,
            },
            confidence=(usage.confidence if usage is not None else "low"),
        )
