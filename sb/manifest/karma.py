"""KARMA subsystem manifest (band 4) — the shipped peer-reputation
surface verbatim (cogs/karma_cog.py): !thanks (rep/thank), the !karma
group (card + add), the /karma ephemeral slash card. One K7 op
(karma.give, INV-K), two stores (aggregate + the anti-abuse audit
ledger), the shipped karma.granted event, and the INV-K reconciliation
invariant. The settings slice claims the shipped karma keys
(karma_enabled / karma_cooldown / karma_daily_cap / karma_reaction_emoji
— sb/domain/settings/keys.py karma module).
"""

from __future__ import annotations

from sb.domain.karma import handlers as _handlers
from sb.domain.karma import panels as _panels
from sb.domain.karma.invariants import declare_karma_invariants
from sb.domain.karma.ops import EVT_KARMA_GRANTED, register_ops
from sb.domain.karma.policy import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_DAILY_CAP,
    DEFAULT_REACTION_EMOJI,
    MAX_COOLDOWN_SECONDS,
    MAX_DAILY_CAP,
    MAX_REACTION_EMOJI_LEN,
    MIN_COOLDOWN_SECONDS,
    MIN_DAILY_CAP,
)
from sb.domain.karma.store import KARMA_AUDIT_STORE, KARMA_STORE
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import ReplyVisibility
from sb.spec.refs import HandlerRef
from sb.spec.settings import Activation, SettingSpec

# shipped payload keys verbatim (services/karma_service.py bus.emit)
KARMA_GRANTED_EVENT = EventSpec(
    name=EVT_KARMA_GRANTED,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("from_user", "int"),
        FieldSpec("to_user", "int"),
        FieldSpec("delta", "int"),
        FieldSpec("new_total", "int"),
        FieldSpec("source", "str"),
    ),
    owner_subsystem="karma",
    delivery=DeliveryClass.BEST_EFFORT,
)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=True,
                settings_key="karma_enabled",
                activation=Activation.ON_BY_DEFAULT,
                hint="Master switch for karma. When off, !thanks / "
                     "!karma add politely decline. On by default."),
    SettingSpec(name="cooldown_seconds", value_type=int,
                default=DEFAULT_COOLDOWN_SECONDS,
                settings_key="karma_cooldown",
                bounds=(MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS),
                input_hint="numeric_presets",
                presets=(1800, 3600, 86400),
                hint="How long a member must wait before thanking the "
                     "same recipient again (seconds). The main anti-farm "
                     "guard. 0 disables the cooldown."),
    SettingSpec(name="daily_cap", value_type=int, default=DEFAULT_DAILY_CAP,
                settings_key="karma_daily_cap",
                bounds=(MIN_DAILY_CAP, MAX_DAILY_CAP),
                input_hint="numeric_presets",
                presets=(5, 10, 25),
                hint="Maximum karma grants one member can give per "
                     "rolling 24 hours."),
    SettingSpec(name="reaction_emoji", value_type=str,
                default=DEFAULT_REACTION_EMOJI,
                settings_key="karma_reaction_emoji",
                bounds=(MAX_REACTION_EMOJI_LEN,),
                hint="React-to-thank: set an emoji (e.g. ✨) and reacting "
                     "with it grants karma to the message's author — same "
                     "cooldown and daily cap as !thanks. Empty = off "
                     "(the default)."),
)


MANIFEST = SubsystemManifest(
    key="karma",
    version=1,
    commands=(
        CommandSpec(name="thanks", kind=CommandKind.PREFIX,
                    route=HandlerRef("karma.thanks"),
                    aliases=("rep", "thank"),
                    cooldown=CooldownSpec(rate=5, per_s=10),
                    audience_tier="user", capability="karma",
                    summary="Give a karma point to a helpful member.",
                    usage="!thanks @user [reason]"),
        CommandSpec(name="karma", kind=CommandKind.PREFIX,
                    route=HandlerRef("karma.card_view"),
                    cooldown=CooldownSpec(rate=5, per_s=10),
                    audience_tier="user", capability="karma",
                    summary="Show a member's karma standing.",
                    usage="!karma [@user]"),
        CommandSpec(name="add", kind=CommandKind.PREFIX, group="karma",
                    route=HandlerRef("karma.thanks"),
                    audience_tier="user", capability="karma",
                    summary="Give a karma point: !karma add @user [reason].",
                    usage="!karma add @user [reason]"),
        CommandSpec(name="karma", kind=CommandKind.SLASH,
                    route=HandlerRef("karma.card_view"),
                    reply_visibility=ReplyVisibility.EPHEMERAL,
                    audience_tier="user", capability="karma",
                    summary="Show your karma (peer reputation) — or "
                            "another member's.",
                    usage="/karma [member]"),
    ),
    # the two shipped result cards (cogs/karma_cog.py _karma_card +
    # utils/embeds.error) — component-less session cards, zero sim-gate
    # rows (run-minted session panels are auto-exempt below the floor).
    panels=(_panels.card_spec(), _panels.error_card_spec()),
    settings=_SETTINGS,
    stores=(KARMA_STORE, KARMA_AUDIT_STORE),
    events=(KARMA_GRANTED_EVENT,),
    capabilities=(),
    data_invariants=(declare_karma_invariants(),),
)

register_ops()
register_event_specs([KARMA_GRANTED_EVENT])


def _ensure_refs() -> None:
    from sb.domain.karma import invariants as _inv
    from sb.domain.karma import ops as _ops
    from sb.domain.karma import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _inv.ensure_invariant_refs()
    register_ops()
    register_event_specs([KARMA_GRANTED_EVENT])


ENSURE_REFS = _ensure_refs
