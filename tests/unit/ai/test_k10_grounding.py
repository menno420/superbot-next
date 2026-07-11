"""K10 grounded-answer engine: format, name guard, absence guard,
verifier registry + the verify-and-regenerate-once loop."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone

from sb.kernel.ai.grounding import absence_guard, format as gformat, name_guard, verify

# registry cleanup: conftest.py's dir-wide after-only reset


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


class TestFormat:
    def test_sanitise_strips_and_caps(self):
        assert gformat.sanitise("a\x00b   c", cap=0) == "ab c"
        assert gformat.sanitise("x" * 300).endswith("…")
        assert gformat.sanitise(42) == ""

    def test_relative_time(self):
        now = datetime.now(timezone.utc)
        assert gformat.relative_time(now - timedelta(seconds=30)).endswith("s ago")
        assert gformat.relative_time(now - timedelta(hours=2)) == "2h ago"
        assert gformat.relative_time(now + timedelta(hours=1)) == "just now"
        assert gformat.relative_time(None) == "unknown"

    def test_render_line_provenance_never_cut(self):
        line = gformat.render_grounding_line(
            "b" * 500,
            source_name="Wiki",
            fetched_at=None,
            max_chars=80,
        )
        assert line.endswith("(source: Wiki, fetched unknown)")
        assert len(line) <= 80 + 8  # body budget floor tolerance

    def test_infinite_sentinel(self):
        assert gformat.is_infinite(9_999_999)
        assert gformat.is_infinite(10_000_000.0)
        assert not gformat.is_infinite(9_999_998)
        assert not gformat.is_infinite(True)


class TestNameGuard:
    def test_build_matchers_filters(self):
        matchers = name_guard.build_matchers(
            canonicals=["Sauda", "Monkey Buccaneer", "Psi"],
            aliases=["brickell", "eti", "ice", "glaive lord"],
        )
        assert "sauda" in matchers.single and "psi" in matchers.single
        assert "monkey buccaneer" in matchers.multi
        assert "glaive lord" in matchers.multi
        assert "brickell" in matchers.single
        assert "eti" not in matchers.single  # length filter
        assert "ice" not in matchers.single  # stoplist

    def test_custom_stoplist(self):
        matchers = name_guard.build_matchers(
            canonicals=["Faust"],
            aliases=["heathcliff"],
            stoplist=frozenset({"faust"}),
        )
        assert "faust" not in matchers.single
        assert "heathcliff" in matchers.single

    def test_names_present_whole_word_and_substring(self):
        matchers = name_guard.build_matchers(["Sauda", "Glaive Lord"], [])
        found = name_guard.names_present("the glaive lord beats sauda's record", matchers)
        assert found == {"glaive lord", "sauda"}

    def test_offending_numbers_comma_normalized_substring(self):
        assert name_guard.offending_numbers("costs 48210", "price 48,210") == ()
        assert name_guard.offending_numbers("costs 5000", "cap 150000") == ()  # substring leniency
        assert name_guard.offending_numbers("costs 777", "cap 150000") == ("777",)


class TestAbsenceGuard:
    def _register_paragon(self):
        apos = r"['’]"
        absence_guard.register_existence_attribute(
            absence_guard.ExistenceAttribute(
                name="paragon",
                affirm_re=re.compile(
                    r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)" + apos + r"s Paragon\b",
                ),
                deny_res=(
                    re.compile(r"\bno\s+(?:\w+\s+){0,2}paragon\b"),
                    re.compile(
                        r"\b(?:does\s+not|doesn" + apos + r"?t)"
                        r"\s+have\s+(?:a\s+|an\s+|any\s+)?(?:\w+\s+){0,2}paragon\b",
                    ),
                ),
                exclude_qualifiers=frozenset({"second", "another"}),
                owner_subsystem="btd6",
            ),
        )

    def test_contradicted_absence_fires(self):
        self._register_paragon()
        haystack = "Monkey Buccaneer's Paragon is Navarch of the Seas."
        answer = "The Monkey Buccaneer does not have a paragon."
        offending = absence_guard.contradicted_absence_claims(answer, haystack)
        assert offending and "does not have a paragon" in offending[0]

    def test_true_negative_never_blocked(self):
        self._register_paragon()
        haystack = "Monkey Buccaneer's Paragon is Navarch of the Seas."
        assert (
            absence_guard.contradicted_absence_claims(
                "The Tack Shooter has no paragon.", haystack,
            )
            == ()
        )

    def test_qualifier_excluded(self):
        self._register_paragon()
        haystack = "Monkey Buccaneer's Paragon is Navarch of the Seas."
        assert (
            absence_guard.contradicted_absence_claims(
                "The Monkey Buccaneer has no second paragon.", haystack,
            )
            == ()
        )

    def test_empty_registry_never_fires(self):
        assert absence_guard.contradicted_absence_claims("no paragon", "x") == ()


class TestVerifyRegistry:
    def test_no_verifier_vacuously_grounded(self):
        assert verify.verify_reply("general.nl_answer", "anything").grounded

    def test_raising_verifier_fails_closed(self):
        def bad(reply, facts, tools):
            raise RuntimeError("index broken")

        verify.register_grounding_verifier("d.answer", bad, owner_subsystem="d")
        verdict = verify.verify_reply("d.answer", "text")
        assert not verdict.grounded
        assert "verifier_error" in verdict.notes

    def test_constraint_builder_lists_offenders(self):
        verdict = verify.GroundingResult(
            grounded=False,
            reason_code="grounding_failed",
            used_fact_keys=(),
            offending_names=("navarch",),
            offending_numbers=("777",),
            offending_absence_claims=("X has no paragon.",),
        )
        text = verify.build_grounding_constraint(verdict, domain_label="BTD6")
        assert "navarch" in text and "777" in text
        assert "DOES list the thing" in text
        assert "BTD6" in text


class TestRegenerateOnceLoop:
    def _verifier(self, allowed: str):
        def fn(reply, facts, tools):
            if allowed in reply:
                return verify.GROUNDED
            return verify.GroundingResult(
                grounded=False,
                reason_code="grounding_failed",
                used_fact_keys=(),
                offending_names=("badname",),
            )

        return fn

    def test_grounded_first_pass(self):
        verify.register_grounding_verifier(
            "d.answer", self._verifier("good"), owner_subsystem="d",
        )

        async def regen(constraint):
            raise AssertionError("must not regenerate")

        outcome = run(
            verify.verify_and_regenerate_once(
                "d.answer", "good answer", regenerate=regen,
            ),
        )
        assert outcome.grounded and not outcome.retry_attempted

    def test_retry_rescued(self):
        verify.register_grounding_verifier(
            "d.answer", self._verifier("good"), owner_subsystem="d",
        )
        seen = {}

        async def regen(constraint):
            seen["constraint"] = constraint
            return "good corrected answer", False

        outcome = run(
            verify.verify_and_regenerate_once("d.answer", "bad", regenerate=regen),
        )
        assert outcome.grounded and outcome.retry_rescued
        assert outcome.reply_text == "good corrected answer"
        assert "GROUNDING CORRECTION" in seen["constraint"]
        assert "badname" in seen["constraint"]

    def test_floor_on_double_failure(self):
        verify.register_grounding_verifier(
            "d.answer", self._verifier("good"), owner_subsystem="d",
        )

        async def regen(constraint):
            return "still bad", False

        outcome = run(
            verify.verify_and_regenerate_once("d.answer", "bad", regenerate=regen),
        )
        assert not outcome.grounded
        assert outcome.retry_attempted and not outcome.retry_rescued
        assert not outcome.degraded

    def test_degraded_retry_is_provider_outage_not_grounding(self):
        verify.register_grounding_verifier(
            "d.answer", self._verifier("good"), owner_subsystem="d",
        )

        async def regen(constraint):
            return "", True  # provider outage on retry

        outcome = run(
            verify.verify_and_regenerate_once("d.answer", "bad", regenerate=regen),
        )
        assert not outcome.grounded
        assert outcome.degraded

    def test_regenerate_fault_contained(self):
        verify.register_grounding_verifier(
            "d.answer", self._verifier("good"), owner_subsystem="d",
        )

        async def regen(constraint):
            raise RuntimeError("gateway broke somehow")

        outcome = run(
            verify.verify_and_regenerate_once("d.answer", "bad", regenerate=regen),
        )
        assert not outcome.grounded
