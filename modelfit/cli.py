from __future__ import annotations

import argparse
import math
import re
import sys
import textwrap
from pathlib import Path

from modelfit import advice_report, advisor, color, history, project, score, vendors
from modelfit.evalset import EvalResult, Miss, evaluate
from modelfit.providers import AGENTS, EFFORT_BUDGETS, MODELS
from modelfit.report import HIDDEN_MODEL_PREFIX, write_csv, write_markdown, write_pareto_png
from modelfit.runner import CLI_MODE, DEFAULT_CACHE_PATH, MOCK_MODE, REAL_MODE, Result, run
from modelfit.tasks import Task, load_tasks
from modelfit.vendors import MODEL_NAME_SEPARATOR, Vendor

PERCENT_SCALE = 100
MOCK_DEFAULT_TRIALS = 8
MEASURED_DEFAULT_TRIALS = 1
CONFIRMING_ANSWERS = ("y", "yes")
REPORTS_DIRECTORY = "reports"
SLUG_WORDS = 6
SLUG_MAX_LENGTH = 60
DEFAULT_SLUG = "task"
LABEL_WIDTH = 12
WIDE_LABEL_WIDTH = 16
TOTAL_WIDTH = 96
VENDOR_LABEL_WIDTH = 11
LOW_SIGNAL_SHORT_LABEL = "low — blind spot"
CLEAR_ACCURACY_STYLES = ("bold", "green")
ADVERSARIAL_ACCURACY_STYLES = ("bold", "red")

_NON_SLUG_CHARACTERS = re.compile(r"[^a-z0-9]+")


def main(argv: list[str] | None = None) -> int:
    argument_parser = _argument_parser()
    args = argument_parser.parse_args(argv)
    return _dispatch(args=args, argument_parser=argument_parser)


def _argument_parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(prog="modelfit")
    subcommands = argument_parser.add_subparsers(dest="cmd", required=True)
    _configure_run_parser(
        run_parser=subcommands.add_parser(
            "run", help="run the model x effort sweep and write a report"
        )
    )
    _configure_advise_parser(
        advise_parser=subcommands.add_parser(
            "advise", help="read one task's wording and say which dial to turn"
        )
    )
    subcommands.add_parser("lessons", help="what your own advice history says about your work")
    subcommands.add_parser("eval", help="grade the advisor against labelled cases")
    return argument_parser


def _configure_run_parser(run_parser: argparse.ArgumentParser) -> None:
    mode_group = run_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mock", action="store_true", help="deterministic offline demo (default)"
    )
    mode_group.add_argument("--real", action="store_true", help="call the Anthropic API")
    mode_group.add_argument(
        "--via-cli",
        choices=list(AGENTS),
        default=None,
        help="run via an already-authenticated agent CLI (spends real quota; no API key stored "
        "here). For codex, pass --models with GPT ids, not the Anthropic MODELS table.",
    )
    run_parser.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    run_parser.add_argument("--efforts", nargs="+", default=list(EFFORT_BUDGETS.keys()))
    run_parser.add_argument(
        "--trials",
        type=int,
        default=None,
        help="repeats per cell (reliability estimate). default: 8 mock, 1 real/cli",
    )
    run_parser.add_argument("--out", default=REPORTS_DIRECTORY)
    run_parser.add_argument("--tasks", default="tasks", help="directory of *.yaml task files")
    run_parser.add_argument("--no-cache", action="store_true")
    run_parser.add_argument(
        "--yes", action="store_true", help="skip the spend confirmation for --via-cli"
    )


def _configure_advise_parser(advise_parser: argparse.ArgumentParser) -> None:
    advise_parser.add_argument("text", help="the task, in the words you'd actually use")
    verbosity_group = advise_parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "--short",
        "--compact",
        dest="short",
        action="store_true",
        help="one line: model/effort, escalation, confidence -- for repeat use",
    )
    verbosity_group.add_argument(
        "--explain",
        action="store_true",
        help="full signal-by-signal breakdown and raw scores -- for debugging the classifier",
    )
    advise_parser.add_argument(
        "--vendor",
        choices=list(vendors.VENDORS),
        default=None,
        help="show only this vendor's model ids (default: every vendor)",
    )
    advise_parser.add_argument(
        "--out", default=None, help="markdown path (default: reports/advice_*.md)"
    )
    advise_parser.add_argument(
        "--chart", default=None, help="chart path (default: reports/advice_*.png)"
    )
    advise_parser.add_argument(
        "--outcome",
        choices=list(history.OUTCOMES),
        default=None,
        help="record what actually happened at the advised start (feeds `lessons`)",
    )
    advise_parser.add_argument(
        "--used-effort",
        choices=list(EFFORT_BUDGETS.keys()),
        default=None,
        help="the effort you actually used, recorded alongside the outcome",
    )


def _dispatch(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> int:
    if args.cmd == "run":
        return _cmd_run(args=args, argument_parser=argument_parser)
    if args.cmd == "advise":
        return _cmd_advise(args=args, argument_parser=argument_parser)
    if args.cmd == "lessons":
        return _cmd_lessons(args=args, argument_parser=argument_parser)
    if args.cmd == "eval":
        return _cmd_eval(args=args, argument_parser=argument_parser)
    argument_parser.print_help()
    return 1


def _cmd_run(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> int:
    mode = _run_mode(args=args)
    _validate_anthropic_models_outside_cli_mode(
        args=args, argument_parser=argument_parser, mode=mode
    )
    _validate_efforts(args=args, argument_parser=argument_parser)
    all_tasks = _load_tasks_or_exit(args=args, argument_parser=argument_parser)
    trials = _trials(args=args, mode=mode)
    if _announce_run_and_confirm(args=args, mode=mode, all_tasks=all_tasks, trials=trials) is False:
        return 1
    results = run(
        tasks=all_tasks,
        models=args.models,
        efforts=args.efforts,
        mode=mode,
        agent=args.via_cli,
        trials=trials,
        cache_path=_cache_path(args=args),
    )
    stats = score.by_config(results=results)
    front = score.pareto(stats=stats)
    picks = score.per_quadrant(results=results)
    has_png = _write_run_reports(
        args=args, mode=mode, results=results, stats=stats, front=front, picks=picks
    )
    _print_summary(picks=picks, front=front, mode=mode)
    print(f"Wrote {args.out}/report.md, results.csv" + _run_chart_note(has_png=has_png))
    return 0


def _run_mode(args: argparse.Namespace) -> str:
    if args.via_cli is not None and len(args.via_cli) > 0:
        return CLI_MODE
    if args.real is True:
        return REAL_MODE
    return MOCK_MODE


def _validate_anthropic_models_outside_cli_mode(
    args: argparse.Namespace, argument_parser: argparse.ArgumentParser, mode: str
) -> None:
    if mode == CLI_MODE:
        return
    bad_models = [model for model in args.models if model not in MODELS]
    if len(bad_models) > 0:
        argument_parser.error(f"unknown model(s) {bad_models}; choose from {list(MODELS)}")


def _validate_efforts(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> None:
    bad_efforts = [effort for effort in args.efforts if effort not in EFFORT_BUDGETS]
    if len(bad_efforts) > 0:
        argument_parser.error(
            f"unknown effort(s) {bad_efforts}; choose from {list(EFFORT_BUDGETS)}"
        )


def _load_tasks_or_exit(
    args: argparse.Namespace, argument_parser: argparse.ArgumentParser
) -> list[Task]:
    all_tasks = load_tasks(directory=args.tasks)
    if len(all_tasks) == 0:
        argument_parser.error(
            f"no *.yaml task files found in {args.tasks!r}. "
            "Add one (see the bundled examples in tasks/) or pass --tasks <dir>."
        )
    return all_tasks


def _trials(args: argparse.Namespace, mode: str) -> int:
    if args.trials is not None:
        return args.trials
    if mode == REAL_MODE or mode == CLI_MODE:
        return MEASURED_DEFAULT_TRIALS
    return MOCK_DEFAULT_TRIALS


def _announce_run_and_confirm(
    args: argparse.Namespace, mode: str, all_tasks: list[Task], trials: int
) -> bool:
    if mode != CLI_MODE:
        print(
            f"Running {len(all_tasks)} tasks x {len(args.models)} models x "
            f"{len(args.efforts)} efforts x {trials} trials in {mode.upper()} mode..."
        )
        return True
    print(
        f"Running {len(all_tasks)} tasks x {len(args.models)} models x "
        f"{len(args.efforts)} efforts x {trials} trials via the {args.via_cli} CLI..."
    )
    if args.yes is True:
        return True
    return _confirm_cli_spend(args=args, all_tasks=all_tasks, trials=trials)


def _confirm_cli_spend(args: argparse.Namespace, all_tasks: list[Task], trials: int) -> bool:
    call_count = len(all_tasks) * len(args.models) * len(args.efforts) * trials
    prompt = f"About to make {call_count} real CLI calls via {args.via_cli}. Continue? [y/N] "
    answer = input(prompt).strip().lower()
    if answer not in CONFIRMING_ANSWERS:
        print("Aborted.")
        return False
    return True


def _cache_path(args: argparse.Namespace) -> str | None:
    if args.no_cache is True:
        return None
    return DEFAULT_CACHE_PATH


def _write_run_reports(
    args: argparse.Namespace,
    mode: str,
    results: list[Result],
    stats: list[score.ConfigStat],
    front: list[score.ConfigStat],
    picks: list[score.QuadrantPick],
) -> bool:
    write_csv(results=results, path=f"{args.out}/results.csv")
    has_png = write_pareto_png(stats=stats, front=front, path=f"{args.out}/pareto.png")
    write_markdown(
        stats=stats,
        front=front,
        picks=picks,
        path=f"{args.out}/report.md",
        has_png=has_png,
        mode=_report_mode(args=args, mode=mode),
    )
    return has_png


def _report_mode(args: argparse.Namespace, mode: str) -> str:
    if mode == CLI_MODE:
        return f"cli ({args.via_cli})"
    return mode


def _run_chart_note(has_png: bool) -> str:
    if has_png is True:
        return ", pareto.png"
    return " (install matplotlib for the chart)"


def _print_summary(
    picks: list[score.QuadrantPick], front: list[score.ConfigStat], mode: str = MOCK_MODE
) -> None:
    if mode == MOCK_MODE:
        _print_mock_notice()
    _print_recommendations(picks=picks)
    _print_frontier(front=front)
    print()


def _print_mock_notice() -> None:
    print(
        color.label(
            text="\n(mock mode: illustrative synthetic results, not measured model "
            "performance — see --real / --via-cli)"
        )
    )


def _print_recommendations(picks: list[score.QuadrantPick]) -> None:
    print(color.heading(text="\n=== Recommendation by task type ==="))
    for pick in picks:
        quadrant = color.quadrant(name=f"{pick.quadrant:8s}")
        print(
            f"  {quadrant} -> {_short_model_name(model=pick.model):14s} "
            f"effort={pick.effort:4s}  pass={pick.pass_rate * PERCENT_SCALE:3.0f}%  "
            f"{_cost_per_solved_text(cost_per_solved=pick.cost_per_solved)}"
        )


def _print_frontier(front: list[score.ConfigStat]) -> None:
    print(color.heading(text="\n=== Cost-efficiency frontier (rational choices only) ==="))
    for stat in sorted(front, key=_sortable_cost_per_solved):
        print(
            f"  {_short_model_name(model=stat.model):14s} effort={stat.effort:4s}  "
            f"pass={stat.pass_rate * PERCENT_SCALE:3.0f}%  "
            f"{_cost_per_solved_text(cost_per_solved=stat.cost_per_solved)}"
        )


def _short_model_name(model: str) -> str:
    return model.replace(HIDDEN_MODEL_PREFIX, "")


def _cost_per_solved_text(cost_per_solved: float | None) -> str:
    if cost_per_solved is None or cost_per_solved == math.inf:
        return "n/a"
    return f"${cost_per_solved:.4f}/solved"


def _sortable_cost_per_solved(stat: score.ConfigStat) -> float:
    if stat.cost_per_solved is not None:
        return stat.cost_per_solved
    return math.inf


def _cmd_advise(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> int:
    text = args.text.strip()
    if len(text) == 0:
        argument_parser.error(
            'give me a task to read, e.g. modelfit advise "refactor the auth module"'
        )
    task_estimate = advisor.estimate(text=text)
    stem = _slug(text=text)
    out_path = _path_or_default(path=args.out, default=f"{REPORTS_DIRECTORY}/advice_{stem}.md")
    chart_path = _path_or_default(path=args.chart, default=f"{REPORTS_DIRECTORY}/advice_{stem}.png")
    _print_advice(task_estimate=task_estimate, args=args)
    has_png = project.chart(task_estimate=task_estimate, path=chart_path, vendor=args.vendor)
    written = advice_report.write(
        task_estimate=task_estimate,
        path=out_path,
        chart_rel=_chart_file_name(chart_path=chart_path, has_png=has_png),
        vendor=args.vendor,
    )
    log = history.record(
        task_estimate=task_estimate, outcome=args.outcome, used_effort=args.used_effort
    )
    _print_bookkeeping_to_stderr(
        written=written, chart_path=chart_path, has_png=has_png, log=log, outcome=args.outcome
    )
    return 0


def _slug(text: str, words: int = SLUG_WORDS) -> str:
    cleaned = _NON_SLUG_CHARACTERS.sub("_", text.lower()).strip("_")
    stem = "_".join(cleaned.split("_")[:words])[:SLUG_MAX_LENGTH]
    if len(stem) > 0:
        return stem
    return DEFAULT_SLUG


def _path_or_default(path: str | None, default: str) -> str:
    if path is not None and len(path) > 0:
        return path
    return default


def _chart_file_name(chart_path: str, has_png: bool) -> str | None:
    if has_png is True:
        return chart_path.rsplit("/", 1)[-1]
    return None


def _print_advice(task_estimate: advisor.Estimate, args: argparse.Namespace) -> None:
    if args.short is True:
        _print_short(task_estimate=task_estimate, vendor=args.vendor)
        return
    if args.explain is True:
        _print_explain(task_estimate=task_estimate, vendor=args.vendor)
        return
    _print_compact(task_estimate=task_estimate, vendor=args.vendor)


def _print_bookkeeping_to_stderr(
    written: str, chart_path: str, has_png: bool, log: Path, outcome: str | None
) -> None:
    print(
        f"Wrote {written}"
        + _advice_chart_note(chart_path=chart_path, has_png=has_png)
        + f"; logged to {log}",
        file=sys.stderr,
    )
    if outcome is not None and len(outcome) > 0:
        print(f"Recorded outcome: {outcome}. `modelfit lessons` counts it.", file=sys.stderr)


def _advice_chart_note(chart_path: str, has_png: bool) -> str:
    if has_png is True:
        return f", {chart_path}"
    return " (install matplotlib for the chart)"


def _field(
    label_text: str, value: str, width: int = LABEL_WIDTH, total_width: int = TOTAL_WIDTH
) -> None:
    wrapped = textwrap.fill(value, width=total_width - width, subsequent_indent=" " * width)
    print(f"{color.label(text=f'{label_text:<{width}}')}{wrapped}")


def _print_short(task_estimate: advisor.Estimate, vendor: str | None = None) -> None:
    shown_vendors = vendors.chosen(vendor=vendor)
    start = (
        MODEL_NAME_SEPARATOR.join(
            shown_vendor.models[task_estimate.start_tier] for shown_vendor in shown_vendors
        )
        + f" @ {task_estimate.start_effort}"
    )
    tail = _short_next_step(task_estimate=task_estimate)
    signal = _short_signal_label(confidence=task_estimate.confidence)
    print(f"{start}{tail}  [{signal}]")


def _short_next_step(task_estimate: advisor.Estimate) -> str:
    if task_estimate.quadrant == advisor.BOTH_QUADRANT:
        return " → human review if it fails"
    if _has_escalation(task_estimate=task_estimate) is True:
        return " → escalate if needed"
    return ""


def _short_signal_label(confidence: str) -> str:
    if confidence == advisor.LOW_CONFIDENCE:
        return LOW_SIGNAL_SHORT_LABEL
    return confidence


def _has_escalation(task_estimate: advisor.Estimate) -> bool:
    escalate_to = task_estimate.escalate_to
    if escalate_to is not None and len(escalate_to) > 0:
        return True
    return False


def _is_hedged(task_estimate: advisor.Estimate) -> bool:
    runner_up = task_estimate.runner_up
    if task_estimate.confidence == advisor.HIGH_CONFIDENCE:
        return False
    if runner_up is None or len(runner_up) == 0:
        return False
    return True


def _runner_up_or_model(runner_up: str | None) -> str:
    if runner_up is not None and len(runner_up) > 0:
        return runner_up
    return advisor.MODEL_QUADRANT


def _blind_spot_alternative(task_estimate: advisor.Estimate, shown_vendors: list[Vendor]) -> str:
    alternative_tier, alternative_effort, _ = advisor.plan_for(
        quadrant=_runner_up_or_model(runner_up=task_estimate.runner_up)
    )
    alternative_names = vendors.names(tier=alternative_tier, shown_vendors=shown_vendors)
    return f"{alternative_names} at {advisor.effort_phrase(effort=alternative_effort)}"


def _print_compact(task_estimate: advisor.Estimate, vendor: str | None = None) -> None:
    shown_vendors = vendors.chosen(vendor=vendor)
    print()
    _print_start_fields(task_estimate=task_estimate, shown_vendors=shown_vendors)
    if _has_escalation(task_estimate=task_estimate) is True:
        _field(
            label_text="IF NEEDED",
            value=vendors.fill(text=str(task_estimate.escalate_to), shown_vendors=shown_vendors),
        )
    _print_signal_field(task_estimate=task_estimate)
    print()
    if task_estimate.hidden_knowledge_warning is True:
        _print_blind_spot_field(task_estimate=task_estimate, shown_vendors=shown_vendors)
        print()
        return
    _field(label_text="WHY", value=task_estimate.why_short)
    if _is_hedged(task_estimate=task_estimate) is True:
        _print_second_opinion_field(task_estimate=task_estimate)
    print()


def _print_start_fields(task_estimate: advisor.Estimate, shown_vendors: list[Vendor]) -> None:
    effort = advisor.effort_phrase(effort=task_estimate.start_effort)
    if len(shown_vendors) == 1:
        model = shown_vendors[0].models[task_estimate.start_tier]
        _field(label_text="START", value=color.action(text=f"{model} / {effort}"))
        return
    for vendor_index, shown_vendor in enumerate(shown_vendors):
        start_config = color.action(
            text=f"{shown_vendor.models[task_estimate.start_tier]} / {effort}"
        )
        vendor_label = color.label(text=f"{shown_vendor.label:<{VENDOR_LABEL_WIDTH}}")
        _field(
            label_text=_start_label(vendor_index=vendor_index),
            value=f"{vendor_label}{start_config}",
        )


def _start_label(vendor_index: int) -> str:
    if vendor_index == 0:
        return "START"
    return ""


def _print_signal_field(task_estimate: advisor.Estimate) -> None:
    tag = advisor.confidence_tag(confidence=task_estimate.confidence)
    _field(label_text="SIGNAL", value=f"{color.confidence(level=task_estimate.confidence)} ({tag})")


def _print_blind_spot_field(task_estimate: advisor.Estimate, shown_vendors: list[Vendor]) -> None:
    alternative = _blind_spot_alternative(task_estimate=task_estimate, shown_vendors=shown_vendors)
    blind_spot = (
        "Nothing in the wording signals difficulty. That is this tool's blind spot: "
        + ", ".join(advisor.BLIND_SPOTS)
        + " can all look simple from the wording alone. If this task is actually one "
        f"of those, start with {alternative} yourself instead of the suggestion above."
    )
    _field(label_text="BLIND SPOT", value=blind_spot, width=WIDE_LABEL_WIDTH)


def _print_second_opinion_field(task_estimate: advisor.Estimate) -> None:
    runner_up = str(task_estimate.runner_up)
    print()
    hint = advisor.distinguish_hint(runner_up=runner_up)
    second_opinion = f"could be {color.quadrant(name=runner_up)} instead. {hint}"
    _field(label_text="SECOND OPINION", value=second_opinion, width=WIDE_LABEL_WIDTH)


def _print_explain(task_estimate: advisor.Estimate, vendor: str | None = None) -> None:
    shown_vendors = vendors.chosen(vendor=vendor)
    _print_explain_header(task_estimate=task_estimate)
    _print_explain_signals(task_estimate=task_estimate)
    _print_explain_start(task_estimate=task_estimate, shown_vendors=shown_vendors)
    if _is_hedged(task_estimate=task_estimate) is True:
        _print_explain_second_option(task_estimate=task_estimate, shown_vendors=shown_vendors)
    if task_estimate.hidden_knowledge_warning is True:
        _print_explain_blind_spot(task_estimate=task_estimate, shown_vendors=shown_vendors)
    print(f"\n{advisor.teach_line(task_estimate=task_estimate)}")


def _print_explain_header(task_estimate: advisor.Estimate) -> None:
    print(
        f"\n{color.heading(text='===')} {color.quadrant(name=task_estimate.quadrant)} "
        f"{color.heading(text=f'— {task_estimate.shape} ===')}"
    )
    print(f"  lever      : {task_estimate.lever}")
    confidence_note = advisor.confidence_note(confidence=task_estimate.confidence)
    print(f"  signal     : {color.confidence(level=task_estimate.confidence)} ({confidence_note})")
    print(
        f"  scores     : effort {task_estimate.effort_score} (baseline 1 + signals), "
        f"model {task_estimate.model_score}"
    )


def _print_explain_signals(task_estimate: advisor.Estimate) -> None:
    print(color.heading(text="\n--- why (signals that fired) ---"))
    for reason in task_estimate.reasons:
        print(f"  - {reason}")


def _print_explain_start(task_estimate: advisor.Estimate, shown_vendors: list[Vendor]) -> None:
    print(color.heading(text="\n--- start here ---"))
    start_effort = advisor.effort_phrase(effort=task_estimate.start_effort)
    print(f"  {task_estimate.start_tier} tier at {start_effort}")
    for shown_vendor in shown_vendors:
        model = shown_vendor.models[task_estimate.start_tier]
        print(f"    {shown_vendor.label:<{VENDOR_LABEL_WIDTH}}{model}")
    if _has_escalation(task_estimate=task_estimate) is True:
        escalation = vendors.fill(text=str(task_estimate.escalate_to), shown_vendors=shown_vendors)
        print(f"  if it fails: {escalation}")
    if len(shown_vendors) > 1:
        print(
            "  (tiers line up only roughly across vendors -- `modelfit run` measures\n"
            "   which one is actually cheaper per solved task on your work)"
        )


def _print_explain_second_option(
    task_estimate: advisor.Estimate, shown_vendors: list[Vendor]
) -> None:
    runner_up = str(task_estimate.runner_up)
    alternative_tier, alternative_effort, _ = advisor.plan_for(quadrant=runner_up)
    alternative_names = vendors.names(tier=alternative_tier, shown_vendors=shown_vendors)
    alternative_phrase = advisor.effort_phrase(effort=alternative_effort)
    print(color.heading(text="\n--- not fully sure: second option ---"))
    print(
        f"  could also be {color.quadrant(name=runner_up)} "
        f"({alternative_names} at {alternative_phrase})"
    )
    print(f"  how to tell : {advisor.distinguish_hint(runner_up=runner_up)}")


def _print_explain_blind_spot(task_estimate: advisor.Estimate, shown_vendors: list[Vendor]) -> None:
    alternative = _blind_spot_alternative(task_estimate=task_estimate, shown_vendors=shown_vendors)
    print(color.heading(text="\n--- blind spot ---"))
    print(
        "  Nothing in the wording signals difficulty, which is exactly where this tool\n"
        "  is weakest. Plain phrasing hides hard knowledge: "
        + ", ".join(advisor.BLIND_SPOTS)
        + f".\n  If that's the subject matter, start with {alternative} yourself instead."
    )


def _cmd_lessons(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> int:
    print(color.heading(text="\n=== Lessons from your own advice history ==="))
    for lesson in history.lessons():
        print(f"  - {lesson}")
    print()
    return 0


def _cmd_eval(args: argparse.Namespace, argument_parser: argparse.ArgumentParser) -> int:
    result = evaluate()
    if result.total == 0:
        argument_parser.error("no labelled cases found (expected eval/advisor_cases.yaml)")
    _print_eval_accuracy(result=result)
    if len(result.misses) > 0:
        _print_eval_misses(misses=result.misses)
    print(
        "\nThe adversarial number is meant to be poor. A word-reader cannot see difficulty "
        "that the words don't carry —\nthat gap is the caveat, so it is printed, not blended "
        "away.\n"
    )
    return 0


def _print_eval_accuracy(result: EvalResult) -> None:
    clear_accuracy = color.c(f"{result.clear_accuracy:.2f}", *CLEAR_ACCURACY_STYLES)
    adversarial_accuracy = color.c(
        f"{result.adversarial_accuracy:.2f}", *ADVERSARIAL_ACCURACY_STYLES
    )
    print(color.heading(text="\n=== Advisor self-eval (deterministic, exact quadrant match) ==="))
    print(f"  overall     : {result.overall_accuracy:.2f}  ({result.correct}/{result.total})")
    print(
        f"  clear       : {clear_accuracy}  "
        f"({result.clear_correct}/{result.clear_total})  — does the mechanism work?"
    )
    print(
        f"  adversarial : {adversarial_accuracy}  "
        f"({result.adversarial_correct}/{result.adversarial_total})  — how far wording is "
        "from meaning"
    )


def _print_eval_misses(misses: list[Miss]) -> None:
    print(color.heading(text="\n--- misses (kept on purpose; this is the error bar) ---"))
    for miss in misses:
        print(
            f"  [{_miss_tag(miss=miss)}] said {miss.predicted}, truth {miss.truth}: "
            f"{miss.task.splitlines()[0]}"
        )
        if len(miss.note) > 0:
            print(f"      {miss.note.strip()}")


def _miss_tag(miss: Miss) -> str:
    if bool(miss.adversarial) is True:
        return "adversarial"
    return "CLEAR"


if __name__ == "__main__":
    sys.exit(main())
