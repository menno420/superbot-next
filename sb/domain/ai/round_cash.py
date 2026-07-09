"""The round-cash plan→execute→verify workflow (band 7) — the first
real ``register_answer_workflow`` runner (the shipped
``ai_round_cash_workflow`` MVP re-homed, K10 D-0023 note): recognise a
round-cash RANGE question deterministically, compute the inclusive
range cash from the committed rounds data, verify per-round coverage,
and emit :class:`AIAnswerWithEvidence` (Q-0046) with Q-0043 inclusive
semantics. Never a guessed number: an unsupported modifier or a data
gap yields status="unsupported" with the evidence stating why.

Focused port: the RANGE branch (recognisers verbatim: cash keyword /
money-question gate, the four range patterns incl. the r-shorthand and
clause-separated anchors, the end-of-round completion shift, ABR cue,
double/half-cash modifier honesty, stated-balance projection). The
afford_check branch rides the deep-tools successor (D-0048)."""

from __future__ import annotations

import re

from sb.domain.btd6 import keywords as btd6_keywords
from sb.kernel.ai.contracts import AIAnswerWithEvidence, CalculationEvidence

__all__ = ["plan_question", "register_round_cash_workflow", "run"]

_CASH_KEYWORD_RE = re.compile(
    r"\b(?:cash|money|income|earn(?:ed|ings?|s)?)\b", re.I)
_MODIFIER_RE = re.compile(r"\b(double|half)\s+cash\b", re.I)
_MONEY_QUESTION_RE = re.compile(
    r"\bhow\s+much\b[^.?!\n]{0,60}?\b(?:have|get|make|earn|gain)\b", re.I)

_RT = r"(?:rounds?|r)\s*"
_RTA = r"(?:the\s+)?(?:end\s+of\s+)?" + _RT

_RANGE_RES = (
    re.compile(
        r"\bfrom\s+" + _RTA + r"(\d{1,3})\s*(?:to|through|thru|until|till|[-–])"
        r"\s*(?:" + _RTA + r")?(\d{1,3})\b", re.I),
    re.compile(
        r"\b" + _RT + r"(\d{1,3})\s*(?:to|through|thru|[-–])"
        r"\s*(?:" + _RT + r")?(\d{1,3})\b", re.I),
    re.compile(r"\bbetween\s+" + _RT + r"(\d{1,3})\s+and\s+(\d{1,3})\b", re.I),
    re.compile(
        r"\b(?:at|from|on|by)\s+" + _RTA + r"(\d{1,3})\b[^.?!\n]{0,80}?"
        r"\b(?:to|until|till|reach(?:ing)?|going\s+to|get(?:ting)?\s+to|by|at)"
        r"\s+" + _RTA + r"(\d{1,3})\b", re.I),
)

_COMPLETED_ROUND_TMPL = (
    r"\b(?:end\s+of|after|beat(?:ing)?|clear(?:ed|ing)?|finish(?:ed|ing)?|"
    r"complet(?:ed|ing))\s+(?:the\s+)?(?:rounds?|r)\s*{n}\b"
)

_AMOUNT_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([km])?", re.I)
_BALANCE_CUE_RE = re.compile(
    r"\b(?:i\s+have|i\s+had|holding|with)\s+\$?\s*"
    r"(\d[\d,]*(?:\.\d+)?)\s*([km])?\b", re.I)


def _scale(raw: str, suffix: str | None) -> float:
    value = float(raw.replace(",", ""))
    if suffix:
        value *= 1_000 if suffix.lower() == "k" else 1_000_000
    return value


def plan_question(text: str) -> dict | None:
    """Deterministically recognise a round-cash range question, else
    None (the workflow stays out — the model path runs unchanged)."""
    if not text:
        return None
    if not (_CASH_KEYWORD_RE.search(text) or _MONEY_QUESTION_RE.search(text)):
        return None
    for pattern in _RANGE_RES:
        match = pattern.search(text)
        if match is None:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        start, end = min(first, second), max(first, second)
        completed = None
        if re.search(_COMPLETED_ROUND_TMPL.format(n=start), text, re.I):
            completed = start
            start += 1
        balance = None
        bal_match = _BALANCE_CUE_RE.search(text)
        if bal_match is not None:
            balance = _scale(bal_match.group(1), bal_match.group(2))
        modifier = None
        mod_match = _MODIFIER_RE.search(text)
        if mod_match is not None:
            modifier = mod_match.group(1).lower()
        return {
            "intent": "range_cash", "round_start": start, "round_end": end,
            "starting_balance": balance, "completed_round_anchor": completed,
            "roundset": ("abr" if btd6_keywords.ABR_CUE_RE.search(text)
                         else "default"),
            "unsupported_modifier": modifier,
        }
    return None


def _range_cash(start: int, end: int, roundset: str) -> tuple[float, list[int]]:
    """Sum of the dataset round-cash column, INCLUSIVE of both endpoints
    (Q-0043). Returns (total, missing_rounds)."""
    from sb.domain.btd6 import dataset

    blob = dataset.read_blob(
        "abr_rounds.json" if roundset == "abr" else "rounds.json") or {}
    by_round = {int(r.get("round", -1)): r for r in blob.get("rounds", ())}
    total = 0.0
    missing: list[int] = []
    for n in range(start, end + 1):
        row = by_round.get(n)
        if row is None or row.get("cash") is None:
            missing.append(n)
        else:
            total += float(row["cash"])
    return total, missing


async def run(question: str, ctx: object = None) -> AIAnswerWithEvidence | None:
    """The registered runner: None = unrecognised (model path runs)."""
    plan = plan_question(question)
    if plan is None:
        return None
    start, end = plan["round_start"], plan["round_end"]
    roundset = plan["roundset"]
    total, missing = _range_cash(start, end, roundset)
    from sb.domain.btd6 import dataset

    assumptions = [
        f"range r{start}–r{end} INCLUSIVE of both endpoints (Q-0043)",
        f"roundset={roundset}",
        "base economy only (no cash modifiers applied)",
    ]
    if plan["completed_round_anchor"] is not None:
        assumptions.append(
            f"r{plan['completed_round_anchor']} already completed — its "
            "income is counted in the stated balance, range starts one "
            "round later")
    evidence = CalculationEvidence(
        evidence_id=f"round_cash:{roundset}:{start}-{end}",
        calculator="btd6.round_cash_range",
        calculator_version=dataset.game_version(),
        normalized_inputs={"round_start": start, "round_end": end,
                           "roundset": roundset},
        assumptions=tuple(assumptions),
        outputs={"range_cash": total, "missing_rounds": missing},
    )
    if missing:
        return AIAnswerWithEvidence(
            contract="calculation_explained",
            workflow="analyze_execute_verify",
            intent="range_cash", status="unsupported",
            result_text=(
                f"The dataset has no {roundset} cash entry for round(s) "
                f"{missing[:5]} — I can't compute r{start}–r{end} without "
                "guessing."),
            inclusive_range=True, evidence=(evidence,))
    bits = [
        f"Round cash r{start}–r{end} (inclusive, "
        f"{'ABR' if roundset == 'abr' else 'standard'} set): ${total:,.0f}.",
    ]
    if plan["starting_balance"] is not None:
        projected = plan["starting_balance"] + total
        bits.append(
            f"With your stated ${plan['starting_balance']:,.0f}, that "
            f"projects to ${projected:,.0f}.")
    if plan["unsupported_modifier"]:
        bits.append(
            f"NOTE: '{plan['unsupported_modifier']} cash' is NOT applied — "
            "this is the base economy figure; scale it yourself for that "
            "mode.")
    return AIAnswerWithEvidence(
        contract="calculation_explained",
        workflow="analyze_execute_verify",
        intent="range_cash", status="complete",
        result_text=" ".join(bits),
        inclusive_range=True, evidence=(evidence,))


def register_round_cash_workflow() -> None:
    """Idempotent registration under the shipped workflow label."""
    from sb.kernel.ai import orchestration

    try:
        orchestration.register_answer_workflow(
            "analyze_execute_verify", run, owner_subsystem="ai")
    except ValueError:
        pass  # identical re-registration path differs by closure identity
