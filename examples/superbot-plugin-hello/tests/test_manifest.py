"""Authoring-time checks for the hello manifest (needs the host `sb`
package — `pip install -e .[host]` or run inside a host checkout)."""

from superbot_plugin_hello import manifest as m


def test_manifest_shape() -> None:
    assert m.MANIFEST.key == "hello"
    assert [c.name for c in m.MANIFEST.commands] == ["hello"]
    assert [p.panel_id for p in m.MANIFEST.panels] == [m.PANEL_ID]


def test_command_routes_to_the_panel() -> None:
    (cmd,) = m.MANIFEST.commands
    assert cmd.route is not None and cmd.route.name == m.PANEL_ID


def test_v1_contract_facets_only() -> None:
    # stores / data_invariants / wizard_sections are host-owned in v1.
    assert m.MANIFEST.stores == ()
    assert m.MANIFEST.data_invariants == ()
    assert m.MANIFEST.wizard_sections == ()


def test_panel_ref_registered_on_import() -> None:
    from sb.spec.refs import PanelRef, is_registered

    m.ENSURE_REFS()
    assert is_registered(PanelRef(m.PANEL_ID))
