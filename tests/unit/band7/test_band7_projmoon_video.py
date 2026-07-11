"""Band 7 slice 2 — ProjMoon (Limbus) + shared video tasks onto K10:
the MINTED 12-probe corpus grounds through the real retrieval, the
A-17 gates pass under the deterministic provider with sockets denied,
and the probe order (btd6 → projmoon → video → general) carries the
shipped classify() semantics."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.domain.media import ai_tasks as media_ai
from sb.domain.media import video
from sb.domain.projmoon import ai_tasks as pm_ai
from sb.domain.projmoon import context as pm_context
from sb.domain.projmoon import dataset as pm_dataset
from sb.domain.projmoon import grounding as pm_grounding
from sb.domain.projmoon.evals import GROUNDING_PROBES, register_eval_suite
from sb.kernel.ai import evals, flags, router, routing, tasks
from sb.kernel.ai.grounding import absence_guard, verify
from sb.kernel.ai.providers.deterministic import DeterministicProvider
from sb.kernel.config import preflight

run = asyncio.run

BASE_ENV = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "x",
    "DATABASE_URL": "postgresql://u@localhost/db",
    "SB_DATA_PLANE": "test",
    "SB_TEST_DB_HOSTS": "localhost",
}


def _enable_ai():
    flags.install_ai_config(preflight(dict(BASE_ENV, AI_ENABLED="1")))


@pytest.fixture(autouse=True)
def _reset_ai_state():
    yield
    flags.reset_flags_for_tests()
    routing.clear_overrides()
    tasks.clear_tasks_for_tests()
    router.clear_probes_for_tests()
    verify.clear_verifiers_for_tests()
    absence_guard.clear_attributes_for_tests()
    evals.clear_suites_for_tests()
    video.reset_video_reader_for_tests()
    from sb.kernel.ai import feature_facts, instructions

    feature_facts.clear_gatherers_for_tests()
    instructions.clear_task_contracts_for_tests()
    from sb.kernel.ai.gateway import reset_default_gateway

    reset_default_gateway()


# --- the minted corpus (offline layer) ---------------------------------------------


@pytest.mark.parametrize("probe", GROUNDING_PROBES, ids=lambda p: p.question)
def test_corpus_question_grounds_its_answer(probe):
    blob = "\n".join(pm_context.build(probe.question).facts).lower()
    for needle in probe.expect:
        assert needle.lower() in blob, (
            f"{probe.question!r}: expected grounded fact containing {needle!r}"
        )
    for bad in probe.forbid:
        assert bad.lower() not in blob


def test_corpus_meets_the_a17_floor():
    assert len(GROUNDING_PROBES) >= 10  # A-17(d): projmoon MUST mint >=10
    assert all(p.expect for p in GROUNDING_PROBES)


def test_projmoon_eval_suite_passes_deterministic_gate():
    _enable_ai()
    pm_ai.register_projmoon_ai()
    from sb.kernel.ai.gateway import AIGateway

    suite = next(
        s for s in evals.registered_suites()
        if s.suite_id == "projmoon_qa_accuracy"
    )
    assert len(suite.cases) >= suite.min_cases
    result = run(
        evals.run_suite(
            suite, gateway=AIGateway(), provider=DeterministicProvider(),
        ),
    )
    assert result.passed, [
        (c.case_id, [g for g in c.grades if not g.passed and not g.advisory])
        for c in result.cases
        if not c.passed
    ]
    assert result.advisory_failures  # llm_judge tier recorded, never gating


# --- K10 registrations ---------------------------------------------------------------


def test_legacy_ids_claimed_verbatim():
    pm_ai.register_projmoon_ai()
    media_ai.register_video_ai()
    for task_id in ("projmoon.answer", "video.describe", "video.compare",
                    "video.qa"):
        assert task_id in tasks.LEGACY_TASK_IDS
        assert tasks.task_registered(task_id)
    assert "projmoon.answer" in verify.registered_verifier_tasks()


def test_probe_order_btd6_beats_projmoon_beats_video():
    from sb.domain.btd6 import ai_tasks as btd6_ai

    btd6_ai.register_btd6_ai()
    pm_ai.register_projmoon_ai()
    media_ai.register_video_ai()
    ctx = router.RouteContext()
    # Limbus token routes projmoon…
    assert router.classify("who is faust in limbus", ctx).task \
        == "projmoon.answer"
    # …but a BTD6 keyword in the same text wins (shipped order).
    assert router.classify("limbus or btd6, which is harder", ctx).task \
        == "btd6.answer"
    # Video legs (shipped confidences).
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert router.classify(f"{url} {url.replace('Q', 'A', 1)}", ctx).task \
        == "video.compare"
    assert router.classify(f"what is this video about {url}", ctx).task \
        == "video.qa"
    assert router.classify(url, ctx).task == "video.describe"
    # Ordinary chat falls through.
    assert router.classify("good morning", ctx).task == "general.nl_answer"


# --- projmoon grounding verifier -----------------------------------------------------


def test_projmoon_verifier_names_only():
    facts = ("Faust: LCB Sinner No. 2 …",)
    ok = pm_grounding.validate_projmoon_reply(
        "Faust is Sinner No. 2.", facts=facts)
    assert ok.grounded
    bad = pm_grounding.validate_projmoon_reply(
        "Heathcliff would win that fight.", facts=facts)
    assert not bad.grounded
    assert "heathcliff" in bad.offending_names
    # Numbers never offend on the projmoon path (names-only).
    nums = pm_grounding.validate_projmoon_reply(
        "Faust deals 42 damage.", facts=facts)
    assert nums.grounded
    # Ordinary English words (sins/statuses/damage types) never offend.
    words = pm_grounding.validate_projmoon_reply(
        "This deals slash damage and applies burn.", facts=facts)
    assert words.grounded


def test_projmoon_refusal_floor():
    text = pm_grounding.no_data_refusal()
    assert "Project Moon" in text
    assert "won't state" in text


# --- video gatherer (empty-facts short-circuit + reader port) -------------------------


def test_video_build_short_circuits_without_reader():
    out = run(video.build("https://youtu.be/dQw4w9WgXcQ explain this"))
    assert out.facts == ()
    assert out.error_reason == "video_feature_disabled"


def test_video_build_renders_facts_with_reader():
    async def reader(video_id):
        assert video_id == "dQw4w9WgXcQ"
        return {"title": "Test <@123> video", "channel_name": "Chan",
                "duration_seconds": 212,
                "description": "desc\x00line",
                "transcript_excerpt": None}

    video.install_video_metadata_reader(reader)
    out = run(video.build("https://youtu.be/dQw4w9WgXcQ"))
    assert out.error_reason is None
    blob = "\n".join(out.facts)
    assert "Video title: Test [mention] video" in blob  # mention scrubbed
    assert "transcript: unavailable" in blob
    assert "youtube.com/watch?v=dQw4w9WgXcQ" in blob


def test_video_build_no_urls_and_error_reason():
    async def reader(video_id):
        return "video_unavailable"

    video.install_video_metadata_reader(reader)
    out = run(video.build("no links here"))
    assert out.error_reason == "video_grounding_failed"
    out = run(video.build("https://youtu.be/dQw4w9WgXcQ"))
    assert out.error_reason == "video_unavailable"


# --- the !pm surface -----------------------------------------------------------------


def test_pm_oracle_cards():
    """The shipped `!pm` reply embeds (goldens/project_moon bytes) —
    the handlers present these verbatim through projmoon.card."""
    from sb.domain.projmoon import oracle_cards as cards

    over = cards.overview_card()
    assert over.title == "🌑 Project Moon — Limbus knowledge"
    assert over.style_token == "purple"
    assert over.footer == cards.FOOTER
    assert ("Sinners (12)",
            "Yi Sang, Faust, Don Quixote, Ryōshū, Meursault, Hong Lu, …",
            False) in over.fields

    hit = cards.entry_card(pm_dataset.resolve("don quixote"))
    assert hit.title == "🌑 Don Quixote"
    assert ("Literary origin", "*Don Quixote* — Miguel de Cervantes",
            False) in hit.fields

    miss = cards.lookup_miss_card("zzzz")
    assert miss.title == "🌑 Limbus lookup"
    assert "don't have a Limbus entry matching **zzzz**" in miss.description
    assert miss.style_token == "greyple" and miss.footer == ""

    origins = cards.origins_card()
    assert "**Heathcliff** — *Wuthering Heights*, Emily Brontë" in (
        origins.description)

    ego = cards.kind_card("ego_grade")
    assert ego.title == "🌑 Limbus — E.G.O grades"
    assert ego.fields[-1][0] == "ALEPH"

    # the shipped rstrip("s") singularizer + internal kind-key hint, verbatim
    cmiss = cards.category_miss_card("status", "zzzz")
    assert cmiss.description.startswith("No statuse matches **zzzz**.")
    assert "`!pm list status`" in cmiss.description


def test_dataset_resolver_longest_token_wins():
    entry = pm_dataset.resolve("tell me about don quixote please")
    assert entry is not None and entry.canonical == "Don Quixote"


def test_manifest_imports_and_registers():
    import sb.manifest.projmoon as manifest

    names = [c.qualified_name for c in manifest.MANIFEST.commands]
    assert "pm" in names
    assert "pm lookup" in names
    assert "pm origins" in names
    manifest.ENSURE_REFS()
    # The manifest import registered the video tasks too.
    assert tasks.task_registered("video.qa")
