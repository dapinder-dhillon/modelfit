from __future__ import annotations

import csv
import math
from pathlib import Path

from modelfit.runner import Result
from modelfit.score import ConfigStat, QuadrantPick

NOT_AVAILABLE = "n/a"
SMALL_AMOUNT_THRESHOLD = 0.01
PERCENT_SCALE = 100
CENTS_PER_DOLLAR = 100
HIDDEN_MODEL_PREFIX = "claude-"
MOCK_MODE = "mock"
CLI_MODE_PREFIX = "cli"
UNCONTROLLED_EFFORT = "n/a"
FRONTIER_MARK = "*"
CHART_FIGURE_SIZE = (8, 5.5)
CHART_DPI = 130
FRONTIER_COLOR = "#c0392b"
OFF_FRONTIER_COLOR = "#95a5a6"

CSV_HEADER = [
    "task",
    "quadrant",
    "model",
    "effort",
    "passed",
    "in_tokens",
    "out_tokens",
    "cost_usd",
    "latency_s",
    "detail",
]

WHY_BY_QUADRANT = {
    "NEITHER": "recall/boilerplate — cheapest config already wins",
    "EFFORT": "logic to work out — **effort** carried it, not the model",
    "MODEL": "needs knowledge/judgement — **model** carried it, not effort",
    "BOTH": "long multi-step — needs a strong model **and** high effort",
}


def write_csv(results: list[Result], path: str) -> None:
    csv_file = Path(path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(CSV_HEADER)
        for result in results:
            writer.writerow(_csv_row(result=result))


def write_pareto_png(stats: list[ConfigStat], front: list[ConfigStat], path: str) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    plotted = _plottable_points(stats=stats)
    if len(plotted) == 0:
        return False
    front_ids = _config_ids(stats=front)

    figure, axes = plt.subplots(figsize=CHART_FIGURE_SIZE)
    for stat, cost in plotted:
        on_front = (stat.model, stat.effort) in front_ids
        axes.scatter(
            cost * CENTS_PER_DOLLAR,
            stat.pass_rate * PERCENT_SCALE,
            s=90,
            zorder=3,
            color=_point_color(on_front=on_front),
            edgecolors="black",
            linewidths=0.6,
        )
        axes.annotate(
            f"{_short_model_name(model=stat.model)}\n{stat.effort}",
            (cost * CENTS_PER_DOLLAR, stat.pass_rate * PERCENT_SCALE),
            fontsize=7,
            ha="center",
            va="bottom",
            xytext=(0, 6),
            textcoords="offset points",
        )

    frontier_points = _frontier_points(front=front)
    axes.plot(
        [x for x, _ in frontier_points],
        [y for _, y in frontier_points],
        color=FRONTIER_COLOR,
        lw=1.2,
        ls="--",
        zorder=2,
        label="Pareto frontier",
    )

    axes.set_xlabel("cost per SOLVED task (cents)  → cheaper is left")
    axes.set_ylabel("pass rate (%)  → better is up")
    axes.set_title("Which model+effort is actually worth it")
    axes.grid(True, alpha=0.25)
    axes.legend(loc="lower right", fontsize=8)
    figure.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=CHART_DPI)
    plt.close(figure)
    return True


def write_markdown(
    stats: list[ConfigStat],
    front: list[ConfigStat],
    picks: list[QuadrantPick],
    path: str,
    has_png: bool,
    mode: str,
) -> None:
    lines: list[str] = []
    lines += _header_lines(mode=mode)
    lines += _mock_caveat_lines(mode=mode)
    lines += _cli_caveat_lines(mode=mode, stats=stats)
    lines += _verdict_lines(picks=picks)
    lines += _frontier_lines(stats=stats, front=front)
    lines += _chart_lines(has_png=has_png)
    lines += _how_to_read_lines()
    report_file = Path(path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines))


def _money(amount: float | None) -> str:
    if amount is None or amount == math.inf:
        return NOT_AVAILABLE
    if amount < SMALL_AMOUNT_THRESHOLD:
        return f"${amount:.5f}"
    return f"${amount:.4f}"


def _short_model_name(model: str) -> str:
    return model.replace(HIDDEN_MODEL_PREFIX, "")


def _csv_row(result: Result) -> list[object]:
    return [
        result.task_id,
        result.quadrant,
        result.model,
        result.effort,
        result.passed,
        result.in_tokens,
        result.out_tokens,
        result.cost_usd,
        result.latency_s,
        result.detail,
    ]


def _config_ids(stats: list[ConfigStat]) -> set[tuple[str, str]]:
    return {(stat.model, stat.effort) for stat in stats}


def _plottable_points(stats: list[ConfigStat]) -> list[tuple[ConfigStat, float]]:
    points: list[tuple[ConfigStat, float]] = []
    for stat in stats:
        cost = stat.cost_per_solved
        if cost is not None and cost != math.inf:
            points.append((stat, cost))
    return points


def _point_color(on_front: bool) -> str:
    if on_front is True:
        return FRONTIER_COLOR
    return OFF_FRONTIER_COLOR


def _frontier_points(front: list[ConfigStat]) -> list[tuple[float, float]]:
    frontier_points: list[tuple[float, float]] = []
    for stat, cost in _plottable_points(stats=front):
        frontier_points.append((cost * CENTS_PER_DOLLAR, stat.pass_rate * PERCENT_SCALE))
    frontier_points.sort(key=lambda point: point[0])
    return frontier_points


def _header_lines(mode: str) -> list[str]:
    return [
        "# modelfit report\n",
        f"_Mode: **{mode}**. Cost is per **solved** task, not per token._\n",
    ]


def _mock_caveat_lines(mode: str) -> list[str]:
    if mode != MOCK_MODE:
        return []
    return [
        "> **Mock mode:** every number below is an illustrative synthetic result "
        "from a deterministic formula, not a measured outcome from any real model. "
        "It proves the tool's machinery works; it is not evidence about which model "
        "is actually best. Run `--real` or `--via-cli` for numbers you can act on.\n"
    ]


def _cli_caveat_lines(mode: str, stats: list[ConfigStat]) -> list[str]:
    if mode.startswith(CLI_MODE_PREFIX) is False:
        return []
    lines = [
        "> **CLI mode caveat:** these runs went through an already-authenticated agent CLI, "
        "not the API directly. That CLI can inject its own system prompt, tools, or context "
        'you don\'t control, so "same task in" is directional here, not as tightly '
        "controlled as the SDK path. `$/solved` shows `n/a` wherever the CLI didn't report "
        "token usage.\n"
    ]
    if _has_uncontrolled_effort(stats=stats) is True:
        lines.append(
            "> The **effort axis is not controlled** for at least one row below — this agent "
            "has no equivalent for the requested level, so those rows report effort `n/a` "
            "rather than a number that would imply control that wasn't there.\n"
        )
    return lines


def _has_uncontrolled_effort(stats: list[ConfigStat]) -> bool:
    for stat in stats:
        if stat.effort == UNCONTROLLED_EFFORT:
            return True
    return False


def _verdict_lines(picks: list[QuadrantPick]) -> list[str]:
    lines = [
        "## The verdict, by task type\n",
        "What the failure shape tells you to turn — read straight off the data.\n",
        "| Task type | Use this model | Effort | Pass rate | $/solved | Why |",
        "|---|---|---|---|---|---|",
    ]
    for pick in picks:
        lines.append(
            f"| {pick.quadrant} | `{_short_model_name(model=pick.model)}` | {pick.effort} "
            f"| {pick.pass_rate * PERCENT_SCALE:.0f}% | {_money(amount=pick.cost_per_solved)} "
            f"| {WHY_BY_QUADRANT.get(pick.quadrant, '')} |"
        )
    lines.append("")
    return lines


def _frontier_lines(stats: list[ConfigStat], front: list[ConfigStat]) -> list[str]:
    front_ids = _config_ids(stats=front)
    lines = [
        "## Cost-efficiency frontier\n",
        "Only configs on the frontier are ever rational — everything else is "
        "beaten on both quality and cost. `*` marks the frontier.\n",
        "| Model | Effort | Pass rate | Total cost | $/solved | Frontier |",
        "|---|---|---|---|---|---|",
    ]
    for stat in stats:
        lines.append(
            f"| `{_short_model_name(model=stat.model)}` | {stat.effort} "
            f"| {stat.pass_rate * PERCENT_SCALE:.0f}% "
            f"| {_money(amount=stat.total_cost)} | {_money(amount=stat.cost_per_solved)} "
            f"| {_frontier_mark(stat=stat, front_ids=front_ids)} |"
        )
    lines.append("")
    return lines


def _frontier_mark(stat: ConfigStat, front_ids: set[tuple[str, str]]) -> str:
    if (stat.model, stat.effort) in front_ids:
        return FRONTIER_MARK
    return ""


def _chart_lines(has_png: bool) -> list[str]:
    if has_png is True:
        return ["![Pareto frontier](pareto.png)\n"]
    return []


def _how_to_read_lines() -> list[str]:
    return [
        "## How to read this\n",
        "- Look **down a quadrant**, not at one global 'best model'. The winner "
        "changes by task type — that's the whole point.\n"
        "- If a cheap model at **high effort** matches a big model, your bottleneck "
        "was deliberation, not knowledge. Don't pay for capability you don't need.\n"
        "- The only place 'just use the best model at high effort' is correct is the "
        "**BOTH** row — long, self-directed, multi-step work.\n"
        "- Now delete the toy tasks and drop in ~20 real ones from your backlog. "
        "The recommendation becomes yours, and defensible.\n",
    ]
