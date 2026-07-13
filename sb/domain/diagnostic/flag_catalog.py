"""The shipped feature-flag DECLARATION registry (diagnostic flip) —
the capture world's 8 builtin flags, ported VERBATIM from the oracle
(disbot/core/runtime/feature_flags.py ``_register_builtins`` at the
corpus posture) for the 🚩 Flag Manager's detail view.

CAPTURE-WORLD LITERAL (the command_catalog precedent): the shipped
registry was populated by code-level ``FeatureFlag`` declarations —
name, label, description, default, owner, removal target, audience,
db_editable are all COMPILE-TIME constants of the oracle, so they port
as data. The v1 kernel has NO flag rollout pipeline and NO runtime
consumer of any of these flags (v1 gates ride the RC-10 Config seam,
sb/kernel/ai/flags.py class); the truthful v1 resolution of every flag
is therefore its declared default with ``source="default"`` and no
guild override — exactly the bytes the shipped read-only
``!platform flags`` card pins for the same world state
(sb/domain/diagnostic/platform_views.py: ``default=False eff=off
src=default`` per flag).

``NO_CONSUMER`` mirrors the oracle's ``_NO_CONSUMER_FLAGS`` honesty
rule ("so an operator does not waste time flipping an override that
changes nothing") — and in THIS build the rule covers every flag: no
v1 runtime code reads any of the 8, so the Flag Manager's
Enable/Disable refuse the silent no-op write with final copy instead
of persisting rows nothing consumes (the oracle's own env-only refusal
pattern, generalized to the world where the whole registry has no
consumer)."""

from __future__ import annotations

__all__ = ["FLAG_DECLARATIONS", "NO_CONSUMER", "flag_details"]

#: the oracle's ``_NO_CONSUMER_FLAGS`` set, verbatim (flags whose
#: declaration existed but which no ORACLE runtime code consulted).
NO_CONSUMER: frozenset[str] = frozenset({
    "resources.unified",
    "settings.mutation.primary",
    "resource_provisioning.primary",
})

#: name → the oracle declaration's display constants, verbatim
#: (core/runtime/feature_flags.py — label / description / default /
#: owner / removal_target / audience / db_editable).
FLAG_DECLARATIONS: dict[str, dict] = {
    "settings.manager_cog.enabled": {
        "label": "Settings menu (!settings)",
        "description": (
            "Gates the runtime behaviour of the user-facing Settings "
            "Manager cog (!settings) introduced in S5.  Default ON since "
            "PR #8 — the cog opens the Settings hub for administrators by "
            "default.  Operators can kill-switch it OFF via the "
            "SUPERBOT_FF_SETTINGS__MANAGER_COG__ENABLED=off env override "
            "or the (future) !platform flags command; when OFF the cog "
            "returns a clearly-worded 'disabled' embed instead."),
        "default": True,
        "owner": "platform",
        "removal_target": "S11 stable",
        "audience": "operator",
        "db_editable": True,
    },
    "youtube.context.enabled": {
        "label": "YouTube context for AI replies",
        "description": (
            "Enable YouTube URL metadata/transcript context for AI "
            "responses. When ON the AI pipeline fetches video metadata "
            "and transcript excerpts and includes them as grounded facts. "
            "Env override: SUPERBOT_FF_YOUTUBE_CONTEXT_ENABLED=on. "
            "Requires YOUTUBE_API_KEY to be set; if missing the flag is "
            "effectively off even when enabled here."),
        "default": False,
        "owner": "platform",
        "removal_target": "",
        "audience": "operator",
        "db_editable": True,
    },
    "bindings.primary": {
        "label": "Bindings as primary source (internal rollout gate)",
        "description": (
            "subsystem_bindings is the primary source of bound "
            "channel/role values; legacy raw-id settings KV becomes "
            "read-only fallback."),
        "default": False,
        "owner": "platform",
        "removal_target": "Phase 2b stable",
        "audience": "internal",
        "db_editable": True,
    },
    "feature_flag.primary": {
        "label": "Feature-flag runtime gate (env-only, internal)",
        "description": (
            "Feature flag runtime (Phase 2d) is authoritative for gate "
            "evaluation; env vars are back-compat fallback only."),
        "default": False,
        "owner": "platform",
        "removal_target": "Phase 2d stable",
        "audience": "internal",
        "db_editable": False,
    },
    "participation.enabled": {
        "label": "Participation runtime (internal rollout gate)",
        "description": "Per-user participation runtime (user_* tables) is live.",
        "default": False,
        "owner": "platform",
        "removal_target": "Phase 2c stable",
        "audience": "internal",
        "db_editable": True,
    },
    "resource_provisioning.primary": {
        "label": "Resource provisioning pipeline primary (operator kill-switch)",
        "description": (
            "Operator kill-switch for services.resource_provisioning."
            "ResourceProvisioningPipeline.  Provisioning proceeds by "
            "default; the pipeline refuses only when an operator "
            "explicitly sets this flag OFF (env/DB override).  Flag-eval "
            "failure fails OPEN (provisioning proceeds)."),
        "default": False,
        "owner": "platform",
        "removal_target": "S10+ stable",
        "audience": "internal",
        "db_editable": True,
    },
    "resources.unified": {
        "label": "Unified resource discovery (internal rollout gate)",
        "description": (
            "Selectors consume core/resources/ as the canonical "
            "discovery layer."),
        "default": False,
        "owner": "platform",
        "removal_target": "Phase 2a stable",
        "audience": "internal",
        "db_editable": True,
    },
    "settings.mutation.primary": {
        "label": "Settings mutation pipeline primary (operator kill-switch)",
        "description": (
            "Operator kill-switch for services.settings_mutation."
            "SettingsMutationPipeline.  Mutations proceed by default; the "
            "pipeline refuses writes only when an operator explicitly "
            "sets this flag OFF (env/DB override).  Flag-eval failure "
            "fails OPEN (writes proceed)."),
        "default": False,
        "owner": "platform",
        "removal_target": "S5+ stable",
        "audience": "internal",
        "db_editable": True,
    },
}


def flag_details(name: str) -> dict:
    """The v1 twin of the oracle's ``_resolve_flag_details`` — the
    declaration constants plus the truthful v1 resolution (declared
    default, ``source="default"``, no guild override; module
    docstring). An unknown name answers the oracle's own unregistered
    shape ("Flag is no longer declared.")."""
    decl = FLAG_DECLARATIONS.get(name)
    if decl is None:
        # the oracle's unregistered branch, verbatim copy.
        return {
            "name": name,
            "label": "",
            "description": "Flag is no longer declared.",
            "default": "?",
            "effective": "?",
            "source": "unregistered",
            "owner": "?",
            "removal_target": "",
            "audience": "internal",
            "db_editable": False,
            "has_guild_override": False,
            "no_consumer": True,
        }
    on_off = "on" if decl["default"] else "off"
    return {
        "name": name,
        "label": decl["label"],
        "description": decl["description"],
        "default": on_off,
        "effective": on_off,          # v1 truth: no override store exists
        "source": "default",          # matches the shipped flags-card bytes
        "owner": decl["owner"],
        "removal_target": decl["removal_target"],
        "audience": decl["audience"],
        "db_editable": decl["db_editable"],
        "has_guild_override": False,  # v1 truth: no feature_flag_state table
        "no_consumer": True,          # v1 truth: no consumer for ANY flag here
    }
