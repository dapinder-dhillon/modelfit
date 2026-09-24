"""
Task loader.

Tasks are plain data (an id, a quadrant tag, a prompt, a verifier name, and a
fixture) — nothing about them requires Python. So they live as YAML files, one
task per file, in a `tasks/` directory (see the bundled examples there). This
is the file people actually touch to make the tool theirs: drop a new
`tasks/my_task.yaml` in, no code required. The four quadrants:

    NEITHER : recall / boilerplate   -> cheap model, low effort wins on cost
    EFFORT  : self-contained logic   -> effort matters, model barely does
    MODEL   : breadth / judgement    -> model matters, effort barely does
    BOTH    : long multi-step change -> only big model + high effort is reliable

If you need a genuinely new *kind* of check (not just a new task), that's the
one place Python is still required: add a verifier to `verifiers.REGISTRY` and
keep it deterministic (see the module docstring in verifiers.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import verifiers

QUADRANTS = ["NEITHER", "EFFORT", "MODEL", "BOTH"]

_REQUIRED_FIELDS = {"id", "quadrant", "prompt", "verifier", "fixture"}
_KNOWN_FIELDS = _REQUIRED_FIELDS | {"max_tokens"}


@dataclass(frozen=True)
class Task:
    id: str
    quadrant: str  # NEITHER | EFFORT | MODEL | BOTH
    prompt: str  # what the model is asked to do
    verifier: str  # name of a function in verifiers.py
    fixture: dict[str, Any] = field(default_factory=dict)  # ground truth for the verifier
    max_tokens: int = 1500


def _task_from_dict(data: dict[str, Any], source: Path) -> Task:
    if not isinstance(data, dict):
        raise ValueError(f"{source}: expected a YAML mapping at the top level")

    missing = _REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"{source}: missing required field(s) {sorted(missing)}")

    unknown = data.keys() - _KNOWN_FIELDS
    if unknown:
        raise ValueError(f"{source}: unknown field(s) {sorted(unknown)}")

    if data["quadrant"] not in QUADRANTS:
        raise ValueError(f"{source}: quadrant must be one of {QUADRANTS}, got {data['quadrant']!r}")

    if data["verifier"] not in verifiers.REGISTRY:
        raise ValueError(
            f"{source}: unknown verifier {data['verifier']!r}, "
            f"choose from {sorted(verifiers.REGISTRY)}"
        )

    if not isinstance(data["fixture"], dict):
        raise ValueError(f"{source}: fixture must be a mapping")

    kwargs: dict[str, Any] = {k: data[k] for k in _REQUIRED_FIELDS}
    if "max_tokens" in data:
        kwargs["max_tokens"] = data["max_tokens"]
    return Task(**kwargs)


def load_tasks(directory: str | Path = "tasks") -> list[Task]:
    """Load every `*.yaml`/`*.yml` file in `directory` as a Task. Returns an
    empty list if the directory doesn't exist (a fresh checkout with no tasks
    defined yet), rather than erroring."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []

    paths = sorted(dir_path.glob("*.yaml")) + sorted(dir_path.glob("*.yml"))
    tasks = [_task_from_dict(yaml.safe_load(p.read_text()), p) for p in paths]

    seen: dict[str, Path] = {}
    for task, path in zip(tasks, paths, strict=True):
        if task.id in seen:
            raise ValueError(f"duplicate task id {task.id!r} in {seen[task.id]} and {path}")
        seen[task.id] = path

    return tasks
