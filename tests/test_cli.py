from __future__ import annotations

from pathlib import Path

import pytest

from modelfit.cli import main

_TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"


def test_unknown_model_exits_with_clear_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--models", "bogus-model", "--no-cache"])
    assert exc.value.code == 2
    assert "unknown model" in capsys.readouterr().err


def test_unknown_effort_exits_with_clear_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--efforts", "medium", "--no-cache"])
    assert exc.value.code == 2
    assert "unknown effort" in capsys.readouterr().err


def test_missing_tasks_dir_exits_with_clear_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--no-cache", "--tasks", str(tmp_path / "nope")])
    assert exc.value.code == 2
    assert "no *.yaml task files found" in capsys.readouterr().err


def test_valid_mock_run_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(
        [
            "run",
            "--mock",
            "--no-cache",
            "--models",
            "claude-haiku-4-5",
            "--efforts",
            "off",
            "--trials",
            "1",
            "--tasks",
            str(_TASKS_DIR),
            "--out",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 0
    assert (tmp_path / "out" / "report.md").exists()
    assert (tmp_path / "out" / "results.csv").exists()
