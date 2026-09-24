from __future__ import annotations

import math

from modelfit import score
from modelfit.runner import Result


def _result(**kw) -> Result:
    base = dict(
        task_id="t1",
        quadrant="NEITHER",
        model="claude-haiku-4-5",
        effort="off",
        trial=0,
        passed=True,
        detail="ok",
        in_tokens=100,
        out_tokens=50,
        cost_usd=0.01,
        latency_s=0.5,
    )
    base.update(kw)
    return Result(**base)


class TestByConfig:
    def test_aggregates_pass_rate_and_cost(self):
        results = [
            _result(passed=True, cost_usd=0.01),
            _result(passed=True, cost_usd=0.01),
            _result(passed=False, cost_usd=0.01),
        ]
        stats = score.by_config(results)
        assert len(stats) == 1
        s = stats[0]
        assert s.n == 3
        assert s.solved == 2
        assert s.pass_rate == 2 / 3
        assert s.total_cost == 0.03
        assert math.isclose(s.cost_per_solved, 0.015)

    def test_zero_solved_gives_inf_cost(self):
        results = [_result(passed=False, cost_usd=0.01)]
        stats = score.by_config(results)
        assert stats[0].cost_per_solved == math.inf

    def test_separates_by_model_and_effort(self):
        results = [
            _result(model="claude-haiku-4-5", effort="off"),
            _result(model="claude-haiku-4-5", effort="high"),
            _result(model="claude-opus-4-8", effort="off"),
        ]
        stats = score.by_config(results)
        assert len(stats) == 3


class TestPareto:
    def test_dominated_config_excluded(self):
        stats = [
            score.ConfigStat("a", "off", 10, 10, 1.0, 0.10, 0.010),
            score.ConfigStat("b", "off", 10, 10, 1.0, 0.20, 0.020),  # dominated by a
        ]
        front = score.pareto(stats)
        assert [s.model for s in front] == ["a"]

    def test_tradeoff_configs_both_kept(self):
        # a is cheaper but less reliable; b is more reliable but pricier -> both rational
        stats = [
            score.ConfigStat("a", "off", 10, 5, 0.5, 0.05, 0.010),
            score.ConfigStat("b", "high", 10, 9, 0.9, 0.45, 0.050),
        ]
        front = score.pareto(stats)
        assert {s.model for s in front} == {"a", "b"}

    def test_exact_tie_neither_dominates(self):
        stats = [
            score.ConfigStat("a", "off", 10, 10, 1.0, 0.10, 0.010),
            score.ConfigStat("b", "off", 10, 10, 1.0, 0.10, 0.010),
        ]
        front = score.pareto(stats)
        assert len(front) == 2


class TestPerQuadrant:
    def test_picks_cheapest_reliable_config_per_quadrant(self):
        results = [
            _result(
                quadrant="EFFORT",
                model="claude-haiku-4-5",
                effort="off",
                passed=False,
                cost_usd=0.001,
            ),
            _result(
                quadrant="EFFORT",
                model="claude-sonnet-5",
                effort="high",
                passed=True,
                cost_usd=0.10,
            ),
            _result(
                quadrant="MODEL", model="claude-opus-4-8", effort="off", passed=True, cost_usd=0.05
            ),
        ]
        picks = score.per_quadrant(results)
        by_quad = {p.quadrant: p for p in picks}
        assert by_quad["EFFORT"].model == "claude-sonnet-5"
        assert by_quad["EFFORT"].effort == "high"
        assert by_quad["MODEL"].model == "claude-opus-4-8"

    def test_quadrant_with_no_solves_reports_inf(self):
        results = [_result(quadrant="BOTH", passed=False)]
        picks = score.per_quadrant(results)
        assert picks[0].cost_per_solved == math.inf

    def test_output_ordered_by_canonical_quadrant_order(self):
        results = [
            _result(quadrant="BOTH"),
            _result(quadrant="NEITHER"),
            _result(quadrant="MODEL"),
            _result(quadrant="EFFORT"),
        ]
        picks = score.per_quadrant(results)
        assert [p.quadrant for p in picks] == ["NEITHER", "EFFORT", "MODEL", "BOTH"]
