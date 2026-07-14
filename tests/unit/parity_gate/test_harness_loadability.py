"""Loadability pin for the imported parity harness runner.

``parity/harness/runner.py`` is imported-harness code; this pin holds the
2026-07-13 dead-ref ruling: ``apply_isolation_resets`` (which loaded the
long-gone ``tests/_isolation.py``) is retired, and the module itself must
keep importing cleanly. DB-free — nothing here boots a bot.
"""

from __future__ import annotations

import importlib


class TestHarnessRunnerLoadability:
    def test_runner_imports_cleanly(self):
        module = importlib.import_module("parity.harness.runner")
        assert sorted(module.__all__) == [
            "capture_case",
            "golden_path",
            "replay_case",
        ]
        # The dead isolation ref stays retired (its target,
        # tests/_isolation.py, no longer exists in the tree).
        assert not hasattr(module, "apply_isolation_resets")
