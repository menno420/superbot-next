"""BTD6 QA-accuracy eval corpus (band 7, A-17) — the 16 shipped probes
of ``tests/evals/btd6_corpus.py`` @7f7628e1 imported VERBATIM (questions,
expect/forbid needles, rubrics, notes), registered as the domain's
:class:`EvalSuiteSpec` on the K10 harness.

Two layers, exactly as shipped:

* deterministic (REQUIRED) — for each probe the answer-bearing fact must
  be grounded by the REAL retrieval (``sb.domain.btd6.context.build``)
  and the known wrong claim must not be (``expect``/``forbid``);
* advisory (NEVER gating) — each probe's live-model rubric rides an
  ``llm_judge``-class grader that records "not run" under the
  deterministic CI provider (design-spec §8 Q9: a required live-judge
  gate is FORBIDDEN).

Grow the corpus from real misses: when a BTD6 answer is reported wrong,
add a probe."""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.ai import evals

__all__ = ["GROUNDING_PROBES", "GroundingProbe", "build_suite", "register_eval_suite"]


@dataclass(frozen=True)
class GroundingProbe:
    """One corpus question + how to judge it at each layer (shipped)."""

    question: str
    expect: tuple[str, ...]
    rubric: str = ""
    forbid: tuple[str, ...] = ()
    note: str = ""


GROUNDING_PROBES: tuple[GroundingProbe, ...] = (
    # --- the live screenshot misses ------------------------------------------
    GroundingProbe(
        question="can glue strike and avenger deal with DDTs",
        expect=("lead does not resist glue", "moab glue", "status effect"),
        rubric=(
            "Must say glue is a STATUS effect that ignores damage-type immunity "
            "(so Lead does NOT resist glue), and that affecting MOAB-class bloons "
            "like DDTs needs MOAB Glue. It may also note Glue Strike only debuffs "
            "/ doesn't pop. PASS as long as it never claims Lead resists/blocks "
            "glue."
        ),
        forbid=("lead resists glue", "lead is immune to glue"),
        note="screenshot #2 — the 'Lead resists glue' hallucination",
    ),
    GroundingProbe(
        question="can ice monkey slow ddts",
        expect=("cold", "lead", "cold snap"),
        rubric=(
            "Must say base Ice Monkey CANNOT slow/freeze DDTs because its effect "
            "is Cold-based and blocked by the Lead property, AND name a crosspath "
            "that fixes it (Cold Snap, or Embrittlement). Failing to name the "
            "crosspath fix is a FAIL."
        ),
        note="screenshot #3 — ice is cold-based, blocked by lead; Cold Snap fixes it",
    ),
    GroundingProbe(
        question="does glue work on lead bloons",
        expect=("lead does not resist glue",),
        rubric=(
            "Must answer YES — glue works on Lead bloons because glue is a status "
            "effect that ignores damage-type immunity. FAIL if it says Lead "
            "resists or is immune to glue."
        ),
        forbid=("lead resists glue",),
    ),
    # --- damage-type interactions --------------------------------------------
    GroundingProbe(
        question="what damage can pop lead bloons",
        expect=("needs explosion, fire, plasma, glacier, acid",),
        rubric=(
            "Must list damage types that pop Lead — Explosion, Fire, Plasma, "
            "Glacier, Acid, and/or Normal — and NOT offer Sharp, Cold, Shatter, "
            "or Energy as able to pop Lead."
        ),
        note="the lead pop-guide 'needs' clause is grounded",
    ),
    GroundingProbe(
        question="can you pop purple bloons with plasma",
        expect=("energy, plasma, fire, and frigid damage cannot pop purple",),
        rubric="Must answer NO — Purple bloons are immune to Plasma damage.",
    ),
    GroundingProbe(
        question="can a bomb shooter pop black bloons",
        expect=("explosion damage cannot pop black",),
        rubric=(
            "Must answer NO — a base Bomb Shooter deals Explosion damage, which "
            "is blocked by the Black property."
        ),
    ),
    GroundingProbe(
        question="does sharp damage pop lead",
        expect=("sharp, shatter, cold, and energy damage cannot pop lead",),
        rubric="Must answer NO — Lead bloons are immune to Sharp damage.",
    ),
    GroundingProbe(
        question="how do I deal with a DDT",
        expect=("camo detection", "fire, plasma, normal, acid, or glacier"),
        rubric=(
            "Must say a DDT needs CAMO DETECTION plus a damage type that is not "
            "blocked by Lead+Black — i.e. Fire, Plasma, Normal, Acid, or Glacier "
            "(NOT Sharp, Cold, Energy, or Explosion). PASS if it conveys the "
            "camo-detection + non-blocked-damage requirement, even without naming "
            "specific towers."
        ),
        forbid=("ddts are immune to glue", "lead resists glue"),
    ),
    GroundingProbe(
        question="can glacier damage pop lead",
        expect=("unlike plain cold",),
        rubric=(
            "Must answer YES — Glacier damage CAN pop Lead bloons. (Noting that "
            "plain Cold cannot is a plus but not required for a pass.)"
        ),
        note="Glacier is the cold variant that DOES pop lead",
    ),
    # --- bloon immunities (game-sourced) -------------------------------------
    GroundingProbe(
        question="what is a DDT immune to",
        expect=("immune to sharp, shatter, cold, energy, explosion",),
        rubric=(
            "Must state a DDT is immune to Sharp, Shatter, Cold, Energy, and "
            "Explosion damage (it has Lead + Black). Naming all five is required; "
            "omitting one is a FAIL."
        ),
    ),
    GroundingProbe(
        question="what is a zebra bloon immune to",
        expect=("explosion", "cold"),
        rubric=(
            "Must state a Zebra bloon is immune to BOTH Explosion AND Cold "
            "damage (Black + White). Naming only one is a FAIL."
        ),
        note="Zebra = Black + White → both",
    ),
    GroundingProbe(
        question="what is a purple bloon immune to",
        expect=("energy", "plasma", "fire"),
        rubric=(
            "Must state a Purple bloon is immune to Energy, Plasma, and Fire "
            "damage (Frigid too is acceptable). Missing any of Energy/Plasma/Fire "
            "is a FAIL."
        ),
    ),
    # --- regression probes for prior fixed live misses -----------------------
    GroundingProbe(
        question="what is the damage of a d67 dart paragon",
        expect=("apex plasma master at degree 67", "not an upgrade-path code"),
        rubric=(
            "Must treat 'd67' as the paragon's DEGREE (1-100) and give the Apex "
            "Plasma Master's Degree-67 stats (~48 dmg). FAIL if it reads 'd67' as "
            "an upgrade path '0-6-7' or claims it can't exist because tiers cap at 5."
        ),
        forbid=("0-6-7",),
        note="BUG-0015 — 'd67' is the paragon DEGREE, not a 0-6-7 upgrade-path code",
    ),
    GroundingProbe(
        question="does the monkey buccaneer have a paragon",
        expect=("navarch of the seas",),
        rubric=(
            "Must answer YES and name Navarch of the Seas as the Monkey "
            "Buccaneer's paragon. FAIL if it claims the Monkey Buccaneer has no "
            "paragon."
        ),
        forbid=("no paragon", "does not have a paragon", "doesn't have a paragon"),
        note=(
            "absence-claim repro (absence-guard design doc Update 2) — the false "
            "'Monkey Buccaneer has no paragon' that the committed data grounds against"
        ),
    ),
    GroundingProbe(
        question="how much is a despo on impoppable",
        expect=("desperado", "impoppable $360"),
        rubric=(
            "Must identify and price the Desperado (a Primary-category tower; "
            "Impoppable base $360), resolving the 'despo' shorthand correctly. "
            "FAIL if it answers about the Plasma Monkey Fan Club (PMFC) or any "
            "other tower."
        ),
        forbid=("plasma monkey fan club", "pmfc"),
        note="BUG-0003 — 'despo'/'despos' shorthand resolves to Desperado, not PMFC",
    ),
    GroundingProbe(
        question="what is the health of an elite lych",
        expect=("elite lych per-tier health", "30,000 hp"),
        rubric=(
            "Must give the ELITE Lych health from the Elite table (T1 30,000 HP "
            "up to T5 24,000,000 HP), NOT the Standard table (T1 14,000 HP). FAIL "
            "if it serves Standard HP as Elite."
        ),
        note="BUG-0002 — Elite boss HP comes from the Elite table, not the Standard one",
    ),
)


async def _grounded_blob(question: str) -> str:
    from sb.domain.btd6 import context

    ctx = await context.build(question)
    return "\n".join(ctx.facts).lower()


def _expect_grader(question: str, needle: str) -> evals.Grader:
    async def grade(outcome: evals.EvalOutcome) -> evals.GradeResult:
        blob = await _grounded_blob(question)
        return evals.GradeResult(
            "grounds_expected",
            needle.lower() in blob,
            f"needle={needle!r}",
        )

    return grade


def _forbid_grader(question: str, needle: str) -> evals.Grader:
    async def grade(outcome: evals.EvalOutcome) -> evals.GradeResult:
        blob = await _grounded_blob(question)
        return evals.GradeResult(
            "forbids_wrong_claim",
            needle.lower() not in blob,
            f"needle={needle!r}",
        )

    return grade


def _rubric_judge(rubric: str) -> evals.Grader:
    def judge(outcome: evals.EvalOutcome) -> evals.GradeResult:
        # The llm_judge tier needs a live model; under the deterministic
        # CI provider it is recorded as not-run (advisory, never gating).
        return evals.GradeResult(
            "llm_judge",
            False,
            f"live judge not run (deterministic CI); rubric: {rubric[:80]}",
        )

    return judge


def build_suite() -> evals.EvalSuiteSpec:
    from sb.domain.btd6 import dataset

    cases = []
    for index, probe in enumerate(GROUNDING_PROBES):
        graders: list[evals.Grader] = [
            _expect_grader(probe.question, needle) for needle in probe.expect
        ]
        graders.extend(
            _forbid_grader(probe.question, needle) for needle in probe.forbid
        )
        if probe.rubric:
            graders.append(evals.advisory(_rubric_judge(probe.rubric)))
        cases.append(
            evals.EvalCase(
                case_id=f"btd6-{index:02d}",
                task="btd6.answer",
                payload={"question": probe.question},
                graders=tuple(graders),
            ),
        )
    return evals.EvalSuiteSpec(
        suite_id="btd6_qa_accuracy",
        owner_subsystem="btd6",
        cases=tuple(cases),
        content_version=f"btd6@{dataset.game_version()}",
    )


def register_eval_suite() -> evals.EvalSuiteSpec:
    """Idempotent registration on the K10 suite registry."""
    for suite in evals.registered_suites():
        if suite.suite_id == "btd6_qa_accuracy":
            return suite
    return evals.register_suite(build_suite())
