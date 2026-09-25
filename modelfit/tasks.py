from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from modelfit import verifiers

QUADRANTS = ["NEITHER", "EFFORT", "MODEL", "BOTH"]
DEFAULT_TASKS_DIRECTORY = "tasks"
DEFAULT_MAX_TOKENS = 1500
YAML_PATTERNS = ("*.yaml", "*.yml")
MAX_TOKENS_FIELD = "max_tokens"

_REQUIRED_FIELDS = {"id", "quadrant", "prompt", "verifier", "fixture"}
_KNOWN_FIELDS = _REQUIRED_FIELDS | {MAX_TOKENS_FIELD}


@dataclass(frozen=True)
class Task:
    id: str
    quadrant: str
    prompt: str
    verifier: str
    fixture: dict[str, Any] = field(default_factory=dict)
    max_tokens: int = DEFAULT_MAX_TOKENS


def load_tasks(directory: str | Path = DEFAULT_TASKS_DIRECTORY) -> list[Task]:
    tasks_directory = Path(directory)
    if tasks_directory.is_dir() is False:
        return []
    paths = _task_file_paths(tasks_directory=tasks_directory)
    tasks = [_task_from_dict(data=yaml.safe_load(path.read_text()), source=path) for path in paths]
    _validate_unique_ids(tasks=tasks, paths=paths)
    return tasks


def _task_file_paths(tasks_directory: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in YAML_PATTERNS:
        paths += sorted(tasks_directory.glob(pattern))
    return paths


def _task_from_dict(data: dict[str, Any], source: Path) -> Task:
    _validate_task_data(data=data, source=source)
    return Task(**_task_arguments(data=data))


def _task_arguments(data: dict[str, Any]) -> dict[str, Any]:
    task_arguments: dict[str, Any] = {
        field_name: data[field_name] for field_name in _REQUIRED_FIELDS
    }
    if MAX_TOKENS_FIELD in data:
        task_arguments[MAX_TOKENS_FIELD] = data[MAX_TOKENS_FIELD]
    return task_arguments


def _validate_task_data(data: dict[str, Any], source: Path) -> None:
    _validate_is_mapping(data=data, source=source)
    _validate_no_missing_fields(data=data, source=source)
    _validate_no_unknown_fields(data=data, source=source)
    _validate_quadrant(data=data, source=source)
    _validate_verifier(data=data, source=source)
    _validate_fixture(data=data, source=source)


def _validate_is_mapping(data: dict[str, Any], source: Path) -> None:
    if isinstance(data, dict) is False:
        raise ValueError(f"{source}: expected a YAML mapping at the top level")


def _validate_no_missing_fields(data: dict[str, Any], source: Path) -> None:
    missing = _REQUIRED_FIELDS - data.keys()
    if len(missing) > 0:
        raise ValueError(f"{source}: missing required field(s) {sorted(missing)}")


def _validate_no_unknown_fields(data: dict[str, Any], source: Path) -> None:
    unknown = data.keys() - _KNOWN_FIELDS
    if len(unknown) > 0:
        raise ValueError(f"{source}: unknown field(s) {sorted(unknown)}")


def _validate_quadrant(data: dict[str, Any], source: Path) -> None:
    if data["quadrant"] not in QUADRANTS:
        raise ValueError(f"{source}: quadrant must be one of {QUADRANTS}, got {data['quadrant']!r}")


def _validate_verifier(data: dict[str, Any], source: Path) -> None:
    if data["verifier"] not in verifiers.REGISTRY:
        raise ValueError(
            f"{source}: unknown verifier {data['verifier']!r}, "
            f"choose from {sorted(verifiers.REGISTRY)}"
        )


def _validate_fixture(data: dict[str, Any], source: Path) -> None:
    if isinstance(data["fixture"], dict) is False:
        raise ValueError(f"{source}: fixture must be a mapping")


def _validate_unique_ids(tasks: list[Task], paths: list[Path]) -> None:
    seen: dict[str, Path] = dict()
    for task, path in zip(tasks, paths, strict=True):
        if task.id in seen:
            raise ValueError(f"duplicate task id {task.id!r} in {seen[task.id]} and {path}")
        seen[task.id] = path
