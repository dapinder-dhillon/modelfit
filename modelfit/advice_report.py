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

from . import vendors
from .advisor import BLIND_SPOTS, Estimate, confidence_note, distinguish_hint, plan_for, teach_line


def render(est: Estimate, chart_rel: str | None = None, vendor: str | None = None) -> str:
    """Render the advice as markdown. Leads with the action (what to run, and
    what to do if it fails) before the classification that justifies it --
    someone skimming should get the verdict without reading the reasoning."""
    shown = vendors.chosen(vendor)
    lines: list[str] = []
    lines.append("# modelfit advice\n")
    lines.append("_Read from the wording only. No model was asked. Same text → same verdict._\n")

    lines.append("## The task\n")
    for line in est.text.splitlines() or [""]:
        lines.append(f"> {line}")
    lines.append("")

    lines.append("## Recommendation\n")
    if len(shown) == 1:
        model = shown[0].models[est.start_tier]
        lines.append(f"**Start at `{model}` with effort `{est.start_effort}`.**\n")
    else:
        lines.append(f"**Start on the {est.start_tier} tier with effort `{est.start_effort}`:**\n")
        for v in shown:
            lines.append(f"- {v.label}: `{v.models[est.start_tier]}`")
        lines.append(
            "\n_Tiers line up only roughly across vendors — a starting guess, not a "
            "measured equivalence._\n"
        )
    if est.escalate_to:
        lines.append(f"If it fails: **{vendors.fill(est.escalate_to, shown)}**.\n")
    else:
        lines.append(
            "There is nothing to escalate to by default — if this fails, the wording "
            "misled the advisor, so re-read the failure before spending more.\n"
        )
    lines.append(
        f"**Signal:** {est.confidence} — how clearly the wording matched, "
        "not how likely this is to succeed.\n"
    )

    lines.append("## Why\n")
    lines.append(f"Shape: **{est.quadrant}** — {est.shape}.\n")
    lines.append(f"{est.why_short}\n")
    lines.append("<details><summary>Full signal breakdown</summary>\n")
    for reason in est.reasons:
        lines.append(f"- {reason}")
    lines.append(
        f"\nScores: effort {est.effort_score} (baseline 1 + signals), model {est.model_score}.\n"
    )
    lines.append(f"{confidence_note(est.confidence)}\n")
    lines.append(f"{teach_line(est)}\n")
    lines.append("</details>\n")

    if est.confidence != "high" and est.runner_up:
        alt_tier, alt_effort, alt_escalate = plan_for(est.runner_up)
        lines.append("## Not fully sure — second option\n")
        lines.append(
            f"This could also be shaped like **{est.runner_up}** "
            f"(start {vendors.names(alt_tier, shown)} at effort `{alt_effort}`"
            + (f"; if it fails: {vendors.fill(alt_escalate, shown)}" if alt_escalate else "")
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
            "If the subject matter is any of those, use the second option above instead "
            "of the recommendation at the top.\n"
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


def write(est: Estimate, path: str, chart_rel: str | None = None, vendor: str | None = None) -> str:
    """Write the advice markdown to `path`. Returns the path written."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(est, chart_rel, vendor))
    return str(target)
