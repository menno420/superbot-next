"""Config-installed AI feature gates (K10) — the shipped ``feature_flags``
env reads re-homed onto the RC-10 Config seam.

Shipped ``disbot/core/runtime/ai/feature_flags.py`` read the raw process
environment on every call; the config-accessor seam bans env reads outside
``sb/kernel/config``, so the composition root calls
:func:`install_ai_config(cfg)` after ``preflight()`` and every gate reads
the installed frozen Config (module-level-state port, the
``install_owner_config`` pattern).

Boot safety is unchanged from shipped semantics: AI is disabled unless the
operator opts in (``AI_ENABLED``), and the default provider is
``deterministic`` so no external call is ever made by accident. UNINSTALLED
config fails closed (``ai_enabled() == False``).

Shipped dynamic env-name patterns fold to typed CSV fields (RC-10 one
frozen attribute per env var — D-0022):

* ``AI_TASK_<NAME>_ENABLED`` per-task kill switches → ``AI_TASKS_DISABLED``
  (CSV of task ids; the per-task flag stays a kill switch, not an opt-in).
* ``AI_ROUTING_<TASK>`` per-task routes → ``AI_TASK_ROUTING``
  (CSV of ``task=provider:model`` entries; consumed by routing.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.config import Config

__all__ = [
    "ai_enabled",
    "ai_tools_enabled",
    "api_key_for",
    "default_provider",
    "fallback_provider",
    "install_ai_config",
    "reset_flags_for_tests",
    "server_member_lookup_enabled",
    "task_enabled",
    "task_routing_entries",
]

_cfg: Config | None = None


def install_ai_config(cfg: Config) -> None:
    """Install the preflighted Config; call once at the composition root."""
    global _cfg
    _cfg = cfg


def reset_flags_for_tests() -> None:
    global _cfg
    _cfg = None


def _get(name: str, default: object) -> object:
    if _cfg is None:
        return default
    return getattr(_cfg, name, default)


def ai_enabled() -> bool:
    """True if the AI platform is globally enabled (default OFF)."""
    return bool(_get("AI_ENABLED", False))


def default_provider() -> str:
    """The configured default provider name (default ``deterministic``)."""
    value = str(_get("AI_DEFAULT_PROVIDER", "") or "").strip().lower()
    return value or "deterministic"


def fallback_provider() -> str:
    """Optional secondary provider for the gateway's fault cascade.

    Empty means no fallback; the gateway ignores a fallback equal to the
    primary provider.
    """
    return str(_get("AI_FALLBACK_PROVIDER", "") or "").strip().lower()


def task_enabled(task_id: str) -> bool:
    """True if ``task_id`` may call a provider.

    Layers on :func:`ai_enabled` (global gate first). Once the global gate
    is on, tasks default to ENABLED; ``AI_TASKS_DISABLED`` is a selective
    kill switch (shipped ``AI_TASK_<NAME>_ENABLED`` semantics, CSV-folded).
    """
    if not ai_enabled():
        return False
    disabled = _get("AI_TASKS_DISABLED", ()) or ()
    return task_id not in {str(t).strip() for t in disabled}


def ai_tools_enabled() -> bool:
    """True if the gateway may offer read-only tools to the model.

    Layers on :func:`ai_enabled`; default OFF, so tool calling is inert
    until an operator opts in.
    """
    if not ai_enabled():
        return False
    return bool(_get("AI_TOOLS_ENABLED", False))


def server_member_lookup_enabled() -> bool:
    """True if AI tools may expose member-level guild data (the sensitive
    tier). Layers on :func:`ai_tools_enabled`; default OFF."""
    if not ai_tools_enabled():
        return False
    return bool(_get("AI_SERVER_MEMBER_LOOKUP_ENABLED", False))


def api_key_for(provider: str) -> str:
    """The installed API key for ``provider`` ('' when absent/uninstalled).

    The provider adapters are the only consumers; they raise
    ``ProviderUnavailableError`` on an empty key so the gateway degrades.
    """
    field = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider)
    if field is None:
        return ""
    return str(_get(field, "") or "")


def task_routing_entries() -> dict[str, str]:
    """Parse ``AI_TASK_ROUTING`` (CSV of ``task=provider:model``) into
    ``{task_id: "provider:model"}``. Malformed entries are skipped (the
    routing resolver falls back to defaults — never a boot failure)."""
    raw = _get("AI_TASK_ROUTING", ()) or ()
    out: dict[str, str] = {}
    for entry in raw:
        text = str(entry).strip()
        task_id, sep, target = text.partition("=")
        if sep and task_id.strip() and target.strip():
            out[task_id.strip()] = target.strip()
    return out
