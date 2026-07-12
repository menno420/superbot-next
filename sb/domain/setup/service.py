"""The setup workspace + entry-flow domain service (the setup parity flip).

ORACLE (reconstructed @befc6d0d via search_code fragments — full-file
oracle reads stay denied):

* ``disbot/services/setup_channel.py`` — ``ensure_setup_channel``: the
  create-or-find ``#superbot-setup`` workspace. Find is a NAME check over
  the gateway guild cache (an operator channel named anything else is
  never adopted; a cached ``superbot-setup`` is reused WITHOUT a create
  call — goldens/setup/sweep_slash_setup-advanced + -status record ZERO
  channel calls over the capture's leaked workspace, trap 17); create
  routes through the channel-state port with the private overwrite map
  passed AT creation (goldens/_unmapped→setup sweep_setup.json pins all
  four entries + ``reason: null``).
* ``disbot/cogs/setup/_wizard_entry.py`` + ``views/setup/wizard.py``
  (``open_setup_workspace``) — the advanced wizard entry posts the depth
  chooser as the workspace anchor and replies with a jump link.
* ``disbot/views/setup/essential_setup.py`` — the ``!setup`` / ``/setup``
  essential flow posts the Step-1 card into the workspace; "no session
  row or cross-restart persistence is needed" (its docstring — the
  goldens pin the empty ``setup_session`` delta).

Overwrite-recompute-on-reuse (the oracle's session-pointer branch
"repair its overwrites") is NOT ported here: no golden pins a repair
wire byte (the capture's reuse rode the name-find branch, which repairs
nothing), and no bulk-recompute wire verb exists in the corpus (D-0077's
own "oracle mechanism unrecovered" note). When a wizard-lifecycle slice
needs it, it composes per-target ``set_overwrite`` calls (the existing
edit_channel_permissions verb).

LIVE ARMING: the live composition root does not arm the channel-state
create surface yet (D-0077 shipped the port + capture twin only; the
D-0049-family discord adapter is the named successor) — until it does,
these flows refuse honestly through the port's fail-loud default.
"""

from __future__ import annotations

import dataclasses
from typing import Any

__all__ = [
    "BOT_WORKSPACE_ALLOW",
    "MEMBER_WORKSPACE_ALLOW",
    "SETUP_CHANNEL_NAME",
    "VIEW_CHANNEL_BIT",
    "ensure_setup_channel",
    "install_workspace_member_source",
    "jump_link",
    "post_panel_to_channel",
    "reset_setup_ports_for_tests",
    "workspace_overwrites",
]

#: the shipped literal (disbot/services/setup_channel.py) — the name IS the
#: adoption guard: operator-created "setup" channels are never adopted.
SETUP_CHANNEL_NAME = "superbot-setup"

#: discord permission bits, named (the golden-pinned masks decompose to
#: exactly these — goldens/setup/sweep_setup.json permission_overwrites):
VIEW_CHANNEL_BIT = 1024            # view_channel (read_messages)
_SEND_MESSAGES_BIT = 2048
_MANAGE_MESSAGES_BIT = 8192
_EMBED_LINKS_BIT = 16384
_READ_HISTORY_BIT = 65536

#: the bot's own workspace grant: view + send + manage_messages +
#: embed_links + read_message_history = 93184 (golden byte).
BOT_WORKSPACE_ALLOW = (VIEW_CHANNEL_BIT | _SEND_MESSAGES_BIT
                       | _MANAGE_MESSAGES_BIT | _EMBED_LINKS_BIT
                       | _READ_HISTORY_BIT)

#: the invoker/delegate grant: view + send + read_message_history = 68608
#: (golden byte).
MEMBER_WORKSPACE_ALLOW = (VIEW_CHANNEL_BIT | _SEND_MESSAGES_BIT
                          | _READ_HISTORY_BIT)


def jump_link(guild_id: int, channel_id: int, message_id: int) -> str:
    """``message.jump_url`` — discord.py's canonical channels URL."""
    return (f"https://discord.com/channels/{int(guild_id)}/"
            f"{int(channel_id)}/{int(message_id)}")


# --- workspace member/role inputs (the guild-cache read the overwrite map
# needs: admin roles + the bot member) ---------------------------------------------

_member_source = None   # async (guild_id) -> duck guild | None (role-service shape)


def install_workspace_member_source(source) -> None:
    """source: async (guild_id) -> duck guild (roles/me) | None — the SAME
    gateway-cache view the role domain's guild_view port reads; the
    composition root may install one callable for both."""
    global _member_source
    _member_source = source


def reset_setup_ports_for_tests() -> None:
    global _member_source
    _member_source = None


async def workspace_overwrites(guild_id: int, invoker_id: int,
                               delegated: tuple[int, ...] = ()) -> tuple:
    """The oracle's private-workspace overwrite map, in the goldens' wire
    order (sweep_setup.json): @everyone denied view, every ADMIN role
    denied view (privacy: admins see the workspace only when delegated),
    the bot allowed its working set, then the invoking owner (+ each
    delegated admin) allowed view/send/history."""
    from sb.domain.channel.service import ChannelOverwrite

    admin_role_ids: list[int] = []
    bot_id = 0
    if _member_source is not None:
        guild = await _member_source(int(guild_id))
        if guild is not None:
            for role in getattr(guild, "roles", ()) or ():
                if int(getattr(role, "id", 0)) == int(guild_id):
                    continue        # @everyone rides the leading entry
                perms = getattr(role, "permissions", None)
                if bool(getattr(perms, "administrator", False)):
                    admin_role_ids.append(int(role.id))
            bot_id = int(getattr(getattr(guild, "me", None), "id", 0) or 0)
    entries = [ChannelOverwrite(target_id=int(guild_id), target_type=0,
                                allow=0, deny=VIEW_CHANNEL_BIT)]
    entries.extend(ChannelOverwrite(target_id=rid, target_type=0,
                                    allow=0, deny=VIEW_CHANNEL_BIT)
                   for rid in admin_role_ids)
    if bot_id:
        entries.append(ChannelOverwrite(target_id=bot_id, target_type=1,
                                        allow=BOT_WORKSPACE_ALLOW, deny=0))
    entries.append(ChannelOverwrite(target_id=int(invoker_id), target_type=1,
                                    allow=MEMBER_WORKSPACE_ALLOW, deny=0))
    entries.extend(ChannelOverwrite(target_id=int(d), target_type=1,
                                    allow=MEMBER_WORKSPACE_ALLOW, deny=0)
                   for d in delegated)
    return tuple(entries)


async def ensure_setup_channel(guild_id: int, invoker_id: int,
                               delegated: tuple[int, ...] = ()
                               ) -> tuple[int, bool]:
    """Create-or-find the private workspace; returns ``(channel_id,
    created)``. FIND: the gateway-cache NAME lookup (the shipped
    guild.get_channel/name-scan leg — the channel-domain lookup port, the
    ``!xpimport`` resolver posture); a hit is reused with NO wire call
    (capture-faithful: the trap-17 leaked workspace, seeded per-case by
    the runner's CAPTURE_WORLD_CHANNELS — the sweep_xpimport/sweep_slowmode
    precedent). MISS: one ``create_text_channel`` POST with the overwrite
    map at creation (D-0077's port contract: the port always creates;
    get-before-create is THIS function). ``reason=None`` — the shipped
    create carried no audit reason (golden byte)."""
    from sb.domain.channel import service as channel_service

    existing = await channel_service.resolve_channel(
        int(guild_id), SETUP_CHANNEL_NAME)
    if existing is not None:
        return int(existing), False
    overwrites = await workspace_overwrites(guild_id, invoker_id, delegated)
    actions = channel_service.active_actions()   # the S11 port receiver form
    created = await actions.create_text_channel(
        int(guild_id), name=SETUP_CHANNEL_NAME, overwrites=overwrites,
        parent_id=None, reason=None)
    return int(created), True


# --- workspace panel post ----------------------------------------------------------

class _ChannelSendOrigin:
    """A responder-less presentation origin: the presenter falls to its
    channel-send branch (parity twin: ``record_send``; the live presenter's
    channel-anchor lane is the D-0049-family successor)."""

    surface = None


async def post_panel_to_channel(panel_id: str, req: Any,
                                channel_id: int,
                                params: dict | None = None) -> int | None:
    """Open a panel INTO a specific channel (the oracle's
    ``channel.send(embed=..., view=...)`` workspace post) and return the
    minted message id. The presentation request is the driving request
    re-scoped onto the target channel with NO interaction responder, so
    the presenter takes its channel-send path and the interaction's own
    response slot stays free for the entry's ephemeral reply."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = dict(req.args or {})
    if params:
        args.update(params)
    channel_req = dataclasses.replace(
        req, channel_id=int(channel_id), args=args,
        responder=_ChannelSendOrigin(), origin=None)
    key = await open_panel(PanelRef(panel_id), channel_req)
    try:
        return int(str(key))
    except (TypeError, ValueError):
        return None
