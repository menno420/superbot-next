"""The A-17 socket-deny eval guard (K10).

The deterministic tier of the knowledge-domain eval gate runs a domain's
``EvalSuiteSpec`` corpus under the deterministic provider INSIDE required
CI — and must be structurally incapable of touching the network (frozen
design-spec §8 Q9: a required live-judge gate is FORBIDDEN; fresh semantic
grading stays advisory).

:func:`deny_sockets` enforces that at the transport layer: inside the
context, ANY attempt to create a network connection raises
:class:`SocketDenied` loudly (never a silent skip). AF_UNIX is left alone
so in-process plumbing (if any) keeps working; it is the INET families
that reach providers.

Usage (the eval harness arms this around every required-CI suite run)::

    with deny_sockets():
        results = await run_suite(suite, gateway=...)
"""

from __future__ import annotations

import contextlib
import socket
from collections.abc import Iterator

__all__ = ["SocketDenied", "deny_sockets"]


class SocketDenied(RuntimeError):
    """A network connection was attempted inside a socket-denied eval run."""


_INET_FAMILIES = frozenset(
    {socket.AF_INET, getattr(socket, "AF_INET6", socket.AF_INET)},
)


class _DenyingSocket(socket.socket):
    """A socket subclass that refuses INET construction outright."""

    def __init__(self, family: int = -1, *args: object, **kwargs: object) -> None:
        fam = family if family != -1 else socket.AF_INET
        if fam in _INET_FAMILIES:
            raise SocketDenied(
                "network access is denied inside the deterministic eval "
                "gate (A-17 / design-spec §8 Q9); route the case through "
                "the deterministic provider instead",
            )
        super().__init__(family, *args, **kwargs)  # type: ignore[arg-type]


def _deny_getaddrinfo(*_args: object, **_kwargs: object) -> object:
    raise SocketDenied(
        "DNS resolution is denied inside the deterministic eval gate (A-17)",
    )


@contextlib.contextmanager
def deny_sockets() -> Iterator[None]:
    """Deny INET socket creation + DNS resolution within the context.

    Patches ``socket.socket``, ``socket.create_connection``, and
    ``socket.getaddrinfo`` (the three roads every HTTP client takes) and
    restores them on exit, exception-safe. Re-entrant: nested use keeps
    the guard armed until the outermost exit.
    """
    original_socket = socket.socket
    original_create = socket.create_connection
    original_gai = socket.getaddrinfo

    def _deny_create(*_args: object, **_kwargs: object) -> object:
        raise SocketDenied(
            "network access is denied inside the deterministic eval gate (A-17)",
        )

    socket.socket = _DenyingSocket  # type: ignore[misc]
    socket.create_connection = _deny_create  # type: ignore[assignment]
    socket.getaddrinfo = _deny_getaddrinfo  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[misc]
        socket.create_connection = original_create  # type: ignore[assignment]
        socket.getaddrinfo = original_gai  # type: ignore[assignment]
