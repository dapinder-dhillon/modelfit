"""
Tests for CLI-mode (`--via-cli claude|codex`). These NEVER call a real CLI --
`subprocess.run` is monkeypatched throughout, matching the pattern used to keep
`verify_python_callable` tests offline. Real-CLI verification was done by hand
(see the comment above `AGENTS` in providers.py); these tests only prove the
plumbing and the honesty rules around it.
"""

from __future__ import annotations

import json
from typing import Any

from modelfit import providers, runner
from modelfit.report import _money, write_markdown
from modelfit.score import ConfigStat, QuadrantPick, by_config, pareto
from modelfit.tasks import Task


class _FakeCompleted:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _task(**overrides: Any) -> Task:
    base: dict[str, Any] = dict(
        id="t1",
        quadrant="NEITHER",
        prompt='reply with the JSON object {"ok": true}',
        verifier="verify_json_equals",
        fixture={"expected": {"ok": True}},
    )
    base.update(overrides)
    return Task(**base)


class TestCallCliClaude:
    def test_success_is_parsed_and_verifier_passes(self, monkeypatch):
        payload = {
            "result": '{"ok": true}',
            "is_error": False,
            "total_cost_usd": 0.0123,
            "usage": {"input_tokens": 12, "output_tokens": 34},
        }

        def fake_run(argv, **kwargs):
            assert argv[0] == "claude"
            assert "--model" in argv and "claude-haiku-4-5" in argv
            assert "--effort" in argv and "low" in argv
            return _FakeCompleted(json.dumps(payload))

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, effort = providers.call_cli("claude", "claude-haiku-4-5", "low", "say ok", 500)
        assert effort == "low"  # controllable -> modelfit's own vocabulary, not the CLI's
        assert call.error is None
        assert call.cost_usd == 0.0123
        assert call.in_tokens == 12
        assert call.out_tokens == 34
        assert call.text == '{"ok": true}'

    def test_off_effort_has_no_equivalent_and_is_reported_as_na(self, monkeypatch):
        def fake_run(argv, **kwargs):
            assert "--effort" not in argv  # off has no equivalent on this CLI: skip the flag
            return _FakeCompleted(json.dumps({"result": "ok", "is_error": False}))

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        _call, effort = providers.call_cli("claude", "claude-haiku-4-5", "off", "say ok", 500)
        assert effort == "n/a"

    def test_nonzero_exit_fails_with_stderr_tail_as_detail(self, monkeypatch):
        def fake_run(argv, **kwargs):
            return _FakeCompleted(
                json.dumps({"result": "", "is_error": True, "usage": {}}),
                stderr="line one\nmodel not found",
                returncode=1,
            )

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, _effort = providers.call_cli("claude", "bogus", "low", "say ok", 500)
        assert call.error == "model not found"
        assert call.text == ""

    def test_usage_absent_leaves_cost_unknown(self, monkeypatch):
        def fake_run(argv, **kwargs):
            return _FakeCompleted(json.dumps({"result": "ok", "is_error": False}))

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, _effort = providers.call_cli("claude", "claude-haiku-4-5", "low", "say ok", 500)
        assert call.in_tokens == 0
        assert call.out_tokens == 0
        assert call.cost_usd is None

    def test_reported_tokens_without_direct_cost_fall_back_to_pricing(self, monkeypatch):
        payload = {
            "result": "ok",
            "is_error": False,
            "usage": {"input_tokens": 1000, "output_tokens": 1000},
        }

        def fake_run(argv, **kwargs):
            return _FakeCompleted(json.dumps(payload))

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, _effort = providers.call_cli("claude", "claude-haiku-4-5", "low", "say ok", 500)
        assert call.cost_usd == providers.cost_usd("claude-haiku-4-5", 1000, 1000)


class TestCallCliCodex:
    def test_success_event_stream_is_parsed(self, monkeypatch):
        events = [
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": '{"ok": true}'},
            },
            {"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 9}},
        ]

        def fake_run(argv, **kwargs):
            assert argv[0] == "codex"
            assert "-m" in argv and "gpt-5.1" in argv
            assert "-c" in argv and "model_reasoning_effort=none" in argv
            return _FakeCompleted("\n".join(json.dumps(e) for e in events))

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/codex")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, effort = providers.call_cli("codex", "gpt-5.1", "off", "say ok", 500)
        assert effort == "off"  # codex DOES have an off-equivalent ("none")
        assert call.error is None
        assert call.text == '{"ok": true}'
        assert call.in_tokens == 5
        assert call.out_tokens == 9

    def test_turn_failed_event_fails_with_message_as_detail(self, monkeypatch):
        events = [
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "error", "message": "the model is not supported"},
            {"type": "turn.failed", "error": {"message": "the model is not supported"}},
        ]

        def fake_run(argv, **kwargs):
            return _FakeCompleted("\n".join(json.dumps(e) for e in events), returncode=1)

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/codex")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, _effort = providers.call_cli("codex", "bogus", "low", "say ok", 500)
        assert call.error == "the model is not supported"
        assert call.text == ""

    def test_stray_plain_text_stdout_lines_are_skipped(self, monkeypatch):
        stdout = "Reading additional input from stdin...\n" + json.dumps(
            {"type": "turn.failed", "message": "boom"}
        )

        def fake_run(argv, **kwargs):
            return _FakeCompleted(stdout, returncode=1)

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/codex")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        call, _effort = providers.call_cli("codex", "gpt-5.1", "low", "say ok", 500)
        assert call.error == "boom"


class TestCallCliMissingExecutable:
    def test_missing_binary_raises_a_clear_error(self, monkeypatch):
        monkeypatch.setattr(providers.shutil, "which", lambda _name: None)
        try:
            providers.call_cli("claude", "claude-haiku-4-5", "low", "say ok", 500)
        except RuntimeError as e:
            assert "claude" in str(e)
            assert "--real" in str(e) or "--mock" in str(e)
        else:
            raise AssertionError("expected RuntimeError for a missing CLI binary")


class TestRunnerViaCli:
    def test_run_marks_passing_and_failing_cells_correctly(self, monkeypatch, tmp_path):
        good = _task(id="good")
        bad = _task(id="bad", fixture={"expected": {"ok": False}})

        def fake_run(argv, **kwargs):
            return _FakeCompleted(
                json.dumps(
                    {
                        "result": '{"ok": true}',
                        "is_error": False,
                        "total_cost_usd": 0.001,
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                )
            )

        monkeypatch.setattr(providers.shutil, "which", lambda _name: "/usr/bin/claude")
        monkeypatch.setattr(providers.subprocess, "run", fake_run)

        results = runner.run(
            [good, bad],
            ["claude-haiku-4-5"],
            ["low"],
            mode="cli",
            agent="claude",
            trials=1,
            cache_path=str(tmp_path / "cache.json"),
        )
        by_id = {r.task_id: r for r in results}
        assert by_id["good"].passed is True
        assert by_id["bad"].passed is False
        assert by_id["good"].effort == "low"
        assert by_id["good"].cost_usd == 0.001

    def test_cli_mode_requires_an_agent(self):
        try:
            runner.run([_task()], ["claude-haiku-4-5"], ["low"], mode="cli", cache_path=None)
        except ValueError as e:
            assert "agent" in str(e)
        else:
            raise AssertionError("expected ValueError when mode='cli' has no agent")


class TestUnknownCostReporting:
    def test_score_and_report_handle_none_cost_without_crashing(self, tmp_path):
        results = [
            runner.Result(
                task_id="t1",
                quadrant="NEITHER",
                model="gpt-5.1",
                effort="n/a",
                trial=0,
                passed=True,
                detail="cli call",
                in_tokens=0,
                out_tokens=0,
                cost_usd=None,
                latency_s=1.0,
            )
        ]
        stats = by_config(results)
        assert stats[0].cost_per_solved is None
        assert _money(stats[0].cost_per_solved) == "n/a"

        front = pareto(stats)
        assert stats[0] in front  # can't be proven dominated with an unknown cost

        picks = [
            QuadrantPick("NEITHER", "gpt-5.1", "n/a", 1.0, None),
        ]
        out_path = tmp_path / "report.md"
        write_markdown(stats, front, picks, str(out_path), False, "cli (codex)")
        text = out_path.read_text()
        assert "n/a" in text
        assert "CLI mode caveat" in text
        assert "effort axis is not controlled" in text

    def test_config_stat_with_known_cost_still_formats_normally(self):
        stat = ConfigStat("claude-haiku-4-5", "low", 4, 4, 1.0, 0.02, 0.005)
        assert _money(stat.cost_per_solved) == "$0.00500"
