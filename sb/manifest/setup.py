"""SETUP subsystem manifest (parity flip) — the shipped wizard entry
surface verbatim (ORACLE @befc6d0d: cogs/quicksetup_cog.py ``!setup`` /
``/setup``; cogs/setup_cog.py + cogs/setup/_wizard_entry.py the
``setup-*`` hyphen-namespaced slash family — discord.py forbids
whitespace in slash names, so the oracle shipped multi-token setup
commands as ``setup-*``), the four golden-pinned panels, the
``setup_session`` store, the K7 session ops, and the G-19
wizard_sections facet (all 10 shipped registrants, band-1 carried).

DELIBERATELY NOT DECLARED (goldens are the spec):

* ``/setup-depth`` — the oracle registered it with app_commands CHOICES,
  so the sweep's invalid value ``"test"`` produced NOTHING lib-side
  (discord.py dropped the interaction). goldens/setup/
  sweep_slash_setup-depth pins that SILENCE (zero calls); in this
  architecture an unregistered slash name reproduces it exactly (the
  #151 drop rule), while declaring it would register the name and mint a
  response byte the golden lacks (trap 17 / D-0076's ``/setup depth``
  clause: declaring-while-reproducing-silence is a contradiction — the
  declaration waits for a D-0019-style ruled re-capture).
* ``/setup-delegate`` / ``/setup-undelegate`` — capture-skipped
  (``parity/goldens/_sweep_skips.json``: "unsupported required option
  type user"); no golden exists on either surface (trap 28).
The ``!setupadvanced`` / ``!setupdescribe`` prefix twins ARE declared
(the wave-9 stray re-home): the oracle shipped them as plain prefix
commands in cogs/setup_cog.py (``name="setupadvanced"``, alias
``advancedsetup``; ``name="setupdescribe"``, alias ``describesetup``)
routing into the SAME wizard/describe entry bodies the slash family
uses — the port routes them to the same handlers
(goldens/setup/sweep_setupadvanced + sweep_setupdescribe pin the
prefix bytes).
"""

from __future__ import annotations

from sb.domain.setup import ai_tasks as _ai_tasks
from sb.domain.setup import handlers as _handlers
from sb.domain.setup import ops as _ops
from sb.domain.setup import panels as _panels
from sb.domain.setup import store as _store
from sb.domain.setup.sections import SECTIONS
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import DeferMode, ReplyVisibility
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="setup",
    version=1,
    commands=(
        CommandSpec(
            name="setup",
            kind=CommandKind.BOTH,
            route=HandlerRef("setup.essential_open"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Guided server setup: presets, channels, roles, "
                    "moderation, review.",
            usage="/setup",
            audience_tier="administrator",
            capability="setup",
            slash_common=True,               # config-lane, ADMIN floor
        ),
        CommandSpec(
            name="setup-hub",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.hub_open"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Open the setup hub (depth chooser first).",
            usage="/setup-hub",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-advanced",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.advanced_open"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Open the advanced setup wizard (power users).",
            usage="/setup-advanced",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setupadvanced",
            kind=CommandKind.PREFIX,
            aliases=("advancedsetup",),
            route=HandlerRef("setup.advanced_open"),
            summary="Open or resume the advanced (linear) setup wizard.",
            usage="!setupadvanced",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-describe",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.describe_entry"),
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Describe your server; get setup suggestions.",
            usage="/setup-describe description:<text>",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setupdescribe",
            kind=CommandKind.PREFIX,
            aliases=("describesetup",),
            route=HandlerRef("setup.describe_entry"),
            summary="Describe your server in words; propose how to "
                    "wire it to the bot.",
            usage="!setupdescribe",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-status",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.status_view"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Quick at-a-glance setup state (read-only).",
            usage="/setup-status",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-reset",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.reset_view"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Clear the staged setup draft.",
            usage="/setup-reset",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-skip",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.skip_section"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Mark a wizard section skipped.",
            usage="/setup-skip section:<slug>",
            audience_tier="administrator",
            capability="setup",
        ),
        CommandSpec(
            name="setup-unskip",
            kind=CommandKind.SLASH,
            route=HandlerRef("setup.unskip_section"),
            defer_mode=DeferMode.NONE,
            reply_visibility=ReplyVisibility.EPHEMERAL,
            summary="Restore a skipped wizard section.",
            usage="/setup-unskip section:<slug>",
            audience_tier="administrator",
            capability="setup",
        ),
    ),
    panels=(_panels.setup_hub_spec(), _panels.essential_card_spec(),
            _panels.status_card_spec(), _panels.suggestions_card_spec()),
    stores=(_store.SETUP_SESSION_STORE,),
    wizard_sections=SECTIONS,
)

_ai_tasks.register_ai_tasks()
_ops.register_ops()


def _ensure_refs() -> None:
    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_setup_refs()
    _handlers.ensure_handler_refs()
    _ai_tasks.register_ai_tasks()
    _ops.register_ops()


# module-attribute hook convention (D-0026)
ENSURE_REFS = _ensure_refs
