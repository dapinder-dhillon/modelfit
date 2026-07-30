"""
CLI:
  python -m modelfit.cli run [--mock|--real|--via-cli {claude,codex}] [--models...] [--efforts...]
  python -m modelfit.cli advise "<task text>" [--out ...] [--chart ...]
  python -m modelfit.cli lessons
  python -m modelfit.cli eval

`run` measures: it sweeps model x effort over your tasks and reports
cost-per-solved. --mock is free and deterministic; --real calls the Anthropic
SDK directly (needs ANTHROPIC_API_KEY); --via-cli shells out to an
already-authenticated agent CLI instead, so auth lives wherever that CLI
already logged in and no key is stored here -- it spends real quota, so it asks
for confirmation first unless --yes is given. `advise` guesses, cheaply and
deterministically, from the wording of a single task — no model is called to
decide, and it prints the signals it used plus how sure it is. `eval` grades
the guesser against labelled cases so the guessing is accountable.
"""

from __future__ import annotations

import argparse
import re
import sys

from . import advice_report, advisor, history, project, score
from .evalset import evaluate
from .providers import AGENTS, EFFORT_BUDGETS, MODELS
from .report import write_csv, write_markdown, write_pareto_png
from .runner import run
from .tasks import load_tasks


def _cps_str(cost_per_solved: float | None) -> str:
    if cost_per_solved is None or cost_per_solved == float("inf"):
        return "n/a"
    return f"${cost_per_solved:.4f}/solved"


def _cps_sort_key(stat: score.ConfigStat) -> float:
    return stat.cost_per_solved if stat.cost_per_solved is not None else float("inf")


def _print_summary(picks: list[score.QuadrantPick], front: list[score.ConfigStat]) -> None:
    print("\n=== Recommendation by task type ===")
    for p in picks:
        print(
            f"  {p.quadrant:8s} -> {p.model.replace('claude-',''):14s} "
            f"effort={p.effort:4s}  pass={p.pass_rate*100:3.0f}%  {_cps_str(p.cost_per_solved)}"
        )
    print("\n=== Cost-efficiency frontier (rational choices only) ===")
    for s in sorted(front, key=_cps_sort_key):
        print(
            f"  {s.model.replace('claude-',''):14s} effort={s.effort:4s}  "
            f"pass={s.pass_rate*100:3.0f}%  {_cps_str(s.cost_per_solved)}"
        )
    print()


def _slug(text: str, words: int = 6) -> str:
    """A stable, filesystem-safe stem for a task's report/chart pair."""
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    stem = "_".join(cleaned.split("_")[:words])[:60]
    return stem or "task"


def _cmd_run(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    mode = "cli" if args.via_cli else ("real" if args.real else "mock")

    if mode != "cli":
        # MODELS is Anthropic's own tier table; CLI mode may target a different
        # provider entirely (e.g. codex + GPT ids), so it isn't a valid gate there.
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

    trials = args.trials if args.trials is not None else (1 if mode in ("real", "cli") else 8)

    if mode == "cli":
        n_calls = len(all_tasks) * len(args.models) * len(args.efforts) * trials
        print(
            f"Running {len(all_tasks)} tasks x {len(args.models)} models x "
            f"{len(args.efforts)} efforts x {trials} trials via the {args.via_cli} CLI..."
        )
        if not args.yes:
            prompt = f"About to make {n_calls} real CLI calls via {args.via_cli}. Continue? [y/N] "
            answer = input(prompt).strip().lower()
            if answer not in ("y", "yes"):
                print("Aborted.")
                return 1
    else:
        print(
            f"Running {len(all_tasks)} tasks x {len(args.models)} models x "
            f"{len(args.efforts)} efforts x {trials} trials in {mode.upper()} mode..."
        )

    results = run(
        all_tasks,
        args.models,
        args.efforts,
        mode=mode,
        agent=args.via_cli,
        trials=trials,
        cache_path=None if args.no_cache else "cache/results.json",
    )
    stats = score.by_config(results)
    front = score.pareto(stats)
    picks = score.per_quadrant(results)

    report_mode = f"cli ({args.via_cli})" if mode == "cli" else mode
    write_csv(results, f"{args.out}/results.csv")
    has_png = write_pareto_png(stats, front, f"{args.out}/pareto.png")
    write_markdown(stats, front, picks, f"{args.out}/report.md", has_png, report_mode)

    _print_summary(picks, front)
    print(
        f"Wrote {args.out}/report.md, results.csv"
        + (", pareto.png" if has_png else " (install matplotlib for the chart)")
    )
    return 0


def _cmd_advise(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    text = args.text.strip()
    if not text:
        ap.error('give me a task to read, e.g. modelfit advise "refactor the auth module"')

    est = advisor.estimate(text)
    stem = _slug(text)
    out_path = args.out or f"reports/advice_{stem}.md"
    chart_path = args.chart or f"reports/advice_{stem}.png"

    print(f"\n=== {est.quadrant} — {est.shape} ===")
    print(f"  lever      : {est.lever}")
    print(f"  confidence : {est.confidence} ({advisor.confidence_note(est.confidence)})")
    print(f"  scores     : effort {est.effort_score}, model {est.model_score}")

    print("\n--- why (signals that fired) ---")
    for reason in est.reasons:
        print(f"  - {reason}")

    print("\n--- start here ---")
    print(f"  {est.start_model.replace('claude-','')} at effort {est.start_effort}")
    if est.escalate_to:
        print(f"  if it fails, escalate to: {est.escalate_to}")

    if est.confidence != "high" and est.runner_up:
        alt_model, alt_effort, _ = advisor.plan_for(est.runner_up)
        print("\n--- not fully sure: second option ---")
        print(
            f"  could also be {est.runner_up} "
            f"({alt_model.replace('claude-','')} at effort {alt_effort})"
        )
        print(f"  how to tell : {advisor.distinguish_hint(est.runner_up)}")

    if est.hidden_knowledge_warning:
        print("\n--- blind spot ---")
        print(
            "  Nothing in the wording signals difficulty, which is exactly where this tool\n"
            "  is weakest. Plain phrasing hides hard knowledge: "
            + ", ".join(advisor.BLIND_SPOTS)
            + ".\n  If that's the subject matter, override this and start higher."
        )

    print(f"\n{advisor.teach_line(est)}")

    has_png = project.chart(est, chart_path)
    chart_rel = chart_path.rsplit("/", 1)[-1] if has_png else None
    written = advice_report.write(est, out_path, chart_rel)
    log = history.record(est, outcome=args.outcome, used_effort=args.used_effort)

    print(
        f"\nWrote {written}"
        + (f", {chart_path}" if has_png else " (install matplotlib for the chart)")
        + f"; logged to {log}"
    )
    if args.outcome:
        print(f"Recorded outcome: {args.outcome}. `modelfit lessons` counts it.")
    return 0


def _cmd_lessons(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    print("\n=== Lessons from your own advice history ===")
    for lesson in history.lessons():
        print(f"  - {lesson}")
    print()
    return 0


def _cmd_eval(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    result = evaluate()
    if result.total == 0:
        ap.error("no labelled cases found (expected eval/advisor_cases.yaml)")

    print("\n=== Advisor self-eval (deterministic, exact quadrant match) ===")
    print(f"  overall     : {result.overall_accuracy:.2f}  ({result.correct}/{result.total})")
    print(
        f"  clear       : {result.clear_accuracy:.2f}  "
        f"({result.clear_correct}/{result.clear_total})  — does the mechanism work?"
    )
    print(
        f"  adversarial : {result.adversarial_accuracy:.2f}  "
        f"({result.adversarial_correct}/{result.adversarial_total})  — how far wording is "
        "from meaning"
    )

    if result.misses:
        print("\n--- misses (kept on purpose; this is the error bar) ---")
        for m in result.misses:
            tag = "adversarial" if m.adversarial else "CLEAR"
            print(f"  [{tag}] said {m.predicted}, truth {m.truth}: {m.task.splitlines()[0]}")
            if m.note:
                print(f"      {m.note.strip()}")

    print(
        "\nThe adversarial number is meant to be poor. A word-reader cannot see difficulty "
        "that the words don't carry —\nthat gap is the caveat, so it is printed, not blended "
        "away.\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modelfit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the model x effort sweep and write a report")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", help="deterministic offline demo (default)")
    g.add_argument("--real", action="store_true", help="call the Anthropic API")
    g.add_argument(
        "--via-cli",
        choices=list(AGENTS),
        default=None,
        help="run via an already-authenticated agent CLI (spends real quota; no API key stored "
        "here). For codex, pass --models with GPT ids, not the Anthropic MODELS table.",
    )
    r.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    r.add_argument("--efforts", nargs="+", default=list(EFFORT_BUDGETS.keys()))
    r.add_argument(
        "--trials",
        type=int,
        default=None,
        help="repeats per cell (reliability estimate). default: 8 mock, 1 real/cli",
    )
    r.add_argument("--out", default="reports")
    r.add_argument("--tasks", default="tasks", help="directory of *.yaml task files")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--yes", action="store_true", help="skip the spend confirmation for --via-cli")

    a = sub.add_parser("advise", help="read one task's wording and say which dial to turn")
    a.add_argument("text", help="the task, in the words you'd actually use")
    a.add_argument("--out", default=None, help="markdown path (default: reports/advice_*.md)")
    a.add_argument("--chart", default=None, help="chart path (default: reports/advice_*.png)")
    a.add_argument(
        "--outcome",
        choices=list(history.OUTCOMES),
        default=None,
        help="record what actually happened at the advised start (feeds `lessons`)",
    )
    a.add_argument(
        "--used-effort",
        choices=list(EFFORT_BUDGETS.keys()),
        default=None,
        help="the effort you actually used, recorded alongside the outcome",
    )

    sub.add_parser("lessons", help="what your own advice history says about your work")
    sub.add_parser("eval", help="grade the advisor against labelled cases")

    args = ap.parse_args(argv)
    handlers = {
        "run": _cmd_run,
        "advise": _cmd_advise,
        "lessons": _cmd_lessons,
        "eval": _cmd_eval,
    }
    handler = handlers.get(args.cmd)
    if handler is None:
        ap.print_help()
        return 1
    return handler(args, ap)


if __name__ == "__main__":
    sys.exit(main())
