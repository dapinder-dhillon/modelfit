from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from modelfit import providers
from modelfit.runner import run
from modelfit.tasks import load_tasks

_TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
_ALL_TASKS = load_tasks(_TASKS_DIR)
_ONE_TASK = _ALL_TASKS[:1]


class TestCacheAdditivity:
    def test_mock_results_are_not_reused_as_real_results(self, tmp_path, monkeypatch):
        cache_path = str(tmp_path / "results.json")
        calls = []

        def fake_real_call(model, effort, prompt, max_tokens):
            calls.append(prompt)
            return providers.Call(
                text="def backoff_delays(attempts): return [2**i for i in range(attempts - 1)]",
                in_tokens=10,
                out_tokens=20,
                latency_s=0.1,
            )

        monkeypatch.setattr(providers, "call_real", fake_real_call)
        mock_result = run(
            _ONE_TASK, ["claude-haiku-4-5"], ["off"], mode="mock", cache_path=cache_path
        )
        real_result = run(
            _ONE_TASK, ["claude-haiku-4-5"], ["off"], mode="real", cache_path=cache_path
        )

        assert len(calls) == 1
        assert mock_result[0].detail.startswith("mock ")
        assert real_result[0].detail == "tests passed"

    def test_changed_task_is_recomputed(self, tmp_path, monkeypatch):
        cache_path = str(tmp_path / "results.json")
        calls = []
        real_call_mock = providers.call_mock

        def counting_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial=0):
            calls.append(prompt)
            return real_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial)

        monkeypatch.setattr(providers, "call_mock", counting_call_mock)
        changed_task = replace(_ONE_TASK[0], prompt=_ONE_TASK[0].prompt + " More detail.")
        run(_ONE_TASK, ["claude-haiku-4-5"], ["off"], mode="mock", cache_path=cache_path)
        run([changed_task], ["claude-haiku-4-5"], ["off"], mode="mock", cache_path=cache_path)

        assert len(calls) == 2

    def test_rerun_does_not_recompute_existing_cells(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "results.json"
        calls: list[str] = []
        real_call_mock = providers.call_mock

        def counting_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial=0):
            calls.append(f"{model}|{effort}|{trial}")
            return real_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial)

        monkeypatch.setattr(providers, "call_mock", counting_call_mock)

        run(
            _ONE_TASK,
            ["claude-haiku-4-5"],
            ["off"],
            mode="mock",
            trials=1,
            cache_path=str(cache_path),
        )
        first_call_count = len(calls)
        assert first_call_count == 1

        run(
            _ONE_TASK,
            ["claude-haiku-4-5"],
            ["off"],
            mode="mock",
            trials=1,
            cache_path=str(cache_path),
        )
        assert len(calls) == first_call_count  # no new calls: fully cached

    def test_adding_a_model_only_computes_new_cells(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "results.json"
        calls: list[str] = []
        real_call_mock = providers.call_mock

        def counting_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial=0):
            calls.append(model)
            return real_call_mock(model, effort, prompt, max_tokens, quadrant, task_id, trial)

        monkeypatch.setattr(providers, "call_mock", counting_call_mock)

        run(
            _ONE_TASK,
            ["claude-haiku-4-5"],
            ["off"],
            mode="mock",
            trials=1,
            cache_path=str(cache_path),
        )
        run(
            _ONE_TASK,
            ["claude-haiku-4-5", "claude-sonnet-5"],
            ["off"],
            mode="mock",
            trials=1,
            cache_path=str(cache_path),
        )
        assert calls == ["claude-haiku-4-5", "claude-sonnet-5"]

    def test_cache_written_to_disk(self, tmp_path):
        cache_path = tmp_path / "results.json"
        run(
            _ONE_TASK,
            ["claude-haiku-4-5"],
            ["off"],
            mode="mock",
            trials=2,
            cache_path=str(cache_path),
        )
        data = json.loads(cache_path.read_text())
        assert len(data) == 2  # one entry per trial

    def test_corrupted_cache_does_not_crash(self, tmp_path):
        cache_path = tmp_path / "results.json"
        cache_path.write_text("{not valid json")
        results = run(
            _ONE_TASK,
            ["claude-haiku-4-5"],
            ["off"],
            mode="mock",
            trials=1,
            cache_path=str(cache_path),
        )
        assert len(results) == 1


class TestMockDeterminism:
    def test_two_full_runs_produce_identical_results(self, tmp_path):
        r1 = run(
            _ALL_TASKS,
            ["claude-haiku-4-5", "claude-opus-4-8"],
            ["off", "high"],
            mode="mock",
            trials=2,
            cache_path=None,
        )
        r2 = run(
            _ALL_TASKS,
            ["claude-haiku-4-5", "claude-opus-4-8"],
            ["off", "high"],
            mode="mock",
            trials=2,
            cache_path=None,
        )
        assert [vars(r) for r in r1] == [vars(r) for r in r2]
