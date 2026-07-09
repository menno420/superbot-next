"""Project Moon (Limbus) QA-accuracy eval corpus (band 7, A-17) —
MINTED here: the oracle had NO projmoon corpus, and the A-17(d) mandate
says the domain must mint one at its port band (≥10 probes). Twelve
probes over the committed structural fixtures, in the exact
GroundingProbe shape of the BTD6 corpus so both gates read alike:
deterministic tier = the REAL retrieval (``context.build``) must ground
every expect needle and no forbid needle; rubric tier = advisory
llm_judge (recorded, never gating).

Grow from real misses: when a Limbus answer is reported wrong, add a
probe."""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.ai import evals

__all__ = ["GROUNDING_PROBES", "GroundingProbe", "build_suite", "register_eval_suite"]


@dataclass(frozen=True)
class GroundingProbe:
    question: str
    expect: tuple[str, ...]
    rubric: str = ""
    forbid: tuple[str, ...] = ()
    note: str = ""


GROUNDING_PROBES: tuple[GroundingProbe, ...] = (
    # --- sinner identity + literary origins ---------------------------------
    GroundingProbe(
        question="who is faust in limbus company",
        expect=("faust", "goethe"),
        rubric="Must identify Faust as LCB Sinner No. 2 and credit Goethe's "
               "Faust as the literary origin.",
    ),
    GroundingProbe(
        question="what is heathcliff's literary origin in limbus",
        expect=("wuthering heights", "emily brontë"),
        rubric="Must name Wuthering Heights by Emily Brontë.",
        forbid=("moby-dick",),
    ),
    GroundingProbe(
        question="who is rodion in limbus company",
        expect=("crime and punishment", "dostoevsky"),
        rubric="Must credit Crime and Punishment by Fyodor Dostoevsky.",
    ),
    GroundingProbe(
        question="which book is gregor from in limbus",
        expect=("the metamorphosis", "kafka"),
        rubric="Must name The Metamorphosis by Franz Kafka.",
    ),
    GroundingProbe(
        question="list all sinners in limbus",
        expect=("yi sang", "outis", "gregor", "hong lu"),
        rubric="Must list the 12 LCB Sinners (roster completeness).",
        note="roster-trigger probe — 'all sinners' pulls the full kind",
    ),
    # --- E.G.O grades ---------------------------------------------------------
    GroundingProbe(
        question="what is the aleph grade in limbus",
        expect=("rank 5/5",),
        rubric="Must say ALEPH is the highest E.G.O grade.",
        forbid=("rank 1/5",),
    ),
    GroundingProbe(
        question="what is zayin in limbus",
        expect=("lowest e.g.o grade",),
        rubric="Must say ZAYIN is the lowest E.G.O grade.",
    ),
    GroundingProbe(
        question="what are the ego grades in limbus",
        expect=("zayin", "teth", "waw", "aleph"),
        rubric="Must list the five grades in order (ZAYIN/TETH/HE/WAW/ALEPH).",
        note="roster-trigger probe — grade order completeness",
    ),
    # --- combat mechanics / damage / statuses ---------------------------------
    GroundingProbe(
        question="how does clash work in limbus",
        expect=("clash", "coin"),
        rubric="Must describe clashing: both skills flip coins, the higher "
               "final value wins and the loser's attack is blunted.",
    ),
    GroundingProbe(
        question="what damage types are there in limbus",
        expect=("slash", "pierce", "blunt"),
        rubric="Must name exactly the three attack damage types "
               "(Slash / Pierce / Blunt).",
        note="roster-trigger probe",
    ),
    GroundingProbe(
        question="what does burn do in limbus",
        expect=("burn", "damage-over-time"),
        rubric="Must say Burn is damage-over-time keyed on Burn potency.",
    ),
    GroundingProbe(
        question="what is tremor in limbus",
        expect=("tremor", "stagger"),
        rubric="Must connect Tremor to stagger pressure / bursting to lower "
               "the stagger threshold.",
    ),
)


def _grounded_blob(question: str) -> str:
    from sb.domain.projmoon import context

    return "\n".join(context.build(question).facts).lower()


def _expect_grader(question: str, needle: str) -> evals.Grader:
    def grade(outcome: evals.EvalOutcome) -> evals.GradeResult:
        return evals.GradeResult(
            "grounds_expected",
            needle.lower() in _grounded_blob(question),
            f"needle={needle!r}",
        )

    return grade


def _forbid_grader(question: str, needle: str) -> evals.Grader:
    def grade(outcome: evals.EvalOutcome) -> evals.GradeResult:
        return evals.GradeResult(
            "forbids_wrong_claim",
            needle.lower() not in _grounded_blob(question),
            f"needle={needle!r}",
        )

    return grade


def _rubric_judge(rubric: str) -> evals.Grader:
    def judge(outcome: evals.EvalOutcome) -> evals.GradeResult:
        return evals.GradeResult(
            "llm_judge",
            False,
            f"live judge not run (deterministic CI); rubric: {rubric[:80]}",
        )

    return judge


def build_suite() -> evals.EvalSuiteSpec:
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
                case_id=f"projmoon-{index:02d}",
                task="projmoon.answer",
                payload={"question": probe.question},
                graders=tuple(graders),
            ),
        )
    return evals.EvalSuiteSpec(
        suite_id="projmoon_qa_accuracy",
        owner_subsystem="projmoon",
        cases=tuple(cases),
        content_version="limbus-structural@1.0",
    )


def register_eval_suite() -> evals.EvalSuiteSpec:
    for suite in evals.registered_suites():
        if suite.suite_id == "projmoon_qa_accuracy":
            return suite
    return evals.register_suite(build_suite())
