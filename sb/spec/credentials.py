"""Credential-lifecycle grammar leaf + the ONE flat credential registry (S13).

Built to frozen L0 spec 12 (credential lifecycle + supply-chain posture) §2.A.
A SIBLING leaf of `SecretSpec` — it does NOT redefine or grow the spec-05
config/secret grammar (the ⑪ `InvariantSpec` discipline). The two are keyed by
`config_ref` (the env-var name); the invariant is
`store == WORKER_ENV  ⟺  config_ref is not None`.

Every credential the project concentrates (Q-0213) is EXACTLY ONE row here —
where it physically lives, how it rotates (posture + horizon), and how it is
killed (a CLOSED `RevocationRef` vocabulary member, never a free string).
`tools/check_credential_lifecycle.py` enforces machine-completeness both
directions against the credential-bearing subset of `CONFIG_FIELDS`.

Registry provenance (source wins, Q-0120): the spec's §2.A table was grounded
against old-repo `disbot/config.py`; THIS registry is grounded against the
harvested `CONFIG_FIELDS` at S13 — four additional worker secrets the spec
table predates (DISCORD_WEBHOOK_URL, PARAGON_API_KEY, YOUTUBE_API_KEY,
CLAUDE_ROUTINE_TOKEN) get rows (and three additive `RevocationRef` members
name their real kill mechanisms — rule 1 demands a real kill-path per row).
`CONTROL_API_TOKEN` has NO row yet: its SecretSpec does not exist in this
repo (control-api ports at band 5); a registry row with a dangling
`config_ref` would violate rule 3. Its row lands with its config field.

Stdlib-only leaf apart from sb.spec.roles.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sb.spec.roles import register_field_roles

__all__ = [
    "CREDENTIAL_REGISTRY",
    "BlastTier",
    "CredentialSpec",
    "CredentialStore",
    "RevocationRef",
    "RotationPosture",
    "credential_for",
]


class RotationPosture(str, enum.Enum):
    """spec 12 §2.A verbatim."""

    MANAGED = "managed"            # platform rotates it; the arm re-reads
    AUTONOMOUS = "autonomous"      # a routine re-issues + swaps on a cadence, NO owner touch
    OWNER_PROMPT = "owner_prompt"  # cadence exists; the swap needs one irreducible owner step
    ON_COMPROMISE = "on_compromise"  # no cadence; rotated only on a compromise signal


class RevocationRef(str, enum.Enum):
    """CLOSED kill-path vocabulary — one token per kill mechanism (spec 12
    §2.A; token → concrete API dispatch is CUT-1 ops wiring, membership is
    CI-validated NOW). The last three are additive members minted at S13 for
    the harvested worker secrets the spec table predates (ledgered D-0016)."""

    RAILWAY_API_TOKEN_DELETE = "railway.apiTokenDelete"
    RAILWAY_VAR_ROTATE = "railway.var_rotate"
    RAILWAY_DB_CRED_ROTATE = "railway.db_credential_rotate"
    GITHUB_TOKEN_SETTINGS = "github.token_settings"
    GITHUB_SECRET_UPDATE = "github.secret_update"
    DISCORD_RESET_TOKEN = "discord.reset_token"
    ANTHROPIC_CONSOLE = "anthropic.console"
    OPENAI_DASHBOARD = "openai.dashboard"
    # -- additive (S13 harvest; source wins Q-0120) --
    DISCORD_WEBHOOK_DELETE = "discord.webhook_delete"    # delete/recreate the channel webhook
    GOOGLE_CLOUD_CONSOLE = "google.cloud_console"        # revoke/reissue a Google API key
    PARAGON_DASHBOARD = "paragon.dashboard"              # revoke/reissue the paragon-calc key


class BlastTier(int, enum.Enum):
    """TOTAL ORDER — higher int = higher blast = earlier in the recovery
    runbook (`sorted(compromised, key=lambda c: c.blast, reverse=True)`)."""

    TEST_ONLY = 0      # test bot / non-prod — no real-world harm
    SPEND = 1          # provider spend-drain, capped by billing limits
    BOT_PRESENCE = 2   # prod-bot user-visible outage / nuisance, no data loss
    CONTROL = 3        # dashboard / control-plane write access
    PROD_DATA = 4      # read/write against prod data
    ACCOUNT = 5        # full platform account — provisioning root, reads all secrets


class CredentialStore(str, enum.Enum):
    """Where the credential PHYSICALLY lives — the disjoint-partition
    discriminator (`WORKER_ENV ⟺ config_ref is not None`)."""

    WORKER_ENV = "worker_env"                    # prod worker env — IS a CONFIG_FIELDS credential
    AGENT_CONTAINER_ENV = "agent_container_env"  # agent/dev container env — NOT worker config
    GITHUB_ACTIONS_SECRET = "github_actions_secret"
    RAILWAY_ACCOUNT = "railway_account"          # a Railway account-level API token
    GITHUB_APP = "github_app"                    # the GitHub repo-write token
    DISCORD_PORTAL = "discord_portal"            # minted in the Discord developer portal


@dataclass(frozen=True)
class CredentialSpec:
    """One credential — a SIBLING of SecretSpec, NOT a field on it (spec 12
    §2.A). `config_ref` names the CONFIG_FIELDS env_var the WORKER reads it
    from; None ⟺ the credential never enters the worker's env."""

    name: str                          # [S] the credential identity (registry key)
    store: CredentialStore             # [S] where it physically lives
    config_ref: str | None             # [S] SecretSpec/DSN env_var; None if out-of-band
    rotation: RotationPosture          # [S]
    cadence_days: int | None           # [S] non-None ⟺ rotation ∈ {AUTONOMOUS, OWNER_PROMPT}
    revocation_ref: RevocationRef      # [S] the CLOSED kill-path token
    blast: BlastTier                   # [S] total-ordered severity (runbook triage order)


register_field_roles(
    "CredentialSpec",
    name="S", store="S", config_ref="S", rotation="S", cadence_days="S",
    revocation_ref="S", blast="S",
)


# ---------------------------------------------------------------------------
# The ONE flat, disjoint credential inventory (spec 12 §2.A table + the S13
# source-wins harvest). cadence defaults: leaf 90 / root 180 (ops-tunable
# constants, not a fork).
# ---------------------------------------------------------------------------

CREDENTIAL_REGISTRY: tuple[CredentialSpec, ...] = (
    # -- roots (OWNER_PROMPT: the swap has one irreducible platform step) --
    CredentialSpec("railway_account_token", CredentialStore.RAILWAY_ACCOUNT, None,
                   RotationPosture.OWNER_PROMPT, 180,
                   RevocationRef.RAILWAY_API_TOKEN_DELETE, BlastTier.ACCOUNT),
    CredentialSpec("github_repo_write_token", CredentialStore.GITHUB_APP, None,
                   RotationPosture.OWNER_PROMPT, 180,
                   RevocationRef.GITHUB_TOKEN_SETTINGS, BlastTier.CONTROL),
    # -- worker-env leaves (config_ref names the CONFIG_FIELDS entry) --
    CredentialSpec("discord_prod_bot_token", CredentialStore.WORKER_ENV,
                   "DISCORD_BOT_TOKEN_PRODUCTION",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.DISCORD_RESET_TOKEN, BlastTier.BOT_PRESENCE),
    CredentialSpec("prod_dsn", CredentialStore.WORKER_ENV, "DATABASE_URL",
                   RotationPosture.MANAGED, None,
                   RevocationRef.RAILWAY_DB_CRED_ROTATE, BlastTier.PROD_DATA),
    CredentialSpec("anthropic_api_key", CredentialStore.WORKER_ENV, "ANTHROPIC_API_KEY",
                   RotationPosture.AUTONOMOUS, 90,
                   RevocationRef.ANTHROPIC_CONSOLE, BlastTier.SPEND),
    CredentialSpec("openai_api_key", CredentialStore.WORKER_ENV, "OPENAI_API_KEY",
                   RotationPosture.AUTONOMOUS, 90,
                   RevocationRef.OPENAI_DASHBOARD, BlastTier.SPEND),
    CredentialSpec("prod_attest_token", CredentialStore.WORKER_ENV, "SB_PROD_ATTEST",
                   RotationPosture.AUTONOMOUS, 90,
                   RevocationRef.RAILWAY_VAR_ROTATE, BlastTier.PROD_DATA),
    # -- S13 harvest rows (worker secrets the spec's §2.A table predates) --
    CredentialSpec("discord_ops_webhook_url", CredentialStore.WORKER_ENV,
                   "DISCORD_WEBHOOK_URL",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.DISCORD_WEBHOOK_DELETE, BlastTier.BOT_PRESENCE),
    CredentialSpec("paragon_api_key", CredentialStore.WORKER_ENV, "PARAGON_API_KEY",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.PARAGON_DASHBOARD, BlastTier.SPEND),
    CredentialSpec("youtube_api_key", CredentialStore.WORKER_ENV, "YOUTUBE_API_KEY",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.GOOGLE_CLOUD_CONSOLE, BlastTier.SPEND),
    CredentialSpec("claude_routine_token", CredentialStore.WORKER_ENV,
                   "CLAUDE_ROUTINE_TOKEN",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.ANTHROPIC_CONSOLE, BlastTier.CONTROL),
    # -- band-5 row (the S13-deferred CONTROL_API_TOKEN — its SecretSpec
    #    landed with the control-api band; ON_COMPROMISE like the sibling
    #    worker tokens — a cadence swap must be coordinated with the
    #    dashboard side, so no autonomous rotation) --
    CredentialSpec("control_api_token", CredentialStore.WORKER_ENV,
                   "CONTROL_API_TOKEN",
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.RAILWAY_VAR_ROTATE, BlastTier.CONTROL),
    # -- out-of-band leaves --
    CredentialSpec("database_public_url", CredentialStore.GITHUB_ACTIONS_SECRET, None,
                   RotationPosture.AUTONOMOUS, 90,
                   RevocationRef.GITHUB_SECRET_UPDATE, BlastTier.PROD_DATA),
    CredentialSpec("discord_test_bot_token", CredentialStore.AGENT_CONTAINER_ENV, None,
                   RotationPosture.ON_COMPROMISE, None,
                   RevocationRef.DISCORD_RESET_TOKEN, BlastTier.TEST_ONLY),
)


def credential_for(name: str) -> CredentialSpec:
    """Return the registry row for `name`; KeyError if absent."""
    for spec in CREDENTIAL_REGISTRY:
        if spec.name == name:
            return spec
    raise KeyError(name)
