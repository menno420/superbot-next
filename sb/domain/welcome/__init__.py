"""WELCOME subsystem (band 2) — greeting/farewell template engine + the
A-14 join-verification anchors (entry-role binding = the deny-until-role
gate's role source; min-account-age = the screening input). The
member-join feed arms when the member band ports."""

from __future__ import annotations

__all__ = ["DEFAULT_JOIN_MESSAGE", "DEFAULT_LEAVE_MESSAGE", "render_message"]

# shipped defaults, verbatim (services/welcome_config.py)
DEFAULT_JOIN_MESSAGE = ("👋 Welcome {user} to **{server}**! "
                        "You're member #{count}.")
DEFAULT_LEAVE_MESSAGE = "👋 **{user}** has left {server}. We're now {count} members."


def render_message(template: str, *, user: str, server: str,
                   count: int) -> str:
    """The shipped placeholder set ({user}/{server}/{count}); unknown
    braces pass through verbatim (never a KeyError to the operator)."""
    out = template or ""
    return (out.replace("{user}", user)
               .replace("{server}", server)
               .replace("{count}", str(count)))
