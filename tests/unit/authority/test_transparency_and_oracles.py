"""Transparency trigger (spec 04 §3.5, RC-5/RC-15), the owner predicate,
the K1 bootstrap oracle, and the P4 compiler arming."""

import asyncio
import dataclasses
from datetime import datetime, timezone

from sb.kernel.authority import owner as owner_mod
from sb.kernel.authority.channel_access import CommandAccessSnapshot, resolve_channel_access
from sb.kernel.authority.decision import AuthorityDecision
from sb.kernel.authority.transparency import (
    LoggingTransparencySink,
    TransparencySink,
    build_transparency_audit,
)
from sb.namespace.bootstrap import BOOTSTRAP_COMMANDS, is_bootstrap_command
from sb.spec.authority import Lane
from sb.spec.outcomes import DenialReason


def _decision(**overrides):
    kw = dict(allowed=True, authority_ref="", lane=Lane.CAPABILITY,
              required_tier="administrator", member_tier="user",
              owner_override=True, lane_would_deny=True,
              reason=DenialReason.ALLOWED, detail="", denial_message=None)
    kw.update(overrides)
    return AuthorityDecision(**kw)


_CLOCK = lambda: datetime(2026, 7, 8, tzinfo=timezone.utc)  # noqa: E731


def _build(auth, channel=None):
    return build_transparency_audit(
        auth, channel, actor_id=111, guild_id=5, target_key="settings",
        surface="slash", clock=_CLOCK)


def test_trigger_fires_only_when_override_carried_the_dispatch():
    audit = _build(_decision())
    assert audit is not None
    assert audit.would_deny_reason is DenialReason.AUTHORITY
    assert audit.timestamp == _CLOCK()
    # override was a no-op => no audit noise
    assert _build(_decision(lane_would_deny=False)) is None
    # no override at all => never fires (setup_delegate case included)
    assert _build(_decision(owner_override=False)) is None


def test_trigger_reads_the_channel_leg_too():
    channel = asyncio.run(resolve_channel_access(
        CommandAccessSnapshot(mode="disabled_except_bootstrap"), 1,
        owner_override=True, is_bootstrap=False, is_operator=False,
        is_owner=False))
    audit = _build(_decision(lane_would_deny=False), channel)
    assert audit is not None
    assert audit.would_deny_reason is DenialReason.CHANNEL


def test_logging_sink_satisfies_the_port():
    sink = LoggingTransparencySink()
    assert isinstance(sink, TransparencySink)
    audit = _build(_decision())
    asyncio.run(sink.emit(audit))
    asyncio.run(sink.flush_digest())


def test_owner_predicate_and_member_gate():
    owner_mod.reset_for_tests()
    try:
        class Cfg:
            BOT_OWNER_USER_ID = 42
            EXTRA_OWNER_USER_IDS = ()
        owner_mod.install_owner_config(Cfg())
        assert owner_mod.is_platform_owner(42)
        assert not owner_mod.is_platform_owner(43)
        assert not owner_mod.is_platform_owner(None)
        assert owner_mod.owner_override_holds(42, True)
        assert not owner_mod.owner_override_holds(42, False)  # X-7 member-gated
    finally:
        owner_mod.reset_for_tests()


def test_bootstrap_oracle_ported_verbatim():
    assert "setup" in BOOTSTRAP_COMMANDS and len(BOOTSTRAP_COMMANDS) == 24
    assert is_bootstrap_command("help")
    assert is_bootstrap_command("platform identity")   # space root
    assert is_bootstrap_command("setup-hub")           # hyphen root
    assert is_bootstrap_command("  SETTINGS  ")        # normalized
    assert not is_bootstrap_command("economy-daily")
    assert not is_bootstrap_command(None)
    assert not is_bootstrap_command("")


def test_compiler_p4_is_armed_by_the_leaf():
    """Landing sb/spec/authority.py arms 01's P4 (spec 01 §11): a manifest
    spec carrying a bad authority_ref is now a COMPILE_ERROR."""
    from sb.spec.manifest import SubsystemManifest
    from sb.spec.refs import clear_ref_table, handler
    from sb.spec.roles import register_field_roles
    from tools.manifest_compile import compile_manifests

    @dataclasses.dataclass(frozen=True)
    class AuthCommandSpec:
        name: str
        surface: str = "slash"
        route: object = None
        authority_ref: str = ""

    register_field_roles("AuthCommandSpec", name="S", surface="S", route="S",
                         authority_ref="S")

    clear_ref_table()

    @handler("authproof.noop")
    def _noop():  # pragma: no cover
        pass

    from sb.spec.refs import HandlerRef

    def _manifest(ref):
        return SubsystemManifest(
            key="authproof",
            commands=(AuthCommandSpec("authprobe", route=HandlerRef("authproof.noop"),
                                      authority_ref=ref),),
        )

    good = compile_manifests(manifests=[_manifest("moderator")])
    assert good.ok, [dataclasses.astuple(v) for v in good.violations]

    bad = compile_manifests(manifests=[_manifest("NotATier")])
    assert not bad.ok
    assert any(v.pass_name == "authority" and "bad_authority" in v.detail
               for v in bad.violations)

    clear_ref_table()
