"""The shared thin-handler kit (ORDER 004 item 4 — boilerplate collapse).

Every domain band's HandlerRef modules grew the SAME two lines of glue,
copy-pasted 22×: a frozen ``Reply(outcome, user_message)`` duck-shape the
resolver renders (spec 02 §3.4 — resolve.py reads only ``.outcome`` /
``.user_message``), and ``_ctx_from_req`` mapping a ``ResolveRequest`` onto
a :class:`~sb.kernel.workflow.context.WorkflowContext` for ``engine.run``.
This module is their ONE home; domain modules import it instead of
re-declaring it. Existing local ``Reply`` classes stay duck-compatible —
the resolver never isinstance-checks — so migration is import-swap only.

Leaf-light: stdlib + ``sb.kernel.workflow.context`` (itself a leaf over
``sb.spec``); safe to import at domain-module import time (manifest
compile stays hermetic).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.workflow.context import WorkflowContext

__all__ = ["Reply", "ctx_from_request"]


@dataclass(frozen=True)
class Reply:
    """The thin-handler reply duck-shape the resolver renders.

    ``suppress_mentions`` is the shipped ``allowed_mentions=
    AllowedMentions.none()`` send kwarg as reply data: the resolver
    threads the Reply through ``Result.workflow``, and the responders
    (discord + parity capture twin) read the flag off it — the
    ``!aireview preset add`` confirmation pins the wire byte
    (goldens/ai/sweep_aireview_preset_add: ``allowed_mentions:
    {"parse": []}``)."""

    outcome: str
    user_message: str
    suppress_mentions: bool = False


def ctx_from_request(req, params: dict) -> WorkflowContext:
    """Map a ResolveRequest onto the WorkflowContext ``engine.run`` takes
    (actor/guild/request_id/confirmed thread through; params are the op's)."""
    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)
