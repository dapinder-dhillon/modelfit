"""
Task-shape advisor: which dial to reach for, before you have spent anything.

`modelfit run` answers "which config wins on MY tasks" by measuring. This module
answers the cheaper question people ask first: "I have this one task in front of
me — where do I start?" It answers it by reading the **wording**, with
deterministic regexes and nothing else.

The honesty constraints are the point, not a limitation:

* **No LLM is involved in the decision.** Same text in -> same verdict out,
  forever. An advisor that asked a model which model to use would be circular.
* **Every verdict prints the signals that fired.** No opaque score to trust.
* **Confidence is honest.** Weak or conflicting signals lower it and surface the
  runner-up quadrant. When *nothing* fires, this does NOT report "easy" — it
  keeps confidence low and warns that plain wording hides hard knowledge (crypto,
  SQL tuning, timezones, concurrency).

It reads words, not meaning. It is a second opinion to argue with, not an oracle;
`modelfit run` is where you go for evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# The signals. Each either fires or it doesn't — no weights learned from
# anywhere, no probabilities, nothing to drift. Add one only if you can say in a
# sentence which dial it implies and why.
# --------------------------------------------------------------------------- #

# A condition to carry through the whole answer. Costs deliberation, not talent.
_EXCEPTION = re.compile(r"\b(never|without|except|avoid|not|no|don'?t|must not)\b", re.IGNORECASE)

# Order matters, so state has to survive across steps. Also deliberation.
_ORDERED = re.compile(
    r"\b(then|after|afterwards|before|first|next|finally|once|steps?)\b", re.IGNORECASE
)

# Asks for a call you cannot derive from the prompt alone. That is knowledge.
_JUDGEMENT = re.compile(
    r"\b(review|assess|evaluate|why|best|secure|security|vulnerab\w*|correct|which|recommend"
    r"|design|architect\w*|trade-?offs?|analy\w*|decide|risks?|audit)\b",
    re.IGNORECASE,
)

# Self-directed work over a surface nobody enumerated. Costs both dials.
_BREADTH = re.compile(
    r"\b(refactor\w*|across|entire|all|migrat\w*|whole|repo|repository|codebase"
    r"|end-to-end|multiple|everywhere)\b",
    re.IGNORECASE,
)

# Requirement counting: explicit list items if present, else conjunctions.
_LIST_ITEM = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+")
_CONJUNCTION = re.compile(r"\band\b|\balso\b|\bplus\b|;", re.IGNORECASE)

MANY_REQUIREMENTS = 3  # at or above this, the count itself is a signal

# What each quadrant *is*, in the language of failure shapes.
SHAPES: dict[str, str] = {
    "NEITHER": "recall / boilerplate — one pass, no conditions to carry",
    "EFFORT": "self-contained logic — conditions to hold on to while you work",
    "MODEL": "knowledge / judgement — a call you can't derive from the prompt",
    "BOTH": "long, multi-step, self-directed change over a wide surface",
}

# The dial the shape tells you to turn.
LEVERS: dict[str, str] = {
    "NEITHER": "none",
    "EFFORT": "EFFORT",
    "MODEL": "the MODEL",
    "BOTH": "BOTH — plus human review",
}

# (start_model, start_effort, escalate_to). Model ids come from providers.MODELS.
PLANS: dict[str, tuple[str, str, str | None]] = {
    "NEITHER": ("claude-haiku-4-5", "off", None),
    "EFFORT": ("claude-sonnet-5", "low", "sonnet @ high effort"),
    "MODEL": ("claude-sonnet-5", "high", "opus @ low effort"),
    "BOTH": ("claude-opus-4-8", "high", "human review — don't ship unattended"),
}

_TEACH: dict[str, str] = {
    "NEITHER": (
        "Nothing to turn up: the wording carries no extra conditions, so start at the "
        "cheapest config and escalate only if it actually fails."
    ),
    "EFFORT": (
        "Turn up EFFORT, not the model: the cost here is holding conditions in mind, "
        "and deliberation buys that far more cheaply than talent does."
    ),
    "MODEL": (
        "Turn up the MODEL, not effort: the cost here is knowledge and judgement, "
        "and more thinking time does not supply either."
    ),
    "BOTH": (
        "Turn up BOTH and keep a human in the loop: long self-directed work needs "
        "talent and deliberation, and still deserves someone reading the diff."
    ),
}

# How to tell the primary verdict apart from the runner-up, keyed by runner-up.
_DISTINGUISH: dict[str, str] = {
    "NEITHER": (
        "If the cheapest config just passes first time, the wording oversold it — "
        "drop back to the cheap config and stop paying for the hedge."
    ),
    "EFFORT": (
        "If it fails by contradicting itself or quietly dropping a condition you stated, "
        "that is deliberation — raise effort before you buy a bigger model."
    ),
    "MODEL": (
        "If it fails by reaching for the wrong API, or by making a shallow call it had no "
        "way to derive, that is knowledge — raise the model, not the effort."
    ),
    "BOTH": (
        "If it fails on both counts at once — conditions dropped *and* wrong choices made — "
        "treat it as BOTH: big model, high effort, and read the diff yourself."
    ),
}

_CONFIDENCE_NOTES: dict[str, str] = {
    "high": "Signals agree and there are enough of them; the wording is doing real work here.",
    "medium": "The signals lean one way but not cleanly — the second option below is live.",
    "low": "Little or nothing in the wording to go on. This is a guess, not a reading.",
}

# Domains whose difficulty is invisible in a one-line prompt. Named explicitly so
# the "no signals fired" case says something useful instead of "looks easy".
BLIND_SPOTS = ("crypto", "SQL tuning", "timezones / DST", "concurrency")


@dataclass(frozen=True)
class Estimate:
    """One deterministic reading of one task's wording."""

    text: str
    effort_score: int
    model_score: int
    quadrant: str
    shape: str
    lever: str
    start_model: str
    start_effort: str
    escalate_to: str | None
    reasons: list[str]
    confidence: str  # high | medium | low
    runner_up: str | None  # the other quadrant it could plausibly be
    hidden_knowledge_warning: bool


def plan_for(quadrant: str) -> tuple[str, str, str | None]:
    """(start_model, start_effort, escalate_to) for a quadrant. Where to *start* —
    deliberately the cheapest config that has a real chance, not the safest one."""
    return PLANS[quadrant]


def teach_line(est: Estimate) -> str:
    """One sentence naming the lever. This is the sentence worth remembering when
    the report is closed and there is a task on the screen."""
    return _TEACH[est.quadrant]


def distinguish_hint(runner_up: str | None) -> str:
    """How to tell the primary verdict apart from its runner-up, once the first
    attempt has failed. The failure shape is the tiebreaker the wording couldn't be."""
    if runner_up is None:
        return ""
    return _DISTINGUISH[runner_up]


def confidence_note(confidence: str) -> str:
    return _CONFIDENCE_NOTES[confidence]


def _found(pattern: re.Pattern[str], text: str) -> list[str]:
    """Distinct matched words, in order of first appearance, lowercased."""
    seen: list[str] = []
    for word in pattern.findall(text):
        lowered = word.lower()
        if lowered not in seen:
            seen.append(lowered)
    return seen


def _quote(words: list[str], limit: int = 4) -> str:
    shown = ", ".join(f'"{w}"' for w in words[:limit])
    return f"{shown}, ..." if len(words) > limit else shown


def requirement_count(text: str) -> int:
    """Explicit list items if the task has them, otherwise clauses joined by
    conjunctions. Three separate things to satisfy at once is a different job
    from one thing, however simple each one is."""
    items = len(_LIST_ITEM.findall(text))
    if items:
        return items
    return len(_CONJUNCTION.findall(text)) + 1


def _quadrant_for(effort: int, model: int, breadth: bool) -> str:
    """First match wins. Order encodes the thesis: 'needs both' outranks 'needs
    knowledge', which outranks 'needs deliberation', which outranks 'routine'."""
    if effort >= 4 and (model >= 2 or breadth):
        return "BOTH"
    if model >= 2:
        return "MODEL"
    if effort >= 4:
        return "EFFORT"
    if effort >= 2:
        return "EFFORT"  # one condition sitting on top of otherwise routine work
    return "NEITHER"


def _confidence(
    quadrant: str, effort: int, model: int, breadth: bool, any_signal: bool
) -> tuple[str, str | None, bool]:
    """(confidence, runner_up, hidden_knowledge_warning).

    The rule that matters: silence is not evidence of ease. A task nothing fires
    on gets LOW confidence and a blind-spot warning, never a confident 'easy'."""
    if quadrant == "NEITHER":
        if not any_signal:
            return "low", "MODEL", True
        return "high", None, False
    if quadrant == "EFFORT":
        if model >= 1 and breadth:
            return "medium", "BOTH", False
        if model >= 1:
            return "medium", "MODEL", False
        if effort >= 4:
            return "high", None, False
        return "medium", "NEITHER", False
    if quadrant == "MODEL":
        if effort >= 3:
            return "medium", "BOTH", False
        return "high", None, False
    return ("high" if effort >= 5 and breadth else "medium"), "EFFORT", False


def estimate(text: str) -> Estimate:
    """Read a task's wording and say which dial to turn, why, and how sure it is.

    `effort_need` starts at 1 because every task costs *some* deliberation; the
    model axis starts at 0 because plenty of tasks need no knowledge you did not
    already hand over in the prompt."""
    reasons: list[str] = []
    effort = 1
    model = 0

    exceptions = _found(_EXCEPTION, text)
    if exceptions:
        effort += 2
        reasons.append(
            f"exception / negation wording ({_quote(exceptions)}) → effort +2 — "
            "a condition to carry through the whole answer"
        )

    ordered = _found(_ORDERED, text)
    if ordered:
        effort += 2
        reasons.append(
            f"ordered / multi-step wording ({_quote(ordered)}) → effort +2 — "
            "state has to survive from one step to the next"
        )

    judgement = _found(_JUDGEMENT, text)
    if judgement:
        model += 2
        reasons.append(
            f"judgement / knowledge wording ({_quote(judgement)}) → model +2 — "
            "asks for a call that cannot be derived from the prompt alone"
        )

    breadth_words = _found(_BREADTH, text)
    breadth = bool(breadth_words)
    if breadth:
        effort += 1
        model += 1
        reasons.append(
            f"breadth / self-directed wording ({_quote(breadth_words)}) → effort +1, model +1 — "
            "the surface to change was never enumerated for it"
        )

    requirements = requirement_count(text)
    if requirements >= MANY_REQUIREMENTS:
        effort += 2
        model += 1
        reasons.append(
            f"{requirements} separate requirements to satisfy at once → effort +2, model +1 — "
            "each one is another thing to not drop"
        )

    any_signal = bool(reasons)
    if not any_signal:
        reasons.append(
            "no signal fired — the wording is plain. That is NOT evidence the task is "
            "easy, only that the words carry no difficulty; see the blind-spot note"
        )

    quadrant = _quadrant_for(effort, model, breadth)
    confidence, runner_up, hidden = _confidence(quadrant, effort, model, breadth, any_signal)
    start_model, start_effort, escalate_to = plan_for(quadrant)

    return Estimate(
        text=text.strip(),
        effort_score=effort,
        model_score=model,
        quadrant=quadrant,
        shape=SHAPES[quadrant],
        lever=LEVERS[quadrant],
        start_model=start_model,
        start_effort=start_effort,
        escalate_to=escalate_to,
        reasons=reasons,
        confidence=confidence,
        runner_up=runner_up,
        hidden_knowledge_warning=hidden,
    )
