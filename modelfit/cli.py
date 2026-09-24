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
import textwrap

from . import advice_report, advisor, color, history, project, score
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


def _print_summary(
    picks: list[score.QuadrantPick], front: list[score.ConfigStat], mode: str = "mock"
) -> None:
    if mode == "mock":
        # Printed once at the top of `run` too, but that line scrolls away long
        # before anyone reads these tables -- repeat it right where the numbers
        # people actually screenshot and share are.
        print(
            color.label(
                "\n(mock mode: illustrative synthetic results, not measured model "
                "performance — see --real / --via-cli)"
            )
        )
    print(color.heading("\n=== Recommendation by task type ==="))
    for p in picks:
        quad = color.quadrant(f"{p.quadrant:8s}")
        print(
            f"  {quad} -> {p.model.replace('claude-',''):14s} "
            f"effort={p.effort:4s}  pass={p.pass_rate*100:3.0f}%  {_cps_str(p.cost_per_solved)}"
        )
    print(color.heading("\n=== Cost-efficiency frontier (rational choices only) ==="))
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

    _print_summary(picks, front, mode)
    print(
        f"Wrote {args.out}/report.md, results.csv"
        + (", pareto.png" if has_png else " (install matplotlib for the chart)")
    )
    return 0


def _field(label_text: str, value: str, width: int = 12, total_width: int = 96) -> None:
    """One `LABEL   value` line, label dimmed, value wrapped under the label
    column if it runs long. The label recedes; the value is what to read."""
    wrapped = textwrap.fill(value, width=total_width - width, subsequent_indent=" " * width)
    print(f"{color.label(f'{label_text:<{width}}')}{wrapped}")


def _print_short(est: advisor.Estimate) -> None:
    """One line. For the person running this 50x/day who already knows the tool.
    Still can't say "escalate" for BOTH -- there's no bigger config above
    opus/high, so the honest next step is a human, not another escalation."""
    start = f"{est.start_model.replace('claude-', '')}/{est.start_effort}"
    if est.quadrant == "BOTH":
        tail = " → human review if it fails"
    elif est.escalate_to:
        tail = " → escalate if needed"
    else:
        tail = ""
    # confidence == "low" only ever happens on the blind-spot path (§ _confidence) --
    # a bare "[low]" reads like an ordinary hedge, not "the wording told us nothing".
    conf = "low — blind spot" if est.confidence == "low" else est.confidence
    print(f"{start}{tail}  [{conf}]")


def _print_compact(est: advisor.Estimate) -> None:
    """The default: lead with the action, not the classifier's internals.
    Still honors the tool's honesty invariants -- WHY always shows (or BLIND
    SPOT in its place), and a hedge always shows when confidence isn't high."""
    start = f"{est.start_model.replace('claude-', '')} / {advisor.effort_phrase(est.start_effort)}"
    print()
    _field("START", color.action(start))
    if est.escalate_to:
        _field("IF NEEDED", est.escalate_to)
    # Called SIGNAL, not CONFIDENCE: this measures how clearly the wording
    # matched a pattern, not how likely the recommendation is to succeed. Those
    # are different claims, and only one of them is something regex matching can
    # actually back up -- outcomes, not word matches, are what would calibrate
    # the other one (see `lessons`).
    tag = advisor.confidence_tag(est.confidence)
    _field("SIGNAL", f"{color.confidence(est.confidence)} ({tag})")
    print()

    if est.hidden_knowledge_warning:
        # runner_up is always "MODEL" here (see _confidence's NEITHER branch) --
        # naming the concrete alternative beats telling the user to "override"
        # a result with no flag or mechanism to actually do that.
        alt_model, alt_effort, _ = advisor.plan_for(est.runner_up or "MODEL")
        alt = f"{alt_model.replace('claude-', '')} at {advisor.effort_phrase(alt_effort)}"
        blind = (
            "Nothing in the wording signals difficulty. That is this tool's blind spot: "
            + ", ".join(advisor.BLIND_SPOTS)
            + f" can all look simple from the wording alone. If this task is actually one "
            f"of those, start with {alt} yourself instead of the suggestion above."
        )
        _field("BLIND SPOT", blind, width=16)
        return

    _field("WHY", est.why_short)

    if est.confidence != "high" and est.runner_up:
        print()
        hint = advisor.distinguish_hint(est.runner_up)
        second = f"could be {color.quadrant(est.runner_up)} instead. {hint}"
        _field("SECOND OPINION", second, width=16)


def _print_explain(est: advisor.Estimate) -> None:
    """Every signal, the raw scores (baseline included, so the arithmetic is
    checkable), and the full prose -- the debug view, not the daily one."""
    print(
        f"\n{color.heading('===')} {color.quadrant(est.quadrant)} "
        f"{color.heading(f'— {est.shape} ===')}"
    )
    print(f"  lever      : {est.lever}")
    conf_note = advisor.confidence_note(est.confidence)
    print(f"  signal     : {color.confidence(est.confidence)} ({conf_note})")
    print(
        f"  scores     : effort {est.effort_score} (baseline 1 + signals), "
        f"model {est.model_score}"
    )

    print(color.heading("\n--- why (signals that fired) ---"))
    for reason in est.reasons:
        print(f"  - {reason}")

    print(color.heading("\n--- start here ---"))
    start_phrase = advisor.effort_phrase(est.start_effort)
    print(f"  {est.start_model.replace('claude-', '')} at {start_phrase}")
    if est.escalate_to:
        print(f"  if it fails: {est.escalate_to}")

    if est.confidence != "high" and est.runner_up:
        alt_model, alt_effort, _ = advisor.plan_for(est.runner_up)
        print(color.heading("\n--- not fully sure: second option ---"))
        print(
            f"  could also be {color.quadrant(est.runner_up)} "
            f"({alt_model.replace('claude-', '')} at {advisor.effort_phrase(alt_effort)})"
        )
        print(f"  how to tell : {advisor.distinguish_hint(est.runner_up)}")

    if est.hidden_knowledge_warning:
        alt_model, alt_effort, _ = advisor.plan_for(est.runner_up or "MODEL")
        alt = f"{alt_model.replace('claude-', '')} at {advisor.effort_phrase(alt_effort)}"
        print(color.heading("\n--- blind spot ---"))
        print(
            "  Nothing in the wording signals difficulty, which is exactly where this tool\n"
            "  is weakest. Plain phrasing hides hard knowledge: "
            + ", ".join(advisor.BLIND_SPOTS)
            + f".\n  If that's the subject matter, start with {alt} yourself instead."
        )

    print(f"\n{advisor.teach_line(est)}")


def _cmd_advise(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    text = args.text.strip()
    if not text:
        ap.error('give me a task to read, e.g. modelfit advise "refactor the auth module"')

    est = advisor.estimate(text)
    stem = _slug(text)
    out_path = args.out or f"reports/advice_{stem}.md"
    chart_path = args.chart or f"reports/advice_{stem}.png"

    if args.short:
        _print_short(est)
    elif args.explain:
        _print_explain(est)
    else:
        _print_compact(est)

    # Bookkeeping, not the answer -- stderr, so `modelfit advise "..." > out`
    # captures only the recommendation, never file paths or log confirmations.
    has_png = project.chart(est, chart_path)
    chart_rel = chart_path.rsplit("/", 1)[-1] if has_png else None
    written = advice_report.write(est, out_path, chart_rel)
    log = history.record(est, outcome=args.outcome, used_effort=args.used_effort)

    print(
        f"Wrote {written}"
        + (f", {chart_path}" if has_png else " (install matplotlib for the chart)")
        + f"; logged to {log}",
        file=sys.stderr,
    )
    if args.outcome:
        print(f"Recorded outcome: {args.outcome}. `modelfit lessons` counts it.", file=sys.stderr)
    return 0


def _cmd_lessons(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    print(color.heading("\n=== Lessons from your own advice history ==="))
    for lesson in history.lessons():
        print(f"  - {lesson}")
    print()
    return 0


def _cmd_eval(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    result = evaluate()
    if result.total == 0:
        ap.error("no labelled cases found (expected eval/advisor_cases.yaml)")

    print(color.heading("\n=== Advisor self-eval (deterministic, exact quadrant match) ==="))
    print(f"  overall     : {result.overall_accuracy:.2f}  ({result.correct}/{result.total})")
    print(
        f"  clear       : {color.c(f'{result.clear_accuracy:.2f}', 'bold', 'green')}  "
        f"({result.clear_correct}/{result.clear_total})  — does the mechanism work?"
    )
    print(
        f"  adversarial : {color.c(f'{result.adversarial_accuracy:.2f}', 'bold', 'red')}  "
        f"({result.adversarial_correct}/{result.adversarial_total})  — how far wording is "
        "from meaning"
    )

    if result.misses:
        print(color.heading("\n--- misses (kept on purpose; this is the error bar) ---"))
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
    verbosity = a.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--short",
        "--compact",
        dest="short",
        action="store_true",
        help="one line: model/effort, escalation, confidence -- for repeat use",
    )
    verbosity.add_argument(
        "--explain",
        action="store_true",
        help="full signal-by-signal breakdown and raw scores -- for debugging the classifier",
    )
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
