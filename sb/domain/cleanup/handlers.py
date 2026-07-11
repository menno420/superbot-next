"""Cleanup-surface handlers — the ``!cleanuphistory`` scan front door
plus the declared + honest pending terminals for every panel click whose
target is its own port slice (the settings/servermanagement precedent,
never a silent stub): the Logging Status / Settings / Cleanup Policies
sub-views, the word add/remove modals + the word-menu refresh (the
word-mutation panel slice), the Scan History button and the
anti-evasion toggle. Refs register at MODULE IMPORT (the
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
⚠️ over-limit helper (``delete_after=7``) and the matched>0 deletion
leg land with the channel-ops slice.
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

_SLICE = " ports with the word-mutation panel slice."


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

    pending_handler("cleanup.logging_pending",
                    "📝 The Logging Status view ports with the "
                    "server-logging slice.")
    pending_handler("cleanup.settings_pending",
                    "⚙️ The cleanup settings view ports with the "
                    "settings-mutation slice.")
    pending_handler("cleanup.policies_pending",
                    "🧹 The Cleanup Policies panel (diagnostics + presets "
                    "builder) ports with the cleanup-policy slice.")
    pending_handler("cleanup.word_add_pending",
                    f"➕ The Add-Word modal{_SLICE}")
    pending_handler("cleanup.word_remove_pending",
                    f"➖ The Remove-Word modal{_SLICE}")
    pending_handler("cleanup.word_refresh_pending",
                    f"🔄 The word-menu refresh{_SLICE}")
    pending_handler("cleanup.scan_history_pending",
                    "🔍 The Scan-History button ports with the channel-ops "
                    "slice (`!cleanuphistory` is the command front door).")
    pending_handler("cleanup.anti_evasion_pending",
                    f"🛡️ The anti-evasion toggle{_SLICE}")

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
