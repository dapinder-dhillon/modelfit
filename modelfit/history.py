"""
Local history and the lessons it supports.

Every `modelfit advise` call is appended to `~/.modelfit/history.json` (override
the directory with `MODELFIT_HOME`). Local file, additive writes, nothing sent
anywhere.

The discipline here mirrors the harness's: **only count what was actually
recorded.** Calibration lines are computed from outcomes the user passed in with
`--outcome`, never from a guess about whether the recommendation "probably
worked". An inferred pass rate would be exactly the kind of soft number this
project exists to avoid.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .advisor import Estimate

OUTCOMES = ("pass", "fail")


def history_path(path: str | Path | None = None) -> Path:
    """Where history lives. Explicit path wins, then `MODELFIT_HOME`, then `~/.modelfit`."""
    if path is not None:
        return Path(path)
    home = os.environ.get("MODELFIT_HOME")
    root = Path(home).expanduser() if home else Path.home() / ".modelfit"
    return root / "history.json"


def load(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Read the log. A missing file is an empty history, not an error."""
    target = history_path(path)
    if not target.exists():
        return []
    try:
        data = json.loads(target.read_text())
    except json.JSONDecodeError:
        print(f"warning: history at {target} is corrupted, starting fresh", file=sys.stderr)
        return []
    return data if isinstance(data, list) else []


def record(
    est: Estimate,
    outcome: str | None = None,
    used_effort: str | None = None,
    path: str | Path | None = None,
) -> Path:
    """Append one advice call. Additive: existing entries are never rewritten."""
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {list(OUTCOMES)}, got {outcome!r}")

    target = history_path(path)
    entries = load(target)
    entries.append(
        {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "text": est.text,
            "quadrant": est.quadrant,
            "confidence": est.confidence,
            "runner_up": est.runner_up,
            "effort_score": est.effort_score,
            "model_score": est.model_score,
            "start_model": est.start_model,
            "start_effort": est.start_effort,
            "hidden_knowledge_warning": est.hidden_knowledge_warning,
            "outcome": outcome,
            "used_effort": used_effort,
        }
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(entries, indent=2))
    return target


_STANDING_LESSON = (
    "Standing lesson: the advisor reads wording, not meaning. When it says low "
    "confidence, believe it — crypto, SQL tuning, timezone/DST and concurrency work all "
    "look boring in a one-line prompt."
)


def lessons(path: str | Path | None = None) -> list[str]:
    """What your own history says about your work. Distribution of task shapes,
    calibration against outcomes you recorded, and one lesson that always holds."""
    entries = load(path)
    if not entries:
        return [
            'No advice history yet. Run `modelfit advise "<your task>"` a few times, then '
            "come back — this reads only your own local log.",
            _STANDING_LESSON,
        ]

    out: list[str] = []
    total = len(entries)
    shapes = Counter(str(e.get("quadrant", "?")) for e in entries)
    spread = ", ".join(f"{quad} {n}" for quad, n in shapes.most_common())
    out.append(f"Shapes you have asked about ({total} total): {spread}.")

    top, top_n = shapes.most_common(1)[0]
    dominant = {
        "NEITHER": "Most of your asks look routine — your default config should be the cheap one.",
        "EFFORT": "Most of your asks are deliberation-shaped — effort is your usual lever, "
        "not a bigger model.",
        "MODEL": "Most of your asks need knowledge — paying for model tier is justified "
        "for your work.",
        "BOTH": "Most of your asks are long multi-step work — budget for a strong model at "
        "high effort, and for reading the diff.",
    }.get(top, "")
    if dominant and top_n / total >= 0.4:
        out.append(dominant)

    low = sum(1 for e in entries if e.get("confidence") == "low")
    if low:
        out.append(
            f"{low}/{total} verdicts were low confidence — the wording carried no signal. "
            "Those are the ones to double-check by hand, not to trust."
        )

    recorded = [e for e in entries if e.get("outcome") in OUTCOMES]
    if not recorded:
        out.append(
            "Calibration: 0 outcomes recorded, so nothing is claimed. Pass "
            "`--outcome pass|fail` after you try a recommendation — outcomes are only ever "
            "counted when you record them, never inferred."
        )
    else:
        passed = sum(1 for e in recorded if e["outcome"] == "pass")
        out.append(
            f"Calibration: {passed}/{len(recorded)} recorded outcomes passed at the advised "
            f"start config ({len(recorded)}/{total} asks have a recorded outcome; the rest are "
            "not counted either way)."
        )
        by_quad = Counter(str(e.get("quadrant", "?")) for e in recorded if e["outcome"] == "fail")
        if by_quad:
            worst = ", ".join(f"{quad} ({n})" for quad, n in by_quad.most_common())
            out.append(
                f"Recorded failures at the advised start, by shape: {worst}. "
                "If one shape dominates, the plan for that shape starts too low."
            )

    out.append(_STANDING_LESSON)
    return out
