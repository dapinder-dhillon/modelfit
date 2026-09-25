from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from modelfit import providers, verifiers
from modelfit.tasks import Task

MOCK_MODE = "mock"
REAL_MODE = "real"
CLI_MODE = "cli"
DEFAULT_CACHE_PATH = "cache/results.json"
CACHE_JSON_INDENT = 2
COST_DECIMALS = 6
LATENCY_DECIMALS = 3


@dataclass
class Result:
    task_id: str
    quadrant: str
    model: str
    effort: str
    trial: int
    passed: bool
    detail: str
    in_tokens: int
    out_tokens: int
    cost_usd: float | None
    latency_s: float


def run(
    tasks: list[Task],
    models: list[str],
    efforts: list[str],
    mode: str = MOCK_MODE,
    agent: str | None = None,
    trials: int = 1,
    cache_path: str | None = DEFAULT_CACHE_PATH,
) -> list[Result]:
    _validate_agent_for_mode(mode=mode, agent=agent)
    cache_file = _cache_file(cache_path=cache_path)
    cache = _load_cache(cache_file=cache_file)
    results: list[Result] = []
    for task in tasks:
        for model in models:
            for effort in efforts:
                for trial in range(trials):
                    result = _cached_or_computed_result(
                        task=task,
                        model=model,
                        effort=effort,
                        trial=trial,
                        mode=mode,
                        agent=agent,
                        cache=cache,
                    )
                    results.append(result)
    _save_cache(cache_file=cache_file, cache=cache)
    return results


def _validate_agent_for_mode(mode: str, agent: str | None) -> None:
    if mode == CLI_MODE and agent is None:
        raise ValueError("mode='cli' requires an agent name (e.g. 'claude' or 'codex')")


def _cache_file(cache_path: str | None) -> Path | None:
    if cache_path is not None and len(cache_path) > 0:
        return Path(cache_path)
    return None


def _load_cache(cache_file: Path | None) -> dict[str, dict]:
    if cache_file is None or cache_file.exists() is False:
        return dict()
    try:
        return json.loads(cache_file.read_text())
    except json.JSONDecodeError:
        print(f"warning: cache at {cache_file} is corrupted, starting fresh", file=sys.stderr)
        return dict()


def _save_cache(cache_file: Path | None, cache: dict[str, dict]) -> None:
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=CACHE_JSON_INDENT))


def _cache_key(
    task_id: str,
    model: str,
    effort: str,
    trial: int,
    mode: str = MOCK_MODE,
    agent: str | None = None,
) -> str:
    if mode == CLI_MODE:
        return f"{task_id}|{model}|{effort}|{trial}|cli|{agent}"
    return f"{task_id}|{model}|{effort}|{trial}"


def _cached_or_computed_result(
    task: Task,
    model: str,
    effort: str,
    trial: int,
    mode: str,
    agent: str | None,
    cache: dict[str, dict],
) -> Result:
    cache_key = _cache_key(
        task_id=task.id, model=model, effort=effort, trial=trial, mode=mode, agent=agent
    )
    if cache_key in cache:
        return Result(**cache[cache_key])
    result = _computed_result(
        task=task, model=model, effort=effort, trial=trial, mode=mode, agent=agent
    )
    cache[cache_key] = asdict(result)
    return result


def _computed_result(
    task: Task, model: str, effort: str, trial: int, mode: str, agent: str | None
) -> Result:
    if mode == REAL_MODE:
        return _real_result(task=task, model=model, effort=effort, trial=trial)
    if mode == CLI_MODE:
        return _cli_result(task=task, model=model, effort=effort, trial=trial, agent=agent)
    return _mock_result(task=task, model=model, effort=effort, trial=trial)


def _real_result(task: Task, model: str, effort: str, trial: int) -> Result:
    call = providers.call_real(
        model=model, effort=effort, prompt=task.prompt, max_tokens=task.max_tokens
    )
    passed, detail = verifiers.verify(name=task.verifier, output=call.text, fixture=task.fixture)
    cost = providers.cost_usd(model=model, in_tokens=call.in_tokens, out_tokens=call.out_tokens)
    return _result(
        task=task,
        model=model,
        effort=effort,
        trial=trial,
        passed=passed,
        detail=detail,
        call=call,
        cost=cost,
    )


def _cli_result(task: Task, model: str, effort: str, trial: int, agent: str | None) -> Result:
    assert agent is not None
    call, used_effort = providers.call_cli(
        agent=agent, model=model, effort=effort, prompt=task.prompt, max_tokens=task.max_tokens
    )
    passed, detail = _cli_verdict(task=task, call=call)
    return _result(
        task=task,
        model=model,
        effort=used_effort,
        trial=trial,
        passed=passed,
        detail=detail,
        call=call,
        cost=call.cost_usd,
    )


def _cli_verdict(task: Task, call: providers.Call) -> tuple[bool, str]:
    if call.error is not None:
        return False, call.error
    return verifiers.verify(name=task.verifier, output=call.text, fixture=task.fixture)


def _mock_result(task: Task, model: str, effort: str, trial: int) -> Result:
    call, passed = providers.call_mock(
        model=model,
        effort=effort,
        prompt=task.prompt,
        max_tokens=task.max_tokens,
        quadrant=task.quadrant,
        task_id=task.id,
        trial=trial,
    )
    cost = providers.cost_usd(model=model, in_tokens=call.in_tokens, out_tokens=call.out_tokens)
    return _result(
        task=task,
        model=model,
        effort=effort,
        trial=trial,
        passed=passed,
        detail=_mock_detail(passed=passed),
        call=call,
        cost=cost,
    )


def _mock_detail(passed: bool) -> str:
    if passed is True:
        return "mock pass"
    return "mock fail"


def _result(
    task: Task,
    model: str,
    effort: str,
    trial: int,
    passed: bool,
    detail: str,
    call: providers.Call,
    cost: float | None,
) -> Result:
    return Result(
        task_id=task.id,
        quadrant=task.quadrant,
        model=model,
        effort=effort,
        trial=trial,
        passed=passed,
        detail=detail,
        in_tokens=call.in_tokens,
        out_tokens=call.out_tokens,
        cost_usd=_rounded_cost(cost=cost),
        latency_s=round(call.latency_s, LATENCY_DECIMALS),
    )


def _rounded_cost(cost: float | None) -> float | None:
    if cost is None:
        return None
    return round(cost, COST_DECIMALS)
