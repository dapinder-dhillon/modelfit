"""
Runner: sweep the model x effort grid over every task.

Results are cached additively to disk keyed on (task, model, effort) so reruns
are cheap and nothing is destroyed — add a model, rerun, only the new cells cost
anything.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from . import providers, verifiers
from .tasks import Task


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
    cost_usd: float | None  # None in CLI mode when the agent didn't report usage
    latency_s: float


def _key(
    task_id: str, model: str, effort: str, trial: int, mode: str = "mock", agent: str | None = None
) -> str:
    if mode == "cli":
        return f"{task_id}|{model}|{effort}|{trial}|cli|{agent}"
    return f"{task_id}|{model}|{effort}|{trial}"


def run(
    tasks: list[Task],
    models: list[str],
    efforts: list[str],
    mode: str = "mock",
    agent: str | None = None,
    trials: int = 1,
    cache_path: str | None = "cache/results.json",
) -> list[Result]:
    if mode == "cli" and agent is None:
        raise ValueError("mode='cli' requires an agent name (e.g. 'claude' or 'codex')")

    cache: dict[str, dict] = {}
    cpath = Path(cache_path) if cache_path else None
    if cpath and cpath.exists():
        try:
            cache = json.loads(cpath.read_text())
        except json.JSONDecodeError:
            print(f"warning: cache at {cpath} is corrupted, starting fresh", file=sys.stderr)

    results: list[Result] = []
    for task in tasks:
        for model in models:
            for effort in efforts:
                for trial in range(trials):
                    k = _key(task.id, model, effort, trial, mode, agent)
                    if k in cache:
                        results.append(Result(**cache[k]))
                        continue

                    used_effort = effort
                    if mode == "real":
                        call = providers.call_real(model, effort, task.prompt, task.max_tokens)
                        passed, detail = verifiers.verify(task.verifier, call.text, task.fixture)
                        cost: float | None = providers.cost_usd(
                            model, call.in_tokens, call.out_tokens
                        )
                    elif mode == "cli":
                        assert agent is not None
                        call, used_effort = providers.call_cli(
                            agent, model, effort, task.prompt, task.max_tokens
                        )
                        if call.error is not None:
                            passed, detail = False, call.error
                        else:
                            passed, detail = verifiers.verify(
                                task.verifier, call.text, task.fixture
                            )
                        cost = call.cost_usd
                    else:
                        call, passed = providers.call_mock(
                            model,
                            effort,
                            task.prompt,
                            task.max_tokens,
                            task.quadrant,
                            task.id,
                            trial,
                        )
                        detail = "mock pass" if passed else "mock fail"
                        cost = providers.cost_usd(model, call.in_tokens, call.out_tokens)

                    res = Result(
                        task_id=task.id,
                        quadrant=task.quadrant,
                        model=model,
                        effort=used_effort,
                        trial=trial,
                        passed=passed,
                        detail=detail,
                        in_tokens=call.in_tokens,
                        out_tokens=call.out_tokens,
                        cost_usd=round(cost, 6) if cost is not None else None,
                        latency_s=round(call.latency_s, 3),
                    )
                    results.append(res)
                    cache[k] = asdict(res)

    if cpath:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps(cache, indent=2))
    return results
