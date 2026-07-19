"""Display-scope settings-status renderer stored-value coercion sweep.

The security + image_moderation subsystems each consist ONLY of a
``panels.py`` — so their ``_render_status`` renderer_override is their SOLE
stored-config coercion site. Each render reads every displayed field through
the K7 ``resolve`` seam and defends against malformed / off-type stored rows
with local ``_flag_of`` (present truthy/falsy-token recognition) and
``_int_of`` (``int(str(resolve(...)).strip())`` with an
``except (TypeError, ValueError)`` fallback) helpers, plus
``age_action = str(resolve(...) or "alert")``. Removing any of those swallows
would let a bad KV row silently ship a WRONG DISPLAYED toggle or number.

The pre-existing coverage (band6 hub-wiring / band2 manifest) drives these
panels only for registration + hub wiring — never for present/malformed
stored-value RENDERING. These tests drive ``_render_status`` end-to-end
through the same ``resolve`` seam the panel uses and assert the REAL rendered
embed bytes (the displayed toggle / number). Every assertion was verified
against a live probe of the real renderer before commit.

HONESTY NOTE on ``_flag_of``: it is the welcome/counters *membership* shape —
a present unrecognized token resolves to ``False`` via the truthy-token
membership test, and the ``fallback`` argument is the ``None``/UNSET-only leg
(every call site here passes ``fallback=False``, so unset also renders off).
This differs from automod/server_logging ``_as_bool`` (return-the-fallback on
an unrecognized present token). The hazard pinned is the silent wrong toggle:
drop the membership tuple and a stored ``"on"``/``"yes"`` would render off.
"""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_settings():
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


def _ctx():
    from types import SimpleNamespace

    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


def _install(subsystem: str, names: tuple[str, ...], store: dict) -> None:
    """Declare ``names`` under ``subsystem`` (default None) and install a
    per-guild reader backed by ``store`` (key ``"subsystem.name"`` -> value)."""
    from sb.kernel import settings as ksettings

    for name in names:
        ksettings.register_setting(
            ksettings.SettingDeclaration(subsystem=subsystem, name=name,
                                         default=None))

    async def reader(guild_id, key):
        if guild_id is not None and key in store:
            return store[key]
        return ksettings.UNSET

    ksettings.install_settings_reader(reader)


_SECURITY_KEYS = (
    "enabled", "raid_enabled", "age_enabled",
    "raid_join_count", "raid_window_seconds", "raid_slowmode_seconds",
    "raid_lockdown_seconds", "age_min_days", "age_action",
)
_IMAGE_KEYS = (
    "enabled", "sexual_enabled", "violence_enabled",
    "harassment_enabled", "hate_enabled", "threshold_percent",
)


# --- security ----------------------------------------------------------------------

def test_security_status_flags_and_ints_from_present_stored_values():
    """Present truthy/falsy flag tokens flip the displayed toggle, a real
    ``bool`` passes through, a stripped numeric string coerces to its int, a
    malformed int reverts to the shipped fallback (the ``except`` swallow), and
    ``age_action`` renders the present literal. No slowmode binding ⇒ the
    alert-only lockdown branch."""
    from sb.domain.security.panels import _render_status, status_spec

    _install("security", _SECURITY_KEYS, {
        "security.enabled": "on",             # truthy token -> Master 🟢 on
        "security.raid_enabled": True,        # real bool passes through -> on
        "security.age_enabled": "garbage",    # unrecognized present -> off
        "security.raid_join_count": " 25 ",   # stripped numeric string -> 25
        "security.raid_window_seconds": "not-int",  # malformed -> fallback 60
        "security.age_min_days": "3",         # numeric string -> 3
        "security.age_action": "kick",        # present literal preserved
    })

    r = run(_render_status(status_spec(), _ctx()))
    assert r.embed.description == (
        "**Master:** 🟢 on\n📢 **Alert channel:** *(unset)*")
    raid_name, raid_val, raid_inline = r.embed.fields[0]
    assert raid_name == "🚨 Raid detection — 🟢 on"      # real-bool passthrough
    assert raid_val == (
        "Trigger: **25** joins / **60s**\n"             # 25 coerced, 60 fallback
        "Lockdown: alert-only (no slowmode channel set)")
    assert raid_inline is False
    age_name, age_val, _ = r.embed.fields[1]
    assert age_name == "⚠️ Account-age filter — ⚫ off"   # unrecognized -> off
    assert age_val == "Threshold: **3** days\nAction: **kick**"


def test_security_status_slowmode_branch_pins_coerced_seconds(monkeypatch):
    """With ``raid_slowmode_channel`` bound AND ``raid_slowmode_seconds > 0``
    the ``applies_raid_slowmode`` branch renders the slowmode sentence — the
    ONLY render path that displays ``raid_slowmode_seconds`` /
    ``raid_lockdown_seconds``. A stripped numeric slowmode string coerces; a
    malformed lockdown value reverts to fallback 300."""
    import sb.kernel.db.settings as dbs

    async def _fake_binding(guild_id, subsystem, name, conn=None):
        return 999 if name == "raid_slowmode_channel" else None

    monkeypatch.setattr(dbs, "get_binding", _fake_binding)

    from sb.domain.security.panels import _render_status, status_spec

    _install("security", _SECURITY_KEYS, {
        "security.raid_slowmode_seconds": " 15 ",     # stripped numeric -> 15
        "security.raid_lockdown_seconds": "not-int",  # malformed -> fallback 300
    })

    r = run(_render_status(status_spec(), _ctx()))
    _, raid_val, _ = r.embed.fields[0]
    assert raid_val == (
        "Trigger: **10** joins / **60s**\n"           # both unset -> fallbacks
        "Lockdown: slowmode **15s** for **300s**")     # 15 coerced, 300 fallback


def test_security_status_all_unset_renders_shipped_fallbacks():
    """Contrast: every setting UNSET renders the shipped fallback display —
    flags off, the shipped int fallbacks (10 joins / 60s, 7 days), and
    ``age_action`` reverting to ``"alert"`` via ``str(None or "alert")``."""
    from sb.domain.security.panels import _render_status, status_spec

    _install("security", _SECURITY_KEYS, {})

    r = run(_render_status(status_spec(), _ctx()))
    assert r.embed.description == (
        "**Master:** ⚫ off\n📢 **Alert channel:** *(unset)*")
    assert r.embed.fields[0] == (
        "🚨 Raid detection — ⚫ off",
        "Trigger: **10** joins / **60s**\n"
        "Lockdown: alert-only (no slowmode channel set)",
        False)
    assert r.embed.fields[1] == (
        "⚠️ Account-age filter — ⚫ off",
        "Threshold: **7** days\nAction: **alert**",
        False)


# --- image_moderation --------------------------------------------------------------

def test_image_moderation_status_flags_and_threshold_from_present_values():
    """Present truthy/falsy category tokens flip each displayed toggle, a real
    ``bool`` passes through, and a stripped numeric ``threshold_percent`` string
    coerces into the ``≥ N% confidence`` line."""
    from sb.domain.image_moderation.panels import _render_status, status_spec

    _install("image_moderation", _IMAGE_KEYS, {
        "image_moderation.enabled": "yes",              # truthy -> Master on
        "image_moderation.sexual_enabled": True,        # real bool -> on
        "image_moderation.violence_enabled": "off",     # falsy token -> off
        "image_moderation.harassment_enabled": "garbage",  # unrecognized -> off
        "image_moderation.hate_enabled": "1",           # truthy token -> on
        "image_moderation.threshold_percent": " 55 ",   # stripped numeric -> 55
    })

    r = run(_render_status(status_spec(), _ctx()))
    assert r.embed.description == (
        "**Master:** 🟢 on\n"
        "**Action threshold:** ≥ 55% confidence\n"
        "\n"
        "🔞 **Sexual** — 🟢 on\n"
        "🔪 **Violence** — ⚫ off\n"
        "😠 **Harassment** — ⚫ off\n"
        "🚫 **Hate** — 🟢 on")


def test_image_moderation_status_malformed_threshold_reverts_to_default():
    """A malformed ``threshold_percent`` reverts to the shipped fallback 80 (the
    ``_int_of`` ``except`` swallow), and every unset category flag renders off."""
    from sb.domain.image_moderation.panels import _render_status, status_spec

    _install("image_moderation", _IMAGE_KEYS, {
        "image_moderation.threshold_percent": "not-int",  # malformed -> 80
    })

    r = run(_render_status(status_spec(), _ctx()))
    assert r.embed.description == (
        "**Master:** ⚫ off\n"
        "**Action threshold:** ≥ 80% confidence\n"
        "\n"
        "🔞 **Sexual** — ⚫ off\n"
        "🔪 **Violence** — ⚫ off\n"
        "😠 **Harassment** — ⚫ off\n"
        "🚫 **Hate** — ⚫ off")
