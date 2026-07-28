"""
CLI:  python -m modelfit.cli run [--mock|--real] [--models ...] [--efforts ...]

--mock (default) runs with no API key and produces a deterministic sample report.
--real calls the Anthropic API (needs `pip install anthropic` and ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import argparse
import sys

from . import score
from .providers import EFFORT_BUDGETS, MODELS
from .report import write_csv, write_markdown, write_pareto_png
from .runner import run
from .tasks import load_tasks


def _print_summary(picks: list[score.QuadrantPick], front: list[score.ConfigStat]) -> None:
    print("\n=== Recommendation by task type ===")
    for p in picks:
        cps = "n/a" if p.cost_per_solved == float("inf") else f"${p.cost_per_solved:.4f}/solved"
        print(
            f"  {p.quadrant:8s} -> {p.model.replace('claude-',''):14s} "
            f"effort={p.effort:4s}  pass={p.pass_rate*100:3.0f}%  {cps}"
        )
    print("\n=== Cost-efficiency frontier (rational choices only) ===")
    for s in sorted(front, key=lambda s: s.cost_per_solved):
        print(
            f"  {s.model.replace('claude-',''):14s} effort={s.effort:4s}  "
            f"pass={s.pass_rate*100:3.0f}%  ${s.cost_per_solved:.4f}/solved"
        )
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modelfit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the model x effort sweep and write a report")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", help="deterministic offline demo (default)")
    g.add_argument("--real", action="store_true", help="call the Anthropic API")
    r.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    r.add_argument("--efforts", nargs="+", default=list(EFFORT_BUDGETS.keys()))
    r.add_argument(
        "--trials",
        type=int,
        default=None,
        help="repeats per cell (reliability estimate). default: 8 mock, 1 real",
    )
    r.add_argument("--out", default="reports")
    r.add_argument("--tasks", default="tasks", help="directory of *.yaml task files")
    r.add_argument("--no-cache", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd != "run":
        ap.print_help()
        return 1

    bad_models = [m for m in args.models if m not in MODELS]
    if bad_models:
        ap.error(f"unknown model(s) {bad_models}; choose from {list(MODELS)}")
    bad_efforts = [e for e in args.efforts if e not in EFFORT_BUDGETS]
    if bad_efforts:
        ap.error(f"unknown effort(s) {bad_efforts}; choose from {list(EFFORT_BUDGETS)}")

    all_tasks = load_tasks(args.tasks)
    if not all_tasks:
        ap.error(
            f"no *.yaml task files found in {args.tasks!r}. "
            "Add one (see the bundled examples in tasks/) or pass --tasks <dir>."
        )

    mode = "real" if args.real else "mock"
    trials = args.trials if args.trials is not None else (1 if mode == "real" else 8)
    print(
        f"Running {len(all_tasks)} tasks x {len(args.models)} models x "
        f"{len(args.efforts)} efforts x {trials} trials in {mode.upper()} mode..."
    )

    results = run(
        all_tasks,
        args.models,
        args.efforts,
        mode=mode,
        trials=trials,
        cache_path=None if args.no_cache else "cache/results.json",
    )
    stats = score.by_config(results)
    front = score.pareto(stats)
    picks = score.per_quadrant(results)

    write_csv(results, f"{args.out}/results.csv")
    has_png = write_pareto_png(stats, front, f"{args.out}/pareto.png")
    write_markdown(stats, front, picks, f"{args.out}/report.md", has_png, mode)

    _print_summary(picks, front)
    print(
        f"Wrote {args.out}/report.md, results.csv"
        + (", pareto.png" if has_png else " (install matplotlib for the chart)")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
