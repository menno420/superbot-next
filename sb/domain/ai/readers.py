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

__all__ = ["guild_orchestration_default", "install_ai_platform"]


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


async def _policy_bundle_with_overlays(guild_id: int):
    """The band-1 KV guild policy WIDENED with the typed override tables
    (the policy-mutation slice — the follow-up the band-1 module named:
    "widening them to the typed tables changes no caller").

    * overlays: ai_channel_policy / ai_category_policy / ai_role_policy
      rows in the K10 PolicyBundle row shapes;
    * the shipped minted-row semantics: the ORACLE's bump_generation
      upserted the ai_guild_policy row on the FIRST scoped write, so a
      guild with only overrides resolved AI_GLOBALLY_DISABLED (enabled
      defaults false), never GUILD_NOT_CONFIGURED — here the generation
      counter row is the mint marker and the defaults dict is its twin;
    * fail-safe: any store read failure degrades to the base KV bundle
      (the _preset_lookup posture — replay/DB-free roots keep the exact
      band-1 behavior).
    """
    from sb.domain.settings.ai_readers import _policy_bundle
    from sb.kernel.ai.policy import PolicyBundle

    base = await _policy_bundle(guild_id)
    try:
        from sb.domain.ai import policy_store

        channel, category, role = await policy_store.load_overlays(guild_id)
        generation = await policy_store.get_generation(guild_id)
    except Exception:  # noqa: BLE001 — overlay miss = the band-1 bundle
        logger.debug("ai policy overlay read failed guild=%s", guild_id,
                     exc_info=True)
        return base
    policy = dict(base.policy) if base.policy else None
    if policy is None and generation is not None:
        # the shipped minted-defaults row (migration 039 column defaults).
        policy = {
            "enabled": False,
            "natural_language_enabled": False,
            "minimum_level_default": 2,
            "cooldown_seconds": 30,
            "guild_instruction_profile_id": None,
            "fresh_user_mention_allowance": 1,
        }
    if policy is not None:
        policy["generation"] = int(generation or 0)
    return PolicyBundle(policy=policy, channel=channel, category=category,
                        role=role)


async def _profile_key_with_overlays(guild_id: int, channel_id: int,
                                     category_id: int | None):
    """The band-1 K10 profile-key reader WIDENED with the typed
    orchestration overlays (the orchestration-mutation slice — the
    shipped most-specific-wins columns of migration 062: channel →
    category → guild):

    * channel/category keys: the ai_channel_policy / ai_category_policy
      ``orchestration_profile`` columns (migration 0031);
    * guild key: the ``ai_orchestration_profile`` guild_settings row (the
      shipped ai_guild_policy column's KV twin, D-0025) — falling back to
      the band-1 read (the declared ``guild_instruction_profile``
      approximation) ONLY while the row was never written; a PRESENT row
      is authoritative even when it encodes an explicit CLEAR (the codex
      #187 P2 — a clear must not resurrect the band-1 approximation; the
      ORACLE's clear resolved straight to the compatible default);
    * fail-safe: any store read failure degrades to the band-1 reader's
      answer (the _policy_bundle_with_overlays posture — replay/DB-free
      roots keep the exact band-1 behavior).
    """
    from sb.domain.settings.ai_readers import _profile_key

    base = await _profile_key(guild_id, channel_id, category_id)
    try:
        from sb.domain.ai import policy_store

        channel_map, category_map = (
            await policy_store.load_orchestration_overlays(guild_id))
        present, guild_key = (
            await policy_store.read_guild_orchestration_profile(guild_id))
    except Exception:  # noqa: BLE001 — overlay miss = the band-1 answer
        logger.debug("ai orchestration overlay read failed guild=%s",
                     guild_id, exc_info=True)
        return base
    chan_key = channel_map.get(int(channel_id))
    cat_key = (category_map.get(int(category_id))
               if category_id is not None else None)
    return chan_key, cat_key, (guild_key if present else base[2])


async def guild_orchestration_default(guild_id: int) -> str | None:
    """The guild-default orchestration key EXACTLY as the K10 reader
    above would serve it (KV row when ever written — explicit clear
    included — else the band-1 fallback), for display surfaces (the
    tools chooser's "Current" field, the preview footer): the shipped
    UI read the SAME single source the resolver consumed
    (snapshot.orchestration.guild_profile_key), so mirroring the
    resolver IS the oracle posture (the codex #187 P2 twin). Fail-safe
    None."""
    try:
        from sb.domain.ai import policy_store

        present, guild_key = (
            await policy_store.read_guild_orchestration_profile(guild_id))
        if present:
            return guild_key
    except Exception:  # noqa: BLE001 — fall to the band-1 read
        logger.debug("guild orchestration default read failed guild=%s",
                     guild_id, exc_info=True)
    try:
        from sb.domain.settings.ai_readers import _profile_key

        return (await _profile_key(int(guild_id), 0, None))[2]
    except Exception:  # noqa: BLE001 — display surfaces degrade to unset
        return None


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
    guild-policy overlay + the preset short-circuit + the typed policy
    OVERRIDE overlays (the policy-mutation slice) + the typed
    ORCHESTRATION overlays (the orchestration-mutation slice) — each
    installed OVER its band-1 reader; same seam, widened read."""
    from sb.domain.settings.ai_readers import install_ai_readers
    from sb.kernel.ai import gateway, nl_engine, orchestration, policy

    install_ai_readers()
    policy.install_policy_bundle_reader(_policy_bundle_with_overlays)
    orchestration.install_profile_key_reader(_profile_key_with_overlays)
    gateway.install_guild_policy_reader(_guild_policy_overlay)
    nl_engine.install_preset_lookup(_preset_lookup)
