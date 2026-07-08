"""The bootstrap-command oracle (K1/registry — spec 04 §3.4 CONSUMED row).

Ported verbatim from the shipped ``core/runtime/command_access.py:30-102``:
bootstrap-ness is a NAMING/REGISTRY property (the roster is name-pattern
based — ``setup-*``/``settings-*``/``admin-*``/``platform-*``/``help-*``/
``diagnostics-*`` roots), so K1 owns the classifier; the K8 resolver computes
``is_bootstrap = is_bootstrap_command(target.key)`` before calling K6's
``resolve_channel_access``. A future explicit ``CommandSpec.is_bootstrap``
[S] field is a labeled deferral (spec 04 §9) — it would replace this
heuristic without changing any consumer (they already receive a bool).
"""

from __future__ import annotations

__all__ = ["BOOTSTRAP_COMMANDS", "is_bootstrap_command"]

# Shipped allowlist, verbatim (command_access.py:41-68).
BOOTSTRAP_COMMANDS: frozenset[str] = frozenset(
    {
        "admin",
        "adminmenu",
        "check_database",
        "checkdb",
        "diag",
        "diag_status",
        "diagnostic_bot_status",
        "diagnostics",
        "find_command",
        "findcmd",
        "help",
        "latency",
        "list_commands_detailed",
        "listcmds",
        "ping",
        "platform",
        "settings",
        "setup",
        "slashes",
        "slashlist",
        "syncs",
        "syncslash",
        "system_info",
        "sysinfo",
    },
)


def is_bootstrap_command(command_name: str | None) -> bool:
    """True iff ``command_name`` is a bootstrap command (shipped verbatim).

    Accepts three spellings so prefix groups, slash sub-commands, and
    operator-namespaced slash commands all classify consistently: bare names
    (``"help"``), qualified group names (whitespace-separated,
    ``"platform identity"``), and hyphen-namespaced slash commands
    (``"setup-hub"`` — the hyphen root only widens within the existing
    bootstrap surface).
    """
    if not command_name:
        return False
    normalized = command_name.strip().lower()
    if not normalized:
        return False
    if normalized in BOOTSTRAP_COMMANDS:
        return True
    space_root = normalized.split(maxsplit=1)[0]
    if space_root in BOOTSTRAP_COMMANDS:
        return True
    hyphen_root = normalized.split("-", maxsplit=1)[0]
    return hyphen_root in BOOTSTRAP_COMMANDS
