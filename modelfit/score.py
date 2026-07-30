"""
Scoring turns raw runs into the two things that actually answer the question:

  1. cost-per-SOLVED-task per (model, effort) config, and the Pareto frontier
     (you only ever want configs that aren't beaten on both quality AND cost).
  2. the per-quadrant winner: the cheapest config that reliably passes each
     kind of task -- which is where you SEE that effort won one quadrant and
     model won another.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from .providers import MODELS
from .runner import Result

INF = math.inf


@dataclass
class ConfigStat:
    model: str
    effort: str
    n: int
    solved: int
    pass_rate: float
    total_cost: float | None  # None if any run in this config had unknown cost (CLI mode)
    cost_per_solved: float | None  # None if unknown; INF if cost is known but nothing solved


def by_config(results: list[Result]) -> list[ConfigStat]:
    agg: dict[tuple[str, str], list[Result]] = defaultdict(list)
    for r in results:
        agg[(r.model, r.effort)].append(r)

    stats: list[ConfigStat] = []
    for (model, effort), rs in agg.items():
        n = len(rs)
        solved = sum(1 for r in rs if r.passed)
        costs = [r.cost_usd for r in rs]
        total: float | None
        cost_per_solved: float | None
        if any(c is None for c in costs):
            total = None
            cost_per_solved = None
        else:
            total = sum(c for c in costs if c is not None)
            cost_per_solved = (total / solved) if solved else INF
        stats.append(
            ConfigStat(
                model=model,
                effort=effort,
                n=n,
                solved=solved,
                pass_rate=solved / n if n else 0.0,
                total_cost=total,
                cost_per_solved=cost_per_solved,
            )
        )

    def _sort_key(s: ConfigStat) -> tuple[float, float]:
        return -s.pass_rate, s.cost_per_solved if s.cost_per_solved is not None else INF

    stats.sort(key=_sort_key)
    return stats


def pareto(stats: list[ConfigStat]) -> list[ConfigStat]:
    """A config is on the frontier if nothing else has >= pass_rate AND
    <= cost_per_solved (with at least one strictly better). A config with
    unknown cost (CLI mode, usage not reported) can't be shown to be dominated
    or to dominate anything, so it always stays on the frontier -- the report
    renders it `n/a` rather than implying a number we don't have."""
    front = []
    for s in stats:
        if s.cost_per_solved is None:
            front.append(s)
            continue
        dominated = any(
            o.cost_per_solved is not None
            and (o.pass_rate >= s.pass_rate and o.cost_per_solved <= s.cost_per_solved)
            and (o.pass_rate > s.pass_rate or o.cost_per_solved < s.cost_per_solved)
            for o in stats
            if o is not s
        )
        if not dominated:
            front.append(s)
    return front


@dataclass
class QuadrantPick:
    quadrant: str
    model: str
    effort: str
    pass_rate: float
    cost_per_solved: float | None  # None if unknown; INF if known but nothing solved


def per_quadrant(results: list[Result]) -> list[QuadrantPick]:
    """Cheapest config that maximises pass rate, per quadrant. This is the table
    that replaces 'complex -> big model' with an actual recommendation."""
    quads: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        quads[r.quadrant].append(r)

    picks: list[QuadrantPick] = []
    for quad, rs in quads.items():
        cfg: dict[tuple[str, str], list[Result]] = defaultdict(list)
        for r in rs:
            cfg[(r.model, r.effort)].append(r)

        best: tuple[float, float, int, str, str] | None = None
        best_cps: float | None = None
        for (model, effort), crs in cfg.items():
            solved = sum(1 for r in crs if r.passed)
            rate = solved / len(crs)
            costs = [r.cost_usd for r in crs]
            cps: float | None
            if any(c is None for c in costs):
                cps = None
            else:
                cps = (sum(c for c in costs if c is not None) / solved) if solved else INF
            cps_sort = cps if cps is not None else INF
            cand = (rate, cps_sort, MODELS.get(model, 0), effort, model)
            # maximise rate, then minimise cost, then prefer smaller model/effort
            if best is None or (rate > best[0]) or (rate == best[0] and cps_sort < best[1]):
                best = cand
                best_cps = cps
        assert best is not None  # cfg is never empty: quad only exists if >=1 result
        picks.append(QuadrantPick(quad, best[4], best[3], round(best[0], 2), best_cps))
    order = {"NEITHER": 0, "EFFORT": 1, "MODEL": 2, "BOTH": 3}
    picks.sort(key=lambda p: order.get(p.quadrant, 9))
    return picks
