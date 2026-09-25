from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from modelfit.advisor import estimate
from modelfit.tasks import QUADRANTS

LOCAL_CASES_PATH = "eval/advisor_cases.yaml"
CASES_DIRECTORY_NAME = "eval"
CASES_FILE_NAME = "advisor_cases.yaml"

_REQUIRED_FIELDS = {"task", "truth"}
_KNOWN_FIELDS = _REQUIRED_FIELDS | {"adversarial", "note"}
_BUNDLED_CASES_PATH = (
    Path(__file__).resolve().parent.parent / CASES_DIRECTORY_NAME / CASES_FILE_NAME
)


@dataclass(frozen=True)
class EvalCase:
    task: str
    truth: str
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


GradedCase = tuple[EvalCase, str]


def default_cases_path() -> Path:
    local_cases_path = Path(LOCAL_CASES_PATH)
    if local_cases_path.is_file() is True:
        return local_cases_path
    return _BUNDLED_CASES_PATH


def load_cases(path: str | Path | None = None) -> list[EvalCase]:
    cases_file = _cases_file(path=path)
    if cases_file.is_file() is False:
        return []
    data = yaml.safe_load(cases_file.read_text())
    if data is None:
        return []
    _validate_case_list(data=data, source=cases_file)
    return [
        _case_from_dict(data=item, source=cases_file, index=index)
        for index, item in enumerate(data)
    ]


def evaluate(cases: list[EvalCase] | None = None, path: str | Path | None = None) -> EvalResult:
    graded_cases = _graded_cases(eval_cases=_cases_or_loaded(cases=cases, path=path))
    clear_cases = _clear_cases(graded_cases=graded_cases)
    adversarial_cases = _adversarial_cases(graded_cases=graded_cases)
    total = len(graded_cases)
    correct = _correct_count(graded_cases=graded_cases)
    clear_correct = _correct_count(graded_cases=clear_cases)
    adversarial_correct = _correct_count(graded_cases=adversarial_cases)
    return EvalResult(
        total=total,
        correct=correct,
        overall_accuracy=_ratio(correct=correct, total=total),
        clear_total=len(clear_cases),
        clear_correct=clear_correct,
        clear_accuracy=_ratio(correct=clear_correct, total=len(clear_cases)),
        adversarial_total=len(adversarial_cases),
        adversarial_correct=adversarial_correct,
        adversarial_accuracy=_ratio(correct=adversarial_correct, total=len(adversarial_cases)),
        misses=_misses(graded_cases=graded_cases),
    )


def _cases_file(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    return default_cases_path()


def _validate_case_list(data: Any, source: Path) -> None:
    if isinstance(data, list) is False:
        raise ValueError(f"{source}: expected a YAML list of cases at the top level")


def _case_from_dict(data: Any, source: Path, index: int) -> EvalCase:
    where = f"{source}[{index}]"
    _validate_case(data=data, where=where)
    return EvalCase(
        task=str(data["task"]),
        truth=str(data["truth"]),
        adversarial=bool(data.get("adversarial", False)),
        note=str(data.get("note", "")),
    )


def _validate_case(data: Any, where: str) -> None:
    _validate_is_mapping(data=data, where=where)
    _validate_no_missing_fields(data=data, where=where)
    _validate_no_unknown_fields(data=data, where=where)
    _validate_truth(data=data, where=where)


def _validate_is_mapping(data: Any, where: str) -> None:
    if isinstance(data, dict) is False:
        raise ValueError(f"{where}: expected a YAML mapping")


def _validate_no_missing_fields(data: dict[str, Any], where: str) -> None:
    missing = _REQUIRED_FIELDS - data.keys()
    if len(missing) > 0:
        raise ValueError(f"{where}: missing required field(s) {sorted(missing)}")


def _validate_no_unknown_fields(data: dict[str, Any], where: str) -> None:
    unknown = data.keys() - _KNOWN_FIELDS
    if len(unknown) > 0:
        raise ValueError(f"{where}: unknown field(s) {sorted(unknown)}")


def _validate_truth(data: dict[str, Any], where: str) -> None:
    if data["truth"] not in QUADRANTS:
        raise ValueError(f"{where}: truth must be one of {QUADRANTS}, got {data['truth']!r}")


def _cases_or_loaded(cases: list[EvalCase] | None, path: str | Path | None) -> list[EvalCase]:
    if cases is not None:
        return cases
    return load_cases(path=path)


def _graded_cases(eval_cases: list[EvalCase]) -> list[GradedCase]:
    graded_cases: list[GradedCase] = []
    for eval_case in eval_cases:
        graded_cases.append((eval_case, estimate(text=eval_case.task).quadrant))
    return graded_cases


def _clear_cases(graded_cases: list[GradedCase]) -> list[GradedCase]:
    return [graded for graded in graded_cases if _is_adversarial(eval_case=graded[0]) is False]


def _adversarial_cases(graded_cases: list[GradedCase]) -> list[GradedCase]:
    return [graded for graded in graded_cases if _is_adversarial(eval_case=graded[0]) is True]


def _is_adversarial(eval_case: EvalCase) -> bool:
    if bool(eval_case.adversarial) is True:
        return True
    return False


def _is_hit(graded_case: GradedCase) -> bool:
    eval_case, predicted = graded_case
    if predicted == eval_case.truth:
        return True
    return False


def _correct_count(graded_cases: list[GradedCase]) -> int:
    return sum(1 for graded in graded_cases if _is_hit(graded_case=graded) is True)


def _misses(graded_cases: list[GradedCase]) -> list[Miss]:
    misses: list[Miss] = []
    for graded in graded_cases:
        if _is_hit(graded_case=graded) is False:
            misses.append(_miss(graded_case=graded))
    return misses


def _miss(graded_case: GradedCase) -> Miss:
    eval_case, predicted = graded_case
    return Miss(
        task=eval_case.task,
        truth=eval_case.truth,
        predicted=predicted,
        adversarial=eval_case.adversarial,
        note=eval_case.note,
    )


def _ratio(correct: int, total: int) -> float:
    if total != 0:
        return correct / total
    return 0.0
