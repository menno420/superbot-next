"""The `verified_live` record schema + registry semantics (V-5).

Schema = verification-review §3.3 (every named field carried), tiered per
A-18, with the verification requirement encoded per owner ruling Q-0244:

  - an AUTOMATED-tier record for a slash/component surface is VERIFIED only
    with BOTH `prefix_twin_live` and `pipeline_replay` evidence;
  - an AUTOMATED-tier prefix-command record needs `prefix_twin_live` (the
    lane-A live agent test) — parity replay evidence strengthens it;
  - a HUMAN_REQUIRED record needs a signer + `human_walk` (or owner
    judgment) evidence to be VERIFIED — and an UNVERIFIED human row is
    NEVER a gate failure: it flows to the debt list (A-18(3)/Q-0244:
    nothing in the human lane blocks CUT-3).

A VERIFIED record is a signed fact: signer, timestamp, build SHA, and at
least one evidence row are mandatory. Stdlib-only (yaml import is guarded
to the loader so the schema stays importable anywhere).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "verification" / "verified_live.yml"

__all__ = [
    "CutoverStatus",
    "EvidenceKind",
    "EvidenceRow",
    "REGISTRY_PATH",
    "Status",
    "SurfaceKind",
    "Tier",
    "VerifiedLiveRecord",
    "debt_list",
    "load_registry",
    "validate_record",
]


class SurfaceKind(enum.Enum):
    COMMAND = "command"          # prefix or slash (qualified name)
    PANEL = "panel"
    CUSTOM_ID = "custom_id"
    FLOW = "flow"                # a multi-surface scenario (Q-0234 walk)


class Tier(enum.Enum):
    """A-18: the ONE schema field that tiers the registry."""

    AUTOMATED = "automated"
    HUMAN_REQUIRED = "human_required"


class Status(enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"        # a one-way signed fact for a given build SHA
    DEBT = "debt"                # published on the CUT-2/CUT-3 debt list


class EvidenceKind(enum.Enum):
    PREFIX_TWIN_LIVE = "prefix_twin_live"    # lane-A live agent test (Q-0244)
    PIPELINE_REPLAY = "pipeline_replay"      # in-process pipeline-true replay
    PARITY_GOLDEN = "parity_golden"          # V-1 replay coverage citation
    HUMAN_WALK = "human_walk"                # the Q-0234 judgment walk
    OWNER_JUDGMENT = "owner_judgment"
    TRANSCRIPT = "transcript"
    SCREENSHOT_VIDEO = "screenshot_video"


class CutoverStatus(enum.Enum):
    PRE_CUT1 = "pre_cut1"
    CUT1 = "cut1"      # test-guild live boot
    CUT2 = "cut2"      # prod-data import window
    CUT3 = "cut3"      # token swap
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class EvidenceRow:
    kind: EvidenceKind
    link: str            # URL / transcript path / golden case id — never ""

    @classmethod
    def from_data(cls, data: dict) -> "EvidenceRow":
        return cls(kind=EvidenceKind(data["kind"]), link=str(data.get("link", "")))


@dataclass(frozen=True)
class VerifiedLiveRecord:
    """One §3.3 sign-off row."""

    record_id: str                       # unique, e.g. "economy.balance.slash"
    subsystem: str
    surface_kind: SurfaceKind            # command/panel/custom_id under test
    surface_id: str                      # qualified name / panel_id / custom_id
    tier: Tier                           # A-18
    scenario_steps: tuple[str, ...]      # §3.3 scenario steps
    expected_visible: str                # exact user-visible result
    expected_effects: tuple[str, ...]    # DB/audit/event effects
    status: Status = Status.UNVERIFIED
    test_guild: str = ""                 # §3.3 test guild/channel/persona
    test_channel: str = ""
    persona: str = ""
    signer: str = ""                     # owner/operator signer
    signed_at: str = ""                  # ISO timestamp
    build_sha: str = ""                  # build SHA / container image
    evidence: tuple[EvidenceRow, ...] = ()
    cutover_status: CutoverStatus = CutoverStatus.PRE_CUT1
    notes: str = ""

    @classmethod
    def from_data(cls, data: dict) -> "VerifiedLiveRecord":
        return cls(
            record_id=str(data["record_id"]),
            subsystem=str(data["subsystem"]),
            surface_kind=SurfaceKind(data["surface_kind"]),
            surface_id=str(data["surface_id"]),
            tier=Tier(data["tier"]),
            scenario_steps=tuple(str(s) for s in data.get("scenario_steps", ())),
            expected_visible=str(data.get("expected_visible", "")),
            expected_effects=tuple(str(e) for e in data.get("expected_effects", ())),
            status=Status(data.get("status", "unverified")),
            test_guild=str(data.get("test_guild", "")),
            test_channel=str(data.get("test_channel", "")),
            persona=str(data.get("persona", "")),
            signer=str(data.get("signer", "")),
            signed_at=str(data.get("signed_at", "")),
            build_sha=str(data.get("build_sha", "")),
            evidence=tuple(EvidenceRow.from_data(e) for e in data.get("evidence", ())),
            cutover_status=CutoverStatus(data.get("cutover_status", "pre_cut1")),
            notes=str(data.get("notes", "")),
        )


def _slash_or_component(record: VerifiedLiveRecord) -> bool:
    if record.surface_kind in (SurfaceKind.PANEL, SurfaceKind.CUSTOM_ID):
        return True
    return record.surface_kind is SurfaceKind.COMMAND and record.surface_id.startswith("/")


def validate_record(record: VerifiedLiveRecord) -> list[str]:
    """Schema + tier rules for ONE record. An UNVERIFIED record is always
    schema-valid (the debt-list model); VERIFIED is the gated transition."""
    problems: list[str] = []
    if not record.record_id or not record.subsystem or not record.surface_id:
        problems.append(f"{record.record_id or '?'}: record_id/subsystem/surface_id required")
    if not record.scenario_steps:
        problems.append(f"{record.record_id}: scenario_steps required (§3.3 — never a bare checkbox)")
    if not record.expected_visible:
        problems.append(f"{record.record_id}: expected_visible required")
    if record.status is not Status.VERIFIED:
        return problems

    # VERIFIED = a signed fact
    if not record.signer:
        problems.append(f"{record.record_id}: VERIFIED requires a signer")
    if not record.signed_at:
        problems.append(f"{record.record_id}: VERIFIED requires signed_at")
    if not record.build_sha:
        problems.append(f"{record.record_id}: VERIFIED requires build_sha (§3.3: tied to a build)")
    kinds = {e.kind for e in record.evidence}
    if not record.evidence or any(not e.link for e in record.evidence):
        problems.append(f"{record.record_id}: VERIFIED requires evidence rows with links")
    if record.tier is Tier.AUTOMATED:
        if _slash_or_component(record):
            required = {EvidenceKind.PREFIX_TWIN_LIVE, EvidenceKind.PIPELINE_REPLAY}
            if not required <= kinds:
                problems.append(
                    f"{record.record_id}: Q-0244 — a slash/component surface is "
                    f"verified by prefix-twin live pass + in-process "
                    f"pipeline-true replay (missing "
                    f"{sorted(k.value for k in required - kinds)})"
                )
        elif EvidenceKind.PREFIX_TWIN_LIVE not in kinds:
            problems.append(
                f"{record.record_id}: automated-tier prefix surface needs the "
                f"lane-A live agent test (prefix_twin_live evidence)"
            )
    else:
        if not (kinds & {EvidenceKind.HUMAN_WALK, EvidenceKind.OWNER_JUDGMENT}):
            problems.append(
                f"{record.record_id}: human_required tier verifies via a "
                f"human walk / owner judgment evidence row"
            )
    return problems


def debt_list(records: list[VerifiedLiveRecord]) -> list[VerifiedLiveRecord]:
    """The CUT-2/CUT-3 reaction-window publication (A-18(3), confirmed by
    Q-0244): unsigned/unverified HUMAN-tier rows + explicit DEBT rows.
    Published, never blocking, never silently dropped."""
    return [
        r for r in records
        if r.status is Status.DEBT
        or (r.tier is Tier.HUMAN_REQUIRED and r.status is not Status.VERIFIED)
    ]


def load_registry(path: Path | None = None) -> tuple[dict[str, str], list[VerifiedLiveRecord]]:
    """-> (subsystem dashboard map, record list)."""
    import yaml  # guarded to the loader: the schema stays stdlib-importable

    data = yaml.safe_load((path or REGISTRY_PATH).read_text())
    subsystems = {str(k): str(v) for k, v in (data.get("subsystems") or {}).items()}
    records = [VerifiedLiveRecord.from_data(r) for r in data.get("records") or []]
    return subsystems, records
