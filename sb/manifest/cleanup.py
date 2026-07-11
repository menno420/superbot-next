"""CLEANUP subsystem manifest (band 2) — the word-filter lanes (K7 ops +
prohibited_words store, migration 0011) + the shipped panel surfaces (the
parity flip): ``!cleanup`` opens the REAL Cleanup Hub, ``!wordmenu`` the
REAL Prohibited Words Manager (sb/domain/cleanup/panels.py —
goldens/cleanup/ pins every wire byte), and ``!cleanuphistory`` runs the
shipped channel-history scan through the domain history-reader port
(sb/domain/cleanup/service.py; the deletion leg stays the channel-ops
slice's port)."""

from __future__ import annotations

from sb.domain.cleanup import handlers as _handlers
from sb.domain.cleanup import ops as _ops
from sb.domain.cleanup import panels as _panels
from sb.domain.cleanup import store as _store
from sb.domain.cleanup.ops import register_ops
from sb.domain.cleanup.store import PROHIBITED_WORDS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef
from sb.spec.settings import SettingSpec


def _cmd(name, route, summary, *, group="", tier=""):
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=route, summary=summary, capability="cleanup",
                       audience_tier=tier)


MANIFEST = SubsystemManifest(
    key="cleanup",
    version=1,
    commands=(
        # the shipped admin-gated panel front doors (cleanup_cog.py —
        # the hub and the words manager were Administrator surfaces).
        _cmd("cleanup", PanelRef("cleanup.hub"), "Open the cleanup menu.",
             tier="administrator"),
        _cmd("wordmenu", PanelRef("cleanup.words"),
             "Open the word-filter menu.", tier="administrator"),
        # the shipped scan rode perms_or_owner(manage_messages=True) —
        # the moderator tier (TIER_DISCORD_PERMISSION's closest floor).
        _cmd("cleanuphistory", HandlerRef("cleanup.history_scan"),
             "Sweep recent channel history.", tier="moderator"),
        _cmd("word", HandlerRef("cleanup.word_list"),
             "List the prohibited words."),
        _cmd("add", WorkflowRef("cleanup.word_add_op"),
             "Add a prohibited word.", group="word"),
        _cmd("remove", WorkflowRef("cleanup.word_remove_op"),
             "Remove a prohibited word.", group="word"),
        _cmd("list", HandlerRef("cleanup.word_list"),
             "List the prohibited words.", group="word"),
    ),
    panels=(_panels.cleanup_hub_spec(), _panels.cleanup_words_spec()),
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
    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
