"""The SINGLE owner-override predicate (K6, spec 04 §3.3 step 4 / §2).

``is_platform_owner`` ports the shipped deploy-config leaf (config.py:46-73):
identity is the authoritative Discord user id, never message text; the
configured owner (``BOT_OWNER_USER_ID``) plus every ``EXTRA_OWNER_USER_IDS``
account (owner ruling Q-0245 / A-21) clears the owner seam.

``owner_override_holds(user_id, is_member) := is_platform_owner(user_id) and
is_member`` — MEMBER-GATED (X-7 member-guilds-only, built structurally; the
owner confirms the scope, spec 04 §8-a). Computed ONCE at the top of
``resolve_authority`` and threaded into the channel-access lane (the L-12
non-bootstrap-deny fix); the ~11-16 shipped ``is_platform_owner``
authorization sites collapse to this one predicate. The only sanctioned
``is_platform_owner`` callers are (a) this module's ``owner_override_holds``
and (b) the K8 surface adapter building ``ActorRef.is_bot_owner`` (a
classification fact for the bootstrap leg) — AST-fenced at S9.

Owner identity is deploy config, not a table. The composition root calls
``install_owner_config(cfg)`` after ``preflight()``; module-level state ports
the shipped module-global posture (like ``sb.kernel.lifecycle``), with the
harvested config defaults live even before install (config.py source-wins).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.config import Config

__all__ = [
    "install_owner_config",
    "is_platform_owner",
    "owner_override_holds",
    "reset_for_tests",
]

_owner_id: int | None = None
_extra_owner_ids: frozenset[int] = frozenset()
_installed = False


def install_owner_config(cfg: "Config") -> None:
    """Install the deploy-declared owner identity from the typed Config
    (``BOT_OWNER_USER_ID`` INT + ``EXTRA_OWNER_USER_IDS`` CSV, both in
    CONFIG_FIELDS since K0). Called once at the composition root."""
    global _owner_id, _extra_owner_ids, _installed
    raw_owner = getattr(cfg, "BOT_OWNER_USER_ID", None)
    _owner_id = int(raw_owner) if raw_owner is not None else None
    extras: set[int] = set()
    for token in getattr(cfg, "EXTRA_OWNER_USER_IDS", ()) or ():
        try:
            extras.add(int(str(token).strip()))
        except ValueError:
            continue  # a typo in the env var must never crash boot (shipped)
    _extra_owner_ids = frozenset(extras)
    _installed = True


def reset_for_tests() -> None:
    """Clear installed owner identity (test seam, mirrors lifecycle's)."""
    global _owner_id, _extra_owner_ids, _installed
    _owner_id = None
    _extra_owner_ids = frozenset()
    _installed = False


def is_platform_owner(user_id: int | None) -> bool:
    """True iff ``user_id`` is the deploy-declared bot/platform owner (or an
    EXTRA_OWNER_USER_IDS fully-trusted operator account). The single source
    of truth for "is this the bot owner?" (config.py:61 intent, enforced).

    Before ``install_owner_config`` runs, NO ONE is the owner (fail-closed:
    an uninstalled engine can never mint an override)."""
    if user_id is None or not _installed:
        return False
    return user_id == _owner_id or user_id in _extra_owner_ids


def owner_override_holds(user_id: int | None, is_member: bool) -> bool:
    """THE owner-override predicate (spec 04 §3.3 step 4, frozen-l0 row 28):
    bot-owner AND member of the target guild (member-guilds-only, X-7)."""
    return is_platform_owner(user_id) and is_member
