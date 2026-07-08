"""S13 — credential lifecycle: registry gate, cadence detector, rotation
executor phase machine (frozen L0 spec 12 §2.A/§2.B)."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from sb.kernel.credentials import cadence as cad
from sb.kernel.credentials import rotation as rot
from sb.spec.credentials import (
    CREDENTIAL_REGISTRY,
    BlastTier,
    CredentialSpec,
    CredentialStore,
    RevocationRef,
    RotationPosture,
    credential_for,
)
from tests.unit.credentials.conftest import NOW
from tools.check_credential_lifecycle import check as lifecycle_check


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


# --- the registry + gate (spec 12 §2.A) -----------------------------------------

class TestRegistryGate:
    def test_committed_registry_clean(self):
        assert lifecycle_check() == []

    def test_cadence_posture_mismatch_red(self):
        bad = (CredentialSpec("x", CredentialStore.RAILWAY_ACCOUNT, None,
                              RotationPosture.AUTONOMOUS, None,
                              RevocationRef.RAILWAY_VAR_ROTATE, BlastTier.SPEND),)
        problems = lifecycle_check(registry=CREDENTIAL_REGISTRY + bad)
        assert any("needs a cadence_days" in p for p in problems)

    def test_event_driven_with_cadence_red(self):
        bad = (CredentialSpec("x", CredentialStore.RAILWAY_ACCOUNT, None,
                              RotationPosture.ON_COMPROMISE, 30,
                              RevocationRef.RAILWAY_VAR_ROTATE, BlastTier.SPEND),)
        problems = lifecycle_check(registry=CREDENTIAL_REGISTRY + bad)
        assert any("must not carry cadence_days" in p for p in problems)

    def test_dangling_config_ref_red(self):
        bad = (CredentialSpec("x", CredentialStore.WORKER_ENV, "NO_SUCH_SECRET",
                              RotationPosture.ON_COMPROMISE, None,
                              RevocationRef.RAILWAY_VAR_ROTATE, BlastTier.SPEND),)
        problems = lifecycle_check(registry=CREDENTIAL_REGISTRY + bad)
        assert any("names no credential-bearing" in p for p in problems)

    def test_partition_invariant_red(self):
        bad = (CredentialSpec("x", CredentialStore.GITHUB_APP, "SB_PROD_ATTEST",
                              RotationPosture.ON_COMPROMISE, None,
                              RevocationRef.GITHUB_TOKEN_SETTINGS, BlastTier.CONTROL),)
        problems = lifecycle_check(registry=CREDENTIAL_REGISTRY + bad)
        assert any("WORKER_ENV" in p and "violated" in p for p in problems)

    def test_uncovered_worker_secret_red(self):
        # dropping a WORKER_ENV row leaves its config field uncovered
        registry = tuple(c for c in CREDENTIAL_REGISTRY
                         if c.config_ref != "SB_PROD_ATTEST")
        problems = lifecycle_check(registry=registry)
        assert any("SB_PROD_ATTEST" in p and "no CREDENTIAL_REGISTRY" in p
                   for p in problems)

    def test_duplicate_row_red(self):
        problems = lifecycle_check(
            registry=CREDENTIAL_REGISTRY + (credential_for("railway_account_token"),))
        assert any("duplicate registry row" in p for p in problems)

    def test_blast_tier_total_order(self):
        assert (BlastTier.ACCOUNT > BlastTier.PROD_DATA > BlastTier.CONTROL
                > BlastTier.BOT_PRESENCE > BlastTier.SPEND > BlastTier.TEST_ONLY)


# --- the cadence detector (spec 12 §2.B(1)) --------------------------------------

class TestCadence:
    def test_never_rotated_cadence_rows_due(self):
        due = cad.rotation_due({}, NOW)
        names = {d.cred.name for d in due}
        # every AUTONOMOUS/OWNER_PROMPT row, no MANAGED/ON_COMPROMISE row
        assert "anthropic_api_key" in names and "railway_account_token" in names
        assert "prod_dsn" not in names and "discord_prod_bot_token" not in names

    def test_fresh_rotation_not_due(self):
        last = {"anthropic_api_key": NOW - timedelta(days=5)}
        due = {d.cred.name for d in cad.rotation_due(last, NOW)}
        assert "anthropic_api_key" not in due

    def test_overdue_rotation_due_and_horizon_stable(self):
        last = {"anthropic_api_key": NOW - timedelta(days=91)}
        due = [d for d in cad.rotation_due(last, NOW)
               if d.cred.name == "anthropic_api_key"]
        assert len(due) == 1 and not due[0].is_root
        # horizon is period-stable: same epoch an hour later
        later = NOW + timedelta(hours=1)
        assert cad.horizon_epoch(due[0].cred, NOW) == cad.horizon_epoch(due[0].cred, later)

    def test_root_rows_prompt_not_arm(self, monkeypatch):
        prompts: list[str] = []
        monkeypatch.setattr(cad, "record_operator_finding",
                            lambda **kw: prompts.append(kw["summary"]))

        class FakeLane:
            armed: list[tuple] = []

            async def arm_one_shot(self, spec, fire_at, *, payload=None, **kw):
                self.armed.append((spec.name, dict(payload or {})))

        lane = FakeLane()
        armed, prompted = run(cad.arm_due_rotations(lane, NOW, last_rotated={}))
        assert prompted == 2  # the two roots
        assert armed == len(lane.armed) > 0
        assert all(name == "credentials:rotate" for name, _ in lane.armed)
        assert all("name" in p and "horizon_epoch" in p for _, p in lane.armed)


# --- the rotation executor (spec 12 §2.B(1b-1c)) ---------------------------------

class FakeProvider:
    def __init__(self, *, verify_ok=True, orphan=None):
        self.issued: list[str] = []
        self.verified: list[str] = []
        self.verify_ok = verify_ok
        self.orphan = orphan

    async def issue(self, cred):
        self.issued.append(cred.name)
        return f"fp-{cred.name}"

    async def adopt_orphan(self, cred, horizon_epoch):
        return self.orphan

    async def verify(self, cred, fingerprint):
        self.verified.append(fingerprint)
        return self.verify_ok


class TestRotationExecutor:
    def test_key_is_horizon_stable(self):
        k = rot.rotation_key("anthropic_api_key", 114)
        assert k.render() == "credential.rotation:0:anthropic_api_key:114"

    def test_fresh_rotation_reaches_verified(self, rot_env):
        ledger, idem = rot_env
        provider = FakeProvider()
        rot.install_rotation_provider(provider)
        result = run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert result == "verified"
        row = ledger.rows[("anthropic_api_key", 114)]
        assert row.phase == "verified" and row.fingerprint == "fp-anthropic_api_key"
        assert idem.keys[rot.rotation_key("anthropic_api_key", 114).render()] == "success"
        assert provider.issued == ["anthropic_api_key"]

    def test_issued_pending_verify_resume_skips_reissue(self, rot_env):
        """The swap-redeploy landing: re-run completes the verify, never
        mints a second credential (spec 12 §2.B(1c) re-run rule)."""
        ledger, idem = rot_env
        provider = FakeProvider(verify_ok=False)
        rot.install_rotation_provider(provider)
        with pytest.raises(rot.RotationUnavailable):
            run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert ledger.rows[("anthropic_api_key", 114)].phase == "issued_pending_verify"
        assert provider.issued == ["anthropic_api_key"]
        # the re-fire (boot-reconcile): verify now serves
        provider.verify_ok = True
        result = run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert result == "verified"
        assert provider.issued == ["anthropic_api_key"]  # NO second issue

    def test_reserved_resume_adopts_orphan(self, rot_env):
        ledger, idem = rot_env
        # simulate a crash after txn-1: guard + RESERVED row committed
        run(self._reserve_only(ledger, idem))
        provider = FakeProvider(orphan="fp-orphan")
        rot.install_rotation_provider(provider)
        result = run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert result == "verified"
        assert provider.issued == []  # adopted, never re-issued
        assert ledger.rows[("anthropic_api_key", 114)].fingerprint == "fp-orphan"

    async def _reserve_only(self, ledger, idem):
        await idem.once(rot.rotation_key("anthropic_api_key", 114), conn=None)
        await ledger.reserve_rotation("anthropic_api_key", 114, now=NOW, conn=None)

    def test_terminal_outcome_noops(self, rot_env):
        ledger, idem = rot_env
        provider = FakeProvider()
        rot.install_rotation_provider(provider)
        run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        result = run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert result == "noop"
        assert provider.issued == ["anthropic_api_key"]  # once total

    def test_no_provider_fails_loud(self, rot_env, monkeypatch):
        ledger, idem = rot_env
        findings: list[str] = []
        monkeypatch.setattr(rot, "record_operator_finding",
                            lambda **kw: findings.append(kw["summary"]))
        result = run(rot.run_rotation("anthropic_api_key", 114, clock=lambda: NOW))
        assert result == "failed"
        assert ledger.rows[("anthropic_api_key", 114)].phase == "failed"
        assert idem.keys[rot.rotation_key("anthropic_api_key", 114).render()] == "blocked"
        assert any("rotation blocked" in f for f in findings)

    def test_task_spec_passes_scheduler_fences(self):
        from sb.kernel.scheduler.due_queue import _check_task
        _check_task(rot.ROTATION_TASK)  # raises on violation

    def test_handler_registered(self):
        from sb.spec import refs
        try:
            fn = refs.resolve(refs.HandlerRef("kernel.credentials.rotation_fire"))
        except Exception:
            # another suite ran clear_ref_table() (the sanctioned test seam);
            # re-register the module's decorator target and retry.
            refs.handler("kernel.credentials.rotation_fire")(rot.rotation_fire)
            fn = refs.resolve(refs.HandlerRef("kernel.credentials.rotation_fire"))
        assert fn is rot.rotation_fire
