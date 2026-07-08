"""CLEANUP subsystem manifest (band 2) — the word-filter lanes (K7 ops +
prohibited_words store, migration 0011) + the history-sweep surfaces
(channel-ops port when it arms)."""

from __future__ import annotations

from sb.domain.cleanup import ops as _ops
from sb.domain.cleanup import store as _store
from sb.domain.cleanup.ops import register_ops
from sb.domain.cleanup.store import PROHIBITED_WORDS_STORE
from sb.domain.operator_spine import ensure_hub, hub_spec, pending_handler
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef
from sb.spec.settings import SettingSpec

_TITLE, _BLURB = "Cleanup", ("Prohibited-word filter + message-hygiene "
                             "sweeps.")
ensure_hub("cleanup", _TITLE, _BLURB)

_PENDING = pending_handler(
    "cleanup.history_pending",
    "History sweeps aren't armed in this build yet — the channel-ops port "
    "lands with the discord adapter slice.")


def _cmd(name, route, summary, *, group=""):
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=route, summary=summary, capability="cleanup")


MANIFEST = SubsystemManifest(
    key="cleanup",
    version=1,
    commands=(
        _cmd("cleanup", PanelRef("cleanup.hub"), "Open the cleanup menu."),
        _cmd("wordmenu", PanelRef("cleanup.hub"), "Open the word-filter menu."),
        _cmd("cleanuphistory", _PENDING, "Sweep recent channel history."),
        _cmd("word", HandlerRef("cleanup.word_list"),
             "List the prohibited words."),
        _cmd("add", WorkflowRef("cleanup.word_add_op"),
             "Add a prohibited word.", group="word"),
        _cmd("remove", WorkflowRef("cleanup.word_remove_op"),
             "Remove a prohibited word.", group="word"),
        _cmd("list", HandlerRef("cleanup.word_list"),
             "List the prohibited words.", group="word"),
    ),
    panels=(hub_spec("cleanup", _TITLE, _BLURB),),
    settings=(
        SettingSpec(name="spam_window_seconds", value_type=int, default=15,
                    settings_key="cleanup_spam_window_seconds",
                    bounds=(1, 3600),
                    hint="Repeated-message window for cleanup sweeps."),
    ),
    stores=(PROHIBITED_WORDS_STORE,),
    events=(), capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    ensure_hub("cleanup", _TITLE, _BLURB)
    pending_handler("cleanup.history_pending", "")
    _store.ensure_refs()
    _ops.ensure_ops_refs()


ENSURE_REFS = _ensure_refs
