"""The deterministic setup advisor (the ``/setup-describe`` fallback lane).

ORACLE (reconstructed @befc6d0d via search_code fragments):
``disbot/services/setup_plan.py`` — ``DeterministicAdvisor``, a
"name-matching advisor over a GuildSnapshot": per channel × per
``_CHANNEL_RULES`` rule, a token match mints one ``SetupRecommendation``
per (subsystem, binding) slot with a reason line
``f"{target_label} `{name}` matches token `{token}` ({confidence})"``;
every candidate is then validated against the subsystem-schema registry
(``f"subsystem {subsystem!r} not registered"`` /
``f"binding {subsystem}.{binding_name} not declared"``) and the failures
land in ``SetupPlanDraft.dropped`` as
``f"{rec.subsystem}.{rec.binding_name}: {drop}"`` strings.

Reconstruction gaps, ledgered (trap 24 — pin the corpus, ledger the
drift):

* the full oracle rule TABLE never surfaced in fragments; the table below
  carries the recovered rules (general/economy fragments verbatim) plus
  the logging/commands pairs whose EXISTENCE and reasons the golden's own
  bytes prove (goldens/setup/sweep_slash_setup-describe: the two 🟢 high
  logging matches + the three dropped lines);
* candidate ORDER: the golden pins kept lines audit→mod and dropped lines
  announce→bot→main — both are the binding-name sort of the slot map;
  the port makes that ordering explicit (``sorted`` over binding_name)
  rather than depending on an unrecovered snapshot iteration order;
* VALIDATION target: the oracle validated against ITS OWN
  ``subsystem_schema`` registry — capture-time oracle state the new
  bot's manifest registry deliberately does not mirror (``general`` IS a
  subsystem here; the oracle never registered one). The advisor
  therefore validates against the CAPTURE-TIME schema slice carried as
  data below (the ticket-store constant-read posture for under-ported
  boundaries); the wizard-lifecycle successor re-homes validation onto
  the live binding registry when the apply lane ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "GuildChannel",
    "SetupPlanDraft",
    "SetupRecommendation",
    "install_channel_index",
    "reset_plan_ports_for_tests",
    "suggest",
]


@dataclass(frozen=True)
class GuildChannel:
    """One text channel of the advisor's guild snapshot."""

    id: int
    name: str


@dataclass(frozen=True)
class SetupRecommendation:
    subsystem: str
    binding_name: str
    target_kind: str
    target_id: int
    target_name: str
    confidence: str
    reason: str


@dataclass(frozen=True)
class SetupPlanDraft:
    """Aggregated output of an advisor run: ``recommendations`` carries the
    surviving proposals; ``dropped`` one-line reasons for every candidate
    that was filtered out (the oracle's debug-aid contract)."""

    recommendations: tuple[SetupRecommendation, ...] = ()
    dropped: tuple[str, ...] = ()
    source: str = "deterministic"

    def count(self, confidence: str) -> int:
        return sum(1 for r in self.recommendations
                   if r.confidence == confidence)


@dataclass(frozen=True)
class _Rule:
    tokens: tuple[str, ...]
    subsystem: str
    binding_name: str
    expected_kind: str = "channel"


#: the channel-name rule table (oracle _CHANNEL_RULES; general + economy
#: entries recovered verbatim, logging/commands proven by the golden's
#: output bytes — reconstruction note in the module docstring).
_CHANNEL_RULES: tuple[_Rule, ...] = (
    _Rule(tokens=("audit-log", "audit", "audit-logs"),
          subsystem="logging", binding_name="audit_channel"),
    _Rule(tokens=("mod-log", "mod-logs", "modlog"),
          subsystem="logging", binding_name="mod_channel"),
    _Rule(tokens=("commands", "bot-commands", "bot-spam"),
          subsystem="commands", binding_name="bot_channel"),
    _Rule(tokens=("general", "chat", "main"),
          subsystem="general", binding_name="main_channel"),
    _Rule(tokens=("economy", "coins", "shop"),
          subsystem="economy", binding_name="announce_channel"),
)

#: CAPTURE-TIME subsystem-schema slice (the oracle's ``all_schemas()``
#: registry as the advisor saw it): subsystem key -> the declared CHANNEL
#: binding names. ``logging`` carried the 11-slot route table (mod/audit
#: among them — the #167 port's own binding vocabulary); ``economy``/
#: ``xp`` carried their homed log/announce pointers (disbot
#: services/binding_backfill.py) but NO ``announce_channel`` on economy;
#: ``commands``/``general`` were never registered subsystems.
_CAPTURE_SCHEMA: dict[str, frozenset[str]] = {
    "logging": frozenset({"mod_channel", "audit_channel"}),
    "economy": frozenset({"log_channel"}),
    "xp": frozenset({"announce_channel"}),
}


def _validate(rec: SetupRecommendation) -> str | None:
    """The oracle's ``_validate_against_schema`` mirror (reason strings
    verbatim — goldens/setup/sweep_slash_setup-describe pins both)."""
    bindings = _CAPTURE_SCHEMA.get(rec.subsystem)
    if bindings is None:
        return f"subsystem {rec.subsystem!r} not registered"
    if rec.binding_name not in bindings:
        return f"binding {rec.subsystem}.{rec.binding_name} not declared"
    return None


def _match(rule: _Rule, name: str) -> tuple[str, str] | None:
    """Best token match for one channel name: exact name == token is a
    ``high``-confidence hit; a token appearing as a full hyphen-separated
    part of the name is ``medium`` (the oracle's tiered `best` pick — the
    golden pins only the high tier's byte)."""
    lowered = name.lower()
    parts = tuple(lowered.split("-"))
    best: tuple[str, str] | None = None
    for token in rule.tokens:
        if lowered == token:
            return ("high", token)
        if best is None and token in parts:
            best = ("medium", token)
    return best


# --- the channel snapshot port ------------------------------------------------------

_channel_index = None   # async (guild_id) -> tuple[GuildChannel, ...]


def install_channel_index(index) -> None:
    """index: async (guild_id) -> tuple[GuildChannel, ...] — the gateway
    guild cache's text-channel listing (the GuildSnapshot collect leg)."""
    global _channel_index
    _channel_index = index


def reset_plan_ports_for_tests() -> None:
    global _channel_index
    _channel_index = None


async def suggest(guild_id: int) -> SetupPlanDraft:
    """One deterministic advisor run over the installed channel index."""
    channels: tuple[GuildChannel, ...] = ()
    if _channel_index is not None:
        channels = tuple(await _channel_index(int(guild_id)) or ())
    slots: dict[tuple[str, str], SetupRecommendation] = {}
    for channel in channels:
        for rule in _CHANNEL_RULES:
            hit = _match(rule, channel.name)
            if hit is None:
                continue
            key = (rule.subsystem, rule.binding_name)
            if key in slots:
                continue            # first hit wins the slot
            confidence, token = hit
            reason = (f"channel name `{channel.name}` matches token "
                      f"`{token}` ({confidence})")
            slots[key] = SetupRecommendation(
                subsystem=rule.subsystem, binding_name=rule.binding_name,
                target_kind=rule.expected_kind, target_id=int(channel.id),
                target_name=str(channel.name), confidence=confidence,
                reason=reason)
    kept: list[SetupRecommendation] = []
    dropped: list[str] = []
    for rec in sorted(slots.values(), key=lambda r: r.binding_name):
        drop = _validate(rec)
        if drop is not None:
            dropped.append(f"{rec.subsystem}.{rec.binding_name}: {drop}")
            continue
        kept.append(rec)
    return SetupPlanDraft(recommendations=tuple(kept),
                          dropped=tuple(dropped))
