"""BTD6 guided CT-team flow (band 7) — the ORACLE
``disbot/services/btd6_ct_team_service.py`` +
``disbot/views/btd6/ct_group_flow.py`` @9c16365, focused port (curation
report 2026-07-13 row 2: ``btd6.ctteam.set_team`` REWORK — the
``btd6.ctteam_set_pending`` terminal retires here).

The decided shape (Settings Phase 2, Q-0064): **accept URL/ID → parse →
preview → confirm**, never a generic scalar text field. Entry points:

* ``!btd6 ctteam <url-or-id>`` — the parsed id goes straight to the
  preview+confirm step (no immediate write; ``clear`` stays immediate —
  reversible, nothing to preview);
* the ``btd6.ctteam`` panel's "Set CT team…" button — opens the G-10
  ``btd6.ctteam_set_form`` modal (the shipped ``CTGroupFlowModal``).

Both converge on the ``btd6.ctteam_confirm`` session page (the shipped
``CTGroupConfirmView``, author-locked 180s): Confirm commits ONE audited
write through the ``btd6.set_ct_team`` K7 op (legacy-KV
``guild_settings.btd6_ct_group_id`` — the ``btd6.set_announce_channel``
twin lane, key verbatim from utils/settings_keys/btd6.py), Cancel
discards. The Confirm leg re-checks authority at execution time (the
oracle's views rule) via the action's ``audience_tier="staff"`` two-lane
grammar + the op's staff authority floor — the cleanup policy_widgets
layering.

Deviations from the oracle, ledgered:

* the oracle EDITED the confirm message in place (buttons disabled,
  embed dropped); this engine answers the Confirm/Cancel click with the
  result reply and lets the session page expire — the cleanup
  policy-flow page-swap posture (same steps, same copy, ledgered idiom);
* the oracle's modal path sent the preview EPHEMERAL while the prefix
  path was public; the ``btd6.ctteam_confirm`` page presents on the
  engine's one panel visibility — both entries public, like the
  ``btd6.ctteam`` view itself (golden-UNPINNED path);
* the live bracket standings in the preview (``get_ct_bracket``) ride
  the NK ingestion successor (D-0046) — with no live-event source the
  oracle's own no-active-event branch renders ("No Contested Territory
  event is active right now."), which is also this build's true state.
  A pointer commit never required the NK API to be reachable (oracle
  module doc), so the flow arms whole without it.

Registered at MODULE IMPORT (the BUG A rule).
"""

from __future__ import annotations

import dataclasses
import logging
import re

from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)
from sb.spec.outcomes import BLOCKED, SUCCESS

logger = logging.getLogger("sb.domain.btd6.ct_team")

__all__ = [
    "ensure_ct_team_refs",
    "get_team_group_id",
    "parse_group_id",
]

#: the shipped legacy-KV settings key (utils/settings_keys/btd6.py
#: BTD6_CT_GROUP_ID, verbatim) — the write home is the audited
#: ``btd6.set_ct_team`` op leg (sb/domain/btd6/ops.py).
CT_GROUP_KEY = "btd6_ct_group_id"

# A Ninja Kiwi group id is a hex token (the live example is 42 chars).
# Accept a bare id or the tail of a full ``.../group/<id>`` URL; reject
# anything that is not a plausible hex token so a mis-paste fails loudly
# instead of being fetched as a bad path param. (Oracle constants,
# verbatim.)
_GROUP_ID_RE = re.compile(r"[0-9a-fA-F]{8,64}")
_GROUP_URL_MARKER = "/group/"

#: oracle copy, verbatim (CTGroupFlowModal.on_submit / handle_ctteam).
PARSE_REFUSAL = (
    "That doesn't look like a CT bracket id or group URL. Paste "
    "your team's `…/leaderboard/group/<id>` link or the bare id.")


def parse_group_id(raw: str) -> str | None:
    """Extract a bare group id from a pasted id or full group URL
    (oracle ``btd6_ct_team_service.parse_group_id``, verbatim).

    Returns the lower-cased hex id, or ``None`` when ``raw`` carries no
    plausible group token.
    """
    text = (raw or "").strip()
    if not text:
        return None
    # Full URL: take the segment after ``/group/``.
    if _GROUP_URL_MARKER in text:
        text = text.split(_GROUP_URL_MARKER, 1)[1]
    text = text.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    match = _GROUP_ID_RE.fullmatch(text)
    return match.group(0).lower() if match else None


async def get_team_group_id(guild_id: int) -> str:
    """The configured CT bracket id for ``guild_id`` (``""`` when unset)
    — READ-ONLY over the shipped legacy-KV ``guild_settings`` table (the
    ai review-channel read precedent)."""
    from sb.kernel.db.pool import fetchone

    row = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = $2",
        (int(guild_id), CT_GROUP_KEY))
    return "" if row is None else str(row["value"] or "")


async def team_group_id_or_empty(guild_id: int | None) -> str:
    """Presentation-lane read: ``""`` on any failure — rendering the
    CT-team view/preview must never require the DB (the oracle's own
    degrade posture: committing/previewing survives a fetch failure)."""
    if not guild_id:
        return ""
    try:
        return await get_team_group_id(int(guild_id))
    except Exception:  # noqa: BLE001 — presentation survives a read failure
        logger.warning("ct_team: settings read failed for guild=%s",
                       guild_id, exc_info=True)
        return ""


# --- handlers --------------------------------------------------------------------


async def _open_confirm(req, group_id: str) -> None:
    """Open the preview+confirm session page carrying the parsed id in
    the session args (the cleanup policy-flow state carrier)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(
        PanelRef("btd6.ctteam_confirm"),
        dataclasses.replace(
            req, args={**dict(req.args), "ct_group_id": group_id}))


async def ctteam_set_submit(req) -> Reply | None:
    """The shipped ``CTGroupFlowModal.on_submit``: parse the pasted
    URL/id, refuse the mis-paste (copy verbatim), else the preview+
    confirm step — never an immediate write."""
    if not req.guild_id:
        # defensive — the panel only opens in guilds (oracle DM guard).
        return Reply(BLOCKED, "Use this in a server, not a DM.")
    group_id = parse_group_id(str(req.args.get("raw") or ""))
    if group_id is None:
        return Reply(BLOCKED, PARSE_REFUSAL)
    await _open_confirm(req, group_id)
    return None


async def ctteam_confirm_submit(req) -> Reply:
    """The shipped ``CTGroupConfirmView.confirm``: re-validate, ONE
    audited write through the ``btd6.set_ct_team`` op, the shipped
    success byte. Authority re-checks at execution time (views rule) via
    the action's staff tier + the op's staff floor."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    group_id = parse_group_id(str(req.args.get("ct_group_id") or ""))
    if group_id is None:
        # the shipped defensive branch (parsed earlier) — also the guard
        # for a stale/foreign page open with bare args (cleanup posture).
        return Reply(BLOCKED,
                     "That bracket id no longer parses — nothing saved.")
    result = await engine.run(WorkflowRef("btd6.set_ct_team"),
                              _ctx_from_req(req, {"group_id": group_id}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message or "Couldn't update the CT team.")
    return Reply(SUCCESS, f"✅ CT team set to `{group_id}`.")


async def ctteam_cancel(req) -> Reply:
    """The shipped ``CTGroupConfirmView.cancel`` byte, verbatim."""
    return Reply(SUCCESS, "Cancelled — CT team unchanged.")


# --- registration — MODULE IMPORT (BUG A rule) -------------------------------------


_HANDLERS = (
    ("btd6.ctteam_set_submit", ctteam_set_submit),
    ("btd6.ctteam_confirm_submit", ctteam_confirm_submit),
    ("btd6.ctteam_cancel", ctteam_cancel),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def ensure_ct_team_refs() -> None:
    _register()


_register()
