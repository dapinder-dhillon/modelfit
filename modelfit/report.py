"""
Reporting: the tangible artifact you show people.

Writes:
  reports/report.md   -- the readable verdict (per-quadrant table + Pareto)
  reports/results.csv -- every raw run
  reports/pareto.png  -- quality vs cost-per-solved scatter (if matplotlib present)
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from .runner import Result
from .score import ConfigStat, QuadrantPick


def _money(x: float) -> str:
    if x == math.inf:
        return "n/a"
    return f"${x:.5f}" if x < 0.01 else f"${x:.4f}"


def write_csv(results: list[Result], path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
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
        )
        for r in results:
            w.writerow(
                [
                    r.task_id,
                    r.quadrant,
                    r.model,
                    r.effort,
                    r.passed,
                    r.in_tokens,
                    r.out_tokens,
                    r.cost_usd,
                    r.latency_s,
                    r.detail,
                ]
            )


def write_pareto_png(stats: list[ConfigStat], front: list[ConfigStat], path: str) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    plotted = [s for s in stats if s.cost_per_solved != math.inf]
    if not plotted:
        return False
    front_ids = {(s.model, s.effort) for s in front}

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for s in plotted:
        on_front = (s.model, s.effort) in front_ids
        ax.scatter(
            s.cost_per_solved * 100,
            s.pass_rate * 100,
            s=90,
            zorder=3,
            color="#c0392b" if on_front else "#95a5a6",
            edgecolors="black",
            linewidths=0.6,
        )
        ax.annotate(
            f"{s.model.replace('claude-','')}\n{s.effort}",
            (s.cost_per_solved * 100, s.pass_rate * 100),
            fontsize=7,
            ha="center",
            va="bottom",
            xytext=(0, 6),
            textcoords="offset points",
        )

    fx = sorted(front, key=lambda s: s.cost_per_solved)
    ax.plot(
        [s.cost_per_solved * 100 for s in fx],
        [s.pass_rate * 100 for s in fx],
        color="#c0392b",
        lw=1.2,
        ls="--",
        zorder=2,
        label="Pareto frontier",
    )

    ax.set_xlabel("cost per SOLVED task (cents)  \u2192 cheaper is left")
    ax.set_ylabel("pass rate (%)  \u2192 better is up")
    ax.set_title("Which model+effort is actually worth it")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return True


def write_markdown(
    stats: list[ConfigStat],
    front: list[ConfigStat],
    picks: list[QuadrantPick],
    path: str,
    has_png: bool,
    mode: str,
) -> None:
    front_ids = {(s.model, s.effort) for s in front}
    lines: list[str] = []
    lines.append("# modelfit report\n")
    lines.append(f"_Mode: **{mode}**. Cost is per **solved** task, not per token._\n")

    lines.append("## The verdict, by task type\n")
    lines.append("What the failure shape tells you to turn — read straight off the data.\n")
    lines.append("| Task type | Use this model | Effort | Pass rate | $/solved | Why |")
    lines.append("|---|---|---|---|---|---|")
    why = {
        "NEITHER": "recall/boilerplate — cheapest config already wins",
        "EFFORT": "logic to work out — **effort** carried it, not the model",
        "MODEL": "needs knowledge/judgement — **model** carried it, not effort",
        "BOTH": "long multi-step — needs a strong model **and** high effort",
    }
    for p in picks:
        lines.append(
            f"| {p.quadrant} | `{p.model.replace('claude-','')}` | {p.effort} "
            f"| {p.pass_rate*100:.0f}% | {_money(p.cost_per_solved)} | {why.get(p.quadrant,'')} |"
        )
    lines.append("")

    lines.append("## Cost-efficiency frontier\n")
    lines.append(
        "Only configs on the frontier are ever rational — everything else is "
        "beaten on both quality and cost. `*` marks the frontier.\n"
    )
    lines.append("| Model | Effort | Pass rate | Total cost | $/solved | Frontier |")
    lines.append("|---|---|---|---|---|---|")
    for s in stats:
        star = "*" if (s.model, s.effort) in front_ids else ""
        lines.append(
            f"| `{s.model.replace('claude-','')}` | {s.effort} | {s.pass_rate*100:.0f}% "
            f"| {_money(s.total_cost)} | {_money(s.cost_per_solved)} | {star} |"
        )
    lines.append("")

    if has_png:
        lines.append("![Pareto frontier](pareto.png)\n")

    lines.append("## How to read this\n")
    lines.append(
        "- Look **down a quadrant**, not at one global 'best model'. The winner "
        "changes by task type — that's the whole point.\n"
        "- If a cheap model at **high effort** matches a big model, your bottleneck "
        "was deliberation, not knowledge. Don't pay for capability you don't need.\n"
        "- The only place 'just use the best model at high effort' is correct is the "
        "**BOTH** row — long, self-directed, multi-step work.\n"
        "- Now delete the toy tasks and drop in ~20 real ones from your backlog. "
        "The recommendation becomes yours, and defensible.\n"
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines))
