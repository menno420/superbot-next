"""S13 credential-rotation fakes: in-memory phase ledger + idempotency +
rollback-honoring transaction, monkeypatched onto sb.kernel.credentials.
rotation's imported symbols (the module imports names directly)."""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone

import pytest

from sb.kernel.credentials import rotation as rot
from sb.kernel.db.credentials import RotationRow
from sb.kernel.db.idempotency import PriorOutcome


class FakeLedger:
    """In-memory sb_credential_rotation honoring the CRUD contracts."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], RotationRow] = {}

    async def reserve_rotation(self, name, horizon_epoch, *, now, conn):
        self.rows.setdefault((name, horizon_epoch), RotationRow(
            name=name, horizon_epoch=horizon_epoch, phase="reserved",
            fingerprint=None, issued_at=None, verified_at=None, detail=None))

    async def read_rotation(self, name, horizon_epoch, *, conn):
        return self.rows.get((name, horizon_epoch))

    async def set_phase(self, name, horizon_epoch, phase, *, now,
                        fingerprint=None, detail=None, conn):
        prior = self.rows[(name, horizon_epoch)]
        self.rows[(name, horizon_epoch)] = RotationRow(
            name=name, horizon_epoch=horizon_epoch, phase=phase,
            fingerprint=fingerprint or prior.fingerprint,
            issued_at=now if phase == "issued_pending_verify" else prior.issued_at,
            verified_at=now if phase == "verified" else prior.verified_at,
            detail=detail or prior.detail)

    async def last_verified_at(self, *, conn):
        return {r.name: r.verified_at for r in self.rows.values()
                if r.phase == "verified"}


class FakeIdempotency:
    def __init__(self) -> None:
        self.keys: dict[str, str | None] = {}

    async def once(self, key, *, conn) -> bool:
        k = key.render()
        if k in self.keys:
            return False
        self.keys[k] = None
        return True

    async def record_outcome(self, key, outcome, *, result_ref=None, conn) -> None:
        self.keys[key.render()] = outcome

    async def read_outcome(self, key, *, conn):
        out = self.keys.get(key.render())
        if out is None:
            return None
        return PriorOutcome(outcome=out, result_ref=None, first_seen_at=0)


@pytest.fixture
def rot_env(monkeypatch):
    ledger = FakeLedger()
    idem = FakeIdempotency()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        rows_snapshot = dict(ledger.rows)
        keys_snapshot = dict(idem.keys)
        try:
            yield object()
        except BaseException:
            ledger.rows.clear(); ledger.rows.update(rows_snapshot)
            idem.keys.clear(); idem.keys.update(keys_snapshot)
            raise

    monkeypatch.setattr(rot, "ledger_db", ledger)
    monkeypatch.setattr(rot, "transaction", fake_transaction)
    monkeypatch.setattr(rot, "once", idem.once)
    monkeypatch.setattr(rot, "record_outcome", idem.record_outcome)
    monkeypatch.setattr(rot, "read_outcome", idem.read_outcome)
    rot.reset_rotation_ports_for_tests()
    yield ledger, idem
    rot.reset_rotation_ports_for_tests()


NOW = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
