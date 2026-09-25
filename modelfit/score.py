from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from modelfit.runner import Result

INF = math.inf
QUADRANT_ORDER = {"NEITHER": 0, "EFFORT": 1, "MODEL": 2, "BOTH": 3}
UNKNOWN_QUADRANT_ORDER = 9
PASS_RATE_DECIMALS = 2

QuadrantCandidate = tuple[float, float, str, str, float | None]


@dataclass
class ConfigStat:
    model: str
    effort: str
    n: int
    solved: int
    pass_rate: float
    total_cost: float | None
    cost_per_solved: float | None


@dataclass
class QuadrantPick:
    quadrant: str
    model: str
    effort: str
    pass_rate: float
    cost_per_solved: float | None


def by_config(results: list[Result]) -> list[ConfigStat]:
    stats: list[ConfigStat] = []
    for (model, effort), config_results in _group_by_config(results=results).items():
        stats.append(_config_stat(model=model, effort=effort, config_results=config_results))
    stats.sort(key=_config_sort_key)
    return stats


def pareto(stats: list[ConfigStat]) -> list[ConfigStat]:
    front: list[ConfigStat] = []
    for stat in stats:
        if _is_on_frontier(stat=stat, stats=stats) is True:
            front.append(stat)
    return front


def per_quadrant(results: list[Result]) -> list[QuadrantPick]:
    picks: list[QuadrantPick] = []
    for quadrant, quadrant_results in _group_by_quadrant(results=results).items():
        picks.append(_quadrant_pick(quadrant=quadrant, quadrant_results=quadrant_results))
    picks.sort(key=_quadrant_sort_key)
    return picks


def _group_by_config(results: list[Result]) -> dict[tuple[str, str], list[Result]]:
    results_by_config: dict[tuple[str, str], list[Result]] = defaultdict(list)
    for result in results:
        results_by_config[(result.model, result.effort)].append(result)
    return results_by_config


def _group_by_quadrant(results: list[Result]) -> dict[str, list[Result]]:
    results_by_quadrant: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        results_by_quadrant[result.quadrant].append(result)
    return results_by_quadrant


def _config_stat(model: str, effort: str, config_results: list[Result]) -> ConfigStat:
    run_count = len(config_results)
    solved = _solved_count(results=config_results)
    total_cost = _total_cost(results=config_results)
    return ConfigStat(
        model=model,
        effort=effort,
        n=run_count,
        solved=solved,
        pass_rate=_pass_rate(solved=solved, run_count=run_count),
        total_cost=total_cost,
        cost_per_solved=_cost_per_solved(total_cost=total_cost, solved=solved),
    )


def _solved_count(results: list[Result]) -> int:
    return sum(1 for result in results if bool(result.passed) is True)


def _total_cost(results: list[Result]) -> float | None:
    costs = [result.cost_usd for result in results]
    if _has_unknown_cost_value(costs=costs) is True:
        return None
    return sum(cost for cost in costs if cost is not None)


def _has_unknown_cost_value(costs: list[float | None]) -> bool:
    for cost in costs:
        if cost is None:
            return True
    return False


def _cost_per_solved(total_cost: float | None, solved: int) -> float | None:
    if total_cost is None:
        return None
    if solved != 0:
        return total_cost / solved
    return INF


def _pass_rate(solved: int, run_count: int) -> float:
    if run_count != 0:
        return solved / run_count
    return 0.0


def _sortable_cost(cost_per_solved: float | None) -> float:
    if cost_per_solved is not None:
        return cost_per_solved
    return INF


def _config_sort_key(stat: ConfigStat) -> tuple[float, float]:
    return -stat.pass_rate, _sortable_cost(cost_per_solved=stat.cost_per_solved)


def _is_on_frontier(stat: ConfigStat, stats: list[ConfigStat]) -> bool:
    if _has_unknown_cost(stat=stat) is True:
        return True
    if _is_dominated(stat=stat, stats=stats) is True:
        return False
    return True


def _has_unknown_cost(stat: ConfigStat) -> bool:
    if stat.cost_per_solved is None:
        return True
    return False


def _is_dominated(stat: ConfigStat, stats: list[ConfigStat]) -> bool:
    for other in stats:
        if other is not stat and _dominates(other=other, stat=stat) is True:
            return True
    return False


def _dominates(other: ConfigStat, stat: ConfigStat) -> bool:
    if other.cost_per_solved is None or stat.cost_per_solved is None:
        return False
    at_least_as_good = (
        other.pass_rate >= stat.pass_rate and other.cost_per_solved <= stat.cost_per_solved
    )
    strictly_better = (
        other.pass_rate > stat.pass_rate or other.cost_per_solved < stat.cost_per_solved
    )
    if at_least_as_good is True and strictly_better is True:
        return True
    return False


def _quadrant_pick(quadrant: str, quadrant_results: list[Result]) -> QuadrantPick:
    best: QuadrantCandidate | None = None
    for (model, effort), config_results in _group_by_config(results=quadrant_results).items():
        candidate = _quadrant_candidate(model=model, effort=effort, config_results=config_results)
        if best is None or _is_better_candidate(candidate=candidate, best=best) is True:
            best = candidate
    assert best is not None
    pass_rate, _, model, effort, cost_per_solved = best
    return QuadrantPick(
        quadrant=quadrant,
        model=model,
        effort=effort,
        pass_rate=round(pass_rate, PASS_RATE_DECIMALS),
        cost_per_solved=cost_per_solved,
    )


def _quadrant_candidate(model: str, effort: str, config_results: list[Result]) -> QuadrantCandidate:
    solved = _solved_count(results=config_results)
    pass_rate = solved / len(config_results)
    cost_per_solved = _cost_per_solved(
        total_cost=_total_cost(results=config_results), solved=solved
    )
    return (
        pass_rate,
        _sortable_cost(cost_per_solved=cost_per_solved),
        model,
        effort,
        cost_per_solved,
    )


def _is_better_candidate(candidate: QuadrantCandidate, best: QuadrantCandidate) -> bool:
    candidate_pass_rate, candidate_sortable_cost, _, _, _ = candidate
    best_pass_rate, best_sortable_cost, _, _, _ = best
    if candidate_pass_rate > best_pass_rate:
        return True
    if candidate_pass_rate == best_pass_rate and candidate_sortable_cost < best_sortable_cost:
        return True
    return False


def _quadrant_sort_key(pick: QuadrantPick) -> int:
    return QUADRANT_ORDER.get(pick.quadrant, UNKNOWN_QUADRANT_ORDER)
