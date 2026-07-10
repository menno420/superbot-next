"""substrate-kit bootstrap v1.7.0 — GENERATED, DO NOT EDIT.

Single-file, stdlib-only. Regenerate from source with:
    python3 substrate-kit/src/build_bootstrap.py
Source of truth: substrate-kit/src/engine/. Edits here are overwritten.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Collection, Sequence
from collections.abc import Iterator
from collections.abc import Mapping, Sequence
from collections.abc import Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass, field, fields
from dataclasses import dataclass, field
from datetime import date
from datetime import date as _led_date
from datetime import date, datetime, timezone
from datetime import datetime, timedelta, timezone
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Any, NamedTuple
from typing import NamedTuple
import argparse
import ast
import copy
import difflib
import hashlib
import itertools
import json
import os
import random
import re
import string
import sys
import tempfile
import time
import uuid

# --- engine/lib/atomicio.py ---
"""Atomic file writes for crash-safe state.

A write goes to a sibling ``*.tmp`` file and is renamed into place with
``os.replace`` — an atomic rename on POSIX and Windows — so a process that dies
mid-write can never leave a half-written, unparseable file behind. This is the
robustness floor the whole engine builds on (plan: Gemini round).
"""




def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically via a temp file + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

# --- engine/lib/config.py ---
"""Host-project configuration for one substrate-kit install.

Reads and writes ``substrate.config.json`` — the single file that absorbs every
host-specific knob so the engine code never hardcodes a project value. Two
interpreters are kept explicitly separate (Hermes-final): ``interpreter`` is the
kit's own runtime, ``interpreter_for_checks`` is the host project's verification
runtime (e.g. ``python3.10`` for a repo whose CI pins 3.10).
"""




CONFIG_FILENAME = "substrate.config.json"
DEFAULT_STATE_DIR = ".substrate"

# THE kit version (founding plan §4.1). Semver keyed to the planted-doc
# contract, state schema, config schema, and CLI surface: MAJOR = breaking
# change to any of those; MINOR = new capability; PATCH = fixes. Exposed as
# `bootstrap.py --version`, stamped into the dist header by
# `src/build_bootstrap.py`, and recorded into `substrate.config.json`
# (`kit_version`) + state by `adopt`/`upgrade`. Bump together with
# `pyproject.toml` `[project] version` (a test pins them equal) and a new
# CHANGELOG.md section (the release workflow refuses to publish without one).
KIT_VERSION = "1.7.0"


def _new_project_id() -> str:
    """Return a short, stable identifier for one install."""
    return uuid.uuid4().hex[:12]


def _default_cadence() -> dict[str, int]:
    """Return the default cadence knobs (every hardcoded cadence lives here)."""
    return {
        # 30, not 20: the source repo's live cadence (superbot Q-0134 — at burst
        # velocity a 20-band fired the docs pass several times a day); the 20
        # default was stale drift the founding plan §3.4 rules fixed.
        "reconciliation_prs": 30,
        "reconciliation_sessions": 20,
        "compaction_sessions": 20,
        "critical_slot_grace_sessions": 3,
        "staleness_days": 14,
        "guided_practice_sessions": 3,
    }


def _default_reflection() -> dict:
    """Return the reflection-buffer knobs (size cap is a hard context guard)."""
    return {"enabled": True, "buffer_size": 5}


def _default_orientation() -> dict:
    """Return the orientation-budget knobs (the K0 ≤7,000-word gate).

    ``boot_docs`` empty means "fall back to ``readpath_docs``" — the
    unconditional boot-read set the budget counts.
    """
    return {"budget_words": 7000, "boot_docs": []}


def _default_economy() -> dict:
    """Return the context-economy knobs (taxonomy/gauges are host policy).

    ``maturity`` gates the actuator: ``shadow`` (report only, the first-prune
    safety protocol) -> ``gated`` (apply with review) -> ``normal``. Classes and
    gauges ship empty — the engine supplies a documented generic default when
    unset; each adopting repo declares its own table (the kit ships the search,
    not our constants).
    """
    return {
        "maturity": "shadow",
        "pass_records_dir": "planning",
        "reference_roots": [],
        "id_patterns": [r"Q-\d{3,}", r"D-\d{3,}", r"R-\d{3,}"],
        "classes": [],
        "gauges": [],
        "debt_threshold": 10,
    }


def _default_namespace() -> dict:
    """Return the namespace-guard knobs (roots to scan + reserved-name map)."""
    return {"roots": [], "reserved": {}}


def _default_review_seam() -> dict:
    """Return the review-seam knobs (provisioned, not wired — no live reviewer)."""
    return {"reviewer": None}


def _default_heartbeat_files() -> list[str]:
    """Return the control-heartbeat file(s) the status checker validates.

    One entry — ``control/status.md`` — for the normal one-Project-per-repo
    shape. A SHARED repo hosting several Projects lists one file per lane
    (the superbot-games pattern, inbox ORDER 004: e.g.
    ``control/status-mining.md`` + ``control/status-exploration.md``): the
    one-writer-per-file rule is preserved *per lane*, and every listed
    heartbeat must beat. An empty list falls back to the default at every
    consumer (a misconfiguration must not silently disable the gate).
    """
    return ["control/status.md"]


def _default_badge_tokens() -> list[str]:
    """Return the default Status-badge taxonomy the doc checker accepts."""
    return [
        "binding",
        "living-ledger",
        "reference",
        "plan",
        "historical",
        "audit",
        "owner-guidance",
        "ideas",
        "archive",
    ]


def _default_readpath_docs() -> list[str]:
    """Return the read-path doc names that seed the reachability roots."""
    return ["AGENT_ORIENTATION.md", "current-state.md"]


def _default_session_markers() -> list[dict[str, str]]:
    """Return the markers every session log must carry (label + substring).

    The Model line (``📊 Model: <model> · <effort> · <task-class>``) is the
    PL-004 telemetry feed (KL-3): ``session-close`` harvests it into
    ``telemetry/model-usage.jsonl``. New adopts require it from birth;
    existing installs gain it at ``upgrade`` (a consumer's gate only tightens
    when it upgrades — founding plan §5.2).
    """
    return [
        {"label": "Status badge", "needle": "**Status:**"},
        {"label": "Session idea", "needle": "💡"},
        {"label": "Previous-session review", "needle": "previous-session review"},
        {"label": "Model line", "needle": "\N{BAR CHART} Model:"},
    ]


@dataclass
class Config:
    """Host-project configuration for one substrate-kit install."""

    project_id: str = field(default_factory=_new_project_id)
    # The kit version this install last adopted/upgraded from — "" until an
    # `adopt`/`upgrade` records it (a pre-release install honestly reports
    # unrecorded rather than guessing). A DECLARED dataclass field on purpose:
    # `from_dict` drops unknown keys and `save_config` serialises only
    # dataclass fields, so a bare JSON key would be stripped on the next
    # load→save round-trip (founding plan §4.1).
    kit_version: str = ""
    interpreter: str = field(default_factory=lambda: sys.executable)
    interpreter_for_checks: str | None = None
    state_dir: str = DEFAULT_STATE_DIR
    docs_root: str = "docs"
    sessions_dir: str = ".sessions"
    paths: dict[str, str] = field(default_factory=dict)
    cadence: dict[str, int] = field(default_factory=_default_cadence)
    scopes: dict[str, str] = field(default_factory=dict)
    badge_tokens: list[str] = field(default_factory=_default_badge_tokens)
    readpath_docs: list[str] = field(default_factory=_default_readpath_docs)
    session_markers: list[dict[str, str]] = field(
        default_factory=_default_session_markers,
    )
    reflection: dict = field(default_factory=_default_reflection)
    orientation: dict = field(default_factory=_default_orientation)
    economy: dict = field(default_factory=_default_economy)
    namespace: dict = field(default_factory=_default_namespace)
    seams: list[dict] = field(default_factory=list)
    review_seam: dict = field(default_factory=_default_review_seam)
    heartbeat_files: list[str] = field(default_factory=_default_heartbeat_files)

    def to_json(self) -> str:
        """Serialise the config to indented, key-sorted JSON."""
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        """Build a Config from a parsed dict, ignoring unknown keys."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def config_path(root: Path) -> Path:
    """Return the config-file path for a project ``root``."""
    return root / CONFIG_FILENAME


def load_config(root: Path) -> Config:
    """Load the config from ``root``; return defaults if none exists."""
    path = config_path(root)
    if not path.exists():
        return Config()
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config.from_dict(data)


def save_config(root: Path, config: Config) -> None:
    """Write ``config`` to ``root`` atomically."""
    atomic_write_text(config_path(root), config.to_json() + "\n")

# --- engine/lib/state.py ---
"""The state-backend interface and its default JSON implementation.

The *interface* — not a raw JSON shape — is the contract the rest of the engine
codes against (Hermes-final, plan §2), so a future SQLite backend can replace the
JSON one without a rewrite. The default backend is one JSON file written
atomically; mutations inside a ``transaction`` roll back on error and flush once.
"""




STATE_SCHEMA_VERSION = 1


def default_state(project_id: str) -> dict[str, Any]:
    """Return the initial state document for a fresh install."""
    return {
        "version": STATE_SCHEMA_VERSION,
        "project_id": project_id,
        "mode": "guided",
        "promotion_rights": "propose",
        "stage": "integration",
        "stance": "analysis",
        "session_count": 0,
        "slots": {},
        "slot_values": {},
        "open_questions": [],
        "quiet_sessions": 0,
        "graduation": {
            "soft_target_sessions": 50,
            "criteria": {
                "critical_slots_filled_pct": 0.8,
                "blocking_questions": 0,
            },
        },
        "mode_history": [],
        "reflection_buffer": {"active_count": 0, "last_mined": None},
        "graduation_proposed": False,
        "last_compaction_session": 0,
        "review_log": [],
    }


class StateBackend(ABC):
    """Read / write / query / transaction / migrate contract for engine state."""

    version: int = STATE_SCHEMA_VERSION

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Return the value stored at ``key`` or ``default``."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store ``value`` at ``key`` (flushing unless inside a transaction)."""

    @abstractmethod
    def query(self, prefix: str = "") -> dict[str, Any]:
        """Return all key/value pairs whose key starts with ``prefix``."""

    @abstractmethod
    def transaction(self) -> AbstractContextManager[StateBackend]:
        """Return a context manager that commits on success, rolls back on error."""

    @abstractmethod
    def migrate(self, to_version: int) -> None:
        """Migrate the stored document to schema ``to_version``."""


class JsonStateBackend(StateBackend):
    """A StateBackend backed by one atomically-written JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = self._read()
        self._txn_depth = 0

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _flush(self) -> None:
        atomic_write_text(
            self._path,
            json.dumps(self._data, indent=2, sort_keys=True) + "\n",
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value stored at ``key`` or ``default``."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` at ``key``; flush now unless inside a transaction."""
        self._data[key] = value
        if self._txn_depth == 0:
            self._flush()

    def query(self, prefix: str = "") -> dict[str, Any]:
        """Return all key/value pairs whose key starts with ``prefix``."""
        return {k: v for k, v in self._data.items() if k.startswith(prefix)}

    @contextmanager
    def transaction(self) -> Iterator[JsonStateBackend]:
        """Buffer writes; roll back the whole document on error, else flush once.

        Re-entrant (Q-0223 tail ①): a helper that opens its own transaction may
        be composed inside a caller's wider transaction. Each level snapshots on
        entry and restores its own snapshot on error; only the *outermost* exit
        flushes, so a composed multi-write either fully lands or fully rolls
        back to the enclosing level's snapshot — never a partial flush.
        """
        snapshot = copy.deepcopy(self._data)
        self._txn_depth += 1
        try:
            yield self
        except Exception:
            self._data = snapshot
            raise
        finally:
            self._txn_depth -= 1
        if self._txn_depth == 0:
            self._flush()

    def migrate(self, to_version: int) -> None:
        """Set the stored schema version (no transforms needed at v1)."""
        self._data["version"] = to_version
        self._flush()

    @property
    def data(self) -> dict[str, Any]:
        """Return a shallow copy of the current state document."""
        return dict(self._data)

# --- engine/lib/guardrail.py ---
"""The live-loop guardrail.

A mechanical guarantee (plan: design-corroboration) that the kit never operates
on its own repository root — which would let it mutate the very workflow it runs
inside. Safe targets are the system temp tree, an ``examples/`` subtree of the
kit, or any directory outside the kit. Enforced in code, in the first commit —
not left as a doc.
"""




class UnsafeTargetError(Exception):
    """Raised when a target directory would corrupt the kit's own live loop."""


def assert_safe_target(target: Path, kit_root: Path) -> None:
    """Refuse to operate on the kit's own repo root.

    Unsafe: ``kit_root`` itself or a non-``examples`` path inside it — even
    when the kit checkout lives under the system temp tree (an earlier
    temp-tree shortcut ran first and silently voided the whole guarantee for a
    kit cloned into ``/tmp``). Everything outside ``kit_root``, and the
    ``examples/`` subtree, is safe. A ``kit_root`` that is a *file* (the
    single-file bootstrap has no kit tree to protect) never matches.
    """
    target = Path(target).resolve()
    kit_root = Path(kit_root).resolve()
    inside_kit = target == kit_root or target.is_relative_to(kit_root)
    inside_examples = target.is_relative_to(kit_root / "examples")
    if inside_kit and not inside_examples:
        msg = f"refusing to operate on the kit's own tree: {target}"
        raise UnsafeTargetError(msg)

# --- engine/lib/modes.py ---
"""Integration-mode behavior policies (plan section 3 — the adoption-pace axis).

The ``mode`` state field (observe | guided | active) existed since PR 1 but nothing
read it; this module is the single place its *behavior* is defined, so every
consumer (interview quota, orientation depth, trigger mandates, actuator gating,
graduation) asks one policy table instead of re-deriving the semantics.

The three modes, per the approved plan:

- **observe** — the kit imposes nothing: each session writes a light note, asks
  only 1-2 observation questions, and passively profiles how the user already
  works; after enough sessions it *proposes* a tailored workflow (never
  auto-graduates — proposal only).
- **guided** — the default: the workflow rolls out one practice at a time in a
  fixed order (session logs → idea lifecycle → question router → session-enders
  → gates), each arriving only after the prior is established; triggers may
  mandate questions.
- **active** — the full workflow from session 1; the interview runs aggressively
  (no quota) to fill slots fast.

``promotion_rights`` is the *separate* autonomy axis: what the agent may change
without sign-off. Actuators (economy prunes, maintenance writes) may apply only
when the mode allows it AND promotion_rights is ``"promote"`` — otherwise they
stay dry-run/propose.
"""



MODES = ("observe", "guided", "active")

# The guided-mode rollout order is fixed by the plan; only the pacing is ours.
GUIDED_ROLLOUT = (
    "session_logs",
    "idea_lifecycle",
    "question_router",
    "session_enders",
    "gates",
)

DEFAULT_MODE = "guided"

# One behavior record per mode. quota None = unlimited questions per session.
_MODE_POLICIES: dict[str, dict[str, Any]] = {
    "observe": {
        "question_quota": 2,
        "orientation_depth": "minimal",
        "practices": "none",
        "triggers_mandate": False,
        "actuators_allowed": False,
        "auto_graduate": False,
        "workflow_proposal_after_sessions": 5,
    },
    "guided": {
        "question_quota": 3,
        "orientation_depth": "standard",
        "practices": "rollout",
        "triggers_mandate": True,
        "actuators_allowed": True,
        "auto_graduate": True,
        "workflow_proposal_after_sessions": None,
    },
    "active": {
        "question_quota": None,
        "orientation_depth": "full",
        "practices": "all",
        "triggers_mandate": True,
        "actuators_allowed": True,
        "auto_graduate": True,
        "workflow_proposal_after_sessions": None,
    },
}


def mode_policy(state: dict[str, Any]) -> dict[str, Any]:
    """Return the behavior policy for the state's active mode.

    An unknown or missing mode falls back to the default (``guided``) so every
    consumer fails open onto sane behavior rather than crashing on bad state.
    """
    mode = state.get("mode", DEFAULT_MODE)
    return dict(_MODE_POLICIES.get(mode, _MODE_POLICIES[DEFAULT_MODE]))


def question_quota(state: dict[str, Any]) -> int | None:
    """Return the per-session interview question quota (None = unlimited)."""
    quota = mode_policy(state)["question_quota"]
    return quota if quota is None else int(quota)


def orientation_depth(state: dict[str, Any]) -> str:
    """Return the orientation-injection depth: minimal | standard | full."""
    return str(mode_policy(state)["orientation_depth"])


def triggers_mandate(state: dict[str, Any]) -> bool:
    """True when fired triggers may *mandate* questions (guided/active only)."""
    return bool(mode_policy(state)["triggers_mandate"])


def actuators_may_apply(state: dict[str, Any]) -> bool:
    """True when actuators may apply changes (mode allows AND rights say promote).

    This is the promotion-rights enforcement point: whatever the mode, an agent
    whose ``promotion_rights`` is ``"propose"`` (or ``"observe"``) only ever
    produces dry-run reports.
    """
    if not mode_policy(state)["actuators_allowed"]:
        return False
    return state.get("promotion_rights") == "promote"


def may_auto_graduate(state: dict[str, Any]) -> bool:
    """True when graduation may fire automatically (observe mode proposes only)."""
    return bool(mode_policy(state)["auto_graduate"])


def workflow_proposal_due(state: dict[str, Any]) -> bool:
    """True when observe mode has watched long enough to propose its workflow."""
    threshold = mode_policy(state)["workflow_proposal_after_sessions"]
    if threshold is None:
        return False
    return int(state.get("session_count", 0)) >= int(threshold)


def active_practices(
    state: dict[str, Any],
    cadence: dict[str, int] | None = None,
) -> list[str]:
    """Return the workflow practices currently active under the mode's pacing.

    observe: none (the kit imposes nothing). active: all from session 1.
    guided: one practice unlocks per ``guided_practice_sessions`` sessions
    (config cadence, default 3), in the fixed rollout order — the "only after
    the prior is established" pacing, made deterministic.
    """
    practices = mode_policy(state)["practices"]
    if practices == "none":
        return []
    if practices == "all":
        return list(GUIDED_ROLLOUT)
    interval = int((cadence or {}).get("guided_practice_sessions", 3))
    interval = max(interval, 1)
    sessions = int(state.get("session_count", 0))
    unlocked = 1 + sessions // interval
    return list(GUIDED_ROLLOUT[:unlocked])

# --- engine/interview/question_bank.py ---
"""The interview question bank — the seed set the staged onboarding draws from.

Curation policy (Hermes #7): keep this lean. Add a question only when its slot
genuinely blocks graduation, or a checker keeps flagging its absence; prune
questions that no longer earn their place. Each entry is a plain dict so the bank
ships inside the stdlib-only bootstrap with no parser (the plan named
``question_bank.yml``; a Python module is the simplest form that embeds and runs
identically in ``src`` and the single-file ``dist`` — no YAML/JSON dependency).

Entry fields:
  id        — stable "Q-NNN" identifier.
  slot      — the content slot it fills (matches the project index).
  audience  — "user" (ask the maintainer) or "self" (the agent infers).
  prompt    — the question text.
  routing   — where a confirmed answer lands (a doc:field or state:key).
  priority  — "blocking" | "high" | "normal".
  critical  — True if graduation requires this slot filled (confirmed, not assumed).

Optional fields:
  trigger   — a trigger kind (see engine/loop/triggers.py); the question is pulled
              into a mandatory-question session when that trigger fires.
  objective — True when a different model can verify the answer against evidence
              (the review seam may then confirm a provisional answer); subjective
              slots stay provisional until the user confirms.
  min_len   — anti-gaming floor: an answer shorter than this never fills the slot.
"""


CURATION_RULE = (
    "Lean bank: add a question only when it blocks graduation or a checker keeps "
    "flagging its slot; prune questions that no longer earn their place."
)

QUESTIONS: list[dict] = [
    {
        "id": "Q-001",
        "slot": "integration_mode",
        "audience": "user",
        "prompt": "Adoption pace for the workflow? observe | guided | active.",
        "routing": "state:mode",
        "priority": "blocking",
        "critical": True,
        # The sole blocking+critical slot needs an anti-gaming floor too — the
        # valid values (observe/guided/active) are all >=6 chars, so a floor of
        # 4 rejects a hollow single-char graduation without ever rejecting a
        # real mode.
        "min_len": 4,
    },
    {
        "id": "Q-002",
        "slot": "project_name",
        "audience": "user",
        "prompt": "What is this project called?",
        "routing": "templates/CLAUDE.md:project_name",
        "priority": "high",
        "critical": True,
        "objective": True,
        "min_len": 2,
    },
    {
        "id": "Q-003",
        "slot": "primary_language",
        "audience": "user",
        "prompt": "Primary language / runtime (e.g. Python 3.10, TypeScript)?",
        "routing": "templates/CLAUDE.md:language",
        "priority": "high",
        "critical": True,
        "objective": True,
        "min_len": 3,
    },
    {
        "id": "Q-004",
        "slot": "architecture_layers",
        "audience": "user",
        "prompt": "What are the top-level layers and their import rules?",
        "routing": "templates/architecture.md:layers",
        "priority": "high",
        "critical": True,
        "trigger": "critical_unfilled",
        "objective": True,
        "min_len": 20,
    },
    {
        "id": "Q-005",
        "slot": "verify_command",
        "audience": "user",
        "prompt": "One command that proves a change is good (tests + lint)?",
        "routing": "templates/CLAUDE.md:verify_command",
        "priority": "high",
        "critical": True,
        "objective": True,
        "min_len": 4,
    },
    {
        "id": "Q-006",
        "slot": "ownership_model",
        "audience": "self",
        "prompt": "Which component owns each data store / write path?",
        "routing": "templates/ownership.md:owners",
        "priority": "normal",
        "critical": False,
        "objective": True,
        "min_len": 20,
    },
    {
        "id": "Q-007",
        "slot": "doc_roots",
        "audience": "self",
        "prompt": "Where does durable documentation live?",
        "routing": "state:paths.docs",
        "priority": "normal",
        "critical": False,
    },
    {
        "id": "Q-008",
        "slot": "owner_profile",
        "audience": "user",
        "prompt": "How do you like an agent to work (tone, detail, autonomy)?",
        "routing": "templates/owner-profile.md:style",
        "priority": "normal",
        "critical": False,
    },
    {
        "id": "Q-009",
        "slot": "mutation_seam",
        "audience": "self",
        "prompt": "How are writes gated (the audited mutation seam)?",
        "routing": "templates/runtime_contracts.md:mutations",
        "priority": "normal",
        "critical": False,
        "objective": True,
        "min_len": 20,
    },
    {
        "id": "Q-010",
        "slot": "review_ritual",
        "audience": "user",
        "prompt": "Your PR-review and release rhythm?",
        "routing": "templates/owner-profile.md:procedures",
        "priority": "normal",
        "critical": False,
    },
    {
        "id": "Q-011",
        "slot": "drift_resolution",
        "audience": "self",
        "prompt": "Doc-hygiene checks are failing - what drifted, and what fixes it?",
        "routing": "state:open_questions",
        "priority": "high",
        "critical": False,
        "trigger": "drift",
    },
    {
        "id": "Q-012",
        "slot": "staleness_review",
        "audience": "user",
        "prompt": "Memory looks stale (reconciliation overdue) - what changed since the last update?",
        "routing": "templates/current-state.md:refresh",
        "priority": "normal",
        "critical": False,
        "trigger": "staleness",
    },
    {
        "id": "Q-013",
        "slot": "new_area_ownership",
        "audience": "user",
        "prompt": "A new area appeared with no ownership/folio entry - which component owns it?",
        "routing": "templates/ownership.md:owners",
        "priority": "high",
        "critical": False,
        "trigger": "new_area",
    },
]

# --- engine/interview/stages.py ---
"""Stage state machine + adaptive graduation (plan section 2).

Stage 1 (``integration``) graduates to stage 2 (``steady``) *adaptively* — when
the project's **critical** content slots are mostly filled (by confirmed, not
assumed, answers), no blocking questions remain, and several consecutive sessions
surface no new mandatory question — not at a hard session count.
"""




STAGE_INTEGRATION = "integration"
STAGE_STEADY = "steady"

_DEFAULT_FILL_PCT = 0.8
_DEFAULT_QUIET_SESSIONS = 3


def critical_fill_ratio(slots: dict[str, str], critical: list[str]) -> float:
    """Return the fraction of ``critical`` slots marked ``filled``."""
    if not critical:
        return 1.0
    filled = sum(1 for name in critical if slots.get(name) == "filled")
    return filled / len(critical)


def graduation_ready(
    state: dict[str, Any],
    critical: list[str],
) -> tuple[bool, list[str]]:
    """Return ``(ready, reasons)`` for graduating integration -> steady.

    ``reasons`` lists the unmet criteria when not ready (empty when ready).
    """
    criteria = state.get("graduation", {}).get("criteria", {})
    want_pct = criteria.get("critical_slots_filled_pct", _DEFAULT_FILL_PCT)
    want_quiet = criteria.get("quiet_sessions_required", _DEFAULT_QUIET_SESSIONS)
    reasons: list[str] = []

    ratio = critical_fill_ratio(state.get("slots", {}), critical)
    if ratio < want_pct:
        reasons.append(f"critical slots {ratio:.0%} < {want_pct:.0%}")
    blocking = len(state.get("open_questions", []))
    if blocking:
        reasons.append(f"{blocking} blocking question(s) open")
    quiet = state.get("quiet_sessions", 0)
    if quiet < want_quiet:
        reasons.append(f"quiet streak {quiet} < {want_quiet}")
    return (not reasons, reasons)


def maybe_graduate(backend: Any, critical: list[str]) -> bool:
    """Advance integration -> steady if ready; return whether it graduated.

    Mode-conditional (the plan's per-mode behavior): ``observe`` mode never
    auto-graduates — when ready it records a *proposal* (``graduation_proposed``)
    for the user to accept (switch mode or graduate explicitly); guided/active
    graduate automatically.
    """
    if backend.get("stage") != STAGE_INTEGRATION:
        return False
    ready, _ = graduation_ready(backend.data, critical)
    if not ready:
        return False
    if not may_auto_graduate(backend.data):
        backend.set("graduation_proposed", True)
        return False
    backend.set("stage", STAGE_STEADY)
    return True

# --- engine/interview/interview.py ---
"""The interview pass — fills content slots from the question bank (plan section 4).

A session asks its pending questions. A user-facing answer fills a slot
(``filled``); when no human is present the agent self-answers, recording a
*provisional* assumption (``provisional``) that never counts toward graduation
until confirmed. This is what lets an autonomous run keep moving without blocking:
it records assumptions, flags them, and moves on.
"""




_PRIORITY_ORDER = {"blocking": 0, "high": 1, "normal": 2}
_PLACEHOLDER_ANSWERS = frozenset({"todo", "tbd", "...", "n/a", "?"})
_ANSWER_STRIP = string.punctuation + string.whitespace


def critical_slots(bank: list[dict] | None = None) -> list[str]:
    """Return the slot names the bank marks as critical."""
    bank = QUESTIONS if bank is None else bank
    return [q["slot"] for q in bank if q.get("critical")]


def pending_questions(
    state: dict[str, Any],
    bank: list[dict] | None = None,
) -> list[dict]:
    """Return bank questions whose slot is not yet ``filled``."""
    bank = QUESTIONS if bank is None else bank
    slots = state.get("slots", {})
    return [q for q in bank if slots.get(q["slot"]) != "filled"]


def session_questions(
    state: dict[str, Any],
    bank: list[dict] | None = None,
) -> list[dict]:
    """Return this session's ask list: pending, priority-ordered, quota-capped.

    The cap is the integration mode's question quota (observe asks 1-2, guided a
    few, active unlimited). Blocking questions sort first, so a quota can never
    hide one.
    """
    pending = sorted(
        pending_questions(state, bank),
        key=lambda q: _PRIORITY_ORDER.get(q.get("priority", "normal"), 2),
    )
    quota = question_quota(state)
    return pending if quota is None else pending[:quota]


def answer_is_substantive(question: dict, answer: str) -> bool:
    """True when ``answer`` passes the anti-gaming floor for this slot.

    Completeness counts only non-placeholder content: no leftover ``${slot}``
    marker, not a stock placeholder word, and at least the slot's ``min_len``
    characters — so an autonomous run can't graduate on hollow answers.
    """
    text = answer.strip()
    if not text or "${" in text:
        return False
    # Strip surrounding punctuation before the placeholder-word check so
    # "todo." / "tbd!" / "n/a?" cannot slip past the exact-match set.
    if text.lower().strip(_ANSWER_STRIP) in _PLACEHOLDER_ANSWERS:
        return False
    # Content-free answers never fill a slot: no alphanumeric char at all
    # ("??", "...", "!!"), or a single character repeated ("aaaa", "....").
    if not any(ch.isalnum() for ch in text) or len(set(text)) == 1:
        return False
    return len(text) >= int(question.get("min_len", 1))


def _set_without_open_question(backend: Any, question_id: str | None) -> None:
    """Drop ``question_id`` from open_questions via ``backend.set`` (no flush).

    Called *inside* a transaction so the slot fill and its escalation
    resolution commit in one atomic flush — a crash between two separate
    flushes once left a filled slot with a stale open question that nothing
    automatic could clear.
    """
    if not question_id:
        return
    open_questions = list(backend.get("open_questions", []))
    if question_id in open_questions:
        open_questions.remove(question_id)
        backend.set("open_questions", open_questions)


def record_answer(backend: Any, question: dict, answer: str, *, source: str) -> None:
    """Fill ``question``'s slot from an answer.

    ``source="user"`` confirms the slot (``filled``) when the answer passes the
    anti-gaming floor (``partial`` otherwise); any other source records a
    ``provisional`` self-answer that must be confirmed before it counts. A
    filled answer also resolves the question's escalated open-question entry.
    """
    if source == "user":
        status = "filled" if answer_is_substantive(question, answer) else "partial"
    else:
        status = "provisional"
    slots = dict(backend.get("slots", {}))
    values = dict(backend.get("slot_values", {}))
    slots[question["slot"]] = status
    values[question["slot"]] = {
        "value": answer,
        "source": source,
        "question_id": question["id"],
    }
    with backend.transaction():
        backend.set("slots", slots)
        backend.set("slot_values", values)
        if status == "filled":
            _set_without_open_question(backend, question["id"])


def confirm_slot(backend: Any, slot: str, *, source: str) -> bool:
    """Promote a ``provisional`` slot to ``filled`` (the confirmation seam).

    ``source`` records who confirmed (``"user"`` or ``"reviewer:<name>"``).
    Returns False when the slot is not provisional (nothing to confirm).
    """
    slots = dict(backend.get("slots", {}))
    if slots.get(slot) != "provisional":
        return False
    values = dict(backend.get("slot_values", {}))
    entry = dict(values.get(slot, {}))
    entry["source"] = f"confirmed:{source}"
    slots[slot] = "filled"
    values[slot] = entry
    with backend.transaction():
        backend.set("slots", slots)
        backend.set("slot_values", values)
        _set_without_open_question(backend, entry.get("question_id"))
    return True


def run_session(
    backend: Any,
    answers: dict[str, str],
    *,
    autonomous: bool = False,
    bank: list[dict] | None = None,
) -> dict[str, Any]:
    """Run one interview session, then attempt graduation.

    ``answers`` maps slot -> user answer. A pending question with a user answer is
    confirmed; otherwise, in ``autonomous`` mode it is self-answered provisionally
    (within the integration mode's question quota — blocking questions sort first,
    so the quota never starves one). A session that leaves no blocking question
    unanswered extends the quiet streak; any unanswered blocking question resets
    it AND escalates onto ``open_questions``, which holds graduation until the
    question is answered.
    """
    bank = QUESTIONS if bank is None else bank
    pending = sorted(
        pending_questions(backend.data, bank),
        key=lambda q: _PRIORITY_ORDER.get(q.get("priority", "normal"), 2),
    )
    quota = question_quota(backend.data)
    left_blocking = False
    self_answered = 0
    for question in pending:
        slot = question["slot"]
        blocking = question.get("priority") == "blocking"
        if slot in answers:
            record_answer(backend, question, answers[slot], source="user")
            continue
        if autonomous and (quota is None or self_answered < quota):
            # Never downgrade an existing provisional value (e.g. an
            # adopt-time derived answer) to a placeholder assumption — the
            # slot already carries better content awaiting confirmation.
            if backend.get("slots", {}).get(slot) != "provisional":
                record_answer(
                    backend, question, f"ASSUMED: {slot}", source="assumption"
                )
                self_answered += 1
            if not blocking:
                continue
            # A provisional self-answer does NOT discharge a blocking question
            # — it must still escalate, or an autonomous run could graduate on
            # an unconfirmed assumption for the one slot marked blocking.
        elif not blocking:
            continue
        left_blocking = True
        open_questions = list(backend.get("open_questions", []))
        if question["id"] not in open_questions:
            open_questions.append(question["id"])
            backend.set("open_questions", open_questions)

    backend.set("session_count", int(backend.get("session_count", 0)) + 1)
    quiet = int(backend.get("quiet_sessions", 0))
    backend.set("quiet_sessions", 0 if left_blocking else quiet + 1)

    graduated = maybe_graduate(backend, critical_slots(bank))
    return {
        "session": backend.get("session_count"),
        "pending_after": len(pending_questions(backend.data, bank)),
        "graduated": graduated,
        "stage": backend.get("stage"),
    }

# --- engine/checks/check_docs.py ---
"""Generic doc-hygiene checker (config-driven port of ``check_docs``).

Three portable checks, every input supplied by the caller (from config) rather
than hardcoded:

  1. **badge**      — every ``*.md`` under ``docs_root`` (non-ADR) carries a
     ``> **Status:** `<token>``` line in its first 12 lines, ``<token>`` drawn
     from the project's allowed taxonomy.
  2. **link**       — every relative markdown link ``[text](path)`` resolves to
     an existing file (external / anchor-only links are skipped).
  3. **reachable**  — every live doc is reachable by following links + backtick
     ``<docs>/*.md`` refs from a read-path root (the read-path docs + any
     ``README.md``). Orphans fail unless badged ``historical`` / ``archive`` or
     an ADR.

The host's soft ratchets (top-level pile, recently-shipped) and the
superbot-specific freshness rule are intentionally left behind — they are
project policy, not portable mechanism. Pure stdlib; returns findings rather
than printing so the CLI owns all output.
"""




class Finding(NamedTuple):
    """One doc-hygiene violation: ``path`` is relative to ``docs_root``."""

    path: str
    kind: str
    message: str


# `> **Status:** `<token>`` — the machine-readable badge (rich text may follow).
_BADGE_RE = re.compile(r"\*\*Status:\*\*\s*`([a-z-]+)`")
# ADR filename: NNN-something.md (exempt — ADRs use their own Accepted/Superseded).
_ADR_RE = re.compile(r"^\d+-.*\.md$")
# Markdown link target: [text](target).
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Badges whose docs are retired content and need no inbound link.
_EXEMPT_BADGES = frozenset({"historical", "archive"})

_BADGE_MISSING = "missing `> **Status:** `<token>`` in first 12 lines"
_ORPHAN_MSG = (
    "orphan: not reachable from any read-path doc / README "
    "(link it from one, or badge it historical/archive)"
)


def _md_files(docs_root: Path) -> list[Path]:
    """Return every ``*.md`` under ``docs_root`` (sorted, empty if absent)."""
    if not docs_root.exists():
        return []
    return sorted(docs_root.rglob("*.md"))


def _is_adr(path: Path) -> bool:
    """True for ``decisions/NNN-*.md`` ADR files (badge-exempt)."""
    return path.parent.name == "decisions" and bool(_ADR_RE.match(path.name))


def badge_token(path: Path) -> str | None:
    """Return the doc's Status-badge token from its first 12 lines, or None.

    Public: the trigger detector (and any host tooling) classifies docs by this
    same badge scan — one badge reader, not per-module copies. An unreadable or
    non-UTF-8 file reads as badge-less rather than crashing the whole scan.
    """
    try:
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:12])
    except (OSError, UnicodeDecodeError):
        return None
    match = _BADGE_RE.search(head)
    return match.group(1) if match else None


# Backward-compatible alias for the original private name.
_badge_token = badge_token


def _link_target(raw: str) -> str:
    """Normalise a markdown link target (drop ``<>``, title, ``#anchor``)."""
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:].split(">", 1)[0]
    parts = target.split()
    target = parts[0] if parts else target
    return target.split("#", 1)[0]


def _backtick_docs_re(docs_root: Path) -> re.Pattern[str]:
    """Compile the ``<docs>/*.md`` backtick-ref pattern for this doc root."""
    name = re.escape(docs_root.name)
    return re.compile(rf"`({name}/[\w./-]+\.md)`")


def check_badges(docs_root: Path, badge_tokens: Collection[str]) -> list[Finding]:
    """Every non-ADR doc must declare a Status badge from the taxonomy."""
    allowed = set(badge_tokens)
    findings: list[Finding] = []
    for f in _md_files(docs_root):
        if _is_adr(f):
            continue
        rel = f.relative_to(docs_root).as_posix()
        token = badge_token(f)
        if token is None:
            findings.append(Finding(rel, "badge", _BADGE_MISSING))
        elif token not in allowed:
            allowed_list = ", ".join(sorted(allowed))
            findings.append(
                Finding(
                    rel,
                    "badge",
                    f"invalid badge token `{token}` (allowed: {allowed_list})",
                ),
            )
    return findings


def check_links(docs_root: Path) -> list[Finding]:
    """Relative markdown links inside ``docs_root`` must resolve.

    An unreadable / non-UTF-8 file is reported as an ``encoding`` finding
    instead of crashing the scan (one bad byte must not take down triggers,
    ``maintain``, and ``check`` together).
    """
    findings: list[Finding] = []
    for f in _md_files(docs_root):
        rel = f.relative_to(docs_root).as_posix()
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(Finding(rel, "encoding", f"unreadable as UTF-8: {exc}"))
            continue
        for lineno, line in enumerate(lines, 1):
            for raw in _MD_LINK_RE.findall(line):
                if raw.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = _link_target(raw)
                if not target or target.startswith(("http", "mailto:")):
                    continue
                if not (f.parent / target).resolve().exists():
                    msg = f"L{lineno}: dead link -> {raw}"
                    findings.append(Finding(rel, "link", msg))
    return findings


def _outgoing_links(path: Path, docs_root: Path) -> set[Path]:
    """Resolve every relative markdown link + backtick ``<docs>/*.md`` ref."""
    out: set[Path] = set()
    backtick = _backtick_docs_re(docs_root)
    root = docs_root.parent
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return out
    for line in text.splitlines():
        for raw in _MD_LINK_RE.findall(line):
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = _link_target(raw)
            if target:
                out.add((path.parent / target).resolve())
        for ref in backtick.findall(line):
            out.add((root / ref).resolve())
    return out


def check_reachable(docs_root: Path, readpath_docs: Sequence[str]) -> list[Finding]:
    """Every live doc must be reachable from a read-path root / README.

    Walks the doc graph (markdown links + backtick ``<docs>/*.md`` refs) from the
    roots; any doc not reached — and not ``historical`` / ``archive`` badged or an
    ADR — is an orphan.
    """
    roots = [docs_root / name for name in readpath_docs]
    roots += sorted(docs_root.rglob("README.md"))
    seen: set[Path] = set()
    queue: deque[Path] = deque()
    for root in roots:
        resolved = root.resolve()
        if root.exists() and resolved not in seen:
            seen.add(resolved)
            queue.append(resolved)
    while queue:
        cur = queue.popleft()
        if cur.suffix != ".md" or not cur.exists():
            continue
        for nxt in _outgoing_links(cur, docs_root):
            if nxt not in seen and nxt.suffix == ".md" and nxt.exists():
                seen.add(nxt)
                queue.append(nxt)

    findings: list[Finding] = []
    for f in _md_files(docs_root):
        if f.resolve() in seen or _is_adr(f):
            continue
        if badge_token(f) in _EXEMPT_BADGES:
            continue
        rel = f.relative_to(docs_root).as_posix()
        findings.append(Finding(rel, "reachable", _ORPHAN_MSG))
    return findings


def run_doc_checks(
    docs_root: Path,
    badge_tokens: Collection[str],
    readpath_docs: Sequence[str],
) -> list[Finding]:
    """Run every doc check and return the combined findings."""
    return (
        check_badges(docs_root, badge_tokens)
        + check_links(docs_root)
        + check_reachable(docs_root, readpath_docs)
    )

# --- engine/checks/allowlist.py ---
"""Reasons-required check allowlist (KL-3 — the §5.3 triage mechanism).

Port of the host project's ``*_exceptions.yml`` discipline: a finding may be
suppressed only by an allowlist entry that says **why**. The file lives at
``<state_dir>/check-exceptions.yml`` (consumer-owned, committed), a YAML list
of entries::

    # one entry per accepted finding — reason is REQUIRED
    # verdict: accepted_risk (default) or false_positive
    - path: docs/legacy-import.md
      kind: badge
      reason: "generated import, migrates at KL-5 — badge lands with the move"
      triaged: 2026-07-09
      by: session-kl3
      verdict: accepted_risk

Schema: ``{path, kind, reason (REQUIRED), triaged, by, verdict?}``. An entry
without a non-empty ``reason`` is **refused**: it suppresses nothing and is
itself reported as a finding — the door, not a nag. Creating a (valid) entry
IS the false_positive / accepted_risk verdict event for the guard-fire feed
(founding plan §5.3): the suppressed fire is recorded with the entry's
verdict + reason instead of a null awaiting triage.

The parser is a deliberate stdlib-only YAML *subset* (the engine imports no
third-party packages): comments, a flat list of flat string-valued mappings,
optional single/double quotes. Anything it cannot read is reported as a
finding rather than silently ignored — a malformed allowlist must never
silently widen (entries lost = findings resurface: fail-closed for
suppression, loud about why).
"""




EXCEPTIONS_FILENAME = "check-exceptions.yml"

_ENTRY_KEYS = ("path", "kind", "reason", "triaged", "by", "verdict")
_VERDICTS = ("accepted_risk", "false_positive")


def _unquote(value: str) -> str:
    """Strip one matching pair of surrounding quotes from ``value``."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_allowlist(text: str, source: str) -> tuple[list[dict], list[Finding]]:
    """Parse the YAML-subset allowlist ``text`` into (entries, findings).

    Valid entries (with a non-empty ``reason``) go to ``entries``; refused or
    unparseable material becomes ``Finding``s with ``kind="allowlist"``
    (``path`` = ``source``, the allowlist file's own relpath).
    """
    entries: list[dict] = []
    findings: list[Finding] = []
    current: dict | None = None

    def close(entry: dict | None) -> None:
        if entry is None:
            return
        reason = str(entry.get("reason", "")).strip()
        label = entry.get("path") or entry.get("kind") or "?"
        if not reason:
            findings.append(
                Finding(
                    source,
                    "allowlist",
                    f"entry for {label!r} has no reason — refused "
                    "(reasons are required; the entry suppresses nothing)",
                ),
            )
            return
        verdict = entry.get("verdict", "accepted_risk")
        if verdict not in _VERDICTS:
            findings.append(
                Finding(
                    source,
                    "allowlist",
                    f"entry for {label!r} has unknown verdict {verdict!r} "
                    f"(allowed: {', '.join(_VERDICTS)}) — refused",
                ),
            )
            return
        entry["verdict"] = verdict
        entries.append(entry)

    for number, raw in enumerate(text.splitlines(), start=1):
        # Full-line comments only: a reason like "see PR #1770" keeps its #.
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        if stripped.startswith("- "):
            close(current)
            current = {}
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        if current is None or ":" not in stripped:
            findings.append(
                Finding(
                    source,
                    "allowlist",
                    f"line {number} is not part of a `- key: value` entry — "
                    "unparseable (the allowlist accepts a flat YAML list of "
                    "flat mappings only)",
                ),
            )
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        if key not in _ENTRY_KEYS:
            findings.append(
                Finding(
                    source,
                    "allowlist",
                    f"line {number}: unknown key {key!r} "
                    f"(known: {', '.join(_ENTRY_KEYS)})",
                ),
            )
            continue
        current[key] = _unquote(value.strip())
    close(current)
    return entries, findings


def load_allowlist(root: Path, state_dir: str) -> tuple[list[dict], list[Finding]]:
    """Load ``<state_dir>/check-exceptions.yml`` — ``([], [])`` when absent.

    An unreadable file yields no entries and one finding (never a crash: the
    checker must run on any tree).
    """
    path = root / state_dir / EXCEPTIONS_FILENAME
    source = f"{state_dir}/{EXCEPTIONS_FILENAME}"
    if not path.is_file():
        return [], []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], [Finding(source, "allowlist", "file unreadable — no suppression")]
    return parse_allowlist(text, source)


def apply_allowlist(
    findings: list,
    entries: list[dict],
) -> tuple[list, list[tuple]]:
    """Split ``findings`` into (kept, suppressed) by exact path+kind match.

    ``suppressed`` pairs each dropped finding with the entry that covered it,
    so the caller can record the guard fire with the entry's verdict+reason.
    Matching is deliberately exact on ``path`` and ``kind`` — a broad glob
    would let one entry silence a class of future findings its reason never
    triaged.
    """
    kept: list = []
    suppressed: list[tuple] = []
    for finding in findings:
        entry = next(
            (
                e
                for e in entries
                if e.get("path") == str(finding.path)
                and e.get("kind") == str(finding.kind)
            ),
            None,
        )
        if entry is None:
            kept.append(finding)
        else:
            suppressed.append((finding, entry))
    return kept, suppressed

# --- engine/checks/check_session_log.py ---
"""Generic session-log completeness checker (config-driven port).

The session workflow asks every session to end with a
``<sessions_dir>/<date>-<slug>.md`` log that carries a set of required markers
(by default: a Status badge, a session-idea flag, and a previous-session review).
Each marker is a ``{"label", "needle"}`` pair from ``substrate.config.json``, so a
host tunes the ritual without touching engine code.

Unlike the host's version this port does **not** shell out to ``git`` to pick the
"current" log — ``subprocess`` is banned in engine code and is host-CI sugar
anyway. The current log is the newest ``*.md`` by mtime under ``sessions_dir``;
CI workflows should prefer ``check --session-log <file>`` with the card the
PR's diff touches, because a fresh checkout flattens every mtime to checkout
time and silently degrades the newest-by-mtime guess. Pure stdlib; returns the
missing markers rather than printing.
"""




def _marker_miss(marker: Mapping[str, str]) -> str:
    """Name one missed marker: its label AND the exact byte-form expected.

    ``Model line (expected `📊 Model:`)`` instead of a bare ``Model line`` —
    the run-1 ON-arm false-red lesson (idea
    model-line-checker-false-red-2026-07-09): a card visibly carrying a
    ``> **Model:**`` line red as "missing: Model line" tells the agent
    nothing about WHICH byte-form the needle scan wanted. A red must name
    the expected form, never contradict what the agent can see on the card.
    """
    label = marker.get("label", "?") or "?"
    needle = marker.get("needle", "")
    return f"{label} (expected `{needle}`)" if needle else label


def missing_markers(text: str, markers: Sequence[Mapping[str, str]]) -> list[str]:
    """Return, for each marker whose needle is absent from ``text``, its
    label plus the expected byte-form (see :func:`_marker_miss`).

    Tolerant of partial host-config entries: a marker without a ``needle`` is
    skipped (nothing to search for) rather than raising, and a missing
    ``label`` reports as ``"?"``.
    """
    lower = text.lower()
    return [
        _marker_miss(m)
        for m in markers
        if m.get("needle") and m.get("needle", "").lower() not in lower
    ]


def latest_session_log(sessions_dir: Path) -> Path | None:
    """Best guess at this session's log: newest ``*.md`` by mtime (skip README)."""
    if not sessions_dir.is_dir():
        return None
    candidates = [p for p in sessions_dir.glob("*.md") if p.name != "README.md"]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


# Status-badge values that mean "this session is not finished yet". A card
# carrying one is INCOMPLETE even when every marker needle is present — the
# born-red discipline checks the status VALUE, not just the badge's presence.
# (KL-1 lesson, kit repo PR #9: a reopened card kept its idea/review markers
# from the previous PR, so a presence-only check read born-red as green and
# auto-merge landed the PR without its close-out.) ``drafted`` is the
# auto-draft state (KL-5): an auto-drafted skeleton is real write-back but
# not a finished session — drafted holds the gate exactly like born-red.
IN_PROGRESS_TOKENS = ("in-progress", "in progress", "wip", "hold", "drafted")

# The auto-draft judgment-slot opener (KL-5). Drafted text marks every field
# only the session can fill with ``[[fill: <hint>]]``; a card still carrying
# one is DRAFTED, not completed — a distinct, mechanically countable state
# between "nothing written" (the twice-measured Phase-2.5 baseline) and a
# genuine close-out. The needle-based markers may all be present in a draft
# (the stand-ins carry them on purpose), so this token is what keeps an
# unedited draft from counting complete.
DRAFT_FILL_TOKEN = "[[fill:"

# Inline code spans + fenced blocks are stripped before counting: a card
# whose prose *mentions* the token (`[[fill:]]` in backticks — session cards
# about the draft mechanism legitimately do) is not an unresolved slot; the
# draft always writes real slots bare.
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def unresolved_fill_count(text: str) -> int:
    """Return how many auto-draft ``[[fill:]]`` slots remain in ``text``.

    Counts only slots outside inline code spans and fenced code blocks —
    prose that *talks about* the token doesn't hold the gate.
    """
    stripped = _CODE_SPAN_RE.sub("", _FENCE_RE.sub("", text))
    return stripped.count(DRAFT_FILL_TOKEN)


def status_in_progress(text: str) -> bool:
    """True when the log's Status badge line carries an in-progress value."""
    for line in text.splitlines():
        if "**status:**" in line.lower():
            lowered = line.lower()
            return any(token in lowered for token in IN_PROGRESS_TOKENS)
    return False


def check_log(path: Path, markers: Sequence[Mapping[str, str]]) -> list[str]:
    """Return what keeps one log file from counting complete (all if unreadable).

    Three conditions feed the list: marker needles that are absent, a Status
    badge still carrying an in-progress value, and unresolved auto-draft
    ``[[fill:]]`` slots (the drafted-vs-completed distinction, KL-5 — a
    drafted card is named as drafted, never mistaken for a finished one).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [_marker_miss(m) for m in markers]
    missing = missing_markers(text, markers)
    fills = unresolved_fill_count(text)
    if fills:
        missing.append(
            f"{fills} auto-draft [[fill:]] slot(s) unresolved "
            "(the card is drafted, not completed)",
        )
    if status_in_progress(text):
        missing.append("a completed Status (badge still says in-progress)")
    return missing

# --- engine/checks/check_namespace.py ---
"""Portable namespace / shadowing guard (Lane B6, the Q-0200 class).

Three AST-level checks over the Python roots a host configures
(``config.namespace``):

  1. **in-module shadowing** — the same top-level ``def`` / ``class`` name
     bound twice in one module; the later binding silently wins and the
     earlier one dies unnoticed (superbot's ``round_composition`` collision,
     caught only at CI).
  2. **cross-module collision** — the same public (non-underscore) top-level
     name defined in two modules of one package, unless one of the two is the
     package's ``__init__.py`` (the deliberate re-export pattern).
  3. **reserved names** — a name from the configured reserved map
     (``{"Name": "canonical/module.py"}``) defined outside its canonical
     module.

Uses only stdlib ``ast``; a file that fails to parse becomes a
``namespace-parse`` finding, never an exception. Findings reuse the
``Finding`` record from ``engine.checks.check_docs`` with paths relative to
the scanned root where possible.
"""




_NS_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _ns_rel(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` (posix) when possible, else str."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _ns_py_files(root: Path) -> list[Path]:
    """Return the ``*.py`` files under ``root`` (or ``root`` itself if a file)."""
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _ns_top_level_defs(tree: ast.Module) -> list[tuple[str, int]]:
    """Return ``(name, lineno)`` for every top-level def/class in ``tree``."""
    return [
        (node.name, node.lineno)
        for node in tree.body
        if isinstance(node, _NS_DEF_NODES)
    ]


def _ns_overloaded_names(tree: ast.Module) -> set[str]:
    """Names whose top-level defs carry ``@overload`` — not shadowing.

    ``@typing.overload`` stacks re-bind the same name by design; flagging them
    as in-module shadowing was a verified false positive.
    """
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if (
                isinstance(deco, ast.Name)
                and deco.id == "overload"
                or isinstance(deco, ast.Attribute)
                and deco.attr == "overload"
            ):
                names.add(node.name)
    return names


def _ns_dispatch_registered_names(tree: ast.Module) -> set[str]:
    """Names whose top-level defs carry ``@<x>.register`` — not shadowing.

    The ``functools.singledispatch`` idiom re-binds the same name (canonically
    ``def _``) once per registered type; the ``.register`` decorator captures
    each function, so the last global binding is irrelevant. Flagging the
    repeated defs as in-module shadowing was a verified false positive.
    Handles both ``@process.register`` and ``@process.register(int)``.
    """
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            target = deco.func if isinstance(deco, ast.Call) else deco
            if isinstance(target, ast.Attribute) and target.attr == "register":
                names.add(node.name)
    return names


def _ns_matches_canonical(rel: str, canonical: str) -> bool:
    """True when the scanned relpath is the reserved name's canonical module."""
    canon = canonical.replace("\\", "/").lstrip("./")
    return rel == canon or rel.endswith(f"/{canon}")


def check_namespace(
    roots: list[Path],
    *,
    reserved: dict[str, str] | None = None,
) -> list[Finding]:
    """Run the three namespace checks over ``roots``; return the findings.

    ``reserved`` maps a name to the canonical module relpath allowed to define
    it. Kinds: ``namespace`` for collisions, ``namespace-parse`` for files
    that fail to parse (reported, never raised).
    """
    reserved = reserved or {}
    findings: list[Finding] = []
    # (package dir, public name) -> [(rel, module filename, lineno)]
    package_defs: dict[tuple[str, str], list[tuple[str, str, int]]] = {}

    for root in roots:
        rel_base = root.parent if root.is_file() else root
        for py in _ns_py_files(root):
            rel = _ns_rel(py, rel_base)
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, ValueError, OSError, UnicodeDecodeError) as exc:
                lineno = getattr(exc, "lineno", None)
                where = f"L{lineno}: " if lineno else ""
                msg = f"{where}failed to parse: {exc.__class__.__name__}: {exc}"
                findings.append(Finding(rel, "namespace-parse", msg))
                continue

            seen: dict[str, int] = {}
            # `_` is the conventional throwaway (and the canonical
            # singledispatch register target); `.register`-decorated defs are
            # the named-function dispatch form — neither is real shadowing.
            exempt_shadow = _ns_overloaded_names(tree)
            exempt_shadow |= _ns_dispatch_registered_names(tree)
            for name, lineno in _ns_top_level_defs(tree):
                if name in seen and name not in exempt_shadow and name != "_":
                    msg = (
                        f"`{name}` defined twice in one module "
                        f"(L{seen[name]} and L{lineno}) — the later def "
                        "silently shadows the earlier"
                    )
                    findings.append(Finding(rel, "namespace", msg))
                seen.setdefault(name, lineno)
                if not name.startswith("_"):
                    key = (py.parent.resolve().as_posix(), name)
                    package_defs.setdefault(key, []).append(
                        (rel, py.name, lineno),
                    )
                canonical = reserved.get(name)
                if canonical is not None and not _ns_matches_canonical(
                    rel,
                    canonical,
                ):
                    msg = (
                        f"L{lineno}: reserved name `{name}` defined outside "
                        f"its canonical module `{canonical}`"
                    )
                    findings.append(Finding(rel, "namespace", msg))

    for (_, name), sites in sorted(package_defs.items()):
        modules = {filename for _, filename, _ in sites}
        non_init = [s for s in sites if s[1] != "__init__.py"]
        if len(modules) < 2 or len({s[1] for s in non_init}) < 2:
            continue  # one module, or an __init__ re-export pair
        site_list = ", ".join(f"{rel}:L{lineno}" for rel, _, lineno in non_init)
        msg = (
            f"public name `{name}` defined in multiple modules of one "
            f"package ({site_list}) — rename or move to a shared home"
        )
        findings.append(Finding(non_init[0][0], "namespace", msg))
    return findings

# --- engine/checks/check_seam_authority.py ---
r"""Config-driven seam-authority fences (Lane B6).

A *seam* is a boundary the host declares in ``config.seams`` — "all writes go
through the mutation service", "no direct pool access outside the db layer" —
generalising superbot's hardcoded architecture fences into pure data. Each
seam is a dict::

    {"name": "db-seam",
     "paths": ["src/**/*.py"],        # globs to scan, relative to root
     "forbidden": "pool\\.execute",   # regex; a hit is a violation
     "allowed": ["src/db/**"],        # exempt globs (the seam's own home)
     "message": "call db.* helpers, never the pool directly"}

The scan is plain line-by-line text matching (no AST, no imports) so it works
on any language the host points it at. A regex hit in a non-exempt file
becomes a ``Finding(kind="seam")`` whose message carries the seam name, the
configured message, and the line number. Findings reuse the ``Finding``
record from ``engine.checks.check_docs``; unreadable/binary files are skipped.
"""





def _seam_files(root: Path, globs: list[str]) -> list[Path]:
    """Return the de-duplicated files matched by ``globs`` under ``root``."""
    matched: set[Path] = set()
    for pattern in globs:
        for candidate in root.glob(pattern):
            if candidate.is_file():
                matched.add(candidate)
    return sorted(matched)


def _seam_exempt_files(root: Path, allowed: list[str]) -> set[Path]:
    """Resolve the exempt set with the SAME glob semantics as ``paths``.

    fnmatch let ``*`` cross ``/`` — an ``allowed`` pattern like ``src/*``
    silently exempted ``src/sub/hack.py`` and opened a fence gap. Re-globbing
    with ``root.glob`` keeps both sides of the seam on pathlib semantics.

    A glob hit that is a *directory* is expanded to the files under it — a
    trailing ``**`` (the documented ``src/db/**`` "own home" form) matches only
    directories in ``Path.glob``, so exempting by raw glob hits compared the
    file being scanned against a set of dirs and exempted **nothing**: a seam
    flagged its own home. Directory hits now contribute their whole file
    subtree (the ``economy`` reference-scan idiom), so ``src/db/**``,
    ``src/db/*`` and ``src/db/**/*`` all exempt the subtree as documented.
    """
    exempt: set[Path] = set()
    for pattern in allowed:
        for hit in root.glob(pattern):
            if hit.is_file():
                exempt.add(hit)
            elif hit.is_dir():
                exempt.update(p for p in hit.rglob("*") if p.is_file())
    return exempt


def check_seam_authority(root: Path, seams: list[dict]) -> list[Finding]:
    """Scan the configured seams under ``root``; return the violations.

    Each seam dict supplies ``name``, ``paths`` (globs to scan), ``forbidden``
    (a regex), optional ``allowed`` (exempt globs), and ``message``. A seam
    with an invalid regex is itself reported as a finding rather than raising
    (a broken fence should fail loud in the report, not crash the check).
    """
    findings: list[Finding] = []
    for seam in seams:
        name = seam.get("name", "unnamed")
        message = seam.get("message", "forbidden pattern")
        pattern = seam.get("forbidden", "")
        if not pattern:
            # An empty pattern's ``.search`` matches every line — a seam with no
            # ``forbidden`` would flag every line of every in-scope file. That is
            # a misconfiguration; report it loud instead of drowning the report.
            msg = f"seam `{name}`: no `forbidden` regex configured — seam skipped"
            findings.append(Finding("", "seam", msg))
            continue
        try:
            forbidden = re.compile(pattern)
        except re.error as exc:
            msg = f"seam `{name}`: invalid forbidden regex: {exc}"
            findings.append(Finding("", "seam", msg))
            continue
        exempt = _seam_exempt_files(root, list(seam.get("allowed", [])))
        for path in _seam_files(root, list(seam.get("paths", []))):
            rel = path.relative_to(root).as_posix()
            if path in exempt:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if forbidden.search(line):
                    msg = f"L{lineno}: seam `{name}`: {message}"
                    findings.append(Finding(rel, "seam", msg))
    return findings

# --- engine/checks/check_orientation_budget.py ---
"""Orientation-budget gate — the K0 <=7,000-word boot-read cap (Lane B6).

Orientation cost is the tax every session pays before real work starts, so
the kit meters it: the *boot set* (``config.orientation["boot_docs"]``,
falling back to ``config.readpath_docs`` when empty) must total no more than
``config.orientation["budget_words"]`` words. Boot-doc entries name files
under ``docs_root``; an entry containing ``/`` resolves from the project root
instead, so hosts can meter root-level docs (a journal, a CLAUDE.md) too.

Per-doc self-caps ride on top: a doc whose first 12 lines declare
``substrate-budget: N words`` is individually capped at N — a living doc can
pin its own growth ceiling without touching config.

Finding kinds: ``orientation-missing`` (a boot doc is absent),
``orientation-budget`` (the total blows the budget), ``orientation-doc-cap``
(a self-capped doc outgrew its declared cap). Findings reuse the ``Finding``
record from ``engine.checks.check_docs``.
"""




# `substrate-budget: 500 words` — the per-doc self-cap declaration.
_OB_SELF_CAP_RE = re.compile(r"substrate-budget:\s*(\d+)\s*words", re.IGNORECASE)
_OB_HEAD_LINES = 12
_OB_TOTAL_KEY = "_total"


def _ob_word_count(path: Path) -> int | None:
    """Return the doc's word count, or ``None`` when it cannot be read."""
    try:
        return len(path.read_text(encoding="utf-8").split())
    except (OSError, UnicodeDecodeError):
        return None


def _ob_self_cap(path: Path) -> int | None:
    """Return the doc's declared self-cap from its first 12 lines, if any."""
    try:
        head = path.read_text(encoding="utf-8").splitlines()[:_OB_HEAD_LINES]
    except (OSError, UnicodeDecodeError):
        return None
    match = _OB_SELF_CAP_RE.search("\n".join(head))
    return int(match.group(1)) if match else None


def _ob_rel(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` (posix) when possible, else str."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def orientation_word_count(root: Path, boot_docs: list[Path]) -> dict[str, int]:
    """Return per-doc word counts plus a ``_total`` for the boot set.

    Keys are paths relative to ``root`` where possible. A missing or
    unreadable doc counts 0 here — ``check_orientation_budget`` is the layer
    that reports it.
    """
    counts: dict[str, int] = {}
    total = 0
    for doc in boot_docs:
        words = _ob_word_count(doc) or 0
        counts[_ob_rel(doc, root)] = words
        total += words
    counts[_OB_TOTAL_KEY] = total
    return counts


def _ob_boot_paths(root: Path, config: Config) -> list[Path]:
    """Resolve the configured boot set to concrete paths.

    Explicit ``orientation["boot_docs"]`` entries: a bare name resolves under
    ``docs_root``, an entry with ``/`` resolves from the project root. The
    ``readpath_docs`` fallback resolves under ``docs_root`` unconditionally —
    matching ``check_reachable``, which reads the same key.
    """
    orientation = config.orientation or {}
    docs_root = root / config.docs_root
    explicit = list(orientation.get("boot_docs") or [])
    if explicit:
        # Explicit boot docs: a bare name resolves under docs_root, an entry
        # with "/" resolves from the project root (CONSTITUTION.md etc.).
        return [root / e if "/" in e else docs_root / e for e in explicit]
    # readpath_docs fallback: resolve under docs_root unconditionally, matching
    # check_reachable — the two consumers of that key must agree.
    return [docs_root / e for e in config.readpath_docs]


def check_orientation_budget(root: Path, config: Config) -> list[Finding]:
    """Meter the boot-read set against the orientation budget.

    Reports missing boot docs (``orientation-missing``), a total word count
    over ``orientation["budget_words"]`` (``orientation-budget``), and any doc
    that outgrew its own ``substrate-budget: N words`` self-cap
    (``orientation-doc-cap``).
    """
    findings: list[Finding] = []
    boot_paths = _ob_boot_paths(root, config)
    for doc in boot_paths:
        if not doc.is_file():
            msg = "boot doc missing — fix the path or the orientation config"
            findings.append(Finding(_ob_rel(doc, root), "orientation-missing", msg))

    counts = orientation_word_count(root, boot_paths)
    budget = int((config.orientation or {}).get("budget_words", 7000))
    total = counts[_OB_TOTAL_KEY]
    if total > budget:
        msg = (
            f"boot-read set totals {total} words, over the "
            f"{budget}-word orientation budget — trim or demote a boot doc"
        )
        findings.append(Finding(_OB_TOTAL_KEY, "orientation-budget", msg))

    for doc in boot_paths:
        cap = _ob_self_cap(doc)
        if cap is None:
            continue
        words = counts.get(_ob_rel(doc, root), 0)
        if words > cap:
            msg = f"doc is {words} words, over its {cap}-word self-cap"
            findings.append(Finding(_ob_rel(doc, root), "orientation-doc-cap", msg))
    return findings

# --- engine/checks/check_status_current.py ---
"""Status-freshness checker — the ``control/`` heartbeat(s) must exist and beat.

Why + provenance: the fleet coordination protocol (canonical spec: superbot
``docs/planning/fleet-coordination-protocol-2026-07-09.md``; kit band KL-8,
inbox ORDER 002) makes ``control/status.md`` each Project's heartbeat — the
manager treats a stale status as a **dark** Project. The protocol's whole
value collapses if a Project silently stops writing it, so the discipline is
enforced, not exhorted (PL-007), exactly like the session-card gate.

Multi-Project repos (inbox ORDER 004): a SHARED repo hosting several
Projects keeps one heartbeat file *per lane* (the superbot-games pattern —
``control/status-mining.md`` + ``control/status-exploration.md``), preserving
one-writer-per-file per lane. The validated path set is therefore
**configurable**: ``substrate.config.json`` → ``heartbeat_files`` (default
``["control/status.md"]``); every listed heartbeat is checked independently
and each finding names its own file. Callers pass the configured list via
``status_files``; unset/empty falls back to the single-file default (a
misconfiguration must not silently disable the gate).

Two postures, deliberately split (the spec's "warns → graduates to the
born-red post-adopt gate" wording, resolved so a *required CI check* never
reds on wall-clock time alone):

- **Gate findings** (ride the ordinary strict finding loop — RED under
  ``check --strict``): *static, deterministic* protocol states —
  ``status-missing`` (the control bus exists but a configured heartbeat file
  doesn't) and ``status-no-heartbeat`` (the file is still the adopt-time
  seed, or carries no parseable ``updated:`` ISO-8601 line). These are the
  born-red graduation: an adopted host stays red until its first real
  heartbeat, the same shape as ``session-loop-idle``.
- **Advisory findings** (warn-only — emitted + telemetry-recorded, **never**
  exit-affecting): ``status-stale`` — the heartbeat parses but is older than
  ``max_age_hours`` (default 72h). Time-based red in a required check would
  be a bomb: an untouched-for-a-week repo's next unrelated PR would arrive
  pre-reddened. The warning still surfaces in every ``check`` run and the
  Stop hook separately nags when no heartbeat file was overwritten this
  session (``hooks/stop_check.py``).

Input-gated like every checker: engages only when the protocol is present
(any ``control/{README,inbox}.md`` or configured heartbeat file exists) — a
host that never adopted the bus adds nothing here. Stdlib only; unreadable
files fail open.
"""




CONTROL_DIR = "control"
STATUS_RELPATH = "control/status.md"
INBOX_RELPATH = "control/inbox.md"
CONTROL_README_RELPATH = "control/README.md"

# The manager's stale-= -dark horizon. Wider than the self-poll cadence the
# spec suggests (2-4h) on purpose: the checker warns about *abandonment*, not
# about a quiet afternoon — revise with data (KF-8 posture).
DEFAULT_MAX_AGE_HOURS = 72

_UPDATED_RE = re.compile(r"^updated:\s*(\S+)", re.MULTILINE)


def parse_heartbeat(text: str) -> datetime | None:
    """Return the ``updated:`` line's timestamp as an aware UTC datetime.

    Accepts the contract's ISO-8601 shapes (``2026-07-09T12:07Z``,
    ``...T12:07:00+00:00``, minutes or seconds precision). A trailing ``Z``
    is normalized for ``fromisoformat`` (Python 3.10 floor). A naive
    timestamp is taken as UTC — the contract says ISO8601, sessions write
    UTC, and treating it otherwise would fabricate staleness. None when the
    line is absent or unparseable (the adopt seed's prose sentinel lands
    here by design).
    """
    match = _UPDATED_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def heartbeat_relpaths(status_files: Sequence[str] | None) -> list[str]:
    """Normalize the configured heartbeat list (unset/empty → the default).

    The fallback-on-empty is deliberate: a stray ``"heartbeat_files": []``
    must degrade to the protocol's single-file default, never silently
    disable the gate (same fail-safe instinct as the fast lane's
    empty-diff-runs-the-full-suite rule).
    """
    files = [str(rel) for rel in (status_files or []) if str(rel).strip()]
    return files or [STATUS_RELPATH]


def _control_present(target: Path, status_relpaths: Sequence[str]) -> bool:
    """True when the control bus exists (any protocol/heartbeat file)."""
    candidates = [INBOX_RELPATH, CONTROL_README_RELPATH, *status_relpaths]
    return any((target / rel).is_file() for rel in candidates)


def _check_one_status(
    target: Path,
    rel: str,
    *,
    now: datetime,
    max_age_hours: int,
) -> tuple[list[Finding], list[Finding]]:
    """Return ``(gate, advisory)`` findings for one heartbeat file ``rel``."""
    status_path = target / rel
    if not status_path.is_file():
        return (
            [
                Finding(
                    rel,
                    "status-missing",
                    f"the control/ bus exists but {rel} doesn't — the "
                    "manager reads this file as your heartbeat; write it "
                    "(format: control/README.md).",
                ),
            ],
            [],
        )
    try:
        text = status_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], []  # fail open — an unreadable file is not a verdict
    heartbeat = parse_heartbeat(text)
    if heartbeat is None:
        return (
            [
                Finding(
                    rel,
                    "status-no-heartbeat",
                    "no parseable `updated:` ISO-8601 heartbeat — still the "
                    "adopt seed? Overwrite the whole file with your real "
                    "status as the session's LAST step (control/README.md).",
                ),
            ],
            [],
        )
    age = now - heartbeat
    if age > timedelta(hours=max_age_hours):
        hours = int(age.total_seconds() // 3600)
        return (
            [],
            [
                Finding(
                    rel,
                    "status-stale",
                    f"heartbeat is ~{hours}h old (> {max_age_hours}h) — the "
                    "manager treats a stale status as a DARK Project; "
                    f"overwrite {rel} this session.",
                ),
            ],
        )
    return [], []


def check_status_current(
    target: Path,
    *,
    now: datetime | None = None,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    status_files: Sequence[str] | None = None,
) -> tuple[list[Finding], list[Finding]]:
    """Return ``(gate_findings, advisory_findings)`` for ``target``'s heartbeat(s).

    Gate findings ride the strict finding loop (exit-affecting under
    ``--strict``); advisory findings are surfaced + telemetry-recorded but
    must never touch the exit code (see module docstring). Both lists are
    empty when the ``control/`` protocol is absent. ``status_files`` is the
    host's configured heartbeat list (``Config.heartbeat_files``); each
    listed file is validated independently so a multi-Project repo gates
    every lane's heartbeat — unset/empty falls back to
    ``["control/status.md"]``.
    """
    relpaths = heartbeat_relpaths(status_files)
    if not _control_present(target, relpaths):
        return [], []
    current = now or datetime.now(timezone.utc)
    gate: list[Finding] = []
    advisory: list[Finding] = []
    for rel in relpaths:
        one_gate, one_advisory = _check_one_status(
            target,
            rel,
            now=current,
            max_age_hours=max_age_hours,
        )
        gate += one_gate
        advisory += one_advisory
    return gate, advisory

# --- engine/checks/check_owner_actions.py ---
"""Owner-action quality checker — ⚑ needs-owner asks must be actionable.

Why + provenance: the owner-action quality band (inbox ORDER 008, owner
directive 2026-07-09). Agents' ``⚑ needs-owner`` items were too often
(a) unnecessary — based on assumed walls nobody actually hit — or
(b) phrased so a non-technical owner couldn't act on them directly. The
owner is the scarcest resource in the program; every unclear or
unnecessary ask burns attention and stalls the asking lane. The contract
(canonical: ``control/README.md`` § the OWNER-ACTION item format) gives
every ask six REQUIRED fields:

- ``WHAT`` — one plain sentence, zero jargon
- ``WHERE`` — exact click path or URL
- ``HOW`` — paste-ready text/values where applicable
- ``WHY-IT-MATTERS`` — one sentence in product terms
- ``UNBLOCKS`` — what starts moving the moment it's done
- ``VERIFIED-NEEDED`` — the attempt made + the exact error/wall proving
  only the owner can do this (assumption-based asks are banned)

Posture: **advisory-only, never exit-affecting** — the deliberate mirror
of ``check_status_current``'s staleness warning. Existing adopters carry
free-text asks today; a gate would pre-redden every heartbeat the moment
this ships. The warning surfaces in every ``check`` run (both CI lanes —
the asks live in the heartbeat files the control fast lane already
validates) and the ``session-close`` skill asks the same question at close;
migration pressure without a locked door.

Detection is deliberately coarse (one finding per heartbeat file naming
the absent field labels, scanning the whole file so inline items and
linked blocks both count): the point is a nudge toward the format, not a
parser for every free-text shape an ask can take. Input-gated like every
checker — engages only when the ``control/`` protocol is present and the
file's ``⚑ needs-owner`` value is something other than ``none``. Stdlib
only; unreadable files fail open.
"""




# The six REQUIRED field labels (ORDER 008), canonical spelling first.
# VERIFIED-NEEDED is the band's heart — the attempted-or-exact-wall proof
# that kills assumption-based asks. The canonical labels match the shipped
# templates and control/README.md § OWNER-ACTION format exactly (checker and
# templates agree). Two fields also accept a shorthand spelling adopters
# write inline — WHY:/VERIFIED-WHEN: — because accepting an alternate only
# ever *withholds* this advisory nag (never adds one), so it stays
# backward-compatible and never newly reddens a valid ledger.
OWNER_ACTION_FIELDS = (
    ("WHAT:",),
    ("WHERE:",),
    ("HOW:",),
    ("WHY-IT-MATTERS:", "WHY:"),
    ("UNBLOCKS:",),
    ("VERIFIED-NEEDED:", "VERIFIED-WHEN:"),
)

NEEDS_OWNER_TOKEN = "⚑ needs-owner"


def _needs_owner_value(text: str) -> str | None:
    """Return the ``⚑ needs-owner`` value, or None when the line is absent.

    The heartbeat contract writes one ``⚑ needs-owner: <...>`` line; the
    value is everything after the first colon following the token. Only the
    first occurrence counts — the format block in a README copy would
    otherwise self-trigger.
    """
    idx = text.find(NEEDS_OWNER_TOKEN)
    if idx == -1:
        return None
    line = text[idx:].splitlines()[0]
    _, _, value = line.partition(":")
    return value.strip()


def check_owner_actions(
    target: Path,
    *,
    status_files: Sequence[str] | None = None,
) -> list[Finding]:
    """Return advisory findings for unstructured ⚑ needs-owner asks.

    One ``owner-action-fields`` finding per configured heartbeat file whose
    ``⚑ needs-owner`` value is present and not ``none`` while the file lacks
    one or more OWNER-ACTION field labels (the whole file is scanned, so an
    inline item and a structured block below the list both satisfy the
    contract). Advisory by contract: callers must never count these toward
    an exit code (see module docstring). Empty when the ``control/``
    protocol is absent.
    """
    relpaths = heartbeat_relpaths(status_files)
    control_evidence = [INBOX_RELPATH, CONTROL_README_RELPATH, *relpaths]
    if not any((target / rel).is_file() for rel in control_evidence):
        return []
    findings: list[Finding] = []
    for rel in relpaths:
        path = target / rel
        if not path.is_file():
            continue  # missing heartbeat is check_status_current's finding
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # fail open — an unreadable file is not a verdict
        value = _needs_owner_value(text)
        if value is None or value.lower().startswith("none") or not value:
            continue
        missing = [
            alts[0].rstrip(":")
            for alts in OWNER_ACTION_FIELDS
            if not any(alt in text for alt in alts)
        ]
        if missing:
            findings.append(
                Finding(
                    rel,
                    "owner-action-fields",
                    "⚑ needs-owner carries asks without the OWNER-ACTION "
                    f"fields (missing: {', '.join(missing)}) — the owner is "
                    "the scarcest resource: structure each ask per "
                    "control/README.md § OWNER-ACTION format (attempt it "
                    "yourself or cite the exact wall — VERIFIED-NEEDED; "
                    "assumption-based asks are banned), and withdraw stale "
                    "asks.",
                ),
            )
    return findings

# --- engine/checks/check_inbox_append.py ---
"""Inbox append-only gate — ``control/inbox.md`` may only grow, ORDER-shaped.

Why + provenance: the fleet coordination protocol (``control/README.md``)
makes ``control/inbox.md`` the manager's ORDER bus with **one writer** and an
**append-only** law — but that law was convention-only, enforced by nothing.
The fleet adoption review 2026-07-09 (issue #36, report 2) proved the gap
live: PR #34 (an ORDER 003 append) merged 19 s after it opened on the CI
control fast lane, with zero validation that the change was pure-append, that
existing ORDERs were untouched, or that the appended text was even a valid
ORDER block. Any session could silently rewrite or erase orders on a green
control-only PR.

This checker closes the LAW half (PL-007, "enforce, don't exhort"): a change
to ``control/inbox.md`` must be **PURE-APPEND** vs the merge-base — the base
file's bytes are a *prefix* of the new file (existing bytes unchanged,
additions only at/after the end) — and the appended text must follow the
ORDER-block grammar (``control/README.md`` → "inbox.md order format"). Writer
IDENTITY is deliberately NOT enforced: on a single-account program it is not
enforceable in-repo (issue #36 report 2, stated honestly in the protocol
doc); this gate enforces the part of the law that lives in the bytes.

Diff access without shelling out: engine code is pure stdlib — ``subprocess``
is banned (§3.2). So, exactly like the session-log gate, CI does the git work
in bash (extract the merge-base blob of ``control/inbox.md`` to a file) and
hands the path in via ``check --inbox-base <file>``; this checker only reads
two files and compares them. No base path (a local ``check`` with no diff
context, or the file/base absent) → **no-op**, the same fail-open posture as
the mtime session-log fallback. It engages only when there is a real diff to
judge, so ``check`` stays meaningful on a tree with no inbox change.
"""




# The ORDER header grammar (control/README.md "inbox.md order format"):
#   ## ORDER <nnn> · <ISO8601> · status: <state>     [# optional manager note]
# The `·` is U+00B7 (the protocol's separator). A trailing `#` note is allowed
# (the README's own example carries one), so the value is the first token.
_ORDER_HEADER_PREFIX = "## ORDER "
_ORDER_HEADER_RE = re.compile(r"^## ORDER \S+ · .+ · status: \S+")

# Every ORDER block carries these fields (control/README.md order format).
_REQUIRED_FIELDS = ("priority:", "do:", "why:", "done-when:")


def _order_grammar_findings(appended: str) -> list[Finding]:
    """Return grammar findings for the ``appended`` region of the inbox.

    The region is either the freshly appended ORDER block(s) (normal append)
    or — when the change *created* the file — its whole body, which may open
    with the file header (a ``#`` title + a ``>`` blockquote intro). Content
    before the first ``## ORDER`` header is allowed only if it is that header
    (blank / ``#`` / ``>`` lines); anything else is stray. Each ORDER block is
    validated for a well-formed header and the four required fields.
    """
    lines = appended.splitlines()
    header_idxs = [i for i, ln in enumerate(lines) if ln.startswith(_ORDER_HEADER_PREFIX)]
    findings: list[Finding] = []

    preamble_end = header_idxs[0] if header_idxs else len(lines)
    for ln in lines[:preamble_end]:
        stripped = ln.strip()
        if stripped and not stripped.startswith(("#", ">")):
            findings.append(
                Finding(
                    INBOX_RELPATH,
                    "inbox-order-grammar",
                    "appended content that is neither the file header nor a "
                    "`## ORDER` block — the inbox appends ORDER blocks only "
                    "(control/README.md order format).",
                ),
            )
            break

    bounds = header_idxs + [len(lines)]
    for b in range(len(header_idxs)):
        block = lines[bounds[b] : bounds[b + 1]]
        findings += _validate_block(block)
    return findings


def _validate_block(block: list[str]) -> list[Finding]:
    """Return findings for one ORDER block (header line through its body)."""
    header = block[0]
    if not _ORDER_HEADER_RE.match(header):
        return [
            Finding(
                INBOX_RELPATH,
                "inbox-order-grammar",
                f"malformed ORDER header {header.strip()!r} — expected "
                "`## ORDER <nnn> · <ISO8601> · status: <state>` "
                "(control/README.md order format).",
            ),
        ]
    missing = [
        field
        for field in _REQUIRED_FIELDS
        if not any(ln.lstrip().startswith(field) for ln in block[1:])
    ]
    if missing:
        label = header.strip()
        return [
            Finding(
                INBOX_RELPATH,
                "inbox-order-grammar",
                f"{label!r} is missing required field(s): {', '.join(missing)} "
                "— every order carries priority/do/why/done-when "
                "(control/README.md order format).",
            ),
        ]
    return []


def check_inbox_append(target: Path, base_path: Path) -> list[Finding]:
    """Return the append-only findings for ``target``'s ``control/inbox.md``.

    ``base_path`` is the merge-base version of the file, extracted by CI (the
    engine never shells out to git). Empty list means the change is a legal
    pure-append of well-formed ORDER block(s) — or there is nothing to judge
    (inbox or base absent/unreadable → fail open, like every other checker).
    """
    inbox = target / INBOX_RELPATH
    base = Path(base_path)
    if not inbox.is_file() or not base.is_file():
        return []
    try:
        new_text = inbox.read_text(encoding="utf-8")
        old_text = base.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []  # fail open — an unreadable file is not a verdict

    if not new_text.startswith(old_text):
        # The append-only law is violated the instant the old bytes are no
        # longer a prefix: an existing ORDER line was edited, reordered, or
        # deleted. Grammar of the "appended" tail is meaningless here.
        return [
            Finding(
                INBOX_RELPATH,
                "inbox-not-append",
                "control/inbox.md changed non-append vs the merge-base — the "
                "one-writer/append-only law (control/README.md) allows only "
                "additions at the end; an existing ORDER was edited, "
                "reordered, or deleted. Restore the prior bytes verbatim and "
                "append your new ORDER block instead.",
            ),
        ]
    appended = new_text[len(old_text) :]
    return _order_grammar_findings(appended)

# --- engine/checks/check_claims.py ---
"""Claim-aware checker — order-claims must be unique and live (ORDER 007).

Why + provenance: the fleet coordination protocol (``control/README.md`` §
"Claiming an order") makes every ``new`` order single-executor. Before
building, a lane appends ``claimed-by: <order-ids> <lane-or-session>
<ISO8601>`` to the ``orders:`` line of its OWN heartbeat (``control/status*.md``)
and lands it on main FIRST — so two readers of the same ``status: new`` order
cannot both execute it. That convention was born from a realized failure, not
a theoretical one (substrate-kit PRs #50/#51: two lanes independently executed
the same ORDER 005 the same day, and a whole session's work had to be
reconciled as twins). But the convention shipped **doc-only** — enforced by
nothing. This checker closes the "enforce, don't exhort" gap for the claim
band, exactly as ``check_inbox_append`` did for the append-only law and
``check_owner_actions`` did for the OWNER-ACTION format.

What it flags (both **advisory** — a nudge, never a locked door, the same
posture as the staleness + owner-action warnings):

- ``claims-duplicate`` — two or more DISTINCT heartbeat files carry a
  ``claimed-by:`` naming the SAME order id. That is the twin-execution race
  itself: the tiebreak (earliest claim merged to main wins) is a human call,
  so the checker surfaces the collision rather than picking a winner.
- ``claims-stale`` — a live ``claimed-by:`` for an order that is (a) already
  reported in some lane's ``done=`` (the executor was meant to DROP the claim
  when moving the id into ``done=`` — a lingering claim on a done order is
  dead), or (b) older than the convention's ~24h abandonment horizon (a claim
  with no fresh activity "may be treated as abandoned and re-claimed"). The
  checker cannot see build activity from the status file alone, so the age
  finding is deliberately a *withdraw-or-refresh* nudge, not a verdict.

Posture is **advisory-only, never exit-affecting** — the deliberate mirror of
``check_owner_actions`` / ``check_status_current``'s staleness warning. Claims
are a coordination hint the manager reconciles; a hard gate would red a
required check on a race the checker can't adjudicate.

Input-gated on the ``control/`` protocol and per heartbeat file, like every
control-band checker. Pure stdlib — no ``subprocess`` (§3.2); it only reads the
heartbeat files the fast lane already validates. Unreadable / claim-less files
fail open (no verdict).
"""




# The convention's abandonment horizon (control/README.md § "Claims expire"):
# a claim with no visible activity after ~24h may be re-claimed. Seeded here,
# revisable by data (KF-8 posture), mirroring check_status_current's constant.
CLAIM_STALE_HOURS = 24

# The orders line carries the claim + the done ledger:
#   orders: acked=<ids> done=<ids> [claimed-by: <ids> <lane> <ISO8601>]
_ORDERS_RE = re.compile(r"^orders:\s*(.*)$", re.MULTILINE)
_DONE_RE = re.compile(r"\bdone=(\S*)")
# claimed-by: <ids> <lane-or-session> <ISO8601> — three whitespace tokens.
# The ids token is `+`/`,`-separated (README example: `007+008`); the lane may
# itself carry hyphens (`coordinator-lane`) so it is a whole token, not parsed.
_CLAIMED_RE = re.compile(r"claimed-by:\s*(\S+)\s+(\S+)\s+(\S+)")


def _norm_id(raw: str) -> str | None:
    """Return a 3-digit-normalized order id (``7`` / ``007`` → ``007``), or None."""
    token = raw.strip()
    if not token.isdigit():
        return None
    return f"{int(token):03d}"


def _expand_ids(token: str) -> set[str]:
    """Expand an id list token to a normalized id set.

    Handles the protocol's shapes: comma lists (``001,002``), ``+``-joined
    claim ids (``007+008``), and inclusive ranges (``001-006``). Unparseable
    fragments are skipped rather than crashing the scan.
    """
    ids: set[str] = set()
    for part in re.split(r"[,+]", token):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_raw, _, hi_raw = part.partition("-")
            lo, hi = lo_raw.strip(), hi_raw.strip()
            if lo.isdigit() and hi.isdigit():
                for n in range(int(lo), int(hi) + 1):
                    ids.add(f"{n:03d}")
                continue
        norm = _norm_id(part)
        if norm is not None:
            ids.add(norm)
    return ids


def _parse_iso(raw: str) -> datetime | None:
    """Parse a claim's ISO-8601 timestamp to an aware UTC datetime, or None.

    Mirrors ``check_status_current.parse_heartbeat``'s normalization: a
    trailing ``Z`` is rewritten for ``fromisoformat`` (Python 3.10 floor) and
    a naive stamp is read as UTC (the contract says ISO8601, sessions write
    UTC — treating it otherwise would fabricate staleness).
    """
    token = raw.strip()
    if token.endswith(("Z", "z")):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _orders_line(text: str) -> str | None:
    """Return the first ``orders:`` line's value, or None when absent."""
    match = _ORDERS_RE.search(text)
    return match.group(1) if match else None


def _done_ids(orders_value: str) -> set[str]:
    """Return the set of order ids reported in ``done=`` on an orders line."""
    match = _DONE_RE.search(orders_value)
    return _expand_ids(match.group(1)) if match else set()


def _claim(orders_value: str) -> tuple[set[str], str, datetime | None] | None:
    """Return ``(ids, lane, ts)`` for the line's ``claimed-by:``, or None.

    ``ids`` is the normalized claimed order-id set, ``lane`` the claimant
    token, ``ts`` the parsed timestamp (None when unparseable — the age check
    then simply skips, never fabricating staleness).
    """
    match = _CLAIMED_RE.search(orders_value)
    if not match:
        return None
    ids = _expand_ids(match.group(1))
    if not ids:
        return None
    return ids, match.group(2), _parse_iso(match.group(3))


def check_claims(
    target: Path,
    *,
    status_files: Sequence[str] | None = None,
    now: datetime | None = None,
) -> list[Finding]:
    """Return advisory findings for duplicate / stale order-claims.

    Scans every configured heartbeat file's ``orders:`` line for
    ``claimed-by:`` annotations (ORDER 007). Emits ``claims-duplicate`` when
    two distinct files claim one order id, and ``claims-stale`` when a live
    claim names an order already in some lane's ``done=`` or is older than
    ``CLAIM_STALE_HOURS``. Advisory by contract — callers must never count
    these toward an exit code (see module docstring). Empty when the
    ``control/`` protocol is absent, and fail-open on unreadable files.
    """
    relpaths = heartbeat_relpaths(status_files)
    control_evidence = [INBOX_RELPATH, CONTROL_README_RELPATH, *relpaths]
    if not any((target / rel).is_file() for rel in control_evidence):
        return []

    now = now or datetime.now(timezone.utc)
    # Per file: its claim (ids, lane, ts). Plus the union of every done= ledger
    # across lanes — an order done anywhere retires its claim everywhere.
    claims: dict[str, tuple[set[str], str, datetime | None]] = {}
    done_union: set[str] = set()
    for rel in relpaths:
        path = target / rel
        if not path.is_file():
            continue  # a missing heartbeat is check_status_current's finding
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # fail open — an unreadable file is not a verdict
        orders_value = _orders_line(text)
        if orders_value is None:
            continue
        done_union |= _done_ids(orders_value)
        claim = _claim(orders_value)
        if claim is not None:
            claims[rel] = claim

    findings: list[Finding] = []

    # DUPLICATE — one order id claimed by two or more distinct files.
    holders: dict[str, list[str]] = {}
    for rel, (ids, _lane, _ts) in claims.items():
        for oid in ids:
            holders.setdefault(oid, []).append(rel)
    for oid in sorted(holders):
        rels = sorted(holders[oid])
        if len(rels) < 2:
            continue
        who = ", ".join(f"{r} ({claims[r][1]})" for r in rels)
        for rel in rels:
            findings.append(
                Finding(
                    rel,
                    "claims-duplicate",
                    f"order {oid} is claimed by {len(rels)} lanes ({who}) — "
                    "the twin-execution race (control/README.md § Claiming an "
                    "order). Reconcile by the tiebreak (earliest claim merged "
                    "to main wins); the loser withdraws its claim and stands "
                    "down.",
                ),
            )

    # STALE — a live claim for a done order, or one past the ~24h horizon.
    for rel in sorted(claims):
        ids, _lane, ts = claims[rel]
        done_here = sorted(ids & done_union)
        if done_here:
            findings.append(
                Finding(
                    rel,
                    "claims-stale",
                    f"claim for order(s) {', '.join(done_here)} that already "
                    "appear in a lane's done= — the executor drops the "
                    "claimed-by annotation when moving ids into done= "
                    "(control/README.md § Claiming an order). Withdraw the "
                    "stale claim in your next heartbeat.",
                ),
            )
        if ts is not None:
            age_hours = (now - ts).total_seconds() / 3600
            if age_hours > CLAIM_STALE_HOURS:
                findings.append(
                    Finding(
                        rel,
                        "claims-stale",
                        f"claim for order(s) {', '.join(sorted(ids))} is "
                        f"{age_hours:.0f}h old (> {CLAIM_STALE_HOURS}h "
                        "abandonment horizon, control/README.md § Claims "
                        "expire) — refresh it with a fresh heartbeat / open PR "
                        "reference if still building, or withdraw it so the "
                        "order can be re-claimed.",
                    ),
                )
    return findings

# --- engine/checks/check_capability_xref.py ---
"""OWNER-ACTION ↔ CAPABILITIES cross-reference advisory (kit-lab queue item 8).

Why + provenance: the #68 session card's 💡 idea
(``.sessions/2026-07-09-order008.md``) — the OWNER-ACTION
``VERIFIED-NEEDED`` field (ORDER 008) and ``docs/CAPABILITIES.md`` (ORDER
006) are two halves of one loop that nothing closes: when an ask's
VERIFIED-NEEDED cites a technical wall that is NOT yet in the capability
ledger, the wall should be appended there in the same session (THE
DISCOVERY RULE step 4 — "an unrecorded discovery is re-paid by every
future session"); and a ledger entry that records the cited surface as a
verified WORKING capability means the ask may be resting on a wall that
has since fallen. This checker cross-references the two files and nudges
both ways, turning every owner-ask into a capability-ledger contribution
for free.

What it flags (both **advisory** — a nudge, never a locked door, the same
posture as ``check_claims`` / ``check_owner_actions``):

- ``owner-ask-wall-unrecorded`` — a wall-shaped OWNER-ACTION (its
  VERIFIED-NEEDED cites a technical block: a 403, an access-denied, an
  owner-only surface) whose wall the capability ledger does not record.
  The nudge: append the wall to the ledger this session.
- ``owner-ask-capability-resolved`` — a wall-shaped OWNER-ACTION whose
  cited surface the ledger records ONLY as a verified-working capability
  (no matching wall entry). The nudge: re-verify the ask — the wall may
  have fallen — and withdraw it or record the residual wall.

Detection is deliberately coarse, mirroring ``check_owner_actions``'s
posture note: VERIFIED-NEEDED texts are free prose, so the cross-check is
distinctive-token overlap against the ledger's Walls/Capabilities sections
(headings + tagged append-log entries), not a parser for every shape a
wall citation can take. Judgment-shaped asks (license calls, product
rulings — "product judgment", "not a technical wall") are out of the
ledger's scope and are skipped entirely; an ask with no wall marker at all
is skipped too. False nudges cost one glance; an unrecorded wall costs
every future session a rediscovery.

Posture is **advisory-only, never exit-affecting** — existing adopters
carry free-prose asks today, and token overlap can never be a verdict.
Input-gated on the ``control/`` protocol and per heartbeat file, like
every control-band checker. Pure stdlib — no ``subprocess`` (§3.2); it
only reads the heartbeat files the fast lane already validates plus the
planted capability ledger. Unreadable files fail open (no verdict).
"""




# Where adopt plants the capability ledger (src/engine/adopt.py PLANTED_DOCS:
# CAPABILITIES.md.tmpl → docs/CAPABILITIES.md) — same fixed relpath here.
CAPABILITIES_RELPATH = "docs/CAPABILITIES.md"

# An OWNER-ACTION block heading: `⚑ OWNER-ACTION <id> — <title>` (control/
# README.md § OWNER-ACTION format). The id token is free-form (`1`, `10`).
_OWNER_ACTION_RE = re.compile(r"^⚑ OWNER-ACTION\s+(\S+)[ \t]*(.*)$", re.MULTILINE)

# The ORDER 008 field labels, canonical + the shorthand spellings
# check_owner_actions accepts (#99 token alignment: WHY:/VERIFIED-WHEN:).
# _VERIFIED_LABELS locate the wall-evidence field; the rest bound its value.
_VERIFIED_LABELS = ("VERIFIED-NEEDED:", "VERIFIED-WHEN:")
_BOUNDARY_LABELS = (
    "WHAT:",
    "WHERE:",
    "HOW:",
    "WHY-IT-MATTERS:",
    "WHY:",
    "UNBLOCKS:",
)

# Wall-shaped evidence markers (lowercase substring match on VERIFIED-NEEDED):
# the hard-block vocabulary the ledger's Walls section exists to record.
_WALL_MARKERS = (
    "403",
    "denied",
    "refused",
    "blocked",
    "wall",
    "owner-only",
    "owner-click",
    "owner ui",
    "console ui",
    "no agent path",
    "no mcp",
)

# Judgment-shaped asks are OUT of the ledger's scope — a license choice or a
# rubric ruling is owner judgment by nature, not a technical wall to record.
_JUDGMENT_MARKERS = (
    "product judgment",
    "owner judgment",
    "not a technical wall",
    "legal",
)

# Generic tokens that would match any prose — excluded from anchor sets so
# overlap means the SAME surface, not the same register.
_STOPWORDS = frozenset(
    """
    about action actions after agent agents already also and any are because
    been before being between both but can cannot capability capabilities
    could did does doing done each either else enumerated environment error
    every exact exists file files for from had has have how into item items
    its itself may more most must need needed needs never none not nothing
    now one only other our out over own path paths per proves same section
    see session sessions should since some such than that the their them
    then there these they this those through today under until upon verified
    very wall walls was were what when where which while who whose will with
    would yet you your
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._/:\-]*")


def _tokens(text: str) -> set[str]:
    """Return the lowercase token set of ``text`` (ledger side — unfiltered)."""
    return {tok.strip("./:-_") for tok in _TOKEN_RE.findall(text.lower())}


def _anchors(text: str) -> set[str]:
    """Return the DISTINCTIVE token set of a VERIFIED-NEEDED value.

    A token anchors the cross-check only when it is specific enough that a
    match in the ledger plausibly means the same surface: it carries a digit
    or path/identifier punctuation, or is ≥ 6 chars — and is not a generic
    stopword. Short/common words never anchor (coarse by design, see the
    module docstring).
    """
    anchors: set[str] = set()
    for raw in _TOKEN_RE.findall(text.lower()):
        tok = raw.strip("./:-_")
        if len(tok) < 3 or tok in _STOPWORDS:
            continue
        if (
            any(ch.isdigit() for ch in tok)
            or any(ch in "./:-_" for ch in tok)
            or len(tok) >= 6
        ):
            anchors.add(tok)
    return anchors


def _owner_action_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return ``(id, title, block_text)`` per ⚑ OWNER-ACTION item in ``text``.

    A block runs from its heading to the next blank line, the next ``⚑``
    heading, or EOF — the shape the control heartbeat writes (fields on
    their own lines, blocks separated by blank lines).
    """
    blocks: list[tuple[str, str, str]] = []
    for match in _OWNER_ACTION_RE.finditer(text):
        start = match.start()
        blank = text.find("\n\n", match.end())
        nxt = text.find("\n⚑", match.end())
        ends = [pos for pos in (blank, nxt) if pos != -1]
        end = min(ends) if ends else len(text)
        blocks.append((match.group(1), match.group(2).strip(), text[start:end]))
    return blocks


def _verified_needed(block: str) -> str | None:
    """Return a block's VERIFIED-NEEDED value, or None when the field is absent.

    Accepts the canonical label and the VERIFIED-WHEN: shorthand (the #99
    token set check_owner_actions accepts). The value runs from the label to
    the next field label or the block's end (VERIFIED-NEEDED is last in the
    template order, but a reordered block still parses).
    """
    idx = -1
    label_len = 0
    for label in _VERIFIED_LABELS:
        pos = block.find(label)
        if pos != -1 and (idx == -1 or pos < idx):
            idx, label_len = pos, len(label)
    if idx == -1:
        return None
    value = block[idx + label_len :]
    cut = len(value)
    for label in _BOUNDARY_LABELS:
        pos = value.find(label)
        if pos != -1:
            cut = min(cut, pos)
    return value[:cut].strip()


def _is_wall_shaped(verified: str) -> bool:
    """True when a VERIFIED-NEEDED cites a technical wall (not owner judgment)."""
    lower = verified.lower()
    if any(marker in lower for marker in _JUDGMENT_MARKERS):
        return False
    return any(marker in lower for marker in _WALL_MARKERS)


def _ledger_sides(text: str) -> tuple[set[str], set[str]]:
    """Split the capability ledger into ``(wall_tokens, capability_tokens)``.

    Sections are keyed on the planted template's headings (``## Walls`` /
    ``## Capabilities``); append-log entries (``- YYYY-MM-DD · tag · …``)
    join the side(s) their tag names — a ``wall+recipe`` entry feeds both
    the wall side (tag says wall) and stays out of the capability side
    (a recipe around a wall is not the wall's absence).
    """
    wall_parts: list[str] = []
    cap_parts: list[str] = []
    section = None
    log_side: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            lower = line.lower()
            if "wall" in lower:
                section = "walls"
            elif "capabilit" in lower:
                section = "caps"
            elif "append log" in lower:
                section = "log"
            else:
                section = None
            continue
        if section == "walls":
            wall_parts.append(line)
        elif section == "caps":
            cap_parts.append(line)
        elif section == "log":
            if line.startswith("- "):
                fields = line.split("·")
                tag = fields[1].lower() if len(fields) > 1 else ""
                log_side = wall_parts if "wall" in tag else cap_parts
                log_side.append(line)
            elif line.strip() and log_side is not None:
                log_side.append(line)  # continuation line of the entry above
    return _tokens("\n".join(wall_parts)), _tokens("\n".join(cap_parts))


def check_capability_xref(
    target: Path,
    *,
    status_files: Sequence[str] | None = None,
    capabilities_relpath: str = CAPABILITIES_RELPATH,
) -> list[Finding]:
    """Return advisory findings cross-referencing owner asks vs the ledger.

    Scans every configured heartbeat file's ``⚑ OWNER-ACTION`` blocks; each
    wall-shaped VERIFIED-NEEDED is token-matched against the capability
    ledger's Walls/Capabilities sides. Emits ``owner-ask-wall-unrecorded``
    when the wall is nowhere in the ledger (or the ledger is absent), and
    ``owner-ask-capability-resolved`` when only the capability side matches.
    Advisory by contract — callers must never count these toward an exit
    code (see module docstring). Empty when the ``control/`` protocol is
    absent; fail-open on unreadable files and anchor-less asks.
    """
    relpaths = heartbeat_relpaths(status_files)
    control_evidence = [INBOX_RELPATH, CONTROL_README_RELPATH, *relpaths]
    if not any((target / rel).is_file() for rel in control_evidence):
        return []

    ledger_path = target / capabilities_relpath
    ledger_text: str | None = None
    if ledger_path.is_file():
        try:
            ledger_text = ledger_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []  # fail open — an unreadable ledger is not a verdict
    wall_tokens, cap_tokens = (
        _ledger_sides(ledger_text) if ledger_text is not None else (set(), set())
    )

    findings: list[Finding] = []
    for rel in relpaths:
        path = target / rel
        if not path.is_file():
            continue  # missing heartbeat is check_status_current's finding
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # fail open — an unreadable file is not a verdict
        for item_id, title, block in _owner_action_blocks(text):
            verified = _verified_needed(block)
            if not verified or not _is_wall_shaped(verified):
                continue  # field-less asks are check_owner_actions' finding;
                # judgment asks are out of the ledger's scope
            anchors = _anchors(verified)
            if not anchors:
                continue  # nothing distinctive to match — no verdict
            need = min(2, len(anchors))
            label = f"OWNER-ACTION {item_id}" + (f" ({title})" if title else "")
            if len(anchors & wall_tokens) >= need:
                continue  # the cited wall is recorded — the loop is closed
            if len(anchors & cap_tokens) >= need:
                findings.append(
                    Finding(
                        rel,
                        "owner-ask-capability-resolved",
                        f"{label} cites a wall, but {capabilities_relpath} "
                        "records the matching surface only as a verified "
                        "WORKING capability — the wall may have fallen. "
                        "Re-verify the ask (THE DISCOVERY RULE step 3) and "
                        "withdraw it, or record the residual wall.",
                    ),
                )
            else:
                findings.append(
                    Finding(
                        rel,
                        "owner-ask-wall-unrecorded",
                        f"{label} cites a technical wall that "
                        f"{capabilities_relpath} does not record — append "
                        "the wall there this session (THE DISCOVERY RULE "
                        "step 4: dated, exact error, workaround), so the "
                        "ask's evidence becomes every later session's "
                        "starting fact.",
                    ),
                )
    return findings

# --- engine/ledger.py ---
"""Decision ledger — the ``[D-NNNN]`` provenance-separated rulebook (Lane B6).

Implements the kit's ``docs/decisions.md`` grammar (plan: Q-0214.4 depth — a
constitution cites decisions by id instead of narrating them inline). One
entry is::

    ## [D-0001] <title>
    - status: decided | superseded | retired
    - date: YYYY-MM-DD
    - supersedes: D-NNNN        (optional)
    - superseded-by: D-NNNN     (stamped on the OLD entry when superseded)
    - verdict: <one ruling line>
    - why: <2-3 lines, continuation lines allowed>
    - provenance: <link or ref>

``parse_ledger`` is tolerant of prose between entries (the ledger is a living
markdown doc, not a database). ``append_decision`` assigns the next id and —
when superseding — rewrites the old entry in place so the chain is stamped on
both ends. ``check_ledger`` and ``check_stamp_discipline`` are the hygiene
checkers, reusing the ``Finding`` record from ``engine.checks.check_docs``.
Pure stdlib; every write goes through ``atomic_write_text``.
"""




LEDGER_FILENAME = "decisions.md"

# `## [D-0001] <title>` — the strict entry heading.
_LED_HEADING_RE = re.compile(r"^## \[(D-\d{3,})\] (.+)$")
# Any `## ` heading that *tries* to be an entry but fails the strict form.
_LED_HEADING_ATTEMPT_RE = re.compile(r"^##\s*\[?\s*D-", re.IGNORECASE)
# `- key: value` field line inside an entry block.
_LED_FIELD_RE = re.compile(r"^- ([a-z-]+):\s*(.*)$")
# A bare decision id, for supersedes targets and stamp-discipline citations.
_LED_ID_RE = re.compile(r"\bD-\d{3,}\b")
_LED_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_LED_STATUSES = frozenset({"decided", "superseded", "retired"})
_LED_REQUIRED_FIELDS = ("status", "date", "verdict", "why", "provenance")

_LED_HEADER = """# Decisions

> **Status:** `living-ledger` — append-only decision ledger; entries are \
superseded, never deleted.

<!-- Grammar: ## [D-NNNN] <title> / - status: decided|superseded|retired / \
- date: YYYY-MM-DD / - supersedes: D-NNNN (opt) / - superseded-by: D-NNNN \
(opt) / - verdict: <one line> / - why: <2-3 lines> / - provenance: <ref> -->
"""


def _led_field_key(raw: str) -> str:
    """Map a grammar field name to its entry-dict key (``-`` -> ``_``)."""
    return raw.replace("-", "_")


def _led_blocks(text: str) -> list[tuple[int, list[str]]]:
    """Split ``text`` into entry blocks: ``(heading lineno, block lines)``.

    A block starts at any ``## `` heading that looks like a decision entry
    (strict or malformed) and runs until the next ``## `` heading or EOF.
    Prose outside blocks is ignored.
    """
    blocks: list[tuple[int, list[str]]] = []
    current: list[str] | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            current = None
            if _LED_HEADING_ATTEMPT_RE.match(line):
                current = [line]
                blocks.append((lineno, current))
        elif current is not None:
            current.append(line)
    return blocks


def _led_parse_block(lines: list[str]) -> dict | None:
    """Parse one entry block into a dict, or ``None`` if the heading is bad."""
    match = _LED_HEADING_RE.match(lines[0])
    if match is None:
        return None
    entry: dict = {
        "id": match.group(1),
        "title": match.group(2).strip(),
        "status": None,
        "date": None,
        "supersedes": None,
        "superseded_by": None,
        "verdict": None,
        "why": None,
        "provenance": None,
    }
    last_key: str | None = None
    for line in lines[1:]:
        field = _LED_FIELD_RE.match(line)
        if field is not None:
            key = _led_field_key(field.group(1))
            if key in entry and key not in ("id", "title"):
                entry[key] = field.group(2).strip()
                last_key = key
            else:
                last_key = None
        elif line[:1].isspace() and line.strip() and last_key is not None:
            # Continuation line (indented) — the multi-line `why` case.
            entry[last_key] = f"{entry[last_key]}\n{line.strip()}"
        elif not line.strip():
            last_key = None
    return entry


def parse_ledger(text: str) -> list[dict]:
    """Parse ledger ``text`` into entry dicts, tolerating prose between entries.

    Malformed headings are skipped here (``check_ledger`` reports them);
    missing fields parse as ``None``.
    """
    entries: list[dict] = []
    for _, lines in _led_blocks(text):
        entry = _led_parse_block(lines)
        if entry is not None:
            entries.append(entry)
    return entries


def next_decision_id(entries: list[dict]) -> str:
    """Return the next free decision id (``D-0001`` for an empty ledger)."""
    highest = 0
    for entry in entries:
        try:
            highest = max(highest, int(entry["id"].split("-", 1)[1]))
        except (KeyError, IndexError, ValueError):
            continue
    return f"D-{highest + 1:04d}"


def _led_format_entry(entry: dict) -> str:
    """Render one entry dict back into its grammar block."""
    lines = [f"## [{entry['id']}] {entry['title']}"]
    lines.append(f"- status: {entry['status']}")
    lines.append(f"- date: {entry['date']}")
    if entry.get("supersedes"):
        lines.append(f"- supersedes: {entry['supersedes']}")
    if entry.get("superseded_by"):
        lines.append(f"- superseded-by: {entry['superseded_by']}")
    lines.append(f"- verdict: {entry['verdict']}")
    why = str(entry["why"]).split("\n")
    lines.append(f"- why: {why[0]}")
    lines.extend(f"  {cont}" for cont in why[1:])
    lines.append(f"- provenance: {entry['provenance']}")
    return "\n".join(lines)


def _led_stamp_superseded(text: str, old_id: str, new_id: str) -> str:
    """Rewrite ``old_id``'s entry in ``text``: status + superseded-by stamp."""
    out: list[str] = []
    in_target = False
    stamped = False
    for line in text.splitlines():
        if line.startswith("## "):
            # ANY level-2 heading ends the current block (mirrors _led_blocks)
            # — a prose section after the target must never get stamped.
            heading = _LED_HEADING_RE.match(line)
            in_target = heading is not None and heading.group(1) == old_id
        elif in_target and not line.strip():
            # An entry's field block is contiguous and ends at its first blank
            # line. Without this, a target that is the LAST entry keeps
            # ``in_target`` true to EOF (no later ``## `` to reset it) and would
            # silently stamp any field-shaped bullet in trailing prose.
            in_target = False
        field = _LED_FIELD_RE.match(line) if in_target else None
        if field is not None:
            key = field.group(1)
            if key == "status":
                out.append("- status: superseded")
                out.append(f"- superseded-by: {new_id}")
                stamped = True
                continue
            if key == "superseded-by" and stamped:
                continue  # replaced above
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def append_decision(
    path: Path,
    *,
    title: str,
    verdict: str,
    why: str,
    provenance: str,
    supersedes: str | None = None,
    date: str | None = None,
) -> dict:
    """Append a new decision to the ledger at ``path`` and return its dict.

    Creates the file (header + grammar comment) when absent, assigns the next
    free id, and — when ``supersedes`` names an existing entry — rewrites that
    old entry in place (``status: superseded`` plus a ``superseded-by`` stamp)
    so the chain is recorded on both ends. The whole file is written atomically.
    Raises ``ValueError`` when ``supersedes`` names an id not in the ledger.
    """
    text = path.read_text(encoding="utf-8") if path.exists() else _LED_HEADER
    entries = parse_ledger(text)
    if supersedes is not None:
        known = {entry["id"] for entry in entries}
        if supersedes not in known:
            msg = f"supersedes target {supersedes} not found in {path.name}"
            raise ValueError(msg)
    entry = {
        "id": next_decision_id(entries),
        "title": title,
        "status": "decided",
        "date": date or _led_date.today().isoformat(),
        "supersedes": supersedes,
        "superseded_by": None,
        "verdict": verdict,
        "why": why,
        "provenance": provenance,
    }
    if supersedes is not None:
        text = _led_stamp_superseded(text, supersedes, entry["id"])
    if not text.endswith("\n"):
        text += "\n"
    atomic_write_text(path, f"{text}\n{_led_format_entry(entry)}\n")
    return entry


def current_rules(entries: list[dict]) -> list[dict]:
    """Return the live rule set: supersedes chains resolved, retired dropped.

    An entry is live when its status is neither ``superseded`` nor ``retired``
    *and* no other entry names it as a supersedes target (chain resolution
    holds even when the old entry missed its stamp).
    """
    replaced = {e["supersedes"] for e in entries if e.get("supersedes")}
    return [
        e
        for e in entries
        if e.get("status") not in ("superseded", "retired") and e["id"] not in replaced
    ]


def check_ledger(path: Path) -> list[Finding]:
    """Validate the ledger grammar; return findings (empty for a clean file).

    Flags: unparseable entry blocks, missing/invalid required fields, duplicate
    ids, dangling ``supersedes`` targets, non-monotonic ids, and a superseded
    entry missing its ``superseded-by`` stamp. An absent ledger yields no
    findings (adoption plants it).
    """
    if not path.exists():
        return []
    rel = path.name
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    entries: list[dict] = []
    for lineno, lines in _led_blocks(text):
        entry = _led_parse_block(lines)
        if entry is None:
            msg = f"L{lineno}: unparseable entry heading: {lines[0].strip()}"
            findings.append(Finding(rel, "ledger", msg))
            continue
        entries.append(entry)
        for field in _LED_REQUIRED_FIELDS:
            if not entry.get(field):
                msg = f"L{lineno}: {entry['id']} missing required field `{field}`"
                findings.append(Finding(rel, "ledger", msg))
        status = entry.get("status")
        if status and status not in _LED_STATUSES:
            allowed = ", ".join(sorted(_LED_STATUSES))
            msg = f"L{lineno}: {entry['id']} invalid status `{status}` ({allowed})"
            findings.append(Finding(rel, "ledger", msg))
        if entry.get("date") and not _LED_DATE_RE.match(entry["date"]):
            msg = f"L{lineno}: {entry['id']} invalid date `{entry['date']}`"
            findings.append(Finding(rel, "ledger", msg))
        if status == "superseded" and not entry.get("superseded_by"):
            msg = f"L{lineno}: {entry['id']} superseded without a superseded-by stamp"
            findings.append(Finding(rel, "ledger", msg))

    seen: set[str] = set()
    known = {entry["id"] for entry in entries}
    previous = 0
    for entry in entries:
        number = int(entry["id"].split("-", 1)[1])
        if entry["id"] in seen:
            findings.append(Finding(rel, "ledger", f"duplicate id {entry['id']}"))
        elif number <= previous:
            msg = f"non-monotonic id {entry['id']} after D-{previous:04d}"
            findings.append(Finding(rel, "ledger", msg))
        seen.add(entry["id"])
        previous = max(previous, number)
        target = entry.get("supersedes")
        if target and target not in known:
            msg = f"{entry['id']} supersedes dangling target {target}"
            findings.append(Finding(rel, "ledger", msg))
    return findings


def check_stamp_discipline(docs_root: Path, ledger_path: Path) -> list[Finding]:
    """Flag a decision id cited from more than one doc outside the ledger.

    The provenance-separated model wants each ``D-NNNN`` stamped at exactly one
    home (the rule it justifies); a second citation is drift risk — when the
    decision changes, one of the two goes stale. Kind ``stamp`` (warn-class).
    """
    if not docs_root.exists():
        return []
    ledger_resolved = ledger_path.resolve()
    citations: dict[str, list[str]] = {}
    for doc in sorted(docs_root.rglob("*.md")):
        if doc.resolve() == ledger_resolved:
            continue
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = doc.relative_to(docs_root).as_posix()
        for cited in set(_LED_ID_RE.findall(text)):
            citations.setdefault(cited, []).append(rel)
    findings: list[Finding] = []
    for cited, docs in sorted(citations.items()):
        if len(docs) > 1:
            cite_list = ", ".join(sorted(docs))
            msg = (
                f"{cited} cited from {len(docs)} docs ({cite_list}) — "
                "stamp each decision at one home"
            )
            findings.append(Finding(sorted(docs)[0], "stamp", msg))
    return findings

# --- engine/loop/kpis.py ---
"""Workflow KPIs for the self-improving loop (plan section 5, Lane B1).

Deterministic read-only metrics over the state document + sessions directory:
``router_metrics`` measures the question-router's health (slot completeness,
open questions, the assumption-confirmation rate that keeps autonomous runs
honest), ``workflow_kpis`` adds the session/reflection counters, and
``kpi_footer`` renders the one-line 📊 summary the orientation and reports
embed. Pure stdlib; returns data / text, never prints.
"""




def _kpi_confirmation_rate(slot_values: dict[str, Any]) -> float:
    """Return confirmed-over-self-answered for the recorded slot values.

    Self-answered slots are those whose ``source`` is ``"assumption"`` or
    starts with ``"confirmed:"`` (a confirmed former assumption). With no
    self-answered slots there is nothing to confirm — the rate is 1.0.
    """
    confirmed = 0
    self_answered = 0
    if not isinstance(slot_values, dict):
        return 1.0
    for entry in slot_values.values():
        if not isinstance(entry, dict):
            # A hand-corrupted state.json can carry a non-dict slot value; skip
            # it rather than raising (the kit's read-side fail-open contract —
            # a KPI read must never brick session-close / maintain). Matches the
            # non-dict guards in reflections / episodes / maintenance.
            continue
        source = str(entry.get("source", ""))
        if source.startswith("confirmed:"):
            confirmed += 1
            self_answered += 1
        elif source == "assumption":
            self_answered += 1
    if self_answered == 0:
        return 1.0
    return confirmed / self_answered


def router_metrics(state: dict[str, Any]) -> dict[str, Any]:
    """Return the question-router health metrics for one state document.

    ``completeness_pct`` counts ``filled`` slots only — ``provisional`` and
    ``partial`` answers never inflate completeness (the anti-gaming floor's
    KPI mirror). With no recorded slots completeness is 0.0.
    """
    slots = state.get("slots", {})
    statuses = list(slots.values())
    total = len(statuses)
    filled = statuses.count("filled")
    provisional = statuses.count("provisional")
    completeness = round(100.0 * filled / total, 1) if total else 0.0
    return {
        "slots_total": total,
        "slots_filled": filled,
        "slots_provisional": provisional,
        "completeness_pct": completeness,
        "open_questions": len(state.get("open_questions", [])),
        "assumption_confirmation_rate": _kpi_confirmation_rate(
            state.get("slot_values", {}),
        ),
        "quiet_sessions": int(state.get("quiet_sessions", 0)),
        "session_count": int(state.get("session_count", 0)),
    }


def workflow_kpis(state: dict[str, Any], sessions_dir: Path) -> dict[str, Any]:
    """Return the full workflow KPI record: router metrics + session counters.

    ``sessions_logged`` counts ``*.md`` logs under ``sessions_dir`` (README
    excluded, 0 when the directory is absent); ``reflections_active`` reads
    the state's reflection-buffer counter.
    """
    kpis = router_metrics(state)
    logged = 0
    if sessions_dir.is_dir():
        logged = sum(1 for p in sessions_dir.glob("*.md") if p.name != "README.md")
    buffer = state.get("reflection_buffer", {})
    kpis["sessions_logged"] = logged
    kpis["reflections_active"] = int(buffer.get("active_count", 0))
    kpis["stage"] = state.get("stage")
    kpis["mode"] = state.get("mode")
    return kpis


def kpi_footer(kpis: dict[str, Any]) -> str:
    """Render the one-line 📊 KPI summary for orientation blocks and reports.

    Router metrics always appear; the workflow extras (logged sessions,
    active lessons, mode, stage) appear when present in ``kpis``.
    """
    completeness = float(kpis.get("completeness_pct", 0.0))
    parts = [
        f"completeness {completeness:.0f}%",
        f"open-Q {kpis.get('open_questions', 0)}",
        f"sessions {kpis.get('session_count', 0)}",
        f"quiet {kpis.get('quiet_sessions', 0)}",
    ]
    if "sessions_logged" in kpis:
        parts.append(f"logged {kpis['sessions_logged']}")
    if "reflections_active" in kpis:
        parts.append(f"lessons {kpis['reflections_active']}")
    if kpis.get("mode") is not None:
        parts.append(f"mode {kpis['mode']}")
    if kpis.get("stage") is not None:
        parts.append(f"stage {kpis['stage']}")
    return "📊 substrate: " + " · ".join(parts)

# --- engine/loop/reflections.py ---
"""Reflection buffer — the loop's compact learned-lesson memory (plan lane B2).

Reflections are small ``{"lesson", "evidence", "tags"}`` records mined from
session logs or added deliberately, stored in one atomically-written JSON file
(``<state_dir>/reflections.json``). The buffer is deliberately tiny — a hard
``buffer_size`` cap keeps the orientation injection cheap — and fail-open: a
missing or corrupt file reads as an empty list, never a crash. The miner is
deterministic and read-only; the caller decides what (if anything) becomes a
stored reflection.
"""




REFLECTIONS_FILENAME = "reflections.json"

_REF_ID_RE = re.compile(r"^R-(\d+)$")
_REF_IDEA_MARK = "\N{ELECTRIC LIGHT BULB}"  # 💡 — session-idea lines
_REF_FLAG_MARK = "\N{BLACK FLAG}"  # ⚑ — self-initiated / friction flags
_REF_PATH_SUFFIXES = (".py", ".md", ".js", ".ts", ".yml", ".json")
_REF_STRIP_CHARS = "`'\"()[]<>,;:!?."


def load_reflections(path: Path) -> list[dict]:
    """Return the reflection entries at ``path`` — ``[]`` on absent/corrupt."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _ref_save(path: Path, entries: list[dict]) -> None:
    """Write ``entries`` to ``path`` atomically as pretty-printed JSON."""
    atomic_write_text(path, json.dumps(entries, indent=2) + "\n")


def _ref_next_id(entries: list[dict]) -> str:
    """Return the next ``R-NNNN`` id, monotonic over the ids already present."""
    highest = 0
    for entry in entries:
        match = _REF_ID_RE.match(str(entry.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"R-{highest + 1:04d}"


def _ref_is_inactive(entry: dict) -> bool:
    """True when an entry is deprecated or superseded (prune/skip candidate)."""
    return entry.get("status") == "deprecated" or bool(entry.get("superseded_by"))


def _ref_prune(entries: list[dict], buffer_size: int) -> list[dict]:
    """Drop overflow beyond ``buffer_size``: oldest inactive first, then oldest.

    ``buffer_size`` is clamped to at least 1 — a zero/negative host config must
    never silently discard every lesson (or crash), and the entry just added is
    never its own prune victim.
    """
    buffer_size = max(1, int(buffer_size))
    pruned = list(entries)
    while len(pruned) > buffer_size:
        victim = next((e for e in pruned[:-1] if _ref_is_inactive(e)), pruned[0])
        pruned.remove(victim)
    return pruned


def add_reflection(
    path: Path,
    *,
    lesson: str,
    evidence: str,
    tags: list[str],
    status: str = "provisional",
    buffer_size: int = 5,
) -> dict:
    """Append a reflection to the buffer at ``path`` and return the new entry.

    Assigns the next monotonic ``R-NNNN`` id, stamps today's ISO date, and
    prunes overflow beyond ``buffer_size`` (oldest superseded/deprecated
    entries first, then oldest overall). ``status`` is ``provisional`` until a
    later session confirms the lesson held up.
    """
    entries = load_reflections(path)
    entry = {
        "id": _ref_next_id(entries),
        "lesson": lesson,
        "evidence": evidence,
        "tags": list(tags),
        "status": status,
        "date": date.today().isoformat(),
    }
    entries.append(entry)
    _ref_save(path, _ref_prune(entries, buffer_size))
    return entry


def active_lessons(entries: list[dict], buffer_size: int) -> list[dict]:
    """Return live lessons newest-first, capped at ``buffer_size``.

    Skips entries whose status is ``deprecated`` and entries carrying a
    ``superseded_by`` stamp.
    """
    live = [entry for entry in entries if not _ref_is_inactive(entry)]
    live.reverse()
    return live[:buffer_size]


def supersede_reflection(path: Path, old_id: str, new_id: str) -> bool:
    """Stamp ``superseded_by`` on ``old_id``'s entry; False when it is absent."""
    entries = load_reflections(path)
    for entry in entries:
        if entry.get("id") == old_id:
            entry["superseded_by"] = new_id
            _ref_save(path, entries)
            return True
    return False


def lessons_block(entries: list[dict]) -> str:
    """Render the "Learned lessons" orientation block ("" when nothing active).

    Provisional entries are flagged ``(provisional)`` so the reading agent
    weighs them as candidates, not settled rules.
    """
    live = active_lessons(entries, len(entries))
    if not live:
        return ""
    lines = ["## Learned lessons", ""]
    for entry in live:
        flag = " (provisional)" if entry.get("status") == "provisional" else ""
        lines.append(f"- [{entry.get('id', '?')}] {entry.get('lesson', '')}{flag}")
    return "\n".join(lines) + "\n"


def _ref_newest_logs(sessions_dir: Path, last_n: int) -> list[Path]:
    """Return the newest ``last_n`` logs by mtime (name-tiebroken), oldest first."""
    if not sessions_dir.is_dir() or last_n < 1:
        return []
    logs = [p for p in sessions_dir.glob("*.md") if p.name != "README.md"]
    logs.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return logs[-last_n:]


def _ref_clean_line(line: str) -> str:
    """Strip list/blockquote prefixes and the emoji markers from a mined line."""
    text = _REF_LEAD_PREFIX_RE.sub("", line.strip())
    for mark in (_REF_IDEA_MARK, _REF_FLAG_MARK):
        text = text.replace(mark, "")
    return text.strip().lstrip(":").strip()


# List/blockquote prefixes a marker-led line may open with: bullets ("- ", "* ",
# "+ "), blockquotes ("> "), and ordered-list numbers ("1. ", "12) "), possibly
# nested. Stripped before the marker-lead test below.
_REF_LEAD_PREFIX_RE = re.compile(r"^(?:\s*(?:[-*+>]\s|\d{1,3}[.)]\s))*\s*")


def _ref_marker_tags(line: str) -> list[str]:
    """Return the tags for a line *led* by an emoji marker (may be empty).

    Only lines whose content starts at the marker — after list/blockquote
    prefixes and emphasis characters — are lesson candidates. A mid-prose
    marker mention ("see 💡 below for the durable fix", "its friction-index 💡
    was left floating") is a cross-reference, not a lesson; harvesting those
    produced junk fragments in the kit-lab band (observed 2026-07-09).
    """
    text = _REF_LEAD_PREFIX_RE.sub("", line).lstrip("*_ ")
    if text.startswith(_REF_IDEA_MARK):
        return ["idea"]
    if text.startswith(_REF_FLAG_MARK):
        return ["flag"]
    return []


def _ref_path_tokens(line: str) -> list[str]:
    """Return file-path tokens: contain ``/`` and end in a known code/doc suffix."""
    tokens: list[str] = []
    for raw in line.split():
        token = raw.strip(_REF_STRIP_CHARS)
        if "/" in token and token.endswith(_REF_PATH_SUFFIXES):
            tokens.append(token)
    return tokens


def _ref_mine_log(log: Path) -> tuple[list[dict], dict[str, str]]:
    """Mine one log: (marker-line candidates, first evidence per cited path)."""
    candidates: list[dict] = []
    paths_seen: dict[str, str] = {}
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return candidates, paths_seen
    for lineno, line in enumerate(lines, 1):
        if "[DEPRECATED]" in line:
            continue
        evidence = f"{log.name}:L{lineno}"
        # Heading lines ("## 💡 Session idea") are section *structure*, not
        # lessons — mining them produced header-text reflections in the KL-0
        # dogfood (friction guard, 2026-07-09). Path tokens in headings still
        # count for the recurring-path pass.
        is_heading = line.lstrip().startswith("#")
        tags = [] if is_heading else _ref_marker_tags(line)
        if tags:
            candidates.append(
                {"lesson": _ref_clean_line(line), "evidence": evidence, "tags": tags},
            )
        for token in _ref_path_tokens(line):
            paths_seen.setdefault(token, evidence)
    return candidates, paths_seen


def mine_reflections(sessions_dir: Path, *, last_n: int = 5) -> list[dict]:
    """Mine candidate lessons from the newest ``last_n`` session logs.

    Deterministic and read-only — never writes state; the caller decides what
    to promote into the buffer. Three extraction passes:

      1. 💡-led idea lines → ``{"lesson", "evidence", "tags": ["idea"]}``.
      2. ⚑-led flag lines → the same shape, tagged ``flag``.
      3. Any file path cited in >= 2 different logs → one
         ``Recurring attention on <path>`` candidate.

    Passes 1–2 require the marker to *lead* the line (after list/blockquote
    prefixes) — a mid-prose marker mention is a cross-reference, never a
    lesson. Lines containing ``[DEPRECATED]`` are skipped entirely;
    ``#``-prefixed heading lines never become lesson candidates (passes 1–2)
    but their path tokens still feed pass 3.
    """
    candidates: list[dict] = []
    sightings: dict[str, dict[str, str]] = {}
    for log in _ref_newest_logs(sessions_dir, last_n):
        mined, paths_seen = _ref_mine_log(log)
        candidates.extend(mined)
        for token, evidence in paths_seen.items():
            sightings.setdefault(token, {})[log.name] = evidence
    for token in sorted(sightings):
        seen = sightings[token]
        if len(seen) < 2:
            continue
        evidence = ", ".join(seen[name] for name in sorted(seen))
        candidates.append(
            {
                "lesson": f"Recurring attention on {token}",
                "evidence": evidence,
                "tags": ["recurring-path"],
            },
        )
    return candidates

# --- engine/loop/friction.py ---
"""The friction-report protocol's consumer half (founding plan §9.1, KL-4).

The context-delta loop, cross-repo: a consumer collects its kit-friction ⚑
records, wraps them in a small envelope, and files them as a **GitHub issue
labeled ``friction`` on the kit repo** (⚑ KF-7). The engine is stdlib-only
and holds no network credentials, so the split is explicit:

- **The engine (``friction export``)** builds the envelope and writes it to
  the outbox at ``<state_dir>/friction-outbox/`` — the same outbox §9.1
  prescribes for network/credential failure, used unconditionally: every
  export lands there first, and the file doubles as the retry buffer.
- **The session/agent files the issue** (its GitHub surface — MCP, ``gh``,
  Actions) using the issue-ready title + body ``friction export``/``show``
  print, then deletes the drained outbox file. Session-close advises on
  pending files (best-effort, fail-open — the lab cannot drain a consumer's
  outbox; it has no consumer write access).

Envelope (§9.1, D-14 — the payload IS the reflection record shape)::

    { "schema": 1, "repo": "<github full name>", "project_id": "<config id>",
      "kit_version": "1.0.0", "reports": [ {reflection-record…}, … ] }

Reports = the reflection buffer's ``flag``-tagged records **plus** a direct
session-log scan for un-mined ⚑ lines — the buffer is a 5-slot rolling
window, not an archive, so export never depends on it alone (D-14).
"""




FRICTION_SCHEMA = 1
FRICTION_OUTBOX_DIRNAME = "friction-outbox"
FRICTION_LABEL = "friction"

# owner/repo out of a git remote URL — tolerant of https, ssh, and proxy
# forms (…github.com/owner/repo.git · git@github.com:owner/repo ·
# http://proxy/git/owner/repo). Fail-open: no match reads as "".
_REMOTE_REPO_RE = re.compile(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?\s*$")


def detect_repo(root: Path) -> str:
    """Best-effort ``owner/repo`` from ``.git/config``'s origin URL ("" if not).

    Pure file parsing (the engine may not shell out): finds the
    ``[remote "origin"]`` section's ``url =`` line and extracts the last two
    path components. Any failure — no repo, detached layouts, exotic
    remotes — returns ``""`` so the caller can require ``--repo`` instead.
    """
    config_path = root / ".git" / "config"
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    in_origin = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_origin = stripped.replace("'", '"') == '[remote "origin"]'
            continue
        if in_origin and stripped.startswith("url"):
            _, _, url = stripped.partition("=")
            match = _REMOTE_REPO_RE.search(url.strip())
            return match.group(1) if match else ""
    return ""


def friction_reports(target: Path, config: Any) -> list[dict]:
    """Collect the ⚑ friction records for one export (D-14, both sources).

    Buffer records tagged ``flag`` come through verbatim (full reflection
    record shape); the direct session-log scan adds un-mined ⚑ lines as
    ``{lesson, evidence, tags}`` records, deduplicated against the buffer
    (and against each other) by lesson text.
    """
    reflections_path = target / config.state_dir / REFLECTIONS_FILENAME
    reports = [
        entry
        for entry in load_reflections(reflections_path)
        if "flag" in (entry.get("tags") or [])
    ]
    seen = {str(entry.get("lesson", "")) for entry in reports}
    # A deliberately huge last_n: the export scans EVERY session log — the
    # buffer's 5-slot window must never bound what gets reported.
    for candidate in mine_reflections(target / config.sessions_dir, last_n=100000):
        if "flag" not in candidate.get("tags", []):
            continue
        lesson = str(candidate.get("lesson", ""))
        if not lesson or lesson in seen:
            continue
        seen.add(lesson)
        reports.append(candidate)
    return reports


def build_envelope(
    *,
    repo: str,
    project_id: str,
    kit_version: str,
    reports: list[dict],
) -> dict:
    """Return the §9.1 wire envelope for ``reports``."""
    return {
        "schema": FRICTION_SCHEMA,
        "repo": repo,
        "project_id": project_id,
        "kit_version": kit_version,
        "reports": reports,
    }


def outbox_dir(target: Path, state_dir: str) -> Path:
    """Return the friction-outbox directory for one install."""
    return target / state_dir / FRICTION_OUTBOX_DIRNAME


def list_outbox(target: Path, state_dir: str) -> list[Path]:
    """Return the pending outbox envelopes, oldest first ([] when none)."""
    box = outbox_dir(target, state_dir)
    if not box.is_dir():
        return []
    return sorted(p for p in box.glob("*.json") if p.is_file())


def write_outbox(target: Path, state_dir: str, envelope: dict) -> Path:
    """Write ``envelope`` to a fresh outbox file (atomic); return its path."""
    box = outbox_dir(target, state_dir)
    stamp = date.today().isoformat()
    serial = 1
    while (path := box / f"{stamp}-friction-{serial:02d}.json").exists():
        serial += 1
    atomic_write_text(path, json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    return path


def load_envelope(path: Path) -> dict | None:
    """Read one outbox envelope; None on a missing/corrupt file (fail-open)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def friction_issue_title(envelope: dict) -> str:
    """Return the friction issue's title line."""
    repo = envelope.get("repo") or envelope.get("project_id") or "unknown consumer"
    count = len(envelope.get("reports") or [])
    version = envelope.get("kit_version") or "unrecorded"
    plural = "s" if count != 1 else ""
    return f"[friction] {repo}: {count} report{plural} @ kit v{version}"


def friction_issue_body(envelope: dict) -> str:
    """Return the friction issue's body: one-line summary + fenced JSON (§9.1)."""
    reports = envelope.get("reports") or []
    lessons = [str(r.get("lesson", ""))[:120] for r in reports[:3]]
    summary = "; ".join(lesson for lesson in lessons if lesson) or "(no lessons)"
    if len(reports) > 3:
        summary += f"; … +{len(reports) - 3} more"
    payload = json.dumps(envelope, indent=2, sort_keys=True)
    return (
        f"Consumer friction report — {summary}\n"
        "\n"
        f"```json\n{payload}\n```\n"
        "\n"
        f"*Filed per founding plan §9.1 (label `{FRICTION_LABEL}`; triage = "
        "the lab loop's step 5 three-clause bar; disposition comment + "
        "close).*\n"
    )

# --- engine/loop/telemetry.py ---
"""Telemetry substrate — guard-fire records + the model-usage harvest (KL-3).

Two feeds, both mechanized (the Phase-2.5 lesson: mechanize, don't exhort)
and both **fail-open by contract** — telemetry must never crash a check, a
hook, or session-close (founding plan §5.3/§5.2):

- **Guard fires** (B3): one JSONL record per finding a guard surfaces,
  appended to ``<state_dir>/guard-fires.jsonl`` by the two local choke points
  (``cmd_check``'s finding loop, ``cmd_hook``'s dispatch). The ``ci`` surface
  is **derived, not written** — a JSONL appended inside an Actions runner
  dies with the job, so the lab sweep reads the GitHub Checks API instead,
  and ``did_not_run`` rows are computed the same way (never written here).
- **Model usage** (B2 / PL-004): sessions self-report one machine-parsed
  run-report line — ``- **📊 Model:** <model> · <effort> · <task-class>`` —
  and ``session-close`` harvests it into ``telemetry/model-usage.jsonl``.
  ``tokens_out`` is null-tolerated (KF-9: no meter exists; an optional 4th
  ``·`` segment fills it when one does). ``outcome`` ships as the PL-004
  object with null fields — the lab loop's sweep backfills them (CI result,
  merged PR, the 14-day revert window).

Appends use a single ``write`` in append mode (atomic enough for one-line
records on POSIX); full-file rewrites are never performed on either feed —
JSONL because atomic appends beat rewriting a JSON array (plan D-10).
"""




GUARD_FIRES_FILENAME = "guard-fires.jsonl"
MODEL_USAGE_RELPATH = "telemetry/model-usage.jsonl"

# The run-report needle. \N escape keeps the engine source ASCII-safe.
MODEL_LINE_NEEDLE = "\N{BAR CHART} Model:"  # 📊 Model:

# The 9 PL-004 task classes, verbatim (docs/program/rulings.md): the 8
# founding Q-0248 classes + `feature build` (the PL-010 amendment).
TASK_CLASSES = (
    "docs-only",
    "mechanical refactor",
    "test writing",
    "runtime bugfix",
    "kernel/architecture design",
    "review/verify",
    "research",
    "idea/planning",
    "feature build",
)

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def guard_fires_path(root: Path, state_dir: str) -> Path:
    """Return the guard-fire JSONL path for one install."""
    return root / state_dir / GUARD_FIRES_FILENAME


def _append_jsonl(path: Path, record: dict) -> None:
    """Append one compact JSON line to ``path`` (parents created)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def record_guard_fires(
    root: Path,
    state_dir: str,
    *,
    cmd: str,
    surface: str,
    posture: str,
    findings: list,
    verdict: str | None = None,
    reason: str | None = None,
) -> int:
    """Append one §5.3 record per finding; return how many were written.

    ``findings`` is any iterable of objects with ``path``/``kind``/``message``
    attributes (the kit's uniform ``Finding`` tuple is already the payload).
    ``guard`` is the finding's ``kind`` — per-kind granularity is exactly the
    per-guard unit B3 computes fire/FP rates over. ``verdict``/``reason`` are
    pre-filled only when an allowlist entry suppressed the finding (creating
    the entry IS the false_positive/accepted_risk verdict event); ``judge``
    and ``outcome`` always start null — a later, *different* party fills them
    (the grading-separation rule).

    Fail-open by contract: any failure (unwritable path, weird finding
    object) writes nothing and raises nothing — telemetry never blocks an
    agent-facing path. Writes only into an **existing** install
    (``state_dir`` present): ``check`` runs on un-adopted trees and must stay
    read-only there.
    """
    try:
        if not (root / state_dir).is_dir():
            return 0
        path = guard_fires_path(root, state_dir)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        written = 0
        for finding in findings:
            record = {
                "ts": ts,
                "guard": str(finding.kind),
                "cmd": cmd,
                "surface": surface,
                "posture": posture,
                "finding": {
                    "path": str(finding.path),
                    "kind": str(finding.kind),
                    "message": str(finding.message),
                },
                "verdict": verdict,
                "reason": reason,
                "judge": None,
                "outcome": None,
            }
            _append_jsonl(path, record)
            written += 1
        return written
    except Exception:  # noqa: BLE001 — telemetry fails open by contract
        return 0


def _parse_model_payload(payload: str) -> dict | None:
    """Parse one needle line's payload; None when it under-fills (<3 segments)."""
    parts = [p.strip(" *`") for p in payload.split("\N{MIDDLE DOT}")]
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return None
    tokens_out: int | None = None
    if len(parts) >= 4:
        try:
            tokens_out = int(parts[3].replace(",", "").replace("_", ""))
        except ValueError:
            tokens_out = None
    return {
        "model": parts[0],
        "effort": parts[1],
        "task_class": parts[2],
        "tokens_out": tokens_out,
    }


def parse_model_line(text: str) -> dict | None:
    """Parse the last *validly-formed* ``📊 Model:`` line out of a log's text.

    Returns ``{"model", "effort", "task_class", "tokens_out"}`` or None when
    no needle-bearing line parses (needle absent, or every candidate has
    fewer than three ``·`` segments). Last-VALID wins — a corrected report
    later in the card still supersedes an earlier one (the original
    last-occurrence intent), but a line that merely *mentions* the marker in
    prose (no ``·`` payload) no longer shadows a real telemetry line above
    it. That shadowing was found live in websites#31: last-needle selection
    made a prose mention beat the genuine line → None → a misleading
    "no line" advisory while the marker scan passed.
    Bold markers and the list dash are cosmetic and stripped; an optional 4th
    integer segment fills ``tokens_out`` (KF-9 — null until a meter exists).
    """
    parsed = None
    for line in text.splitlines():
        if MODEL_LINE_NEEDLE in line and DRAFT_FILL_TOKEN not in line:
            # An auto-drafted stand-in (`[[fill: model]] · …`, KL-5) is not a
            # report — harvesting it would feed placeholder junk into the
            # PL-004 dataset. Skip it; the advisory keeps asking for the line.
            candidate = _parse_model_payload(line.split(MODEL_LINE_NEEDLE, 1)[1])
            if candidate is not None:
                parsed = candidate
    return parsed


def _build_model_usage_record(session: str, parsed: dict) -> dict:
    """Build one PL-004 model-usage row from a session slug + parsed 📊 line.

    Shared by ``harvest_model_usage`` (single-latest) and
    ``reconcile_model_usage`` (whole-tree sweep) so both feeds emit the exact
    same shape. ``outcome`` ships all-null — a later lab sweep backfills it.
    """
    match = _DATE_PREFIX_RE.match(session)
    return {
        "session": session,
        "date": match.group(1) if match else date.today().isoformat(),
        "model": parsed["model"],
        "effort": parsed["effort"],
        "task_class": parsed["task_class"],
        "tokens_out": parsed["tokens_out"],
        "outcome": {
            "ci_green_first_push": None,
            "checker_findings": None,
            "merged_pr": None,
            "reverted_within_window": None,
        },
    }


def _model_usage_sessions(path: Path) -> set[str]:
    """Return the session slugs already recorded at ``path`` (dedupe key)."""
    sessions: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and record.get("session"):
                sessions.add(str(record["session"]))
    except OSError:
        pass
    return sessions


def harvest_model_usage(root: Path, session_log: Path | None) -> list[str]:
    """Harvest the 📊 line from ``session_log`` into the model-usage JSONL.

    Returns human-readable result lines for the CLI to emit (advisories when
    the line is missing or the task class is off-taxonomy). The record is the
    PL-004 shape: ``{session, date, model, effort, task_class, tokens_out,
    outcome}``, ``outcome`` an all-null object until the lab sweep backfills
    it. One record per session slug — a re-run session-close never
    double-appends. Fail-open: any unexpected failure reports itself as an
    advisory rather than raising into session-close.
    """
    try:
        if session_log is None:
            return [f"no session log — no {MODEL_LINE_NEEDLE} line to harvest."]
        parsed = parse_model_line(session_log.read_text(encoding="utf-8"))
        if parsed is None:
            return [
                f"session log {session_log.name} has no "
                f"`{MODEL_LINE_NEEDLE}` line — add "
                "`- **\N{BAR CHART} Model:** <model> · <effort> · <task-class>` "
                "so the PL-004 dataset gets this session's row.",
            ]
        lines: list[str] = []
        if parsed["task_class"] not in TASK_CLASSES:
            known = " | ".join(TASK_CLASSES)
            lines.append(
                f"task_class {parsed['task_class']!r} is not one of the "
                f"{len(TASK_CLASSES)} PL-004 classes ({known}) — recorded "
                "verbatim; fix the line or the taxonomy.",
            )
        session = session_log.stem
        path = root / MODEL_USAGE_RELPATH
        if session in _model_usage_sessions(path):
            lines.append(f"model-usage: {session} already recorded (skipped).")
            return lines
        _append_jsonl(path, _build_model_usage_record(session, parsed))
        lines.append(f"model-usage: recorded {session} -> {MODEL_USAGE_RELPATH}")
        return lines
    except Exception:  # noqa: BLE001 — telemetry fails open by contract
        return ["model-usage: harvest failed (fail-open) — row not recorded."]


def reconcile_model_usage(root: Path, sessions_dir: Path) -> list[str]:
    """Sweep EVERY complete session card into the model-usage feed (write-at-commit).

    The single-latest ``harvest_model_usage`` at session-close only ever wrote
    the *newest* card's row, so a card committed while a newer card already
    existed never reached ``telemetry/model-usage.jsonl`` — the KL-3
    undercount (gen-2 queue item 6: 10 recorded rows vs 42 eligible cards).
    This reconcile closes that gap deterministically: it appends one row for
    every **complete** card carrying a valid ``📊 Model:`` line that is not
    already recorded, so the moment a card commits complete its telemetry row
    exists and no later card can shadow it out of the harvest.

    Completeness-gated on the exact machinery the session-log checker uses
    (``status_in_progress`` + ``unresolved_fill_count``): a born-red /
    in-progress / drafted card has no finished session to report and is picked
    up only once it flips complete — the write-at-card-commit contract. The
    record shape is the PL-004 object built by ``_build_model_usage_record``;
    ``outcome`` starts all-null (the lab sweep backfills it). Idempotent
    (dedupe by session slug, in-batch too — re-running never double-appends),
    append-only, and fail-open like every telemetry path. Returns
    human-readable summary lines for the CLI.
    """
    try:
        if not sessions_dir.is_dir():
            return []
        path = root / MODEL_USAGE_RELPATH
        recorded = _model_usage_sessions(path)
        added: list[str] = []
        for card in sorted(sessions_dir.glob("*.md")):
            if card.name == "README.md":
                continue
            try:
                text = card.read_text(encoding="utf-8")
            except OSError:
                continue
            # A card only earns its row once it commits complete — an
            # in-progress or drafted (born-red) card is not a finished session.
            if status_in_progress(text) or unresolved_fill_count(text):
                continue
            parsed = parse_model_line(text)
            if parsed is None:
                continue
            session = card.stem
            if session in recorded:
                continue
            _append_jsonl(path, _build_model_usage_record(session, parsed))
            recorded.add(session)
            added.append(session)
        if not added:
            return ["model-usage: reconcile — no unrecorded complete cards."]
        head = f"model-usage: reconcile recorded {len(added)} card(s) -> {MODEL_USAGE_RELPATH}"
        if len(added) <= 6:
            head += f" ({', '.join(added)})"
        return [head]
    except Exception:  # noqa: BLE001 — telemetry fails open by contract
        return ["model-usage: reconcile failed (fail-open) — rows not recorded."]

# --- engine/loop/handoff.py ---
"""Auto-drafted session handoff (band KL-5, founding plan §10 — the ruled B1 prerequisite).

The Phase-2.5 A/B measured the same failure twice: write-back that depends on
agent discipline does not happen in task-focused sessions (the ON arm read the
planted docs and wrote **nothing** back). This module stops asking the agent to
remember: ``session-close`` and the Stop hook **draft** the session card's
close-out from evidence the engine can already see, so the agent *edits a
draft* instead of authoring from scratch — the same trick that makes the
born-red card work (the card exists before the work; closing it is editing,
not remembering).

Evidence sources (all pure stdlib — no subprocess, per the engine lint bans):

- a **session-start anchor** (``state["session_anchor"]``) recorded by the
  SessionStart hook: timestamp + git HEAD/branch, read from ``.git`` by file
  parsing (loose refs, ``packed-refs``, worktree ``gitdir:`` files);
- an **mtime scan** of the working tree against the anchor — the stdlib
  analog of ``git diff --stat`` — classified code / tests / docs / sessions;
- git **HEAD movement** since the anchor (commits happened / nothing
  committed yet);
- the **derived verify command** (the adopt-time ``verify_command`` slot) —
  the engine cannot execute it, so the draft carries it as a run-and-record
  slot rather than fake results (the console's no-fake-data rule).

The drafted text marks every judgment-only field with a ``[[fill: …]]`` slot
and the card with ``<!-- substrate:auto-draft -->``; the session-log checker
counts unresolved slots, so a **drafted-but-unedited card is distinguishable
from a completed one** and the born-red gate keeps holding until the slots
resolve. Everything here is fail-open by contract: drafting can never crash a
hook or ``session-close``.
"""




# State key for the session-start evidence anchor.
SESSION_ANCHOR_KEY = "session_anchor"
# Provenance marker stamped into every auto-drafted card/section.
DRAFT_MARKER = "<!-- substrate:auto-draft -->"

# Directories the evidence scan never descends into (vendored/derived trees;
# ``.git`` and the configured state_dir are excluded separately).
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".eggs",
    },
)
_CODE_SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".rb",
        ".c",
        ".h",
        ".cpp",
        ".sh",
    },
)
# Rendering cap per evidence category — a giant session lists the head + a
# "+N more" tail instead of flooding the card.
_EVIDENCE_RENDER_CAP = 15
_SHA_LEN = 9


def _fill(hint: str) -> str:
    """Return one unresolved judgment slot for the drafted text."""
    return f"{DRAFT_FILL_TOKEN} {hint}]]"


# ---------------------------------------------------------------------------
# Git evidence — pure file parsing (subprocess is banned in engine code)
# ---------------------------------------------------------------------------


def _git_dir(root: Path) -> Path | None:
    """Resolve ``root``'s git directory (handles worktree ``gitdir:`` files)."""
    dot = root / ".git"
    if dot.is_dir():
        return dot
    if dot.is_file():
        text = dot.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            if not gitdir.is_absolute():
                gitdir = (root / gitdir).resolve()
            if gitdir.is_dir():
                return gitdir
    return None


def _git_common_dir(git_dir: Path) -> Path:
    """Return the shared git dir (worktrees keep refs in ``commondir``)."""
    pointer = git_dir / "commondir"
    if pointer.is_file():
        common = Path(pointer.read_text(encoding="utf-8", errors="replace").strip())
        if not common.is_absolute():
            common = (git_dir / common).resolve()
        if common.is_dir():
            return common
    return git_dir


def _resolve_ref(git_dir: Path, ref: str) -> str | None:
    """Resolve a symbolic ref to a sha via loose refs, then ``packed-refs``."""
    common = _git_common_dir(git_dir)
    for base in (git_dir, common):
        loose = base / ref
        if loose.is_file():
            sha = loose.read_text(encoding="utf-8", errors="replace").strip()
            return sha or None
    packed = common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(("#", "^")):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() == ref:
                return parts[0].strip() or None
    return None


def read_git_head(root: Path) -> tuple[str | None, str | None]:
    """Return ``(branch, sha)`` for ``root``'s HEAD — ``(None, None)`` on any failure.

    Pure file parsing (``HEAD`` → loose ref → ``packed-refs``), worktree-aware.
    Fail-open by contract: evidence gathering must never raise into a hook.
    """
    try:
        git_dir = _git_dir(root)
        if git_dir is None:
            return (None, None)
        head = (git_dir / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        if head.startswith("ref:"):
            ref = head.split(":", 1)[1].strip()
            branch = ref[len("refs/heads/") :] if ref.startswith("refs/heads/") else ref
            return (branch, _resolve_ref(git_dir, ref))
        # Detached HEAD: the file holds the sha itself.
        if len(head) >= 40 and all(c in "0123456789abcdef" for c in head.lower()):
            return (None, head)
        return (None, None)
    except Exception:  # fail open — git evidence is best-effort by contract
        return (None, None)


# ---------------------------------------------------------------------------
# The session-start anchor
# ---------------------------------------------------------------------------


def record_session_anchor(root: Path, config: Config, backend: Any) -> None:
    """Record this session's evidence anchor into state (fail-open).

    Stores ``{ts, epoch, head, branch}`` under ``state["session_anchor"]``.
    A same-day re-fire (SessionStart runs again on resume/clear) keeps the
    original anchor so mid-session resumes don't hide earlier changes; a
    stale anchor from a previous day is overwritten.
    """
    try:
        now = datetime.now(timezone.utc)
        existing = backend.data.get(SESSION_ANCHOR_KEY) if backend.data else None
        if isinstance(existing, dict):
            ts = existing.get("ts")
            if isinstance(ts, str) and ts[:10] == now.date().isoformat():
                return
        branch, sha = read_git_head(root)
        backend.set(
            SESSION_ANCHOR_KEY,
            {
                "ts": now.isoformat(timespec="seconds"),
                "epoch": now.timestamp(),
                "head": sha,
                "branch": branch,
            },
        )
    except Exception:  # fail open — anchoring must never crash a session start
        return


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------


@dataclass
class SessionEvidence:
    """What the engine can see about this session without being told."""

    anchor_ts: str | None = None
    anchor_epoch: float | None = None
    branch: str | None = None
    head_start: str | None = None
    head_now: str | None = None
    verify_command: str | None = None
    # category -> sorted relative paths; categories: code/tests/docs/sessions/other
    changed: dict[str, list[str]] = field(default_factory=dict)


def _classify(rel: str, config: Config) -> str:
    """Classify one changed path into an evidence category."""
    parts = Path(rel).parts
    if parts and parts[0] == config.sessions_dir:
        return "sessions"
    if parts and parts[0] == config.docs_root:
        return "docs"
    name = Path(rel).name
    if any(p in ("tests", "test") for p in parts[:-1]) or name.startswith("test_"):
        return "tests"
    if Path(rel).suffix.lower() in _CODE_SUFFIXES:
        return "code"
    return "other"


def _changed_since(root: Path, config: Config, epoch: float) -> dict[str, list[str]]:
    """Return files modified after ``epoch``, classified — the mtime diff scan."""
    changed: dict[str, list[str]] = {}
    skip = set(_SKIP_DIR_NAMES) | {config.state_dir}
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in skip and not entry.is_symlink():
                    stack.append(entry)
                continue
            try:
                if entry.stat().st_mtime <= epoch:
                    continue
            except OSError:
                continue
            rel = str(entry.relative_to(root))
            changed.setdefault(_classify(rel, config), []).append(rel)
    return {category: sorted(paths) for category, paths in sorted(changed.items())}


def gather_evidence(root: Path, config: Config, state: dict[str, Any]) -> SessionEvidence:
    """Collect the drafting evidence (fail-open — a partial view beats none)."""
    evidence = SessionEvidence()
    try:
        anchor = state.get(SESSION_ANCHOR_KEY)
        if isinstance(anchor, dict):
            ts, epoch = anchor.get("ts"), anchor.get("epoch")
            evidence.anchor_ts = ts if isinstance(ts, str) else None
            evidence.anchor_epoch = float(epoch) if isinstance(epoch, (int, float)) else None
            head = anchor.get("head")
            evidence.head_start = head if isinstance(head, str) else None
        evidence.branch, evidence.head_now = read_git_head(root)
        values = state.get("slot_values")
        if isinstance(values, dict):
            entry = values.get("verify_command")
            if isinstance(entry, dict) and isinstance(entry.get("value"), str):
                evidence.verify_command = entry["value"]
        if evidence.anchor_epoch is not None:
            evidence.changed = _changed_since(root, config, evidence.anchor_epoch)
    except Exception:  # fail open — return whatever was gathered so far
        return evidence
    return evidence


# ---------------------------------------------------------------------------
# Draft composition
# ---------------------------------------------------------------------------


def _evidence_lines(evidence: SessionEvidence) -> list[str]:
    """Render the auto-collected evidence as card bullet lines."""
    lines: list[str] = []
    if evidence.anchor_epoch is None:
        lines.append(
            "- files touched: unknown — no session-start anchor recorded "
            "(the SessionStart hook / `session-start` records it at boot).",
        )
    elif not evidence.changed:
        lines.append(
            f"- no files changed since session start ({evidence.anchor_ts}).",
        )
    else:
        for category, paths in evidence.changed.items():
            head = ", ".join(f"`{p}`" for p in paths[:_EVIDENCE_RENDER_CAP])
            tail = len(paths) - _EVIDENCE_RENDER_CAP
            more = f" (+{tail} more)" if tail > 0 else ""
            lines.append(f"- {category} touched ({len(paths)}): {head}{more}")
    if evidence.branch or evidence.head_now:
        branch = f"branch `{evidence.branch}`" if evidence.branch else "detached HEAD"
        start, now = evidence.head_start, evidence.head_now
        if start and now and start != now:
            movement = f"HEAD {start[:_SHA_LEN]} → {now[:_SHA_LEN]} (commits made this session)"
        elif start and now:
            movement = f"HEAD unchanged at {now[:_SHA_LEN]} (nothing committed yet)"
        elif now:
            movement = f"HEAD {now[:_SHA_LEN]}"
        else:
            movement = "HEAD unresolved"
        lines.append(f"- git: {branch}, {movement}.")
    if evidence.verify_command:
        lines.append(
            f"- verify: run `{evidence.verify_command}` and record the result "
            f"→ {_fill('verify result — the engine cannot execute commands')}",
        )
    else:
        lines.append(f"- verify: {_fill('how this session was verified (command + result)')}")
    return lines


# Label -> drafted stand-in line for the default session markers. Unknown
# host-configured markers get a generic needle-carrying line so resolving the
# slot satisfies the marker too.
def _marker_line(marker: dict[str, str]) -> str | None:
    """Return the drafted stand-in for one missing session marker."""
    label = marker.get("label", "")
    needle = marker.get("needle", "")
    if not needle or needle == "**Status:**":
        return None
    if label == "Session idea":
        return f"## 💡 Session idea\n\n{_fill('one idea you genuinely believe in — never filler')}"
    if label == "Previous-session review":
        return (
            "## ⟲ Previous-session review\n\n"
            f"{_fill('one genuine remark on the previous session + one workflow improvement')}"
        )
    if label == "Model line":
        return (
            f"- **\N{BAR CHART} Model:** {_fill('model')} \N{MIDDLE DOT} "
            f"{_fill('effort')} \N{MIDDLE DOT} {_fill('task-class (Q-0248 taxonomy)')}"
        )
    return f"- {needle} {_fill(label or 'resolve this marker')}"


def draft_close_out(
    evidence: SessionEvidence,
    markers: list[dict[str, str]] | None = None,
) -> str:
    """Compose the drafted close-out section (evidence + judgment slots).

    ``markers`` — the session markers still missing from the card, each drafted
    as a needle-carrying stand-in so one edit pass resolves everything.
    """
    parts = [
        f"## Close-out (auto-drafted {date.today().isoformat()} — edit, don't author)",
        "",
        DRAFT_MARKER,
        "",
        "**Evidence (auto-collected — verify, then keep or correct):**",
        "",
        *_evidence_lines(evidence),
        "",
        "**Judgment (the half only the session knows — resolve every slot):**",
        "",
        f"- Decisions made: {_fill('decisions taken this session, or none')}",
        f"- Next session should know: {_fill('the handoff pointer — where to pick up')}",
    ]
    for marker in markers or []:
        line = _marker_line(marker)
        if line:
            parts += ["", line]
    return "\n".join(parts) + "\n"


def draft_card(slug: str, evidence: SessionEvidence, config: Config) -> str:
    """Compose a full drafted skeleton card (the missing-card path)."""
    body = draft_close_out(evidence, list(config.session_markers))
    return (
        f"# Session {slug}\n\n"
        "> **Status:** `drafted` *(auto-drafted by substrate-kit — edit the\n"
        "> close-out, resolve every `[[fill:]]` slot, then flip this badge to\n"
        "> `complete`.)*\n\n"
        f"{body}"
    )


# ---------------------------------------------------------------------------
# The drafting orchestrator (both write-back surfaces call this)
# ---------------------------------------------------------------------------


def _unique_card_path(sessions_dir: Path, day: str) -> Path:
    """Return a non-colliding path for a drafted skeleton card."""
    path = sessions_dir / f"{day}-session.md"
    serial = 2
    while path.exists():
        path = sessions_dir / f"{day}-session-{serial}.md"
        serial += 1
    return path


def ensure_draft(root: Path, config: Config, backend: Any) -> list[str]:
    """Draft the session card / close-out from evidence; return advisory lines.

    The mechanized write-back seam (`session-close` and the Stop hook both run
    it): a missing card gets a drafted skeleton; an in-progress card missing
    close-out markers gets the drafted section appended; a card already
    drafted is only counted (unresolved slots); a completed card is never
    touched. Fail-open by contract — any failure returns ``[]`` rather than
    raising into a hook.
    """
    try:
        try:
            state = dict(backend.data) if backend.data else {}
        except Exception:
            state = {}
        evidence = gather_evidence(root, config, state)
        sessions_dir = root / config.sessions_dir
        card = latest_session_log(sessions_dir)
        if (
            card is not None
            and evidence.anchor_epoch is not None
            and card.stat().st_mtime <= evidence.anchor_epoch
        ):
            card = None  # newest card predates this session — not ours
        if card is None:
            day = date.today().isoformat()
            path = _unique_card_path(sessions_dir, day)
            atomic_write_text(path, draft_card(f"{day} — {path.stem}", evidence, config))
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            return [
                f"session card was missing — auto-drafted {rel}: verify the "
                "evidence, resolve the [[fill:]] slots, flip Status to complete",
            ]
        text = card.read_text(encoding="utf-8")
        if DRAFT_MARKER in text or DRAFT_FILL_TOKEN in text:
            slots = text.count(DRAFT_FILL_TOKEN)
            if slots:
                return [
                    f"auto-draft in {card.name}: {slots} [[fill:]] slot(s) still "
                    "unresolved — the card counts drafted, not completed",
                ]
            return []
        if not status_in_progress(text):
            return []  # completed card — consumer-owned, never touched
        missing = check_log(card, config.session_markers)
        missing_misses = {m for m in missing if not m.startswith("a completed Status")}
        if not missing_misses:
            return []  # close-out already written; only the status flip remains
        # check_log reports each miss as "label (expected `needle`)" — map it
        # back to the configured marker via the same formatter so the drafted
        # stand-ins can never drift from what the checker said was missing.
        markers = [m for m in config.session_markers if _marker_miss(m) in missing_misses]
        section = draft_close_out(evidence, markers)
        atomic_write_text(card, text.rstrip("\n") + "\n\n" + section)
        return [
            f"auto-drafted close-out appended to {card.name} — verify the "
            "evidence, resolve the [[fill:]] slots, flip the Status badge",
        ]
    except Exception:  # fail open — drafting must never crash a hook
        return []

# --- engine/loop/episodes.py ---
"""Episodic index — a tiny searchable memory over session logs (plan lane B2).

Each session log becomes one compact ``{"slug", "date", "tags", "summary"}``
record in ``<state_dir>/episodic_index.json``, so an agent can grep *which*
past session touched a topic without reading every log top-to-bottom. Tags
come from the log's first heading (minus stopwords) plus the workflow's marker
emojis (💡 idea, ⚑ flag, ⟲ review, 📊 telemetry). The index is a derived
artifact: rebuildable from the logs at any time, written atomically, and
fail-open on absence/corruption.
"""




EPISODIC_INDEX_FILENAME = "episodic_index.json"

_EPI_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
_EPI_WORD_RE = re.compile(r"[a-z0-9][\w-]*")
_EPI_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    },
)
_EPI_MARKERS = (
    "\N{ELECTRIC LIGHT BULB}",  # 💡 session idea
    "\N{BLACK FLAG}",  # ⚑ self-initiated / friction flag
    "\N{ANTICLOCKWISE GAPPED CIRCLE ARROW}",  # ⟲ previous-session review
    "\N{BAR CHART}",  # 📊 telemetry / KPI footer
)
_EPI_SUMMARY_LIMIT = 140


def _epi_load(index_path: Path) -> list[dict]:
    """Return the index entries at ``index_path`` — ``[]`` on absent/corrupt."""
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _epi_save(index_path: Path, entries: list[dict]) -> None:
    """Write ``entries`` to ``index_path`` atomically as pretty-printed JSON."""
    atomic_write_text(index_path, json.dumps(entries, indent=2) + "\n")


def _epi_tags(text: str) -> list[str]:
    """Tags: first ``# `` heading words minus stopwords, plus marker emojis."""
    tags: list[str] = []
    for line in text.splitlines():
        if line.startswith("# "):
            words = _EPI_WORD_RE.findall(line[2:].lower())
            tags.extend(word for word in words if word not in _EPI_STOPWORDS)
            break
    tags.extend(mark for mark in _EPI_MARKERS if mark in text)
    return list(dict.fromkeys(tags))


def _epi_summary(text: str) -> str:
    """Return the first non-blank non-heading line, truncated to 140 chars."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:_EPI_SUMMARY_LIMIT]
    return ""


def index_session(log_path: Path) -> dict:
    """Summarise one session log into ``{"slug", "date", "tags", "summary"}``.

    ``slug`` and ``date`` parse from the ``YYYY-MM-DD-<slug>.md`` filename
    convention; a non-conforming name degrades gracefully to the whole stem as
    the slug with an empty date. An unreadable file yields empty tags/summary.
    """
    match = _EPI_NAME_RE.match(log_path.stem)
    if match:
        session_date, slug = match.group(1), match.group(2)
    else:
        session_date, slug = "", log_path.stem
    try:
        text = log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    return {
        "slug": slug,
        "date": session_date,
        "tags": _epi_tags(text),
        "summary": _epi_summary(text),
    }


def rebuild_episodic_index(sessions_dir: Path, index_path: Path) -> list[dict]:
    """Rebuild the whole index from ``sessions_dir`` and write it atomically.

    Scans ``*.md`` excluding ``README.md``, sorted by filename (the date-first
    naming convention makes that chronological). Returns the entries written;
    an absent sessions dir yields an empty index.
    """
    logs: list[Path] = []
    if sessions_dir.is_dir():
        logs = sorted(p for p in sessions_dir.glob("*.md") if p.name != "README.md")
    entries = [index_session(p) for p in logs]
    _epi_save(index_path, entries)
    return entries


def append_episode(index_path: Path, entry: dict) -> None:
    """Add ``entry`` to the index, replacing an existing (slug, date) match.

    Keyed on slug *and* date: re-indexing the same log updates in place, while
    a same-slug session from a different day appends instead of silently
    deleting the earlier episode.
    """
    entries = _epi_load(index_path)
    key = (entry.get("slug"), entry.get("date"))
    for i, existing in enumerate(entries):
        if (existing.get("slug"), existing.get("date")) == key:
            entries[i] = entry
            break
    else:
        entries.append(entry)
    _epi_save(index_path, entries)


def search_episodes(index_path: Path, tag: str) -> list[dict]:
    """Return every indexed episode carrying ``tag`` in its tag list."""
    return [entry for entry in _epi_load(index_path) if tag in entry.get("tags", [])]

# --- engine/loop/triggers.py ---
"""Trigger scan for the self-improving loop (plan section 5, Lane B1).

The loop's sensory layer: ``check_triggers`` inspects the project tree plus the
state document and reports which of the five trigger kinds fired —

- ``critical_unfilled`` — a graduation-critical slot is still not ``filled``
  after the cadence's grace window (one trigger per slot).
- ``blocking_open``     — escalated blocking questions sit on
  ``state["open_questions"]``.
- ``drift``             — the doc-hygiene checks (badge / link / reachable)
  report findings.
- ``staleness``         — the newest session log is older than
  ``cadence["staleness_days"]`` days, or reconciliation is overdue by session
  count.
- ``new_area``          — a direct subdirectory of the docs root holds only
  unreachable *and* unbadged markdown (nobody owns it yet).

``mandatory_questions`` then maps fired triggers back onto question-bank
entries, and ``trigger_block`` renders the orientation text block. The mode
policy (``engine.lib.modes.triggers_mandate``) decides whether the block is a
mandate or an advisory — this module only renders whichever the caller picked.
Pure stdlib; returns data / text, never prints.
"""




_TRG_PRIORITY_ORDER = {"blocking": 0, "high": 1, "normal": 2}
_TRG_SECONDS_PER_DAY = 86_400.0


class Trigger(NamedTuple):
    """One fired trigger: kind, severity, human message, related question ids."""

    kind: str
    severity: str
    message: str
    question_ids: tuple[str, ...]


def _trg_critical_unfilled(
    state: dict[str, Any],
    cadence: dict[str, int],
    bank: list[dict],
) -> list[Trigger]:
    """One trigger per critical slot still unfilled past the grace window."""
    grace = int(cadence.get("critical_slot_grace_sessions", 3))
    if int(state.get("session_count", 0)) <= grace:
        return []
    slots = state.get("slots", {})
    critical = dict.fromkeys(q["slot"] for q in bank if q.get("critical"))
    triggers: list[Trigger] = []
    for slot in critical:
        if slots.get(slot) == "filled":
            continue
        ids = tuple(q["id"] for q in bank if q["slot"] == slot)
        message = (
            f"critical slot '{slot}' is not filled after the "
            f"{grace}-session grace window"
        )
        triggers.append(Trigger("critical_unfilled", "blocking", message, ids))
    return triggers


def _trg_blocking_open(state: dict[str, Any]) -> list[Trigger]:
    """One trigger when escalated blocking questions are open."""
    open_questions = [str(q) for q in state.get("open_questions", [])]
    if not open_questions:
        return []
    listed = ", ".join(open_questions)
    message = f"{len(open_questions)} blocking question(s) open: {listed}"
    return [Trigger("blocking_open", "blocking", message, tuple(open_questions))]


def _trg_drift(docs_root: Path, config: Config) -> list[Trigger]:
    """One trigger when the doc-hygiene checks report any finding."""
    findings = run_doc_checks(docs_root, config.badge_tokens, config.readpath_docs)
    if not findings:
        return []
    kinds = ", ".join(sorted({f.kind for f in findings}))
    message = f"doc hygiene reports {len(findings)} finding(s) ({kinds})"
    return [Trigger("drift", "high", message, ())]


def _trg_staleness(
    state: dict[str, Any],
    cadence: dict[str, int],
    sessions_dir: Path,
) -> list[Trigger]:
    """One trigger when memory looks stale (old log or overdue reconciliation)."""
    reasons: list[str] = []
    stale_days = int(cadence.get("staleness_days", 14))
    newest = latest_session_log(sessions_dir)
    if newest is not None:
        age_days = (time.time() - newest.stat().st_mtime) / _TRG_SECONDS_PER_DAY
        if age_days > stale_days:
            reasons.append(
                f"newest session log is {int(age_days)} days old "
                f"(threshold {stale_days})",
            )
    overdue = int(cadence.get("reconciliation_sessions", 20))
    since = int(state.get("session_count", 0)) - int(
        state.get("last_compaction_session", 0),
    )
    if since >= overdue:
        reasons.append(
            f"{since} sessions since the last compaction (cadence {overdue})",
        )
    if not reasons:
        return []
    return [Trigger("staleness", "normal", "; ".join(reasons), ())]


def _trg_new_area(docs_root: Path, config: Config) -> list[Trigger]:
    """One trigger per docs subdirectory whose docs are all orphaned + unbadged."""
    if not docs_root.is_dir():
        return []
    orphans = {f.path for f in check_reachable(docs_root, config.readpath_docs)}
    triggers: list[Trigger] = []
    for sub in sorted(p for p in docs_root.iterdir() if p.is_dir()):
        files = sorted(sub.rglob("*.md"))
        if not files:
            continue
        all_unowned = all(
            f.relative_to(docs_root).as_posix() in orphans and badge_token(f) is None
            for f in files
        )
        if all_unowned:
            message = (
                f"new docs area '{sub.name}/' ({len(files)} file(s)) is "
                "entirely unreachable and unbadged — no ownership entry yet"
            )
            triggers.append(Trigger("new_area", "high", message, ()))
    return triggers


def check_triggers(
    root: Path,
    config: Config,
    state: dict[str, Any],
    bank: list[dict] | None = None,
) -> list[Trigger]:
    """Scan the project tree + state and return every fired trigger.

    ``root`` is the project root; the docs root and sessions dir are resolved
    from ``config``. Returns triggers grouped by kind in the fixed order
    critical_unfilled, blocking_open, drift, staleness, new_area.
    """
    bank = QUESTIONS if bank is None else bank
    cadence = dict(config.cadence or {})
    docs_root = root / config.docs_root
    sessions_dir = root / config.sessions_dir
    return (
        _trg_critical_unfilled(state, cadence, bank)
        + _trg_blocking_open(state)
        + _trg_drift(docs_root, config)
        + _trg_staleness(state, cadence, sessions_dir)
        + _trg_new_area(docs_root, config)
    )


def mandatory_questions(
    triggers: list[Trigger],
    bank: list[dict] | None = None,
) -> list[dict]:
    """Return the bank questions the fired triggers pull into this session.

    Selects entries whose ``trigger`` field matches a fired kind, plus the
    entries a ``critical_unfilled`` trigger names via ``question_ids``.
    De-duplicated by id; priority-ordered (blocking, high, normal — stable).
    """
    bank = QUESTIONS if bank is None else bank
    fired_kinds = {t.kind for t in triggers}
    named_ids = {
        qid for t in triggers if t.kind == "critical_unfilled" for qid in t.question_ids
    }
    selected: list[dict] = []
    seen: set[str] = set()
    for question in bank:
        wanted = question.get("trigger") in fired_kinds or question["id"] in named_ids
        if wanted and question["id"] not in seen:
            seen.add(question["id"])
            selected.append(question)
    return sorted(
        selected,
        key=lambda q: _TRG_PRIORITY_ORDER.get(q.get("priority", "normal"), 2),
    )


def trigger_block(
    triggers: list[Trigger],
    questions: list[dict],
    *,
    mandate: bool,
) -> str:
    """Render the orientation trigger block ('' when nothing fired).

    ``mandate=True`` (guided/active modes) opens with a MANDATORY
    question-session header; otherwise the block is an advisory.
    """
    if not triggers:
        return ""
    if mandate:
        header = "## ⚠️ MANDATORY question session — triggers fired"
    else:
        header = "## Trigger advisory (non-mandatory)"
    lines = [header, ""]
    lines += [f"- [{t.severity}] {t.kind}: {t.message}" for t in triggers]
    if questions:
        lines += ["", "Questions to ask this session:"]
        lines += [
            f"- {q['id']} ({q.get('priority', 'normal')}): {q['prompt']}"
            for q in questions
        ]
    return "\n".join(lines) + "\n"

# --- engine/loop/maintenance.py ---
"""Maintenance actuators for the self-improving loop (plan section 5, Lane B3).

The loop's housekeeping arm: the compaction cadence and its pre-compaction
"State Delta" snapshot, the escalated open-question list (the blocking-question
brake graduation waits on), the promotion-rights downgrade, and the composed
``maintain`` human report. Pure stdlib; every file write goes through
``atomic_write_text``; functions return data / text, never print — the CLI
owns all output.

The sibling loop modules (``reflections``, ``kpis``, ``review_seam``) are
imported lazily with fail-open fallbacks, so this module keeps working when a
build ships without them (the single-file bootstrap concatenation case).
"""




_MNT_VALUE_WIDTH = 80


def compaction_due(state: dict[str, Any], cadence: dict[str, int]) -> bool:
    """True when the compaction cadence window has elapsed.

    Fires when ``session_count - last_compaction_session`` reaches
    ``cadence["compaction_sessions"]`` (default 20).

    Deliberate reduction of the plan's "~700K tokens OR 20 sessions": the kit
    has no token telemetry (stdlib-only, no provider hooks), so only the
    session-count half ships; hosts with token accounting can trigger
    ``run_compaction`` directly when their own meter trips.
    """
    every = int(cadence.get("compaction_sessions", 20))
    since = int(state.get("session_count", 0)) - int(
        state.get("last_compaction_session", 0),
    )
    return since >= every


def _mnt_cell(value: Any) -> str:
    """Collapse ``value`` to one table-safe line truncated to 80 chars."""
    text = " ".join(str(value).split()).replace("|", "/")
    return text[:_MNT_VALUE_WIDTH]


def _mnt_lesson_lines(reflections: list[dict]) -> list[str]:
    """Render the active-lesson lines from the reflection entries."""
    live = active_lessons(reflections, len(reflections))
    return [f"- [{e.get('id', '?')}] {e.get('lesson', '')}" for e in live]


def _mnt_slot_lines(state: dict[str, Any]) -> list[str]:
    """Render the slot table (name-sorted; values truncated to 80 chars)."""
    slots = state.get("slots", {})
    if not slots:
        return []
    values = state.get("slot_values", {})
    lines = ["| slot | status | value |", "| --- | --- | --- |"]
    for slot in sorted(slots):
        entry = values.get(slot, {})
        value = entry.get("value", "") if isinstance(entry, dict) else entry
        lines.append(f"| {slot} | {slots[slot]} | {_mnt_cell(value)} |")
    return lines


def state_delta(state: dict[str, Any], reflections: list[dict]) -> str:
    """Render the pre-compaction State Delta markdown — dense, deterministic.

    The counters line always appears; the slot table, open-questions list, and
    active-lessons list appear only when non-empty. No timestamps: two calls
    over the same inputs return identical text.
    """
    lines = [
        f"# State Delta — session {int(state.get('session_count', 0))}",
        "",
        f"- mode: {state.get('mode', '?')} · stage: {state.get('stage', '?')} · "
        f"sessions: {int(state.get('session_count', 0))} · "
        f"quiet: {int(state.get('quiet_sessions', 0))}",
    ]
    slot_lines = _mnt_slot_lines(state)
    if slot_lines:
        lines += ["", "## Slots", "", *slot_lines]
    open_questions = [str(q) for q in state.get("open_questions", [])]
    if open_questions:
        lines += ["", "## Open questions", ""]
        lines += [f"- {qid}" for qid in open_questions]
    lesson_lines = _mnt_lesson_lines(reflections)
    if lesson_lines:
        lines += ["", "## Active lessons", "", *lesson_lines]
    return "\n".join(lines) + "\n"


def _mnt_load_reflections(state_dir: Path) -> list[dict]:
    """Load the reflection buffer for the delta (``[]`` when unavailable)."""
    return load_reflections(state_dir / REFLECTIONS_FILENAME)


def run_compaction(root: Path, config: Config, backend: Any) -> Path:
    """Write the State Delta snapshot and reset the compaction counter.

    Writes ``<state_dir>/state-delta-<session_count>.md`` atomically, then
    stamps ``last_compaction_session`` so ``compaction_due`` stays quiet until
    the next cadence window. Returns the written path.
    """
    state_dir = root / config.state_dir
    session = int(backend.get("session_count", 0))
    delta = state_delta(backend.data, _mnt_load_reflections(state_dir))
    path = state_dir / f"state-delta-{session}.md"
    atomic_write_text(path, delta)
    backend.set("last_compaction_session", session)
    return path


def escalate_blocking(backend: Any, question_id: str) -> bool:
    """Append ``question_id`` to the escalated open-questions list once.

    Idempotent: True when it appended, False when the id was already open.
    Open questions hold graduation until answered (the blocking brake).
    """
    open_questions = list(backend.get("open_questions", []))
    if question_id in open_questions:
        return False
    open_questions.append(question_id)
    backend.set("open_questions", open_questions)
    return True


def resolve_open_question(backend: Any, question_id: str) -> bool:
    """Drop ``question_id`` from the open-questions list; False when absent."""
    open_questions = list(backend.get("open_questions", []))
    if question_id not in open_questions:
        return False
    open_questions.remove(question_id)
    backend.set("open_questions", open_questions)
    return True


def downgrade_promotion(backend: Any, *, reason: str) -> None:
    """Cap autonomy: ``promotion_rights`` → ``"propose"``, logged with why.

    Appends a ``promotion_downgrade`` event to ``review_log`` so the loss of
    apply-rights always carries its provenance.
    """
    log = list(backend.get("review_log", []))
    log.append(
        {
            "event": "promotion_downgrade",
            "reason": reason,
            "date": date.today().isoformat(),
        },
    )
    with backend.transaction():
        backend.set("promotion_rights", "propose")
        backend.set("review_log", log)


def _mnt_item_line(item: Any) -> str:
    """Render one report line for a trigger or a checker finding.

    Triggers (kind/severity/message) render like the orientation block;
    findings (path/kind/message) render path-first; anything else renders as
    its ``str``.
    """
    kind = getattr(item, "kind", None)
    message = getattr(item, "message", None)
    if kind is None or message is None:
        return f"- {item}"
    severity = getattr(item, "severity", None)
    if severity is not None:
        return f"- [{severity}] {kind}: {message}"
    path = getattr(item, "path", None)
    prefix = f"{path}: " if path else ""
    return f"- {prefix}[{kind}] {message}"


def _mnt_review_dir() -> str:
    """Return the review-payload directory name.

    Mirrors ``review_seam.REVIEW_DIR`` as a literal: ``review_seam`` imports
    this module at top level, so importing it back would be circular — the
    seam's own test pins the two values equal.
    """
    return "review"


def _mnt_advisories(root: Path, config: Config, backend: Any) -> list[str]:
    """Return the maintenance advisories: compaction due, payloads waiting."""
    advisories: list[str] = []
    if compaction_due(backend.data, dict(config.cadence or {})):
        advisories.append("compaction due — write the State Delta snapshot")
    review_dir = root / config.state_dir / _mnt_review_dir()
    if review_dir.is_dir():
        pending = sorted(review_dir.glob("payload-*.json"))
        if pending:
            advisories.append(
                f"{len(pending)} review payload(s) awaiting a reviewer",
            )
    return advisories


def _mnt_footer(kpis: dict[str, Any]) -> str:
    """Render the KPI footer line for the report."""
    return kpi_footer(kpis)


def maintenance_report(
    root: Path,
    config: Config,
    backend: Any,
    *,
    triggers: list[Any],
    economy_findings: list[Any],
    ledger_findings: list[Any],
    kpis: dict[str, Any],
) -> str:
    """Compose the ``maintain`` human report from the loop's sensor outputs.

    Every section is skipped when its input is empty; a maintenance-advisories
    section surfaces compaction cadence and accumulated review payloads (the
    no-reviewer graceful fallback); the report ends with the KPI footer when
    ``kpis`` is non-empty.
    """
    lines = [
        f"# Maintenance report — session {int(backend.get('session_count', 0))}",
    ]
    sections: tuple[tuple[str, list[Any]], ...] = (
        ("Triggers", triggers),
        ("Economy findings", economy_findings),
        ("Ledger findings", ledger_findings),
    )
    for title, items in sections:
        if not items:
            continue
        lines += ["", f"## {title}", ""]
        lines += [_mnt_item_line(item) for item in items]
    advisories = _mnt_advisories(root, config, backend)
    if advisories:
        lines += ["", "## Maintenance", ""]
        lines += [f"- {advisory}" for advisory in advisories]
    if kpis:
        lines += ["", _mnt_footer(kpis)]
    return "\n".join(lines) + "\n"

# --- engine/loop/review_seam.py ---
"""The external-review seam — provisioned, not wired (plan section 6, Lane B3).

A second model can audit the interview's provisional self-answers, but the kit
never talks to one (no subprocess, no network): it emits an **anti-anchor**
payload — the proposition and its evidence, NO confidence score, NO author
commentary — and the host records the verdict through one entry point. With no
reviewer configured, payloads simply accumulate for the owner; nothing blocks.
Pure stdlib; writes via ``atomic_write_text``.
"""




REVIEW_DIR = "review"

# Deterministic checks first — the reviewer runs mechanical verification
# before exercising judgment; subjective slots route straight to the owner.
_REV_OBJECTIVE_STOPS = (
    "verify against repository source",
    "run the project verify command",
)
_REV_SUBJECTIVE_STOPS = ("route to the owner - subjective slot",)

_REV_WIRING_DOC = """\
# Review seam — provisioned, not wired

The kit never calls an external model. It defines a payload format and two
entry points; the host wires ANY reviewer (a second model, a CLI, a human)
around them:

1. `bootstrap review build <slot>` emits the payload JSON to
   `<state_dir>/review/payload-<slot>.json`.
2. The external reviewer reads ONLY that payload — never the chat context,
   never the author's notes or working files.
3. The host records the verdict:
   `bootstrap review confirm <slot> --verdict pass|fail --reviewer <name>`.
   A `pass` on an objective slot confirms it; a `pass` on a subjective slot is
   recorded but the slot stays provisional (only the owner confirms taste);
   a `fail` escalates the question as blocking and downgrades promotion
   rights to propose-only.

Graceful no-reviewer fallback: with no reviewer configured, payloads simply
accumulate in the review directory for the owner to work through — nothing
blocks, and the maintenance report counts them.

Anti-anchor rule: the payload carries the proposition, its evidence, and
deterministic stop conditions — NO confidence score and NO author commentary,
so the reviewer cannot anchor on the author's own belief.

Unverified reviewer: calibrate a new reviewer against known-answer issues
before trusting its dissent — a verdict that fights the evidence is the
reviewer's bug until proven otherwise.
"""


def _rev_bank_entry(slot: str) -> dict:
    """Return the question-bank entry for ``slot`` (``{}`` when unknown)."""
    for question in QUESTIONS:
        if question.get("slot") == slot:
            return question
    return {}


def _rev_slot_value(backend: Any, slot: str) -> dict:
    """Return the recorded slot-value entry for ``slot`` (``{}`` when absent)."""
    entry = dict(backend.get("slot_values", {})).get(slot, {})
    return entry if isinstance(entry, dict) else {}


def build_review_payload(backend: Any, slot: str) -> dict:
    """Build the anti-anchor review payload for a provisional ``slot``.

    The payload carries the proposition and its evidence ONLY — no confidence
    score, no author commentary — so the reviewing model cannot anchor on the
    author's belief. Objective slots get deterministic stop conditions first;
    subjective slots route to the owner. Returns ``{}`` when the slot is not
    provisional (nothing to review). Never raises ``KeyError``.
    """
    if dict(backend.get("slots", {})).get(slot) != "provisional":
        return {}
    entry = _rev_slot_value(backend, slot)
    question = _rev_bank_entry(slot)
    objective = bool(question.get("objective", False))
    stops = _REV_OBJECTIVE_STOPS if objective else _REV_SUBJECTIVE_STOPS
    evidence = (
        f"question: {question.get('prompt', '')} | "
        f"recorded source: {entry.get('source', '')}"
    )
    return {
        "format_version": 1,
        "slot": slot,
        "proposition": entry.get("value", ""),
        "evidence": evidence,
        "stop_conditions": list(stops),
        "objective": objective,
    }


def write_review_payload(root: Path, config: Config, payload: dict) -> Path:
    """Write ``payload`` to ``<state_dir>/review/payload-<slot>.json``.

    Atomic, indented, key-sorted JSON; returns the written path.
    """
    slot = str(payload.get("slot", "unknown"))
    path = root / config.state_dir / REVIEW_DIR / f"payload-{slot}.json"
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def clear_review_payload(root: Path, config: Config, slot: str) -> bool:
    """Remove the consumed payload for ``slot``; True when one was present.

    A verdict recorded via ``apply_review_verdict`` consumes the payload, but the
    payload FILE persists — and ``maintenance._mnt_advisories`` counts every
    ``payload-*.json`` as "awaiting a reviewer", so without this the count never
    decrements after a review (it grows without bound under a wired reviewer).
    Idempotent: a missing payload is a no-op.
    """
    path = root / config.state_dir / REVIEW_DIR / f"payload-{slot}.json"
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def _rev_log(backend: Any, slot: str, verdict: str, reviewer: str) -> None:
    """Append one review-log entry (the state contract's four-field shape)."""
    log = list(backend.get("review_log", []))
    log.append(
        {
            "slot": slot,
            "verdict": verdict,
            "reviewer": reviewer,
            "date": date.today().isoformat(),
        },
    )
    backend.set("review_log", log)


def apply_review_verdict(
    backend: Any,
    slot: str,
    *,
    verdict: str,
    reviewer: str,
) -> str:
    """Record an external reviewer's verdict on a provisional slot.

    Three outcomes:

    - ``pass`` on an *objective* slot confirms it (provisional → filled,
      source ``reviewer:<name>``) → returns ``"confirmed"``.
    - ``pass`` on a *subjective* slot is recorded only — the slot stays
      provisional and promotion stays capped at propose → ``"recorded"``.
    - ``fail`` escalates the slot's question as blocking AND downgrades
      promotion rights to propose-only → ``"escalated"``.

    Every outcome appends a review-log entry. Raises ``ValueError`` on any
    verdict other than ``"pass"`` / ``"fail"``. A slot that is not currently
    ``provisional`` (typo'd, already confirmed, never answered) returns
    ``"not-provisional"`` untouched — mirroring ``build_review_payload``'s
    guard, so a stray verdict can neither falsely confirm nor escalate.
    """
    if verdict not in ("pass", "fail"):
        raise ValueError(f"unknown review verdict: {verdict!r}")
    if backend.get("slots", {}).get(slot) != "provisional":
        return "not-provisional"
    question = _rev_bank_entry(slot)
    # Each multi-write outcome is one transaction (Q-0223 tail ①): the escalate/
    # downgrade/log (and confirm/log) legs land together or not at all. The
    # helpers open their own transactions internally — safe, because the JSON
    # backend's transaction is re-entrant and only the outermost exit flushes.
    if verdict == "fail":
        question_id = str(_rev_slot_value(backend, slot).get("question_id", ""))
        question_id = question_id or str(question.get("id", slot))
        with backend.transaction():
            escalate_blocking(backend, question_id)
            downgrade_promotion(
                backend,
                reason=f"review fail on slot '{slot}' by {reviewer}",
            )
            _rev_log(backend, slot, verdict, reviewer)
        return "escalated"
    if question.get("objective", False):
        with backend.transaction():
            confirm_slot(backend, slot, source=f"reviewer:{reviewer}")
            _rev_log(backend, slot, verdict, reviewer)
        return "confirmed"
    _rev_log(backend, slot, verdict, reviewer)
    return "recorded"


def seam_wiring_doc() -> str:
    """Return the wiring instructions for hosting ANY external reviewer.

    The seam ships provisioned, not wired: the kit defines the payload format
    and the verdict entry points; the host decides which model (if any) reads
    the payloads — and without one, they accumulate gracefully for the owner.
    """
    return _REV_WIRING_DOC

# --- engine/economy/engine.py ---
"""The context-economy engine (plan §5.B, Lane B4).

The retention/taxonomy layer of the self-improving loop: docs are classified
into host-declared classes (badge- and/or glob-matched), gauges watch word and
count budgets, an inbound-reference scan protects cited files, and the actuator
applies the TRIPLE FILTER (harvested AND past window AND zero inbound refs)
before any deletion — writing one tombstone line per pruned file into a
per-band shard. Retention windows are measured in **days** from file mtime:
the kit supports day windows only; "bands" are a host cadence unit layered on
top of it, never a kit unit. ``economy["maturity"]`` gates the actuator —
``"shadow"`` never applies. Pure stdlib; returns data / text, never prints.
"""




# Minimal inline copy of check_docs._badge_token's regex (private there); drop
# once the helper is promoted to a public name in engine/checks/check_docs.py.
_ECO_BADGE_RE = re.compile(r"\*\*Status:\*\*\s*`([a-z-]+)`")

_ECO_SECONDS_PER_DAY = 86400.0


class EconomyFinding(NamedTuple):
    """One economy finding: ``path`` is relative to the project root."""

    path: str
    kind: str
    message: str


DEFAULT_CLASSES: list[dict] = [
    {
        "name": "sessions",
        "globs": ["<sessions_dir>/*.md"],
        "mode": "delete_tomb",
        "window_days": 14,
        "tombstone_dir": "<sessions_dir>/pruned",
    },
    {
        "name": "plans",
        "badges": ["plan"],
        "mode": "archive",
        "window_days": 60,
    },
    {
        "name": "living",
        "badges": ["living-ledger", "reference", "binding"],
        "mode": "keep",
    },
]
"""Minimal generic class profile — a STARTING POINT, not shipped policy.

Used only when ``config.economy["classes"]`` is empty. Every adopting host is
expected to replace it with its own measured taxonomy (the kit ships the
search, not our constants). Placeholder tokens (``<sessions_dir>`` etc.) are
expanded from the host config at evaluation time.
"""


def _eco_expand(pattern: str, config: Config) -> str:
    """Expand ``<sessions_dir>`` / ``<docs_root>`` / ``<state_dir>`` tokens."""
    return (
        pattern.replace("<sessions_dir>", config.sessions_dir)
        .replace("<docs_root>", config.docs_root)
        .replace("<state_dir>", config.state_dir)
    )


def _eco_classes(config: Config) -> list[dict]:
    """Return the active class table (host classes or the generic default)."""
    return list(config.economy.get("classes") or DEFAULT_CLASSES)


def _eco_md_files(docs_root: Path) -> list[Path]:
    """Return every ``*.md`` under ``docs_root`` (sorted, empty if absent)."""
    if not docs_root.exists():
        return []
    return sorted(docs_root.rglob("*.md"))


def _eco_read_text(path: Path) -> str | None:
    """Read ``path`` as UTF-8 text; None when unreadable or not text."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _eco_badge_token(path: Path) -> str | None:
    """Return the doc's Status-badge token from its first 12 lines, or None."""
    text = _eco_read_text(path)
    if text is None:
        return None
    match = _ECO_BADGE_RE.search("\n".join(text.splitlines()[:12]))
    return match.group(1) if match else None


def _eco_wc(path: Path) -> int:
    """Return the whitespace word count of one text file (0 if unreadable)."""
    text = _eco_read_text(path)
    return len(text.split()) if text else 0


def _eco_rel(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` as posix (absolute-safe fallback)."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def classify_docs(root: Path, config: Config) -> dict[str, list[Path]]:
    """Bucket project docs into economy classes plus the ``_unbadged`` bucket.

    Classes come from ``config.economy["classes"]`` (``DEFAULT_CLASSES`` when
    empty); each class matches by Status-badge token (``badges``, scanned from
    a doc's first 12 lines with the check_docs regex convention) and/or by
    root-relative ``globs``. The first matching class wins. Docs under the
    docs root that match no class AND carry no badge land in ``"_unbadged"``.
    """
    docs = _eco_md_files(root / config.docs_root)
    buckets: dict[str, list[Path]] = {}
    assigned: set[Path] = set()
    for cls in _eco_classes(config):
        matched: set[Path] = set()
        for pattern in cls.get("globs", []):
            expanded = _eco_expand(str(pattern), config)
            matched.update(p for p in root.glob(expanded) if p.is_file())
        badges = set(cls.get("badges", []))
        if badges:
            matched.update(f for f in docs if _eco_badge_token(f) in badges)
        fresh = sorted(p for p in matched if p.resolve() not in assigned)
        assigned.update(p.resolve() for p in fresh)
        buckets[cls["name"]] = fresh
    buckets["_unbadged"] = [
        f for f in docs if f.resolve() not in assigned and _eco_badge_token(f) is None
    ]
    return buckets


def _eco_word_cap_value(root: Path, config: Config, gauge: dict) -> int:
    """Return a word_cap gauge's value: one file's words, or a dir's summed."""
    target = root / _eco_expand(str(gauge.get("path", "")), config)
    if target.is_dir():
        return sum(_eco_wc(f) for f in sorted(target.rglob("*.md")))
    if target.is_file():
        return _eco_wc(target)
    return 0


def _eco_count_cap_value(root: Path, config: Config, gauge: dict) -> int:
    """Return a count_cap gauge's value: file count under its glob."""
    pattern = _eco_expand(str(gauge.get("glob", "")), config)
    if not pattern:
        return 0
    return sum(1 for p in root.glob(pattern) if p.is_file())


def _eco_route_budget(root: Path, config: Config) -> tuple[int, int]:
    """Return (value, cap) for the boot-route word budget.

    Value sums word counts over the boot set resolved by the orientation
    checker's own ``_ob_boot_paths`` (ONE resolver for both consumers — the
    gauge once resolved everything under docs_root and undercounted
    root-level boot docs to 0); cap is ``orientation["budget_words"]``.
    """
    value = sum(_eco_wc(path) for path in _ob_boot_paths(root, config))
    cap = int(config.orientation.get("budget_words", 7000))
    return value, cap


def economy_gauges(root: Path, config: Config) -> list[dict]:
    """Evaluate the configured gauges (word_cap / count_cap / route_budget).

    When ``config.economy["gauges"]`` is empty, falls back to one
    ``route_budget`` gauge derived from ``config.orientation``. Unknown kinds
    are skipped. Each result is ``{"name", "kind", "value", "cap", "over"}``.
    """
    gauges = list(config.economy.get("gauges") or [])
    if not gauges:
        gauges = [{"name": "route_budget", "kind": "route_budget"}]
    results: list[dict] = []
    for gauge in gauges:
        kind = str(gauge.get("kind", ""))
        cap = int(gauge.get("cap") or 0)
        if kind == "word_cap":
            value = _eco_word_cap_value(root, config, gauge)
        elif kind == "count_cap":
            value = _eco_count_cap_value(root, config, gauge)
        elif kind == "route_budget":
            value, default_cap = _eco_route_budget(root, config)
            cap = int(gauge.get("cap") or default_cap)
        else:
            continue
        results.append(
            {
                "name": str(gauge.get("name", kind)),
                "kind": kind,
                "value": value,
                "cap": cap,
                "over": value > cap,
            },
        )
    return results


def _eco_scan_files(root: Path, config: Config) -> list[Path]:
    """Return the reference-scan set: docs-root ``*.md`` + reference roots."""
    files: set[Path] = set(_eco_md_files(root / config.docs_root))
    for pattern in config.economy.get("reference_roots", []):
        expanded = _eco_expand(str(pattern), config)
        for hit in root.glob(expanded):
            if hit.is_file():
                files.add(hit)
            elif hit.is_dir():
                files.update(p for p in hit.rglob("*") if p.is_file())
    return sorted(files)


def inbound_references(
    root: Path,
    config: Config,
    targets: list[Path],
    exclude: dict[str, set[str]] | None = None,
) -> dict[str, list[str]]:
    """Map each target to the files that cite it (plain-text scan, stdlib).

    A scanner file cites a target when it contains (a) an id-pattern token
    (``config.economy["id_patterns"]``) drawn from the target's filename, or
    (b) the target's filename stem. Scans every ``*.md`` under the docs root
    plus every text file under each ``economy["reference_roots"]`` glob; a
    file never counts as citing itself. ``exclude`` maps a target *stem* to
    resolved scanner paths that must not count as citations — the pass record
    whose harvest table licenses a slug's deletion would otherwise hold every
    harvested file forever (the triple filter became unsatisfiable).
    """
    exclude = exclude or {}
    patterns = [re.compile(p) for p in config.economy.get("id_patterns", [])]
    scanners: list[tuple[Path, str]] = []
    for f in _eco_scan_files(root, config):
        text = _eco_read_text(f)
        if text is not None:
            scanners.append((f, text))
    refs: dict[str, list[str]] = {}
    for target in targets:
        ids = {m for pat in patterns for m in pat.findall(target.name)}
        needles = ids | {target.stem}
        excluded = exclude.get(target.stem, set())
        citing = {
            _eco_rel(f, root)
            for f, text in scanners
            if f.resolve() != target.resolve()
            and f.resolve().as_posix() not in excluded
            and any(needle in text for needle in needles)
        }
        refs[_eco_rel(target, root)] = sorted(citing)
    return refs


def _eco_expired(path: Path, window_days: Any) -> tuple[bool, int]:
    """Return (past-window?, age-in-days) for ``path`` (mtime-based)."""
    if window_days is None:
        return False, 0
    age = (time.time() - path.stat().st_mtime) / _ECO_SECONDS_PER_DAY
    return age > float(window_days), int(age)


def _eco_delete_row(
    rel: str,
    cls: dict,
    *,
    expired: bool,
    in_harvest: bool,
    n_refs: int,
) -> dict:
    """Build one delete would-act row carrying the TRIPLE FILTER verdict."""
    blockers: list[str] = []
    if not in_harvest:
        blockers.append("not harvested")
    if n_refs:
        blockers.append(f"inbound refs: {n_refs}")
    if not expired:
        blockers.append("window not reached")
    return {
        "path": rel,
        "action": "delete",
        "reason": f"class '{cls['name']}' ({cls.get('window_days')}d window)",
        "eligible": not blockers,
        "blockers": blockers,
        "class": cls["name"],
    }


def _eco_archive_row(rel: str, cls: dict, *, expired: bool) -> dict:
    """Build one archive would-act row (window is the only gate)."""
    return {
        "path": rel,
        "action": "archive",
        "reason": f"class '{cls['name']}' ({cls.get('window_days')}d window)",
        "eligible": expired,
        "blockers": [] if expired else ["window not reached"],
        "class": cls["name"],
    }


def _eco_class_files(classes: list[dict], buckets: dict[str, list[Path]]) -> list:
    """Return (class, file) pairs over every classified file, class order."""
    return [(cls, f) for cls in classes for f in buckets.get(cls["name"], [])]


def _eco_class_rows(
    root: Path,
    classes: list[dict],
    buckets: dict[str, list[Path]],
    harvested: set[str],
    refs: dict[str, list[str]],
) -> tuple[list[dict], list[EconomyFinding], int]:
    """Return (would-act rows, expired/delete_with_refs findings, debt)."""
    rows: list[dict] = []
    findings: list[EconomyFinding] = []
    debt = 0
    for cls, f in _eco_class_files(classes, buckets):
        expired, age = _eco_expired(f, cls.get("window_days"))
        rel = _eco_rel(f, root)
        if expired:
            debt += 1
            message = (
                f"{age}d old exceeds the {cls.get('window_days')}d "
                f"'{cls['name']}' window"
            )
            findings.append(EconomyFinding(rel, "expired", message))
        mode = cls.get("mode")
        if mode == "delete_tomb":
            n_refs = len(refs.get(rel, []))
            in_harvest = f.stem in harvested
            rows.append(
                _eco_delete_row(
                    rel,
                    cls,
                    expired=expired,
                    in_harvest=in_harvest,
                    n_refs=n_refs,
                ),
            )
            if expired and n_refs:
                message = f"expired but still cited by {n_refs} file(s)"
                findings.append(EconomyFinding(rel, "delete_with_refs", message))
        elif mode == "archive":
            rows.append(_eco_archive_row(rel, cls, expired=expired))
    return rows, findings, debt


def _eco_base_findings(
    root: Path,
    buckets: dict[str, list[Path]],
    gauges: list[dict],
) -> list[EconomyFinding]:
    """Return the unbadged + over_cap findings."""
    findings = [
        EconomyFinding(
            _eco_rel(f, root),
            "unbadged",
            "no Status badge and no economy class",
        )
        for f in buckets.get("_unbadged", [])
    ]
    findings += [
        EconomyFinding(
            g["name"],
            "over_cap",
            f"gauge '{g['name']}' at {g['value']} words/files vs cap {g['cap']}",
        )
        for g in gauges
        if g["over"]
    ]
    return findings


def economy_check(
    root: Path,
    config: Config,
    *,
    harvested: set[str] | None = None,
    harvest_exclude: dict[str, set[str]] | None = None,
) -> dict:
    """Run the full economy pass: census, gauges, findings, debt, would-act.

    Findings: ``unbadged`` (doc with no badge and no class), ``over_cap`` (a
    gauge over its cap), ``expired`` (file past its class window — the kit
    supports **day** windows only; "bands" are a host cadence unit, not a kit
    unit), and ``delete_with_refs`` (an expired delete-class file still
    cited). ``debt`` counts expired files. ``would_act`` delete rows carry the
    TRIPLE FILTER: eligible only when the file's stem (slug) is in
    ``harvested`` AND it is past its window AND it has zero inbound refs;
    blockers are the explicit strings ``"not harvested"`` /
    ``"inbound refs: N"`` / ``"window not reached"``.
    """
    harvested = set(harvested or set())
    classes = _eco_classes(config)
    buckets = classify_docs(root, config)
    census = {
        name: {"files": len(files), "words": sum(_eco_wc(f) for f in files)}
        for name, files in buckets.items()
    }
    gauges = economy_gauges(root, config)
    delete_targets = [
        f
        for cls in classes
        if cls.get("mode") == "delete_tomb"
        for f in buckets.get(cls["name"], [])
    ]
    refs = (
        inbound_references(root, config, delete_targets, harvest_exclude)
        if delete_targets
        else {}
    )
    rows, class_findings, debt = _eco_class_rows(
        root,
        classes,
        buckets,
        harvested,
        refs,
    )
    findings = _eco_base_findings(root, buckets, gauges) + class_findings
    return {
        "census": census,
        "gauges": gauges,
        "findings": findings,
        "debt": debt,
        "would_act": rows,
    }


def tombstone_line(path: Path, summary: str) -> str:
    """Render one ~20-word tombstone: ``slug - date - last path - what-it-was``."""
    short = " ".join(summary.split()[:12])
    return f"- {path.stem} - {date.today().isoformat()} - {path.as_posix()} - {short}"


def _eco_doc_summary(path: Path) -> str:
    """Return a short what-it-was summary: first heading or non-blank line."""
    text = _eco_read_text(path) or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return lines[0] if lines else "(empty file)"


def _eco_tombstone_shard(
    root: Path,
    config: Config,
    cls: dict,
    rel_path: Path,
) -> Path:
    """Return the per-band tombstone shard path for one deleted file's class."""
    tomb = cls.get("tombstone_dir")
    if tomb:
        tomb_dir = root / _eco_expand(str(tomb), config)
    else:
        tomb_dir = root / rel_path.parent / "pruned"
    return tomb_dir / f"band-{date.today().strftime('%Y%m')}.md"


def _eco_append_tombstone(shard: Path, line: str) -> None:
    """Append one tombstone line to the shard (create with banner if absent).

    Read-modify-write through ``atomic_write_text`` so a crash mid-append can
    never leave a truncated shard.
    """
    if shard.exists():
        text = shard.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
    else:
        today = date.today()
        text = (
            f"# Tombstones — band {today.strftime('%Y%m')}\n\n"
            "> **Status:** `archive`\n\n"
            f"> Pruned by the context-economy actuator; created "
            f"{today.isoformat()}. One line per deleted file: "
            "slug - date - last path - what-it-was.\n\n"
        )
    atomic_write_text(shard, text + line + "\n")


def _eco_dry_line(row: dict) -> str:
    """Render one would-act row as a dry-run report line."""
    if row.get("eligible"):
        return f"would {row['action']} {row['path']} ({row['reason']})"
    return f"hold {row['path']}: " + "; ".join(row.get("blockers", []))


def _eco_apply_rows(root: Path, config: Config, rows: list[dict]) -> list[str]:
    """Delete eligible delete rows, tombstoning each; archive rows advisory."""
    class_by_name = {c["name"]: c for c in _eco_classes(config)}
    lines: list[str] = []
    for row in rows:
        if not row.get("eligible"):
            lines.append(_eco_dry_line(row))
            continue
        if row.get("action") != "delete":
            lines.append(
                f"advisory: {row['action']} {row['path']} is a host action — "
                "the kit never moves files",
            )
            continue
        path = root / row["path"]
        if not path.is_file():
            lines.append(f"skipped {row['path']}: file no longer exists")
            continue
        cls = class_by_name.get(str(row.get("class", "")), {})
        shard = _eco_tombstone_shard(root, config, cls, Path(row["path"]))
        summary = _eco_doc_summary(path)
        _eco_append_tombstone(shard, tombstone_line(Path(row["path"]), summary))
        path.unlink()
        lines.append(f"deleted {row['path']} -> tombstone {_eco_rel(shard, root)}")
    return lines


def economy_actuate(
    root: Path,
    config: Config,
    report: dict,
    *,
    apply: bool = False,
    acknowledged: bool = False,
) -> list[str]:
    """Apply (or dry-run) the would-act plan from ``economy_check``.

    Dry-run (the default) returns the would-act lines without touching
    anything. ``apply=True`` acts only under the maturity ALLOWLIST:
    ``"normal"`` applies, ``"gated"`` applies only with
    ``acknowledged=True`` (the CE-14 first-prune human-review tier), and
    anything else — including ``"shadow"`` and any typo — refuses outright.
    The lock is acquired atomically (``O_CREAT|O_EXCL``); a pre-existing lock
    refuses (another actuation in flight) and is left in place. It then
    deletes ONLY eligible delete rows (one tombstone line per deletion,
    appended to the class's ``<tombstone_dir>/band-<YYYYMM>.md`` shard),
    removes its own lock in a ``finally`` block, and returns the action
    lines. Archive rows are advisory — the kit never moves files.
    """
    if not apply:
        return [_eco_dry_line(row) for row in report.get("would_act", [])]
    maturity = str(config.economy.get("maturity", "shadow")).strip().lower()
    if maturity not in ("gated", "normal"):
        # Allowlist, not a blocklist: a typo'd maturity ("Shadow", "shadoww")
        # must refuse, never silently apply — deletion is the one place the
        # kit's fail-open posture inverts to fail-closed.
        return [
            f"refused: economy maturity {maturity!r} does not permit apply "
            "(allowed: 'gated' with --reviewed, 'normal') — nothing changed",
        ]
    if maturity == "gated" and not acknowledged:
        return [
            "refused: economy maturity is 'gated' — the first executing prune "
            "needs an explicit human review acknowledgment (pass --reviewed); "
            "promote maturity to 'normal' once the first prune has been "
            "reviewed — nothing changed",
        ]
    lock = root / config.state_dir / "economy.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        # O_CREAT|O_EXCL: atomic acquire — check-then-create raced, and two
        # concurrent actuations could clobber a tombstone shard.
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return [
            f"refused: {config.state_dir}/economy.lock exists — another "
            "actuation may be in flight; nothing changed",
        ]
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"locked {date.today().isoformat()}\n")
        return _eco_apply_rows(root, config, report.get("would_act", []))
    finally:
        lock.unlink(missing_ok=True)


def issue_body(report: dict) -> str:
    """Render the retention-debt routine issue body (markdown).

    Census table + debt count + the top would-act rows (eligible first) — the
    ``--issue-body`` emit the debt-threshold routine posts.
    """
    lines = [
        "## Context-economy retention debt",
        "",
        f"**Debt (expired files): {report.get('debt', 0)}**",
        "",
        "### Census",
        "",
        "| class | files | words |",
        "| --- | --- | --- |",
    ]
    for name, row in sorted(report.get("census", {}).items()):
        lines.append(f"| {name} | {row['files']} | {row['words']} |")
    top = sorted(report.get("would_act", []), key=lambda r: not r.get("eligible"))
    if top:
        lines += ["", "### Top would-act rows", ""]
        lines += [f"- {_eco_dry_line(row)}" for row in top[:10]]
    return "\n".join(lines) + "\n"

# --- engine/economy/harvest.py ---
"""Harvest-table parsing + stub rendering (plan §5.B, Lane B4).

The harvest table is the delete-side safety input of the TRIPLE FILTER: a
pass record commits what it *harvested* from the files it reviewed into a
markdown table under a heading containing "harvest". ``parse_harvest_tables``
recovers the committed slugs (a file is delete-eligible only once its slug
appears here); ``harvest_table_stub`` renders the kit-defined row format,
which round-trips through the parser. Pure stdlib; returns data / text.
"""



_HRV_HEADING_RE = re.compile(r"^#{1,6}\s")
# A table separator row: only pipes, dashes, colons, and whitespace.
_HRV_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|?$")

_HRV_HEADER_ROW = "| slug | status/PR | ⚑ flags | 💡 ideas | 📊 telemetry |"
_HRV_SEPARATOR_ROW = "| --- | --- | --- | --- | --- |"


def _hrv_first_cell(line: str) -> str | None:
    """Return a table row's first-column cell (None when empty)."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if not cells:
        return None
    cell = cells[0].strip("`* ")
    return cell or None


def _hrv_slugs_from_text(text: str) -> set[str]:
    """Collect first-column data cells from tables under harvest headings.

    A "harvest heading" is any markdown heading containing ``harvest``
    (case-insensitive). Within such a section, each contiguous run of ``|``
    lines is one table: its first row is the header (skipped), separator rows
    are skipped, every other row contributes its first cell. Surrounding
    prose is tolerated.
    """
    slugs: set[str] = set()
    in_harvest = False
    in_table = False
    table_is_harvest = False
    for line in text.splitlines():
        if _HRV_HEADING_RE.match(line):
            in_harvest = "harvest" in line.lower()
            in_table = False
            continue
        if not in_harvest or not line.lstrip().startswith("|"):
            in_table = False
            continue
        if not in_table:
            # First row of a new table = header. Only a table whose FIRST
            # header cell is "slug" is a harvest table — an inventory or
            # pending table under a "Harvest backlog" heading must never mark
            # files as harvested (that is a deletion license).
            in_table = True
            header = (_hrv_first_cell(line) or "").lower()
            table_is_harvest = header == "slug"
            continue
        if not table_is_harvest or _HRV_SEPARATOR_RE.match(line.strip()):
            continue
        cell = _hrv_first_cell(line)
        if cell:
            slugs.add(cell)
    return slugs


def parse_harvest_tables(pass_records_dir: Path) -> set[str]:
    """Return every harvested slug committed in the pass-record tables.

    Scans ``*.md`` under ``pass_records_dir`` for markdown tables sitting
    under any heading containing ``"harvest"`` (case-insensitive) and
    collects the first-column cell of each data row (header + separator rows
    skipped). Tolerant of surrounding prose; empty set when the directory is
    absent.
    """
    if not pass_records_dir.is_dir():
        return set()
    slugs: set[str] = set()
    for f in sorted(pass_records_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        slugs |= _hrv_slugs_from_text(text)
    return slugs


def harvest_table_stub(entries: list[dict]) -> str:
    """Render the kit-defined harvest table for ``entries``.

    Columns: ``slug | status/PR | ⚑ flags | 💡 ideas | 📊 telemetry``. Each
    entry supplies ``slug`` (required) plus optional ``status`` / ``flags`` /
    ``ideas`` / ``telemetry``. The output includes the ``## Harvest`` heading
    so it round-trips through ``parse_harvest_tables`` unchanged.
    """
    lines = ["## Harvest", "", _HRV_HEADER_ROW, _HRV_SEPARATOR_ROW]
    for entry in entries:
        lines.append(
            "| {slug} | {status} | {flags} | {ideas} | {telemetry} |".format(
                slug=entry.get("slug", ""),
                status=entry.get("status", "—"),
                flags=entry.get("flags", "—"),
                ideas=entry.get("ideas", "—"),
                telemetry=entry.get("telemetry", "—"),
            ),
        )
    return "\n".join(lines) + "\n"


def harvest_sources(pass_records_dir: Path) -> dict[str, set[str]]:
    """Map each harvested slug to the pass-record files that harvested it.

    The harvest table row is the *deletion license* for its slug — the pass
    record naming a slug must not count as an inbound reference to it, or the
    triple filter becomes unsatisfiable (every harvested file is "referenced"
    by its own harvest record).
    """
    sources: dict[str, set[str]] = {}
    if not pass_records_dir.is_dir():
        return sources
    for record in sorted(pass_records_dir.glob("*.md")):
        try:
            text = record.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for slug in _hrv_slugs_from_text(text):
            sources.setdefault(slug, set()).add(record.resolve().as_posix())
    return sources

# --- engine/economy/simulator.py ---
"""Retention-policy simulator for the context economy (plan §5.B, Lane B5).

A generalized port of superbot's ``tools/sim/retention_policy_sim.py``
(sim-driven design applied to the memory system itself). It models a docs
corpus growing over sessions, agents reading it (boot route, grep discovery,
directory scans, back-references into pruned content, stale encounters), and a
candidate retention policy acting on it. The grid search scores each candidate
on expected agent context cost (words per session) under a hard feasibility
constraint (retrieval-miss risk), with a secondary lean-by-construction
objective (smallest tree at horizon among near-best feasible policies) and a
×1/3–×3 sensitivity sweep over the assumption-grade constants.

The kit ships the SEARCH, not any project's constants: every number returned
by ``default_calibration()`` is an UNVERIFIED illustrative placeholder. Run
``calibration_recipe()`` for the measurement plan, replace the numbers with
your repo's, then re-run ``run_search``.

Calibration shape (one plain dict; all costs are words unless noted)::

    {
      # velocity
      "sessions_per_band": 20.0,     # sessions per reconciliation band
      "words_per_token": 0.75,       # for the tokens-saved line in why-it-won
      "initial_age_bands": 12,       # today's stock spread uniformly this deep
      # living-file stocks and boot route
      "live_files": 100.0,           # living/working docs (non-terminal)
      "live_words": 150000.0,
      "boot_fixed_words": 6000.0,    # always-read orientation route
      "journal_words": 4000.0,       # cappable process-memory journal
      "journal_caps": [1000000, 2000],   # grid toggle: uncapped vs capped
      "ledger_base_words": 1500.0,   # living ledger lean head
      "ledger_tail_per_band": 300.0, # narrative accretion per band if untrimmed
      "ledger_tail_bands_initial": 6,
      "ledger_tail_compressed_bands": 2,
      "index_active_line_words": 20.0,
      "index_hist_line_words": 18.0,
      "tombstone_words": 20.0,       # one tombstone index line
      # discovery tax
      "greps_per_session": 8.0,
      "grep_hits_per_1k_files": 50.0,
      "skim_words_per_hit": 12.0,    # path skim in -l output
      "open_frac_per_hit": 0.10,     # fraction opened before badge-bail
      "open_words_per_hit": 200.0,
      "archive_pollution_w_per_mw": 25.0,  # content-grep noise per Mw archived
      "maintenance_w_per_mw": 8.0,   # sweep/link-check burden per Mw in tree
      "ls_scan_words_per_file": 5.0,
      "ls_scans_per_session": 2.0,
      # back-references into terminal content
      "backref_halflife_bands": 3.0, # demand decays with age (exponential)
      "tombstone_hop_words": 300.0,  # tombstone -> history-recovery effort
      "bare_rederive_words": 3000.0, # no pointer: re-derive / re-decide
      "bare_find_fail": 0.5,         # P(recovery fails without a tombstone)
      # staleness (assumption-grade; sweep it)
      "stale_act_base": 0.01,        # P/session of acting on stale content
      "stale_act_cost": 10000.0,
      # feasibility + search knobs
      "miss_per_band_max": 0.005,    # hard constraint on retrieval-miss risk
      "near_best_frac": 0.05,        # secondary-objective envelope
      "grid_scale": 1,               # widening knob: N multiplies each class's
                                     # candidate windows by 1..N (bigger grid)
      "sensitivity_multipliers": [1/3, 3],
      "sensitivity_keys": ["stale_act_base", "classes.sessions.backref_rate"],
      # document classes (per-class mode × window searched per declarations)
      "classes": [
        {
          "name": "sessions",
          "birth_rate": 1.0,         # new files per session
          "words_each": 700.0,
          "initial_files": 240.0,
          "cited_frac": 0.05,        # inbound-live-reference blocking fraction
          "cascade_unlock_frac": 0.0,  # share of cited_frac released when the
                                       # living tails compress (ledger cascade)
          "backref_rate": 0.05,      # back-reference demand per session
          "tombstone_lines_each": 0.0,  # index lines left per deleted doc
          "indexed": False,          # hist files add boot-index lines
          "active_pool": None,       # or {"initial": F, "lifetime_bands": B}
                                     # for classes born active, then terminal
          "modes": ["keep", "archive", "delete_tomb", "delete_bare"],
          "windows": [1, 2, 4],      # candidate windows, in bands
        },
        ...
      ],
    }

Policy shape (``policy_grid`` builds these; you can hand-craft one too)::

    {"name": str,   # optional on hand-crafted policies; derived when absent
     "classes": {<class name>: {"mode": <RETENTION_MODES member>, "window": int}},
     "ledger_compress": bool, "journal_cap": float,
     "index_hist_tombstones": bool}

Pure stdlib, deterministic per seed (``random.Random`` instances only, no
randomness at import), no I/O, never prints — the CLI wires presentation.
"""



RETENTION_MODES: tuple[str, ...] = ("keep", "archive", "delete_tomb", "delete_bare")


def default_calibration() -> dict[str, Any]:
    """Return a neutral, illustrative calibration — every value UNVERIFIED.

    These numbers exist so the search runs out of the box and the shape is
    executable documentation; they are NOT measurements of any repo. Follow
    ``calibration_recipe()`` to measure your own corpus before trusting a
    winner. The default grid is deliberately small (a few seconds end to end);
    raise ``grid_scale`` to widen the candidate windows.
    """
    return {
        "sessions_per_band": 20.0,
        "words_per_token": 0.75,
        "initial_age_bands": 12,
        "live_files": 100.0,
        "live_words": 150000.0,
        "boot_fixed_words": 6000.0,
        "journal_words": 4000.0,
        "journal_caps": [1000000, 2000],
        "ledger_base_words": 1500.0,
        "ledger_tail_per_band": 300.0,
        "ledger_tail_bands_initial": 6,
        "ledger_tail_compressed_bands": 2,
        "index_active_line_words": 20.0,
        "index_hist_line_words": 18.0,
        "tombstone_words": 20.0,
        "greps_per_session": 8.0,
        "grep_hits_per_1k_files": 50.0,
        "skim_words_per_hit": 12.0,
        "open_frac_per_hit": 0.10,
        "open_words_per_hit": 200.0,
        "archive_pollution_w_per_mw": 25.0,
        "maintenance_w_per_mw": 8.0,
        "ls_scan_words_per_file": 5.0,
        "ls_scans_per_session": 2.0,
        "backref_halflife_bands": 3.0,
        "tombstone_hop_words": 300.0,
        "bare_rederive_words": 3000.0,
        "bare_find_fail": 0.5,
        "stale_act_base": 0.01,
        "stale_act_cost": 10000.0,
        "miss_per_band_max": 0.005,
        "near_best_frac": 0.05,
        "grid_scale": 1,
        "sensitivity_multipliers": [1 / 3, 3],
        "sensitivity_keys": [
            "stale_act_base",
            "grep_hits_per_1k_files",
            "maintenance_w_per_mw",
            "archive_pollution_w_per_mw",
            "classes.sessions.backref_rate",
            "classes.plans.backref_rate",
        ],
        "classes": [
            {
                "name": "sessions",
                "birth_rate": 1.0,
                "words_each": 700.0,
                "initial_files": 240.0,
                "cited_frac": 0.05,
                "cascade_unlock_frac": 0.0,
                "backref_rate": 0.05,
                "tombstone_lines_each": 0.0,
                "indexed": False,
                "active_pool": None,
                "modes": ["keep", "archive", "delete_tomb", "delete_bare"],
                "windows": [1, 2, 4],
            },
            {
                "name": "plans",
                "birth_rate": 0.25,
                "words_each": 2500.0,
                "initial_files": 60.0,
                "cited_frac": 0.90,
                "cascade_unlock_frac": 0.85,
                "backref_rate": 0.20,
                "tombstone_lines_each": 1.0,
                "indexed": True,
                "active_pool": {"initial": 40.0, "lifetime_bands": 4.0},
                "modes": ["keep", "archive", "delete_tomb"],
                "windows": [2, 4],
            },
            {
                "name": "notes",
                "birth_rate": 0.20,
                "words_each": 800.0,
                "initial_files": 40.0,
                "cited_frac": 0.10,
                "cascade_unlock_frac": 0.0,
                "backref_rate": 0.02,
                "tombstone_lines_each": 1.0,
                "indexed": False,
                "active_pool": None,
                "modes": ["delete_tomb"],
                "windows": [4],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Policy space
# ---------------------------------------------------------------------------


def _sim_policy_name(policy: dict[str, Any]) -> str:
    """Render the deterministic display name for one policy dict."""
    parts = [
        f"{name}={spec['mode']}@{spec['window']}b"
        for name, spec in sorted(policy["classes"].items())
    ]
    parts.append(f"ledger={'compress' if policy['ledger_compress'] else 'grow'}")
    parts.append(f"journal<={policy['journal_cap']:g}")
    parts.append(f"idx={'tomb' if policy['index_hist_tombstones'] else 'full'}")
    return " ".join(parts)


def _sim_class_candidates(
    cls_cal: dict[str, Any],
    grid_scale: int,
) -> list[tuple[str, int]]:
    """Return the (mode, window) candidates one class declaration allows.

    ``keep`` collapses to a single ``(keep, 0)`` candidate (its window is
    meaningless); ``grid_scale`` N widens each declared window by factors
    1..N, deduplicated and sorted, so hosts can search deeper without editing
    the class declarations.
    """
    windows = sorted(
        {
            int(w) * f
            for w in cls_cal["windows"]
            for f in range(1, max(grid_scale, 1) + 1)
        },
    )
    candidates: list[tuple[str, int]] = []
    for mode in cls_cal["modes"]:
        if mode == "keep":
            candidates.append(("keep", 0))
        else:
            candidates.extend((mode, w) for w in windows)
    return candidates


def policy_grid(calibration: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the candidate-policy grid from the calibration's class declarations.

    The grid is the cartesian product of every class's ``modes`` × ``windows``
    (widened by ``grid_scale``), crossed with the living-file toggles: ledger
    compression on/off and each ``journal_caps`` value. Historical index lines
    are always tombstone-compressed in generated candidates (the status-quo
    baseline inside ``run_search`` covers the full-line alternative).
    """
    grid_scale = int(calibration.get("grid_scale", 1))
    class_names = [c["name"] for c in calibration["classes"]]
    per_class = [_sim_class_candidates(c, grid_scale) for c in calibration["classes"]]
    journal_caps = calibration.get("journal_caps", [10**9])
    policies: list[dict[str, Any]] = []
    for combo in itertools.product(*per_class):
        for ledger_compress, journal_cap in itertools.product(
            (True, False),
            journal_caps,
        ):
            policy: dict[str, Any] = {
                "classes": {
                    name: {"mode": mode, "window": window}
                    for name, (mode, window) in zip(class_names, combo, strict=True)
                },
                "ledger_compress": ledger_compress,
                "journal_cap": float(journal_cap),
                "index_hist_tombstones": True,
            }
            policy["name"] = _sim_policy_name(policy)
            policies.append(policy)
    return policies


def _sim_status_quo(calibration: dict[str, Any]) -> dict[str, Any]:
    """Return the keep-everything baseline policy for this calibration."""
    policy: dict[str, Any] = {
        "classes": {
            c["name"]: {"mode": "keep", "window": 0} for c in calibration["classes"]
        },
        "ledger_compress": False,
        "journal_cap": float(10**9),
        "index_hist_tombstones": False,
    }
    policy["name"] = _sim_policy_name(policy)
    return policy


# ---------------------------------------------------------------------------
# Corpus state: per class, bucketed by age-in-bands since terminal
# ---------------------------------------------------------------------------


def _sim_initial_state(calibration: dict[str, Any]) -> dict[str, Any]:
    """Build the initial corpus state from the calibration's stocks.

    Each class's initial terminal stock is spread uniformly over
    ``initial_age_bands`` age buckets (bucket index = bands since the file
    went terminal); classes with an ``active_pool`` start with its declared
    active count.
    """
    age_bands = max(int(calibration.get("initial_age_bands", 12)), 1)
    classes: dict[str, dict[str, Any]] = {}
    for cls in calibration["classes"]:
        pool = cls.get("active_pool") or {}
        classes[cls["name"]] = {
            "buckets": [float(cls.get("initial_files", 0.0)) / age_bands] * age_bands,
            "active": float(pool.get("initial", 0.0)),
        }
    return {
        "classes": classes,
        "archived_words": 0.0,
        "tombstone_lines": 0.0,
        "ledger_tail_bands": float(calibration.get("ledger_tail_bands_initial", 0)),
    }


def _sim_age_out(buckets: list[float], window: int, keep_frac: float) -> float:
    """Prune buckets older than ``window`` in place; return files removed.

    ``keep_frac`` is the citation-locked fraction that stays in place (still
    referenced by living docs, so not yet removable).
    """
    removed = 0.0
    for i in range(len(buckets)):
        if i >= window and buckets[i] > 0:
            hold = buckets[i] * keep_frac
            removed += buckets[i] - hold
            buckets[i] = hold
    return removed


def _sim_grow(
    state: dict[str, Any],
    calibration: dict[str, Any],
    rng: random.Random,
) -> None:
    """Advance one band of corpus growth (births, completions, tail accretion).

    Births carry a small deterministic-per-seed jitter (±10%) so the seed is
    load-bearing; the draw count per band is policy-independent, which keeps
    same-seed policy comparisons exact.
    """
    n_sessions = float(calibration["sessions_per_band"])
    for cls in calibration["classes"]:
        cs = state["classes"][cls["name"]]
        births = float(cls["birth_rate"]) * n_sessions * (0.9 + 0.2 * rng.random())
        pool = cls.get("active_pool")
        if pool:
            lifetime = max(float(pool.get("lifetime_bands", 1.0)), 1.0)
            completions = cs["active"] / lifetime
            cs["active"] += births - completions
            cs["buckets"].insert(0, completions)
        else:
            cs["buckets"].insert(0, births)


def _sim_prune(
    state: dict[str, Any],
    policy: dict[str, Any],
    calibration: dict[str, Any],
) -> None:
    """Apply one band of the policy's per-class retention actions.

    Inbound-reference blocking: a class's ``cited_frac`` locks that share of
    delete-eligible files in place; when the policy compresses the living
    tails, ``cascade_unlock_frac`` of that lock is released (the deletability
    cascade — provenance decoration in living history tails is the top citer).
    Archiving is never citation-blocked: the body stays recoverable in-tree.
    """
    for cls in calibration["classes"]:
        spec = policy["classes"][cls["name"]]
        mode, window = spec["mode"], int(spec["window"])
        if mode == "keep" or window <= 0:
            continue
        block = float(cls.get("cited_frac", 0.0))
        if policy["ledger_compress"]:
            block *= 1.0 - float(cls.get("cascade_unlock_frac", 0.0))
        buckets = state["classes"][cls["name"]]["buckets"]
        if mode == "archive":
            moved = _sim_age_out(buckets, window, keep_frac=0.0)
            state["archived_words"] += moved * float(cls["words_each"])
        elif mode == "delete_tomb":
            gone = _sim_age_out(buckets, window, keep_frac=block)
            state["tombstone_lines"] += gone * float(
                cls.get("tombstone_lines_each", 1.0),
            )
        elif mode == "delete_bare":
            _sim_age_out(buckets, window, keep_frac=block)


def _sim_dispo(mode: str, window: int, halflife: float) -> tuple[float, float, float]:
    """Split back-reference demand into (in-tree, tombstone, bare) fractions.

    Demand decays exponentially with age (``halflife`` in bands); the share
    older than the prune window lands on the pruned disposition.
    """
    if mode in ("keep", "archive") or window <= 0:
        return 1.0, 0.0, 0.0
    p_old = 0.5 ** (window / max(halflife, 0.1))
    if mode == "delete_tomb":
        return 1.0 - p_old, p_old, 0.0
    return 1.0 - p_old, 0.0, p_old


def _sim_boot_cost(
    state: dict[str, Any],
    policy: dict[str, Any],
    calibration: dict[str, Any],
) -> float:
    """Return the per-session boot tax (always-read route, words)."""
    tail_bands = (
        float(calibration.get("ledger_tail_compressed_bands", 2))
        if policy["ledger_compress"]
        else state["ledger_tail_bands"]
    )
    ledger_tail = tail_bands * float(calibration["ledger_tail_per_band"])
    journal = min(float(calibration["journal_words"]), float(policy["journal_cap"]))
    per_hist = (
        float(calibration["tombstone_words"])
        if policy["index_hist_tombstones"]
        else float(calibration["index_hist_line_words"])
    )
    index_words = state["tombstone_lines"] * float(calibration["tombstone_words"])
    for cls in calibration["classes"]:
        if not cls.get("indexed", False):
            continue
        cs = state["classes"][cls["name"]]
        index_words += cs["active"] * float(calibration["index_active_line_words"])
        index_words += sum(cs["buckets"]) * per_hist
    return (
        float(calibration["boot_fixed_words"])
        + journal
        + float(calibration["ledger_base_words"])
        + ledger_tail
        + index_words
    )


def _sim_discovery_cost(
    state: dict[str, Any],
    calibration: dict[str, Any],
    term_files: float,
    term_words: float,
) -> float:
    """Return the per-session discovery tax (grep noise, scans, maintenance)."""
    live_files = float(calibration["live_files"]) + sum(
        cs["active"] for cs in state["classes"].values()
    )
    total_files = term_files + live_files
    hits_per_grep = float(calibration["grep_hits_per_1k_files"]) * total_files / 1000.0
    term_share = term_files / max(total_files, 1.0)
    per_hit = float(calibration["skim_words_per_hit"]) + float(
        calibration["open_frac_per_hit"],
    ) * float(calibration["open_words_per_hit"])
    grep_noise = (
        float(calibration["greps_per_session"]) * hits_per_grep * term_share * per_hit
    )
    ls_noise = (
        float(calibration["ls_scans_per_session"])
        * term_files
        * float(calibration["ls_scan_words_per_file"])
    )
    arch_noise = (
        float(calibration["archive_pollution_w_per_mw"]) * state["archived_words"] / 1e6
    )
    tree_words = term_words + float(calibration["live_words"]) + state["archived_words"]
    maintenance = float(calibration["maintenance_w_per_mw"]) * tree_words / 1e6
    return grep_noise + ls_noise + arch_noise + maintenance


def _sim_backref_and_miss(
    policy: dict[str, Any],
    calibration: dict[str, Any],
) -> tuple[float, float]:
    """Return (back-reference cost, retrieval-miss events), both per session.

    In-tree demand costs nothing extra (reading a present body is work, not
    waste); a tombstone costs one recovery hop; a bare deletion costs a full
    re-derivation when recovery fails and a doubled hop when it succeeds. The
    miss metric counts only failed bare recoveries — the risk the feasibility
    constraint bounds.
    """
    halflife = float(calibration["backref_halflife_bands"])
    hop = float(calibration["tombstone_hop_words"])
    fail = float(calibration["bare_find_fail"])
    rederive = float(calibration["bare_rederive_words"])
    backref = miss = 0.0
    for cls in calibration["classes"]:
        spec = policy["classes"][cls["name"]]
        _in_tree, tomb, bare = _sim_dispo(spec["mode"], int(spec["window"]), halflife)
        rate = float(cls.get("backref_rate", 0.0))
        backref += rate * tomb * hop
        backref += rate * bare * (fail * rederive + (1.0 - fail) * hop * 2.0)
        miss += rate * bare * fail
    return backref, miss


def _sim_stale_cost(
    state: dict[str, Any],
    policy: dict[str, Any],
    calibration: dict[str, Any],
    term_words: float,
    initial_term_words: float,
) -> float:
    """Return the per-session staleness cost (acting on dead content as live)."""
    tail_bands = (
        float(calibration.get("ledger_tail_compressed_bands", 2))
        if policy["ledger_compress"]
        else state["ledger_tail_bands"]
    )
    ledger_tail = tail_bands * float(calibration["ledger_tail_per_band"])
    norm_tail = max(
        float(calibration.get("ledger_tail_bands_initial", 1)),
        1.0,
    ) * float(calibration["ledger_tail_per_band"])
    scale = (term_words / (initial_term_words + 1.0)) * 0.6 + (
        ledger_tail / max(norm_tail, 1.0)
    ) * 0.4
    return (
        float(calibration["stale_act_base"])
        * scale
        * float(
            calibration["stale_act_cost"],
        )
    )


def simulate_policy(
    policy: dict[str, Any],
    calibration: dict[str, Any],
    *,
    bands: int,
    seed: int = 7,
) -> dict[str, Any]:
    """Simulate one policy over ``bands`` reconciliation bands; score it.

    Returns the per-policy result record: the four per-session cost components
    (``boot``, ``discovery``, ``backref``, ``stale``, band-averaged words per
    session), their ``total``, the ``miss_per_band`` risk metric with its
    ``feasible`` verdict (< ``miss_per_band_max``), and the horizon-end tree
    size (``end_terminal_files``, ``end_tree_kwords``). Deterministic for a
    given (policy, calibration, bands, seed).
    """
    rng = random.Random(seed)
    name = policy.get("name") or _sim_policy_name(policy)
    state = _sim_initial_state(calibration)
    initial_term_words = sum(
        float(c.get("initial_files", 0.0)) * float(c["words_each"])
        for c in calibration["classes"]
    )
    totals = {"boot": 0.0, "discovery": 0.0, "backref": 0.0, "stale": 0.0}
    miss_events = 0.0
    term_files = term_words = 0.0
    n_bands = max(int(bands), 1)
    for _ in range(n_bands):
        _sim_grow(state, calibration, rng)
        if not policy["ledger_compress"]:
            state["ledger_tail_bands"] += 1.0
        _sim_prune(state, policy, calibration)
        term_files = sum(sum(cs["buckets"]) for cs in state["classes"].values())
        term_words = sum(
            sum(state["classes"][c["name"]]["buckets"]) * float(c["words_each"])
            for c in calibration["classes"]
        )
        totals["boot"] += _sim_boot_cost(state, policy, calibration)
        totals["discovery"] += _sim_discovery_cost(
            state,
            calibration,
            term_files,
            term_words,
        )
        backref, miss = _sim_backref_and_miss(policy, calibration)
        totals["backref"] += backref
        miss_events += miss
        totals["stale"] += _sim_stale_cost(
            state,
            policy,
            calibration,
            term_words,
            initial_term_words,
        )
    per = {k: v / n_bands for k, v in totals.items()}
    per_total = sum(per.values())
    miss_per_band = miss_events / n_bands
    return {
        "policy": policy,
        "name": name,
        **per,
        "total": per_total,
        "miss_per_band": miss_per_band,
        "feasible": miss_per_band < float(calibration.get("miss_per_band_max", 0.005)),
        "end_terminal_files": term_files,
        "end_tree_kwords": (
            term_words + float(calibration["live_words"]) + state["archived_words"]
        )
        / 1000.0,
    }


# ---------------------------------------------------------------------------
# Search, sensitivity, why-it-won
# ---------------------------------------------------------------------------


def _sim_scaled(calibration: dict[str, Any], key: str, mult: float) -> dict[str, Any]:
    """Return a deep copy of the calibration with one constant multiplied.

    ``key`` is either a top-level constant name or a class field addressed as
    ``classes.<class name>.<field>``. Unknown class addresses scale nothing
    (the copy is returned unchanged) so pruned class lists stay sweepable.
    """
    scaled = copy.deepcopy(calibration)
    if key.startswith("classes."):
        _, cls_name, field = key.split(".", 2)
        for cls in scaled["classes"]:
            if cls["name"] == cls_name and field in cls:
                cls[field] = float(cls[field]) * mult
        return scaled
    scaled[key] = float(scaled[key]) * mult
    return scaled


def _sim_sensitivity(
    policy: dict[str, Any],
    calibration: dict[str, Any],
    *,
    bands: int,
    seed: int,
    base_total: float,
) -> list[dict[str, Any]]:
    """Re-score the winner under each sweep multiplier on each swept constant."""
    entries: list[dict[str, Any]] = []
    multipliers = calibration.get("sensitivity_multipliers", [1 / 3, 3])
    for key in calibration.get("sensitivity_keys", []):
        for mult in multipliers:
            scaled = _sim_scaled(calibration, key, float(mult))
            total = simulate_policy(policy, scaled, bands=bands, seed=seed)["total"]
            entries.append(
                {
                    "key": key,
                    "multiplier": float(mult),
                    "total": total,
                    "delta": total - base_total,
                },
            )
    return entries


def _sim_why_it_won(
    winner: dict[str, Any],
    baseline: dict[str, Any],
    calibration: dict[str, Any],
    *,
    feasible_count: int,
    grid_size: int,
    near_count: int,
) -> str:
    """Render the WHY-IT-WON record for one search outcome."""
    words_per_token = max(float(calibration.get("words_per_token", 0.75)), 0.01)
    base_total = baseline["total"]
    saved = base_total - winner["total"]
    pct = 100.0 * saved / base_total if base_total > 0 else 0.0
    near_frac = float(calibration.get("near_best_frac", 0.05))
    lines = [
        f"winner: {winner['name']}",
        (
            f"vs keep-everything baseline: {base_total:,.0f} -> "
            f"{winner['total']:,.0f} words/session ({pct:.0f}% lower), "
            f"~{saved / words_per_token / 1000:.1f}k tokens/session saved"
        ),
        (
            f"tree size at horizon: {baseline['end_tree_kwords']:,.0f}kw -> "
            f"{winner['end_tree_kwords']:,.0f}kw"
        ),
        (
            f"retrieval-miss events/band: {winner['miss_per_band']:.4f} "
            f"(constraint < {float(calibration.get('miss_per_band_max', 0.005)):g})"
        ),
        (
            f"feasible policies: {feasible_count} of {grid_size}; secondary "
            f"objective picked the smallest tree among {near_count} within "
            f"{near_frac:.0%} of the best primary score"
        ),
    ]
    if not winner["feasible"]:
        lines.append(
            "WARNING: no candidate met the miss constraint — winner is the "
            "lowest-cost INFEASIBLE policy; loosen windows or drop delete_bare",
        )
    return "\n".join(lines)


def run_search(
    calibration: dict[str, Any],
    *,
    bands: int = 24,
    seed: int = 7,
) -> dict[str, Any]:
    """Run the full policy-grid search and return the winner with its record.

    Primary objective: lowest expected words/session among FEASIBLE policies
    (``miss_per_band`` under the calibration's bound). Secondary objective
    (lean by construction): among feasible policies within ``near_best_frac``
    of the best primary score, the smallest tree at horizon wins. Returns
    ``{"winner", "why_it_won", "feasible_count", "sensitivity"}`` — the winner
    is the full ``simulate_policy`` record (policy dict under ``"winner"["policy"]``).
    If nothing is feasible the search degrades gracefully: the lowest-cost
    infeasible policy wins and ``why_it_won`` carries a loud warning.
    """
    grid = policy_grid(calibration)
    results = [
        simulate_policy(policy, calibration, bands=bands, seed=seed) for policy in grid
    ]
    feasible = [r for r in results if r["feasible"]]
    pool = feasible or sorted(results, key=lambda r: r["total"])
    best_total = min(r["total"] for r in pool)
    near_frac = float(calibration.get("near_best_frac", 0.05))
    near = [r for r in pool if r["total"] <= best_total * (1.0 + near_frac)]
    near.sort(key=lambda r: (r["end_tree_kwords"], r["total"], r["name"]))
    winner = near[0]
    baseline = simulate_policy(
        _sim_status_quo(calibration),
        calibration,
        bands=bands,
        seed=seed,
    )
    sensitivity = _sim_sensitivity(
        winner["policy"],
        calibration,
        bands=bands,
        seed=seed,
        base_total=winner["total"],
    )
    why = _sim_why_it_won(
        winner,
        baseline,
        calibration,
        feasible_count=len(feasible),
        grid_size=len(grid),
        near_count=len(near),
    )
    return {
        "winner": winner,
        "why_it_won": why,
        "feasible_count": len(feasible),
        "sensitivity": sensitivity,
    }


def calibration_recipe() -> str:
    """Return the re-measurement recipe for grounding a calibration in a repo.

    The kit ships the search, not our constants: every default is a
    placeholder. Measure the five profiles below against YOUR corpus, write
    the numbers into a copy of ``default_calibration()``, then re-run
    ``run_search`` — and re-measure whenever the corpus shape shifts.
    """
    return (
        "Calibration recipe — measure your repo, then edit default_calibration()\n"
        "\n"
        "Every default constant is an UNVERIFIED placeholder. Ground each group\n"
        "in measurements before trusting a winner:\n"
        "\n"
        "```sh\n"
        "# 1) Badge census — per-class stocks (initial_files, words_each):\n"
        "#    count and word-count files per lifecycle class (terminal vs live).\n"
        "grep -rlE '\\*\\*Status:\\*\\* .(historical|archived)' docs/ | wc -l\n"
        "grep -rlE '\\*\\*Status:\\*\\* .(historical|archived)' docs/ | xargs wc -w\n"
        "ls .sessions/*.md | wc -l && wc -w .sessions/*.md | tail -1\n"
        "\n"
        "# 2) Grep-noise profile — discovery constants (grep_hits_per_1k_files,\n"
        "#    share of hits landing in terminal docs): run ~20 representative\n"
        "#    working-term greps and count hit locations.\n"
        'for t in <your 20 working terms>; do grep -rl "$t" docs/ ; done |\n'
        "  sort | uniq -c | sort -rn | head\n"
        "\n"
        "# 3) Velocity — sessions_per_band and per-class birth_rate:\n"
        "#    files born per session over recent history.\n"
        "git log --since='30 days ago' --oneline --merges | wc -l\n"
        "git log --since='30 days ago' --name-only --diff-filter=A -- docs/ |\n"
        "  grep '\\.md$' | sort | uniq | wc -l\n"
        "\n"
        "# 4) Back-reference greps — backref_rate and cited_frac per class:\n"
        "#    how often terminal docs are cited from OUTSIDE their own dir.\n"
        "for f in .sessions/*.md; do\n"
        '  grep -rl "$(basename "$f")" docs/ --include=\'*.md\' |\n'
        "    grep -v '^.sessions/'; done | sort -u | wc -l\n"
        "\n"
        "# 5) Boot word count — boot_fixed_words / journal_words /\n"
        "#    ledger_base_words: word-count the always-read orientation route.\n"
        "wc -w CLAUDE.md .session-journal.md docs/current-state.md\n"
        "```\n"
        "\n"
        "Sweep discipline: constants you could not measure (staleness, archive\n"
        "pollution) stay assumption-grade — list them in sensitivity_keys so\n"
        "every search re-checks the winner under x1/3 and x3. Adopt a winner\n"
        "only when its rank holds across the whole sweep.\n"
    )

# --- engine/stances/stances.py ---
"""Task-stance definitions — the fourth control axis (plan section 3b).

A *stance* is the working agent's operational posture for the current task,
distinct from adoption-pace (``mode``), promotion-rights, and stage. Following
Roo Code's proven mode model, each stance scopes three things to cut context rot
and tool misfires:

  - a **reading-route** — which docs to load first;
  - a **tool-scope** — which action categories are in-bounds;
  - an **output contract** — what the stance is expected to produce.

The active stance lives in state (``"stance"``) and is **advisory**: the contract
guides the agent, and an optional PreToolUse guard can warn on an out-of-stance
action (e.g. an edit while in ``review``) via :func:`is_out_of_stance`.

Like the question bank, the set ships as a Python module — not the plan's literal
``stances.yml`` — so it embeds in the stdlib-only bootstrap with no YAML parser
and runs identically in ``src`` and the single-file ``dist``.
"""


# Canonical action categories a stance's tool-scope is drawn from.
READ = "read"  # read files / memory / source
RUN = "run"  # run read-only tools / commands
EDIT = "edit"  # modify files
COMMENT = "comment"  # emit review comments (no file edits)

ACTIONS = (READ, RUN, EDIT, COMMENT)

DEFAULT_STANCE = "analysis"

STANCES: list[dict] = [
    {
        "name": "question",
        "role": "Answer concisely from memory and source; make no changes.",
        "when_to_use": "A direct question that memory or a quick read can answer.",
        "reading_route": ["current-state.md", "AGENT_ORIENTATION.md"],
        "tools": [READ],
        "output": "A concise answer grounded in memory/source; no edits.",
    },
    {
        "name": "analysis",
        "role": "Read-only deep-dive: investigate and report, do not change.",
        "when_to_use": "Understanding a system, tracing a behavior, scoping work.",
        "reading_route": ["AGENT_ORIENTATION.md", "architecture.md", "ownership.md"],
        "tools": [READ, RUN],
        "output": "Findings (evidence + conclusion), not changes.",
    },
    {
        "name": "debug",
        "role": "Read, run, and make targeted edits to fix a known fault.",
        "when_to_use": "A reproduced, localized fault with a clear blast radius.",
        "reading_route": ["runtime_contracts.md", "current-state.md"],
        "tools": [READ, RUN, EDIT],
        "output": "A targeted fix for the known fault; no broad refactor.",
    },
    {
        "name": "review",
        "role": "Evaluate a diff against the contracts; comment, do not edit.",
        "when_to_use": "Assessing a change someone else (or a prior stance) produced.",
        "reading_route": ["architecture.md", "ownership.md", "runtime_contracts.md"],
        "tools": [READ, COMMENT],
        "output": "A verdict + comments against the contracts; no edits.",
    },
    {
        "name": "plan",
        "role": "Research + safe prototyping, then propose a plan for approval.",
        "when_to_use": "A multi-step or architectural change worth designing first.",
        "reading_route": ["AGENT_ORIENTATION.md", "current-state.md", "roadmap.md"],
        "tools": [READ, RUN],
        "output": "An approved plan (research + safe prototyping; no committed change).",
    },
]

_BY_NAME = {s["name"]: s for s in STANCES}


def stance_names() -> list[str]:
    """Return the available stance names, in declared order."""
    return [s["name"] for s in STANCES]


def get_stance(name: str) -> dict | None:
    """Return the stance definition for ``name`` (or None if unknown)."""
    return _BY_NAME.get(name)


def action_allowed(name: str, action: str) -> bool:
    """True if ``action`` is in ``name``'s tool-scope (False for an unknown stance)."""
    stance = _BY_NAME.get(name)
    return stance is not None and action in stance["tools"]


def is_out_of_stance(name: str, action: str) -> bool:
    """True if ``action`` falls *outside* a known stance's tool-scope.

    The predicate a PreToolUse guard calls to warn on, e.g., an edit while the
    active stance is ``review``. Returns False for an unknown stance (nothing to
    enforce) so the guard fails **open** — it never blocks on a misconfigured name.
    """
    stance = _BY_NAME.get(name)
    if stance is None:
        return False
    return action not in stance["tools"]


def stance_briefing(name: str) -> str:
    """Return the orientation block injected for the active stance.

    The reading-route + tool-scope + output contract, formatted for injection into
    session orientation (alongside the user-style block and reflection buffer).
    """
    stance = _BY_NAME.get(name)
    if stance is None:
        choices = ", ".join(stance_names())
        return f"Unknown stance {name!r} (choose from {choices})."
    route = " -> ".join(stance["reading_route"])
    tools = ", ".join(stance["tools"])
    return (
        f"Stance: {stance['name']} — {stance['role']}\n"
        f"  When: {stance['when_to_use']}\n"
        f"  Read first: {route}\n"
        f"  In-scope actions: {tools}\n"
        f"  Output: {stance['output']}"
    )

# --- engine/skills/skills.py ---
"""Skill sources + the skill/stance precedence model (plan section 3c).

A *skill* is an invokable procedure emitted as a native ``.claude/skills/<name>/
SKILL.md`` (YAML frontmatter for metadata-first loading + a readable body). Unlike
a stance (an ambient posture), a skill is invoked for a specific job and **declares
the capabilities it needs** — so a skill's declared capability **takes precedence
over the ambient stance** (a ``session-close`` that declares it edits can write the
session log even while the active stance is ``review``). Stances stay advisory for
anything a skill has not declared.

Like the question bank and the stances, the set ships as a Python module — embeds
in the stdlib-only bootstrap with no YAML parser, identical in ``src`` and ``dist``.
Bodies use ``${slot}`` placeholders filled from the interview at build time, so a
skill is project-aware (e.g. ``quality-gate`` runs the project's own verify command).
"""



_SESSION_CLOSE_BODY = """\
Close ${project_name}'s current session correctly.

1. Session log — write `.sessions/<date>-<slug>.md`: what changed, one new idea
   you genuinely believe in, and a one-line review of the previous session.
2. Capability delta — did you discover a new capability or hit a wall this
   session? Append it to `docs/CAPABILITIES.md` (dated, with the exact
   error or the proof it worked, plus any workaround).
3. Owner asks — every ⚑ needs-owner item you leave behind carries the
   OWNER-ACTION fields (WHAT / WHERE / HOW / WHY-IT-MATTERS / UNBLOCKS /
   VERIFIED-NEEDED — you attempted it, or you name the exact wall; see
   `control/README.md`). Withdraw stale asks; fewer, clearer asks beat
   complete lists.
4. Idea backlog — groom one idea forward (the ideas-README lifecycle).
5. Verify — run the project's checks: `${verify_command}` and `bootstrap check`.
6. Commit + push on the session branch; open the PR ready (not draft).
7. Drive the PR to a terminal state — merge on green CI, or close with a reason.

Declared capabilities: edit (the log + docs), run (the checks + git)."""

_QUALITY_GATE_BODY = """\
Prove a change is good before pushing ${project_name}.

1. Run `${verify_command}` — the project's full verification (tests + lint/types).
2. Run `bootstrap check --strict` — doc + session-log hygiene.
3. Report every failure with the exact command to reproduce it.
4. Do NOT push on red — green here should mean green in CI.

Declared capabilities: run."""

_REVIEW_BODY = """\
Review the current branch's diff against ${project_name}'s binding contracts.

1. Read the contracts first (architecture / ownership / runtime), then the diff.
2. For each change check layer boundaries, mutation ownership, and the project's
   invariants. Flag violations with file:line and the rule they break.
3. Produce a verdict (approve / request-changes) + concrete fixes.
4. Do not edit — comment only. (The `review` stance pairs with this skill.)

Declared capabilities: comment."""

_REPO_HEALTH_BODY = """\
Audit ${project_name}'s documentation + session-log hygiene.

1. Run `bootstrap check` — badges, link resolution, doc reachability, and the
   required session-log markers.
2. Summarize the drift: orphaned docs, missing badges, incomplete logs.
3. Fix the small ones (link the orphan, badge the doc); capture the rest as ideas.

Declared capabilities: run."""

_DEEP_RESEARCH_BODY = """\
Answer a multi-source factual question with a cited report.

1. Decompose the question into sub-questions; search broadly (fan out).
2. Fetch the strongest sources; cross-check claims adversarially; prefer
   primary/official docs over memory.
3. Flag uncertainty explicitly; never state a guess as fact.
4. Synthesize a concise report with inline citations.

Declared capabilities: run."""

_QUESTION_BODY = """\
Answer a direct question about ${project_name} concisely.

1. Read current-state + the one relevant doc or source file.
2. Answer in a few sentences, grounded in what you read; cite the source.
3. Make no changes. (The `question` stance pairs with this skill.)

Declared capabilities: read-only."""

_ANALYSIS_BODY = """\
Investigate a ${project_name} system and report findings, changing nothing.

1. Read the binding contracts and trace the behavior across files.
2. Produce evidence (file:line) + a conclusion; name the uncertainty.
3. Do not edit. (The `analysis` stance pairs with this skill.)

Declared capabilities: read-only."""

# Each skill declares the capabilities it needs *beyond* read (read is implicit).
# The declared set is what overrides the ambient stance (the precedence rule).
SKILLS: list[dict] = [
    {
        "name": "session-close",
        "description": "End the session correctly — write the log, groom + add an "
        "idea, verify, commit, push, drive the PR to a terminal state.",
        "capabilities": [EDIT, RUN],
        "body": _SESSION_CLOSE_BODY,
    },
    {
        "name": "quality-gate",
        "description": "Run the project's full verification before pushing and "
        "report what must be fixed.",
        "capabilities": [RUN],
        "body": _QUALITY_GATE_BODY,
    },
    {
        "name": "review",
        "description": "Review the branch diff against the binding contracts; "
        "comment with a verdict and fixes, no edits.",
        "capabilities": [COMMENT],
        "body": _REVIEW_BODY,
    },
    {
        "name": "repo-health",
        "description": "Audit doc + session-log hygiene (bootstrap check) and "
        "summarize drift.",
        "capabilities": [RUN],
        "body": _REPO_HEALTH_BODY,
    },
    {
        "name": "deep-research",
        "description": "Fan out web research, adversarially verify sources, and "
        "synthesize a cited report.",
        "capabilities": [RUN],
        "body": _DEEP_RESEARCH_BODY,
    },
    {
        "name": "question",
        "description": "Answer a direct question concisely from memory and source; "
        "make no changes.",
        "capabilities": [],
        "body": _QUESTION_BODY,
    },
    {
        "name": "analysis",
        "description": "Read-only deep-dive: investigate and report findings "
        "without changing anything.",
        "capabilities": [],
        "body": _ANALYSIS_BODY,
    },
]

_SKILL_BY_NAME = {s["name"]: s for s in SKILLS}


def skill_names() -> list[str]:
    """Return the available skill names, in declared order."""
    return [s["name"] for s in SKILLS]


def get_skill(name: str) -> dict | None:
    """Return the skill definition for ``name`` (or None if unknown)."""
    return _SKILL_BY_NAME.get(name)


def skill_capabilities(name: str) -> list[str]:
    """Return a skill's full capability set (declared + the implicit ``read``)."""
    skill = _SKILL_BY_NAME.get(name)
    if skill is None:
        return []
    return [READ, *skill["capabilities"]]


def skill_permits(name: str, action: str) -> bool:
    """True if skill ``name`` declares (or implies) ``action``."""
    return action in skill_capabilities(name)


def action_permitted(
    stance_name: str,
    action: str,
    skill_name: str | None = None,
) -> bool:
    """Resolve whether ``action`` is permitted under a stance, optionally in a skill.

    Precedence (plan section 3c): a skill's explicitly-declared capability **wins**
    over the ambient stance — so an invoked skill can do what it declares even when
    the stance forbids it. For anything the skill has not declared, the stance's
    advisory tool-scope applies.
    """
    if skill_name is not None and skill_permits(skill_name, action):
        return True
    return action_allowed(stance_name, action)


def skill_frontmatter(skill: dict) -> str:
    """Return the native ``SKILL.md`` YAML frontmatter (metadata-first loading)."""
    return f'---\nname: {skill["name"]}\ndescription: "{skill["description"]}"\n---'


def skill_relpath(skill: dict) -> str:
    """Return the emit path for a skill, relative to the skills root."""
    return f"skills/{skill['name']}/SKILL.md"


def skill_document(skill: dict, body: str) -> str:
    """Compose the full ``SKILL.md`` text from a skill + its (rendered) body."""
    return f"{skill_frontmatter(skill)}\n\n# {skill['name']}\n\n{body.rstrip()}\n"

# --- engine/agents/agents.py ---
"""Persona (sub-agent) sources + native emission (plan section 3c).

A *persona* is a spawnable, read-only specialist (the third capability mechanism
alongside stances and skills): the working agent delegates a focused task —
design review, independent critique, deep exploration — to a fresh sub-agent
context. The kit ships three generalized personas, each emitted as a native
``.claude/agents/<name>.md`` (YAML frontmatter ``name`` / ``description`` /
``tools`` + a system-prompt body).

Personas are **interview-populated**: their binding sources are filled from the
project's own contract slots (``${architecture_layers}``, ``${ownership_model}``,
…) at build time — so a persona reviews against *this* project's rules, not
superbot's. Like the skills, they ship as a Python module (not a subdir of
``templates/``) so they embed in the stdlib-only bootstrap with no extra loader.

Personas are spawned specialists, so — unlike skills — they carry no stance
precedence; they are read-only by construction (their declared ``tools`` grant
no write).
"""


# Native read-only tool set for a spawned specialist (no write/edit/run).
_READONLY_TOOLS = ["Read", "Grep", "Glob"]

_ARCHITECT_BODY = """\
You are ${project_name}'s architecture specialist — read-only. Answer design
questions and review proposed changes for layer/ownership compliance BEFORE they
are coded.

Binding model (this project's contracts):
- Layers & import rules: ${architecture_layers}
- Ownership (who owns each write path): ${ownership_model}
- Mutation seam (how writes are gated): ${mutation_seam}

Method: read the relevant contracts + source, then judge a proposed change
against them. Flag every layer-boundary or ownership violation with file:line and
the rule it breaks; propose the compliant placement. You advise — you do not edit."""

_REVIEWER_BODY = """\
You are ${project_name}'s independent reviewer — a second pair of eyes that does
NOT share the author's assumptions. Evaluate a diff against the binding contracts
and surface the risks the author may have anchored past.

Review against: ${architecture_layers} · ${ownership_model} · the project's
verification (`${verify_command}`).

Anti-anchoring rule: judge the change on its evidence, not the author's stated
confidence. Give a verdict (approve / request-changes) + the specific risks and
fixes. Read-only — you comment, you do not edit. (Wire this persona to the
independent-review seam: a *different* model reviewing breaks the monoculture.)"""

_RESEARCHER_BODY = """\
You are ${project_name}'s researcher — read-only deep exploration. Map unfamiliar
code or trace a behavior across the system and report findings; change nothing.

Start from: ${doc_roots} (where durable documentation lives) and the read-path
docs, then follow the source.

Output: evidence (file:line) + a clear conclusion, with the uncertainty named.
Prefer reading source over assuming. You produce understanding, not edits."""

AGENTS: list[dict] = [
    {
        "name": "architect",
        "description": "Read-only design/layer specialist — answer architecture "
        "questions and flag layer/ownership violations before they are coded.",
        "tools": list(_READONLY_TOOLS),
        "body": _ARCHITECT_BODY,
    },
    {
        "name": "reviewer",
        "description": "Independent critic — evaluate a diff against the contracts "
        "without the author's assumptions; verdict + risks, no edits.",
        "tools": list(_READONLY_TOOLS),
        "body": _REVIEWER_BODY,
    },
    {
        "name": "researcher",
        "description": "Read-only deep exploration — map unfamiliar code / trace a "
        "behavior and report evidence-backed findings; change nothing.",
        "tools": list(_READONLY_TOOLS),
        "body": _RESEARCHER_BODY,
    },
]

_AGENT_BY_NAME = {a["name"]: a for a in AGENTS}


def agent_names() -> list[str]:
    """Return the available persona names, in declared order."""
    return [a["name"] for a in AGENTS]


def get_agent(name: str) -> dict | None:
    """Return the persona definition for ``name`` (or None if unknown)."""
    return _AGENT_BY_NAME.get(name)


def agent_frontmatter(agent: dict) -> str:
    """Return the native ``.claude/agents`` YAML frontmatter (name/description/tools)."""
    tools = ", ".join(agent["tools"])
    return (
        f"---\nname: {agent['name']}\n"
        f'description: "{agent["description"]}"\n'
        f"tools: {tools}\n---"
    )


def agent_relpath(agent: dict) -> str:
    """Return the emit path for a persona, relative to the agents root."""
    return f"agents/{agent['name']}.md"


def agent_document(agent: dict, body: str) -> str:
    """Compose the full agent ``.md`` text from a persona + its (rendered) body."""
    return f"{agent_frontmatter(agent)}\n\n{body.rstrip()}\n"

# --- engine/hooks/stance_guard.py ---
"""PreToolUse stance guard — makes the stance layer enforced, not just advisory.

Claude Code calls a PreToolUse hook before each tool runs, passing the tool name
in a JSON payload on stdin. This maps the tool to a stance action category
(read / run / edit / comment) and, if that action is outside the active stance's
tool-scope, produces an advisory warning — the agent stays free to proceed
(stances are advisory by default, plan section 3b). The bootstrap
``hook pretooluse`` command is the runtime entry point; ``settings_snippet``
generates the ``.claude/settings.json`` wiring a host installs.

Everything here **fails open**: an unknown tool, an unknown stance, or a
malformed payload yields no warning — the guard never gets in the way when it is
unsure.
"""




# Claude Code tool name -> the stance action category it performs. Tools not
# listed (Task, the slash-command tools, …) carry no stance opinion (fail open).
TOOL_ACTIONS: dict[str, str] = {
    "Read": READ,
    "Grep": READ,
    "Glob": READ,
    "NotebookRead": READ,
    "Edit": EDIT,
    "Write": EDIT,
    "NotebookEdit": EDIT,
    "Bash": RUN,
    "WebFetch": RUN,
    "WebSearch": RUN,
}


def tool_to_action(tool_name: str) -> str | None:
    """Return the stance action category a Claude Code tool performs (or None)."""
    return TOOL_ACTIONS.get(tool_name)


def tool_from_payload(raw: str) -> str:
    """Extract the tool name from a PreToolUse stdin payload (``""`` if absent)."""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return ""
    name = payload.get("tool_name", "") if isinstance(payload, dict) else ""
    return name if isinstance(name, str) else ""


def evaluate_tool(stance: str, tool_name: str) -> str | None:
    """Return an out-of-stance warning for ``tool_name`` under ``stance``, or None.

    ``None`` means no objection — the tool carries no stance opinion, or the
    action is within the stance's tool-scope. Fails open: an unknown stance or
    tool never warns.
    """
    action = tool_to_action(tool_name)
    if action is None or not is_out_of_stance(stance, action):
        return None
    return (
        f"out-of-stance: {tool_name} ({action}) while stance is '{stance}'. "
        "Re-check the task, or switch stance (`bootstrap stance <name>`). "
        "(advisory — not blocked)"
    )


def settings_snippet(command: str) -> str:
    """Return a ``.claude/settings.json`` PreToolUse wiring snippet (JSON text).

    ``command`` is the shell command Claude Code runs before each tool (e.g.
    ``python3 bootstrap.py hook pretooluse``). The host merges the returned
    ``hooks.PreToolUse`` block into their ``.claude/settings.json``.
    """
    snippet = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": command}],
                },
            ],
        },
    }
    return json.dumps(snippet, indent=2) + "\n"

# --- engine/hooks/session_start.py ---
"""SessionStart orientation composer (plan section 5.B, Lane B7).

The nervous system's *injection* point: when Claude Code starts a session, the
``bootstrap hook sessionstart`` entry point prints the text this module
composes, so the agent boots already knowing the project's mode, stance,
learned lessons, fired triggers, and pending questions. The composition is
**mode-aware** — ``orientation_depth`` (observe → minimal, guided → standard,
active → full) decides which sections render and how hard they cap.

Section order (the plan's fixed sequence): status header → stance briefing →
user-style block → learned lessons (AFTER user-style) → trigger block →
guided-practices line → economy-gauges advisory (over-cap only) → pending
questions (quota view) → observe-mode workflow proposal.

Every section is defensive: a failure inside one section drops that section,
never the whole composition — orientation must never crash a session. This is
the one place broad ``except Exception`` is correct by design (fail open, like
the stance guard).
"""




# Depth "standard" caps the learned-lessons section at this many entries.
_ORI_STANDARD_LESSON_CAP = 3
# Depth "minimal" (observe) renders only these section numbers: the status
# header (1), the trigger block as an advisory (5), and the workflow proposal
# (9) — observe imposes nothing else.
_ORI_MINIMAL_SECTIONS = frozenset({1, 5, 9})


def _ori_status_header(state: dict[str, Any], config: Config) -> str:
    """Render section 1 — the compact status header line block."""
    project = str(state.get("project_id") or config.project_id)
    return (
        f"# Session orientation — {project}\n"
        f"mode: {state.get('mode', '?')} · stage: {state.get('stage', '?')} · "
        f"stance: {state.get('stance', '?')} · "
        f"session: {int(state.get('session_count', 0))}"
    )


def _ori_stance(state: dict[str, Any]) -> str:
    """Render section 2 — the active stance briefing ('' when no stance set)."""
    stance = state.get("stance")
    if not stance:
        return ""
    return stance_briefing(str(stance))


def _ori_user_style(state: dict[str, Any]) -> str:
    """Render section 3 — the owner_profile user-style block ('' when unfilled)."""
    entry = state.get("slot_values", {}).get("owner_profile")
    value = entry.get("value") if isinstance(entry, dict) else entry
    text = str(value).strip() if value else ""
    if not text:
        return ""
    return f"## How the owner works:\n\n> {text}"


def _ori_lessons(root: Path, config: Config, depth: str) -> str:
    """Render section 4 — learned lessons (standard caps at 3, full uncapped)."""
    entries = load_reflections(root / config.state_dir / REFLECTIONS_FILENAME)
    cap = _ORI_STANDARD_LESSON_CAP if depth == "standard" else len(entries)
    return lessons_block(active_lessons(entries, cap))


def _ori_triggers(root: Path, config: Config, state: dict[str, Any]) -> str:
    """Render section 5 — the trigger block (mandate flag per the mode policy)."""
    triggers = check_triggers(root, config, state)
    questions = mandatory_questions(triggers)
    return trigger_block(triggers, questions, mandate=triggers_mandate(state))


def _ori_practices(state: dict[str, Any], config: Config) -> str:
    """Render section 6 — the one-line guided-practices block ('' when empty)."""
    practices = active_practices(state, dict(config.cadence or {}))
    if not practices:
        return ""
    return "Active practices: " + ", ".join(practices)


def _ori_gauges(root: Path, config: Config) -> str:
    """Render section 7 — economy advisory listing ONLY over-cap gauges."""
    over = [g for g in economy_gauges(root, config) if g.get("over")]
    if not over:
        return ""
    lines = ["## Economy advisory — over-cap gauges", ""]
    lines += [
        f"- {g['name']} ({g['kind']}): {g['value']} words/items over cap {g['cap']}"
        for g in over
    ]
    return "\n".join(lines)


def _ori_questions(state: dict[str, Any]) -> str:
    """Render section 8 — the quota-capped ask list with a '+N more' suffix."""
    asks = session_questions(state)
    if not asks:
        return ""
    lines = ["## Questions this session", ""]
    lines += [
        f"- {q['id']} ({q.get('priority', 'normal')}): {q['prompt']}" for q in asks
    ]
    extra = len(pending_questions(state)) - len(asks)
    if extra > 0:
        lines += ["", f"(+{extra} more later)"]
    return "\n".join(lines)


def _ori_proposal(state: dict[str, Any]) -> str:
    """Render section 9 — observe mode's workflow proposal when it is due."""
    if state.get("mode") != "observe" or not workflow_proposal_due(state):
        return ""
    return (
        "## Proposed workflow\n\n"
        "Observe mode has watched enough sessions to propose a tailored "
        "workflow. If the pacing looks right, switch mode to adopt it: "
        "`bootstrap mode guided` (one practice at a time) or "
        "`bootstrap mode active` (the full workflow now). Observe imposes "
        "nothing until you do."
    )


def _ori_safe(build: Any) -> str:
    """Run one section builder, returning '' on any failure (fail open).

    The one place broad ``except Exception`` is correct by design: a bad state
    document or an unreadable file drops that single section — orientation
    must never crash a session.
    """
    try:
        return str(build()).strip()
    except Exception:  # fail open — one bad section never breaks the whole
        return ""


def compose_orientation(root: Path, config: Config, backend: Any) -> str:
    """Compose the mode-aware SessionStart orientation injection.

    Assembles the nine plan sections in fixed order, gated by
    ``orientation_depth``: ``minimal`` renders only the status header, the
    trigger advisory, and the observe-mode proposal; ``standard`` renders all
    sections but caps lessons at 3; ``full`` renders everything uncapped.
    Every section builder runs inside its own guard — a bad state document or
    an unreadable file drops that one section, never the whole composition
    (orientation must never crash a session).
    """
    try:
        state = dict(backend.data)
    except Exception:  # fail open — orientation never crashes a session
        state = {}
    try:
        depth = orientation_depth(state)
    except Exception:  # fail open — fall back to the default depth
        depth = "standard"
    builders = (
        (1, lambda: _ori_status_header(state, config)),
        (2, lambda: _ori_stance(state)),
        (3, lambda: _ori_user_style(state)),
        (4, lambda: _ori_lessons(root, config, depth)),
        (5, lambda: _ori_triggers(root, config, state)),
        (6, lambda: _ori_practices(state, config)),
        (7, lambda: _ori_gauges(root, config)),
        (8, lambda: _ori_questions(state)),
        (9, lambda: _ori_proposal(state)),
    )
    sections: list[str] = []
    for number, build in builders:
        if depth == "minimal" and number not in _ORI_MINIMAL_SECTIONS:
            continue
        text = _ori_safe(build)
        if text:
            sections.append(text)
    if not sections:
        return ""
    return "\n\n".join(sections) + "\n"

# --- engine/hooks/post_edit.py ---
"""PostToolUse edit advisor (plan section 5.B, Lane B7).

Runs after every Edit/Write tool call: the CLI's ``hook postedit`` entry point
extracts the edited file path from the PostToolUse stdin payload and asks
``evaluate_edit`` whether the edit deserves an advisory —

- **generated artifact** — the file lives under ``<state_dir>/rendered`` or
  ``<state_dir>/contextpacks``, or its head carries the ``NOT SOURCE OF
  TRUTH`` marker: edit the template/index and re-render, not the artifact.
- **missing Status badge** — a ``*.md`` under the docs root without a
  ``> **Status:** `<token>``` badge in its first 12 lines (the same badge scan
  ``check_docs`` runs, via the shared ``badge_token`` reader).

Like every hook evaluator this **fails open**: absolute or root-relative paths
both resolve, and an unreadable / missing file yields ``None`` — the advisor
never gets in the way when it is unsure.
"""




# The HTML-comment form only: planted (hand-editable) docs carry the bare
# phrase "NOT SOURCE OF TRUTH" in their badge prose, and the guard must not
# warn on every legitimate edit of a planted binding doc — only generated
# artifacts (contextpacks etc.) open with this comment marker.
_PE_MARKER = "<!-- NOT SOURCE OF TRUTH"
_PE_HEAD_LINES = 12
# <state_dir> subdirectories that hold build artifacts, never source.
_PE_GENERATED_DIRS = ("rendered", "contextpacks")
_PE_GENERATED_MSG = (
    "generated artifact — edit the template/index and re-render, not this file"
)
_PE_BADGE_MSG = (
    "missing Status badge — add `> **Status:** `<token>`` to its first 12 lines"
)


def _pe_resolve(root: Path, file_path: str) -> tuple[Path, Path | None]:
    """Return ``(absolute path, root-relative path or None)`` for an edit path.

    Accepts absolute and root-relative inputs; the relative half is ``None``
    when the file lives outside ``root`` (nothing to classify against config
    paths there).
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = root / path
    try:
        rel = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        rel = None
    return path, rel


def _pe_head(path: Path) -> str:
    """Return the file's first 12 lines ('' when unreadable — fail open)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""
    return "\n".join(lines[:_PE_HEAD_LINES])


def _pe_is_generated(config: Config, rel: Path | None, head: str) -> bool:
    """True when the edited file is a build artifact (by path or by marker)."""
    if _PE_MARKER in head:
        return True
    if rel is None:
        return False
    state_dir = Path(config.state_dir)
    return any(rel.is_relative_to(state_dir / sub) for sub in _PE_GENERATED_DIRS)


def evaluate_edit(root: Path, config: Config, file_path: str) -> str | None:
    """Return the advisory warning for one edited file, or None.

    Warns on a generated artifact (path under ``<state_dir>/rendered`` /
    ``<state_dir>/contextpacks``, or the generated-artifact HTML-comment marker)
    and on a docs-root ``*.md`` lacking a Status badge. Tolerant of absolute
    or root-relative ``file_path`` and of unreadable / missing files (None).
    """
    try:
        path, rel = _pe_resolve(root, file_path)
        if not path.is_file():
            return None
        name = rel.as_posix() if rel is not None else path.as_posix()
        if _pe_is_generated(config, rel, _pe_head(path)):
            return f"{name}: {_PE_GENERATED_MSG}"
        if (
            rel is not None
            and path.suffix == ".md"
            and rel.is_relative_to(Path(config.docs_root))
            and badge_token(path) is None
        ):
            return f"{name}: {_PE_BADGE_MSG}"
        return None
    except Exception:  # fail open — the advisor never blocks an edit
        return None

# --- engine/hooks/stop_check.py ---
"""Stop-hook session-close advisor (plan section 5.B, Lane B7).

Runs when a Claude Code session stops: the CLI's ``hook stopcheck`` entry
point prints the advisory lines ``evaluate_stop`` returns, reminding the agent
what the session ritual still owes —

- the session log is missing, or exists but lacks required markers
  (``latest_session_log`` + ``check_log`` with ``config.session_markers``);
- escalated blocking questions are still open (``state["open_questions"]``);
- the compaction cadence window has elapsed (``compaction_due``);
- the reflection buffer has not been mined today
  (``reflection_buffer.last_mined`` vs today's ISO date);
- no configured control heartbeat (``config.heartbeat_files``, default
  ``control/status.md``) was overwritten this session (KL-8: the
  coordination protocol's deliberate LAST step) — every existing heartbeat
  file's mtime predates the KL-5 session-start anchor's epoch. Skipped,
  fail-open, when the protocol or the anchor is absent; in a multi-lane
  repo (ORDER 004) ANY lane's fresh heartbeat clears the advisory (a
  session cannot know which lane it belongs to, so it never nags a lane
  that isn't its own).

Returns ``[]`` when all clean. Advisory only, and it **fails open**: every
check runs inside its own guard, so a bad state document or an unreadable log
drops that one advisory rather than crashing the stop hook.
"""




_STOP_UNMINED_MSG = "reflections unmined this session — run bootstrap reflect --mine"


def _stop_safe(check: Any) -> list[str]:
    """Run one advisory check, returning [] on any failure (fail open).

    Each check is guarded on its own so one bad input never suppresses the
    other advisories — the stop hook is advisory by contract.
    """
    try:
        return list(check())
    except Exception:  # fail open — one bad check drops only itself
        return []


def _stop_state(backend: Any) -> dict[str, Any]:
    """Return the state document ({} when the backend is unusable — fail open)."""
    try:
        return dict(backend.data)
    except Exception:  # fail open — a broken backend yields no state advisories
        return {}


def _stop_log(root: Path, config: Config) -> list[str]:
    """Advise when the session log is missing or lacks required markers."""
    log = latest_session_log(root / config.sessions_dir)
    if log is None:
        return [
            f"no session log found under {config.sessions_dir}/ — "
            "write one before ending the session",
        ]
    missing = check_log(log, config.session_markers)
    if missing:
        return [f"session log {log.name} is missing: {', '.join(missing)}"]
    return []


def _stop_questions(state: dict[str, Any]) -> list[str]:
    """Advise when escalated blocking questions are still open."""
    open_questions = [str(q) for q in state.get("open_questions", [])]
    if not open_questions:
        return []
    listed = ", ".join(open_questions)
    return [f"{len(open_questions)} blocking question(s) open: {listed}"]


def _stop_compaction(state: dict[str, Any], config: Config) -> list[str]:
    """Advise when the compaction cadence window has elapsed."""
    if compaction_due(state, dict(config.cadence or {})):
        return ["compaction due — write the State Delta snapshot (bootstrap maintain)"]
    return []


def _stop_reflections(state: dict[str, Any]) -> list[str]:
    """Advise when the reflection buffer has not been mined today."""
    buffer = state.get("reflection_buffer")
    last_mined = buffer.get("last_mined") if isinstance(buffer, dict) else None
    if last_mined == date.today().isoformat():
        return []
    return [_STOP_UNMINED_MSG]


def _stop_status(root: Path, state: dict[str, Any], config: Config) -> list[str]:
    """Advise when no control heartbeat was overwritten this session.

    The coordination protocol's LAST step (KL-8) is overwriting the status
    heartbeat; a session that ends without it leaves the manager reading a
    stale (eventually dark) Project. Evidence = file mtime vs the KL-5
    session-start anchor's epoch — no anchor (or no protocol) means no basis
    for the claim, so the advisory is skipped rather than guessed. The
    checked set is ``config.heartbeat_files`` (ORDER 004 — one file per lane
    in a shared multi-Project repo); a fresh mtime on ANY existing lane file
    clears the advisory, because the hook cannot know which lane this
    session belongs to and must not nag another lane's duty.
    """
    statuses = [
        root / rel
        for rel in heartbeat_relpaths(config.heartbeat_files)
        if (root / rel).is_file()
    ]
    if not statuses:
        return []
    anchor = state.get(SESSION_ANCHOR_KEY)
    epoch = anchor.get("epoch") if isinstance(anchor, dict) else None
    if not isinstance(epoch, (int, float)) or isinstance(epoch, bool):
        return []
    if any(status.stat().st_mtime >= float(epoch) for status in statuses):
        return []
    named = ", ".join(
        status.relative_to(root).as_posix() for status in statuses
    )
    return [
        f"{named} not overwritten this session — the protocol's "
        "deliberate LAST step (see control/README.md)",
    ]


def evaluate_stop(root: Path, config: Config, backend: Any) -> list[str]:
    """Return the session-close advisory lines ([] when all clean).

    Five checks in fixed order: session log, open blocking questions,
    compaction cadence, reflection mining, the control-status heartbeat
    (KL-8). Each runs inside its own guard so
    one failing check never suppresses the others — the stop hook is advisory
    and fails open by contract.
    """
    state = _stop_state(backend)
    checks = (
        lambda: _stop_log(root, config),
        lambda: _stop_questions(state),
        lambda: _stop_compaction(state, config),
        lambda: _stop_reflections(state),
        lambda: _stop_status(root, state, config),
    )
    advisories: list[str] = []
    for check in checks:
        advisories.extend(_stop_safe(check))
    return advisories

# --- engine/hooks/settings.py ---
"""Hook settings template + customization contract (plan section 5.B, Lane B7).

The staging half of the hook layer (HOOK-2): ``full_settings_template`` emits
the complete ``.claude`` ``settings.template.json`` wiring all four hook
events — PreToolUse (stance guard), SessionStart (orientation), PostToolUse
(edit advisor), Stop (session-close advisor) — each to
``<interpreter> bootstrap.py hook <event>``, the same command shape the CLI's
``_hook_command`` builds. ``hooks_fill_table`` emits the markdown
customization contract a host reads before merging: which config fields must
match their repo, and the standing rule that the kit *stages* hook settings —
it never writes a live ``.claude/`` tree itself.
"""




# (settings.json event key, bootstrap hook event, tool matcher or None).
_SET_EVENTS: tuple[tuple[str, str, str | None], ...] = (
    ("PreToolUse", "pretooluse", "*"),
    ("SessionStart", "sessionstart", None),
    ("PostToolUse", "postedit", "Edit|Write|NotebookEdit"),
    ("Stop", "stopcheck", None),
)

_SET_FILL_ROWS: tuple[tuple[str, str], ...] = (
    (
        "`interpreter`",
        "the Python that runs the kit itself — every hook command below "
        "starts with it; set it to an interpreter available on your PATH",
    ),
    (
        "`interpreter_for_checks`",
        "your *project's* verification interpreter (the version your CI "
        "pins, e.g. `python3.10`) — kept separate from `interpreter` on "
        "purpose",
    ),
    (
        "`bootstrap.py` path",
        "each hook command assumes `bootstrap.py` sits at your repo root; "
        "rewrite the path inside every command if it lives elsewhere",
    ),
    (
        "`state_dir`",
        "where kit state + staged artifacts live (default `.substrate`) — "
        "the post-edit generated-artifact warning keys off it",
    ),
    (
        "`docs_root`",
        "your documentation root (default `docs`) — the post-edit badge "
        "warning and the SessionStart trigger scan key off it",
    ),
    (
        "`sessions_dir`",
        "where per-session logs live (default `.sessions`) — the Stop-hook "
        "session-log advisory keys off it",
    ),
    (
        "cadence knobs",
        "`cadence.*` in `substrate.config.json` (`compaction_sessions`, "
        "`reconciliation_sessions`, `staleness_days`, "
        "`critical_slot_grace_sessions`, `guided_practice_sessions`) drive "
        "the SessionStart triggers and Stop-hook advisories",
    ),
)


def _set_command(config: Config, event: str, bootstrap_path: str) -> str:
    """Return the shell command Claude Code runs for one hook event."""
    return f"{config.interpreter} {bootstrap_path} hook {event}"


def full_settings_template(config: Config, bootstrap_path: str = "bootstrap.py") -> str:
    """Return the complete ``settings.template.json`` wiring all four hooks.

    JSON text (2-space indent) a host merges into ``.claude/settings.json``:
    PreToolUse (matcher ``*``), SessionStart, PostToolUse (matcher
    ``Edit|Write|NotebookEdit``), and Stop, each running
    ``<interpreter> <bootstrap_path> hook <event>``. Matcher-less events omit
    the ``matcher`` key entirely (they apply unconditionally).
    ``bootstrap_path`` is the path the hook commands reference — adopt passes
    the vendored/root-resolved location so staged hooks resolve inside the
    target repo (the Phase-2.5 staged-hook failure cause).
    """
    hooks: dict[str, list[dict]] = {}
    for settings_event, cli_event, matcher in _SET_EVENTS:
        entry: dict = {}
        if matcher is not None:
            entry["matcher"] = matcher
        entry["hooks"] = [
            {
                "type": "command",
                "command": _set_command(config, cli_event, bootstrap_path),
            },
        ]
        hooks[settings_event] = [entry]
    return json.dumps({"hooks": hooks}, indent=2) + "\n"


def hooks_fill_table() -> str:
    """Return the markdown customization contract for the settings template.

    One ``field | what must match your repo`` row per knob a host must verify
    before installing, plus the install instruction: merge the staged template
    into ``.claude/settings.json`` yourself — the kit stages hook settings, it
    never writes a live ``.claude/`` tree.
    """
    lines = [
        "# Hook settings — customization contract",
        "",
        "The kit **stages** `settings.template.json`; it never writes your",
        "`.claude/` tree. Install by merging the template's `hooks` block into",
        "your repo's `.claude/settings.json` yourself, after checking every",
        "row below against your repo.",
        "",
        "| field | what must match your repo |",
        "| --- | --- |",
    ]
    lines += [f"| {field} | {note} |" for field, note in _SET_FILL_ROWS]
    lines += [
        "",
        "All four hooks are advisory and fail open: they always exit 0 and",
        "never block a tool, an edit, or a session stop.",
    ]
    return "\n".join(lines) + "\n"

# --- engine/render.py ---
"""Render the project's content docs from templates + filled interview slots.

Templates use ``${slot_name}`` placeholders (``string.Template``). A slot the
interview has filled substitutes in; an unfilled slot is left as ``${slot_name}``
and reported — so a half-onboarded project's gaps stay visible rather than going
silently blank. Templates ship embedded in the bootstrap (the generated
``_TEMPLATES`` dict) and, in the source/pip layouts, under
``engine/templates/`` (inside the package so a wheel ships them).
"""




_PLACEHOLDER_RE = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Context keys the ENGINE computes and injects itself — never interview
# slots. The template/bank coherence guard (tests/test_render.py) exempts
# exactly this set, so a template may reference them without a bank question
# existing. Grows deliberately: every addition must be injected by
# build_context (or a caller) unconditionally, or templates strand unfilled.
ENGINE_CONTEXT_KEYS = frozenset({"kit_version"})


def find_placeholders(text: str) -> set[str]:
    """Return the set of ``${name}`` placeholders remaining in ``text``."""
    return set(_PLACEHOLDER_RE.findall(text))


def render(text: str, context: dict[str, str]) -> str:
    """Substitute ``${slot}`` placeholders from ``context`` (unfilled left as-is).

    Only the braced ``${name}`` form is a placeholder — the *same* form
    ``find_placeholders`` reports, so render and the "unfilled slots stay
    visible" safety net can never disagree. Deliberately NOT
    ``string.Template.safe_substitute``: that also collapses ``$$`` → ``$`` and
    substitutes unbraced ``$word``, silently mangling host-authored ``$``
    content (shell ``$$``/``$1``, ``$5`` prices, ``$$LaTeX$$``) on the routine
    ``render --live`` in-place fill — and turning an escaped ``$${VERSION}``
    into a live-looking ``${VERSION}`` that then reports as an unfilled slot.
    A regex sub over the braced form leaves every other ``$`` byte untouched.
    """
    return _PLACEHOLDER_RE.sub(
        lambda m: context[m.group(1)] if m.group(1) in context else m.group(0),
        text,
    )


def build_context(state: dict[str, Any]) -> dict[str, str]:
    """Build the substitution context from a state document's filled slots.

    ``kit_version`` is always present (never a slot): it is the running
    engine's own :data:`KIT_VERSION`, injected here — the single point every
    render path (adopt / upgrade / ``render --live``) flows through — so the
    ``kit:`` self-report line in the planted ``control/status.md`` seed
    (inbox ORDER 003, adopter-visibility band) renders with the real version
    instead of stranding as an unfilled placeholder. A slot named
    ``kit_version`` (none exists) would win over the constant by design.
    (Top-level import on purpose: ``lib/config.py`` precedes ``render.py``
    in the dist's MODULE_ORDER, so the intra-package import strips cleanly;
    a function-body ``from engine...`` would survive into the single file
    and fail at dist runtime.)
    """
    values = state.get("slot_values", {})
    context = {slot: str(entry.get("value", "")) for slot, entry in values.items()}
    context.setdefault("kit_version", KIT_VERSION)
    return context


def load_templates() -> dict[str, str]:
    """Return ``{filename: text}`` for every template (embedded or packaged).

    The single-file bootstrap embeds them as ``_TEMPLATES``; the source/pip
    layouts read ``engine/templates/`` (INSIDE the package, so a wheel ships
    them — they once lived a level up and a pip install silently had none).
    An empty template set is a hard error, never a silent no-op render.
    """
    embedded = globals().get("_TEMPLATES")
    if embedded is not None:
        return dict(embedded)
    root = Path(__file__).resolve().parent / "templates"
    templates = {
        p.name: p.read_text(encoding="utf-8") for p in sorted(root.glob("*.tmpl"))
    }
    if not templates:
        msg = f"no templates found at {root} — broken install"
        raise FileNotFoundError(msg)
    return templates

# --- engine/derive.py ---
"""Adopt-time slot derivation — "adopt renders what it knows" (the Phase-2.5 G2 fix).

The cold-start A/B (``phase-2.5-cold-start-report-2026-07-07.md``) failed
because ``adopt`` planted raw ``${...}`` templates: a task-focused cold
session paid the reading cost and (correctly) ignored them. The fix has two
halves; this module is the first — derive every slot the kit can know
**deterministically** from the target tree (project name, primary language,
verify command, docs root) and record each as a *provisional* interview
answer before the adopt render, so the planted docs open readable instead of
inert. Provisional answers never count toward graduation until confirmed
(the interview contract is unchanged) and ``bootstrap ask`` still asks —
derivation seeds the interview, it does not replace it. Detection is
file-presence based, never a guess: a slot with no confident signal stays
unfilled (and the adopt banner marks it — the second half, in ``adopt.py``).
Pure stdlib.
"""




_REQUIRES_PYTHON_RE = re.compile(r'requires-python\s*=\s*"([^"]+)"')
_MAKEFILE_TEST_RE = re.compile(r"^test\s*:", re.MULTILINE)

# Marker files that make a tree confidently Python before any other check.
_PYTHON_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")


def _read_if_exists(path: Path) -> str:
    """Return the file's text, or empty for a missing/unreadable file."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def detect_language(root: Path) -> str | None:
    """Return the project's primary language from marker files, or None.

    Python wins ties deliberately (the kit's own tooling is Python-first and a
    mixed tree with a ``pyproject.toml`` is Python-led for verification
    purposes). The version qualifier comes only from an explicit
    ``requires-python`` — never inferred.
    """
    if any((root / marker).is_file() for marker in _PYTHON_MARKERS):
        match = _REQUIRES_PYTHON_RE.search(_read_if_exists(root / "pyproject.toml"))
        return f"Python {match.group(1)}" if match else "Python"
    if (root / "package.json").is_file():
        return "TypeScript" if (root / "tsconfig.json").is_file() else "JavaScript"
    if (root / "Cargo.toml").is_file():
        return "Rust"
    if (root / "go.mod").is_file():
        return "Go"
    return None


def _python_has_tests(root: Path) -> bool:
    """True when the tree carries a recognizable pytest surface."""
    if (root / "tests").is_dir() or (root / "pytest.ini").is_file():
        return True
    pyproject = _read_if_exists(root / "pyproject.toml")
    return "[tool.pytest" in pyproject


def _npm_has_real_test_script(root: Path) -> bool:
    """True when package.json declares a test script that isn't npm's stub."""
    text = _read_if_exists(root / "package.json")
    if '"test"' not in text:
        return False
    return "no test specified" not in text


def detect_verify_command(root: Path) -> str | None:
    """Return the one-command verification entry point, or None.

    Order mirrors :func:`detect_language`; each candidate requires a positive
    marker (a test tree, a real test script, a ``test:`` target) so the
    derived command is runnable, not aspirational.
    """
    if any((root / marker).is_file() for marker in _PYTHON_MARKERS):
        if _python_has_tests(root):
            return "python3 -m pytest"
        return None
    if (root / "package.json").is_file() and _npm_has_real_test_script(root):
        return "npm test"
    if (root / "Cargo.toml").is_file():
        return "cargo test"
    if (root / "go.mod").is_file():
        return "go test ./..."
    if _MAKEFILE_TEST_RE.search(_read_if_exists(root / "Makefile")):
        return "make test"
    return None


def derive_slots(root: Path, docs_root: str) -> dict[str, str]:
    """Return every slot value derivable from the target tree.

    Keys match the question bank's slot names. Only confidently-derived
    entries appear — absent key means "leave the slot to the interview".
    """
    derived: dict[str, str] = {"project_name": root.resolve().name}
    language = detect_language(root)
    if language:
        derived["primary_language"] = language
    verify = detect_verify_command(root)
    if verify:
        derived["verify_command"] = verify
    if docs_root:
        derived["doc_roots"] = docs_root
    return derived


def record_derived_slots(backend: Any, derived: dict[str, str]) -> list[str]:
    """Record derived values as provisional answers for still-empty slots.

    Existing answers of any status (filled / partial / provisional) are never
    overwritten — derivation only seeds blanks. Returns report lines in the
    adopt-report format.
    """
    by_slot = {question["slot"]: question for question in QUESTIONS}
    slots = backend.get("slots", {})
    lines: list[str] = []
    for slot, value in derived.items():
        question = by_slot.get(slot)
        if question is None or slots.get(slot):
            continue
        record_answer(backend, question, value, source="derived")
        lines.append(
            f"derived: {slot} = {value!r} (provisional — confirm or correct "
            f"via `bootstrap answer {slot} ...`)",
        )
    return lines

# --- engine/contextpack.py ---
"""AgentContextPack generator — index-or-manifest input (Lane B8, spec 2.10).

Generates per-area *context packs* — the curated "what an agent must know to
work in this area" bundles — from a project index. Two input forms are
accepted (design-spec 2.10: the generator meets hosts where they are):

  1. the kit's own ``project.index.json`` (``{"areas": [...]}``, planted by
     the adopt flow as a skeleton), and
  2. a manifest snapshot (``{"subsystems": [...]}``) as produced by a host's
     existing subsystem manifest — mapped onto the same area shape with
     sensible fallbacks.

Each pack is written under ``<state_dir>/contextpacks/`` and opens with the
``NOT SOURCE OF TRUTH`` marker: packs are build artifacts — regenerate them
from the index, never hand-edit them. Pure stdlib; every write goes through
``atomic_write_text``.
"""




_PACK_MARKER = (
    "<!-- NOT SOURCE OF TRUTH — generated by substrate-kit; "
    "regenerate, do not edit. -->"
)

# The list-valued fields of the canonical area shape, in emit order.
_PACK_LIST_KEYS = (
    "binding_docs",
    "source_roots",
    "do_not_create",
    "gates",
    "verification",
)

_PACK_SECTION_TITLES = {
    "binding_docs": "Binding docs",
    "source_roots": "Source roots",
    "do_not_create": "Do-not-create",
    "gates": "Gates",
    "verification": "Verification",
}

_PACK_SLUG_STRIP_RE = re.compile(r"[^a-z0-9._-]")
_PACK_SLUG_SEP_RE = re.compile(r"[\s/\\]+")


def _pack_slug(name: str) -> str:
    """Slugify an area name for its pack filename (spaces/slashes -> dashes)."""
    slug = _PACK_SLUG_SEP_RE.sub("-", name.strip().lower())
    slug = _PACK_SLUG_STRIP_RE.sub("", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "area"


def _pack_as_list(value: object) -> list[str]:
    """Coerce an index field to a list of strings (unknown/missing -> [])."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _pack_area(entry: dict) -> dict:
    """Normalise one raw index entry onto the canonical area shape."""
    name = str(entry.get("name") or "").strip() or "unnamed-area"
    folio = entry.get("folio")
    area: dict = {
        "name": name,
        "folio": str(folio).strip() if isinstance(folio, str) else "",
    }
    for key in _PACK_LIST_KEYS:
        area[key] = _pack_as_list(entry.get(key))
    return area


def _pack_from_subsystem(entry: dict) -> dict:
    """Map a manifest-snapshot subsystem entry onto the area shape."""
    mapped = dict(entry)
    if not mapped.get("binding_docs"):
        mapped["binding_docs"] = mapped.get("docs")
    if not mapped.get("source_roots"):
        mapped["source_roots"] = mapped.get("roots")
    return _pack_area(mapped)


def load_pack_index(path: Path) -> list[dict]:
    """Load a pack index from ``path``, accepting both supported forms.

    Detects the form by top-level key: ``{"areas": [...]}`` is the kit's own
    ``project.index.json``; ``{"subsystems": [...]}`` is a host manifest
    snapshot (``docs``/``roots`` map onto ``binding_docs``/``source_roots``).
    Unknown or missing per-entry keys become empty lists. Raises ``ValueError``
    when the document is neither form (a wrong file, not a quiet no-op).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("areas"), list):
        return [_pack_area(e) for e in data["areas"] if isinstance(e, dict)]
    if isinstance(data, dict) and isinstance(data.get("subsystems"), list):
        return [
            _pack_from_subsystem(e) for e in data["subsystems"] if isinstance(e, dict)
        ]
    msg = f"{path.name}: expected top-level 'areas' or 'subsystems' list"
    raise ValueError(msg)


def _pack_section(title: str, items: list[str]) -> list[str]:
    """Render one pack section as markdown lines (empty section -> no lines)."""
    if not items:
        return []
    return [f"## {title}", "", *(f"- {item}" for item in items), ""]


def _pack_body(root: Path, area: dict) -> str:
    """Compose one pack's full markdown text from a normalised area."""
    lines = [_PACK_MARKER, "", f"# {area['name']} — agent context pack", ""]
    lines += _pack_section("Folio", [area["folio"]] if area["folio"] else [])
    for key in _PACK_LIST_KEYS:
        items = area[key]
        if key == "source_roots":
            items = [
                entry if (root / entry).exists() else f"{entry} (MISSING)"
                for entry in items
            ]
        lines += _pack_section(_PACK_SECTION_TITLES[key], items)
    return "\n".join(lines).rstrip() + "\n"


def generate_packs(root: Path, config: Config, index: list[dict]) -> list[Path]:
    """Write one context pack per index area; return the written paths.

    Packs land in ``<root>/<state_dir>/contextpacks/<slug>.context.md``.
    ``source_roots`` entries are existence-checked against ``root`` and
    suffixed `` (MISSING)`` when absent, so a stale index is visible in the
    pack instead of silently misleading the agent reading it.
    """
    out_dir = root / config.state_dir / "contextpacks"
    written: list[Path] = []
    used: set[str] = set()
    for entry in index:
        area = _pack_area(entry)
        # Two areas whose names slugify alike (``Economy``/``economy``,
        # ``API v1``/``API-v1``, two unnamed areas → ``area``) must not land on
        # one filename: the later ``atomic_write_text`` would silently erase the
        # earlier pack and ``written`` would double-count one file. Disambiguate
        # to the first free ``slug`` / ``slug-2`` / ``slug-3`` … (robust even if
        # a real ``slug-2`` area also exists); the pack body still names its area
        # in the heading, so a suffixed file stays identifiable.
        base = _pack_slug(area["name"])
        slug, n = base, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        path = out_dir / f"{slug}.context.md"
        atomic_write_text(path, _pack_body(root, area))
        written.append(path)
    return written


def pack_index_skeleton(project_name: str) -> str:
    """Return the planted ``project.index.json`` skeleton (JSON text).

    One example area with every field present-but-empty, plus a ``_comment``
    explaining how each field feeds the AgentContextPack generator
    (index-or-manifest input, design-spec 2.10).
    """
    skeleton = {
        "_comment": (
            "AgentContextPack index (design-spec 2.10). Each `areas` entry "
            "feeds one generated <state_dir>/contextpacks/<name>.context.md: "
            "`name` (the area; slugified into the pack filename), `folio` "
            "(the canonical entry-point doc for the area), `binding_docs` "
            "(authoritative contracts to read first), `source_roots` (key "
            "files/dirs; existence-checked at generation, missing ones "
            "flagged), `do_not_create` (existing systems an agent must not "
            "duplicate), `gates` (currently active expansion conditions), "
            "`verification` (commands to run before pushing). The generator "
            'also accepts a manifest snapshot ({"subsystems": [...]}) '
            "instead of this file."
        ),
        "project": project_name,
        "areas": [
            {
                "name": "example-area",
                "folio": "",
                "binding_docs": [],
                "source_roots": [],
                "do_not_create": [],
                "gates": [],
                "verification": [],
            },
        ],
    }
    return json.dumps(skeleton, indent=2) + "\n"

# --- engine/adopt.py ---
"""One-step adopt flow — plant the workflow docs, stage the packs (Lane B8).

``adopt`` turns a bare host repo into a substrate-governed one in a single
idempotent pass: it renders every content template with the currently filled
interview slots and *plants* the live docs (constitution, contracts, ledgers,
session scaffolding) — **skip-if-exists, never clobbering** a file the host
already owns — then *stages* the ``.claude`` material (working agreement,
skill pack, persona pack, hook wiring, CI example) under ``<state_dir>`` for
the host to install deliberately. Only an explicit ``include_claude=True``
writes a live ``.claude/`` tree, and even then only files that are absent
(the host opt-in stays non-destructive).

Adopt renders what it knows (the Phase-2.5 G2 fix): before rendering, every
deterministically-derivable slot (project name, language, verify command,
docs root — ``engine/derive.py``) is recorded as a provisional interview
answer, and any doc still carrying unfilled ``${slot}`` placeholders is
planted under a loud UNRENDERED banner instead of silently inert — a cold
session sees at a glance which prose is live and which is an unfilled slot.
The guardrail runs first: the kit refuses to adopt into its own tree. Pure
stdlib; every write goes through ``atomic_write_text``.
"""




# Template filename -> planted relpath. CLAUDE.md.tmpl is deliberately absent:
# it is STAGED under <state_dir>/claude/ (the kit never live-writes .claude/
# without the explicit include_claude opt-in).
ADOPT_PLAN: list[tuple[str, str]] = [
    ("CONSTITUTION.md.tmpl", "CONSTITUTION.md"),
    ("decisions.md.tmpl", "docs/decisions.md"),
    ("architecture.md.tmpl", "docs/architecture.md"),
    ("ownership.md.tmpl", "docs/ownership.md"),
    ("runtime_contracts.md.tmpl", "docs/runtime_contracts.md"),
    ("repo-navigation-map.md.tmpl", "docs/repo-navigation-map.md"),
    ("helper-policy.md.tmpl", "docs/helper-policy.md"),
    ("collaboration-model.md.tmpl", "docs/collaboration-model.md"),
    ("ai-project-workflow.md.tmpl", "docs/ai-project-workflow.md"),
    ("owner-profile.md.tmpl", "docs/owner-profile.md"),
    ("AGENT_ORIENTATION.md.tmpl", "docs/AGENT_ORIENTATION.md"),
    ("current-state.md.tmpl", "docs/current-state.md"),
    ("question-router.md.tmpl", "docs/question-router.md"),
    # Capability manifest (inbox ORDER 006): what sessions in this
    # environment can and cannot do — verified findings + the discovery
    # rule (check file → check env → attempt once + capture the exact
    # error → append same session). Sessions read it at start (orientation
    # wiring in CLAUDE.md/CONSTITUTION/AGENT_ORIENTATION templates) and
    # append discoveries at close (session-close skill nudge), so one
    # session's imagined-wall lesson never costs a second session.
    ("CAPABILITIES.md.tmpl", "docs/CAPABILITIES.md"),
    ("ideas-README.md.tmpl", "docs/ideas/README.md"),
    ("session-journal.md.tmpl", ".session-journal.md"),
    # The fleet coordination protocol (band KL-8, spec: superbot
    # docs/planning/fleet-coordination-protocol-2026-07-09.md §2): committed
    # git files are the only medium Projects share, so every adopted repo
    # gets the control/ bus — the manager-written inbox, the project-written
    # status heartbeat, and the local protocol contract. Root-level on
    # purpose (a bus, not documentation): _adopt_dest's docs_root remap
    # never applies.
    ("control-README.md.tmpl", "control/README.md"),
    ("control-inbox.md.tmpl", "control/inbox.md"),
    ("control-status.md.tmpl", "control/status.md"),
]

# State key holding {planted relpath: sha256 hex} for every doc the kit last
# wrote (planted by adopt, or re-rendered in place by `render --live`).
# "Consumer-untouched" is decided by comparing a doc's current hash to this
# record — never by re-rendering old templates, whose slot/banner/date
# substitution makes byte-matching impossible (founding plan §4.3). `upgrade`
# reads it to classify planted-doc drift; installs predating the record have
# no hashes and are honestly treated as consumer-diverged.
DOC_HASHES_STATE_KEY = "planted_doc_hashes"


def _sha256_text(text: str) -> str:
    """Return the sha256 hex digest of ``text`` (utf-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_doc_hash(backend: Any, relpath: str, text: str) -> None:
    """Record ``text``'s sha256 under ``relpath`` in the planted-doc hash map."""
    hashes = dict(backend.get(DOC_HASHES_STATE_KEY) or {})
    hashes[relpath] = _sha256_text(text)
    backend.set(DOC_HASHES_STATE_KEY, hashes)


def doc_is_untouched(backend: Any, relpath: str, current_text: str) -> bool:
    """True when ``current_text`` still matches the recorded kit-written hash."""
    hashes = backend.get(DOC_HASHES_STATE_KEY) or {}
    recorded = hashes.get(relpath)
    return recorded is not None and recorded == _sha256_text(current_text)


BACKUP_DIRNAME = "backup"

# Lane names become path components (`control/status-<lane>.md`) and config
# entries, so the charset is deliberately tight: no separators, no dots, no
# spaces — nothing that could escape control/ or read ambiguously in a list.
_LANE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

SINGLE_HEARTBEAT_RELPATH = "control/status.md"


def lane_status_relpath(lane: str) -> str:
    """Return the per-lane heartbeat relpath (`control/status-<lane>.md`)."""
    return f"control/status-{lane}.md"


def validate_lane_name(lane: str) -> str:
    """Return ``lane`` unchanged, or raise ``ValueError`` for an unsafe name.

    Runs before any write: a lane name is interpolated into a planted path
    and into ``heartbeat_files``, so a bad one must refuse the whole adopt,
    never plant-then-apologize.
    """
    if not _LANE_NAME_RE.fullmatch(lane):
        raise ValueError(
            f"invalid lane name {lane!r} — use letters/digits/hyphen/underscore "
            "(it becomes control/status-<lane>.md)",
        )
    return lane


def _register_lane_heartbeat(
    root: Path,
    config: Config,
    lane: str,
    report: list[str],
) -> bool:
    """Register the lane's heartbeat in ``config.heartbeat_files`` (in place).

    Returns True when the config changed (the caller persists it). Rules,
    all idempotent:

    - already listed → nothing to do (re-adopt safe);
    - the list is still the untouched default (``control/status.md``) and the
      singular file does NOT exist on disk (a lane-shaped repo from the
      start — the ``--lane`` adopt never planted it) → the lane file
      *replaces* the default entry, because the status gate treats every
      listed heartbeat as mandatory and must not hold strict RED on a
      singular file no Project owns;
    - otherwise (a first Project already beats on ``control/status.md``, or
      a custom list names sibling lanes) → *append*, never dropping another
      lane's declared heartbeat (one-writer-per-file scales by splitting).

    An empty configured list means "the default" at every consumer
    (misconfiguration never silently disables the gate), so it is expanded
    to the default before the rules above apply.
    """
    lane_rel = lane_status_relpath(lane)
    files = list(config.heartbeat_files) or [SINGLE_HEARTBEAT_RELPATH]
    if lane_rel in files:
        report.append(f"lane: {lane} — heartbeat already declared ({lane_rel})")
        return False
    if files == [SINGLE_HEARTBEAT_RELPATH] and not (
        root / SINGLE_HEARTBEAT_RELPATH
    ).exists():
        files = [lane_rel]
    else:
        files.append(lane_rel)
    config.heartbeat_files = files
    report.append(
        f"lane: {lane} — heartbeat_files now {files} (substrate.config.json)",
    )
    return True

_DIST_VERSION_RE = re.compile(r"bootstrap v(\d[^\s]*)")


def dist_version(text: str) -> str | None:
    """Parse the version stamp out of a single-file bootstrap's header line."""
    first_line = text.split("\n", 1)[0]
    match = _DIST_VERSION_RE.search(first_line)
    return match.group(1) if match else None


def archive_dist(
    root: Path,
    config: Config,
    dist_file: Path,
    report: list[str],
) -> Path | None:
    """Bank ``dist_file`` under ``<state_dir>/backup/bootstrap-<version>.py``.

    The §4.3 ordering constraint: an upgrade's planted-doc diff needs the OLD
    dist's templates to still exist when it runs, so *both* ``adopt`` and
    ``upgrade`` archive the running dist before anything could overwrite it —
    the archive exists from v1.0.0 onward. Pre-stamp dists archive as
    ``bootstrap-unknown.py``. Idempotent: an identical existing archive is
    left alone; None when there is no single file to archive (source layout).
    """
    if not dist_file.is_file():
        return None
    text = dist_file.read_text(encoding="utf-8")
    version = dist_version(text) or "unknown"
    dest = root / config.state_dir / BACKUP_DIRNAME / f"bootstrap-{version}.py"
    rel = f"{config.state_dir}/{BACKUP_DIRNAME}/bootstrap-{version}.py"
    if dest.exists() and dest.read_text(encoding="utf-8") == text:
        # Never silent on the idempotent path: an upgrade whose OLD dist was
        # already banked (a prior adopt/check pass, or a re-run) must still
        # account for it explicitly, or the report's only `archived:` line
        # names the NEW version and readers conclude the old dist was never
        # banked — the exact doubt the archive-first covenant exists to remove
        # (field-reported three times, v1.6.0 rollout).
        report.append(f"archived: {rel} (already banked)")
        return dest
    atomic_write_text(dest, text)
    report.append(f"archived: {rel}")
    return dest


_ADOPT_NEXT_STEPS = (
    "next steps: run `bootstrap ask` to see the pending interview questions, "
    "answer them and fill the planted docs in place (`bootstrap render --live`), and set "
    "the integration mode with `bootstrap mode <observe|guided|active>`."
)

# First line doubles as the removal marker `strip_unrendered_banner` keys off.
UNRENDERED_BANNER_FIRST_LINE = (
    "> ⚠️ **UNRENDERED SLOTS BELOW — run `python3 bootstrap.py ask`.**"
)
_UNRENDERED_BANNER = (
    UNRENDERED_BANNER_FIRST_LINE + "\n"
    "> Every `${...}` token in this file is an unfilled interview slot, not\n"
    "> project truth. Fill: `bootstrap answer <slot> <value...>`, then\n"
    "> `bootstrap render --live` (fills in place and removes this banner).\n"
    "> Prose without `${...}` tokens is live guidance already.\n\n"
)


def with_unrendered_banner(text: str) -> str:
    """Prepend the loud UNRENDERED banner when ``text`` has unfilled slots.

    An inert-looking doc was the measured Phase-2.5 failure mode: raw
    ``${...}`` placeholders read as non-actionable scaffolding and only cost
    orientation. The banner names what the tokens are and the exact two
    commands that fill them; a fully-rendered doc gets no banner.
    """
    if not find_placeholders(text):
        return text
    return _UNRENDERED_BANNER + text


def strip_unrendered_banner(text: str) -> str:
    """Remove the adopt-time banner (used once a file has no placeholders)."""
    if not text.startswith(UNRENDERED_BANNER_FIRST_LINE):
        return text
    lines = text.split("\n")
    index = 0
    while index < len(lines) and lines[index].startswith(">"):
        index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    return "\n".join(lines[index:])


def _vendor_bootstrap(root: Path, report: list[str]) -> str:
    """Vendor the running single-file bootstrap into ``root``; return hook path.

    The staged hook commands run ``<interpreter> bootstrap.py hook <event>``
    relative to the host repo root — in the Phase-2.5 A/B the file was never
    there, so every staged hook pointed outside the target repo (the second
    G2 failure cause). When adopt runs *as* the single-file ``bootstrap.py``,
    copy it to the target root (skip-if-exists, like every plant) so those
    commands resolve. Running from the source/pip layout there is no single
    file to vendor: fall back to an existing root copy, else the absolute
    path of the running entry point, else the documented bare-name contract
    (the hooks README fill-table row covers relocation).
    """
    at_root = root / "bootstrap.py"
    entry = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    is_bootstrap_entry = (
        entry is not None and entry.name == "bootstrap.py" and entry.is_file()
    )
    # A target that already contains the *generating* dist/bootstrap.py — the
    # kit repo itself, operating on itself as consumer #0 (§3.3) — must not
    # gain a vendored root duplicate: it would silently drift from the
    # CI-byte-pinned dist file (KL-0 friction guard, 2026-07-09). Hook
    # commands point at the dist copy instead.
    dist_copy = root / "dist" / "bootstrap.py"
    if (
        is_bootstrap_entry
        and not at_root.exists()
        and dist_copy.is_file()
        and entry == dist_copy.resolve()
    ):
        return "dist/bootstrap.py"
    if not at_root.exists() and is_bootstrap_entry and entry != at_root:
        _adopt_plant(
            at_root,
            "bootstrap.py",
            entry.read_text(encoding="utf-8"),
            report,
        )
    if at_root.exists():
        return "bootstrap.py"
    if is_bootstrap_entry:
        return str(entry)
    return "bootstrap.py"


def _adopt_dest(relpath: str, config: Config) -> str:
    """Remap the plan's ``docs/`` prefix onto the host's configured docs root."""
    prefix = "docs/"
    if relpath.startswith(prefix) and config.docs_root != "docs":
        return f"{config.docs_root}/{relpath[len(prefix) :]}"
    return relpath


def _adopt_plant(path: Path, relpath: str, text: str, report: list[str]) -> bool:
    """Write ``text`` at ``path`` unless it exists; report planted/kept.

    Returns True when the file was actually written (so callers can record
    provenance — e.g. the planted-doc hash — only for kit-written content).
    """
    if path.exists():
        report.append(f"kept: {relpath}")
        return False
    atomic_write_text(path, text)
    report.append(f"planted: {relpath}")
    return True


def _adopt_stage(path: Path, relpath: str, text: str, report: list[str]) -> None:
    """Write a staged (generated, regenerable) artifact and report it."""
    atomic_write_text(path, text)
    report.append(f"staged: {relpath}")


def _adopt_sessions_readme(markers: list[dict[str, str]]) -> str:
    """Compose the one-paragraph ``.sessions/README.md`` (born-red convention).

    Each marker renders as ``label (`needle`)`` — the exact byte-form the
    session-log checker scans for, not just its human name. Labels alone were
    the run-1 ON-arm false-red (idea model-line-checker-false-red-2026-07-09):
    a cold session that read this README learned "Model line" but had no way
    to learn the ``📊 Model:`` needle, wrote a reasonable ``> **Model:**``
    line, and stayed red against a card that visibly carried a Model line.
    """
    pairs = ", ".join(
        f"{m['label']} (`{m['needle']}`)" if m.get("needle") else m["label"]
        for m in markers
        if m.get("label")
    )
    pairs = pairs or "(no markers configured)"
    return (
        "# Session logs\n\n"
        "Per-session logs live here as `<date>-<slug>.md`, newest first. "
        "Create the log as the session's FIRST commit with a born-red status "
        "(`> **Status:** `in-progress``) so in-flight work is visible to "
        "parallel sessions, then flip it to `complete` as the deliberate LAST "
        "step once the close-out is written — a half-done session never reads "
        "as finished. Before it counts as complete, a log must carry these "
        "markers, each written with its exact backticked byte-form: "
        f"{pairs}.\n\n"
        "If the card is missing at session end, the kit **auto-drafts** one "
        "from evidence (files touched, git HEAD movement, the verify "
        "command); an in-progress card missing its close-out gets the "
        "drafted section appended. A draft is a starting point, not a "
        "close-out: verify the evidence, resolve every `[[fill:]]` slot, "
        "then flip the Status badge — unresolved slots (and the `drafted` "
        "status) keep the card counting incomplete.\n\n"
        "**Guard recipes:** when a card records friction-to-guard material "
        "for a *later* session (a deferred fix, a flagged footgun), carry a "
        "one-line **guard recipe** naming the code anchors — function + file "
        "+ the test target — not just the symptom. A symptom-only entry "
        "costs the next session a re-derivation grep pass; a recipe lets it "
        "land the guard in minutes.\n"
    )


def ci_snippet() -> str:
    """Return the staged, fully-commented GitHub-Actions-style CI example.

    Everything is commented out: the host copies it into
    ``.github/workflows/`` and uncomments/adjusts deliberately — the kit never
    installs live CI.
    """
    return (
        "# Example GitHub-Actions-style quality gate for a substrate-kit host.\n"
        "# Copy into .github/workflows/, uncomment, and adjust the interpreter\n"
        "# and bootstrap path to match your repo.\n"
        "#\n"
        "# `bootstrap.py check --strict` runs every kit checker in one pass:\n"
        "# docs hygiene (badges / links / reachability), session-log markers,\n"
        "# namespace shadowing, seam authority, orientation budget, the\n"
        "# decision ledger, and the control/ status heartbeat.\n"
        "#\n"
        "# Coordination-only writes (control/** heartbeats) should skip heavy\n"
        "# suites — but if a check is REQUIRED, use an in-job short-circuit\n"
        "# (see the staged substrate-gate.yml's control lane), never\n"
        "# `paths-ignore`: a required context that never reports stays\n"
        "# pending and blocks auto-merge.\n"
        "#\n"
        "# name: substrate-quality\n"
        "# on:\n"
        "#   pull_request:\n"
        "#   push:\n"
        "#     branches: [main]\n"
        "# jobs:\n"
        "#   substrate-check:\n"
        "#     runs-on: ubuntu-latest\n"
        "#     steps:\n"
        "#       - uses: actions/checkout@v4\n"
        "#       - name: substrate checks\n"
        "#         run: python3 bootstrap.py check --strict\n"
    )


LIVE_CI_RELPATH = ".github/workflows/substrate-gate.yml"


def live_ci_workflow(interpreter: str = "python3", sessions_dir: str = ".sessions") -> str:
    """Return the LIVE (uncommented) CI gate workflow — the locked door.

    Unlike :func:`ci_snippet` (a commented example the host installs by hand),
    this is a working GitHub-Actions workflow ``adopt --wire-enforcement``
    writes into ``.github/workflows/``. It runs
    ``bootstrap.py check --strict --require-session-log`` on every pull request,
    so the merge is **held red** until the session's journal is written and the
    whole hygiene suite passes. This is the forcing function that makes the
    memory ritual non-optional: a nag can be ignored, a failing required check
    cannot. `fetch-depth: 0` gives the checkout the history the diff needs.
    A docs-only or bot PR that shouldn't need a session card is handled by the
    host adding a `paths-ignore:` or a label carve-out — kept strict by default
    on purpose (the discipline is the point).

    The gate step is **PR-diff-aware**: a fresh CI checkout flattens every file
    mtime to checkout time, so the engine's newest-by-mtime card guess is
    arbitrary in CI (the kit's own CI once carried a git-mtime-restore shim for
    exactly this). The workflow instead derives the card from what the PR/push
    diff touches under ``sessions_dir`` and passes it via
    ``check --session-log``. When the diff names **no card** the step passes
    an explicitly named, nonexistent sentinel **without**
    ``--require-session-log`` — per the engine contract an explicitly named
    absent card is ADVISORY. (The previous behaviour — omitting the argument —
    was NOT fail-open in CI: the engine's newest-by-mtime fallback latched
    onto the mid-session in-progress card and redded every unrelated PR;
    adopter live-fire, gba-homebrew PR #3, 2026-07-10.) A card **ADDED** by
    the PR (a born-red heartbeat: first-commit-carries-an-in-progress-card
    conventions make in-progress the REQUIRED state at birth) also gates
    advisory via the absent sentinel, because under ``--strict`` the engine
    reds ANY existing-but-incomplete card — the locked door could never pass
    a heartbeat (adopter live-fire: gba-homebrew PR #2 merged red on exactly
    this). A card **MODIFIED** by the PR (every session close-out flips one)
    keeps the full ``--require-session-log`` locked door, so a close-out that
    forgot to flip ``complete`` still reds. Both fixes validated live across
    gba-homebrew PRs #3–#14.

    **Control fast lane (KL-8):** a diff touching only ``control/**`` (a
    status heartbeat, a manager inbox append) short-circuits the job GREEN
    *in-job* — deliberately **not** a ``paths-ignore``, because when this
    check is REQUIRED a workflow that never runs leaves the context pending
    forever and auto-merge jams (the fleet-protocol heartbeat-lane lesson,
    2026-07-09). The required context always reports; coordination writes
    never pay the heavy suite and never need a session card. The lane is
    **not checker-free though**: it still runs the scoped
    ``check --strict --status-only`` heartbeat gate, because a control-only
    diff edits exactly the files ``check_status_current`` validates — the
    original lane skipped the one checker that could catch a broken/deleted
    heartbeat, deferring the red onto the next unrelated PR (the fleet
    adoption review finding, 2026-07-09). Stdlib-only on the system
    ``python3``, so the lane stays fast.
    """
    return (
        "# substrate-kit enforcement gate (LIVE — installed by "
        "`bootstrap.py adopt --wire-enforcement`).\n"
        "# Holds the merge red until the session journal is written and every\n"
        "# hygiene check passes. Add a label carve-out if some PRs legitimately\n"
        "# need no session card — but if this check is REQUIRED, prefer an\n"
        "# in-job short-circuit (like the control lane below) over\n"
        "# `paths-ignore`: a required context that never reports stays\n"
        "# pending and blocks auto-merge forever.\n"
        "name: substrate-gate\n"
        "on:\n"
        "  pull_request:\n"
        "  push:\n"
        "    branches: [main]\n"
        "jobs:\n"
        "  substrate-gate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "        with:\n"
        "          fetch-depth: 0\n"
        "      - name: control fast lane (control/**-only diff short-circuits green)\n"
        "        # Heartbeat/inbox commits are coordination, not code: they\n"
        "        # skip the heavy gate but the job still REPORTS green so a\n"
        "        # required context never jams auto-merge. Empty/unreadable\n"
        "        # diffs fail safe onto the full suite.\n"
        "        id: lane\n"
        "        run: |\n"
        '          if [ -n "${{ github.base_ref }}" ]; then\n'
        '            range="origin/${{ github.base_ref }}...HEAD"\n'
        "          else\n"
        '            range="${{ github.event.before }}..${{ github.sha }}"\n'
        "          fi\n"
        '          files="$(git diff --name-only "$range" 2>/dev/null || true)"\n'
        "          control_only=false\n"
        '          if [ -n "$files" ] && [ -z "$(printf \'%s\\n\' "$files" '
        "| grep -v '^control/')\" ]; then\n"
        "            control_only=true\n"
        "          fi\n"
        '          echo "control_only=$control_only" >> "$GITHUB_OUTPUT"\n'
        '          echo "control-only diff: $control_only"\n'
        "      - name: control-status gate (fast lane — a control diff must "
        "still prove its heartbeat)\n"
        "        if: steps.lane.outputs.control_only == 'true'\n"
        "        # The lane skips the heavy gate, but a control-only PR edits\n"
        "        # exactly the files the status checker validates — without\n"
        "        # this step a heartbeat-deleting control PR merges GREEN and\n"
        "        # pre-reddens the NEXT unrelated PR (kit fleet review\n"
        "        # 2026-07-09). Scoped + stdlib-only on the system python3\n"
        "        # (no setup-python): the lane stays fast, and heartbeat PRs\n"
        "        # still need no session card.\n"
        "        run: python3 bootstrap.py check --strict --status-only\n"
        "      - uses: actions/setup-python@v5\n"
        "        if: steps.lane.outputs.control_only != 'true'\n"
        "        with:\n"
        '          python-version: "3.x"\n'
        "      - name: substrate gate (docs + session-log required)\n"
        "        if: steps.lane.outputs.control_only != 'true'\n"
        "        # Gate on the session card THIS PR/push touches (CI flattens\n"
        "        # mtimes, so the engine's newest-by-mtime guess is unreliable\n"
        "        # here). No card in the diff -> pass an explicitly named,\n"
        "        # nonexistent sentinel WITHOUT --require-session-log: per the\n"
        "        # engine's contract an explicit absent card is ADVISORY,\n"
        "        # while the bare mtime fallback latches onto the mid-session\n"
        "        # in-progress card and reds every unrelated PR (adopter\n"
        "        # live-fire, gba-homebrew PR #3, 2026-07-10 — the omitted\n"
        "        # argument was never fail-open in CI). Second live-fire case:\n"
        "        # a heartbeat PR that ADDS the born-red card (first-commit\n"
        "        # conventions REQUIRE an in-progress card at birth) can never\n"
        "        # satisfy the locked door — gba-homebrew PR #2 merged red on\n"
        "        # exactly this. So: a card ADDED by the PR gates ADVISORY via\n"
        "        # the absent sentinel (under --strict the engine reds ANY\n"
        "        # existing-but-incomplete card, required or not — born-red is\n"
        "        # the REQUIRED state at birth, so a heartbeat must not be\n"
        "        # judged on completeness); a card MODIFIED by the PR (every\n"
        "        # session close-out flips one) keeps the full locked-door\n"
        "        # gate, so a close-out that forgot to flip `complete` still\n"
        "        # reds.\n"
        "        run: |\n"
        '          if [ -n "${{ github.base_ref }}" ]; then\n'
        '            range="origin/${{ github.base_ref }}...HEAD"\n'
        "          else\n"
        '            range="${{ github.event.before }}..${{ github.sha }}"\n'
        "          fi\n"
        '          card="$(git diff --name-only --diff-filter=d "$range" -- '
        f"'{sessions_dir}/*.md' ':!{sessions_dir}/README.md' 2>/dev/null "
        '| tail -1)"\n'
        '          added="$(git diff --name-only --diff-filter=A "$range" -- '
        f"'{sessions_dir}/*.md' ':!{sessions_dir}/README.md' 2>/dev/null "
        '| tail -1)"\n'
        '          echo "session gate card: ${card:-<none - advisory sentinel>}"\n'
        '          if [ -n "$card" ] && [ "$card" != "$added" ]; then\n'
        f"            {interpreter} bootstrap.py check --strict --require-session-log"
        ' --session-log "$card"\n'
        "          elif [ -n \"$card\" ]; then\n"
        '            echo "card $card is newly ADDED by this PR (born-red heartbeat)'
        ' — advisory sentinel gate"\n'
        f"            {interpreter} bootstrap.py check --strict --session-log "
        f"{sessions_dir}/__born-red-card-added__.md\n"
        "          else\n"
        f"            {interpreter} bootstrap.py check --strict --session-log "
        f"{sessions_dir}/__no-card-in-diff__.md\n"
        "          fi\n"
    )


def adopt(
    root: Path,
    config: Config,
    backend: Any,
    *,
    kit_root: Path,
    include_claude: bool = False,
    wire_enforcement: bool = False,
    lane: str | None = None,
) -> list[str]:
    """Adopt the substrate workflow into ``root``; return the report lines.

    Steps (all idempotent): (0) guardrail — refuse the kit's own tree; then
    derive what the tree can tell us (provisional slots) and vendor the
    single-file bootstrap so hook commands resolve in-repo;
    (1) plant every ``ADOPT_PLAN`` doc rendered from the current slots —
    skip-if-exists, unrendered docs bannered; (2) plant
    ``<sessions_dir>/README.md``; (3) plant the ``project.index.json``
    skeleton; (4) stage the ``.claude`` material (CLAUDE.md, skills,
    personas, hook settings + fill-table README) under ``<state_dir>``;
    (5) stage the CI example; (6) with ``include_claude``, additionally
    write ``.claude/CLAUDE.md`` + ``.claude/settings.json`` if absent;
    (7) close with the next-steps line.

    ``wire_enforcement`` turns on the two **forcing functions** that make the
    memory ritual actually get used (the Phase-2.5 re-run showed docs alone get
    read but not written back): it implies ``include_claude`` (the live Stop-hook
    **nag**) **and** plants a live CI workflow (:data:`LIVE_CI_RELPATH`) running
    the ``--require-session-log`` gate — the **locked door** that holds a merge
    red until the journal is written. Kept opt-in: the kit still never installs
    executable CI/hooks silently (the deliberate safety default), but a host —
    or the rebuild's K0 session — flips this on to reproduce the enforcement
    this repo's discipline actually runs on.

    ``lane`` makes the adopt **lane-aware** (the self-review G1 fix for
    double-adoption in SHARED repos): the seeded heartbeat plants as
    ``control/status-<lane>.md`` instead of the singular ``control/status.md``
    and is declared in ``config.heartbeat_files`` (see
    :func:`_register_lane_heartbeat` for the replace-vs-append rules), while
    ``control/inbox.md`` and ``control/README.md`` stay single — the
    manager-owned bus is shared, the heartbeat never is. A second Project
    adopting into an already-adopted repo passes ``--lane`` and joins
    (every shared file skip-if-exists kept, only its own heartbeat added)
    instead of re-planting the first Project's files by hand.
    """
    include_claude = include_claude or wire_enforcement
    assert_safe_target(root, kit_root)
    if lane is not None:
        validate_lane_name(lane)
    templates = load_templates()
    report: list[str] = []

    # (0b) Adopt renders what it knows: seed derivable slots (provisional,
    # never overwriting an existing answer), then build the render context.
    report.extend(record_derived_slots(backend, derive_slots(root, config.docs_root)))
    bootstrap_path = _vendor_bootstrap(root, report)
    # (0c) Bank the running dist under <state_dir>/backup/ (§4.3): a future
    # upgrade's doc diff needs the OLD templates to still exist, so the
    # archive is written before anything could ever overwrite the file.
    dist_file = Path(bootstrap_path)
    if not dist_file.is_absolute():
        dist_file = root / bootstrap_path
    archive_dist(root, config, dist_file, report)
    context = build_context(backend.data)
    # The live integration mode is state, not a slot — render it truthfully.
    context.setdefault("integration_mode", str(backend.get("mode", "guided")))

    # (1) Plant the live docs — never clobber; a doc with unfilled ${slots}
    # is planted under the loud UNRENDERED banner (visible, never inert).
    for template_name, plan_rel in ADOPT_PLAN:
        rel = _adopt_dest(plan_rel, config)
        if lane is not None and template_name == "control-status.md.tmpl":
            # Lane-aware adopt: the heartbeat is the ONE per-Project file on
            # the bus — parametrize its dest; a --lane adopt never creates
            # (nor touches) the singular control/status.md.
            rel = lane_status_relpath(lane)
        text = render(templates[template_name], context)
        if template_name == "decisions.md.tmpl":
            # The example D-0001 records THIS adoption — stamp the real date so
            # the planted ledger is check_ledger-clean from its first commit.
            text = text.replace("- date:\n", f"- date: {date.today().isoformat()}\n")
        final = with_unrendered_banner(text)
        if _adopt_plant(root / rel, rel, final, report):
            # Provenance for the upgrade diff (§4.3): hash what the kit wrote.
            record_doc_hash(backend, rel, final)

    # (2) Session-log scaffolding.
    sessions_rel = f"{config.sessions_dir}/README.md"
    readme = _adopt_sessions_readme(config.session_markers)
    _adopt_plant(root / config.sessions_dir / "README.md", sessions_rel, readme, report)

    # (3) The context-pack index skeleton.
    project_name = context.get("project_name") or root.name
    skeleton = pack_index_skeleton(project_name)
    _adopt_plant(root / "project.index.json", "project.index.json", skeleton, report)

    # (4) Stage the .claude material under <state_dir> (regenerated each run).
    state_base = root / config.state_dir
    claude_doc = with_unrendered_banner(render(templates["CLAUDE.md.tmpl"], context))
    claude_rel = f"{config.state_dir}/claude/CLAUDE.md"
    _adopt_stage(state_base / "claude" / "CLAUDE.md", claude_rel, claude_doc, report)
    for skill in SKILLS:
        rel = skill_relpath(skill)
        body = render(skill["body"], context)
        document = skill_document(skill, body)
        _adopt_stage(state_base / rel, f"{config.state_dir}/{rel}", document, report)
    for agent in AGENTS:
        rel = agent_relpath(agent)
        body = render(agent["body"], context)
        document = agent_document(agent, body)
        _adopt_stage(state_base / rel, f"{config.state_dir}/{rel}", document, report)
    settings_text = full_settings_template(config, bootstrap_path=bootstrap_path)
    settings_rel = f"{config.state_dir}/hooks/settings.template.json"
    settings_path = state_base / "hooks" / "settings.template.json"
    _adopt_stage(settings_path, settings_rel, settings_text, report)
    hooks_readme_rel = f"{config.state_dir}/hooks/README.md"
    hooks_readme = hooks_fill_table()
    _adopt_stage(
        state_base / "hooks" / "README.md",
        hooks_readme_rel,
        hooks_readme,
        report,
    )

    # (5) Stage the CI example — and the LIVE gate workflow (KL-7): a default
    # adopt still never installs CI, but the engagement gate's
    # `enforcement-unwired` checklist line must be a one-copy fix, so the
    # ready-to-install substrate-gate.yml is always staged next to the
    # commented example. Kit stages, host installs — doctrine unchanged.
    ci_rel = f"{config.state_dir}/ci/quality.yml.example"
    _adopt_stage(
        state_base / "ci" / "quality.yml.example",
        ci_rel,
        ci_snippet(),
        report,
    )
    gate_text = live_ci_workflow(
        config.interpreter_for_checks or "python3",
        sessions_dir=config.sessions_dir,
    )
    gate_rel = f"{config.state_dir}/ci/substrate-gate.yml"
    _adopt_stage(
        state_base / "ci" / "substrate-gate.yml",
        gate_rel,
        gate_text,
        report,
    )

    # (6) Explicit host opt-in: live .claude/ (still never overwrites).
    if include_claude:
        claude_dir = root / ".claude"
        if _adopt_plant(
            claude_dir / "CLAUDE.md",
            ".claude/CLAUDE.md",
            claude_doc,
            report,
        ):
            record_doc_hash(backend, ".claude/CLAUDE.md", claude_doc)
        _adopt_plant(
            claude_dir / "settings.json",
            ".claude/settings.json",
            settings_text,
            report,
        )

    # (6b) Enforcement opt-in: the LIVE CI gate (the locked door). include_claude
    # above already wired the live nag; this adds the required check that a
    # missing journal can never merge past.
    if wire_enforcement:
        _adopt_plant(
            root / LIVE_CI_RELPATH,
            LIVE_CI_RELPATH,
            gate_text,
            report,
        )

    # (6b2) Lane-aware adopt: declare the just-planted lane heartbeat so the
    # status gate validates it (config mutated in place — cmd_adopt's
    # engagement checklist reads the same object).
    config_dirty = False
    if lane is not None:
        config_dirty = _register_lane_heartbeat(root, config, lane, report)

    # (6c) The install self-identifies (§4.1): record the kit version in the
    # config file (a declared dataclass field — survives load→save) and state.
    if config.kit_version != KIT_VERSION:
        config.kit_version = KIT_VERSION
        config_dirty = True
    if config_dirty:
        save_config(root, config)
    backend.set("kit_version", KIT_VERSION)
    report.append(f"recorded: kit_version {KIT_VERSION}")

    # (7) Point the adopter at the interview loop.
    report.append(_ADOPT_NEXT_STEPS)
    return report

# --- engine/checks/check_engagement.py ---
"""Post-adopt ENGAGEMENT gate — RED until the install is rendered + enforcing + looping.

Why + provenance: the independent fleet review (2026-07-09, superbot
``docs/eap/fleet-review-2026-07-09.md`` §4) found both fresh adopters stranded
identically — planted docs still under the UNRENDERED banner with raw
``${...}`` slots, ``session_count`` 0, no CI running the check. ``adopt``
plants-and-banners by design, but render/enforcement were separate opt-in
steps nothing forced, so a default adopt LOOKED onboarded while being neither
rendered nor enforcing. This checker is the owner-directed fix (band KL-7):
"enforce, don't exhort" (PL-007) applied to onboarding itself — the same
``check --strict`` an adopter's CI runs holds the gate red until the last
mile is walked. Ships with its regression tests (the cold-adopt RED→GREEN
arc), so it is load-bearing from birth, not a PL-008 unverified convenience.

The gate engages only on **adoption evidence** — a recorded ``kit_version``
in config or state (``adopt``/``upgrade`` write it) — so ``check`` stays
meaningful on an un-adopted tree, exactly like the other input-gated
checkers. One exception: a file that still *carries the UNRENDERED banner*
is kit output by construction and is flagged even without version evidence
(pre-v1.0.0 installs never recorded one).

What turns it red (one finding per condition, each message an actionable
checklist line — ``adopt`` prints these same findings as its next steps):

- ``unrendered-banner`` — a planted doc still opens with the adopt-time
  UNRENDERED banner.
- ``unrendered-slot`` — a planted doc still contains ``${...}`` interview
  slots (adoption-evidence-gated: bare ``${name}`` prose in a never-adopted
  repo is host content, not a kit slot).
- ``enforcement-unwired`` — no workflow under ``.github/workflows/`` runs
  ``check --strict`` (the staged ``substrate-gate.yml`` is the one-copy fix).
- ``session-loop-idle`` — no session has ever run: ``session_count`` is 0
  AND no real session card exists under the sessions dir.

Scope: the scan covers exactly the **planted** doc paths (the ``ADOPT_PLAN``
destinations, ``project.index.json``, and a live ``.claude/CLAUDE.md``) —
never template sources, so the kit repo's own ``src/engine/templates/``
(legitimately full of ``${...}``) can never red its own gate. Findings ride
the ordinary ``check`` finding loop: strict-only exit-code impact, guard-fire
telemetry, and the reasons-required allowlist all apply unchanged.
"""




# Planted paths beyond the ADOPT_PLAN doc set that the unrendered scan covers.
# project.index.json is planted by adopt; .claude/CLAUDE.md exists only after
# the include_claude opt-in (scanned when present — a live-but-unrendered
# working agreement is exactly the "looks onboarded, isn't" failure).
EXTRA_SCAN_RELPATHS = ("project.index.json", ".claude/CLAUDE.md")


def _load_state(target: Path, config: Any) -> dict:
    """Read the install's state.json (empty dict when absent/unreadable)."""
    path = target / config.state_dir / "state.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _adoption_evidence(config: Any, state: dict) -> bool:
    """True when this tree is a known kit install (adopt/upgrade recorded it)."""
    return bool(config.kit_version) or bool(state.get("kit_version"))


def scan_relpaths(config: Any) -> list[str]:
    """Return the planted relpaths the unrendered scan covers.

    Public on purpose: ``render --live`` iterates this SAME list, so the
    render verb and the engagement gate can never disagree about whose job a
    planted file is. The run-2 gap (idea render-live-claude-md-gap-2026-07-09)
    was exactly that disagreement — the gate counted ``.claude/CLAUDE.md``'s
    unrendered banner/slots as strict-RED while the render path skipped the
    file, stranding every fresh adopter mid-checklist.
    """
    relpaths = [_adopt_dest(plan_rel, config) for _, plan_rel in ADOPT_PLAN]
    relpaths.extend(EXTRA_SCAN_RELPATHS)
    return relpaths


def _unrendered_findings(
    target: Path,
    config: Any,
    *,
    evidence: bool,
) -> list[Finding]:
    """Scan the planted docs for the UNRENDERED banner / leftover ``${...}``."""
    findings: list[Finding] = []
    for rel in scan_relpaths(config):
        path = target / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        slots = sorted(find_placeholders(text))
        listed = ", ".join(slots[:5]) + (" …" if len(slots) > 5 else "")
        if text.startswith(UNRENDERED_BANNER_FIRST_LINE):
            detail = f" (unfilled: {listed})" if slots else ""
            findings.append(
                Finding(
                    rel,
                    "unrendered-banner",
                    "still under the adopt-time UNRENDERED banner"
                    f"{detail} — answer the slots (`bootstrap.py answer "
                    "<slot> <value>`), then `bootstrap.py render --live`.",
                ),
            )
        elif evidence and slots:
            findings.append(
                Finding(
                    rel,
                    "unrendered-slot",
                    f"{len(slots)} unfilled ${{...}} slot(s): {listed} — "
                    "answer them, then `bootstrap.py render --live`.",
                ),
            )
    return findings


def _strip_comment(line: str) -> str:
    """Drop a YAML/shell ``#`` comment, keeping the code before it.

    A whole-line comment (leading ``#``) yields ``""``; an inline `` #``
    comment keeps the code up to it. A bare ``#`` with no leading space
    (inside a URL or token) is left alone — kept simple, not a YAML parser.
    """
    if line.lstrip().startswith("#"):
        return ""
    idx = line.find(" #")
    return line[:idx] if idx != -1 else line


def _enforcement_wired(target: Path) -> bool:
    """True when some workflow under .github/workflows/ runs ``check --strict``.

    Substring match on purpose: it accepts the planted ``substrate-gate.yml``
    verbatim AND a host's hand-rolled gate (the kit repo's own ``ci.yml``) —
    the condition is "a CI door exists", not "our exact file was copied".
    Comment content is stripped first, so a workflow that only *mentions* the
    command inside a ``#`` comment is not a real door and stays unwired.
    """
    workflows = target / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    for path in sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any("check --strict" in _strip_comment(line) for line in text.splitlines()):
            return True
    return False


def _session_loop_engaged(target: Path, config: Any, state: dict) -> bool:
    """True when at least one session has run (count or a real card)."""
    try:
        if int(state.get("session_count", 0) or 0) >= 1:
            return True
    except (TypeError, ValueError):
        pass
    sessions = target / config.sessions_dir
    if not sessions.is_dir():
        return False
    return any(p.name != "README.md" for p in sessions.glob("*.md"))


def check_engagement(target: Path, config: Any) -> list[Finding]:
    """Return the engagement-gate findings for ``target`` (empty = ENGAGED)."""
    state = _load_state(target, config)
    evidence = _adoption_evidence(config, state)
    findings = _unrendered_findings(target, config, evidence=evidence)
    if not evidence:
        return findings
    if not _enforcement_wired(target):
        findings.append(
            Finding(
                ".github/workflows/",
                "enforcement-unwired",
                "no CI workflow runs `check --strict` — install the staged "
                f"gate: copy {config.state_dir}/ci/substrate-gate.yml to "
                ".github/workflows/ (or `adopt --wire-enforcement`).",
            ),
        )
    if not _session_loop_engaged(target, config, state):
        findings.append(
            Finding(
                config.sessions_dir,
                "session-loop-idle",
                "no session has ever run (session_count 0, no session card) "
                f"— write the first born-red card under {config.sessions_dir}/ "
                "and run `bootstrap.py session-close` at close.",
            ),
        )
    return findings

# --- engine/upgrade.py ---
"""The ``upgrade`` verb — move an install to this bootstrap's version (§4.3).

The consumer flow (``release.json.upgrade_steps`` says exactly this): download
the new release's ``bootstrap.py`` next to the vendored copy as
``bootstrap.py.new`` and run ``python3 bootstrap.py.new upgrade``. The verb
then, in order:

1. **Verifies itself** against ``release.json`` when one is supplied or sits
   next to the running file (sha256 + version) — refusing on mismatch, noting
   the skip when absent.
2. **Archives first** (the §4.3 ordering constraint): the OLD vendored dist is
   banked to ``<state_dir>/backup/bootstrap-<old-version>.py`` and
   ``state.json`` to ``<state_dir>/backup/state.json`` before anything is
   overwritten — together the ``--rollback`` path.
3. **Classifies every planted doc by hash, never by re-render** (template
   rendering stamps slots/banners/dates, so template@old never byte-matches
   even an untouched file): a doc whose current sha256 equals the recorded
   kit-written hash (``adopt``/``render --live`` record it) is
   *consumer-untouched*. Classes: ``unchanged`` ·
   ``template-improved`` (untouched + new template renders differently — safe
   to apply) · ``consumer-edited`` (template unchanged — consumer-owned,
   nothing to apply) · ``diverged`` (both moved, or no recorded hash — manual;
   the report shows the template@old→new delta rendered through the current
   slot context). Old templates are parsed out of the archived old dist's
   embedded ``_TEMPLATES`` (``ast.literal_eval`` — never executed).
4. **Applies template improvements only under ``--apply-docs`` and only to
   consumer-untouched docs** — consumer-owned stays consumer-owned. Installs
   predating the hash record have no hashes: every doc honestly classifies
   ``diverged``.
5. **Replaces the vendored file with itself**, re-runs adopt's staging
   (staged ``.substrate/`` artifacts always regenerate; missing planted docs
   replant), migrates state (backup already banked), records the new
   ``kit_version``, and writes ``<state_dir>/upgrade-report.md``.
6. **Cleans up its own inputs**: after the replace lands, the consumed
   ``bootstrap.py.new`` and the ``release.json`` next to it are removed
   (``--keep-inputs`` opts out) — the first field run (superbot-next#46)
   left both stranded at the repo root.

``upgrade --rollback`` restores the banked state.json + the archived dist
named by ``<state_dir>/backup/last-upgrade.json`` (staged artifacts regenerate
from the restored file; docs applied via ``--apply-docs`` are git-visible and
are not silently reverted). Pure stdlib; every write is atomic.
"""




LAST_UPGRADE_FILENAME = "last-upgrade.json"
UPGRADE_REPORT_FILENAME = "upgrade-report.md"
STATE_BACKUP_FILENAME = "state.json"

# Classification labels (the §4.3 report classes).
CLASS_UNCHANGED = "unchanged"
CLASS_IMPROVED = "template-improved"
CLASS_CONSUMER_EDITED = "consumer-edited"
CLASS_DIVERGED = "diverged"
CLASS_MISSING = "missing"


class UpgradeRefused(Exception):
    """Raised when the self-verification against release.json fails."""


def load_old_templates(dist_text: str) -> dict[str, str] | None:
    """Parse the ``_TEMPLATES`` dict out of an old dist's text (never exec)."""
    try:
        tree = ast.parse(dist_text)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_TEMPLATES":
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    return None
                if isinstance(value, dict):
                    return {str(k): str(v) for k, v in value.items()}
    return None


def find_vendored_bootstrap(root: Path) -> Path | None:
    """Return the install's vendored single-file bootstrap, if any.

    ``bootstrap.py`` at the repo root is the adopt mechanic's plant;
    ``dist/bootstrap.py`` is consumer #0 (the kit repo operating on itself).
    """
    for rel in ("bootstrap.py", "dist/bootstrap.py"):
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return None


def verify_against_release_json(running: Path, release_json: Path) -> list[str]:
    """Return report lines; raise :class:`UpgradeRefused` on a mismatch."""
    payload = json.loads(release_json.read_text(encoding="utf-8"))
    digest = hashlib.sha256(running.read_bytes()).hexdigest()
    if payload.get("sha256") != digest:
        msg = (
            f"sha256 mismatch vs {release_json.name}: expected "
            f"{payload.get('sha256')}, this file is {digest} — corrupted or "
            "tampered download; re-download the release asset."
        )
        raise UpgradeRefused(msg)
    if payload.get("version") != KIT_VERSION:
        msg = (
            f"{release_json.name} names version {payload.get('version')!r} but "
            f"this bootstrap is v{KIT_VERSION} — mismatched release files."
        )
        raise UpgradeRefused(msg)
    return [f"verified: sha256 + version against {release_json.name}"]


def _upgrade_context(backend: Any) -> dict[str, str]:
    """Build the render context exactly the way adopt does."""
    context = build_context(backend.data)
    context.setdefault("integration_mode", str(backend.get("mode", "guided")))
    return context


def _render_planted(template_text: str, template_name: str, context: dict) -> str:
    """Render a template the way adopt plants it (banner; ledger date stamp)."""
    text = render(template_text, context)
    if template_name == "decisions.md.tmpl":
        text = text.replace("- date:\n", f"- date: {date.today().isoformat()}\n")
    return with_unrendered_banner(text)


def _normalize_dates(text: str) -> str:
    """Blank ledger date stamps so an adopt-day stamp is not template drift."""
    lines = text.split("\n")
    return "\n".join(
        "- date:" if line.startswith("- date: ") else line for line in lines
    )


def _doc_plan(root: Path, config: Config) -> list[tuple[str, str]]:
    """Return (template, planted relpath) pairs the diff report covers."""
    plan = [(tpl, _adopt_dest(rel, config)) for tpl, rel in ADOPT_PLAN]
    if (root / ".claude" / "CLAUDE.md").exists():
        plan.append(("CLAUDE.md.tmpl", ".claude/CLAUDE.md"))
    return plan


def classify_planted_docs(
    root: Path,
    config: Config,
    backend: Any,
    old_templates: dict[str, str] | None,
    new_templates: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Classify every planted doc for the upgrade report (§4.3 step 2).

    Returns rows ``{relpath, template, class, note, diff}`` (``diff`` only for
    diverged docs with old templates available — the template@old→new delta,
    both rendered through the *current* slot context for a readable diff).
    """
    context = _upgrade_context(backend)
    templates = new_templates if new_templates is not None else load_templates()
    rows: list[dict[str, str]] = []
    for template_name, rel in _doc_plan(root, config):
        path = root / rel
        row = {"relpath": rel, "template": template_name, "diff": ""}
        if not path.exists():
            row["class"] = CLASS_MISSING
            row["note"] = "absent — upgrade's adopt pass replants it"
            rows.append(row)
            continue
        current = path.read_text(encoding="utf-8")
        new_render = _render_planted(templates[template_name], template_name, context)
        old_render = None
        if old_templates and template_name in old_templates:
            old_render = _render_planted(
                old_templates[template_name],
                template_name,
                context,
            )
        untouched = doc_is_untouched(backend, rel, current)
        if not untouched and _normalize_dates(new_render) == _normalize_dates(
            current,
        ):
            # Self-heal a lost hash record (companion idea
            # upgrade-rollback-loses-doc-hash-records): `upgrade --rollback`
            # restores the pre-upgrade state.json, discarding every
            # planted_doc_hashes entry the upgrade's adopt pass recorded — so
            # on a re-run a doc the kit itself wrote carries no hash and would
            # classify diverged, taking it out of --apply-docs' reach. A
            # byte-match against the NEW template render (date-normalized)
            # *proves* the doc is untouched kit-form; recording the hash
            # recovers a lost record from ground truth, not a provenance lie. A
            # doc a consumer actually edited never byte-matches and stays
            # honestly diverged; and a byte-match to the new render only ever
            # yields `unchanged`, so nothing is auto-applied that would not be.
            record_doc_hash(backend, rel, current)
            untouched = True
        if untouched:
            if _normalize_dates(new_render) == _normalize_dates(current):
                row["class"] = CLASS_UNCHANGED
                row["note"] = "template identical across versions"
            else:
                row["class"] = CLASS_IMPROVED
                row["note"] = (
                    "consumer-untouched + template improved — "
                    "safe to apply with `upgrade --apply-docs`"
                )
        elif old_render is not None and _normalize_dates(
            old_render,
        ) == _normalize_dates(new_render):
            row["class"] = CLASS_CONSUMER_EDITED
            row["note"] = "template unchanged — consumer-owned, nothing to apply"
        else:
            row["class"] = CLASS_DIVERGED
            if old_render is None:
                row["note"] = (
                    "no recorded hash or old templates unavailable "
                    "(pre-1.0 install) — manual review"
                )
            else:
                row["note"] = "both the template and the doc moved — manual merge"
                row["diff"] = "\n".join(
                    difflib.unified_diff(
                        old_render.splitlines(),
                        new_render.splitlines(),
                        fromfile=f"{rel} (template@old, current slots)",
                        tofile=f"{rel} (template@new, current slots)",
                        lineterm="",
                    ),
                )
        rows.append(row)
    return rows


def apply_doc_improvements(
    root: Path,
    config: Config,
    backend: Any,
    rows: list[dict[str, str]],
    new_templates: dict[str, str] | None = None,
) -> list[str]:
    """Re-render + write every ``template-improved`` doc; re-record hashes.

    Only the consumer-untouched class is ever written (the §4.3 covenant:
    planted docs are never auto-edited without ``--apply-docs``, and never
    when the consumer diverged).
    """
    context = _upgrade_context(backend)
    templates = new_templates if new_templates is not None else load_templates()
    lines: list[str] = []
    for row in rows:
        if row["class"] != CLASS_IMPROVED:
            continue
        rel = row["relpath"]
        text = _render_planted(templates[row["template"]], row["template"], context)
        atomic_write_text(root / rel, text)
        record_doc_hash(backend, rel, text)
        lines.append(f"applied: {rel} (template@new, hash re-recorded)")
    return lines


def upgrade_report_text(
    old_version: str,
    rows: list[dict[str, str]],
    applied: list[str],
) -> str:
    """Compose ``<state_dir>/upgrade-report.md``."""
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    summary = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    lines = [
        f"# substrate-kit upgrade report — v{old_version} → v{KIT_VERSION}",
        "",
        f"> Generated {date.today().isoformat()} by `bootstrap.py upgrade`. "
        f"Rollback: `python3 bootstrap.py upgrade --rollback`.",
        "",
        f"**Docs:** {summary}",
        "",
        "| planted doc | class | note |",
        "|---|---|---|",
    ]
    lines += [f"| {r['relpath']} | {r['class']} | {r['note']} |" for r in rows]
    if applied:
        lines += ["", "## Applied (--apply-docs)", ""]
        lines += [f"- {line}" for line in applied]
    diffs = [r for r in rows if r["diff"]]
    if diffs:
        lines += ["", "## Template deltas for diverged docs", ""]
        for row in diffs:
            lines += [f"### {row['relpath']}", "", "```diff", row["diff"], "```", ""]
    return "\n".join(lines) + "\n"


def newest_banked_archive(
    root: Path,
    config: Config,
) -> tuple[Path | None, str | None]:
    """Return ``(path, from_version)`` of the newest banked pre-upgrade dist.

    The archive-first covenant banks the OLD dist under
    ``<state_dir>/backup/bootstrap-<old-version>.py`` and records the exact one
    the last upgrade banked in ``last-upgrade.json`` (``archived_dist`` +
    ``from_version``). That marker names the newest banked pre-upgrade dist —
    the templates the single-shot apply window closed over. Returns
    ``(None, None)`` when no upgrade has banked one (nothing to apply post-hoc
    from).
    """
    marker = root / config.state_dir / BACKUP_DIRNAME / LAST_UPGRADE_FILENAME
    if not marker.is_file():
        return None, None
    try:
        meta = json.loads(marker.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None, None
    archived_rel = meta.get("archived_dist")
    if not archived_rel:
        return None, None
    archived = root / archived_rel
    if not archived.is_file():
        return None, None
    return archived, meta.get("from_version")


def run_apply_docs_posthoc(
    root: Path,
    config: Config,
    backend: Any,
) -> list[str]:
    """Apply template improvements *after* the single-shot window has closed.

    (Idea ``upgrade-apply-docs-single-shot-window``.) Once an upgrade replaced
    the vendored dist, a bare re-run parses new==new templates and can never
    yield a ``template-improved`` row again — the apply window was single-shot.
    But the pre-upgrade dist was banked (archive-first), so its templates
    survive on disk. Load them as ``old_templates`` and run the SAME
    classify/apply the in-run path uses, so an operator who skipped
    ``--apply-docs`` recovers the improvements WITHOUT a rollback. The covenant
    is unchanged: only consumer-untouched kit-form docs are ever written
    (consumer-edited docs stay diverged), hashes are re-recorded, and a re-run
    is idempotent (everything already current). No archive banked yet → a clean,
    actionable message and nothing written (never a crash, never an impossible
    command).
    """
    report: list[str] = []
    archived, from_version = newest_banked_archive(root, config)
    if archived is None:
        report.append(
            "apply-docs: no banked pre-upgrade dist to apply from — post-hoc "
            "--apply-docs needs the archive the last upgrade banked "
            f"({config.state_dir}/{BACKUP_DIRNAME}/bootstrap-<old>.py, named by "
            f"{LAST_UPGRADE_FILENAME}). Nothing applied.",
        )
        return report
    old_templates = load_old_templates(archived.read_text(encoding="utf-8"))
    rows = classify_planted_docs(root, config, backend, old_templates)
    applied = apply_doc_improvements(root, config, backend, rows)
    report += applied
    if not applied:
        report.append(
            "apply-docs: no template-improved docs to apply — every planted "
            "doc is already current or consumer-owned.",
        )
    report_rel = f"{config.state_dir}/{UPGRADE_REPORT_FILENAME}"
    atomic_write_text(
        root / report_rel,
        upgrade_report_text(
            from_version or config.kit_version or "unknown",
            rows,
            applied,
        ),
    )
    report.append(f"report: {report_rel}")
    return report


def run_upgrade(
    root: Path,
    config: Config,
    backend: Any,
    *,
    kit_root: Path,
    running: Path,
    apply_docs: bool = False,
    release_json: Path | None = None,
    cleanup_inputs: bool = True,
) -> list[str]:
    """Execute the §4.3 upgrade flow; return the report lines.

    Raises :class:`UpgradeRefused` when release.json verification fails.
    """
    # Post-hoc --apply-docs (idea upgrade-apply-docs-single-shot-window): when
    # the vendored dist is ALREADY at the running version there is no pending
    # transition, but a prior upgrade that skipped --apply-docs banked the
    # pre-upgrade dist (archive-first covenant). Loading old_templates from that
    # newest banked archive and running the SAME classify/apply the in-run path
    # uses recovers the single-shot window without a rollback. Guarded by
    # apply_docs so a bare same-version re-run keeps its existing no-op shape,
    # and the in-run path (vendored OLDER than KIT_VERSION) is UNCHANGED.
    posthoc_vendored = find_vendored_bootstrap(root)
    if apply_docs and posthoc_vendored is not None:
        vendored_text = posthoc_vendored.read_text(encoding="utf-8")
        if dist_version(vendored_text) == KIT_VERSION:
            return run_apply_docs_posthoc(root, config, backend)

    report: list[str] = []

    # (1) Self-verification (sha256 + version) when release.json is findable.
    candidate = release_json or running.parent / "release.json"
    if candidate.is_file():
        report += verify_against_release_json(running, candidate)
    else:
        report.append(
            "note: no release.json found — sha256 verification skipped "
            "(download it next to the new bootstrap to enable it).",
        )

    # (2) Archive FIRST (§4.3): old dist + state.json, before any overwrite.
    vendored = find_vendored_bootstrap(root)
    old_text = vendored.read_text(encoding="utf-8") if vendored else None
    # From-version: the vendored header states what is actually installed and
    # OUTRANKS the config pin when they disagree — a consumer may record its
    # pin BEFORE the first real upgrade (the D2 order), leaving the pin
    # aspirational while the file on disk is older or unstamped. The field
    # case (superbot-next#46): pin said 1.0.0, the archive honestly said
    # bootstrap-unknown.py, and a rollback would have restored the wrong pin.
    # The one header that cannot name the true "from" is KIT_VERSION itself —
    # the hand-copied-new-dist-over-old case — where the recorded pin wins
    # (distinguishable exactly because the header equals KIT_VERSION).
    header_version = dist_version(old_text) if old_text else None
    if old_text is not None and header_version != KIT_VERSION:
        old_version = header_version or "unknown"
    else:
        old_version = config.kit_version or header_version or "unknown"
    backup_dir = root / config.state_dir / BACKUP_DIRNAME
    archived = None
    if vendored is not None:
        archived = archive_dist(root, config, vendored, report)
    state_path = root / config.state_dir / "state.json"
    if state_path.exists():
        atomic_write_text(
            backup_dir / STATE_BACKUP_FILENAME,
            state_path.read_text(encoding="utf-8"),
        )
        report.append(
            f"backed up: state.json -> "
            f"{config.state_dir}/{BACKUP_DIRNAME}/{STATE_BACKUP_FILENAME}",
        )
    atomic_write_text(
        backup_dir / LAST_UPGRADE_FILENAME,
        json.dumps(
            {
                "from_version": old_version,
                "to_version": KIT_VERSION,
                "date": date.today().isoformat(),
                "vendored": (
                    str(vendored.relative_to(root)) if vendored is not None else None
                ),
                "archived_dist": (
                    str(archived.relative_to(root)) if archived is not None else None
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    # (3) Hash-based planted-doc diff report (§4.3 step 2), computed BEFORE
    # the adopt pass replants anything.
    old_templates = load_old_templates(old_text) if old_text else None
    rows = classify_planted_docs(root, config, backend, old_templates)

    # (4) --apply-docs: template improvements land on untouched docs only.
    applied = apply_doc_improvements(root, config, backend, rows) if apply_docs else []
    for line in applied:
        report.append(line)
    improved = [r for r in rows if r["class"] == CLASS_IMPROVED]
    if improved and not apply_docs:
        # A bare re-run parses the already-new vendored templates and can never
        # yield a template-improved row again (idea
        # upgrade-apply-docs-single-shot-window) — but the pre-upgrade dist was
        # banked (archive-first), so a same-version `upgrade --apply-docs` now
        # applies these POST-HOC from that archive. Name that working recovery
        # (no rollback needed), never a bare "re-run to take them" no-op.
        report.append(
            f"note: {len(improved)} doc(s) have template improvements you "
            "never edited — take them now by re-running with --apply-docs, or "
            "any time later with `upgrade --apply-docs`: it applies them "
            "post-hoc from the banked pre-upgrade archive (no rollback needed).",
        )

    # (5) Replace the vendored file with the running (new) one — only when the
    # running entry actually IS a stamped single-file bootstrap (in the
    # source/pip layouts there is no single file to install).
    running_is_dist = (
        running.is_file()
        and dist_version(running.read_text(encoding="utf-8")) is not None
    )
    replaced = False
    if vendored is not None and running_is_dist and running.resolve() != vendored.resolve():
        atomic_write_text(vendored, running.read_text(encoding="utf-8"))
        replaced = True
        report.append(
            f"replaced: {vendored.relative_to(root)} "
            f"(v{old_version} -> v{KIT_VERSION}; old copy archived)",
        )

    # (6) Staged regeneration: adopt is idempotent — staged artifacts always
    # regenerate, planted docs skip-if-exist, kit_version records new.
    report += adopt(root, config, backend, kit_root=kit_root)

    # (6b) KL-3: the 📊 Model needle joins session_markers at upgrade time —
    # a consumer's gate only tightens when it upgrades, never mid-version
    # (founding plan §5.2); the report says so out loud.
    if not any(
        m.get("needle") == MODEL_LINE_NEEDLE for m in config.session_markers
    ):
        config.session_markers.append(
            {"label": "Model line", "needle": MODEL_LINE_NEEDLE},
        )
        save_config(root, config)
        report.append(
            "session_markers: added the \N{BAR CHART} Model line needle "
            "(KL-3 telemetry) — session logs must now carry "
            "`- **\N{BAR CHART} Model:** <model> \N{MIDDLE DOT} <effort> "
            "\N{MIDDLE DOT} <task-class>`; session-close harvests it into "
            "telemetry/model-usage.jsonl.",
        )

    # (7) State migration (backup already banked above).
    backend.migrate(STATE_SCHEMA_VERSION)
    report.append(f"state: schema at v{STATE_SCHEMA_VERSION} (backup banked).")

    # (8) The report file (§9.2 names it as the upgrade PR's body evidence).
    report_rel = f"{config.state_dir}/{UPGRADE_REPORT_FILENAME}"
    atomic_write_text(
        root / report_rel,
        upgrade_report_text(old_version, rows, applied),
    )
    report.append(f"report: {report_rel}")

    # (9) Self-cleanup of the upgrade inputs: the consumer flow downloads
    # ``bootstrap.py.new`` (+ its ``release.json``) next to the vendored file,
    # and once the replace has landed both are strays the first field run
    # (superbot-next#46) left behind. Only the files the flow itself consumed
    # are touched — the running .new file that was just installed and the
    # release.json sitting NEXT TO it (an explicit --release-json elsewhere is
    # left alone). ``--keep-inputs`` opts out; a cleanup error never fails a
    # completed upgrade (fail-open, like every non-essential step).
    if cleanup_inputs and replaced:
        for leftover in (running, candidate):
            if leftover.parent != running.parent or not leftover.is_file():
                continue
            try:
                leftover.unlink()
                report.append(
                    f"cleaned up: {leftover.name} "
                    "(upgrade input; pass --keep-inputs to retain)",
                )
            except OSError:
                report.append(
                    f"note: could not remove {leftover.name} — "
                    "delete it by hand.",
                )
    return report


def run_rollback(root: Path, config: Config) -> list[str]:
    """Restore the banked state.json + archived dist from the last upgrade."""
    backup_dir = root / config.state_dir / BACKUP_DIRNAME
    marker = backup_dir / LAST_UPGRADE_FILENAME
    if not marker.is_file():
        return [f"rollback: nothing to roll back (no {LAST_UPGRADE_FILENAME})."]
    meta = json.loads(marker.read_text(encoding="utf-8"))
    report: list[str] = []
    state_backup = backup_dir / STATE_BACKUP_FILENAME
    if state_backup.is_file():
        atomic_write_text(
            root / config.state_dir / "state.json",
            state_backup.read_text(encoding="utf-8"),
        )
        report.append("restored: state.json from backup.")
    archived_rel = meta.get("archived_dist")
    vendored_rel = meta.get("vendored")
    if archived_rel and vendored_rel:
        archived = root / archived_rel
        if archived.is_file():
            atomic_write_text(
                root / vendored_rel,
                archived.read_text(encoding="utf-8"),
            )
            report.append(
                f"restored: {vendored_rel} from {archived_rel} "
                f"(back to v{meta.get('from_version')}).",
            )
    recorded = str(meta.get("from_version") or "")
    # "unknown" names an unstamped pre-release dist (the archive is
    # bootstrap-unknown.py) — the honest config value for that state is the
    # unrecorded sentinel "", never the literal string "unknown".
    restored_pin = "" if recorded == "unknown" else recorded
    if config.kit_version and config.kit_version != restored_pin:
        config.kit_version = restored_pin
        save_config(root, config)
        report.append(f"restored: config kit_version -> {config.kit_version!r}.")
    report.append(
        "note: staged .substrate/ artifacts regenerate from the restored file "
        "(run: python3 bootstrap.py adopt); docs applied via --apply-docs are "
        "git-visible and were not reverted.",
    )
    return report

# --- engine/cli.py ---
"""The substrate-kit bootstrap command line.

Surface: ``init`` (idempotent), ``status``, ``mode <name>``, ``stance [name]``
(show or set the task stance), ``ask`` (list the pending interview questions),
``answer`` / ``confirm`` (fill / confirm a slot), ``render`` (write content
docs), ``skills`` / ``agents`` / ``hooks`` (list / ``--build`` the packs),
``hook <event>`` (the runtime hook entry points), ``check`` (every hygiene
checker), ``triggers``, ``reflect``, ``episodes``, ``metrics``, ``maintain``,
``review`` (the independent-review seam), ``economy`` (the context-economy
engine), ``ledger`` (the [D-NNNN] decisions ledger), ``friction`` (export/list/show
the §9.1 friction-report outbox), ``draft`` (auto-draft the session card's
close-out from evidence — KL-5), and ``--simulate N
[--mode m]`` (the CI / proving smoke that drives the staged interview and
asserts per-mode behavior). Output goes through ``_emit`` (``sys.stdout.write``)
rather than ``print`` to keep the engine lint-clean.
"""





def _emit(line: str = "") -> None:
    """Write a line to stdout (avoids the print() lint ban in engine code)."""
    sys.stdout.write(line + "\n")


def _kit_root() -> Path:
    """Return the tree the guardrail protects (the kit's own checkout).

    Only the source layout (``.../src/engine/cli.py``) has a kit tree to
    protect: there, the checkout root is ``parents[2]``. Running as the
    copied single-file bootstrap or a pip install, this returns the module
    file itself — a *file* matches no target directory, so the guardrail
    never engages (there is no kit tree). The old unconditional
    ``parents[2]`` made the dist's guardrail root the grandparent of the
    user's repo, refusing EVERY real ``adopt``/``init`` outside the temp
    tree — the documented primary flow.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "engine" and here.parent.parent.name == "src":
        return here.parents[2]
    return here


def _state_path(root: Path, config: Config) -> Path:
    """Return the state-file path under a project ``root``."""
    return root / config.state_dir / "state.json"


def cmd_init(target: Path) -> int:
    """Create config + state under ``target`` if absent; never clobber."""
    assert_safe_target(target, _kit_root())
    target.mkdir(parents=True, exist_ok=True)
    if config_path(target).exists():
        config = load_config(target)
    else:
        config = Config()
        save_config(target, config)
    state_path = _state_path(target, config)
    if state_path.exists():
        _emit(f"init: already initialised at {target} (idempotent no-op).")
        return 0
    backend = JsonStateBackend(state_path)
    with backend.transaction():
        for key, value in default_state(config.project_id).items():
            backend.set(key, value)
    _emit(f"init: created {state_path} (project_id={config.project_id}).")
    return 0


def cmd_status(target: Path) -> int:
    """Print a one-screen summary of the install's state."""
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    data = backend.data
    if not data:
        _emit(f"status: no state at {target} (run init first).")
        return 1
    _emit(f"project_id : {data.get('project_id')}")
    _emit(f"stage      : {data.get('stage')}")
    _emit(f"mode       : {data.get('mode')}")
    _emit(f"stance     : {data.get('stance')}")
    _emit(f"sessions   : {data.get('session_count')}")
    return 0


def cmd_mode(target: Path, name: str) -> int:
    """Set the integration mode (observe | guided | active)."""
    valid = ("observe", "guided", "active")
    if name not in valid:
        _emit(f"mode: invalid mode {name!r} (choose from {list(valid)}).")
        return 2
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    if not backend.data:
        _emit(f"mode: no state at {target} (run init first).")
        return 1
    history = list(backend.get("mode_history", []))
    history.append(
        {
            "mode": name,
            "session": int(backend.get("session_count", 0)),
            "date": date.today().isoformat(),
        },
    )
    with backend.transaction():
        backend.set("mode", name)
        backend.set("mode_history", history)
    _emit(f"mode: set to {name} (audit trail: {len(history)} switch(es)).")
    return 0


def cmd_stance(target: Path, name: str | None) -> int:
    """Show or set the active task stance (question|analysis|debug|review|plan).

    With no ``name``, prints the active stance's briefing (reading-route +
    tool-scope + output contract) and the available set. With a ``name``, switches
    the active stance in state. The stance is advisory — it scopes orientation, it
    does not block actions.
    """
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    if not backend.data:
        _emit(f"stance: no state at {target} (run init first).")
        return 1
    if name is None:
        active = backend.data.get("stance", DEFAULT_STANCE)
        _emit(stance_briefing(active))
        _emit(f"  available: {', '.join(stance_names())}")
        return 0
    if name not in stance_names():
        _emit(f"stance: invalid stance {name!r} (choose from {stance_names()}).")
        return 2
    backend.set("stance", name)
    _emit(f"stance: set to {name}.")
    _emit(stance_briefing(name))
    return 0


def cmd_ask(target: Path) -> int:
    """List the interview's currently pending questions."""
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    if not backend.data:
        _emit(f"ask: no state at {target} (run init first).")
        return 1
    pending = pending_questions(backend.data)
    if not pending:
        _emit("ask: no pending questions — all slots filled.")
        return 0
    asked = session_questions(backend.data)
    _emit(f"ask: {len(asked)} question(s) this session (mode quota):")
    for question in asked:
        _emit(
            f"  [{question['id']}] "
            f"({question['audience']}/{question['priority']}) {question['prompt']}",
        )
    remaining = len(pending) - len(asked)
    if remaining > 0:
        _emit(f"  (+{remaining} more later — the mode paces the interview)")
    return 0


def _render_live(target: Path, context: dict[str, str], backend: Any) -> int:
    """Fill remaining ``${slot}`` placeholders in the PLANTED docs, in place.

    Placeholders survive verbatim in a planted file until their slot fills, so
    substituting over the live text updates exactly the newly-answered slots
    while preserving every hand edit around them. Returns the leftover count.
    Every rewrite re-records the doc's sha256 (the §4.3 "kit last wrote this"
    provenance the upgrade diff keys on).

    The render set is :func:`engine.checks.check_engagement.scan_relpaths` —
    the SAME list the engagement gate scans — so the two surfaces can never
    disagree about whose job a planted file is. They used to: ``render
    --live`` iterated only the ``ADOPT_PLAN`` docs while the gate also
    counted ``.claude/CLAUDE.md``, so an ``--include-claude`` adopter's
    checklist could not reach GREEN by its own named commands (run-2 finding,
    idea render-live-claude-md-gap-2026-07-09).
    """
    leftover_total = 0
    for rel in scan_relpaths(load_config(target)):
        path = target / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        filled = render(text, context)
        leftover = find_placeholders(filled)
        leftover_total += len(leftover)
        if not leftover:
            # Fully rendered — the adopt-time UNRENDERED banner has done its job.
            filled = strip_unrendered_banner(filled)
        if filled != text:
            atomic_write_text(path, filled)
            record_doc_hash(backend, rel, filled)
            suffix = f" ({len(leftover)} slot(s) still unfilled)" if leftover else ""
            _emit(f"render: filled {rel}{suffix}")
    _emit(f"render: {leftover_total} unfilled placeholder(s) across planted docs.")
    return 0


def cmd_render(target: Path, live: bool = False) -> int:
    """Render the content docs from the current filled slots.

    Default: stage fresh renders of every template into
    ``<state_dir>/rendered/``. With ``live``: fill remaining placeholders in
    the *planted* docs in place (hand edits preserved) — the post-interview
    "make the live docs catch up" pass.
    """
    assert_safe_target(target, _kit_root())
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    if not backend.data:
        _emit(f"render: no state at {target} (run init first).")
        return 1
    context = build_context(backend.data)
    if live:
        return _render_live(target, context, backend)
    out_dir = target / config.state_dir / "rendered"
    leftover_total = 0
    for name, text in load_templates().items():
        rendered = render(text, context)
        leftover = find_placeholders(rendered)
        leftover_total += len(leftover)
        out_name = name[:-5] if name.endswith(".tmpl") else name
        atomic_write_text(out_dir / out_name, rendered)
        suffix = f" ({len(leftover)} slot(s) unfilled)" if leftover else ""
        _emit(f"render: wrote {out_name}{suffix}")
    _emit(f"render: {leftover_total} unfilled placeholder(s) total.")
    return 0


def cmd_skills(target: Path, build: bool) -> int:
    """List the skill pack, or ``--build`` it into ``<state_dir>/skills/``.

    Listing shows each skill + its declared capabilities (what it may do beyond
    read, overriding the ambient stance). Building emits a native ``SKILL.md`` per
    skill into the staging area, body slot-filled from the interview — the host
    then installs them under ``.claude/skills/``. Like ``render``, the kit stages;
    it never writes a live ``.claude/`` tree.
    """
    config = load_config(target)
    if build:
        assert_safe_target(target, _kit_root())
    if not build:
        _emit("skills:")
        for skill in SKILLS:
            caps = ", ".join(skill_capabilities(skill["name"]))
            _emit(f"  {skill['name']} — {skill['description']}")
            _emit(f"    capabilities: {caps}")
        return 0
    backend = JsonStateBackend(_state_path(target, config))
    context = build_context(backend.data) if backend.data else {}
    out_base = target / config.state_dir
    leftover_total = 0
    for skill in SKILLS:
        body = render(skill["body"], context)
        leftover = find_placeholders(body)
        leftover_total += len(leftover)
        atomic_write_text(out_base / skill_relpath(skill), skill_document(skill, body))
        suffix = f" ({len(leftover)} slot(s) unfilled)" if leftover else ""
        _emit(f"skills: wrote {skill_relpath(skill)}{suffix}")
    _emit(f"skills: {len(SKILLS)} skill(s), {leftover_total} unfilled placeholder(s).")
    return 0


def cmd_agents(target: Path, build: bool) -> int:
    """List the persona pack, or ``--build`` it into ``<state_dir>/agents/``.

    Listing shows each persona + its description. Building emits a native
    ``.claude/agents``-style ``<name>.md`` per persona into the staging area, body
    slot-filled from the project's contract slots — the host then installs them
    under ``.claude/agents/``. Like ``render``/``skills``, the kit stages; it never
    writes a live ``.claude/`` tree.
    """
    config = load_config(target)
    if build:
        assert_safe_target(target, _kit_root())
    if not build:
        _emit("agents:")
        for agent in AGENTS:
            _emit(f"  {agent['name']} — {agent['description']}")
        return 0
    backend = JsonStateBackend(_state_path(target, config))
    context = build_context(backend.data) if backend.data else {}
    out_base = target / config.state_dir
    leftover_total = 0
    for agent in AGENTS:
        body = render(agent["body"], context)
        leftover = find_placeholders(body)
        leftover_total += len(leftover)
        atomic_write_text(out_base / agent_relpath(agent), agent_document(agent, body))
        suffix = f" ({len(leftover)} slot(s) unfilled)" if leftover else ""
        _emit(f"agents: wrote {agent_relpath(agent)}{suffix}")
    count = len(AGENTS)
    _emit(f"agents: {count} persona(s), {leftover_total} unfilled placeholder(s).")
    return 0


def _hook_command(config: Config) -> str:
    """Return the shell command Claude Code runs for the PreToolUse guard."""
    return f"{config.interpreter} bootstrap.py hook pretooluse"


def cmd_hooks(target: Path, build: bool) -> int:
    """Show the hook wiring, or ``--build`` the settings files into staging.

    Four hooks: the **PreToolUse stance guard**, **SessionStart orientation**,
    the **PostToolUse edit advisor**, and the **Stop-check advisor**. Building
    stages the PreToolUse snippet, the full four-event
    ``settings.template.json``, and the fill-table README into
    ``<state_dir>/hooks/`` — the host merges them into their own settings
    (adjusting the bootstrap path). Like the other emitters, the kit stages;
    it never writes a live ``.claude/`` tree.
    """
    config = load_config(target)
    if build:
        assert_safe_target(target, _kit_root())
    command = _hook_command(config)
    if not build:
        _emit("hooks:")
        _emit("  pretooluse   — stance guard: warns on an out-of-stance tool.")
        _emit("  sessionstart — prints the mode-aware orientation injection.")
        _emit("  postedit     — warns on generated-artifact / unbadged-doc edits.")
        _emit("  stopcheck    — session-close advisories (log, questions, cadence).")
        _emit(f"  wiring command: {command}")
        return 0
    out = target / config.state_dir / "hooks" / "settings.snippet.json"
    atomic_write_text(out, settings_snippet(command))
    tmpl = target / config.state_dir / "hooks" / "settings.template.json"
    atomic_write_text(tmpl, full_settings_template(config))
    atomic_write_text(
        target / config.state_dir / "hooks" / "README.md",
        hooks_fill_table(),
    )
    _emit(f"hooks: wrote {out.relative_to(target)}")
    _emit(f"hooks: wrote {tmpl.relative_to(target)} (all four events) + README.md")
    _emit("hooks: merge the hook blocks into .claude/settings.json yourself.")
    return 0


def _hook_pretooluse(target: Path) -> list[str]:
    """PreToolUse stance guard: warn on stderr for an out-of-stance tool."""
    tool_name = tool_from_payload(sys.stdin.read())
    if not tool_name:
        return []
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    stance = backend.data.get("stance") if backend.data else None
    if not stance:
        return []
    warning = evaluate_tool(stance, tool_name)
    if warning:
        sys.stderr.write(warning + "\n")
        return [warning]
    return []


def _hook_sessionstart(target: Path) -> list[str]:
    """SessionStart: print the orientation composition + record the anchor.

    The anchor (timestamp + git HEAD/branch, ``state["session_anchor"]``) is
    the evidence baseline the KL-5 auto-draft diffs against at session close.
    Recording is fail-open inside ``record_session_anchor`` — orientation
    must never be blocked by evidence bookkeeping.
    """
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    text = compose_orientation(target, config, backend)
    if text:
        sys.stdout.write(text)
    record_session_anchor(target, config, backend)
    return []


def _hook_postedit(target: Path) -> list[str]:
    """PostToolUse: warn on stderr for a generated-artifact / unbadged-doc edit.

    Handles Edit/Write (``tool_input.file_path``) and NotebookEdit
    (``tool_input.notebook_path``) — the three tools the settings matcher wires.
    A NotebookEdit carries ``notebook_path``, not ``file_path``, so keying only
    on the latter matched notebook edits but never advised them (the matcher
    over-advertised its coverage).
    """
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return []
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    if not isinstance(tool_input, dict):
        return []
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(file_path, str) or not file_path:
        return []
    warning = evaluate_edit(target, load_config(target), file_path)
    if warning:
        sys.stderr.write(warning + "\n")
        return [warning]
    return []


def _hook_stopcheck(target: Path) -> list[str]:
    """Stop: auto-draft the session card, then print the advisories to stderr.

    Drafting runs FIRST (KL-5 — the mechanized write-back the Phase-2.5 A/B
    proved doesn't happen by discipline): a missing card gets a drafted
    skeleton, an in-progress card missing its close-out gets the drafted
    section appended, and the advisories that follow see the drafted state.
    Both halves fail open; the hook always exits 0.
    """
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    lines = ensure_draft(target, config, backend)
    lines += evaluate_stop(target, config, backend)
    for line in lines:
        sys.stderr.write(line + "\n")
    return lines


_HOOK_EVENTS = {
    "pretooluse": _hook_pretooluse,
    "sessionstart": _hook_sessionstart,
    "postedit": _hook_postedit,
    "stopcheck": _hook_stopcheck,
}

# Guard kind per hook event, for the §5.3 guard-fire feed. ``sessionstart``
# is orientation, not a guard — it never records a fire.
_HOOK_GUARD_KINDS = {
    "pretooluse": "stance",
    "postedit": "edit-advisor",
    "stopcheck": "stop-advisory",
}


def cmd_hook(target: Path, event: str) -> int:
    """Run a Claude Code hook entry point (all advisory — always exit 0).

    ``pretooluse`` warns on an out-of-stance tool; ``sessionstart`` prints the
    orientation injection to stdout; ``postedit`` reads the PostToolUse stdin
    payload (``tool_input.file_path``) and warns on stderr; ``stopcheck``
    prints session-close advisories to stderr. Every event fails open on a
    missing / malformed payload, config, or state.

    This dispatch is one of the two guard-fire choke points (KL-3, plan
    §5.3): each warning a guard hook surfaces is appended to
    ``<state_dir>/guard-fires.jsonl`` (surface ``hook``, posture ``advisory``
    — hooks never block). The write is fail-open and never alters the exit
    code: telemetry must never crash a hook.
    """
    handler = _HOOK_EVENTS.get(event)
    if handler is None:
        return 0
    try:
        warnings = handler(target)
        kind = _HOOK_GUARD_KINDS.get(event)
        if warnings and kind:
            record_guard_fires(
                target,
                load_config(target).state_dir,
                cmd=f"hook {event}",
                surface="hook",
                posture="advisory",
                findings=[Finding("", kind, warning) for warning in warnings],
            )
        return 0
    except Exception:  # noqa: BLE001 — hooks fail open by contract, always 0
        return 0


def _extra_check_findings(target: Path, config: Config) -> list:
    """Run the configured non-doc checkers (ledger, namespace, seams, budget).

    Each checker engages only when its inputs exist — an un-adopted project
    with no ledger, no namespace roots, no seams, and no boot docs runs none of
    them, so ``check`` stays meaningful before onboarding.
    """
    findings: list = []
    ledger_path = target / config.docs_root / LEDGER_FILENAME
    if ledger_path.exists():
        findings += check_ledger(ledger_path)
        findings += check_stamp_discipline(target / config.docs_root, ledger_path)
    roots = [target / r for r in config.namespace.get("roots", [])]
    roots = [r for r in roots if r.exists()]
    if roots:
        findings += check_namespace(
            roots,
            reserved=config.namespace.get("reserved") or None,
        )
    if config.seams:
        findings += check_seam_authority(target, config.seams)
    boot_docs = config.orientation.get("boot_docs") or config.readpath_docs
    docs_root = target / config.docs_root
    if any((docs_root / doc).exists() or (target / doc).exists() for doc in boot_docs):
        findings += check_orientation_budget(target, config)
    # The post-adopt ENGAGEMENT gate (KL-7): red in an adopted host until the
    # planted docs are rendered, a CI workflow runs the check, and the session
    # loop has engaged. Self-gating on adoption evidence — a bare tree adds
    # nothing here.
    findings += check_engagement(target, config)
    return findings


def cmd_check(
    target: Path,
    strict: bool,
    *,
    require_session_log: bool = False,
    session_log: Path | None = None,
    status_only: bool = False,
    inbox_base: Path | None = None,
) -> int:
    """Run every hygiene checker against ``target``.

    ``inbox_base`` (CLI ``--inbox-base``) names the merge-base version of
    ``control/inbox.md`` — extracted by CI in bash, because engine code never
    shells out to git (§3.2). When given, the append-only gate runs on both
    lanes: the change to ``control/inbox.md`` must be pure-append vs that base
    and its appended text must be well-formed ORDER blocks (issue #36 report
    2). It rides the fast lane exactly like the status gate — an inbox append
    is control-lane traffic — and self-skips when there is nothing to judge.

    ``status_only`` (CLI ``--status-only``) scopes the run to the control/
    status heartbeat checker alone — the CI control fast lane's gate. A
    control-only diff edits exactly the files ``check_status_current``
    validates, so the lane must not skip that one checker (a
    heartbeat-deleting control PR would merge green and pre-redden the NEXT
    unrelated full-suite PR — the fleet-review 2026-07-09 finding), but it
    must not pay the heavy suite either. Stdlib-only and session-log-free by
    construction: heartbeat PRs carry no session card. The allowlist and
    guard-fire telemetry apply exactly as in a full run, so a suppressed
    status finding behaves identically on both lanes.

    Docs (badge/link/reachable), the decisions ledger + stamp discipline, the
    namespace/shadowing guard, the seam-authority fences, and the orientation
    word budget — each engaging only when its inputs exist. Findings always
    count toward the exit code (under ``--strict``); an *incomplete* existing
    session log counts. A *missing* session log is **advisory by default** (a
    host may run ``check`` mid-session) but becomes a **hard failure** under
    ``require_session_log`` — the gate mode the live CI workflow runs, so a
    session that never writes its journal cannot merge (the "locked door" that
    makes the memory ritual non-optional, not merely advised). Uses config
    defaults if ``target`` has no ``substrate.config.json`` yet, so a project
    can lint before onboarding.

    ``session_log`` (CLI ``--session-log``) names the card to gate on
    *explicitly* — the diff-aware selection a CI workflow derives from which
    ``<sessions_dir>/*.md`` file the PR adds/changes. Without it the gate
    falls back to newest-by-mtime, which a fresh CI checkout silently degrades
    (every mtime flattens to checkout time), the trap that used to require a
    git-mtime-restore shim before this step. A named file that does not exist
    is treated exactly like an absent log (advisory by default, a hard failure
    under ``require_session_log``) — an explicit selection never silently
    falls back to a different card.

    Two KL-3 mechanisms ride the finding loop (plan §5.3):

    - **Reasons-required allowlist**: ``<state_dir>/check-exceptions.yml``
      entries suppress exact path+kind matches — but only entries carrying a
      ``reason``; a reason-less entry is refused and reported as its own
      finding. The session-log gate is never allowlistable.
    - **Guard-fire telemetry** (the ``check`` choke point): every surfaced
      finding — and every allowlist suppression, recorded with the entry's
      verdict + reason (creating the entry IS the verdict event) — appends a
      record to ``<state_dir>/guard-fires.jsonl``. Fail-open, written only
      into an existing install; the ``ci`` surface + ``did_not_run`` rows are
      derived by readers from the Checks API, never written in CI.
    """
    config = load_config(target)
    posture = "blocking" if strict else "advisory"
    # The control-protocol heartbeat (KL-8): static gate findings (missing /
    # heartbeat-less status.md) ride the strict loop like every checker;
    # wall-clock staleness is advisory-only and handled below — a required CI
    # check must never red on time alone (see check_status_current's docstring).
    # The validated path set is the host's configured heartbeat list (ORDER
    # 004: multi-Project repos gate one status file per lane).
    status_gate, status_advisories = check_status_current(
        target,
        status_files=config.heartbeat_files,
    )
    # Owner-action quality (ORDER 008): advisory-only by contract, like the
    # staleness warning — an unstructured ⚑ needs-owner ask nags on every run
    # (both lanes: the asks live in the heartbeat files the fast lane already
    # validates) but never reds a required check (see the checker docstring).
    owner_ask_advisories = check_owner_actions(
        target,
        status_files=config.heartbeat_files,
    )
    # Order-claim hygiene (ORDER 007): advisory-only, like the staleness and
    # owner-action warnings — a duplicate or stale `claimed-by:` is a
    # coordination race the manager reconciles, never a required-check red.
    # Runs on both lanes: claims live on the heartbeat orders line the fast
    # lane already validates.
    claim_advisories = check_claims(
        target,
        status_files=config.heartbeat_files,
    )
    # OWNER-ACTION ↔ CAPABILITIES cross-reference (kit-lab queue item 8, the
    # #68 card idea): advisory-only, like the ORDER 008 format nag it
    # extends — a wall-shaped ask whose wall the capability ledger doesn't
    # record (or records only as a working capability) nudges the session to
    # close the discovery-rule loop, never reds a required check (see the
    # checker docstring). Runs on both lanes: the asks live in the heartbeat
    # files the fast lane already validates.
    xref_advisories = check_capability_xref(
        target,
        status_files=config.heartbeat_files,
    )
    # The inbox append-only gate (issue #36 report 2): a control/inbox.md
    # change must be pure-append vs the merge-base + ORDER-grammar shaped.
    # Rides the finding loop like every checker; engages only when CI handed
    # in a base blob to diff against (no base → no-op, see the checker).
    inbox_findings = (
        check_inbox_append(target, inbox_base) if inbox_base is not None else []
    )
    if status_only:
        # --status-only: the fast lane's scoped gate (see docstring). Only the
        # control-lane checkers run — the heartbeat gate and, when CI passes a
        # base, the inbox append-only gate; everything downstream (allowlist,
        # guard fires, emit loop) is shared with the full run.
        doc_findings = list(status_gate) + inbox_findings
    else:
        docs_root = target / config.docs_root
        doc_findings = list(
            run_doc_checks(
                docs_root,
                config.badge_tokens,
                config.readpath_docs,
            )
        )
        doc_findings += _extra_check_findings(target, config) + status_gate
        doc_findings += inbox_findings
    entries, allow_findings = load_allowlist(target, config.state_dir)
    doc_findings, suppressed = apply_allowlist(doc_findings, entries)
    doc_findings += allow_findings
    if suppressed:
        _emit(
            f"check: {len(suppressed)} finding(s) suppressed by allowlist "
            "(reason-carrying entries; fires recorded with their verdicts).",
        )
        for finding, entry in suppressed:
            record_guard_fires(
                target,
                config.state_dir,
                cmd="check",
                surface="check",
                posture=posture,
                findings=[finding],
                verdict=entry.get("verdict"),
                reason=entry.get("reason"),
            )
    if doc_findings:
        _emit(f"check: {len(doc_findings)} finding(s):")
        for finding in doc_findings:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture=posture,
            findings=doc_findings,
        )
    if status_advisories:
        # Warn-only by contract: surfaced + telemetry-recorded, never counted
        # toward the exit code (a stale heartbeat must not red a required CI
        # check on wall-clock time alone — the Stop hook and this warning are
        # the nag; the manager's dark-Project read is the consequence).
        _emit(
            f"check: {len(status_advisories)} control-status advisory "
            "warning(s) (never exit-affecting):",
        )
        for finding in status_advisories:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture="advisory",
            findings=status_advisories,
        )
    if owner_ask_advisories:
        # Same warn-only contract as the staleness advisory above: surfaced +
        # telemetry-recorded, never counted toward the exit code — the owner-
        # action format migrates by nag, not by locked door (ORDER 008).
        _emit(
            f"check: {len(owner_ask_advisories)} owner-action advisory "
            "warning(s) (never exit-affecting):",
        )
        for finding in owner_ask_advisories:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture="advisory",
            findings=owner_ask_advisories,
        )
    if claim_advisories:
        # Same warn-only contract as the advisories above (ORDER 007): the
        # duplicate/stale-claim nudge is surfaced + telemetry-recorded but
        # never counted toward the exit code — the manager adjudicates the
        # tiebreak; the checker only flags the collision.
        _emit(
            f"check: {len(claim_advisories)} order-claim advisory "
            "warning(s) (never exit-affecting):",
        )
        for finding in claim_advisories:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture="advisory",
            findings=claim_advisories,
        )
    if xref_advisories:
        # Same warn-only contract as the advisories above (queue item 8):
        # the ledger cross-reference is a coarse token-overlap nudge —
        # surfaced + telemetry-recorded, never counted toward the exit code;
        # a heuristic match can never be a verdict.
        _emit(
            f"check: {len(xref_advisories)} capability cross-reference "
            "advisory warning(s) (never exit-affecting):",
        )
        for finding in xref_advisories:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture="advisory",
            findings=xref_advisories,
        )

    log_missing: list[str] = []
    log_absent_fails = False
    if status_only:
        # The fast lane's scoped gate never touches the session-log seam: a
        # control-only heartbeat PR carries no card by design (the lane's
        # whole point), so gating on one here would deadlock every heartbeat.
        if not doc_findings:
            _emit("check: control-status check passed (--status-only).")
            return 0
        return 1 if strict else 0
    if session_log is not None:
        explicit = session_log if session_log.is_absolute() else target / session_log
        log = explicit if explicit.is_file() else None
    else:
        log = latest_session_log(target / config.sessions_dir)
    log_missing = check_log(log, config.session_markers) if log else []
    # In gate mode an absent log is itself a failing condition, so it must feed
    # the exit code exactly like an incomplete one.
    log_absent_fails = log is None and require_session_log
    if log is None:
        if session_log is not None:
            absent = f"--session-log {session_log} does not exist"
        else:
            absent = f"no session log under {config.sessions_dir}/"
        if require_session_log:
            _emit(
                f"check: MERGE HELD — {absent} "
                "(--require-session-log): write one before merging.",
            )
        else:
            _emit(f"check: {absent} (advisory — not a failure).")
    else:
        rel = log.relative_to(target) if log.is_relative_to(target) else log
        if log_missing:
            _emit(f"check: session log {rel} is missing: {', '.join(log_missing)}")
        else:
            _emit(f"check: session log {rel} complete.")
    if log_missing or log_absent_fails:
        # The session gate is a guard too (the kit's flagship one) — its
        # fires feed B3 like any checker's. Never allowlistable, though.
        if log_absent_fails:
            if session_log is not None:
                absent = f"--session-log {session_log} does not exist"
            else:
                absent = f"no session log under {config.sessions_dir}/"
            gate_finding = Finding(
                "",
                "session-log",
                f"{absent} (--require-session-log)",
            )
        else:
            log_rel = str(log.relative_to(target)) if log.is_relative_to(target) else str(log)
            gate_finding = Finding(
                log_rel,
                "session-log",
                f"missing: {', '.join(log_missing)}",
            )
        record_guard_fires(
            target,
            config.state_dir,
            cmd="check",
            surface="check",
            posture="blocking" if (strict or require_session_log) else "advisory",
            findings=[gate_finding],
        )

    if not doc_findings and not log_missing and not log_absent_fails:
        _emit("check: all checks passed.")
        return 0
    return 1 if strict else 0


def _require_state(
    target: Path,
    command: str,
) -> tuple[Config, JsonStateBackend] | None:
    """Load config + state; None (with a message) when the install is missing.

    Also runs the live-loop guardrail: state-backed commands read AND write
    the install, and only ``init``/``adopt`` were guarded before — ``ledger``,
    the ``--build`` emitters, and ``episodes --rebuild`` wrote into a target
    the guardrail would have refused.
    """
    assert_safe_target(target, _kit_root())
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    if not backend.data:
        _emit(f"{command}: no state at {target} (run init first).")
        return None
    return config, backend


def _question_for_slot(slot: str) -> dict | None:
    """Return the bank question that fills ``slot`` (None when unknown)."""
    for question in QUESTIONS:
        if question["slot"] == slot:
            return question
    return None


def cmd_answer(target: Path, slot: str, answer: str) -> int:
    """Record a user answer for ``slot`` (fills it, resolves its escalation)."""
    loaded = _require_state(target, "answer")
    if loaded is None:
        return 1
    _, backend = loaded
    question = _question_for_slot(slot)
    if question is None:
        known = ", ".join(q["slot"] for q in QUESTIONS)
        _emit(f"answer: unknown slot {slot!r} (known: {known}).")
        return 2
    record_answer(backend, question, answer, source="user")
    status = backend.get("slots", {}).get(slot)
    _emit(f"answer: {slot} -> {status}.")
    if status == "partial":
        floor = int(question.get("min_len", 1))
        _emit(f"answer: too thin to count (needs >= {floor} chars of substance).")
    return 0


def cmd_confirm(target: Path, slot: str) -> int:
    """Confirm a provisional (self-answered) slot as user-verified."""
    loaded = _require_state(target, "confirm")
    if loaded is None:
        return 1
    _, backend = loaded
    if confirm_slot(backend, slot, source="user"):
        _emit(f"confirm: {slot} confirmed (provisional -> filled).")
        return 0
    _emit(f"confirm: {slot} is not provisional (nothing to confirm).")
    return 1


def cmd_triggers(target: Path) -> int:
    """Scan for fired triggers and show the mandated / advisory questions."""
    loaded = _require_state(target, "triggers")
    if loaded is None:
        return 1
    config, backend = loaded
    triggers = check_triggers(target, config, backend.data)
    if not triggers:
        _emit("triggers: none fired.")
        return 0
    questions = mandatory_questions(triggers)
    block = trigger_block(
        triggers,
        questions,
        mandate=triggers_mandate(backend.data),
    )
    _emit(block)
    return 0


def cmd_reflect(
    target: Path,
    *,
    add: str | None,
    evidence: str,
    tags: str,
    mine: bool,
) -> int:
    """List, add to, or mine the forward reflection buffer."""
    loaded = _require_state(target, "reflect")
    if loaded is None:
        return 1
    config, backend = loaded
    path = target / config.state_dir / REFLECTIONS_FILENAME
    buffer_size = int(config.reflection.get("buffer_size", 5))
    if add is not None:
        entry = add_reflection(
            path,
            lesson=add,
            evidence=evidence,
            tags=[t for t in tags.split(",") if t],
            buffer_size=buffer_size,
        )
        _emit(f"reflect: added {entry['id']}.")
    if mine:
        known = {e.get("lesson", "") for e in load_reflections(path)}
        candidates = [
            c
            for c in mine_reflections(target / config.sessions_dir)
            if c["lesson"] not in known
        ]
        for cand in candidates:
            entry = add_reflection(
                path,
                lesson=cand["lesson"],
                evidence=cand.get("evidence", ""),
                tags=list(cand.get("tags", [])),
                buffer_size=buffer_size,
            )
            known.add(cand["lesson"])
            _emit(f"reflect: mined {entry['id']} — {cand['lesson'][:60]}")
        if not candidates:
            _emit("reflect: mined nothing new.")
    entries = load_reflections(path)
    backend.set(
        "reflection_buffer",
        {
            "active_count": len(entries),
            "last_mined": (
                date.today().isoformat()
                if mine
                else (backend.get("reflection_buffer", {}) or {}).get("last_mined")
            ),
        },
    )
    block = lessons_block(entries)
    _emit(block if block else "reflect: buffer empty.")
    return 0


def cmd_episodes(target: Path, *, rebuild: bool, search: str | None) -> int:
    """Rebuild or search the episodic index over the session logs."""
    config = load_config(target)
    if rebuild:
        assert_safe_target(target, _kit_root())
    index_path = target / config.state_dir / EPISODIC_INDEX_FILENAME
    if rebuild:
        entries = rebuild_episodic_index(target / config.sessions_dir, index_path)
        _emit(f"episodes: indexed {len(entries)} session(s).")
    if search is not None:
        hits = search_episodes(index_path, search)
        for hit in hits:
            _emit(
                f"  {hit.get('date', '?')} {hit.get('slug', '?')} — "
                f"{hit.get('summary', '')}",
            )
        _emit(f"episodes: {len(hits)} hit(s) for {search!r}.")
    if not rebuild and search is None:
        _emit("episodes: pass --rebuild and/or --search TAG.")
    return 0


def cmd_metrics(target: Path) -> int:
    """Emit the router / workflow KPIs (JSON + the one-line footer)."""
    loaded = _require_state(target, "metrics")
    if loaded is None:
        return 1
    config, backend = loaded
    kpis = workflow_kpis(backend.data, target / config.sessions_dir)
    _emit(json.dumps(kpis, indent=2, sort_keys=True))
    _emit(kpi_footer(kpis))
    return 0


def cmd_maintain(target: Path, *, compact: bool) -> int:
    """Run the self-maintenance loop's report (and compaction when asked)."""
    loaded = _require_state(target, "maintain")
    if loaded is None:
        return 1
    config, backend = loaded
    if compact:
        if compaction_due(backend.data, dict(config.cadence or {})):
            path = run_compaction(target, config, backend)
            rel = path.relative_to(target) if path.is_relative_to(target) else path
            _emit(f"maintain: compaction written -> {rel}")
        else:
            _emit("maintain: compaction not due.")
    triggers = check_triggers(target, config, backend.data)
    economy = economy_check(target, config)
    ledger_path = target / config.docs_root / LEDGER_FILENAME
    ledger_findings = check_ledger(ledger_path) if ledger_path.exists() else []
    kpis = workflow_kpis(backend.data, target / config.sessions_dir)
    _emit(
        maintenance_report(
            target,
            config,
            backend,
            triggers=triggers,
            economy_findings=list(economy.get("findings", [])),
            ledger_findings=ledger_findings,
            kpis=kpis,
        ),
    )
    return 0


def cmd_review(
    target: Path,
    action: str,
    slot: str | None,
    *,
    verdict: str,
    reviewer: str,
) -> int:
    """Drive the independent-review seam: build payloads, record verdicts."""
    if action == "doc":
        _emit(seam_wiring_doc())
        return 0
    if slot is None:
        _emit("review: a slot is required for build/confirm.")
        return 2
    loaded = _require_state(target, "review")
    if loaded is None:
        return 1
    config, backend = loaded
    if action == "build":
        payload = build_review_payload(backend, slot)
        if not payload:
            _emit(f"review: slot {slot!r} is not provisional — nothing to review.")
            return 1
        path = write_review_payload(target, config, payload)
        rel = path.relative_to(target) if path.is_relative_to(target) else path
        _emit(f"review: payload written -> {rel}")
        return 0
    if action == "confirm":
        if verdict not in ("pass", "fail"):
            _emit("review: --verdict must be pass or fail.")
            return 2
        outcome = apply_review_verdict(
            backend,
            slot,
            verdict=verdict,
            reviewer=reviewer,
        )
        _emit(f"review: {slot} -> {outcome}.")
        if outcome == "not-provisional":
            _emit(
                "review: nothing recorded — the slot is not provisional "
                "(typo, already confirmed, or never answered).",
            )
            return 1
        # The verdict is recorded → the payload is consumed. Remove it so the
        # maintenance "awaiting a reviewer" count reflects reality.
        if clear_review_payload(target, config, slot):
            _emit(f"review: cleared consumed payload for {slot}.")
        return 0
    _emit(f"review: unknown action {action!r} (build | confirm | doc).")
    return 2


def cmd_economy(
    target: Path,
    action: str,
    *,
    strict: bool,
    apply: bool,
    reviewed: bool,
    bands: int,
) -> int:
    """Drive the context-economy engine: check, apply, simulate, recipe."""
    config = load_config(target)
    if action == "recipe":
        _emit(calibration_recipe())
        return 0
    if action == "simulate":
        result = run_search(default_calibration(), bands=bands)
        _emit(str(result.get("why_it_won", "")))
        winner = result.get("winner", {})
        name = winner.get("name") if isinstance(winner, dict) else winner
        _emit(f"economy: winner {name} (feasible: {result.get('feasible_count')}).")
        return 0
    pass_records = (
        target / config.docs_root / config.economy.get("pass_records_dir", "planning")
    )
    harvested = parse_harvest_tables(pass_records)
    report = economy_check(
        target,
        config,
        harvested=harvested,
        harvest_exclude=harvest_sources(pass_records),
    )
    if action == "issue-body":
        _emit(issue_body(report))
        return 0
    if action == "check":
        census = report.get("census", {})
        for name in sorted(census):
            row = census[name]
            _emit(
                f"  class {name}: {row.get('files', 0)} file(s), "
                f"{row.get('words', 0)} word(s)",
            )
        for gauge in report.get("gauges", []):
            flag = "OVER" if gauge.get("over") else "ok"
            _emit(f"  gauge {gauge['name']}: {gauge['value']}/{gauge['cap']} [{flag}]")
        findings = report.get("findings", [])
        for finding in findings:
            _emit(f"  [{finding.kind}] {finding.path}: {finding.message}")
        for line in economy_actuate(target, config, report, apply=False):
            _emit(f"  would-act: {line}")
        debt = report.get("debt", 0)
        threshold = int(config.economy.get("debt_threshold", 10))
        _emit(f"economy: debt {debt} (threshold {threshold}).")
        over = bool(findings) or debt >= threshold
        return 1 if strict and over else 0
    if action == "apply":
        if apply:
            backend = JsonStateBackend(_state_path(target, config))
            if backend.data and not actuators_may_apply(backend.data):
                _emit(
                    "economy: refused — the mode/promotion policy does not "
                    "permit actuators to apply (promotion_rights must be "
                    "'promote'); dry-run only.",
                )
                return 1
        lines = economy_actuate(
            target,
            config,
            report,
            apply=apply,
            acknowledged=reviewed,
        )
        for line in lines:
            _emit(f"  {line}")
        if not apply:
            _emit("economy: dry-run (pass --yes to act; maturity gates apply).")
        return 0
    _emit(
        f"economy: unknown action {action!r} "
        "(check | apply | simulate | recipe | issue-body).",
    )
    return 2


def cmd_adopt(
    target: Path,
    include_claude: bool,
    wire_enforcement: bool = False,
    lane: str | None = None,
) -> int:
    """Adopt the workflow into ``target``: init, plant the docs, stage the packs.

    The one-step flow: ``init`` runs first (idempotent — config + state), so a
    bare directory with nothing but the bootstrap file becomes a fully
    substrate-governed project in this single command. ``wire_enforcement``
    additionally turns on the live nag hook + the CI locked door. ``lane``
    is the SHARED-repo shape (multi-Project cohabitation): this Project's
    heartbeat plants as ``control/status-<lane>.md`` and is declared in
    ``heartbeat_files``; the rest of the bus is shared, never re-planted.
    """
    rc = cmd_init(target)
    if rc != 0:
        return rc
    config = load_config(target)
    backend = JsonStateBackend(_state_path(target, config))
    try:
        lines = adopt(
            target,
            config,
            backend,
            kit_root=_kit_root(),
            include_claude=include_claude,
            wire_enforcement=wire_enforcement,
            lane=lane,
        )
    except ValueError as exc:
        _emit(f"adopt: REFUSED — {exc}")
        return 2
    for line in lines:
        _emit(f"adopt: {line}")
    # KL-7 — the adopter is told, in the adopt output itself, exactly what the
    # born-red engagement gate needs: the gate's findings ARE the checklist.
    # KL-8 rider: the control-protocol gate findings (the just-planted seed
    # status.md has no heartbeat yet) join the same checklist — "write your
    # first real heartbeat" is part of engaging, same shape as the first card.
    status_gate, _ = check_status_current(
        target,
        status_files=config.heartbeat_files,
    )
    engage = check_engagement(target, config) + status_gate
    if engage:
        _emit(
            f"adopt: NOT ENGAGED — `check --strict` holds RED until these "
            f"{len(engage)} item(s) are done:",
        )
        for finding in engage:
            where = f"{finding.path}: " if finding.path else ""
            _emit(f"adopt:   [{finding.kind}] {where}{finding.message}")
    else:
        _emit("adopt: ENGAGED — the post-adopt gate is green.")
    return 0


def cmd_upgrade(
    target: Path,
    *,
    apply_docs: bool,
    rollback: bool,
    release_json: Path | None,
    keep_inputs: bool = False,
) -> int:
    """Run the §4.3 upgrade flow (or ``--rollback``) against ``target``.

    The consumer flow: download the new release's file as ``bootstrap.py.new``
    (plus its ``release.json`` for sha256 verification) and run
    ``python3 bootstrap.py.new upgrade``. Archives before it overwrites;
    planted docs are only ever touched under ``--apply-docs`` and only when
    the recorded hash proves the consumer never edited them. On completion
    the consumed inputs (the ``.new`` file + its adjacent ``release.json``)
    are removed unless ``--keep-inputs``.
    """
    loaded = _require_state(target, "upgrade")
    if loaded is None:
        return 1
    config, backend = loaded
    if rollback:
        for line in run_rollback(target, config):
            _emit(f"upgrade: {line}")
        return 0
    running = (
        Path(sys.argv[0]).resolve()
        if sys.argv and sys.argv[0]
        else Path(__file__).resolve()
    )
    try:
        lines = run_upgrade(
            target,
            config,
            backend,
            kit_root=_kit_root(),
            running=running,
            apply_docs=apply_docs,
            release_json=release_json,
            cleanup_inputs=not keep_inputs,
        )
    except UpgradeRefused as exc:
        _emit(f"upgrade: REFUSED — {exc}")
        return 2
    for line in lines:
        _emit(f"upgrade: {line}")
    return 0


def cmd_contextpack(target: Path, index: Path | None) -> int:
    """Generate agent context packs from the project index (or a manifest)."""
    assert_safe_target(target, _kit_root())
    config = load_config(target)
    index_path = index if index is not None else target / "project.index.json"
    if not index_path.exists():
        _emit(f"contextpack: no index at {index_path} (run adopt first).")
        return 1
    try:
        areas = load_pack_index(index_path)
    except ValueError as exc:
        _emit(f"contextpack: {exc}")
        return 2
    if not areas:
        _emit("contextpack: index has no areas — nothing to generate.")
        return 0
    for path in generate_packs(target, config, areas):
        rel = path.relative_to(target) if path.is_relative_to(target) else path
        _emit(f"contextpack: wrote {rel}")
    return 0


def cmd_session_start(target: Path) -> int:
    """Print this session's orientation injection (the SessionStart composition).

    Also records the session-start evidence anchor (fail-open) — the same
    baseline the SessionStart hook records, so a session driven by the CLI
    instead of the hook still gets an evidence-backed auto-draft at close.
    """
    loaded = _require_state(target, "session-start")
    if loaded is None:
        return 1
    config, backend = loaded
    _emit(compose_orientation(target, config, backend))
    record_session_anchor(target, config, backend)
    return 0


def cmd_session_close(target: Path) -> int:
    """Run the session-close ritual: draft, mine, index, advise, report KPIs.

    First auto-drafts the session card's close-out from evidence (KL-5 —
    ``ensure_draft``; fail-open), then mines the session logs into the
    reflection buffer, rebuilds the episodic index, harvests the
    ``📊 Model:`` line into the PL-004 model-usage feed
    (``telemetry/model-usage.jsonl`` — one row per session, KL-3; a drafted
    ``[[fill:]]`` stand-in line is never harvested), prints the stop-check
    advisories, and ends with the KPI footer — the engine analog of the
    one-idea / previous-session-review enders.
    """
    loaded = _require_state(target, "session-close")
    if loaded is None:
        return 1
    config, backend0 = loaded
    # KL-5 mechanized write-back: draft the card/close-out from evidence
    # BEFORE the ritual runs, so mining/advisories see the drafted state and
    # a session that wrote nothing still leaves an evidence-backed draft.
    for line in ensure_draft(target, config, backend0):
        _emit(f"session-close: [draft] {line}")
    rc = cmd_reflect(target, add=None, evidence="", tags="", mine=True)
    if rc != 0:
        return rc
    index_path = target / config.state_dir / EPISODIC_INDEX_FILENAME
    entries = rebuild_episodic_index(target / config.sessions_dir, index_path)
    _emit(f"session-close: indexed {len(entries)} session(s).")
    log = latest_session_log(target / config.sessions_dir)
    for line in harvest_model_usage(target, log):
        _emit(f"session-close: {line}")
    # Whole-tree reconcile (KL-3 write-at-commit, gen-2 queue item 6): the
    # single-latest harvest above only ever wrote the newest card's row, so a
    # card committed under a newer one was never harvested (10 rows vs 42
    # eligible cards). Sweep every complete card so no eligible card is left
    # behind — idempotent + fail-open, so it costs a re-scan and nothing else.
    for line in reconcile_model_usage(target, target / config.sessions_dir):
        _emit(f"session-close: {line}")
    # Re-read state: the mine above stamped reflection_buffer.last_mined, and
    # a pre-mine snapshot would re-advise the mine it just ran.
    backend = JsonStateBackend(_state_path(target, config))
    for line in evaluate_stop(target, config, backend):
        _emit(f"session-close: [advisory] {line}")
    # §9.1: filing friction issues rides session-close, best-effort — the
    # engine cannot reach GitHub, so it advises the session/agent instead.
    pending = list_outbox(target, config.state_dir)
    if pending:
        _emit(
            f"session-close: [advisory] {len(pending)} friction report(s) "
            f"pending in {config.state_dir}/friction-outbox/ — file each as "
            f"a `{FRICTION_LABEL}`-labeled issue on the kit repo "
            "(`friction show <name>` prints the issue title+body), then "
            "delete the drained file.",
        )
    kpis = workflow_kpis(backend.data, target / config.sessions_dir)
    _emit(kpi_footer(kpis))
    return 0


def cmd_draft(target: Path) -> int:
    """Auto-draft the session card / close-out from evidence, on demand.

    The same seam ``session-close`` and the Stop hook run (KL-5): a missing
    card gets a drafted skeleton, an in-progress card missing its close-out
    gets the drafted section appended, a drafted card reports its unresolved
    ``[[fill:]]`` slots, and a completed card is never touched.
    """
    loaded = _require_state(target, "draft")
    if loaded is None:
        return 1
    config, backend = loaded
    lines = ensure_draft(target, config, backend)
    if not lines:
        _emit("draft: nothing to do (card complete, or close-out already present).")
        return 0
    for line in lines:
        _emit(f"draft: {line}")
    return 0


def cmd_friction(
    target: Path,
    action: str,
    *,
    repo: str | None,
    name: str | None,
) -> int:
    """Drive the §9.1 friction-report protocol's consumer half.

    ``export`` collects the ⚑ friction records (reflection buffer + a full
    session-log scan), wraps them in the wire envelope, writes it to
    ``<state_dir>/friction-outbox/``, and prints the issue-ready title +
    body — **the engine never files the issue itself** (stdlib-only, no
    credentials): the session/agent files it on the kit repo with the
    ``friction`` label and deletes the drained outbox file. ``list`` shows
    pending outbox envelopes; ``show <name>`` re-prints one's issue text
    (how a later session drains an outbox held by a network/credential
    failure).
    """
    loaded = _require_state(target, "friction")
    if loaded is None:
        return 1
    config, _ = loaded
    if action == "list":
        pending = list_outbox(target, config.state_dir)
        for path in pending:
            envelope = load_envelope(path) or {}
            count = len(envelope.get("reports") or [])
            _emit(f"  {path.name} — {count} report(s), repo {envelope.get('repo')!r}")
        _emit(f"friction: {len(pending)} pending outbox envelope(s).")
        return 0
    if action == "show":
        if not name:
            _emit("friction: show needs the outbox file name (see `friction list`).")
            return 2
        path = target / config.state_dir / "friction-outbox" / name
        envelope = load_envelope(path)
        if envelope is None:
            _emit(f"friction: no readable envelope at {path}.")
            return 1
        _emit(f"title: {friction_issue_title(envelope)}")
        _emit("")
        _emit(friction_issue_body(envelope))
        return 0
    if action != "export":
        _emit(f"friction: unknown action {action!r} (export | list | show).")
        return 2
    reports = friction_reports(target, config)
    if not reports:
        _emit("friction: no \N{BLACK FLAG} friction records found — nothing to export.")
        return 0
    repo_name = repo or detect_repo(target)
    if not repo_name:
        _emit(
            "friction: could not detect the GitHub repo from .git/config — "
            "pass --repo <owner/name>.",
        )
        return 2
    envelope = build_envelope(
        repo=repo_name,
        project_id=str(config.project_id),
        # The honest install record — "" (rendered "unrecorded") when the
        # install predates version recording; never guessed from KIT_VERSION.
        kit_version=config.kit_version or "",
        reports=reports,
    )
    path = write_outbox(target, config.state_dir, envelope)
    rel = path.relative_to(target) if path.is_relative_to(target) else path
    _emit(f"friction: wrote {rel} ({len(reports)} report(s)).")
    _emit(
        f"friction: now file it — open a `{FRICTION_LABEL}`-labeled issue on "
        "the kit repo with the title+body below, then delete the outbox file.",
    )
    _emit("")
    _emit(f"title: {friction_issue_title(envelope)}")
    _emit("")
    _emit(friction_issue_body(envelope))
    return 0


def cmd_ledger(
    target: Path,
    *,
    title: str,
    verdict: str,
    why: str,
    provenance: str,
    supersedes: str | None,
) -> int:
    """Append a decision to the [D-NNNN] ledger (created on first use)."""
    assert_safe_target(target, _kit_root())
    config = load_config(target)
    path = target / config.docs_root / LEDGER_FILENAME
    entry = append_decision(
        path,
        title=title,
        verdict=verdict,
        why=why,
        provenance=provenance,
        supersedes=supersedes,
    )
    _emit(f"ledger: recorded {entry['id']} — {title}")
    if supersedes:
        _emit(f"ledger: {supersedes} stamped superseded-by {entry['id']}.")
    return 0


def _simulate_mode_asserts(
    mode: str,
    data: dict,
    graduated: bool,
    n: int,
) -> str | None:
    """Return the per-mode behavior violation, or None when behavior held.

    The behavior-assert half of the simulation: observe must never
    auto-graduate (it proposes), guided/active must graduate once the quiet
    streak is long enough.
    """
    quiet_needed = 3
    if mode == "observe":
        if graduated or data.get("stage") != "integration":
            return "observe mode auto-graduated (must only propose)"
        if n > quiet_needed and not data.get("graduation_proposed"):
            return "observe mode never proposed graduation"
        return None
    if n > quiet_needed and not graduated:
        return f"{mode} mode failed to graduate after the quiet streak"
    return None


def cmd_simulate(n: int, mode: str = "guided") -> int:
    """Init into a temp dir and drive ``n`` interview sessions; verify behavior.

    Session 1 supplies confirmed answers for every critical slot; later sessions
    supply none. Asserts the critical slots fill and that the run behaves
    per ``mode``: guided/active graduate integration -> steady once quiet;
    observe only ever *proposes* graduation.
    """
    with tempfile.TemporaryDirectory(prefix="substrate-sim-") as tmp:
        target = Path(tmp)
        rc = cmd_init(target)
        if rc != 0:
            return rc
        state_path = _state_path(target, load_config(target))
        if mode != "guided":
            rc = cmd_mode(target, mode)
            if rc != 0:
                return rc
        crit = critical_slots()
        answers = {slot: f"value-for-{slot}" for slot in crit}
        graduated = False
        for index in range(n):
            backend = JsonStateBackend(state_path)
            result = run_session(backend, answers if index == 0 else {})
            graduated = graduated or result["graduated"]
        data = JsonStateBackend(state_path).data
        missing = [s for s in crit if data.get("slots", {}).get(s) != "filled"]
        if missing:
            _emit(f"simulate: FAILED — critical slots unfilled: {missing}")
            return 1
        violation = _simulate_mode_asserts(mode, data, graduated, n)
        if violation:
            _emit(f"simulate: FAILED — {violation}")
            return 1
        _emit(
            f"simulate: OK — {n} session(s), {len(crit)} critical slots filled, "
            f"mode={mode}, stage={data.get('stage')} (graduated={graduated}).",
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the bootstrap argument parser."""
    parser = argparse.ArgumentParser(prog="bootstrap", description="substrate-kit")
    parser.add_argument(
        "--version",
        action="version",
        version=f"substrate-kit {KIT_VERSION}",
        help="print the kit version and exit",
    )
    parser.add_argument(
        "--simulate",
        type=int,
        metavar="N",
        help="run N synthetic sessions in a temp dir, then exit",
    )
    parser.add_argument(
        "--mode",
        default="guided",
        choices=("observe", "guided", "active"),
        help="integration mode for --simulate (behavior asserts differ per mode)",
    )
    sub = parser.add_subparsers(dest="command")
    for name, helptext in (
        ("init", "initialise a project"),
        ("status", "show install state"),
        ("ask", "list pending interview questions"),
        ("triggers", "scan for fired triggers / mandatory questions"),
        ("metrics", "emit the router + workflow KPIs"),
        ("session-start", "print this session's orientation injection"),
        ("session-close", "draft the close-out, mine reflections, report KPIs"),
        ("draft", "auto-draft the session card / close-out from evidence"),
    ):
        child = sub.add_parser(name, help=helptext)
        child.add_argument("--target", type=Path, default=Path.cwd())
    adopt_p = sub.add_parser("adopt", help="plant the workflow docs + stage the packs")
    adopt_p.add_argument(
        "--include-claude",
        action="store_true",
        help="also write .claude/CLAUDE.md + .claude/settings.json (skip-if-exists)",
    )
    adopt_p.add_argument(
        "--wire-enforcement",
        action="store_true",
        help=(
            "turn on the forcing functions: the live nag hook (implies "
            "--include-claude) + a live CI gate that holds the merge red until "
            "the session journal is written"
        ),
    )
    adopt_p.add_argument(
        "--lane",
        metavar="NAME",
        default=None,
        help=(
            "adopt as a named lane in a SHARED multi-Project repo: plant "
            "control/status-NAME.md as this Project's heartbeat (declared in "
            "heartbeat_files) and share the rest of the control/ bus"
        ),
    )
    adopt_p.add_argument("--target", type=Path, default=Path.cwd())
    upgrade_p = sub.add_parser(
        "upgrade",
        help="upgrade the install to this bootstrap's version (archives first)",
    )
    upgrade_p.add_argument(
        "--apply-docs",
        action="store_true",
        help="re-render template-improved docs the consumer never edited",
    )
    upgrade_p.add_argument(
        "--rollback",
        action="store_true",
        help="restore the state + dist banked by the last upgrade",
    )
    upgrade_p.add_argument(
        "--release-json",
        type=Path,
        default=None,
        help="release.json to verify this file's sha256 against "
        "(default: one next to the running file, when present)",
    )
    upgrade_p.add_argument(
        "--keep-inputs",
        action="store_true",
        help="keep bootstrap.py.new + its release.json after a completed "
        "upgrade (default: the consumed inputs are removed)",
    )
    upgrade_p.add_argument("--target", type=Path, default=Path.cwd())
    contextpack = sub.add_parser(
        "contextpack",
        help="generate agent context packs from the index",
    )
    contextpack.add_argument(
        "--index",
        type=Path,
        default=None,
        help="index or manifest path (default: <target>/project.index.json)",
    )
    contextpack.add_argument("--target", type=Path, default=Path.cwd())
    render_p = sub.add_parser("render", help="render content docs from filled slots")
    render_p.add_argument(
        "--live",
        action="store_true",
        help="fill remaining placeholders in the PLANTED docs in place",
    )
    render_p.add_argument("--target", type=Path, default=Path.cwd())
    answer = sub.add_parser("answer", help="record a user answer for a slot")
    answer.add_argument("slot")
    answer.add_argument("value", nargs="+", help="the answer text")
    answer.add_argument("--target", type=Path, default=Path.cwd())
    confirm = sub.add_parser("confirm", help="confirm a provisional slot")
    confirm.add_argument("slot")
    confirm.add_argument("--target", type=Path, default=Path.cwd())
    reflect = sub.add_parser("reflect", help="list/add/mine the reflection buffer")
    reflect.add_argument("--add", metavar="LESSON", default=None)
    reflect.add_argument("--evidence", default="")
    reflect.add_argument("--tags", default="", help="comma-separated tags")
    reflect.add_argument("--mine", action="store_true")
    reflect.add_argument("--target", type=Path, default=Path.cwd())
    episodes = sub.add_parser("episodes", help="rebuild/search the episodic index")
    episodes.add_argument("--rebuild", action="store_true")
    episodes.add_argument("--search", metavar="TAG", default=None)
    episodes.add_argument("--target", type=Path, default=Path.cwd())
    maintain = sub.add_parser("maintain", help="run the self-maintenance report")
    maintain.add_argument("--compact", action="store_true")
    maintain.add_argument("--target", type=Path, default=Path.cwd())
    review = sub.add_parser("review", help="drive the independent-review seam")
    review.add_argument("action", choices=("build", "confirm", "doc"))
    review.add_argument("slot", nargs="?", default=None)
    review.add_argument("--verdict", default="", help="pass | fail (for confirm)")
    review.add_argument("--reviewer", default="external")
    review.add_argument("--target", type=Path, default=Path.cwd())
    economy = sub.add_parser("economy", help="run the context-economy engine")
    economy.add_argument(
        "action",
        choices=("check", "apply", "simulate", "recipe", "issue-body"),
    )
    economy.add_argument("--strict", action="store_true")
    economy.add_argument("--yes", action="store_true", help="really act (apply)")
    economy.add_argument(
        "--reviewed",
        action="store_true",
        help="acknowledge the human review a 'gated' maturity first prune needs",
    )
    economy.add_argument("--bands", type=int, default=24)
    economy.add_argument("--target", type=Path, default=Path.cwd())
    friction = sub.add_parser(
        "friction",
        help="export/list/show §9.1 friction-report envelopes (outbox)",
    )
    friction.add_argument("action", choices=("export", "list", "show"))
    friction.add_argument(
        "name",
        nargs="?",
        default=None,
        help="outbox file name (for show)",
    )
    friction.add_argument(
        "--repo",
        default=None,
        help="this consumer's GitHub owner/name (default: parsed from .git/config)",
    )
    friction.add_argument("--target", type=Path, default=Path.cwd())
    ledger = sub.add_parser("ledger", help="append a [D-NNNN] decision")
    ledger.add_argument("--title", required=True)
    ledger.add_argument("--verdict", required=True)
    ledger.add_argument("--why", required=True)
    ledger.add_argument("--provenance", required=True)
    ledger.add_argument("--supersedes", default=None)
    ledger.add_argument("--target", type=Path, default=Path.cwd())
    mode = sub.add_parser("mode", help="set the integration mode")
    mode.add_argument("name")
    mode.add_argument("--target", type=Path, default=Path.cwd())
    stance = sub.add_parser("stance", help="show or set the task stance")
    stance.add_argument("name", nargs="?", default=None)
    stance.add_argument("--target", type=Path, default=Path.cwd())
    skills = sub.add_parser("skills", help="list or --build the skill pack")
    skills.add_argument(
        "--build",
        action="store_true",
        help="emit SKILL.md files into <state_dir>/skills/",
    )
    skills.add_argument("--target", type=Path, default=Path.cwd())
    agents = sub.add_parser("agents", help="list or --build the persona pack")
    agents.add_argument(
        "--build",
        action="store_true",
        help="emit agent .md files into <state_dir>/agents/",
    )
    agents.add_argument("--target", type=Path, default=Path.cwd())
    hooks = sub.add_parser("hooks", help="show or --build the hook wiring")
    hooks.add_argument(
        "--build",
        action="store_true",
        help="emit the PreToolUse settings snippet into <state_dir>/hooks/",
    )
    hooks.add_argument("--target", type=Path, default=Path.cwd())
    hook = sub.add_parser("hook", help="run a hook check (e.g. `hook pretooluse`)")
    hook.add_argument("event")
    hook.add_argument("--target", type=Path, default=Path.cwd())
    check = sub.add_parser("check", help="run the doc + session-log hygiene checks")
    check.add_argument("--target", type=Path, default=Path.cwd())
    check.add_argument("--strict", action="store_true", help="exit 1 if any violation")
    check.add_argument(
        "--require-session-log",
        action="store_true",
        help="fail (not just advise) when the session log is missing — the CI gate mode",
    )
    check.add_argument(
        "--session-log",
        type=Path,
        default=None,
        help=(
            "gate on this session card explicitly (e.g. the card the PR's diff "
            "touches) instead of newest-by-mtime; a missing file counts as an "
            "absent log, never a silent fallback"
        ),
    )
    check.add_argument(
        "--status-only",
        action="store_true",
        help=(
            "run ONLY the control/ status heartbeat checker — the CI control "
            "fast lane's scoped gate: a control-only diff edits exactly the "
            "files this checker validates, so the lane must still prove the "
            "heartbeat parses (stdlib-only, session-log-free)"
        ),
    )
    check.add_argument(
        "--inbox-base",
        type=Path,
        default=None,
        help=(
            "gate control/inbox.md against this merge-base copy of the file "
            "(CI extracts the base blob with git, since engine code never "
            "shells out): the change must be pure-append and its appended "
            "text well-formed ORDER blocks; omit when there is no inbox diff"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the bootstrap CLI; return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.simulate is not None:
            return cmd_simulate(args.simulate, args.mode)
        if args.command == "init":
            return cmd_init(args.target)
        if args.command == "status":
            return cmd_status(args.target)
        if args.command == "ask":
            return cmd_ask(args.target)
        if args.command == "render":
            return cmd_render(args.target, live=args.live)
        if args.command == "mode":
            return cmd_mode(args.target, args.name)
        if args.command == "stance":
            return cmd_stance(args.target, args.name)
        if args.command == "skills":
            return cmd_skills(args.target, args.build)
        if args.command == "agents":
            return cmd_agents(args.target, args.build)
        if args.command == "hooks":
            return cmd_hooks(args.target, args.build)
        if args.command == "hook":
            return cmd_hook(args.target, args.event)
        if args.command == "check":
            return cmd_check(
                args.target,
                args.strict,
                require_session_log=args.require_session_log,
                session_log=args.session_log,
                status_only=args.status_only,
                inbox_base=args.inbox_base,
            )
        if args.command == "answer":
            return cmd_answer(args.target, args.slot, " ".join(args.value))
        if args.command == "confirm":
            return cmd_confirm(args.target, args.slot)
        if args.command == "triggers":
            return cmd_triggers(args.target)
        if args.command == "reflect":
            return cmd_reflect(
                args.target,
                add=args.add,
                evidence=args.evidence,
                tags=args.tags,
                mine=args.mine,
            )
        if args.command == "episodes":
            return cmd_episodes(args.target, rebuild=args.rebuild, search=args.search)
        if args.command == "metrics":
            return cmd_metrics(args.target)
        if args.command == "maintain":
            return cmd_maintain(args.target, compact=args.compact)
        if args.command == "review":
            return cmd_review(
                args.target,
                args.action,
                args.slot,
                verdict=args.verdict,
                reviewer=args.reviewer,
            )
        if args.command == "economy":
            return cmd_economy(
                args.target,
                args.action,
                strict=args.strict,
                apply=args.yes,
                reviewed=args.reviewed,
                bands=args.bands,
            )
        if args.command == "adopt":
            return cmd_adopt(
                args.target,
                args.include_claude,
                wire_enforcement=args.wire_enforcement,
                lane=args.lane,
            )
        if args.command == "upgrade":
            return cmd_upgrade(
                args.target,
                apply_docs=args.apply_docs,
                rollback=args.rollback,
                release_json=args.release_json,
                keep_inputs=args.keep_inputs,
            )
        if args.command == "contextpack":
            return cmd_contextpack(args.target, args.index)
        if args.command == "session-start":
            return cmd_session_start(args.target)
        if args.command == "session-close":
            return cmd_session_close(args.target)
        if args.command == "draft":
            return cmd_draft(args.target)
        if args.command == "friction":
            return cmd_friction(
                args.target,
                args.action,
                repo=args.repo,
                name=args.name,
            )
        if args.command == "ledger":
            return cmd_ledger(
                args.target,
                title=args.title,
                verdict=args.verdict,
                why=args.why,
                provenance=args.provenance,
                supersedes=args.supersedes,
            )
    except UnsafeTargetError as exc:
        _emit(f"refused: {exc}")
        return 2
    parser.print_help()
    return 0

_TEMPLATES = {
    'AGENT_ORIENTATION.md.tmpl': '# ${project_name} — agent orientation & reading order\n\n> **Status:** `reference`\n>\n> Generated by substrate-kit. The task reading-router: start here to find which\n> docs a given task needs. **NOT SOURCE OF TRUTH** — the binding contracts win.\n\n## Start every session\n\n1. `.claude/CLAUDE.md` — the working agreement.\n2. `docs/current-state.md` — the living status ledger.\n3. `docs/CAPABILITIES.md` — verified session capabilities & walls (the\n   discovery rule lives there; append what you learn).\n4. This file — task-specific reading routes.\n\n## Binding contracts\n\n- **Architecture / layering:** ${architecture_layers}\n- **Ownership** (who owns each write path): ${ownership_model}\n- **Mutation seam** (how writes are gated): ${mutation_seam}\n\n## Where things live\n\nDocumentation root(s): ${doc_roots}\n\nThe planted doc set (this router reaches every live doc — keep it that way):\n`docs/architecture.md` · `docs/ownership.md` · `docs/runtime_contracts.md` ·\n`docs/collaboration-model.md` · `docs/helper-policy.md` ·\n`docs/repo-navigation-map.md` · `docs/ai-project-workflow.md` ·\n`docs/owner-profile.md` · `docs/current-state.md` · `docs/decisions.md` ·\n`docs/question-router.md` · `docs/CAPABILITIES.md` · `docs/ideas/README.md` — plus the root\n`CONSTITUTION.md` (the working agreement) and `.session-journal.md`.\n\n## Verifying any change\n\n```\n${verify_command}\n```\n',
    'CAPABILITIES.md.tmpl': '# ${project_name} — session capabilities & walls\n\n> **Status:** `living-ledger`\n>\n> Generated by substrate-kit. What agent sessions in THIS environment can and\n> cannot do — **verified findings, never assumptions**. Read at session start\n> (it is in the orientation reading order); append at session close. Fleet\n> master copy: `menno420/fleet-manager` → `docs/capabilities.md` — sync new\n> fleet-wide findings there via the manager when cross-repo access allows.\n\n## Why this file exists\n\nSessions repeatedly fail to discover what they CAN do (claiming `.mp4`s\nunviewable though ffmpeg frame-extraction is standard; forgetting provisioned\nenv tokens exist) and stall on imagined walls — burning owner attention as\nhand reminders. This ledger makes capability knowledge durable across\nsessions: one session\'s discovery is every later session\'s starting fact.\n\n## THE DISCOVERY RULE\n\nBefore declaring anything impossible, and before assuming a tool or\ncredential is missing:\n\n1. **Check this file** — the capability or wall may already be recorded.\n2. **Check the environment** — `printenv` / list the available tools BEFORE\n   assuming no credentials exist (provisioned env tokens are routinely\n   forgotten, not absent).\n3. **Attempt once** — try the operation and capture the **exact** error text;\n   a guessed wall and a verified wall are different facts.\n4. **Append the finding same session** — capability or wall, dated, with the\n   evidence (exact error, or proof it worked) and the workaround if one was\n   found. An unrecorded discovery is re-paid by every future session.\n\n## Capabilities — verified working\n\n- **Media is readable**: a video is never "unviewable" — extract frames\n  (`ffmpeg -i in.mp4 -vf fps=1 frame_%04d.png`) and read the images; same\n  idea for audio (transcribe) and PDFs (render pages). Try the recipe before\n  reporting a format wall.\n- **Provisioned credentials**: the environment often carries tokens/keys as\n  env vars — `printenv` first; a missing-looking credential is usually a\n  missing *look*.\n- **Release cutting despite the tag wall**: `workflow_dispatch` on the\n  release workflow (with a version input) creates the tag in-Actions —\n  proven repeatedly fleet-wide after direct tag pushes 403\'d.\n\n## Walls — verified blocked (use the workaround; don\'t rediscover)\n\n- **Tag push / release create via git**: HTTP 403 from the environment\'s git\n  proxy → use the workflow_dispatch release path.\n- **Branch deletion**: 403 on every path (git push `:branch` and API) →\n  owner deletes by hand / enables "Automatically delete head branches".\n- **`api.github.com` direct HTTP**: blocked → GitHub access is MCP-tools-only.\n- **Environment / routine / Project creation**: owner-click actions in the\n  console — queue them under `⚑ needs-owner`, never wait silently.\n- **Self-merge classifier**: sessions can be refused merging owner-gated PRs\n  while their other capabilities work — and the boundary differs by session\n  kind (a child session was refused where a coordinator was not). Record\n  which kind of session hit which boundary.\n- **GraphQL API quota**: tight — batch queries and prefer the REST-backed\n  MCP tools for bulk reads.\n\n## Append log — newest first\n\nFormat: `- YYYY-MM-DD · capability|wall · finding · evidence · workaround`.\n\n(Hand-filled by sessions, per the discovery rule. Seed walls/capabilities\nabove came from the fleet\'s lived 2026-07 findings; local ones go here.)\n',
    'CLAUDE.md.tmpl': '# ${project_name} — agent working agreement\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit from the staged interview. **NOT SOURCE OF TRUTH**\n> for code — source files always win. Re-render (`bootstrap render`) after the\n> interview fills more slots.\n\n## What this project is\n\n${project_name} is built in ${primary_language}.\n\n## Orientation — read first, in order\n\n1. This file — the working agreement.\n2. `docs/current-state.md` — what is true right now.\n3. `docs/CAPABILITIES.md` — what sessions here CAN and CANNOT do (verified).\n   Never declare a wall or a missing credential without its discovery rule:\n   check the file → check the env → attempt once + capture the exact error →\n   append the finding same session.\n4. `docs/AGENT_ORIENTATION.md` — the task-specific reading router.\n\n## Architecture — layers & import rules\n\n${architecture_layers}\n\n## Verifying a change\n\nRun before every push:\n\n```\n${verify_command}\n```\n\n## How the maintainer works\n\n${owner_profile}\n\n## Workflow adoption\n\nCurrent adoption pace for the substrate workflow: **${integration_mode}**.\n',
    'CONSTITUTION.md.tmpl': "# ${project_name} — constitution\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. The working agreement + autonomy rails. **NOT\n> SOURCE OF TRUTH** for code — source files always win. Rules state their\n> **current value only**; provenance lives in `docs/decisions.md` as [D-NNNN]\n> links and is never narrated inline.\n\n## Working agreement\n\n- **The goal comes first.** Achieve the session's goal end-to-end; don't ship\n  the smallest safe slice.\n- **Session prompts are guidance, not orders.** Weigh every prompt (and every\n  cross-agent report) against source and the binding docs before acting.\n- **Approved plan = execute.** Once a plan is approved, finish it in the same\n  session, with the planning context still loaded — no re-confirming.\n- **Understand-and-reflect.** The owner often hands over a rough fragment, not\n  a full spec — and sometimes doesn't know yet if the idea is even possible.\n  Before substantive work, restate the fuller picture built from the ask —\n  the specs it implied but didn't state, and, when feasibility is uncertain,\n  the possibility space — inline in the first substantive response, never as\n  a separate blocking question. Two payoffs, not one: it catches a misread\n  before work happens, and the filled-in picture is itself new material the\n  owner reasons against and redirects.\n- **Capabilities are discovered, never assumed.** `docs/CAPABILITIES.md` is\n  the verified ledger of what sessions here can and cannot do — read it at\n  session start. Before declaring a wall or a missing credential: check that\n  file → check the environment (`printenv`, tool lists) → attempt once and\n  capture the exact error → append the finding same session. An imagined\n  wall stalls the session; an unrecorded real one taxes every later session.\n- When a doc and a source file disagree: ${drift_resolution}\n\n## Autonomy rails — act vs. ask\n\n- **Act** on contained, reversible, verifiable changes — including a\n  root-cause fix discovered mid-task.\n- **Ask** before anything irreversible (data loss, external publish),\n  large / cross-cutting (architectural), or when the goal itself is\n  genuinely ambiguous. No live owner to ask? Record the question in\n  `docs/question-router.md` instead of skipping it or guessing.\n- **Owner attention is the scarcest resource.** Before routing anything to\n  the owner: attempt it yourself, or cite the exact wall (the\n  `docs/CAPABILITIES.md` discipline) — assumption-based asks are banned.\n  Every ask carries the OWNER-ACTION fields — WHAT / WHERE / HOW /\n  WHY-IT-MATTERS / UNBLOCKS / VERIFIED-NEEDED (format:\n  `control/README.md`) — phrased so a non-technical owner can act on it\n  directly. Expire stale asks; fewer, clearer asks beat complete lists.\n\n## Changing the rules — propose, don't apply\n\n- A binding rule in this file changes by **proposal**, never by silent edit:\n  record the decision in `docs/decisions.md`, cite it here as its [D-NNNN]\n  id, and let the owner (or the review ritual) confirm before the rule text\n  changes.\n- Every rule change ships with its provenance id. This file carries **no\n  history** — the ledger does; superseded rules are looked up there.\n\n## Program law\n\nRulings that bind **every** repo in this program live canonically in the\nsubstrate-kit repo at `docs/program/rulings.md` — the [PL-NNN] register\n(https://github.com/menno420/substrate-kit/blob/main/docs/program/rulings.md):\nPL-001 decide-and-flag · PL-002 never-wait rebuild autonomy · PL-003\nrail-before-scale · PL-004 empirical model allocation · PL-005 observe-first\nbudgets · PL-006 source-wins / false-green · PL-007 enforce-don't-exhort ·\nPL-008 adopt-freely with a kill-switch · PL-009 the kit-lab's rails.\n**Cite PL-IDs — never copy ruling bodies into this repo.** The register is\nthe one home; a local copy is drift by construction. Repo-local rulings stay\nin `docs/decisions.md` / `docs/question-router.md`; a local ruling promoted\nprogram-wide becomes a PL-block there and a pointer here.\n\n## Rails specific to ${project_name}\n\n(Hand-filled: the project's own hard rules, one bullet each, each citing its\n[D-NNNN]. Keep the whole hand-filled file under 150 lines.)\n",
    'ai-project-workflow.md.tmpl': "# ${project_name} — AI project workflow\n\n> **Status:** `reference`\n>\n> Generated by substrate-kit. The multi-agent pipeline: how ideas become work\n> and how sessions run. **NOT SOURCE OF TRUTH** — the binding contracts win.\n\n## Idea lifecycle\n\n```\ncaptured -> classified -> planned -> built -> verified\n```\n\nEvery idea ends implemented, planned, in discussion, or explicitly rejected —\nnever orphaned. Backlog + routing: `docs/ideas/README.md`.\n\n## Session workflow\n\n```\norient -> claim -> born-red card -> build -> verify -> close\n```\n\n1. **Orient** — working agreement, current state, task-specific reading route.\n2. **Claim** — declare your lane so parallel sessions don't collide.\n3. **Born-red card** — open the session record first, marked in-progress, so\n   the work is visible while it is still incomplete.\n4. **Build** — the goal, end-to-end.\n5. **Verify** — run `${verify_command}` before shipping.\n6. **Close** — flip the card complete; log the session, groom one idea, hand\n   off.\n\n## Handoff template\n\n(What the next session needs, four lines: state of the work · what is\nverified · what is still open · the first next step.)\n\n## Adoption pace\n\nCurrent substrate-workflow adoption: **${integration_mode}**.\n",
    'architecture.md.tmpl': '# ${project_name} — architecture\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. Layering, invariants, and decomposition rules.\n> **NOT SOURCE OF TRUTH** for code — source files always win.\n\n## Layers & import rules\n\n${architecture_layers}\n\n| Layer | May import | Must NOT import |\n|---|---|---|\n| (one row per layer, expanded from the summary above) | | |\n\n## Invariants\n\n(The rules that must survive every refactor — write each one as a testable\nstatement, and name the check that enforces it where one exists.)\n\n## Namespace protection — two mechanisms, both required\n\nTwo separate mechanisms guard the namespace, and they catch different\nfailure classes:\n\n1. **A registry for runtime string identities** — event names, command\n   names, settings keys, and any other string that selects behavior at\n   runtime. Collisions here are invisible to static analysis.\n2. **A static AST pass for Python symbol shadowing** — a later top-level\n   `def` / `class` with the same name silently shadows the earlier one, and\n   no import fails.\n\nNeither mechanism subsumes the other. The registry cannot see symbol\nshadowing; the AST pass cannot see string-keyed dispatch. Do not delete one\nbelieving the other covers it.\n\n## Verifying a change\n\n```\n${verify_command}\n```\n',
    'collaboration-model.md.tmpl': "# ${project_name} — collaboration model\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. How the owner and agents work together. **NOT\n> SOURCE OF TRUTH** for code — source files always win.\n\n## The model\n\n- **Goal first.** The owner designs and directs; agents build. Each session\n  achieves its goal end-to-end — not the smallest safe slice.\n- **Session prompts are guidance, not orders.** Weigh every prompt (and every\n  cross-agent report) against source and the binding docs before acting; a\n  prompt is one input, never a command list.\n- **Approved plan = execute.** Once a plan is approved, finish it in the same\n  session, with the planning context still loaded — code, verify, ship —\n  without re-confirming.\n\n## Act vs. ask\n\n- **Act** on contained, reversible, verifiable changes — including a\n  root-cause fix discovered mid-task (that is expected, not scope creep).\n- **Ask** when the change is irreversible (data loss / external publish),\n  large and cross-cutting (architectural), or the goal itself is genuinely\n  ambiguous.\n\n## Routing work to the owner\n\nThe owner is the scarcest resource in the program. An ask reaches the owner\nonly when the agent has **attempted the action itself** or can name the\n**exact wall** (error text, permission denial) proving only the owner can do\nit — assumption-based asks are banned. Every ask uses the OWNER-ACTION\nformat — WHAT / WHERE / HOW / WHY-IT-MATTERS / UNBLOCKS / VERIFIED-NEEDED\n(canonical: `control/README.md`) — phrased so a non-technical owner can act\ndirectly: one plain sentence, an exact click path, paste-ready text.\nWithdraw asks that have gone stale; fewer, clearer asks beat complete lists.\n\n## Friction → guard\n\nAnything that interrupts a session's workflow — a stale file, a checker that\nlied, a footgun — is converted into the **cheapest enforcing prevention**\nbefore the session ends: checker / CI / test first, then hook, then written\nrule. Enforce, don't exhort.\n\n## Guiding questions\n\nDuring exploratory / brainstorming work, surface the single most useful\nquestion about the owner's idea that the agent genuinely cannot derive\nitself — rare and selective, never during routine execution, and only when\nthe answer would actually matter and be actionable. A big or vague idea\nearns a dedicated research pass or its own session before being answered\nfrom memory alone.\n\n## Program law\n\nThis model's program-wide form, and the rulings that bind every repo in the\nprogram, live canonically in the substrate-kit repo at\n`docs/program/rulings.md` (the [PL-NNN] register — e.g. PL-001\ndecide-and-flag, PL-002 never-wait, PL-007 enforce-don't-exhort) and\n`docs/program/collaboration-model.md`\n(https://github.com/menno420/substrate-kit/tree/main/docs/program).\n**Cite PL-IDs — never copy ruling bodies into this repo.**\n\n## Drift & staleness\n\n- When a doc and a source file disagree: ${drift_resolution}\n- Staleness review cadence: ${staleness_review}\n",
    'control-README.md.tmpl': '# Fleet coordination protocol — `control/`\n\n> **Status:** `binding`\n>\n> Local copy for ${project_name}. Canonical spec: `menno420/superbot` →\n> `docs/planning/fleet-coordination-protocol-2026-07-09.md` (§1). Projects cannot talk to each\n> other directly — committed git files are the only shared medium; this directory is the bus.\n\n## The two files\n\n- `control/inbox.md` — ORDERS to this Project. **One writer: the manager** (appends via the\n  GitHub Contents API). Never edit this file.\n- `control/status.md` — STATE from this Project. **One writer: this Project** (overwrite it each\n  session).\n\n## The one rule that keeps it conflict-free\n\n**One writer per file.** The manager is the sole writer of `inbox.md`; this Project is the sole\nwriter of its own `status.md`. Two writers never touch the same file, so there are no merge\nconflicts. Everything is append-only / overwrite-own — forward-only git.\n\n## Multi-Project repos — per-lane heartbeats (optional extension)\n\nA SHARED repo can host several Projects ("lanes" — e.g. a mining lane and an exploration lane\ncohabiting one game repo). The one-writer rule scales by **splitting the heartbeat, never by\nsharing it**:\n\n- **One status file per lane** — `control/status-<lane>.md` (e.g. `control/status-mining.md` +\n  `control/status-exploration.md`). Each lane is the sole writer of its own file and overwrites\n  it as its session\'s deliberate LAST step; no lane ever edits another lane\'s heartbeat.\n- **`control/inbox.md` stays single** — the manager remains its one writer; a lane-specific\n  order names its lane in `do:`.\n- **Declare every lane heartbeat to the kit** — `substrate.config.json` →\n  `"heartbeat_files": ["control/status-mining.md", "control/status-exploration.md"]` (default\n  when unset: `["control/status.md"]`). The status checker then gates each listed file\n  independently (missing / heartbeat-less lane = strict RED; per-lane staleness warns), and the\n  Stop hook\'s overwrite reminder clears when any lane\'s heartbeat is fresh (it cannot know which\n  lane a session belongs to). An empty list falls back to the default — misconfiguration never\n  silently disables the gate.\n- **One command, not hand-edits** — a Project joining a SHARED repo runs\n  `bootstrap adopt --lane <name>`: it plants `control/status-<name>.md` (skip-if-exists),\n  declares it in `heartbeat_files`, and leaves `inbox.md`/`README.md` single — a second lane\n  never re-plants the first Project\'s files (the double-adoption fix).\n\n## Per-session ritual (every session, and every routine wake)\n\n- **FIRST:** git pull (a stale clone reads stale orders); read `control/inbox.md`; execute any\n  order whose status is `new`, in priority order (P0 before P1) — **claim it first** (see\n  "Claiming an order" below). An order\'s `do:` is a pointer to\n  a committed doc — read it. If an order is ambiguous or you disagree, do NOT guess: write it in\n  your status under `⚑ needs-owner` and proceed with the rest.\n- **LAST (deliberate final step):** overwrite `control/status.md` — updated timestamp, current\n  phase, health (green / red-by-design+why / broken+what), last-shipped PR, blockers, orders\n  acked/done, `⚑ needs-owner`. You report order progress ONLY here; never edit `inbox.md`\n  (the manager owns it — one writer per file).\n\nThe kit enforces this loop: `check` flags a missing or heartbeat-less `status.md`\n(strict = red), warns when the heartbeat goes stale, and the Stop hook reminds you when\n`status.md` was not overwritten this session.\n\n## Claiming an order — one executor per order (claim FIRST, build second)\n\nAn order\'s `status: new` is visible to every session that wakes, so two readers can both\nbelieve they are its executor — a realized failure, not a theoretical one (substrate-kit\nPRs #50/#51: two lanes independently executed the same ORDER 005 the same day, and a whole\nsession\'s work had to be reconciled as twins). The manager only flips `new→done` after\nseeing the status report; the claim covers the gap in between.\n\nBefore executing any `new` order:\n\n1. **Re-read the bus at origin/main HEAD** — `control/inbox.md` AND every sibling status\n   file (`control/status*.md`). If another lane\'s status already claims the order\n   (`claimed-by:` naming its id) or reports it in `done=`, stand down and pick other work.\n2. **Claim FIRST, on your own status file\'s orders line** — append\n   `claimed-by: <order-ids> <lane-or-session> <ISO8601>` — and land it on **main** BEFORE\n   any build work (a control-only fast-lane PR, or a direct commit where your rules allow\n   one). A claim that exists only on a branch is invisible; only main counts.\n3. **Re-read once more after the claim merges** — two claims can race in flight; the\n   tiebreak is the earliest claim merged to main. The loser withdraws its claim line in\n   its next status overwrite and stands down.\n4. **Claims expire** — a claim with no visible build activity (no open PR, no fresh\n   heartbeat referencing the order) after ~24h may be treated as abandoned and re-claimed;\n   note the takeover in your status `notes:`. A dead lane must never deadlock an order.\n\nWith an active claim the `orders:` line reads e.g.:\n`orders: acked=001-008 done=001-006 claimed-by: 007+008 coordinator-lane 2026-07-09T18:38Z`\n— the executor drops the `claimed-by:` annotation in the overwrite that moves those ids\ninto `done=`. One writer per file is preserved: you only ever claim on your OWN status.\n(Shipped by inbox ORDER 007 — the root-cause fix for the twin-execution failure; the\nritual was live-proven manually on this repo\'s own orders before graduating here.)\n\n## `status.md` format (what you write every session — your heartbeat)\n\n```markdown\n# <project> · status\nupdated: <ISO8601>            # heartbeat — stale = the manager treats the Project as dark\nphase: <what I\'m doing right now, one line>\nhealth: green | red-by-design (<why>) | broken (<what>)\nkit: v<X.Y.Z> · check: green|red · engaged: yes|no   # kit self-report — see below\nlast-shipped: #<PR> — <one line>\nblockers: <what\'s stopping me, or `none`>\norders: acked=<ids> done=<ids> [claimed-by: <ids> <lane-or-session> <ISO8601>]\n⚑ needs-owner: <a decision/action only the owner can give, or `none`>\nnotes: <anything the manager should know>\n```\n\nThe `kit:` line is the **substrate-coordinator visibility** channel (kit-lab reads it via the\nmanager relay — zero write access to this repo): `v<X.Y.Z>` = the vendored kit version this\nrepo actually runs (update it in the same session as every `bootstrap upgrade`); `check:` =\nthe latest `check --strict` verdict on this tree; `engaged:` = the post-adopt engagement gate\n(`yes` once no UNRENDERED banner/slot remains, live CI runs the gate, and the session loop\nhas engaged).\n\n## ⚑ needs-owner — the OWNER-ACTION item format (quality contract)\n\nThe owner is the scarcest resource in the program: every ask routed to the owner costs\nattention, and an unclear or unnecessary ask stalls your own lane on top of burning his.\n**Before routing ANYTHING to the owner, try it yourself or cite the exact wall** — an\nassumption-based ask ("agents probably can\'t do X") is banned; the bar is the capability\nledger (`docs/CAPABILITIES.md`) plus one real attempt with the captured error.\n\nEvery ⚑ needs-owner item carries ALL of these REQUIRED fields — inline on the item, or as a\nstructured block the item links to:\n\n```markdown\n⚑ OWNER-ACTION\nWHAT: <one plain sentence, zero jargon — the thing the owner does>\nWHERE: <exact click path or URL>\nHOW: <paste-ready text/values where applicable, or "click only">\nWHY-IT-MATTERS: <one sentence, in product terms>\nUNBLOCKS: <what starts moving the moment it\'s done>\nVERIFIED-NEEDED: <the attempt you made + the exact error/wall proving only the owner can do\nthis — never an assumption>\n```\n\nHygiene: **expire or withdraw stale asks every session** (an answered or obsolete ask left in\nthe list is drift), and **fewer, clearer asks beat complete lists**. `check` warns — advisory,\nnever exit-affecting — when a non-`none` ⚑ needs-owner list lacks these fields.\n\n## `inbox.md` order format (manager-written, append-only)\n\n```markdown\n## ORDER <nnn> · <ISO8601> · status: new     # manager flips new→done after seeing status done=\npriority: P0 | P1 | P2\ndo: <pointer to a committed doc/section + the ask, kept short>\nwhy: <one line>\ndone-when: <acceptance test>\n```\n\n## CI + auto-merge notes (learned live, 2026-07-09)\n\n- **Heartbeat commits ride a fast lane, not a `paths-ignore`.** A control-only diff (only\n  `control/**` files changed) must still *report* every required status check, or GitHub treats\n  the missing contexts as pending and auto-merge jams forever. The kit\'s planted\n  `substrate-gate.yml` therefore short-circuits GREEN inside the job on control-only diffs\n  instead of skipping the workflow — copy that pattern (an in-job early exit) into any other\n  heavy suite rather than adding `paths-ignore: [control/**]` to a workflow whose check is\n  required.\n- **API-authored PRs may not trigger CI.** A PR created purely through an app/integration token\n  (e.g. the GitHub Contents API + a REST PR create) can sit with **zero check runs** — required\n  checks then never report and the PR cannot auto-merge. The manager\'s canonical write path is\n  therefore a **direct Contents-API commit to the default branch of `inbox.md`** (it is the sole\n  writer, so no PR is needed). When this Project ships control changes by PR, push the branch\n  over git (a real `git push` triggers `pull_request`/`push` events) before or after creating\n  the PR, and verify the PR shows check runs before relying on auto-merge.\n',
    'control-inbox.md.tmpl': '# ${project_name} · inbox\n\n> ORDERS to this Project. **ONE writer: the manager** — never edit this file. Report order\n> progress in `control/status.md` (`orders: acked=… done=…`). Protocol: `control/README.md`.\n\n*(no orders yet — the manager appends `## ORDER 001 · <ISO8601> · status: new` blocks here)*\n',
    'control-status.md.tmpl': '# ${project_name} · status\nupdated: (seeded at adopt — no real heartbeat yet: overwrite this whole file at your first session close)\nphase: adopted — first session not yet run\nhealth: green\nkit: v${kit_version} · check: red · engaged: no\nlast-shipped: none\nblockers: none\norders: acked= done=\n⚑ needs-owner: none\nnotes: seeded skeleton planted by substrate-kit adopt. This Project is the SOLE writer of this\nfile — overwrite it (never append) as the deliberate LAST step of every session, per\n`control/README.md`. `check` holds strict RED until the first real heartbeat replaces this seed.\nThe `kit:` line is your kit self-report (substrate-coordinator visibility): keep the version in\nsync with your vendored kit on every upgrade, `check:` = your last `check --strict` verdict,\n`engaged:` = the post-adopt engagement gate (yes once `check` reports ENGAGED/green live CI).\n',
    'current-state.md.tmpl': '# ${project_name} — Current State\n\n> **Status:** `living-ledger`\n>\n> Generated by substrate-kit. **Living status ledger.** Source code and merged\n> work always win over this file. Read it second (right after the working\n> agreement) and keep it current as the project moves.\n\n## Stability baseline\n\n(Describe the accepted-stable baseline once established — what is known-good and\nshould not be re-audited without a reported regression.)\n\n## In flight\n\n(Verify against live source control — this section is a dated snapshot.)\n\n## Recently shipped (newest first)\n\n(Merged work only, newest first.)\n\n## Review rhythm\n\n${review_ritual}\n',
    'decisions.md.tmpl': '# ${project_name} — decisions\n\n> **Status:** `living-ledger`\n>\n> Generated by substrate-kit. Append-only decision ledger — entries are\n> superseded, never deleted. Rule docs cite entries as bare [D-NNNN] ids;\n> this file holds the provenance so rules never narrate it inline.\n\n<!-- Grammar: ## [D-NNNN] <title> / - status: decided|superseded|retired / - date: YYYY-MM-DD / - supersedes: D-NNNN (opt) / - superseded-by: D-NNNN (opt) / - verdict: <one line> / - why: <2-3 lines> / - provenance: <ref> -->\n\n## [D-0001] Adopt the substrate-kit workflow\n\n- status: decided\n- date:\n- verdict: ${project_name} runs on the substrate-kit agent workflow.\n- why: A repo-resident working agreement, decision ledger, and session\n  discipline let agents work correctly with little steering; adopting the\n  kit starts ${project_name} governed instead of accreting rules ad hoc.\n- provenance: substrate-kit adoption interview\n',
    'helper-policy.md.tmpl': '# ${project_name} — helper policy\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. When to create / move / promote a helper —\n> read this **before** adding a utility function anywhere. **NOT SOURCE OF\n> TRUTH** for code — source files always win.\n\n## Rules\n\n1. **One source of truth.** A behavior lives in exactly one function. Never\n   copy a helper into a second module "for convenience" — import it, or move\n   it (rule 2).\n2. **Shared helpers live below both consumers.** A helper needed by two\n   layers goes in the shared layer *below* both — never in either consumer\n   layer, and never duplicated into each.\n3. **Exact-name guard.** Before defining a new function, grep for\n   `def <exact_name>` in the target module and its siblings (plus the 1–2\n   nearest concept synonyms). A later same-name `def` silently shadows the\n   earlier one — no import fails, no warning fires.\n4. **Promote on second use.** The moment a private helper is wanted by a\n   second module, promote it to the shared layer — don\'t copy it.\n\n## Where helpers go in ${project_name}\n\n(Hand-filled: the concrete shared-layer path(s) for this repo, lowest layer\nfirst, with one line on what belongs in each.)\n',
    'ideas-README.md.tmpl': '# ${project_name} — idea backlog & lifecycle\n\n> **Status:** `ideas`\n>\n> Generated by substrate-kit. Capture ideas here so they live in the repo, not in\n> chat. Nothing here is approved until it graduates. A **conveyor, not a graveyard**:\n> every idea ends implemented, on a roadmap, in discussion, or explicitly rejected.\n\n## Lifecycle\n\n```\n(1) INTAKE   capture the idea (raw -> captured)\n(2) MAP      name the owning area, rough size, rough risk\n(3) ROUTE    -> quick-win | structured plan | discuss-first (question router)\n(4) GROOM    pull one routable idea forward each session\n(5) OUTCOME  implemented | on a roadmap | in discussion | rejected\n```\n\n## Frontmatter — the idea-outcome record\n\nEvery idea file in this directory (README excepted) opens with a flat\nYAML-subset frontmatter block — the machine-readable outcome record\n("ideas that ship and survive"), so a sweep can score the backlog without\nparsing prose:\n\n```\n---\nstate: captured | routed | promoted | historical\norigin: lab | owner | consumer:<owner>/<repo>\nshipped_pr: null | <PR number in shipped_repo>\nshipped_repo: null | <owner>/<repo>\nmerged_date: null | YYYY-MM-DD\noutcome: open | shipped | survived | reverted | rejected\n---\n```\n\nConventions: `shipped`/`survived`/`reverted` require all three ship fields;\n`open`/`rejected` keep them null; `survived` means the merge is ≥ 30 days old\nwith no revert; name files `<slug>-YYYY-MM-DD.md` (the generation-date cohort\nkey) and link every file from this README. The prose keeps the story, the\nfrontmatter keeps the score.\n\n## Backlog\n\n(Captured ideas, each with a state and a next destination — none left at `raw`.)\n',
    'owner-profile.md.tmpl': "# ${project_name} — owner working profile\n\n> **Status:** `owner-guidance`\n>\n> Generated by substrate-kit. Captures the owner's **working style** so\n> agents collaborate well — never personal data. The person is not shipped\n> with the kit.\n\n## How the owner works\n\n${owner_profile}\n\n## Review ritual\n\n${review_ritual}\n\n## Privacy note\n\nThis doc records working style only: communication preferences, review\ncadence, decision boundaries, autonomy expectations. No contact details, no\npersonal history, nothing that identifies the person beyond their role on\n${project_name}. When in doubt, leave it out.\n",
    'ownership.md.tmpl': "# ${project_name} — ownership\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. Which area / service / pipeline owns each\n> table, event, and write path. **NOT SOURCE OF TRUTH** for code — source\n> files always win.\n\n> **Steady state:** this doc's table is **generated** from store / manifest\n> specs where those exist — a projection, not hand-prose. This skeleton is\n> the interim hand-maintained form until that projection lands.\n\n## Ownership model\n\n${ownership_model}\n\n## Ownership table\n\n| Area | Owner (module / service) | Writes it owns | Notes |\n|---|---|---|---|\n| (one row per owned area) | | | |\n\n## New areas\n\n${new_area_ownership}\n",
    'question-router.md.tmpl': '# ${project_name} — maintainer question router\n\n> **Status:** `owner-guidance`\n>\n> Generated by substrate-kit. Append-only `## Q-NNNN` blocks capture owner-intent\n> decisions and open questions. The interview writes here; confirmed answers route\n> into the durable docs. **Append only** (next free Q-number) — never rewrite history.\n> Any session may append a block, not only the interview — including an unattended\n> run that hits a genuinely useful, non-derivable question with no live owner to ask.\n\n## Block format\n\n```\n## Q-0001\n- **Area / Type / Priority / Status:** ...\n- **Question:** ...\n- **Why agents need this:** ...\n- **Options:** ...\n- **Safe default:** ...\n- **Maintainer answer:** (verbatim)\n- **Routing result:** (which doc / slot the answer landed in)\n```\n\n## Open questions\n\n(Unanswered Q-blocks live here until the maintainer decides; a blocking one gates\ngraduation.)\n',
    'repo-navigation-map.md.tmpl': '# ${project_name} — repo navigation map\n\n> **Status:** `reference`\n>\n> Generated by substrate-kit. Where things live; where new code goes. **NOT\n> SOURCE OF TRUTH** — the tree itself wins.\n\n## Where things live\n\n| Path | What lives there | New code goes here when… |\n|---|---|---|\n| (one row per top-level area) | | |\n\n## Documentation roots\n\n${doc_roots}\n\n## Placement rule of thumb\n\nBefore creating a new file, find the row above that matches it; if no row\nmatches, the map is stale — extend the table in the same change.\n',
    'runtime_contracts.md.tmpl': '# ${project_name} — runtime contracts\n\n> **Status:** `binding`\n>\n> Generated by substrate-kit. Lifecycle guarantees and failure modes. **NOT\n> SOURCE OF TRUTH** for code — source files always win.\n\n## Lifecycle guarantees\n\n### Startup\n\n(What is guaranteed initialized before work begins, and in what order.)\n\n### Steady state\n\n(The invariants that hold while the system is running — connection health,\nqueue bounds, cache coherence.)\n\n### Shutdown\n\n(What is flushed / persisted / cancelled on the way down, and in what order.)\n\n## Mutation seam\n\n${mutation_seam}\n\n## Failure modes\n\n(For each subsystem: what failing looks like from the outside, the blast\nradius, and the recovery step. One subsection per subsystem.)\n',
    'session-journal.md.tmpl': "# ${project_name} — session journal (process memory)\n\n> **Status:** `reference`\n>\n> Generated by substrate-kit. Cross-session working memory — a **guidebook, not a\n> log**. Per-session logs live in `.sessions/<date>-<slug>.md` (newest first);\n> older history archives out. Keep THIS file lean.\n\n## ⚡ Quick reference\n\n(Boot / run-checks / common-recovery commands for ${project_name}.)\n\n## Environment & boot runbook\n\n(How to bring a working dev/test environment up.)\n\n## Recurring problems + fixes\n\n(Known traps and their resolutions — so the next session doesn't re-discover them.)\n\n## Past mistakes to avoid\n\n(Things that went wrong before; don't repeat them.)\n\n## Candidate rules (not yet promoted)\n\n(Proposed working-agreement rules awaiting owner review.)\n",
}

if __name__ == "__main__":
    raise SystemExit(main())
