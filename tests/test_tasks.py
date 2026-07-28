from __future__ import annotations

from pathlib import Path

import pytest

from modelfit.tasks import load_tasks

_VALID = """
id: my_task
quadrant: EFFORT
prompt: do the thing
verifier: verify_json_equals
fixture:
  expected: {"a": 1}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content)


class TestLoadTasks:
    def test_missing_directory_returns_empty(self, tmp_path):
        assert load_tasks(tmp_path / "does_not_exist") == []

    def test_loads_a_valid_task(self, tmp_path):
        _write(tmp_path, "my_task.yaml", _VALID)
        tasks = load_tasks(tmp_path)
        assert len(tasks) == 1
        assert tasks[0].id == "my_task"
        assert tasks[0].quadrant == "EFFORT"
        assert tasks[0].max_tokens == 1500  # default

    def test_max_tokens_override(self, tmp_path):
        _write(tmp_path, "my_task.yaml", _VALID + "max_tokens: 3000\n")
        tasks = load_tasks(tmp_path)
        assert tasks[0].max_tokens == 3000

    def test_missing_required_field_raises(self, tmp_path):
        content = _VALID.replace("quadrant: EFFORT\n", "")
        _write(tmp_path, "bad.yaml", content)
        with pytest.raises(ValueError, match="missing required field"):
            load_tasks(tmp_path)

    def test_unknown_field_raises(self, tmp_path):
        _write(tmp_path, "bad.yaml", _VALID + "typo_field: 1\n")
        with pytest.raises(ValueError, match="unknown field"):
            load_tasks(tmp_path)

    def test_bad_quadrant_raises(self, tmp_path):
        content = _VALID.replace("quadrant: EFFORT", "quadrant: SUPER_HARD")
        _write(tmp_path, "bad.yaml", content)
        with pytest.raises(ValueError, match="quadrant must be one of"):
            load_tasks(tmp_path)

    def test_unknown_verifier_raises(self, tmp_path):
        content = _VALID.replace("verifier: verify_json_equals", "verifier: verify_vibes")
        _write(tmp_path, "bad.yaml", content)
        with pytest.raises(ValueError, match="unknown verifier"):
            load_tasks(tmp_path)

    def test_non_mapping_fixture_raises(self, tmp_path):
        content = _VALID.replace('fixture:\n  expected: {"a": 1}', "fixture: not_a_mapping")
        _write(tmp_path, "bad.yaml", content)
        with pytest.raises(ValueError, match="fixture must be a mapping"):
            load_tasks(tmp_path)

    def test_duplicate_ids_across_files_raises(self, tmp_path):
        _write(tmp_path, "a.yaml", _VALID)
        _write(tmp_path, "b.yaml", _VALID)
        with pytest.raises(ValueError, match="duplicate task id"):
            load_tasks(tmp_path)

    def test_bundled_example_tasks_load_cleanly(self):
        repo_tasks_dir = Path(__file__).resolve().parent.parent / "tasks"
        tasks = load_tasks(repo_tasks_dir)
        assert len(tasks) == 5
        assert {t.quadrant for t in tasks} == {"NEITHER", "EFFORT", "MODEL", "BOTH"}
        assert len({t.id for t in tasks}) == 5
