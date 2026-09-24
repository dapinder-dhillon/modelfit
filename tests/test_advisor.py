"""
Tests for the advisor.

The advisor is a heuristic, so the tests are about the properties that make a
heuristic trustworthy rather than about it being right every time:

* the canonical classifications hold (the mechanism does what it claims),
* every verdict explains itself (no opaque scores),
* it is deterministic (same text -> same verdict, always),
* it never claims confidence it hasn't earned,
* and its adversarial weakness is *documented*, not asserted away.
"""

from __future__ import annotations

import json
from pathlib import Path

from modelfit import advice_report, advisor, history, project
from modelfit.evalset import evaluate, load_cases

_CASES = Path(__file__).resolve().parent.parent / "eval" / "advisor_cases.yaml"

BOILERPLATE = "Write a Dockerfile for a Python 3.12 Flask app that exposes port 8000."
EFFORT_TASK = "Fix this retry helper so it never sleeps after the final attempt."
MODEL_TASK = "Review this IAM policy and explain the security risks."
WEAK_JUDGEMENT_TASK = "Review the list of service names and return it sorted alphabetically."
BOTH_TASK = (
    "Refactor the payment module across all three services so no service calls the legacy "
    "gateway directly, then migrate the remaining callers and update the integration tests."
)


class TestCanonicalClassifications:
    def test_boilerplate_is_neither(self) -> None:
        assert advisor.estimate(BOILERPLATE).quadrant == "NEITHER"

    def test_negation_plus_ordering_is_effort(self) -> None:
        assert advisor.estimate(EFFORT_TASK).quadrant == "EFFORT"

    def test_judgement_wording_is_model(self) -> None:
        assert advisor.estimate(MODEL_TASK).quadrant == "MODEL"

    def test_breadth_plus_conditions_is_both(self) -> None:
        assert advisor.estimate(BOTH_TASK).quadrant == "BOTH"

    def test_plan_uses_real_model_ids(self) -> None:
        from modelfit.providers import EFFORT_BUDGETS, MODELS

        for quadrant in advisor.SHAPES:
            model, effort, _ = advisor.plan_for(quadrant)
            assert model in MODELS
            assert effort in EFFORT_BUDGETS


class TestExplainsItself:
    def test_reasons_are_never_empty(self) -> None:
        texts = [BOILERPLATE, EFFORT_TASK, MODEL_TASK, BOTH_TASK, "", "x", "do the thing"]
        texts += [case.task for case in load_cases(_CASES)]
        for text in texts:
            assert advisor.estimate(text).reasons, f"no reasons given for {text!r}"

    def test_silence_is_reported_as_silence_not_ease(self) -> None:
        est = advisor.estimate(BOILERPLATE)
        assert est.confidence == "low"
        assert est.hidden_knowledge_warning is True
        assert est.runner_up == "MODEL"
        assert "no signal fired" in " ".join(est.reasons)

    def test_teach_line_names_the_lever(self) -> None:
        assert "EFFORT" in advisor.teach_line(advisor.estimate(EFFORT_TASK))
        assert "MODEL" in advisor.teach_line(advisor.estimate(MODEL_TASK))

    def test_hedged_verdicts_carry_a_distinguishing_hint(self) -> None:
        est = advisor.estimate(BOTH_TASK)
        assert est.runner_up == "EFFORT"
        assert advisor.distinguish_hint(est.runner_up)
        assert advisor.distinguish_hint(None) == ""

    def test_review_next_to_a_mechanical_operation_is_not_judgement(self) -> None:
        """ "Review the list and sort it" -- "review" next to a mechanical verb
        (sort/order/alphabetize/...) is filler, not a real judgement call, so it
        shouldn't fire judgement at all. This must classify the same whether or
        not "review" is even in the sentence -- the word shouldn't change the
        answer for a task that's mechanical either way."""
        with_review = advisor.estimate(WEAK_JUDGEMENT_TASK)
        without_review = advisor.estimate("Return the list of service names sorted alphabetically.")
        assert with_review.quadrant == without_review.quadrant == "NEITHER"

    def test_a_lone_generic_judgement_word_does_not_claim_high_confidence(self) -> None:
        """A single generic judgement word with nothing else backing it up (no
        mechanical verb to discount it, no other signal) is still a coin flip,
        not a clear read -- confidence has to say so rather than commit."""
        est = advisor.estimate("Review this configuration.")
        assert est.quadrant == "MODEL"
        assert est.confidence == "medium"
        assert est.runner_up == "NEITHER"

    def test_multiple_judgement_words_still_earn_high_confidence(self) -> None:
        est = advisor.estimate(MODEL_TASK)
        assert est.quadrant == "MODEL"
        assert est.confidence == "high"
        assert est.runner_up is None

    def test_named_blind_spot_domain_gets_a_cautious_path_not_a_cheap_one(self) -> None:
        """Naming a documented blind-spot domain (SQL, crypto, timezone,
        concurrency) directly should route to a cautious MODEL start, not the
        cheap NEITHER default with a warning telling the user to override it."""
        for text in (
            "Make this SQL query faster.",
            "Implement RS256 JWT signature verification.",
            "Handle daylight-saving transitions when computing a duration.",
            "Make this counter thread-safe.",
        ):
            est = advisor.estimate(text)
            assert est.quadrant == "MODEL", f"{text!r} did not get the cautious path"
            assert est.confidence == "high", f"{text!r} should not be hedged"

    def test_at_once_is_concurrency_not_ordering(self) -> None:
        concurrent = advisor.estimate(
            "Two workers process the same payment webhook at once and charge the customer twice."
        )
        sequential = advisor.estimate(
            "Process the payment webhook, then charge the customer once the job finishes."
        )
        assert concurrent.quadrant == "MODEL"
        assert sequential.quadrant == "EFFORT"


class TestDeterminism:
    def test_same_text_gives_the_same_verdict(self) -> None:
        first = advisor.estimate(BOTH_TASK)
        second = advisor.estimate(BOTH_TASK)
        assert (first.quadrant, first.confidence, first.reasons) == (
            second.quadrant,
            second.confidence,
            second.reasons,
        )


class TestSelfEval:
    def test_clear_cases_meet_the_bar(self) -> None:
        result = evaluate(path=_CASES)
        assert result.clear_total >= 10
        assert result.clear_accuracy >= 0.70, f"clear accuracy fell to {result.clear_accuracy:.2f}"

    def test_adversarial_weakness_is_documented_not_fixed(self) -> None:
        """NOT a target to hit. Reading words instead of meaning fails on tasks whose
        difficulty the wording doesn't carry (crypto, SQL tuning, DST, concurrency) and
        on false triggers ('return the list without duplicates'). This test pins the
        gap so it stays visible: if adversarial accuracy ever matched clear accuracy,
        the eval set would have gone soft, not the advisor smart."""
        result = evaluate(path=_CASES)
        assert result.adversarial_total >= 10
        assert result.adversarial_accuracy <= result.clear_accuracy
        assert any(m.adversarial for m in result.misses)

    def test_cases_load_with_both_splits(self) -> None:
        cases = load_cases(_CASES)
        assert len(cases) >= 20
        assert {c.truth for c in cases} == {"NEITHER", "EFFORT", "MODEL", "BOTH"}
        assert all(c.note for c in cases)


class TestArtifacts:
    def test_report_shows_signals_confidence_and_caveat(self) -> None:
        text = advice_report.render(advisor.estimate(BOILERPLATE), chart_rel="c.png")
        assert "no signal fired" in text
        assert "Signal:** low" in text
        assert "Blind spot" in text
        assert "second option" in text
        assert "![Projected pass rate vs cost](c.png)" in text
        assert "not an oracle" in text

    def test_confident_report_skips_the_hedge(self) -> None:
        text = advice_report.render(advisor.estimate(MODEL_TASK))
        assert "second option" not in text
        assert "Blind spot" not in text

    def test_write_creates_the_file(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "advice.md"
        written = advice_report.write(advisor.estimate(EFFORT_TASK), str(target))
        assert Path(written).read_text().startswith("# modelfit advice")

    def test_projection_is_ordered_by_effort_for_an_effort_task(self) -> None:
        est = advisor.estimate(EFFORT_TASK)
        probs = [
            project.projected_cell(est.text, "claude-sonnet-5", effort, est.quadrant)[0]
            for effort in ("off", "low", "high")
        ]
        assert probs[0] < probs[1] < probs[2]

    def test_chart_is_optional_never_fatal(self, tmp_path: Path) -> None:
        drawn = project.chart(advisor.estimate(EFFORT_TASK), str(tmp_path / "c.png"))
        assert drawn in (True, False)


class TestHistory:
    def test_record_is_additive(self, tmp_path: Path) -> None:
        log = tmp_path / "history.json"
        history.record(advisor.estimate(EFFORT_TASK), path=log)
        history.record(advisor.estimate(MODEL_TASK), outcome="pass", path=log)
        entries = json.loads(log.read_text())
        assert [e["quadrant"] for e in entries] == ["EFFORT", "MODEL"]
        assert entries[0]["outcome"] is None
        assert entries[1]["outcome"] == "pass"

    def test_lessons_count_only_recorded_outcomes(self, tmp_path: Path) -> None:
        log = tmp_path / "history.json"
        history.record(advisor.estimate(EFFORT_TASK), path=log)
        history.record(advisor.estimate(MODEL_TASK), outcome="fail", path=log)
        text = " ".join(history.lessons(log))
        assert "1/2 asks have a recorded outcome" in text
        assert "0/1 recorded outcomes passed" in text

    def test_lessons_on_empty_history_say_so(self, tmp_path: Path) -> None:
        text = " ".join(history.lessons(tmp_path / "nothing.json"))
        assert "No advice history yet" in text

    def test_corrupt_history_does_not_crash(self, tmp_path: Path) -> None:
        log = tmp_path / "history.json"
        log.write_text("{not json")
        assert history.load(log) == []
