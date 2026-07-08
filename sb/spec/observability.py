"""Metric grammar + the canonical metric registry (K0).

Built to frozen L0 spec 05 §3.3 — `MetricSpec`, `MetricKind`, `LabelSpec`
(each label carries its declared value domain OR a max-cardinality bound, so
`tools/check_metric_cardinality.py` can bound series count), and `METRICS`:
every metric family declared, names/labels/buckets verbatim from shipped
`disbot/services/metrics.py` (superbot main 7f7628e1 — 46 families).

Stdlib-only leaf. Instantiation lives in `sb.kernel.observability.metrics`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class LabelSpec:
    """A metric label AND its declared value domain.

    Exactly one of (`domain` non-empty, `max_cardinality` > 0) must be set —
    an unbounded label with neither is forbidden (the cardinality-explosion
    class). Enforced at construction (compile-time COMPILE_ERROR analogue).
    """

    name: str                        # [S] label key, verbatim
    domain: tuple[str, ...] = ()     # [S] CLOSED allowed-value set when finite
    max_cardinality: int = 0         # [S] declared upper bound for an OPEN-but-bounded label

    def __post_init__(self) -> None:
        has_domain = bool(self.domain)
        has_bound = self.max_cardinality > 0
        if has_domain == has_bound:  # both or neither
            raise ValueError(
                f"LabelSpec {self.name!r}: exactly one of (domain, max_cardinality) "
                "must be set (an unbounded label is forbidden)"
            )

    @property
    def cardinality(self) -> int:
        return len(self.domain) if self.domain else self.max_cardinality


@dataclass(frozen=True)
class MetricSpec:
    name: str                            # [S] exposition name, verbatim
    kind: MetricKind                     # [S]
    doc: str                             # [S]
    labels: tuple[LabelSpec, ...] = ()   # [S]
    buckets: tuple[float, ...] = ()      # [S] histogram only; empty => COMPILE_ERROR for HISTOGRAM
    cardinality_budget: int = 0          # [O] max expected series; 0 => CI-red unless zero labels
    owner_subsystem: str | None = None   # [S]

    def __post_init__(self) -> None:
        if self.kind is MetricKind.HISTOGRAM and not self.buckets:
            raise ValueError(f"MetricSpec {self.name!r}: HISTOGRAM requires non-empty buckets")


def _lbl(name: str, *domain: str, bound: int = 0) -> LabelSpec:
    return LabelSpec(name, domain=tuple(domain), max_cardinality=bound)


def _budget(labels: tuple[LabelSpec, ...]) -> int:
    n = 1
    for label in labels:
        n *= label.cardinality
    return n


def _metric(name: str, kind: MetricKind, doc: str, labels: tuple[LabelSpec, ...] = (),
            buckets: tuple[float, ...] = (), owner: str | None = None) -> MetricSpec:
    return MetricSpec(
        name=name, kind=kind, doc=doc, labels=labels, buckets=buckets,
        cardinality_budget=_budget(labels) if labels else 0, owner_subsystem=owner,
    )


_C = MetricKind.COUNTER
_G = MetricKind.GAUGE
_H = MetricKind.HISTOGRAM

# Shared bounded-label shorthand (the shipped `_TABLE_RE`/comment bounds made declared).
_GUILD = _lbl("guild_id", bound=1000)
_SUBSYSTEM = _lbl("subsystem", bound=64)
_COG = _lbl("cog", bound=64)
_COMMAND = _lbl("command", bound=300)
_PREFIX = _lbl("prefix", bound=64)
_EVENT = _lbl("event", bound=128)

METRICS: tuple[MetricSpec, ...] = (
    _metric("governance_cache_hits_total", _C,
            "Governance resolution results served from cache", (_GUILD,), owner="governance"),
    _metric("governance_cache_misses_total", _C,
            "Governance resolution results computed (cache miss)", (_GUILD,), owner="governance"),
    _metric("governance_resolution_seconds", _H,
            "Duration of governance resolution operations", (_lbl("operation", bound=20),),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0), owner="governance"),
    _metric("command_total", _C, "Total bot commands processed",
            (_COG, _COMMAND, _lbl("result", "success", "error", "denied")), owner="ops"),
    _metric("session_active_count", _G,
            "Current number of non-expired runtime sessions in the DB", owner="ops"),
    _metric("panel_refresh_total", _C,
            "Total panel edits triggered by the live update scheduler.",
            (_SUBSYSTEM, _lbl("result", "ok", "skipped", "channel_missing",
                              "message_not_found", "forbidden", "http_error",
                              "refresh_fn_error")), owner="panels"),
    _metric("governance_denials_total", _C,
            "Total governance execution denials by subsystem and scope",
            (_SUBSYSTEM, _lbl("scope", bound=16)), owner="governance"),
    _metric("command_access_decisions_total", _C,
            "Command-access resolver decisions broken down by invocation, "
            "decision, reason, mode, and source.",
            (_lbl("invocation", "prefix", "slash"), _lbl("decision", "allow", "deny"),
             _lbl("reason", bound=6), _lbl("mode", bound=4), _lbl("source", bound=4)),
            owner="ops"),
    _metric("task_outcome_total", _C,
            "Outcomes of managed background tasks spawned via core.runtime.tasks",
            (_lbl("name", bound=64), _lbl("outcome", "ok", "error", "cancelled")), owner="ops"),
    _metric("health_finding_recorded_total", _C,
            "Operational-health findings upserted into the persistent store.",
            (_lbl("category", bound=16), _lbl("severity", bound=8)), owner="health"),
    _metric("health_finding_retention_pruned_total", _C,
            "Resolved/ignored health-finding rows pruned by the retention sweep.",
            owner="health"),
    _metric("health_snapshot_collection_seconds", _H,
            "Wall-clock time to collect a health snapshot, by collection lane.",
            (_lbl("lane", "sync", "async"),),
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0), owner="health"),
    _metric("health_snapshot_source_failure_total", _C,
            "Health-adapter sources that errored or timed out during collection "
            "(per-source isolation kept the rest of the snapshot intact).",
            (_lbl("source", bound=32),), owner="health"),
    _metric("health_snapshot_redaction_total", _C,
            "Health snapshots projected for a viewer audience (redaction outcomes).",
            (_lbl("audience", "public", "guild_admin", "platform_owner"),), owner="health"),
    _metric("runtime_lock_boot_handoff_total", _C,
            "Outcome of the boot-time runtime-lock acquisition loop.",
            (_lbl("outcome", "acquired_immediate", "acquired_after_wait", "timeout"),),
            owner="ops"),
    _metric("runtime_lock_boot_wait_seconds", _H,
            "Time spent waiting for the runtime lock during boot (acquired or timed out).",
            buckets=(0.1, 0.5, 1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0), owner="ops"),
    _metric("runtime_lock_heartbeat_total", _C,
            "Runtime-lock heartbeat refresh attempts by outcome.",
            (_lbl("outcome", "ok", "error", "lost", "released"),), owner="ops"),
    _metric("lifecycle_phase", _G,
            "Current lifecycle phase as a multi-series gauge (1=current, 0=other).",
            (_lbl("phase", "STARTING", "RUNNING", "DRAINING", "SHUTTING_DOWN",
                  "RESTARTING", "STOPPED", "FAILED_STARTUP"),), owner="lifecycle"),
    _metric("lifecycle_close_driver_total", _C,
            "Lifecycle close-driver invocations by pending request kind.",
            (_lbl("kind", "shutdown", "restart"),), owner="lifecycle"),
    _metric("lifecycle_close_duration_seconds", _H,
            "Duration of bot.close() invoked by the lifecycle close-driver.",
            (_lbl("kind", "shutdown", "restart"),),
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0), owner="lifecycle"),
    _metric("lifecycle_startup_seconds", _H,
            "Time from process import to first STARTING -> RUNNING transition.",
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0), owner="lifecycle"),
    _metric("runtime_lock_heartbeat_seconds", _H,
            "Duration of the runtime-lock heartbeat UPDATE call (success or error).",
            buckets=(0.005, 0.025, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0), owner="ops"),
    _metric("governance_fail_open_total", _C,
            "Interaction-router governance gate fell open due to resolver error.",
            (_SUBSYSTEM,), owner="governance"),
    _metric("interaction_unhandled_total", _C,
            "Interactions routed to a custom_id prefix with no registered handler.",
            (_PREFIX,), owner="interaction"),
    _metric("anchor_restore_total", _C,
            "Outcomes of PersistentView restoration during on_ready.",
            (_SUBSYSTEM, _lbl("result", "ok", "view_missing", "restore_failed")),
            owner="interaction"),
    _metric("unknown_event_total", _C,
            "EventBus emit/on calls referencing an event name not in the catalogue.",
            (_EVENT, _lbl("op", "emit", "on")), owner="events"),
    _metric("event_handler_failures_total", _C,
            "EventBus subscriber failures (RS05): error or timeout per event.",
            (_EVENT, _lbl("kind", "error", "timeout")), owner="events"),
    _metric("identity_contract_findings_total", _C,
            "Cumulative identity-contract findings detected during validation runs.",
            (_lbl("kind", "entry_point_missing_command", "router_prefix_unknown",
                  "view_subsystem_unknown", "db_anchor_subsystem_unknown"),), owner="ops"),
    _metric("webhook_dispatch_total", _C,
            "WebhookReporter dispatch outcomes (success or caught exception).",
            (_lbl("outcome", "success", "error"),), owner="ops"),
    _metric("lifecycle_event_total", _C,
            "Lifecycle events recorded in the ring buffer, by event name.",
            (_lbl("event", bound=16),), owner="lifecycle"),
    _metric("webhook_dispatch_seconds", _H,
            "Duration of WebhookReporter._send dispatches (success or caught exception).",
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0), owner="ops"),
    _metric("guild_config_cache_hits_total", _C,
            "Guild-config cache hits, labelled by the typed-accessor key.",
            (_lbl("key", bound=64),), owner="config-cache"),
    _metric("guild_config_cache_misses_total", _C,
            "Guild-config cache misses (loader invoked), labelled by key.",
            (_lbl("key", bound=64),), owner="config-cache"),
    _metric("guild_config_cache_invalidations_total", _C,
            "Explicit guild-config invalidations from admin write paths or "
            "guild_lifecycle teardown.",
            (_lbl("scope", "guild", "key"),), owner="config-cache"),
    _metric("guild_config_cache_size", _G,
            "Current number of entries in the guild-config cache.", owner="config-cache"),
    _metric("scope_locks_total", _G,
            "Current number of tracked scope locks across all subsystem prefixes.",
            owner="ops"),
    _metric("scope_locks_wait_seconds", _H,
            "Time spent waiting to acquire a scope lock, labelled by subsystem prefix.",
            (_PREFIX,),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            owner="ops"),
    _metric("scope_locks_idle_swept_total", _C,
            "Scope locks reclaimed by session_gc's idle sweep.", owner="ops"),
    _metric("command_latency_seconds", _H,
            "End-to-end command handler time (on_command -> on_command_completion).",
            (_COG, _COMMAND),
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0), owner="ops"),
    _metric("db_query_seconds", _H,
            "Per-query database time, labelled by a low-cardinality query_name "
            "of the form `<op>:<table>`.",
            (_lbl("query_name", bound=256),),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0), owner="db"),
    _metric("interaction_handler_seconds", _H,
            "Interaction callback total time, labelled by the custom_id prefix "
            "(== subsystem identity per INV-B).",
            (_PREFIX,),
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0), owner="interaction"),
    _metric("message_pipeline_stage_seconds", _H,
            "Per-stage process() time inside the message-pipeline orchestrator.",
            (_lbl("stage", bound=16),),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0), owner="pipeline"),
    _metric("process_memory_rss_bytes", _G,
            "Resident set size of the bot process in bytes, sampled periodically.",
            owner="ops"),
    _metric("ai_request_seconds", _H,
            "Duration of AI provider calls dispatched through the gateway.",
            (_lbl("task", bound=16), _lbl("provider", bound=8)),
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 60.0), owner="ai"),
    _metric("ai_request_total", _C,
            "AI gateway requests by task and outcome.",
            (_lbl("task", bound=16),
             _lbl("outcome", "success", "timeout", "error", "unavailable", "deterministic")),
            owner="ai"),
    _metric("youtube_provider_request_total", _C,
            "YouTube metadata-fetch requests by content-free outcome category.",
            (_lbl("outcome", "success", "key_missing", "private_or_deleted",
                  "quota_limited", "timeout", "fetch_error"),), owner="media"),
)
