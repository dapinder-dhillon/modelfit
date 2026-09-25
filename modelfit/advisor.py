from __future__ import annotations

import re
from dataclasses import dataclass

NEITHER_QUADRANT = "NEITHER"
EFFORT_QUADRANT = "EFFORT"
MODEL_QUADRANT = "MODEL"
BOTH_QUADRANT = "BOTH"

HIGH_CONFIDENCE = "high"
MEDIUM_CONFIDENCE = "medium"
LOW_CONFIDENCE = "low"

BASELINE_EFFORT_NEED = 1
BASELINE_MODEL_NEED = 0
CONDITION_EFFORT_POINTS = 2
ORDERING_EFFORT_POINTS = 2
JUDGEMENT_MODEL_POINTS = 2
DOMAIN_MODEL_POINTS = 2
BREADTH_EFFORT_POINTS = 1
BREADTH_MODEL_POINTS = 1
REQUIREMENTS_EFFORT_POINTS = 2
REQUIREMENTS_MODEL_POINTS = 1
MANY_REQUIREMENTS = 3

BOTH_EFFORT_NEED = 4
MODEL_NEED = 2
STRONG_EFFORT_NEED = 4
SINGLE_CONDITION_EFFORT_NEED = 2
MODEL_NEED_HINT = 1
EFFORT_NEED_SUGGESTING_BOTH = 3
CONFIDENT_BOTH_EFFORT_NEED = 5
LONE_JUDGEMENT_WORD_COUNT = 1

WHY_WORDS_PER_SIGNAL = 2
WHY_WORDS_SHOWN = 4
QUOTED_WORDS_SHOWN = 4
FILLER_JUDGEMENT_WORD = "review"
AT_ONCE_ORDERING_WORD = "once"

_CONDITION_WORDS_NEEDING_EFFORT = re.compile(
    r"\b(never|without|except|avoid|not|no|don'?t|must not)\b", re.IGNORECASE
)

_ORDERING_WORDS_NEEDING_EFFORT = re.compile(
    r"\b(then|after|afterwards|before|first|next|finally|once|steps?)\b", re.IGNORECASE
)

# separate from the ordering pattern: findall returns "" for alternatives outside its group.
_AT_ONCE = re.compile(r"\bat once\b", re.IGNORECASE)

_JUDGEMENT_WORDS_NEEDING_MODEL = re.compile(
    r"\b(review|assess|evaluate|why|best|secure|security|vulnerab\w*|correct|which|recommend"
    r"|design|architect\w*|trade-?offs?|analy\w*|decide|risks?|audit)\b",
    re.IGNORECASE,
)

_MECHANICAL_OPERATION_WORDS = re.compile(
    r"\b(sort(?:ed|ing)?|order(?:ed|ing)?|alphabetiz\w*|dedup(?:licate|e)?\w*|format(?:ted|ting)?)\b",
    re.IGNORECASE,
)

_BREADTH_WORDS_NEEDING_BOTH = re.compile(
    r"\b(refactor\w*|across|entire|all|migrat\w*|whole|repo|repository|codebase"
    r"|end-to-end|multiple|everywhere)\b",
    re.IGNORECASE,
)

_BLIND_SPOT_DOMAIN_WORDS_NEEDING_MODEL = re.compile(
    r"\b(sql|quer(?:y|ies)|crypto\w*|encrypt\w*|decrypt\w*|cipher|nonce|\baes\b|\brsa\b"
    r"|signature|jwt|hash(?:ing)?|timezone\w*|time zone\w*|\bdst\b|daylight[- ]saving\w*"
    r"|\butc\b|concurren\w*|thread\w*|race condition|deadlock|\bmutex\b|simultaneous\w*"
    r"|at once|at the same time)\b",
    re.IGNORECASE,
)

_LIST_ITEM = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+")
_CONJUNCTION = re.compile(r"\band\b|\balso\b|\bplus\b|;", re.IGNORECASE)

_SHORT_EXCEPTION = "a condition must stay true"
_SHORT_ORDERED = "order matters"
_SHORT_JUDGEMENT = "needs judgement the prompt doesn't provide"
_SHORT_DOMAIN = "needs real domain expertise, not just more thinking"
_SHORT_BREADTH = "spans a lot of ground, self-directed"

_NO_SIGNAL_REASON = (
    "no signal fired — the wording is plain. That is NOT evidence the task is "
    "easy, only that the words carry no difficulty; see the blind-spot note"
)
_NO_SIGNAL_WHY = "nothing in the wording — see the blind-spot note"

SHAPES: dict[str, str] = {
    NEITHER_QUADRANT: "recall / boilerplate — one pass, no conditions to carry",
    EFFORT_QUADRANT: "self-contained logic — conditions to hold on to while you work",
    MODEL_QUADRANT: "knowledge / judgement — a call you can't derive from the prompt",
    BOTH_QUADRANT: "long, multi-step, self-directed change over a wide surface",
}

LEVERS: dict[str, str] = {
    NEITHER_QUADRANT: "none",
    EFFORT_QUADRANT: "EFFORT",
    MODEL_QUADRANT: "the MODEL",
    BOTH_QUADRANT: "BOTH — plus human review",
}

PLANS: dict[str, tuple[str, str, str | None]] = {
    NEITHER_QUADRANT: ("small", "off", None),
    EFFORT_QUADRANT: ("mid", "low", "raise effort to high before switching model"),
    MODEL_QUADRANT: ("mid", "high", "switch to {large}, same high effort"),
    BOTH_QUADRANT: ("large", "high", "have a human review it — don't use it unattended"),
}

_TEACH: dict[str, str] = {
    NEITHER_QUADRANT: (
        "Nothing needs turning up. Start with the cheapest config and escalate only if it fails."
    ),
    EFFORT_QUADRANT: (
        "Turn up EFFORT, not the model. This task needs more thinking time, "
        "not more model capability."
    ),
    MODEL_QUADRANT: (
        "Turn up the MODEL, not effort. This task needs more knowledge or judgement; "
        "more thinking time will not add either."
    ),
    BOTH_QUADRANT: (
        "Turn up BOTH and keep a human in the loop. Long, self-directed work needs a "
        "more capable model and more thinking time, and the result still needs review."
    ),
}

_BLIND_SPOT_TEACH_LINE = (
    "Nothing fired, so this isn't a confident 'nothing to turn up' -- "
    "it's a guess. See the blind-spot warning before trusting it."
)

_DISTINGUISH: dict[str, str] = {
    NEITHER_QUADRANT: (
        "If the cheapest config passes first time, the wording made the task look "
        "harder than it was. Use the cheap config."
    ),
    EFFORT_QUADRANT: (
        "If it contradicts itself or drops one of your conditions, it needs more "
        "thinking time. Raise effort before switching to a bigger model."
    ),
    MODEL_QUADRANT: (
        "If it reaches for the wrong API, or makes a call it had no way to know was "
        "right, that's a knowledge gap — raise the model, not the effort."
    ),
    BOTH_QUADRANT: (
        "If it drops conditions and makes wrong choices, treat it as BOTH: use a "
        "bigger model, high effort, and review the result yourself."
    ),
}

_CONFIDENCE_NOTES: dict[str, str] = {
    HIGH_CONFIDENCE: "Several signals point the same way, so confidence is high.",
    MEDIUM_CONFIDENCE: "The signals lean one way, but another result is still plausible.",
    LOW_CONFIDENCE: "There is little or nothing in the wording to go on. Treat this as a guess.",
}

_CONFIDENCE_TAGS: dict[str, str] = {
    HIGH_CONFIDENCE: "clear read of your wording",
    MEDIUM_CONFIDENCE: "could be read another way",
    LOW_CONFIDENCE: "just a guess — see below",
}

_EFFORT_PHRASES: dict[str, str] = {
    "off": "no extra thinking",
    "low": "low effort",
    "high": "high effort",
}

BLIND_SPOTS = ("crypto", "SQL tuning", "timezones / DST", "concurrency")


@dataclass(frozen=True)
class Estimate:
    text: str
    effort_score: int
    model_score: int
    quadrant: str
    shape: str
    lever: str
    start_tier: str
    start_effort: str
    escalate_to: str | None
    reasons: list[str]
    why_short: str
    confidence: str
    runner_up: str | None
    hidden_knowledge_warning: bool


@dataclass(frozen=True)
class _Signal:
    effort_points: int
    model_points: int
    reason: str
    why_words: list[str]
    why_phrase: str


def estimate(text: str) -> Estimate:
    condition_words = _found(pattern=_CONDITION_WORDS_NEEDING_EFFORT, text=text)
    ordering_words = _ordering_words(text=text)
    judgement_words = _judgement_words(text=text)
    domain_words = _found(pattern=_BLIND_SPOT_DOMAIN_WORDS_NEEDING_MODEL, text=text)
    breadth_words = _found(pattern=_BREADTH_WORDS_NEEDING_BOTH, text=text)
    requirements = requirement_count(text=text)
    signals = _fired_signals(
        condition_words=condition_words,
        ordering_words=ordering_words,
        judgement_words=judgement_words,
        domain_words=domain_words,
        breadth_words=breadth_words,
        requirements=requirements,
    )
    effort_score = BASELINE_EFFORT_NEED + sum(signal.effort_points for signal in signals)
    model_score = BASELINE_MODEL_NEED + sum(signal.model_points for signal in signals)
    breadth = len(breadth_words) > 0
    any_signal = len(signals) > 0
    quadrant = _quadrant_for(effort=effort_score, model=model_score, breadth=breadth)
    confidence, runner_up, hidden = _confidence(
        quadrant=quadrant,
        effort=effort_score,
        model=model_score,
        breadth=breadth,
        any_signal=any_signal,
        judgement_count=len(judgement_words),
        domain_hit=len(domain_words) > 0,
    )
    start_tier, start_effort, escalate_to = plan_for(quadrant=quadrant)
    return Estimate(
        text=text.strip(),
        effort_score=effort_score,
        model_score=model_score,
        quadrant=quadrant,
        shape=SHAPES[quadrant],
        lever=LEVERS[quadrant],
        start_tier=start_tier,
        start_effort=start_effort,
        escalate_to=escalate_to,
        reasons=_reasons(signals=signals),
        why_short=_why_short(signals=signals),
        confidence=confidence,
        runner_up=runner_up,
        hidden_knowledge_warning=hidden,
    )


def plan_for(quadrant: str) -> tuple[str, str, str | None]:
    return PLANS[quadrant]


def teach_line(task_estimate: Estimate) -> str:
    if task_estimate.hidden_knowledge_warning is True:
        return _BLIND_SPOT_TEACH_LINE
    return _TEACH[task_estimate.quadrant]


def distinguish_hint(runner_up: str | None) -> str:
    if runner_up is None:
        return ""
    return _DISTINGUISH[runner_up]


def confidence_note(confidence: str) -> str:
    return _CONFIDENCE_NOTES[confidence]


def confidence_tag(confidence: str) -> str:
    return _CONFIDENCE_TAGS[confidence]


def effort_phrase(effort: str) -> str:
    return _EFFORT_PHRASES[effort]


def requirement_count(text: str) -> int:
    list_items = len(_LIST_ITEM.findall(text))
    if list_items > 0:
        return list_items
    return len(_CONJUNCTION.findall(text)) + 1


def _found(pattern: re.Pattern[str], text: str) -> list[str]:
    seen: list[str] = []
    for word in pattern.findall(text):
        lowered = word.lower()
        if lowered not in seen:
            seen.append(lowered)
    return seen


def _ordering_words(text: str) -> list[str]:
    ordering_words = _found(pattern=_ORDERING_WORDS_NEEDING_EFFORT, text=text)
    if _AT_ONCE.search(text) is not None:
        return [word for word in ordering_words if word != AT_ONCE_ORDERING_WORD]
    return ordering_words


def _judgement_words(text: str) -> list[str]:
    judgement_words = _found(pattern=_JUDGEMENT_WORDS_NEEDING_MODEL, text=text)
    mechanical_words = _found(pattern=_MECHANICAL_OPERATION_WORDS, text=text)
    if len(mechanical_words) > 0 and FILLER_JUDGEMENT_WORD in judgement_words:
        return [word for word in judgement_words if word != FILLER_JUDGEMENT_WORD]
    return judgement_words


def _fired_signals(
    condition_words: list[str],
    ordering_words: list[str],
    judgement_words: list[str],
    domain_words: list[str],
    breadth_words: list[str],
    requirements: int,
) -> list[_Signal]:
    candidate_signals = [
        _condition_signal(condition_words=condition_words),
        _ordering_signal(ordering_words=ordering_words),
        _judgement_signal(judgement_words=judgement_words),
        _domain_signal(domain_words=domain_words),
        _breadth_signal(breadth_words=breadth_words),
        _requirements_signal(requirements=requirements),
    ]
    return [signal for signal in candidate_signals if signal is not None]


def _condition_signal(condition_words: list[str]) -> _Signal | None:
    if len(condition_words) == 0:
        return None
    return _Signal(
        effort_points=CONDITION_EFFORT_POINTS,
        model_points=0,
        reason=(
            f"exception / negation wording ({_quote(words=condition_words)}) "
            f"→ effort +{CONDITION_EFFORT_POINTS} — "
            "a condition to carry through the whole answer"
        ),
        why_words=condition_words[:WHY_WORDS_PER_SIGNAL],
        why_phrase=_SHORT_EXCEPTION,
    )


def _ordering_signal(ordering_words: list[str]) -> _Signal | None:
    if len(ordering_words) == 0:
        return None
    return _Signal(
        effort_points=ORDERING_EFFORT_POINTS,
        model_points=0,
        reason=(
            f"ordered / multi-step wording ({_quote(words=ordering_words)}) "
            f"→ effort +{ORDERING_EFFORT_POINTS} — "
            "state has to survive from one step to the next"
        ),
        why_words=ordering_words[:WHY_WORDS_PER_SIGNAL],
        why_phrase=_SHORT_ORDERED,
    )


def _judgement_signal(judgement_words: list[str]) -> _Signal | None:
    if len(judgement_words) == 0:
        return None
    return _Signal(
        effort_points=0,
        model_points=JUDGEMENT_MODEL_POINTS,
        reason=(
            f"judgement / knowledge wording ({_quote(words=judgement_words)}) "
            f"→ model +{JUDGEMENT_MODEL_POINTS} — "
            "asks for a call that cannot be derived from the prompt alone"
        ),
        why_words=judgement_words[:WHY_WORDS_PER_SIGNAL],
        why_phrase=_SHORT_JUDGEMENT,
    )


def _domain_signal(domain_words: list[str]) -> _Signal | None:
    if len(domain_words) == 0:
        return None
    return _Signal(
        effort_points=0,
        model_points=DOMAIN_MODEL_POINTS,
        reason=(
            f"names a documented blind-spot domain ({_quote(words=domain_words)}) "
            f"→ model +{DOMAIN_MODEL_POINTS} — "
            "crypto/SQL/timezone/concurrency topics need real expertise, not just more thinking"
        ),
        why_words=domain_words[:WHY_WORDS_PER_SIGNAL],
        why_phrase=_SHORT_DOMAIN,
    )


def _breadth_signal(breadth_words: list[str]) -> _Signal | None:
    if len(breadth_words) == 0:
        return None
    return _Signal(
        effort_points=BREADTH_EFFORT_POINTS,
        model_points=BREADTH_MODEL_POINTS,
        reason=(
            f"breadth / self-directed wording ({_quote(words=breadth_words)}) "
            f"→ effort +{BREADTH_EFFORT_POINTS}, model +{BREADTH_MODEL_POINTS} — "
            "the surface to change was never enumerated for it"
        ),
        why_words=breadth_words[:WHY_WORDS_PER_SIGNAL],
        why_phrase=_SHORT_BREADTH,
    )


def _requirements_signal(requirements: int) -> _Signal | None:
    if requirements < MANY_REQUIREMENTS:
        return None
    return _Signal(
        effort_points=REQUIREMENTS_EFFORT_POINTS,
        model_points=REQUIREMENTS_MODEL_POINTS,
        reason=(
            f"{requirements} separate requirements to satisfy at once "
            f"→ effort +{REQUIREMENTS_EFFORT_POINTS}, model +{REQUIREMENTS_MODEL_POINTS} — "
            "each one is another thing to not drop"
        ),
        why_words=[],
        why_phrase=f"{requirements} requirements to track at once",
    )


def _reasons(signals: list[_Signal]) -> list[str]:
    if len(signals) == 0:
        return [_NO_SIGNAL_REASON]
    return [signal.reason for signal in signals]


def _why_short(signals: list[_Signal]) -> str:
    if len(signals) == 0:
        return _NO_SIGNAL_WHY
    why_words: list[str] = []
    for signal in signals:
        why_words += signal.why_words
    quoted = _and_join(items=[f'"{word}"' for word in why_words[:WHY_WORDS_SHOWN]])
    implies = "; ".join(signal.why_phrase for signal in signals)
    if len(quoted) > 0:
        return f"your wording has {quoted} → {implies}"
    return implies


def _quote(words: list[str], limit: int = QUOTED_WORDS_SHOWN) -> str:
    shown = ", ".join(f'"{word}"' for word in words[:limit])
    if len(words) > limit:
        return f"{shown}, ..."
    return shown


def _and_join(items: list[str]) -> str:
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _quadrant_for(effort: int, model: int, breadth: bool) -> str:
    if effort >= BOTH_EFFORT_NEED and (model >= MODEL_NEED or breadth is True):
        return BOTH_QUADRANT
    if model >= MODEL_NEED:
        return MODEL_QUADRANT
    if effort >= STRONG_EFFORT_NEED:
        return EFFORT_QUADRANT
    if effort >= SINGLE_CONDITION_EFFORT_NEED:
        return EFFORT_QUADRANT
    return NEITHER_QUADRANT


def _confidence(
    quadrant: str,
    effort: int,
    model: int,
    breadth: bool,
    any_signal: bool,
    judgement_count: int,
    domain_hit: bool,
) -> tuple[str, str | None, bool]:
    if quadrant == NEITHER_QUADRANT:
        return _neither_confidence(any_signal=any_signal)
    if quadrant == EFFORT_QUADRANT:
        return _effort_confidence(effort=effort, model=model, breadth=breadth)
    if quadrant == MODEL_QUADRANT:
        return _model_confidence(
            effort=effort, breadth=breadth, judgement_count=judgement_count, domain_hit=domain_hit
        )
    return _both_confidence(effort=effort, breadth=breadth)


def _neither_confidence(any_signal: bool) -> tuple[str, str | None, bool]:
    if any_signal is False:
        return LOW_CONFIDENCE, MODEL_QUADRANT, True
    return HIGH_CONFIDENCE, None, False


def _effort_confidence(effort: int, model: int, breadth: bool) -> tuple[str, str | None, bool]:
    if model >= MODEL_NEED_HINT and breadth is True:
        return MEDIUM_CONFIDENCE, BOTH_QUADRANT, False
    if model >= MODEL_NEED_HINT:
        return MEDIUM_CONFIDENCE, MODEL_QUADRANT, False
    if effort >= STRONG_EFFORT_NEED:
        return HIGH_CONFIDENCE, None, False
    return MEDIUM_CONFIDENCE, NEITHER_QUADRANT, False


def _model_confidence(
    effort: int, breadth: bool, judgement_count: int, domain_hit: bool
) -> tuple[str, str | None, bool]:
    if effort >= EFFORT_NEED_SUGGESTING_BOTH:
        return MEDIUM_CONFIDENCE, BOTH_QUADRANT, False
    if (
        _is_lone_generic_judgement(
            judgement_count=judgement_count, breadth=breadth, domain_hit=domain_hit
        )
        is True
    ):
        return MEDIUM_CONFIDENCE, NEITHER_QUADRANT, False
    return HIGH_CONFIDENCE, None, False


def _is_lone_generic_judgement(judgement_count: int, breadth: bool, domain_hit: bool) -> bool:
    if judgement_count <= LONE_JUDGEMENT_WORD_COUNT and breadth is False and domain_hit is False:
        return True
    return False


def _both_confidence(effort: int, breadth: bool) -> tuple[str, str | None, bool]:
    if effort >= CONFIDENT_BOTH_EFFORT_NEED and breadth is True:
        return HIGH_CONFIDENCE, EFFORT_QUADRANT, False
    return MEDIUM_CONFIDENCE, EFFORT_QUADRANT, False
