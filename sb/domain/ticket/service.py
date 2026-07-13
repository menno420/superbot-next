"""Ticket domain reads — the shipped ticket_service read seams.

The old bot stored ticket config and ticket rows in its OWN tables
(disbot/services/ticket_service.py ``get_config`` /
``get_ticket_for_channel`` / ``list_user_open``; "Tickets store config in
their own table (not the generic set_setting pipeline)" — the oracle's
2026-06-24 ticket-setup-discoverability card). The ticket-admin re-home
minted ``ticket_config`` + ``ticket_blacklist`` (migration 0032,
sb/domain/ticket/store.py — `!ticketlimit`/`!ticketblacklist` write them
through the K7 ops) and ``get_config`` reads the real row now. The
``tickets`` table (one row per open/closed ticket) still does NOT exist:
its write lane (the channel-provisioning ``open_ticket`` flow) lands with
the ticket-mutation slice. Until that slice, the ticket-row reads answer
the exact state every ticket golden captured — no ticket rows — and every
caller degrades through the shipped guard bytes:

  - ``get_config`` → None ⇒ the hub's "isn't set up yet" branch
    (views/tickets/hub.py ``cfg is None or not cfg.is_set_up``) and the
    open lane's REASON_NOT_CONFIGURED refusal;
  - ``get_ticket_for_channel`` → None ⇒ "This isn't an open ticket
    channel." (cogs/ticket_cog.py add/remove/claim/close);
  - ``list_user_open`` → () ⇒ "You have no open tickets."
    (views/tickets/hub.py).

Zero-vs-ensure: every shipped read on these paths was a PURE read (no
get-or-create anywhere in the guard lanes) — the goldens pin the absence of
any ticket-owned db_delta row, so nothing here may ensure.
"""

from __future__ import annotations

__all__ = ["check_open_eligibility", "get_config", "get_ticket_for_channel",
           "is_set_up", "list_user_open", "NOT_CONFIGURED_MSG",
           "OPEN_PROVISION_PENDING_MSG"]

#: the shipped open-lane eligibility refusal (disbot/services/
#: ticket_service.py REASON_NOT_CONFIGURED map entry, verbatim).
NOT_CONFIGURED_MSG = (
    "The ticket system isn't set up yet — an admin needs to run "
    "`!ticketsetup` and choose a staff role first."
)

#: the shipped REASON_DISABLED map entry, verbatim.
DISABLED_MSG = "The ticket system isn't enabled on this server."

#: the shipped REASON_BLACKLISTED map entry, verbatim.
BLACKLISTED_MSG = "You can't open tickets on this server."

#: honest pending terminal for an ELIGIBLE open on a configured guild —
#: the channel-provisioning open flow (private channel + ticket row +
#: welcome panel) is the ticket-open slice's port. New copy (no oracle
#: twin: the oracle would have opened the ticket), flagged in D-0084.
OPEN_PROVISION_PENDING_MSG = (
    "🎫 Ticket setup is live, but opening tickets (the private-channel "
    "provisioning flow) isn't ported yet — it lands with the ticket-open "
    "slice.")


def is_set_up(cfg) -> bool:
    """The shipped ``TicketConfig.is_set_up`` (enabled + a staff role)."""
    return bool(cfg and cfg.get("enabled") and cfg.get("staff_role_id"))


async def get_config(guild_id: int):
    """The shipped ``ticket_service.get_config`` read — the real
    ``ticket_config`` row since the ticket-admin re-home minted the store
    (migration 0032; `!ticketlimit` writes it), BEST-EFFORT like the
    shipped caller ("Best-effort config read", views/tickets/
    config_panel.py): headless/unmigrated ⇒ None, exactly the state every
    guard golden captured. Callers keep the config-absent guard branches
    (the configured open/hub flows stay the channel-provisioning slice's
    port — module docstring)."""
    try:
        from sb.domain.ticket import store

        return await store.get_config_row(int(guild_id))
    except Exception:  # noqa: BLE001 — best-effort read (shipped posture)
        return None


async def get_ticket_for_channel(channel_id: int):
    """The shipped ``ticket_service.get_ticket_for_channel`` read — None
    until the ticket store lands (see module docstring)."""
    return None


async def list_user_open(guild_id: int, user_id: int) -> tuple:
    """The shipped ``ticket_service.list_user_open`` read — empty until
    the ticket store lands (see module docstring)."""
    return ()


async def check_open_eligibility(guild_id: int,
                                 user_id: int) -> tuple[bool, str]:
    """The shipped ``ticket_service.check_open_eligibility`` gate, in the
    shipped ORDER (disabled → not-configured → blacklisted → limit),
    returning ``(allowed, refusal_message)``. Portable reads only: the
    open-count leg rides ``list_user_open`` (empty until the tickets
    table lands, so the limit branch cannot fire yet — honest, never
    invented)."""
    cfg = await get_config(int(guild_id))
    if cfg is None or not cfg.get("enabled"):
        return False, DISABLED_MSG
    if not is_set_up(cfg):
        return False, NOT_CONFIGURED_MSG
    try:
        from sb.domain.ticket import store

        blacklisted = await store.is_blacklisted(int(guild_id),
                                                 int(user_id))
    except Exception:  # noqa: BLE001 — headless ⇒ the read degrades open
        blacklisted = False
    if blacklisted:
        return False, BLACKLISTED_MSG
    open_count = len(await list_user_open(int(guild_id), int(user_id)))
    max_open = int(cfg.get("max_open_per_user") or 3)
    if open_count >= max_open:
        # the shipped REASON_LIMIT_REACHED map entry, verbatim.
        return False, (f"You already have {open_count} open ticket(s) "
                       f"(limit {max_open}). Close one before opening "
                       "another.")
    return True, ""
