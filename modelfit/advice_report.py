"""
The written verdict for one advised task.

Same principle as `report.py`: the artifact has to survive being read by someone
who wasn't there and is sceptical. So it prints the signals that fired (not just
the answer), states its confidence, shows the runner-up whenever it isn't sure,
and ends with a footer that says plainly what this is — a heuristic read of
wording, not evidence.
"""

from __future__ import annotations

from pathlib import Path

from .advisor import BLIND_SPOTS, Estimate, confidence_note, distinguish_hint, plan_for, teach_line


def _short(model: str) -> str:
    return model.replace("claude-", "")


def render(est: Estimate, chart_rel: str | None = None) -> str:
    """Render the advice as markdown."""
    lines: list[str] = []
    lines.append("# modelfit advice\n")
    lines.append("_Read from the wording only. No model was asked. Same text → same verdict._\n")

    lines.append("## The task\n")
    for line in est.text.splitlines() or [""]:
        lines.append(f"> {line}")
    lines.append("")

    lines.append(f"## Shape: **{est.quadrant}** — {est.shape}\n")
    lines.append(
        f"- **Lever to turn:** {est.lever}\n"
        f"- **Confidence:** {est.confidence} — {confidence_note(est.confidence)}\n"
        f"- **Scores:** effort {est.effort_score}, model {est.model_score}\n"
    )

    lines.append("## Why — the signals that fired\n")
    for reason in est.reasons:
        lines.append(f"- {reason}")
    lines.append("")

    lines.append("## Recommendation\n")
    lines.append(f"**Start at `{_short(est.start_model)}` with effort `{est.start_effort}`.**\n")
    if est.escalate_to:
        lines.append(f"If it fails, escalate to: **{est.escalate_to}**.\n")
    else:
        lines.append(
            "There is nothing to escalate to by default — if this fails, the wording "
            "misled the advisor, so re-read the failure before spending more.\n"
        )
    lines.append(f"{teach_line(est)}\n")

    if est.confidence != "high" and est.runner_up:
        alt_model, alt_effort, alt_escalate = plan_for(est.runner_up)
        lines.append("## Not fully sure — second option\n")
        lines.append(
            f"This could also be shaped like **{est.runner_up}** "
            f"(start `{_short(alt_model)}` at effort `{alt_effort}`"
            + (f", escalating to {alt_escalate}" if alt_escalate else "")
            + ").\n"
        )
        lines.append(f"**How to tell:** {distinguish_hint(est.runner_up)}\n")

    if est.hidden_knowledge_warning:
        lines.append("## Blind spot — wording can hide difficulty\n")
        lines.append(
            "Nothing in this prompt signals difficulty, and that is exactly the case this "
            "tool is weakest on. Plain wording hides hard knowledge: "
            f"{', '.join(BLIND_SPOTS)}. A one-line ask can be a MODEL task in disguise.\n"
        )
        lines.append(
            "If the subject matter is any of those, override this verdict and start higher.\n"
        )

    if chart_rel:
        lines.append(f"![Projected pass rate vs cost]({chart_rel})\n")

    lines.append("---\n")
    lines.append(
        "_Heuristic read of the wording, not a measurement: it sees words, not meaning. "
        "It states its confidence and hedges when it is unsure, and it never calls a model "
        "to decide. Treat it as a second opinion to argue with, not an oracle — "
        "`modelfit run` is where the evidence comes from._\n"
    )
    return "\n".join(lines)


def write(est: Estimate, path: str, chart_rel: str | None = None) -> str:
    """Write the advice markdown to `path`. Returns the path written."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(est, chart_rel))
    return str(target)
