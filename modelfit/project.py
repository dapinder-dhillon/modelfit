"""
Projection chart for a single advised task.

This draws the *shape of the tradeoff* the advisor's verdict implies: projected
pass rate against projected cost, for every model x effort config, on a task of
the estimated quadrant.

It is a projection, not a measurement. The curve comes from the same
deterministic model the mock uses (`providers._pass_probability`), so the picture
is honest about being an illustration — the numbers you can defend come from
`modelfit run` on your own tasks. The chart is labelled that way on purpose.

matplotlib is the optional `chart` extra, so the import is guarded and a missing
chart is a nicety lost, never an error.
"""

from __future__ import annotations

from pathlib import Path

from . import vendors
from .advisor import Estimate
from .providers import EFFORT_BUDGETS, _pass_probability, cost_usd


def projected_cell(
    text: str, model: str, tier: str, effort: str, quadrant: str
) -> tuple[float, float]:
    """(pass_probability, cost_usd) for one cell. Token counts mirror the mock's
    synthetic usage so the cost axis stays consistent with `modelfit run --mock`:
    the prompt goes in, an answer plus the whole thinking budget comes out.
    Pass probability comes from the tier alone, so two vendors' models in the
    same tier differ here only by price -- the equivalence is assumed, which is
    why the chart says "not measured"."""
    in_tokens = 40 + len(text) // 4
    out_tokens = 120 + EFFORT_BUDGETS[effort]
    prob = _pass_probability(quadrant, vendors.TIER_RANK[tier], effort)
    return prob, cost_usd(model, in_tokens, out_tokens)


def chart(est: Estimate, path: str, vendor: str | None = None) -> bool:
    """Write the projection PNG. Returns False if matplotlib isn't installed."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    shown = vendors.chosen(vendor)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    efforts = list(EFFORT_BUDGETS.keys())

    for i, v in enumerate(shown):
        # Solid lines and filled markers for the first vendor, dashed and hollow
        # for the next: same-tier models at the same price land on the exact
        # same points, and neither should hide the other.
        style, face = ("-", None) if i == 0 else ("--", "none")
        for tier in vendors.TIERS:
            model = v.models[tier]
            xs: list[float] = []
            ys: list[float] = []
            for effort in efforts:
                prob, cost = projected_cell(est.text, model, tier, effort, est.quadrant)
                xs.append(cost * 100)
                ys.append(prob * 100)
            ax.plot(xs, ys, style, marker="o", mfc=face, lw=1.2, ms=7, alpha=0.85, label=model)
            for effort, x, y in zip(efforts, xs, ys, strict=True):
                ax.annotate(
                    effort,
                    (x, y),
                    fontsize=6.5,
                    ha="center",
                    va="bottom",
                    xytext=(0, 5),
                    textcoords="offset points",
                )

    starts = [
        projected_cell(
            est.text, v.models[est.start_tier], est.start_tier, est.start_effort, est.quadrant
        )
        for v in shown
    ]
    ax.scatter(
        [cost * 100 for _, cost in starts],
        [prob * 100 for prob, _ in starts],
        s=220,
        facecolors="none",
        edgecolors="#c0392b",
        linewidths=1.8,
        zorder=4,
        label=f"advised start: {est.start_tier} tier @ {est.start_effort}",
    )

    ax.set_xlabel("projected cost per attempt (cents)  → cheaper is left")
    ax.set_ylabel("projected pass rate (%)  → better is up")
    ax.set_title(
        f"Projected for a {est.quadrant} task (confidence: {est.confidence})\n"
        "modelled from the shape, NOT measured — run `modelfit run` for evidence",
        fontsize=10,
    )
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return True
