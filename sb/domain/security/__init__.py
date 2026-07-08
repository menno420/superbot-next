"""SECURITY subsystem (band 2) — raid-window + account-age screening
decision cores; the member-join feed arms when the member band ports."""

from __future__ import annotations

from collections import deque

__all__ = ["RaidWindow", "age_gate_action"]

AGE_ACTIONS = ("alert", "kick", "ban")   # shipped vocabulary (ACTION_ALERT default)


class RaidWindow:
    """Pure sliding-window raid detector (shipped raid rule: >= join_count
    joins inside window_seconds). Caller supplies timestamps (injectable
    clock — determinism by design)."""

    def __init__(self, *, join_count: int = 10, window_seconds: int = 60) -> None:
        self.join_count = max(1, int(join_count))
        self.window_seconds = max(1, int(window_seconds))
        self._joins: deque[float] = deque()

    def note_join(self, at: float) -> bool:
        """Record one join; True = raid threshold crossed AT this join."""
        self._joins.append(at)
        while self._joins and at - self._joins[0] > self.window_seconds:
            self._joins.popleft()
        return len(self._joins) >= self.join_count


def age_gate_action(account_age_days: float, *, enabled: bool,
                    min_days: int, action: str) -> str | None:
    """Account-age screen: None = pass; else the configured action
    (unknown tokens degrade to 'alert' — never a harsher action)."""
    if not enabled or account_age_days >= min_days:
        return None
    return action if action in AGE_ACTIONS else "alert"
