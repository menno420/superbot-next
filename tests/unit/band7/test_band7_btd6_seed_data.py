"""Band 7 — the `!btd6 ops seed-data` terminal ported for real (the last
#144 parked-domain item's bounded core): the audited ``btd6.seed_data`` op
upserts every committed data file (+ the stats tree) into the
migration-054 ``btd6_data_blobs`` store, and the handler renders the
shipped receipt bytes (cogs/btd6/_ops_helpers.py seed_embed,
reconstructed at oracle head b0713fcd).

No golden drives this lane — parity/goldens/_sweep_skips.json pins the
capture skip for BOTH command forms ("bulk data seed — the golden would
embed the whole versioned BTD6 dataset (6.8MB)…"), so these tests pin the
oracle bytes directly: the seed-loop semantics (manifest.json skip, sha256
over the canonical dump, upsert-by-name idempotency), the receipt/empty
card literals, the shipped call ordering (content_drift BEFORE the seed),
and the administrator K6 floor the oracle's ADMIN_DENIED gate maps onto.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from sb.domain.btd6 import dataset
from sb.domain.btd6 import ops as btd6_ops
from sb.domain.btd6 import oracle_cards as cards
from sb.domain.btd6 import oracle_surface as surface
from sb.domain.btd6 import store as btd6_store
from sb.kernel.workflow.spec import LegKind
from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


def _ctx(params: dict, uid: int = 42, gid: int = 7):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=uid), guild_id=gid,
        request_id="r1", confirmed=True, params=params)


def _req(argv=(), gid=1, uid=42):
    return SimpleNamespace(
        args={"argv": tuple(argv)}, guild_id=gid, channel_id=5,
        request_id="r1", confirmed=True,
        actor=SimpleNamespace(user_id=uid))


class FakeBlobStore:
    """In-memory ``btd6_data_blobs`` twin — upsert keyed on name (the
    table's PK), matching the shipped ON CONFLICT (name) DO UPDATE."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.upserts = 0

    def install(self, monkeypatch):
        async def _upsert(conn, *, name, body, sha256=None):
            self.rows[name] = {"body": body, "sha256": sha256}
            self.upserts += 1

        monkeypatch.setattr(btd6_store, "upsert_data_blob", _upsert)
        return self


# --- the seed leg (oracle seed_postgres_from_files loop) ---------------------------


def test_seed_leg_upserts_every_bundled_blob(monkeypatch):
    fake = FakeBlobStore().install(monkeypatch)
    params: dict = {}

    out = run(btd6_ops._record_seed_data(None, _ctx(params)))

    names = dataset.list_blob_names()
    assert len(names) > 20                       # fixtures + the stats tree
    assert any(n.startswith("stats/") for n in names)
    assert set(fake.rows) == set(names)
    assert out.after == {"blobs": len(names)}
    # the ctx.params side-channel the handler reads (karma-refusal lane)
    assert params["_seed_count"] == len(names)


def test_seed_leg_skips_the_manifest_bucket_artifact(monkeypatch):
    """The oracle loop skips ``manifest.json`` (a bucket artifact, not a
    fixture) — carried verbatim even though the committed tree has none."""
    fake = FakeBlobStore().install(monkeypatch)
    real_names = dataset.list_blob_names()
    monkeypatch.setattr(
        dataset, "list_blob_names",
        lambda prefix="": ("manifest.json",) + real_names[:3])
    monkeypatch.setattr(
        dataset, "read_blob",
        lambda name: {"stub": name} if name != "manifest.json" else {"x": 1})

    params: dict = {}
    run(btd6_ops._record_seed_data(None, _ctx(params)))
    assert "manifest.json" not in fake.rows
    assert params["_seed_count"] == 3


def test_seed_leg_sha256_is_the_canonical_dump(monkeypatch):
    """sha256 over ``json.dumps(body, sort_keys=True, ensure_ascii=False)``
    — the exact digest the oracle's content_drift compares against."""
    fake = FakeBlobStore().install(monkeypatch)
    run(btd6_ops._record_seed_data(None, _ctx({})))

    body = dataset.read_blob("towers.json")
    want = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"),
    ).hexdigest()
    assert fake.rows["towers.json"]["sha256"] == want


def test_seed_leg_reruns_idempotently(monkeypatch):
    """"Safe to re-run any time (it upserts)" — the shipped receipt's own
    words: a second run rewrites the same names, no growth."""
    fake = FakeBlobStore().install(monkeypatch)
    run(btd6_ops._record_seed_data(None, _ctx({})))
    first = dict(fake.rows)
    run(btd6_ops._record_seed_data(None, _ctx({})))
    assert set(fake.rows) == set(first)
    assert fake.upserts == 2 * len(first)


# --- the op spec (K6 floor + leg shape) ---------------------------------------------


def test_seed_op_spec_is_the_administrator_db_lane():
    spec = btd6_ops.SEED
    assert spec.op_key == "btd6.seed_data"
    # the shipped gate verbatim: is_administrator_member or ADMIN_DENIED
    assert spec.authority_ref == "administrator"
    assert spec.audit_verb == "btd6_data_seeded"
    assert len(spec.legs) == 1                    # ONE DB leg, no EFFECT leg
    assert spec.legs[0].kind is LegKind.DB
    assert spec.legs[0].reversibility == "reversible"


def test_blob_store_is_declared_on_the_manifest():
    from sb.manifest.btd6 import MANIFEST

    tables = {s.table for s in MANIFEST.stores}
    assert "btd6_data_blobs" in tables
    spec = btd6_store.BTD6_DATA_BLOBS_STORE
    assert spec.bears_value is False
    assert spec.data_class.value == "none"        # versioned fixtures, no PII


def test_content_drift_is_the_file_backend_arm():
    # the shipped file-backend answer — None (no postgres-serving store to
    # drift against); the seed receipt's changed-line stays empty.
    assert dataset.content_drift() is None


# --- the receipt cards (oracle seed_embed bytes) ------------------------------------


def test_seed_empty_card_bytes():
    card = cards.seed_empty_card()
    assert card.title == "🌱 BTD6 data seed"
    assert card.description == (
        "No bundled data files were found to seed. If the repo data has "
        "already been removed, re-generate the fixtures first.")
    assert card.style_token == "orange"


def test_seed_receipt_card_bytes_no_drift():
    card = cards.seed_receipt_card(74, "55.1", None)
    assert card.title == "🌱 BTD6 data seeded"
    assert card.style_token == "green"
    assert card.description == (
        "Upserted **74** blobs into the `btd6_data_blobs` table and "
        "**reloaded the live dataset** — the new data is being served "
        "now; no restart needed.\n"
        "**Now serving:** game version `55.1`.\n\n"
        "First-time setup only: set `BTD6_DATA_BACKEND` = `postgres` in "
        "Railway → Variables, then confirm `!btd6 status` reads "
        "`Data source: postgres (…)`.\n\n"
        "Safe to re-run any time (it upserts).")


def test_seed_receipt_card_versionless_drops_the_serving_line():
    card = cards.seed_receipt_card(3, "", None)
    assert "**Now serving:**" not in card.description
    assert card.description.startswith(
        "Upserted **3** blobs into the `btd6_data_blobs` table and ")


def test_seed_receipt_card_changed_report_bytes():
    """The #1263 changed-file report: first 8 names backticked, the
    overflow folded into ` +N more` — oracle bytes."""
    changed = [f"file{i}.json" for i in range(10)]
    card = cards.seed_receipt_card(74, "55.1", changed)
    shown = ", ".join(f"`file{i}.json`" for i in range(8))
    assert (f"\n**Applied 10 changed file(s):** {shown} +2 more."
            in card.description)
    short = cards.seed_receipt_card(74, "", ["a.json"])
    assert "\n**Applied 1 changed file(s):** `a.json`." in short.description


# --- the handler (shipped seed_embed sequence) ---------------------------------------


class _HandlerSeams:
    def __init__(self, monkeypatch, *, outcome=SUCCESS, count=74,
                 user_message=None):
        self.cards = []
        self.reset_calls = []
        self.run_ctxs = []
        outer = self

        async def _fake_run(ref, ctx):
            outer.run_ctxs.append((str(ref), ctx))
            if outcome == SUCCESS:
                ctx.params["_seed_count"] = count
            return SimpleNamespace(outcome=outcome,
                                   user_message=user_message)

        async def _fake_card(req, embed):
            outer.cards.append(embed)

        from sb.domain.btd6 import stats
        from sb.kernel.workflow import engine

        monkeypatch.setattr(engine, "run", _fake_run)
        monkeypatch.setattr(surface, "_card", _fake_card)
        monkeypatch.setattr(
            dataset, "reset_cache",
            lambda: self.reset_calls.append("dataset"))
        monkeypatch.setattr(
            stats, "reset_stats_cache",
            lambda: self.reset_calls.append("stats"))


def test_cmd_ops_seed_success_sends_the_receipt(monkeypatch):
    seams = _HandlerSeams(monkeypatch, count=74)
    reply = run(surface.cmd_ops_seed(_req()))
    assert reply is None
    assert len(seams.cards) == 1
    card = seams.cards[0]
    assert card.title == "🌱 BTD6 data seeded"
    assert "Upserted **74** blobs" in card.description
    # the real committed game version rode the receipt
    assert "**Now serving:** game version `55.1`." in card.description
    # the shipped "applies immediately" reload ran (file-backend flavor)
    assert seams.reset_calls == ["dataset", "stats"]
    # the audited op is the one write path
    assert "btd6.seed_data" in seams.run_ctxs[0][0]


def test_cmd_ops_seed_zero_files_sends_the_orange_card(monkeypatch):
    seams = _HandlerSeams(monkeypatch, count=0)
    reply = run(surface.cmd_ops_seed(_req()))
    assert reply is None
    assert seams.cards[0].title == "🌱 BTD6 data seed"
    assert seams.cards[0].style_token == "orange"
    assert seams.reset_calls == []               # no seed, no reload


def test_cmd_ops_seed_refusal_is_honest(monkeypatch):
    seams = _HandlerSeams(monkeypatch, outcome=BLOCKED,
                          user_message="You need administrator for that.")
    reply = run(surface.cmd_ops_seed(_req()))
    assert reply is not None
    assert reply.outcome == BLOCKED
    assert reply.user_message == "You need administrator for that."
    assert seams.cards == []
    assert seams.reset_calls == []
