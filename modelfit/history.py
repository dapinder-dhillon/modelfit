from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from modelfit.advisor import Estimate

OUTCOMES = ("pass", "fail")
PASS_OUTCOME = "pass"
FAIL_OUTCOME = "fail"
LOW_CONFIDENCE = "low"
UNKNOWN_QUADRANT = "?"
MODELFIT_HOME_ENVIRONMENT_VARIABLE = "MODELFIT_HOME"
DEFAULT_HOME_DIRECTORY_NAME = ".modelfit"
HISTORY_FILE_NAME = "history.json"
HISTORY_JSON_INDENT = 2
DOMINANT_SHAPE_SHARE = 0.4

DOMINANT_SHAPE_LESSONS = {
    "NEITHER": "Most of your asks look routine — your default config should be the cheap one.",
    "EFFORT": "Most of your asks are deliberation-shaped — effort is your usual lever, "
    "not a bigger model.",
    "MODEL": "Most of your asks need knowledge — paying for model tier is justified "
    "for your work.",
    "BOTH": "Most of your asks are long multi-step work — budget for a strong model at "
    "high effort, and for reading the diff.",
}

_NO_HISTORY_LESSON = (
    'No advice history yet. Run `modelfit advise "<your task>"` a few times, then '
    "come back — this reads only your own local log."
)

_STANDING_LESSON = (
    "Standing lesson: the advisor reads wording, not meaning. When it says low "
    "confidence, believe it — crypto, SQL tuning, timezone/DST and concurrency work all "
    "look boring in a one-line prompt."
)


def history_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    return _history_home() / HISTORY_FILE_NAME


def load(path: str | Path | None = None) -> list[dict[str, Any]]:
    history_file = history_path(path=path)
    if history_file.exists() is False:
        return []
    try:
        data = json.loads(history_file.read_text())
    except json.JSONDecodeError:
        print(f"warning: history at {history_file} is corrupted, starting fresh", file=sys.stderr)
        return []
    return _list_or_empty(data=data)


def record(
    task_estimate: Estimate,
    outcome: str | None = None,
    used_effort: str | None = None,
    path: str | Path | None = None,
) -> Path:
    _validate_outcome(outcome=outcome)
    history_file = history_path(path=path)
    entries = load(path=history_file)
    entries.append(
        _history_entry(task_estimate=task_estimate, outcome=outcome, used_effort=used_effort)
    )
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(json.dumps(entries, indent=HISTORY_JSON_INDENT))
    return history_file


def lessons(path: str | Path | None = None) -> list[str]:
    entries = load(path=path)
    if len(entries) == 0:
        return [_NO_HISTORY_LESSON, _STANDING_LESSON]
    lesson_lines: list[str] = []
    lesson_lines += _shape_lessons(entries=entries)
    lesson_lines += _low_confidence_lessons(entries=entries)
    lesson_lines += _calibration_lessons(entries=entries)
    lesson_lines.append(_STANDING_LESSON)
    return lesson_lines


def _history_home() -> Path:
    home = os.environ.get(MODELFIT_HOME_ENVIRONMENT_VARIABLE)
    if home is not None and len(home) > 0:
        return Path(home).expanduser()
    return Path.home() / DEFAULT_HOME_DIRECTORY_NAME


def _list_or_empty(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    return []


def _validate_outcome(outcome: str | None) -> None:
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {list(OUTCOMES)}, got {outcome!r}")


def _history_entry(
    task_estimate: Estimate, outcome: str | None, used_effort: str | None
) -> dict[str, Any]:
    return {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "text": task_estimate.text,
        "quadrant": task_estimate.quadrant,
        "confidence": task_estimate.confidence,
        "runner_up": task_estimate.runner_up,
        "effort_score": task_estimate.effort_score,
        "model_score": task_estimate.model_score,
        "start_tier": task_estimate.start_tier,
        "start_effort": task_estimate.start_effort,
        "hidden_knowledge_warning": task_estimate.hidden_knowledge_warning,
        "outcome": outcome,
        "used_effort": used_effort,
    }


def _shape_lessons(entries: list[dict[str, Any]]) -> list[str]:
    total = len(entries)
    shapes = Counter(str(entry.get("quadrant", UNKNOWN_QUADRANT)) for entry in entries)
    spread = ", ".join(f"{quadrant} {count}" for quadrant, count in shapes.most_common())
    shape_lessons = [f"Shapes you have asked about ({total} total): {spread}."]
    top_quadrant, top_count = shapes.most_common(1)[0]
    dominant = DOMINANT_SHAPE_LESSONS.get(top_quadrant, "")
    if len(dominant) > 0 and top_count / total >= DOMINANT_SHAPE_SHARE:
        shape_lessons.append(dominant)
    return shape_lessons


def _low_confidence_lessons(entries: list[dict[str, Any]]) -> list[str]:
    total = len(entries)
    low_count = sum(1 for entry in entries if entry.get("confidence") == LOW_CONFIDENCE)
    if low_count == 0:
        return []
    return [
        f"{low_count}/{total} verdicts were low confidence — the wording carried no signal. "
        "Those are the ones to double-check by hand, not to trust."
    ]


def _calibration_lessons(entries: list[dict[str, Any]]) -> list[str]:
    recorded = _recorded_entries(entries=entries)
    if len(recorded) == 0:
        return [
            "Calibration: 0 outcomes recorded, so nothing is claimed. Pass "
            "`--outcome pass|fail` after you try a recommendation — outcomes are only ever "
            "counted when you record them, never inferred."
        ]
    calibration_lessons = [_pass_rate_lesson(recorded=recorded, total=len(entries))]
    calibration_lessons += _failure_lessons(recorded=recorded)
    return calibration_lessons


def _recorded_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry.get("outcome") in OUTCOMES]


def _pass_rate_lesson(recorded: list[dict[str, Any]], total: int) -> str:
    passed = sum(1 for entry in recorded if entry["outcome"] == PASS_OUTCOME)
    return (
        f"Calibration: {passed}/{len(recorded)} recorded outcomes passed at the advised "
        f"start config ({len(recorded)}/{total} asks have a recorded outcome; the rest are "
        "not counted either way)."
    )


def _failure_lessons(recorded: list[dict[str, Any]]) -> list[str]:
    failures_by_quadrant = Counter(
        str(entry.get("quadrant", UNKNOWN_QUADRANT))
        for entry in recorded
        if entry["outcome"] == FAIL_OUTCOME
    )
    if len(failures_by_quadrant) == 0:
        return []
    worst = ", ".join(
        f"{quadrant} ({count})" for quadrant, count in failures_by_quadrant.most_common()
    )
    return [
        f"Recorded failures at the advised start, by shape: {worst}. "
        "If one shape dominates, the plan for that shape starts too low."
    ]
