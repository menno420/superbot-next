"""Clean panel/locale state for the A-3 navigation-completeness golden
(the same reset roster as tests/unit/panels — duplicated because pytest
test dirs are independent top-level packages here)."""

from __future__ import annotations

import pytest

from sb.kernel.interaction.locale import reset_copy_resolver_for_tests
from sb.kernel.panels.engine import reset_panel_engine_for_tests
from sb.kernel.panels.registry import clear_panels_for_tests
from sb.kernel.panels.render import reset_render_ports_for_tests
from sb.kernel.panels.router import reset_router_for_tests


@pytest.fixture(autouse=True)
def _clean_panel_state():
    for reset in (clear_panels_for_tests, reset_router_for_tests,
                  reset_panel_engine_for_tests, reset_render_ports_for_tests,
                  reset_copy_resolver_for_tests):
        reset()
    yield
    for reset in (clear_panels_for_tests, reset_router_for_tests,
                  reset_panel_engine_for_tests, reset_render_ports_for_tests,
                  reset_copy_resolver_for_tests):
        reset()
