from __future__ import annotations

from pathlib import Path

from modelfit import vendors
from modelfit.advisor import Estimate
from modelfit.providers import (
    CHARACTERS_PER_TOKEN,
    EFFORT_BUDGETS,
    MOCK_ANSWER_TOKENS,
    MOCK_PROMPT_OVERHEAD_TOKENS,
    _pass_probability,
    cost_usd,
)

PERCENT_SCALE = 100
CENTS_PER_DOLLAR = 100
CHART_FIGURE_SIZE = (8, 5.5)
CHART_DPI = 130
ADVISED_START_COLOR = "#c0392b"
SOLID_LINE = "-"
DASHED_LINE = "--"
HOLLOW_MARKER_FACE = "none"


def projected_cell(
    text: str, model: str, tier: str, effort: str, quadrant: str
) -> tuple[float, float]:
    in_tokens = MOCK_PROMPT_OVERHEAD_TOKENS + len(text) // CHARACTERS_PER_TOKEN
    out_tokens = MOCK_ANSWER_TOKENS + EFFORT_BUDGETS[effort]
    pass_probability = _pass_probability(
        quadrant=quadrant, tier=vendors.TIER_RANK[tier], effort=effort
    )
    return pass_probability, cost_usd(model=model, in_tokens=in_tokens, out_tokens=out_tokens)


def chart(task_estimate: Estimate, path: str, vendor: str | None = None) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    shown_vendors = vendors.chosen(vendor=vendor)
    figure, axes = plt.subplots(figsize=CHART_FIGURE_SIZE)
    efforts = list(EFFORT_BUDGETS.keys())

    for vendor_index, shown_vendor in enumerate(shown_vendors):
        line_style, marker_face = _distinguishable_line_style(vendor_index=vendor_index)
        for tier in vendors.TIERS:
            model = shown_vendor.models[tier]
            costs_in_cents, pass_percents = _projected_curve(
                task_estimate=task_estimate, model=model, tier=tier, efforts=efforts
            )
            axes.plot(
                costs_in_cents,
                pass_percents,
                line_style,
                marker="o",
                mfc=marker_face,
                lw=1.2,
                ms=7,
                alpha=0.85,
                label=model,
            )
            for effort, cost_in_cents, pass_percent in zip(
                efforts, costs_in_cents, pass_percents, strict=True
            ):
                axes.annotate(
                    effort,
                    (cost_in_cents, pass_percent),
                    fontsize=6.5,
                    ha="center",
                    va="bottom",
                    xytext=(0, 5),
                    textcoords="offset points",
                )

    advised_starts = _advised_start_points(task_estimate=task_estimate, shown_vendors=shown_vendors)
    axes.scatter(
        [cost * CENTS_PER_DOLLAR for _, cost in advised_starts],
        [pass_probability * PERCENT_SCALE for pass_probability, _ in advised_starts],
        s=220,
        facecolors="none",
        edgecolors=ADVISED_START_COLOR,
        linewidths=1.8,
        zorder=4,
        label=f"advised start: {task_estimate.start_tier} tier @ {task_estimate.start_effort}",
    )

    axes.set_xlabel("projected cost per attempt (cents)  → cheaper is left")
    axes.set_ylabel("projected pass rate (%)  → better is up")
    axes.set_title(
        f"Projected for a {task_estimate.quadrant} task "
        f"(confidence: {task_estimate.confidence})\n"
        "modelled from the shape, NOT measured — run `modelfit run` for evidence",
        fontsize=10,
    )
    axes.grid(True, alpha=0.25)
    axes.legend(loc="lower right", fontsize=8)
    figure.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=CHART_DPI)
    plt.close(figure)
    return True


def _distinguishable_line_style(vendor_index: int) -> tuple[str, str | None]:
    if vendor_index == 0:
        return SOLID_LINE, None
    return DASHED_LINE, HOLLOW_MARKER_FACE


def _projected_curve(
    task_estimate: Estimate, model: str, tier: str, efforts: list[str]
) -> tuple[list[float], list[float]]:
    costs_in_cents: list[float] = []
    pass_percents: list[float] = []
    for effort in efforts:
        pass_probability, cost = projected_cell(
            text=task_estimate.text,
            model=model,
            tier=tier,
            effort=effort,
            quadrant=task_estimate.quadrant,
        )
        costs_in_cents.append(cost * CENTS_PER_DOLLAR)
        pass_percents.append(pass_probability * PERCENT_SCALE)
    return costs_in_cents, pass_percents


def _advised_start_points(
    task_estimate: Estimate, shown_vendors: list[vendors.Vendor]
) -> list[tuple[float, float]]:
    return [
        projected_cell(
            text=task_estimate.text,
            model=shown_vendor.models[task_estimate.start_tier],
            tier=task_estimate.start_tier,
            effort=task_estimate.start_effort,
            quadrant=task_estimate.quadrant,
        )
        for shown_vendor in shown_vendors
    ]
