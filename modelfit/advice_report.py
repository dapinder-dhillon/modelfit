from __future__ import annotations

from pathlib import Path

from modelfit import vendors
from modelfit.advisor import (
    BLIND_SPOTS,
    HIGH_CONFIDENCE,
    Estimate,
    confidence_note,
    distinguish_hint,
    plan_for,
    teach_line,
)
from modelfit.vendors import Vendor


def render(task_estimate: Estimate, chart_rel: str | None = None, vendor: str | None = None) -> str:
    shown_vendors = vendors.chosen(vendor=vendor)
    lines: list[str] = []
    lines += _title_lines()
    lines += _task_lines(task_estimate=task_estimate)
    lines += _recommendation_lines(task_estimate=task_estimate, shown_vendors=shown_vendors)
    lines += _why_lines(task_estimate=task_estimate)
    lines += _second_option_lines(task_estimate=task_estimate, shown_vendors=shown_vendors)
    lines += _blind_spot_lines(task_estimate=task_estimate)
    lines += _chart_lines(chart_rel=chart_rel)
    lines += _footer_lines()
    return "\n".join(lines)


def write(
    task_estimate: Estimate, path: str, chart_rel: str | None = None, vendor: str | None = None
) -> str:
    report_file = Path(path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(render(task_estimate=task_estimate, chart_rel=chart_rel, vendor=vendor))
    return str(report_file)


def _title_lines() -> list[str]:
    return [
        "# modelfit advice\n",
        "_Read from the wording only. No model was asked. Same text → same verdict._\n",
    ]


def _task_lines(task_estimate: Estimate) -> list[str]:
    lines = ["## The task\n"]
    for line in _task_text_lines(text=task_estimate.text):
        lines.append(f"> {line}")
    lines.append("")
    return lines


def _task_text_lines(text: str) -> list[str]:
    text_lines = text.splitlines()
    if len(text_lines) == 0:
        return [""]
    return text_lines


def _recommendation_lines(task_estimate: Estimate, shown_vendors: list[Vendor]) -> list[str]:
    lines = ["## Recommendation\n"]
    lines += _start_lines(task_estimate=task_estimate, shown_vendors=shown_vendors)
    lines.append(_escalation_line(task_estimate=task_estimate, shown_vendors=shown_vendors))
    lines.append(
        f"**Signal:** {task_estimate.confidence} — how clearly the wording matched, "
        "not how likely this is to succeed.\n"
    )
    return lines


def _start_lines(task_estimate: Estimate, shown_vendors: list[Vendor]) -> list[str]:
    if len(shown_vendors) == 1:
        model = shown_vendors[0].models[task_estimate.start_tier]
        return [f"**Start at `{model}` with effort `{task_estimate.start_effort}`.**\n"]
    lines = [
        f"**Start on the {task_estimate.start_tier} tier with effort "
        f"`{task_estimate.start_effort}`:**\n"
    ]
    for shown_vendor in shown_vendors:
        lines.append(f"- {shown_vendor.label}: `{shown_vendor.models[task_estimate.start_tier]}`")
    lines.append(
        "\n_Tiers line up only roughly across vendors — a starting guess, not a "
        "measured equivalence._\n"
    )
    return lines


def _escalation_line(task_estimate: Estimate, shown_vendors: list[Vendor]) -> str:
    escalate_to = task_estimate.escalate_to
    if escalate_to is not None and len(escalate_to) > 0:
        return f"If it fails: **{vendors.fill(text=escalate_to, shown_vendors=shown_vendors)}**.\n"
    return (
        "There is nothing to escalate to by default — if this fails, the wording "
        "misled the advisor, so re-read the failure before spending more.\n"
    )


def _why_lines(task_estimate: Estimate) -> list[str]:
    lines = [
        "## Why\n",
        f"Shape: **{task_estimate.quadrant}** — {task_estimate.shape}.\n",
        f"{task_estimate.why_short}\n",
        "<details><summary>Full signal breakdown</summary>\n",
    ]
    for reason in task_estimate.reasons:
        lines.append(f"- {reason}")
    lines.append(
        f"\nScores: effort {task_estimate.effort_score} (baseline 1 + signals), "
        f"model {task_estimate.model_score}.\n"
    )
    lines.append(f"{confidence_note(confidence=task_estimate.confidence)}\n")
    lines.append(f"{teach_line(task_estimate=task_estimate)}\n")
    lines.append("</details>\n")
    return lines


def _second_option_lines(task_estimate: Estimate, shown_vendors: list[Vendor]) -> list[str]:
    runner_up = task_estimate.runner_up
    if task_estimate.confidence == HIGH_CONFIDENCE or runner_up is None or len(runner_up) == 0:
        return []
    alternative_tier, alternative_effort, alternative_escalation = plan_for(quadrant=runner_up)
    alternative_names = vendors.names(tier=alternative_tier, shown_vendors=shown_vendors)
    return [
        "## Not fully sure — second option\n",
        f"This could also be shaped like **{runner_up}** "
        f"(start {alternative_names} at effort `{alternative_effort}`"
        + _alternative_escalation_clause(
            alternative_escalation=alternative_escalation, shown_vendors=shown_vendors
        )
        + ").\n",
        f"**How to tell:** {distinguish_hint(runner_up=runner_up)}\n",
    ]


def _alternative_escalation_clause(
    alternative_escalation: str | None, shown_vendors: list[Vendor]
) -> str:
    if alternative_escalation is not None and len(alternative_escalation) > 0:
        filled = vendors.fill(text=alternative_escalation, shown_vendors=shown_vendors)
        return f"; if it fails: {filled}"
    return ""


def _blind_spot_lines(task_estimate: Estimate) -> list[str]:
    if task_estimate.hidden_knowledge_warning is False:
        return []
    return [
        "## Blind spot — wording can hide difficulty\n",
        "Nothing in this prompt signals difficulty, and that is exactly the case this "
        "tool is weakest on. Plain wording hides hard knowledge: "
        f"{', '.join(BLIND_SPOTS)}. A one-line ask can be a MODEL task in disguise.\n",
        "If the subject matter is any of those, use the second option above instead "
        "of the recommendation at the top.\n",
    ]


def _chart_lines(chart_rel: str | None) -> list[str]:
    if chart_rel is not None and len(chart_rel) > 0:
        return [f"![Projected pass rate vs cost]({chart_rel})\n"]
    return []


def _footer_lines() -> list[str]:
    return [
        "---\n",
        "_Heuristic read of the wording, not a measurement: it sees words, not meaning. "
        "It states its confidence and hedges when it is unsure, and it never calls a model "
        "to decide. Treat it as a second opinion to argue with, not an oracle — "
        "`modelfit run` is where the evidence comes from._\n",
    ]
