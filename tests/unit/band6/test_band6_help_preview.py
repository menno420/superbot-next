"""The 👁 Help Preview port (server_management projections slice B): the
shipped HelpPreviewView/build_help_preview_embed surface as a pure
consumer of the slice-A access projection, honest to the COMPILED help's
hiding rule (the category staff-gate only — D-0054 judgment call 3).

Oracle: menno420/superbot disbot/views/server_management/access_map.py
(HelpPreviewView half) over services/help_projection.py
project_help_with_execution. No golden drives the interior (the hub-open
goldens pin only the hub bytes, which stay identical); these tests pin
the ported copy + bucket semantics.
"""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.governance import cache as gcache
    from sb.domain.server_management import help_preview as hp

    gcache.reset_cache_for_tests()
    hp._tier_pick.clear()
    yield
    gcache.reset_cache_for_tests()
    hp._tier_pick.clear()


def _patch_owners(monkeypatch, *, mode=None, allowed_channels=frozenset()):
    from sb.domain.governance import store as gov_store
    from sb.domain.platform import command_access as ca
    from sb.kernel.authority.channel_access import CommandAccessSnapshot

    async def fake_snapshot(guild_id):
        return CommandAccessSnapshot(mode=mode,
                                     allowed_channels=allowed_channels)

    async def fake_overrides(guild_id, chain):
        return {}

    monkeypatch.setattr(ca, "read_policy_snapshot", fake_snapshot)
    monkeypatch.setattr(gov_store, "fetch_visibility_for_chain",
                        fake_overrides)


def _ctx(gid=1, uid=42, channel_id=2):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=gid, actor=SimpleNamespace(user_id=uid),
        channel_id=channel_id, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={},
        surface="component")


# --- the spec ---------------------------------------------------------------------


def test_help_preview_spec_shape():
    from sb.domain.server_management.help_preview import help_preview_spec
    from sb.spec.panels import Audience, FooterMode, SelectorKind
    from sb.spec.refs import HandlerRef, PanelRef

    spec = help_preview_spec()
    assert spec.panel_id == "server_management.help_preview"
    assert spec.subsystem == "server_management"
    assert spec.title == "👁 Help Preview"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "red"          # the shipped ADMIN_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    (tier_sel,) = spec.selectors
    assert tier_sel.selector_id == "hp_tier"
    assert tier_sel.kind is SelectorKind.ENUM
    assert tier_sel.placeholder == "Simulate audience…"      # shipped byte
    assert tier_sel.audience_tier == "administrator"
    assert tier_sel.on_select == HandlerRef(
        "server_management.help_preview_tier")
    assert spec.navigation.parent == PanelRef("server_management.hub")
    assert spec.layout.pages[0].rows == (("hp_tier",),)


def test_help_preview_spec_passes_the_compile_fences():
    from sb.domain.server_management.help_preview import help_preview_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(help_preview_spec())


# --- the render --------------------------------------------------------------------


def test_render_carries_footer_and_tier_keyed_description(monkeypatch):
    from sb.domain.server_management import help_preview as hp

    _patch_owners(monkeypatch)
    rendered = run(hp._render_help_preview(hp.help_preview_spec(), _ctx()))
    assert rendered.embed.footer == "Read-only preview · simulated audience"
    assert rendered.embed.description == (
        "What Help advertises to a **Normal member** in this channel. "
        "Display-only — the live Help command stays the renderer of "
        "record.")
    from sb.domain.server_management.access_map import SIMULATION_LIMIT_NOTE
    assert rendered.embed.fields[-1] == ("Simulation limits",
                                         SIMULATION_LIMIT_NOTE)

    hp._tier_pick[(1, 42)] = "administrator"
    rendered = run(hp._render_help_preview(hp.help_preview_spec(), _ctx()))
    assert "**Administrator**" in rendered.embed.description


# --- the buckets --------------------------------------------------------------------


def test_buckets_for_a_simulated_normal_member(monkeypatch):
    """A user-tier simulation on default policy: staff-hub features land
    hidden (the compiled staff-gate), governance-locked ones advertise as
    locked with the user-safe reason, the rest advertise."""
    from sb.domain.server_management import help_preview as hp

    _patch_owners(monkeypatch)
    fields = run(hp._help_preview_fields(_ctx()))
    by_name = dict(fields)
    names = [n for n, _ in fields]
    assert names[0].startswith("📣 Advertised (")
    advertised = by_name[names[0]]
    assert "economy" in advertised
    # moderation lives under the staff-only moderation mother hub — the
    # compiled index's only hide.
    hidden_name = next(n for n in names if n.startswith("🙈 Hidden"))
    assert "moderation *(staff-gate)*" in by_name[hidden_name]
    # an admin-tier feature OUTSIDE the staff hubs is governance-locked
    # but STILL advertised (D-0054: the compiled index has no tier
    # filter) — shown as locked with the user-safe reason only.
    locked_name = next(n for n in names if n.startswith("🔒 Shown as locked"))
    locked = "\n".join(v for n, v in fields
                       if n.startswith("🔒 Shown as locked"))
    assert "🔒 **welcome** — You don't have access to this feature here." \
        in locked
    assert locked_name.startswith("🔒 Shown as locked (")
    assert names[-1] == "Simulation limits"


def test_buckets_for_a_simulated_administrator(monkeypatch):
    """An administrator simulation on default policy: nothing hides,
    nothing locks."""
    from sb.domain.server_management import help_preview as hp

    _patch_owners(monkeypatch)
    hp._tier_pick[(1, 42)] = "administrator"
    fields = run(hp._help_preview_fields(_ctx()))
    names = [n for n, _ in fields]
    assert names[0].startswith("📣 Advertised (43)")
    # empty buckets render no field (the shipped _chunk_field early-out).
    assert not any(n.startswith("🔒 Shown as locked") for n in names)
    assert not any(n.startswith("🙈 Hidden") for n in names)


def test_commands_disabled_locks_everything_advertised(monkeypatch):
    """A disabled-except-bootstrap guild: every advertised feature shows
    as locked with the shipped safe copy — never hidden (Help still
    advertises locked features, the shipped rule)."""
    from sb.domain.server_management import help_preview as hp

    _patch_owners(monkeypatch, mode="disabled_except_bootstrap")
    hp._tier_pick[(1, 42)] = "administrator"
    fields = run(hp._help_preview_fields(_ctx()))
    locked = "\n".join(v for n, v in fields
                       if n.startswith("🔒 Shown as locked"))
    assert "Commands are currently disabled in this server." in locked
    assert not any(n.startswith("🙈 Hidden") for n, _ in fields)


def test_unknown_never_hides(monkeypatch):
    """Raising owners degrade to unknown → everything still ADVERTISES
    (the model never hides what it could not verify-deny)."""
    from sb.domain.governance import store as gov_store
    from sb.domain.platform import command_access as ca
    from sb.domain.server_management import help_preview as hp

    async def boom(*a, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(ca, "read_policy_snapshot", boom)
    monkeypatch.setattr(gov_store, "fetch_visibility_for_chain", boom)
    hp._tier_pick[(1, 42)] = "administrator"
    fields = run(hp._help_preview_fields(_ctx()))
    names = [n for n, _ in fields]
    assert names[0] == "📣 Advertised (43)"
    # nothing locks, nothing hides — the buckets stay absent.
    assert not any(n.startswith("🔒 Shown as locked") for n in names)


# --- the tier select ------------------------------------------------------------------


def test_tier_options_mark_the_current_pick():
    from sb.domain.server_management import help_preview as hp

    options = run(hp._tier_options(_ctx()))
    assert [o["value"] for o in options] == [
        "user", "trusted", "staff", "moderator", "administrator"]
    assert [o["default"] for o in options] == [True, False, False, False,
                                               False]


@dataclasses.dataclass
class _Req:
    args: dict
    guild_id: int | None = 1
    channel_id: int | None = 2
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(
        default_factory=lambda: SimpleNamespace(user_id=42))


def test_tier_select_stashes_and_reopens(monkeypatch):
    from sb.domain.server_management import help_preview as hp
    from sb.kernel.panels import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return ""

    monkeypatch.setattr(engine, "open_panel", fake_open)
    handler = resolve(HandlerRef("server_management.help_preview_tier"))
    reply = run(handler(_Req(args={"values": ["staff"]})))
    assert reply.outcome == SUCCESS and reply.user_message is None
    assert hp.preview_tier_for(1, 42) == "staff"
    assert opened == ["server_management.help_preview"]

    reply = run(handler(_Req(args={"values": ["owner"]})))
    assert reply.user_message == "That audience tier is not available."
    assert hp.preview_tier_for(1, 42) == "staff"     # unchanged


# --- the hub flip + refs + manifest ---------------------------------------------------


def test_hub_help_preview_button_forwards_to_the_ported_panel():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in server_management_hub_spec().actions}
    action = by_id["help_preview"]
    assert action.handler == PanelRef("server_management.help_preview")
    # the hub-open goldens stay byte-identical: label/style/custom_id
    # unchanged on the flip.
    assert action.label == "👁 Help Preview"
    assert action.style is ActionStyle.SECONDARY
    assert action.custom_id_override == "server_management:help_preview"
    assert action.audience_tier == "administrator"


def test_refs_registered_and_pending_terminal_retired():
    from sb.domain.server_management import help_preview as hp
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, is_registered

    hp.ensure_help_preview_refs()
    assert is_registered(PanelRef("server_management.help_preview"))
    for name in ("server_management.render_help_preview",
                 "server_management.help_preview_tier"):
        assert is_registered(HandlerRef(name)), name
    for name in ("server_management.help_preview_fields",
                 "server_management.help_preview_tiers"):
        assert is_registered(ProviderRef(name)), name
    # the pending terminal is retired with this slice.
    assert not is_registered(
        HandlerRef("server_management.help_preview_pending"))


def test_manifest_declares_the_help_preview_panel():
    from sb.manifest.server_management import MANIFEST

    ids = [p.panel_id for p in MANIFEST.panels]
    assert ids == ["server_management.hub", "server_management.access_map",
                   "server_management.help_preview"]
