"""Unit checks for sb.kernel.config (K0/S1, frozen L0 spec 05 §3.1-§3.2)."""

import pytest

from sb.kernel.config import (
    ConfigError,
    StartupError,
    assert_intents,
    load_config,
    parse_bool,
    parse_dsn,
    preflight,
)
from sb.spec.config import CONFIG_FIELDS, ConfigType, DataPlane

MINIMAL_TEST_ENV = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "token-value",
    "DATABASE_URL": "postgres://u:p@db.test.internal:5432/sb?sb_plane=test",
    "SB_DATA_PLANE": "test",
}


# --- parse_bool: THE one grammar --------------------------------------------

@pytest.mark.parametrize("raw", ["1", "true", "YES", " on ", "y", "T"])
def test_parse_bool_truthy(raw):
    assert parse_bool(raw, env_var="X") is True


@pytest.mark.parametrize("raw", ["", "0", "false", "NO", " off ", "n", "F"])
def test_parse_bool_falsy(raw):
    assert parse_bool(raw, env_var="X") is False


def test_parse_bool_unknown_token_is_config_error():
    with pytest.raises(ConfigError):
        parse_bool("maybe", env_var="X")


# --- parse_dsn: shape only, never connects -----------------------------------

def test_parse_dsn_accepts_postgres_shapes():
    dsn = "postgresql://user:pw@host:5432/dbname"
    assert parse_dsn(dsn, env_var="DATABASE_URL") == dsn


@pytest.mark.parametrize("dsn", [
    "mysql://u@h/db",            # wrong scheme
    "postgres:///db",            # no host
    "postgres://u@host:5432",    # no db name
    "postgres://u@host:5432/",   # empty db name
])
def test_parse_dsn_rejects_bad_shapes(dsn):
    with pytest.raises(ConfigError):
        parse_dsn(dsn, env_var="DATABASE_URL")


# --- registry sanity ----------------------------------------------------------

def test_every_secret_and_dsn_is_redacted():
    for spec in CONFIG_FIELDS:
        if spec.type in (ConfigType.SECRET, ConfigType.DSN):
            assert spec.redact, spec.env_var


def test_env_names_are_unique_and_valid_identifiers():
    names = [s.env_var for s in CONFIG_FIELDS]
    assert len(names) == len(set(names))
    for name in names:
        assert name.isidentifier()


# --- preflight ---------------------------------------------------------------

def test_preflight_happy_path_test_plane():
    cfg = preflight(MINIMAL_TEST_ENV)
    assert cfg.BOT_PREFIX == "!"                      # default applied
    assert cfg.DB_COMMAND_TIMEOUT_S == 30.0
    assert cfg.data_plane is DataPlane.TEST
    assert cfg.is_configured("DISCORD_BOT_TOKEN_PRODUCTION")
    assert not cfg.is_configured("ANTHROPIC_API_KEY")


def test_preflight_aggregates_all_missing_required():
    with pytest.raises(StartupError) as exc_info:
        preflight({})
    missing = {e.env_var for e in exc_info.value.errors}
    assert {"DISCORD_BOT_TOKEN_PRODUCTION", "DATABASE_URL", "SB_DATA_PLANE"} <= missing


def test_preflight_coercion_and_min_floor():
    env = dict(MINIMAL_TEST_ENV, DB_COMMAND_TIMEOUT_S="0.5")  # below min=1.0
    with pytest.raises(StartupError) as exc_info:
        preflight(env)
    assert any(e.env_var == "DB_COMMAND_TIMEOUT_S" for e in exc_info.value.errors)


def test_preflight_choices_membership():
    env = dict(MINIMAL_TEST_ENV, SETUP_ADVISOR_PROVIDER="banana")
    with pytest.raises(StartupError):
        preflight(env)


def test_csv_coercion_yields_tuple():
    env = dict(MINIMAL_TEST_ENV, EXTRA_OWNER_USER_IDS="123, 456,789")
    cfg = preflight(env)
    assert cfg.EXTRA_OWNER_USER_IDS == ("123", "456", "789")


def test_repr_redacts_secrets_and_dsn():
    cfg = preflight(MINIMAL_TEST_ENV)
    rendered = repr(cfg)
    assert "token-value" not in rendered
    assert "db.test.internal" not in rendered
    assert "redacted" in rendered


def test_config_is_frozen():
    cfg = preflight(MINIMAL_TEST_ENV)
    with pytest.raises(Exception):
        cfg.BOT_PREFIX = "?"


# --- data-plane rail (spec 05 §3.5) -------------------------------------------

def test_test_plane_unset_allowlist_boots_any_host_and_logs_loud(caplog):
    """Q-0263.1 (ORDER 011): SB_TEST_DB_HOSTS unset/empty => open mode.
    Preflight accepts ANY host on the test plane, never refuses, never emits
    an error naming the variable — it logs the connected host once, loudly,
    one line."""
    env = dict(MINIMAL_TEST_ENV, DATABASE_URL="postgres://u:p@prod-db.example.com:5432/sb")
    assert "SB_TEST_DB_HOSTS" not in env
    with caplog.at_level("WARNING", logger="sb.db.data_plane"):
        cfg = preflight(env)  # boots — no StartupError
    assert cfg.data_plane is DataPlane.TEST
    loud = [r for r in caplog.records if r.name == "sb.db.data_plane"]
    assert len(loud) == 1                      # once, one line
    assert loud[0].levelname == "WARNING"      # loud
    assert "prod-db.example.com" in loud[0].getMessage()  # names the connected host
    assert "SB_TEST_DB_HOSTS" not in loud[0].getMessage()  # never names the variable
    # empty string is the same as unset
    env["SB_TEST_DB_HOSTS"] = ""
    assert preflight(env).data_plane is DataPlane.TEST


def test_test_plane_allowlist_enforced_only_when_set(caplog):
    """The allowlist check engages ONLY when deliberately set non-empty:
    a non-allowlisted host without the ?sb_plane=test marker still refuses."""
    env = dict(MINIMAL_TEST_ENV,
               DATABASE_URL="postgres://u:p@prod-db.example.com:5432/sb",
               SB_TEST_DB_HOSTS="db.test.internal")
    with pytest.raises(StartupError):
        preflight(env)
    # allowlisted host passes, silently (no open-mode log)
    env["SB_TEST_DB_HOSTS"] = "prod-db.example.com"
    with caplog.at_level("WARNING", logger="sb.db.data_plane"):
        assert preflight(env).data_plane is DataPlane.TEST
    assert not [r for r in caplog.records if r.name == "sb.db.data_plane"]
    # the ?sb_plane=test marker still passes even when the host is off-list
    env["SB_TEST_DB_HOSTS"] = "db.test.internal"
    env["DATABASE_URL"] = "postgres://u:p@prod-db.example.com:5432/sb?sb_plane=test"
    assert preflight(env).data_plane is DataPlane.TEST


def test_prod_plane_requires_attest_and_worker_identity():
    env = {
        "DISCORD_BOT_TOKEN_PRODUCTION": "t",
        "DATABASE_URL": "postgres://u:p@db.prod.internal:5432/sb",
        "SB_DATA_PLANE": "prod",
        "SB_INTENT_MSGCONTENT_OK": "1",
        "SB_INTENT_MEMBERS_OK": "1",
    }
    with pytest.raises(StartupError) as exc_info:
        preflight(env)
    fields = {e.env_var for e in exc_info.value.errors}
    assert {"SB_PROD_ATTEST", "RAILWAY_SERVICE_NAME"} <= fields
    env["SB_PROD_ATTEST"] = "opaque-token"
    env["RAILWAY_SERVICE_NAME"] = "worker"
    assert preflight(env).data_plane is DataPlane.PROD


# --- intent preflight (L-17) ---------------------------------------------------

def test_prod_plane_intent_denial_degrades_not_refuses():
    """S15 seam correction (frozen L0 spec 14 §2.B / PG-2 ruled DEGRADE):
    an unapproved DEGRADE-posture privileged intent no longer refuses boot —
    it yields explicit DegradedCapability markers instead (the pre-S15
    fail-closed assertion was spec 05's `required=True` behavior)."""
    from sb.kernel.config import intent_degradations
    env = {
        "DISCORD_BOT_TOKEN_PRODUCTION": "t",
        "DATABASE_URL": "postgres://u:p@db.prod.internal:5432/sb",
        "SB_DATA_PLANE": "prod",
        "SB_PROD_ATTEST": "opaque",
        "RAILWAY_SERVICE_NAME": "worker",
    }
    cfg = preflight(env)  # boots — slash-only survivability
    markers = intent_degradations(cfg)
    assert {m.intent for m in markers} == {"message_content", "members"}
    by_intent = {m.intent: m.degrades for m in markers}
    assert "prefix" in by_intent["message_content"]
    assert "member_join" in by_intent["members"]


def test_intent_mirror_invariant_is_compile_checked():
    """required must equal (posture is REQUIRED) — disagreement is a
    ConfigError, never a silent ambiguity (spec 14 §2.B precedence)."""
    import sb.kernel.config as kc
    from sb.spec.config import IntentPosture, IntentSpec
    bad = (IntentSpec("message_content", privileged=True, required=True,
                      approval_env="SB_INTENT_MSGCONTENT_OK",
                      posture=IntentPosture.DEGRADE),)
    cfg = preflight(MINIMAL_TEST_ENV)
    orig = kc.INTENT_CONTRACT
    kc.INTENT_CONTRACT = bad
    try:
        with pytest.raises(StartupError) as exc_info:
            assert_intents(cfg)
        assert any("mirror invariant" in e.reason for e in exc_info.value.errors)
    finally:
        kc.INTENT_CONTRACT = orig


def test_test_plane_intents_advisory_only():
    cfg = preflight(MINIMAL_TEST_ENV)  # approvals absent, plane=test
    assert_intents(cfg)  # must not raise
