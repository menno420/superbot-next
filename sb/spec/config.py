"""Config / secret grammar + the canonical config registry (K0).

Built to frozen L0 spec 05 (ops-kernel rails) §3.1 — `ConfigSpec`/`SecretSpec`/
`ConfigPosture`/`ConfigType` (incl. `CSV`), `IntentSpec`, `DataPlane`, and the
ONE place every env var is declared: `CONFIG_FIELDS`.

All fields are [S] (config declarations are semantic — hand-authored meaning).

Harvest provenance: the "harvested" entries below are every distinct env var
read by shipped superbot source (verified against `disbot/` at superbot main
7f7628e1, 2026-07-08 — 36 distinct names at S1 + HEALTH_PORT/HEALTH_HOST
added at S6 when the health adapter ported = 38; the spec's "39" counted
getenv CALL SITES at spec time, source wins per Q-0120). The 8 NEW
operational fields are declared by spec 05 §3.1 verbatim. A-21
(`EXTRA_OWNER_USER_IDS`) is in the harvested set and lands at K0 per the
canonical plan.

This module is a stdlib-only leaf: no imports outside the stdlib, no env
reads (reading/coercing env is `sb.kernel.config.preflight`'s job).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConfigPosture(str, Enum):
    """What happens when a required value is absent/invalid (spec 05 §3.1)."""

    FAIL_FAST = "fail_fast"  # refuse boot -> FAILED_STARTUP (token, DSN, data-plane)
    DEGRADE = "degrade"      # feature runs reduced (paragon->local estimate; youtube->key_missing)
    DORMANT = "dormant"      # feature entirely inert, no error (control-api, AI keys)


class ConfigType(str, Enum):
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    SECRET = "secret"
    DSN = "dsn"
    CSV = "csv"  # comma-split -> tuple[str, ...]; empty/absent => () (host allowlists)


class DataPlane(str, Enum):
    TEST = "test"
    PROD = "prod"


@dataclass(frozen=True)
class ConfigSpec:
    """One declared env var. `env_var` is verbatim AND the Config attribute name."""

    env_var: str                                   # [S] exact env name, verbatim
    type: ConfigType                               # [S]
    required: bool = False                         # [S] True => no default; absence triggers `posture`
    default: object | None = None                  # [S] present iff required=False; type-consistent
    posture: ConfigPosture = ConfigPosture.FAIL_FAST  # [S] consulted when required & absent/invalid
    owner_subsystem: str | None = None             # [S] provenance for generated docs
    activation_link: str | None = None             # [S] SettingSpec.activation this key drives
    choices: tuple[str, ...] = ()                  # [S] closed set
    min: float | None = None                       # [S] numeric floor (timeouts, intervals)
    redact: bool = False                           # [S] never in logs/diagnostics (True for SECRET/DSN)

    def __post_init__(self) -> None:
        if self.type in (ConfigType.SECRET, ConfigType.DSN) and not self.redact:
            # Redaction is a field property of every credential-bearing type.
            object.__setattr__(self, "redact", True)


@dataclass(frozen=True)
class SecretSpec(ConfigSpec):
    """ConfigSpec with type=SECRET, redact=True enforced.

    A secret is NEVER logged, NEVER surfaced in /lifecycle or diagnostics; only
    its presence/absence ("configured": bool) is observable
    (`Config.is_configured`, spec 05 §3.2).
    """

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", ConfigType.SECRET)
        object.__setattr__(self, "redact", True)


class IntentPosture(str, Enum):
    """S15 (frozen L0 spec 14 §2.B) — mirrors ConfigPosture. The
    AUTHORITATIVE action-on-denial signal; F-3/PG-2 adjudicated DEGRADE
    (canonical-plan F-2 ruling + Q-0246/A-22 product tier)."""

    REQUIRED = "required"  # denial ⇒ FAILED_STARTUP (reserved; none today)
    DEGRADE = "degrade"    # denial ⇒ boot with this intent's capability class disabled + notice


@dataclass(frozen=True)
class IntentSpec:
    """Gateway-intent contract (T2-22 / L-17; S15 spec-14 §2.B seam
    correction: `posture` is authoritative, the frozen `required` bool is a
    shape-compat MIRROR — `required == (posture is REQUIRED)` is enforced by
    `assert_intents` as a config-compile invariant, never a silent
    ambiguity)."""

    name: str                      # [S] "message_content" | "members" | "presences" | ...
    privileged: bool               # [S] True for message_content/members/presences
    required: bool                 # [S] MIRROR of posture (kept for the 05 §3.1 shape)
    approval_env: str | None = None  # [S] the BOOL ConfigSpec env asserting Discord approval
    #     (parsed via parse_bool — a "truthy" grammar, not presence)
    posture: IntentPosture = IntentPosture.DEGRADE  # [S] the action-on-denial signal
    degrades: tuple[str, ...] = ()   # [S] capability classes disabled on denial


# ---------------------------------------------------------------------------
# The canonical registry — the ONE place every env var is declared.
# 38 harvested (verbatim env names) + 9 new operational fields = 47 total
# (8 spec-05 fields + S14's SB_VERIFY_BOOT, spec 13 §8-5 additive growth).
# ---------------------------------------------------------------------------

_FF = ConfigPosture.FAIL_FAST
_DEG = ConfigPosture.DEGRADE
_DOR = ConfigPosture.DORMANT

CONFIG_FIELDS: tuple[ConfigSpec, ...] = (
    # ---- harvested (38) — verbatim env names from shipped disbot/ source ----
    SecretSpec("DISCORD_BOT_TOKEN_PRODUCTION", ConfigType.SECRET, required=True, posture=_FF),
    ConfigSpec("DATABASE_URL", ConfigType.DSN, required=True, posture=_FF, redact=True),
    ConfigSpec("BOT_PREFIX", ConfigType.STR, default="!"),
    ConfigSpec("BOT_OWNER_USER_ID", ConfigType.INT, default=340415158583296000,
               owner_subsystem="ops"),
    ConfigSpec("EXTRA_OWNER_USER_IDS", ConfigType.CSV, default=(),
               owner_subsystem="ops"),  # A-21 declared elevated test actors (Q-0245)
    SecretSpec("DISCORD_WEBHOOK_URL", ConfigType.SECRET, default=None, posture=_DOR,
               owner_subsystem="ops"),  # webhook URL embeds a token -> secret-typed
    ConfigSpec("LOG_LEVEL", ConfigType.STR, default="INFO", owner_subsystem="ops"),
    # Harvested from shipped disbot/healthserver.py:64,70 (missed by the S1
    # sweep — source wins, Q-0120; declared at S6 when the K5 health adapter
    # ported and check_config_usage banned its raw environment reads).
    ConfigSpec("HEALTH_PORT", ConfigType.INT, default=8080, min=1,
               owner_subsystem="ops"),
    ConfigSpec("HEALTH_HOST", ConfigType.STR, default="::",
               owner_subsystem="ops"),  # IPv6 dual-stack; set 0.0.0.0 if no IPv6
    ConfigSpec("AUTO_SYNC_COMMANDS", ConfigType.BOOL, default=True, owner_subsystem="ops"),
    ConfigSpec("STRICT_DISABLED", ConfigType.BOOL, default=False, owner_subsystem="ops"),
    ConfigSpec("IDENTITY_CONTRACT_STRICT", ConfigType.BOOL, default=True, owner_subsystem="ops"),
    ConfigSpec("HEALTH_GROUPED_FINDINGS", ConfigType.BOOL, default=False, owner_subsystem="ops"),
    ConfigSpec("AUTOMATION_SCHEDULER_ENABLED", ConfigType.BOOL, default=False,
               posture=_DOR, owner_subsystem="automation"),
    # AI family (DORMANT: absent keys leave the feature inert)
    ConfigSpec("AI_ENABLED", ConfigType.BOOL, default=False, posture=_DOR,
               owner_subsystem="ai", activation_link="ai.*"),
    ConfigSpec("AI_DEFAULT_PROVIDER", ConfigType.STR, default="deterministic",
               owner_subsystem="ai"),
    ConfigSpec("AI_FALLBACK_PROVIDER", ConfigType.STR, default="", owner_subsystem="ai"),
    # Harvested from shipped disbot/core/runtime/ai/feature_flags.py (missed
    # by the S1 sweep — source wins, Q-0120; declared at K10 when the flags
    # module re-homed onto the Config seam).
    ConfigSpec("AI_TOOLS_ENABLED", ConfigType.BOOL, default=False, posture=_DOR,
               owner_subsystem="ai"),
    ConfigSpec("AI_SERVER_MEMBER_LOOKUP_ENABLED", ConfigType.BOOL, default=False,
               posture=_DOR, owner_subsystem="ai"),
    # K10 CSV folds of the shipped dynamic env-name patterns (RC-10: one
    # frozen typed attribute per env var — D-0022):
    # AI_TASK_<NAME>_ENABLED kill switches -> AI_TASKS_DISABLED (task ids);
    # AI_ROUTING_<TASK> -> AI_TASK_ROUTING ("task=provider:model" entries).
    ConfigSpec("AI_TASKS_DISABLED", ConfigType.CSV, default=(), owner_subsystem="ai"),
    ConfigSpec("AI_TASK_ROUTING", ConfigType.CSV, default=(), owner_subsystem="ai"),
    SecretSpec("ANTHROPIC_API_KEY", ConfigType.SECRET, default=None, posture=_DOR,
               owner_subsystem="ai", activation_link="ai.on_when_keyed"),
    SecretSpec("OPENAI_API_KEY", ConfigType.SECRET, default=None, posture=_DOR,
               owner_subsystem="ai", activation_link="ai.on_when_keyed"),
    ConfigSpec("SETUP_ADVISOR_PROVIDER", ConfigType.STR, default="deterministic",
               choices=("deterministic", "openai", "anthropic"), owner_subsystem="ai"),
    ConfigSpec("SETUP_ADVISOR_OPENAI_MODEL", ConfigType.STR, default="gpt-4o-mini",
               owner_subsystem="ai"),
    # BTD6 / paragon / media family
    SecretSpec("PARAGON_API_KEY", ConfigType.SECRET, default=None, posture=_DEG,
               owner_subsystem="btd6"),  # degrade: paragon -> local estimate
    ConfigSpec("PARAGON_API_BASE_URL", ConfigType.STR,
               default="https://paragon-calc.vercel.app", owner_subsystem="btd6"),
    ConfigSpec("BTD6_DATA_BACKEND", ConfigType.STR, default="", owner_subsystem="btd6"),
    ConfigSpec("BTD6_DATA_BASE_URL", ConfigType.STR, default="", owner_subsystem="btd6"),
    ConfigSpec("BTD6_DATA_CACHE_DIR", ConfigType.STR, default="", owner_subsystem="btd6"),
    ConfigSpec("BTD6_AUTO_SEED", ConfigType.BOOL, default=True, owner_subsystem="btd6"),
    ConfigSpec("BTD6_PASSIVE_CHANNELS", ConfigType.CSV, default=(), owner_subsystem="btd6"),
    ConfigSpec("BTD6_CONFIDENCE_THRESHOLD", ConfigType.FLOAT, default=None,
               owner_subsystem="btd6"),
    ConfigSpec("BTD6_COOLDOWN_SECONDS", ConfigType.FLOAT, default=None, min=0.0,
               owner_subsystem="btd6"),
    ConfigSpec("BTD6_INGESTION_ENABLED", ConfigType.BOOL, default=False, posture=_DOR,
               owner_subsystem="btd6"),
    ConfigSpec("BTD6_INGESTION_STARTUP_DELAY_S", ConfigType.INT, default=60, min=0,
               owner_subsystem="btd6"),
    ConfigSpec("BTD6_INGESTION_DEFAULT_INTERVAL_S", ConfigType.INT, default=3600, min=1,
               owner_subsystem="btd6"),
    SecretSpec("YOUTUBE_API_KEY", ConfigType.SECRET, default=None, posture=_DEG,
               owner_subsystem="media"),  # degrade: youtube -> key_missing outcome
    # Hermes / Claude routine family (DORMANT: control-api inert unless keyed)
    ConfigSpec("CLAUDE_ROUTINE_FIRE_URL", ConfigType.STR, default="", posture=_DOR,
               owner_subsystem="hermes"),
    SecretSpec("CLAUDE_ROUTINE_TOKEN", ConfigType.SECRET, default=None, posture=_DOR,
               owner_subsystem="hermes"),
    ConfigSpec("CLAUDE_ROUTINE_BETA", ConfigType.STR,
               default="experimental-cc-routine-2026-04-01", owner_subsystem="hermes"),
    ConfigSpec("CLAUDE_ROUTINE_VERSION", ConfigType.STR, default="2023-06-01",
               owner_subsystem="hermes"),

    # ---- NEW operational fields (8) declared by spec 05 §3.1 ----
    ConfigSpec("SB_DATA_PLANE", ConfigType.STR, required=True, posture=_FF,
               choices=("test", "prod"), owner_subsystem="ops"),  # the 4th rail's declaration
    ConfigSpec("DB_COMMAND_TIMEOUT_S", ConfigType.FLOAT, default=30.0, min=1.0,
               owner_subsystem="ops"),  # §3.4 — bounds a wedged query
    ConfigSpec("DB_IDLE_LIFETIME_S", ConfigType.FLOAT, default=300.0, min=0.0,
               owner_subsystem="ops"),  # §3.4 — max_inactive_connection_lifetime
    ConfigSpec("SB_TEST_DB_HOSTS", ConfigType.CSV, default=(),
               owner_subsystem="ops"),  # §3.5 — test-plane DSN host allowlist
    SecretSpec("SB_PROD_ATTEST", ConfigType.SECRET, default=None,
               owner_subsystem="ops"),  # §3.5 — opaque human-set prod token; PRESENCE => attested
    ConfigSpec("RAILWAY_SERVICE_NAME", ConfigType.STR, default=None,
               owner_subsystem="ops"),  # §3.5 — Railway-injected service name ('worker' in prod)
    ConfigSpec("SB_INTENT_MSGCONTENT_OK", ConfigType.BOOL, default=False,
               owner_subsystem="ops"),  # §3.2 — approval_env for message_content
    ConfigSpec("SB_INTENT_MEMBERS_OK", ConfigType.BOOL, default=False,
               owner_subsystem="ops"),  # §3.2 — approval_env for members

    # ---- S14 additive operational field (spec 13 §2.2 / §8-5; the
    #      registry COUNT grows, the grammar shape is unchanged) ----
    ConfigSpec("SB_VERIFY_BOOT", ConfigType.BOOL, default=False,
               owner_subsystem="ops"),  # side-effect-free verify-boot profile: no
    #     gateway/token, PollSupervisor + outbox relay NOT started; preflight
    #     REQUIRES SB_DATA_PLANE=test when True (restore-verify.yml, T-7 fix)

    # ---- band-5 additive field (control_api.py harvest — Q-0156/Q-0159:
    #      the private /control/* dashboard bridge is DORMANT unless this
    #      shared-secret token is deliberately configured) ----
    SecretSpec("CONTROL_API_TOKEN", ConfigType.SECRET, default=None,
               posture=_DOR, owner_subsystem="platform"),
)


INTENT_CONTRACT: tuple[IntentSpec, ...] = (
    # S15 seam correction (spec 14 §2.B / PG-2 ruled DEGRADE): required
    # True→False — refuse-to-boot on a routine message_content denial darked
    # the WHOLE bot when every slash command still serves; the fail-closed
    # rule's real goal (no SILENT reliance) is met by the EXPLICIT degrade.
    IntentSpec("message_content", privileged=True, required=False,
               approval_env="SB_INTENT_MSGCONTENT_OK",
               posture=IntentPosture.DEGRADE,
               degrades=("prefix", "fuzzy", "triggers", "nl_message",
                         "passive_onmessage")),
    IntentSpec("members", privileged=True, required=False,
               approval_env="SB_INTENT_MEMBERS_OK",
               posture=IntentPosture.DEGRADE,
               degrades=("member_join", "member_leave", "member_cache")),
)  # the two hardcoded privileged intents in shipped source (bot1.py:77-78)


def spec_for(env_var: str) -> ConfigSpec:
    """Return the declared ConfigSpec for `env_var`; KeyError if undeclared."""
    for spec in CONFIG_FIELDS:
        if spec.env_var == env_var:
            return spec
    raise KeyError(env_var)
