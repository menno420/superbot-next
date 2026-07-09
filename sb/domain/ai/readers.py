"""The last K10 composition seams (band 7): the per-guild policy
OVERLAY reader (gateway provider/model override from declared ai.*
settings), the vetted-answer preset lookup (nl_engine short-circuit,
fail-safe), and ``install_ai_platform()`` — the one call a composition
root makes after ``flags.install_ai_config`` to arm the whole AI
platform (band-1 readers + band-7 seams; the discord history scanner
installs from sb/adapters at the live composition root)."""

from __future__ import annotations

import logging

logger = logging.getLogger("sb.domain.ai.readers")

__all__ = ["install_ai_platform"]


async def _guild_policy_overlay(guild_id: int):
    """Provider/model overlay from the declared ai.* settings (empty
    values = no overlay; LookupError = undeclared → no overlay)."""
    from sb.kernel import settings as ksettings

    out: dict[str, str] = {}
    for name, key in (("default_provider", "default_provider"),
                      ("default_model", "default_model")):
        try:
            value = await ksettings.resolve(guild_id, "ai", name)
        except LookupError:
            return None
        if value:
            out[key] = str(value)
    return out or None


async def _preset_lookup(guild_id: int, question: str | None) -> str | None:
    """Exact normalized-question preset lookup — FAIL-SAFE (any error
    returns None so the model path proceeds; shipped posture)."""
    try:
        from sb.domain.ai import normalize, store

        key = normalize.normalize_question(question)
        if not key:
            return None
        return await store.lookup_preset(guild_id, key)
    except Exception:  # noqa: BLE001 — a preset miss never breaks a reply
        logger.debug("ai preset lookup failed guild=%s", guild_id,
                     exc_info=True)
        return None


def install_ai_platform() -> None:
    """Idempotent: band-1's four setting-backed readers + the band-7
    guild-policy overlay + the preset short-circuit."""
    from sb.domain.settings.ai_readers import install_ai_readers
    from sb.kernel.ai import gateway, nl_engine

    install_ai_readers()
    gateway.install_guild_policy_reader(_guild_policy_overlay)
    nl_engine.install_preset_lookup(_preset_lookup)
