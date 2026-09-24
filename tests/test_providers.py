from __future__ import annotations

import pytest

from modelfit import providers


class TestStableUnit:
    def test_bounded_in_zero_one(self):
        v = providers._stable_unit("a", "b", "c")
        assert 0.0 <= v < 1.0

    def test_deterministic_for_same_inputs(self):
        a = providers._stable_unit("task", "model", "effort", "0")
        b = providers._stable_unit("task", "model", "effort", "0")
        assert a == b

    def test_differs_for_different_inputs(self):
        a = providers._stable_unit("task", "model", "effort", "0")
        b = providers._stable_unit("task", "model", "effort", "1")
        assert a != b


class TestCallMock:
    def test_reproducible_across_calls(self):
        call1, passed1 = providers.call_mock(
            "claude-sonnet-5", "high", "prompt text", 1500, "EFFORT", "backoff_delays", 0
        )
        call2, passed2 = providers.call_mock(
            "claude-sonnet-5", "high", "prompt text", 1500, "EFFORT", "backoff_delays", 0
        )
        assert passed1 == passed2
        assert call1.in_tokens == call2.in_tokens
        assert call1.out_tokens == call2.out_tokens

    def test_different_trial_can_change_outcome_draw(self):
        # not asserting a specific outcome, just that trial feeds the draw
        _, passed_a = providers.call_mock("claude-haiku-4-5", "off", "p", 100, "EFFORT", "t", 0)
        draws = {
            providers._stable_unit("t", "claude-haiku-4-5", "off", str(trial)) for trial in range(5)
        }
        assert len(draws) == 5  # each trial draws independently


class TestCostUsd:
    def test_matches_pricing_table(self):
        pin, pout = providers.PRICING["claude-sonnet-5"]
        cost = providers.cost_usd("claude-sonnet-5", 1_000_000, 1_000_000)
        assert cost == pytest.approx(pin + pout)

    def test_zero_tokens_is_zero_cost(self):
        assert providers.cost_usd("claude-haiku-4-5", 0, 0) == 0.0


class TestCallReal:
    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            providers.call_real("claude-sonnet-5", "off", "prompt", 100)
