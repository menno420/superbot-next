"""Cleanup-surface handlers — the ``!cleanuphistory`` scan front door,
the LIVE 🛡️ Anti-evasion toggle (the 2026-07-13 residue port: the
shipped ``btn_strict`` flow onto the audited
``cleanup.wordfilter_strict_op``), plus ONE declared + honest pending
terminal (the settings/servermanagement precedent, never a silent
stub): the Cleanup Policies sub-view — its own slice (the multi-view
diagnostics + presets-builder flow). The word add/remove modals, the
word-menu refresh, the Scan History button, the hub's Logging Status
nav AND the ⚙️ Settings page route to their LIVE targets in
sb/domain/cleanup/panels.py (the settings/anti-evasion terminals
retired with the residue port). Refs register at MODULE IMPORT (the
composition-parity invariant — the live root never runs ENSURE_REFS).

The scan (``cleanup.history_scan``) ports disbot/cogs/cleanup_cog.py
``cleanup_history``: ``!cleanuphistory [limit=100] [keyword]`` reads the
channel history through the domain history-reader port (the capture
twin records the goldens' ``logs_from`` wire verb), plans the matches,
and answers with the shipped summary copy —
goldens/cleanup/sweep_cleanuphistory.json pins the 0-match path
byte-for-byte ("Scanned 0 message(s) (requested 100, effective 100).
Matched 0 messages for `prohibited`."). The shipped helper deletions
(the invoking message + the 3s ``delete_after`` on the summary) are
reason-less ``delete_message`` calls — the ORDER-009
``invoking-message-deletion`` disposition class; v1 deliberately does
not delete. Deliberate under-ports (in-code notes below): the transient
⚠️ over-limit helper (``delete_after=7``), the non-``prohibited`` mode
matchers (an honest refusal when they would have had to run) and the
matched>0 deletion leg land with the channel-ops slice.
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]

#: the shipped cap (cleanup_cog.py MAX_CLEANUP_HISTORY_LIMIT).
MAX_HISTORY_LIMIT = 1000

#: the shipped mode vocabulary (cleanup_cog.py docstring: "Modes:
#: `keyword <text>` · `commands` · `prohibited` (default) · `spam` ·
#: `embeds` · `links` · `attachments`").
_MODES = frozenset(
    {"commands", "prohibited", "spam", "embeds", "links", "attachments"})

async def _refresh_words_panel(req) -> bool:
    """Best-effort in-place re-render of the words manager after the
    toggle's write settled (the shipped edit_message flow; the settings
    ca_mode / ai `_refresh_settings_page` posture)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        if not message_key:
            return False
        await refresh_session_view(req, message_key=message_key,
                                   params=dict(req.args or {}))
        return True
    except Exception:  # noqa: BLE001 — the text confirm degrade follows
        return False


def _parse_scan_args(argv: tuple) -> tuple[int, str]:
    """``!cleanuphistory [limit=100] [keyword...]`` → (requested_limit,
    mode). The shipped signature took ``limit: int = 100`` then a
    greedy keyword; a bare mode token selects that mode, anything else
    is a keyword search — only the no-arg default path is golden-pinned."""
    requested = 100
    rest = list(argv)
    if rest:
        try:
            requested = int(str(rest[0]))
            rest = rest[1:]
        except ValueError:
            pass                     # no leading int — everything is keyword
    keyword = " ".join(str(t) for t in rest).strip()
    if not keyword:
        mode = "prohibited"          # the shipped default
    elif keyword.lower() in _MODES:
        mode = keyword.lower()
    else:
        mode = "keyword"
    return requested, mode


def _register() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, handler, is_registered

    pending_handler("cleanup.policies_pending",
                    "🧹 The Cleanup Policies panel (diagnostics + presets "
                    "builder) ports with the cleanup-policy slice.")

    if not is_registered(HandlerRef("cleanup.anti_evasion_toggle")):

        @handler("cleanup.anti_evasion_toggle")
        async def anti_evasion_toggle(req) -> Reply | None:
            """🛡️ Anti-evasion (the words manager) — the shipped
            ``_WordMenuView.btn_strict`` flow: read the current strict
            flag, write the INVERSE on the audited
            ``cleanup.wordfilter_strict_op`` (the shipped
            ``prohibited_words_service.set_wordfilter_strict`` posture:
            one write + one audit row), then re-render the panel in
            place — the shipped view answered with the refreshed embed
            and NO ack text, so a successful refresh returns None; the
            text confirm is the degrade when the session view cannot be
            re-rendered (the settings ca_mode posture)."""
            from sb.domain.cleanup import store
            from sb.kernel.interaction.handler_kit import ctx_from_request
            from sb.kernel.workflow import engine
            from sb.spec.refs import WorkflowRef

            if not req.guild_id:
                return Reply(BLOCKED,
                             "❌ Anti-evasion matching can only be "
                             "configured inside a server.")
            try:
                current = await store.get_wordfilter_strict(int(req.guild_id))
            except Exception:  # noqa: BLE001 — no row/no DB = shipped off
                current = False
            new_value = not current
            result = await engine.run(
                WorkflowRef("cleanup.wordfilter_strict_op"),
                ctx_from_request(req, {"strict": new_value}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             "❌ Couldn't update anti-evasion matching: "
                             f"{result.user_message or 'write failed'}")
            if await _refresh_words_panel(req):
                return None
            return Reply(SUCCESS,
                         "🛡️ Anti-evasion matching → "
                         f"{'🟢 **On**' if new_value else '⚫ **Off**'}.")

    if is_registered(HandlerRef("cleanup.history_scan")):
        return

    @handler("cleanup.history_scan")
    async def history_scan(req) -> Reply:
        """``!cleanuphistory`` — the shipped channel-history scan
        (goldens/cleanup/sweep_cleanuphistory.json pins the 0-match
        summary; deliberate under-ports in the module docstring)."""
        from sb.domain.cleanup import service, store

        argv = tuple(req.args.get("argv", ()) or ())
        requested, mode = _parse_scan_args(argv)
        # the shipped clamp (cleanup_cog.py: min(requested, MAX); the
        # transient ⚠️ over-limit helper message rode delete_after=7 —
        # an under-port, channel-ops slice).
        effective = min(requested, MAX_HISTORY_LIMIT)
        try:
            messages = await service.read_history(
                int(req.channel_id or 0), limit=effective)
        except service.HistoryReaderNotInstalled:
            return Reply(BLOCKED,
                         "History sweeps aren't armed in this build yet — "
                         "the channel-ops port lands with the discord "
                         "adapter slice.")
        scanned = len(messages)
        if mode != "prohibited" and scanned:
            # only the prohibited matcher is ported (the shipped default
            # mode; the golden path). Reporting "Matched 0" for a mode
            # whose matcher never ran would be a silent under-port — the
            # declared + honest refusal instead (codex review, PR #140).
            return Reply(BLOCKED,
                         f"Scanned {scanned} message(s), but the `{mode}` "
                         "matcher ports with the channel-ops slice — only "
                         "`prohibited` sweeps are armed in this build.")
        matched = 0
        if mode == "prohibited" and messages:
            try:
                words = [w for w in
                         await store.get_words(int(req.guild_id or 0))]
            except Exception:  # noqa: BLE001 — headless read
                words = []
            for message in messages:
                content = str(getattr(message, "content", "") or "").lower()
                if any(w in content for w in words):
                    matched += 1
        if matched:
            # the shipped sweep DELETED the matched messages — that
            # Discord state-mutation leg is the channel-ops slice's port
            # (declared + honest refusal, never a silent partial sweep).
            return Reply(BLOCKED,
                         f"Matched {matched} of {scanned} scanned message(s) "
                         f"for `{mode}` — the deletion leg of the history "
                         "sweep ports with the channel-ops slice.")
        return Reply(SUCCESS,
                     f"Scanned {scanned} message(s) (requested {requested}, "
                     f"effective {effective}). Matched 0 messages for "
                     f"`{mode}`.")


_register()


def ensure_handler_refs() -> None:
    _register()
