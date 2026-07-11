"""The fuzzy adapter (spec 02 §3.7): a `CommandNotFound` raw token → K1
fuzzy match → AUTO (safe corrections re-enter `resolve()` — never a
`process_commands` re-dispatch) / SUGGEST / NONE.

The AUTO/SUGGEST thresholds are C-5's (shipped `utils/command_resolution.py`
is the K8-material central typo resolver); the corpus is K1's
`command_corpus`. AUTO-run safety derives from the manifest `effect` field
(02 §9 deferral): only `effect == "read"` targets auto-run.
"""

from __future__ import annotations

import difflib

from sb.kernel.interaction.adapters import lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve

__all__ = ["COMMAND_SYNONYMS", "FuzzyDecision", "dispatch_fuzzy",
           "install_prefix_typo_corpus", "prefix_typo_reply",
           "resolve_token", "unknown_prefix_suggestion"]

AUTO_CUTOFF = 0.85
SUGGEST_CUTOFF = 0.6

#: The shipped soft-alias layer feeding the typo resolver (disbot/utils/
#: synonyms.py COMMAND_SYNONYMS @7f7628e1 — bot1.py merged it into the
#: token→canonical map before matching). Entries land here as ported
#: goldens pin them (the STYLE_TOKEN_COLORS growth rule); a canonical not
#: registered on the surface is dropped at match time (the oracle's own
#: BUG-0014 orphan guard, test_command_synonyms_resolve_to_real_commands).
COMMAND_SYNONYMS: dict[str, tuple[str, ...]] = {
    "help": ("hilfe", "commands", "cmds", "cmd", "befehle"),
    "serverinfo": ("sinfo",),
    "userinfo": ("uinfo", "whois", "user"),
    "clear": ("purge", "clean", "delete", "löschen"),
    "warn": ("warning", "verwarnen"),
    "ban": ("bannieren", "banish", "sperren"),
    "kick": ("rauswerfen", "boot", "entfernen"),
    "timeout": ("mute", "stumm", "stumschalten"),
}

#: bot1.py's CommandNotFound SUGGEST reply, verbatim (goldens/moderation/
#: moderation_warn_flow step 2 pins the byte for `!warnings` → `!warn`).
UNKNOWN_COMMAND_SUGGEST = ("❓ Unknown command `{raw}`. "
                           "Did you mean `{prefix}{match}`?")


def unknown_prefix_suggestion(raw: str, corpus: frozenset[str], *,
                              prefix: str,
                              is_read=None) -> str | None:
    """The shipped CommandNotFound SUGGEST surface (bot1.py:541-586 —
    typo token → token map incl. COMMAND_SYNONYMS → canonical → the
    did-you-mean reply). Returns the reply copy, or None for NONE
    decisions and for AUTO decisions on read targets (the shipped silent
    AUTO re-dispatch is NAMED SUCCESSOR work — no golden pins it; a
    mutating canonical never auto-runs, the shipped DESTRUCTIVE_COMMANDS
    downgrade derived from the manifest route instead of a hand-list).

    ``is_read``: canonical name → bool (route effect probe); None treats
    every target as mutating, i.e. always downgrades AUTO to SUGGEST.
    """
    tokens: dict[str, str] = {name: name for name in corpus}
    for canonical, synonyms in COMMAND_SYNONYMS.items():
        if canonical not in corpus:
            continue                      # BUG-0014 orphan guard
        for synonym in synonyms:
            tokens.setdefault(synonym, canonical)
    decision = resolve_token(raw, frozenset(tokens))
    matched = decision.match if decision.kind == "auto" else (
        decision.suggestions[0] if decision.suggestions else None)
    if decision.kind == "none" or not matched:
        return None
    canonical = tokens.get(matched, matched)
    if decision.kind == "auto" and is_read is not None and is_read(canonical):
        return None                       # successor: the silent AUTO re-dispatch
    return UNKNOWN_COMMAND_SUGGEST.format(raw=raw, prefix=prefix,
                                          match=canonical)


#: () -> (frozenset[str] corpus, canonical -> bool is_read) | None — the
#: composition roots install their PREFIX command corpus (live:
#: build_runtime.install_live_target_index; parity: the harness index) so
#: the message feeds can render the shipped did-you-mean without owning
#: index internals.
_prefix_typo_corpus = None


def install_prefix_typo_corpus(provider) -> None:
    global _prefix_typo_corpus
    _prefix_typo_corpus = provider


def reset_prefix_typo_corpus_for_tests() -> None:
    global _prefix_typo_corpus
    _prefix_typo_corpus = None


def prefix_typo_reply(raw: str, *, prefix: str) -> str | None:
    """The feed-facing seam: None until a root installs its corpus (the
    surface stays dormant exactly like the pre-port fuzzy adapter)."""
    if _prefix_typo_corpus is None:
        return None
    corpus, is_read = _prefix_typo_corpus()
    return unknown_prefix_suggestion(raw, corpus, prefix=prefix,
                                     is_read=is_read)


class FuzzyDecision:
    __slots__ = ("kind", "match", "suggestions")

    def __init__(self, kind: str, match: str | None = None,
                 suggestions: tuple[str, ...] = ()):
        self.kind = kind                 # "auto" | "suggest" | "none"
        self.match = match
        self.suggestions = suggestions


def resolve_token(token: str, corpus: frozenset[str]) -> FuzzyDecision:
    matches = difflib.get_close_matches(token, sorted(corpus), n=3,
                                        cutoff=SUGGEST_CUTOFF)
    if not matches:
        return FuzzyDecision("none")
    ratio = difflib.SequenceMatcher(None, token, matches[0]).ratio()
    if ratio >= AUTO_CUTOFF:
        return FuzzyDecision("auto", matches[0], tuple(matches))
    return FuzzyDecision("suggest", None, tuple(matches))


async def dispatch_fuzzy(token: str, corpus: frozenset[str], *,
                         template: ResolveRequest) -> object | None:
    """AUTO path: rebuild the request against the corrected target and
    re-enter resolve() (identical order — authority/validate/cooldown run).
    A mutating/external target never auto-runs. Returns the Result, or the
    FuzzyDecision for suggest/none (the surface renders the did-you-mean)."""
    decision = resolve_token(token, corpus)
    if decision.kind != "auto":
        return decision
    target = lookup_target(decision.match, template.surface)
    if target is None:
        return FuzzyDecision("none")
    if getattr(target.spec, "effect", "read") != "read":
        return FuzzyDecision("suggest", None, (decision.match,))
    req = ResolveRequest(
        surface=template.surface, target=target, actor=template.actor,
        guild_id=template.guild_id, channel_id=template.channel_id,
        args=template.args, responder=template.responder, origin=template.origin,
    )
    _ = Surface  # documentation anchor: fuzzy re-enters on the SAME surface
    return await resolve(req)
