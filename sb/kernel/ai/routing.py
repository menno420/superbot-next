"""Task → (provider, model, timeout) resolution (K10).

Ported from shipped ``disbot/core/runtime/ai/routing.py`` with the closed
enum cut: default-model tables key on the frozen legacy task-id STRINGS
(so band-7 re-binds byte-stable) and unknown/new task ids fall to the
per-provider fallback model.

Resolution order:

1. Explicit :func:`override` (test seam; cleared by :func:`clear_overrides`).
2. ``AI_TASK_ROUTING`` config entry ``task=provider:model``
   (the shipped per-task ``AI_ROUTING_<TASK>`` env pattern, CSV-folded).
3. Default registry built from ``flags.default_provider()``.

Model defaults were the SHIPPED tables verbatim until the owner ruled the
K10 question-router block (PR #30, 2026-07-08): the Anthropic tables below
carry that ruling (K10(b) — bias hard toward Haiku); see D-0033.
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.ai import flags

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "RoutingTarget",
    "clear_overrides",
    "default_model_for",
    "override",
    "resolve",
]

DEFAULT_TIMEOUT_SECONDS = 20.0

# Shipped OpenAI default: gpt-4o-mini across the board. OWNER FLAG
# (PR #30, K10(b), 2026-07-08): gpt-4o-mini is ruled UNRELIABLE; the
# replacement GPT model is TBD — until the owner names one this stays the
# only OpenAI value (provider is non-default; nothing routes here unless an
# operator explicitly selects openai).
_OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
# OWNER RULING (PR #30, K10(b), 2026-07-08) — overrides the shipped tables:
# bias HARD toward claude-haiku-4-5 (sonnet-4-6 is too slow for most tasks);
# reserve Sonnet for tasks that need deeper reasoning. Unknown/new task ids
# therefore fall to Haiku, not Sonnet.
_ANTHROPIC_FALLBACK_MODEL = "claude-haiku-4-5"

# Anthropic per-task policy under the K10(b) ruling: ONLY the
# deeper-reasoning trio keeps Sonnet (mutation proposals, moderation
# judgment, deep strategy analysis); every explain/suggest/triage/answer
# task — and the fallback — is Haiku. (Shipped @7f7628e1 had six Sonnet
# tasks + a Sonnet fallback; the exact trio kept here is this port's
# judgment call under the ruling, ledgered in D-0033 — owner veto flips
# rows, not shape.)
_ANTHROPIC_DEFAULT_MODELS: dict[str, str] = {
    # Deeper-reasoning tasks → Sonnet (the reserved set).
    "settings.propose": "claude-sonnet-4-6",
    "moderation.assist": "claude-sonnet-4-6",
    "btd6.strategy_review": "claude-sonnet-4-6",
    # Ruled down to Haiku by K10(b) (were Sonnet shipped-side).
    "setup.suggest": "claude-haiku-4-5",
    "logs.triage": "claude-haiku-4-5",
    "code_context.explain": "claude-haiku-4-5",
    # Live chat (user is waiting) → fast Haiku.
    "btd6.answer": "claude-haiku-4-5",
    "general.nl_answer": "claude-haiku-4-5",
    # Lighter explain / answer tasks → Haiku.
    "setup.explain": "claude-haiku-4-5",
    "settings.explain": "claude-haiku-4-5",
    "platform.explain_status": "claude-haiku-4-5",
    "platform.explain_consistency": "claude-haiku-4-5",
    "help.answer": "claude-haiku-4-5",
    "video.describe": "claude-haiku-4-5",
    "video.compare": "claude-haiku-4-5",
    "video.qa": "claude-haiku-4-5",
}


@dataclass(frozen=True)
class RoutingTarget:
    """Resolved provider + model + timeout for a single AI call."""

    provider: str
    model: str
    timeout_seconds: float


_OVERRIDES: dict[str, RoutingTarget] = {}


def override(task_id: str, target: RoutingTarget) -> None:
    """Install a routing override; primarily a test seam."""
    _OVERRIDES[task_id] = target


def clear_overrides() -> None:
    """Reset every routing override; restores config/default resolution."""
    _OVERRIDES.clear()


def default_model_for(provider: str, task_id: str) -> str:
    """The default model for ``task_id`` under ``provider`` — lets an
    operator switch provider without also supplying a model, so an OpenAI
    model string never reaches Anthropic (or vice versa)."""
    if provider == "anthropic":
        return _ANTHROPIC_DEFAULT_MODELS.get(task_id, _ANTHROPIC_FALLBACK_MODEL)
    return _OPENAI_FALLBACK_MODEL


def model_matches_provider(provider: str, model: str) -> bool:
    """Crude family check catching a stored model that can't work with the
    resolved provider (stale cross-provider value / typo'd id — it would
    404 at the provider). Only the two real network providers are
    constrained; empty model = match ("auto-pick" handled by the caller)."""
    if not model:
        return True
    if provider == "anthropic":
        return model.startswith("claude")
    if provider == "openai":
        return model.startswith("gpt")
    return True


def resolve(task_id: str) -> RoutingTarget:
    """Resolve the provider, model, and timeout for ``task_id``."""
    if task_id in _OVERRIDES:
        return _OVERRIDES[task_id]

    entry = flags.task_routing_entries().get(task_id, "")
    if entry:
        provider, _, model = entry.partition(":")
        provider = provider.strip().lower()
        if provider:
            model = model.strip() or default_model_for(provider, task_id)
            if not model_matches_provider(provider, model):
                model = default_model_for(provider, task_id)
            return RoutingTarget(
                provider=provider,
                model=model,
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            )

    provider = flags.default_provider()
    return RoutingTarget(
        provider=provider,
        model=default_model_for(provider, task_id),
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
