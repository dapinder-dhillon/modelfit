"""
The advisor's self-eval: labelled cases in, accuracy out.

A heuristic that never grades itself is just an opinion with a CLI. So the cases
live as data (`eval/advisor_cases.yaml`, loaded the same way as `tasks/*.yaml`)
and the score is split in two on purpose:

  clear       : wording that genuinely reflects the shape — does the mechanism work?
  adversarial : plainly-worded but hard tasks, and false triggers — how far is
                wording from meaning?

The adversarial number is expected to be poor. It is printed anyway, next to the
clear number, because that gap IS the caveat: a word-reader cannot see hard
knowledge hiding behind calm phrasing. Hiding the gap behind a single blended
accuracy would be the dishonest version of this tool.

Grading is exact quadrant match — deterministic, like every other check here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .advisor import estimate
from .tasks import QUADRANTS

_REQUIRED_FIELDS = {"task", "truth"}
_KNOWN_FIELDS = _REQUIRED_FIELDS | {"adversarial", "note"}

_BUNDLED = Path(__file__).resolve().parent.parent / "eval" / "advisor_cases.yaml"


@dataclass(frozen=True)
class EvalCase:
    task: str
    truth: str  # NEITHER | EFFORT | MODEL | BOTH
    adversarial: bool = False
    note: str = ""


@dataclass(frozen=True)
class Miss:
    task: str
    truth: str
    predicted: str
    adversarial: bool
    note: str


@dataclass(frozen=True)
class EvalResult:
    total: int
    correct: int
    overall_accuracy: float
    clear_total: int
    clear_correct: int
    clear_accuracy: float
    adversarial_total: int
    adversarial_correct: int
    adversarial_accuracy: float
    misses: list[Miss]


def default_cases_path() -> Path:
    """`eval/advisor_cases.yaml` under the working directory if it exists (so you
    can point the eval at your own cases), else the copy shipped in this repo."""
    local = Path("eval/advisor_cases.yaml")
    return local if local.is_file() else _BUNDLED


def _case_from_dict(data: Any, source: Path, index: int) -> EvalCase:
    where = f"{source}[{index}]"
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected a YAML mapping")

    missing = _REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"{where}: missing required field(s) {sorted(missing)}")

    unknown = data.keys() - _KNOWN_FIELDS
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {sorted(unknown)}")

    if data["truth"] not in QUADRANTS:
        raise ValueError(f"{where}: truth must be one of {QUADRANTS}, got {data['truth']!r}")

    return EvalCase(
        task=str(data["task"]),
        truth=str(data["truth"]),
        adversarial=bool(data.get("adversarial", False)),
        note=str(data.get("note", "")),
    )


def load_cases(path: str | Path | None = None) -> list[EvalCase]:
    """Load the labelled cases. Returns an empty list if the file is absent."""
    target = Path(path) if path is not None else default_cases_path()
    if not target.is_file():
        return []

    data = yaml.safe_load(target.read_text())
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{target}: expected a YAML list of cases at the top level")
    return [_case_from_dict(item, target, i) for i, item in enumerate(data)]


def _ratio(correct: int, total: int) -> float:
    return correct / total if total else 0.0


def evaluate(cases: list[EvalCase] | None = None, path: str | Path | None = None) -> EvalResult:
    """Score `estimate()` against the labelled cases. Exact quadrant match only."""
    items = cases if cases is not None else load_cases(path)

    correct = clear_total = clear_correct = adv_total = adv_correct = 0
    misses: list[Miss] = []

    for case in items:
        predicted = estimate(case.task).quadrant
        hit = predicted == case.truth
        correct += hit
        if case.adversarial:
            adv_total += 1
            adv_correct += hit
        else:
            clear_total += 1
            clear_correct += hit
        if not hit:
            misses.append(
                Miss(
                    task=case.task,
                    truth=case.truth,
                    predicted=predicted,
                    adversarial=case.adversarial,
                    note=case.note,
                )
            )

    total = len(items)
    return EvalResult(
        total=total,
        correct=correct,
        overall_accuracy=_ratio(correct, total),
        clear_total=clear_total,
        clear_correct=clear_correct,
        clear_accuracy=_ratio(clear_correct, clear_total),
        adversarial_total=adv_total,
        adversarial_correct=adv_correct,
        adversarial_accuracy=_ratio(adv_correct, adv_total),
        misses=misses,
    )
