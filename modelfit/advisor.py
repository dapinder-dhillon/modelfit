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

# "at once" means simultaneous, not sequential -- it's a concurrency signal (see
# _BLIND_SPOT_DOMAIN below), not an ordering one. Matched separately so "once" can
# be dropped from _ORDERED's results when it's really "at once" in disguise,
# without corrupting _ORDERED's single capture group (findall needs every
# alternative in a pattern to share one group, or the ungrouped branches come
# back as empty strings instead of the matched text).
_AT_ONCE = re.compile(r"\bat once\b", re.IGNORECASE)

# Asks for a call you cannot derive from the prompt alone. That is knowledge.
_JUDGEMENT = re.compile(
    r"\b(review|assess|evaluate|why|best|secure|security|vulnerab\w*|correct|which|recommend"
    r"|design|architect\w*|trade-?offs?|analy\w*|decide|risks?|audit)\b",
    re.IGNORECASE,
)

# A mechanical, rote operation -- sorting, deduplicating, formatting. When
# "review" is the ONLY judgement word matched and one of these is also present,
# "review" is almost always filler ("review the list and sort it"), not a real
# judgement call. Narrow on purpose: this discounts one specific weak word in one
# specific context, not a general "ignore review" rule.
_MECHANICAL = re.compile(
    r"\b(sort(?:ed|ing)?|order(?:ed|ing)?|alphabetiz\w*|dedup(?:licate|e)?\w*|format(?:ted|ting)?)\b",
    re.IGNORECASE,
)

# Self-directed work over a surface nobody enumerated. Costs both dials.
_BREADTH = re.compile(
    r"\b(refactor\w*|across|entire|all|migrat\w*|whole|repo|repository|codebase"
    r"|end-to-end|multiple|everywhere)\b",
    re.IGNORECASE,
)

# The task explicitly names one of the four documented blind-spot domains
# (crypto, SQL/query tuning, timezones, concurrency). This is deliberately a
# SMALL, tight list of unambiguous domain words, not a general difficulty
# detector -- when it fires, treat it as real knowledge, not a coin flip: a
# named domain is a much stronger signal than an isolated generic word like
# "review" ever is.
_BLIND_SPOT_DOMAIN = re.compile(
    r"\b(sql|quer(?:y|ies)|crypto\w*|encrypt\w*|decrypt\w*|cipher|nonce|\baes\b|\brsa\b"
    r"|signature|jwt|hash(?:ing)?|timezone\w*|time zone\w*|\bdst\b|daylight[- ]saving\w*"
    r"|\butc\b|concurren\w*|thread\w*|race condition|deadlock|\bmutex\b|simultaneous\w*"
    r"|at once|at the same time)\b",
    re.IGNORECASE,
)

# Requirement counting: explicit list items if present, else conjunctions.
_LIST_ITEM = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+")
_CONJUNCTION = re.compile(r"\band\b|\balso\b|\bplus\b|;", re.IGNORECASE)

MANY_REQUIREMENTS = 3  # at or above this, the count itself is a signal

# Short phrase per signal, for the one-line WHY in the compact default view.
# The long form in `reasons` (below) is the --explain version of the same fact.
_SHORT_EXCEPTION = "a condition must stay true"
_SHORT_ORDERED = "order matters"
_SHORT_JUDGEMENT = "needs judgement the prompt doesn't provide"
_SHORT_DOMAIN = "needs real domain expertise, not just more thinking"
_SHORT_BREADTH = "spans a lot of ground, self-directed"

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
# escalate_to is a full actionable phrase, not a bare "model @ effort" label --
# it's printed as "If it fails: <escalate_to>", so it has to read as an instruction.
PLANS: dict[str, tuple[str, str, str | None]] = {
    "NEITHER": ("claude-haiku-4-5", "off", None),
    "EFFORT": ("claude-sonnet-5", "low", "raise effort to high before switching model"),
    "MODEL": (
        "claude-sonnet-5",
        "high",
        # Deliberately keeps effort at "high", unchanged from the start config --
        # the whole claim of this quadrant is "turn up the model, not effort", so
        # the escalation has to actually move only that one dial to back it up.
        "switch to opus-4-8, same high effort",
    ),
    "BOTH": ("claude-opus-4-8", "high", "have a human review it — don't use it unattended"),
}

_TEACH: dict[str, str] = {
    "NEITHER": (
        "Nothing needs turning up. Start with the cheapest config and escalate only if it fails."
    ),
    "EFFORT": (
        "Turn up EFFORT, not the model. This task needs more thinking time, "
        "not more model capability."
    ),
    "MODEL": (
        "Turn up the MODEL, not effort. This task needs more knowledge or judgement; "
        "more thinking time will not add either."
    ),
    "BOTH": (
        "Turn up BOTH and keep a human in the loop. Long, self-directed work needs a "
        "more capable model and more thinking time, and the result still needs review."
    ),
}

# How to tell the primary verdict apart from the runner-up, keyed by runner-up.
_DISTINGUISH: dict[str, str] = {
    "NEITHER": (
        "If the cheapest config passes first time, the wording made the task look "
        "harder than it was. Use the cheap config."
    ),
    "EFFORT": (
        "If it contradicts itself or drops one of your conditions, it needs more "
        "thinking time. Raise effort before switching to a bigger model."
    ),
    "MODEL": (
        "If it reaches for the wrong API, or makes a call it had no way to know was "
        "right, that's a knowledge gap — raise the model, not the effort."
    ),
    "BOTH": (
        "If it drops conditions and makes wrong choices, treat it as BOTH: use a "
        "bigger model, high effort, and review the result yourself."
    ),
}

_CONFIDENCE_NOTES: dict[str, str] = {
    "high": "Several signals point the same way, so confidence is high.",
    "medium": "The signals lean one way, but another result is still plausible.",
    "low": "There is little or nothing in the wording to go on. Treat this as a guess.",
}

# A short tag naming WHAT the confidence is about -- shown next to the bare
# high/medium/low in the compact default view, because "confidence" alone
# doesn't say confidence in what (not the model, not success -- this reading).
_CONFIDENCE_TAGS: dict[str, str] = {
    "high": "clear read of your wording",
    "medium": "could be read another way",
    "low": "just a guess — see below",
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
    why_short: str  # one line: your words -> what they imply, for the compact view
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
    if est.hidden_knowledge_warning:
        # _TEACH["NEITHER"] says "nothing needs turning up" -- true of the
        # wording, but printed right alongside the blind-spot warning that
        # says the opposite might be true, it reads as a flat contradiction.
        return (
            "Nothing fired, so this isn't a confident 'nothing to turn up' -- "
            "it's a guess. See the blind-spot warning before trusting it."
        )
    return _TEACH[est.quadrant]


def distinguish_hint(runner_up: str | None) -> str:
    """How to tell the primary verdict apart from its runner-up, once the first
    attempt has failed. The failure shape is the tiebreaker the wording couldn't be."""
    if runner_up is None:
        return ""
    return _DISTINGUISH[runner_up]


def confidence_note(confidence: str) -> str:
    return _CONFIDENCE_NOTES[confidence]


def confidence_tag(confidence: str) -> str:
    """Short label for what the confidence is about: this reading of the
    wording, not the model's odds of success."""
    return _CONFIDENCE_TAGS[confidence]


_EFFORT_PHRASES: dict[str, str] = {
    "off": "no extra thinking",
    "low": "low effort",
    "high": "high effort",
}


def effort_phrase(effort: str) -> str:
    """Natural phrase for an effort value in a sentence. "off" isn't a degree
    the way low/high are -- it's a toggle, so "off effort" reads like a typo.
    Use this wherever effort appears in prose; the raw value (e.g. in a CLI
    flag or backtick-quoted config citation) is fine as-is."""
    return _EFFORT_PHRASES[effort]


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


def _and_join(items: list[str]) -> str:
    """ "a", "b" and "c" -- for naming the exact words matched, readably."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


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
    quadrant: str,
    effort: int,
    model: int,
    breadth: bool,
    any_signal: bool,
    judgement_count: int,
    domain_hit: bool,
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
        if judgement_count <= 1 and not breadth and not domain_hit:
            # A single generic judgement word ("review", "correct", "which") is a
            # weak signal alone -- "review the list and sort it" shouldn't read as
            # confidently as "review this IAM policy for security risks". Don't
            # claim high confidence for a lone match with nothing backing it up.
            # A named blind-spot domain (crypto/SQL/timezone/concurrency) is exempt:
            # unlike a generic word, naming the domain isn't ambiguous filler.
            return "medium", "NEITHER", False
        return "high", None, False
    return ("high" if effort >= 5 and breadth else "medium"), "EFFORT", False


def estimate(text: str) -> Estimate:
    """Read a task's wording and say which dial to turn, why, and how sure it is.

    `effort_need` starts at 1 because every task costs *some* deliberation; the
    model axis starts at 0 because plenty of tasks need no knowledge you did not
    already hand over in the prompt."""
    reasons: list[str] = []
    why_words: list[str] = []
    why_phrases: list[str] = []
    effort = 1
    model = 0

    exceptions = _found(_EXCEPTION, text)
    if exceptions:
        effort += 2
        reasons.append(
            f"exception / negation wording ({_quote(exceptions)}) → effort +2 — "
            "a condition to carry through the whole answer"
        )
        why_words += exceptions[:2]
        why_phrases.append(_SHORT_EXCEPTION)

    ordered = _found(_ORDERED, text)
    if _AT_ONCE.search(text):
        # "at once" means simultaneous, not sequential -- don't let it pass as
        # an ordering signal when it's really a concurrency one.
        ordered = [w for w in ordered if w != "once"]
    if ordered:
        effort += 2
        reasons.append(
            f"ordered / multi-step wording ({_quote(ordered)}) → effort +2 — "
            "state has to survive from one step to the next"
        )
        why_words += ordered[:2]
        why_phrases.append(_SHORT_ORDERED)

    judgement = _found(_JUDGEMENT, text)
    mechanical = _found(_MECHANICAL, text)
    if mechanical and "review" in judgement:
        # "review the list and sort it" -- "review" is filler next to a
        # mechanical operation, not a real judgement call. Narrow: only "review"
        # itself is discounted, and only in this specific context.
        judgement = [w for w in judgement if w != "review"]
    if judgement:
        model += 2
        reasons.append(
            f"judgement / knowledge wording ({_quote(judgement)}) → model +2 — "
            "asks for a call that cannot be derived from the prompt alone"
        )
        why_words += judgement[:2]
        why_phrases.append(_SHORT_JUDGEMENT)

    domain_words = _found(_BLIND_SPOT_DOMAIN, text)
    if domain_words:
        model += 2
        reasons.append(
            f"names a documented blind-spot domain ({_quote(domain_words)}) → model +2 — "
            "crypto/SQL/timezone/concurrency topics need real expertise, not just more thinking"
        )
        why_words += domain_words[:2]
        why_phrases.append(_SHORT_DOMAIN)

    breadth_words = _found(_BREADTH, text)
    breadth = bool(breadth_words)
    if breadth:
        effort += 1
        model += 1
        reasons.append(
            f"breadth / self-directed wording ({_quote(breadth_words)}) → effort +1, model +1 — "
            "the surface to change was never enumerated for it"
        )
        why_words += breadth_words[:2]
        why_phrases.append(_SHORT_BREADTH)

    requirements = requirement_count(text)
    if requirements >= MANY_REQUIREMENTS:
        effort += 2
        model += 1
        reasons.append(
            f"{requirements} separate requirements to satisfy at once → effort +2, model +1 — "
            "each one is another thing to not drop"
        )
        why_phrases.append(f"{requirements} requirements to track at once")

    any_signal = bool(reasons)
    if not any_signal:
        reasons.append(
            "no signal fired — the wording is plain. That is NOT evidence the task is "
            "easy, only that the words carry no difficulty; see the blind-spot note"
        )
        why_short = "nothing in the wording — see the blind-spot note"
    else:
        quoted = _and_join([f'"{w}"' for w in why_words[:4]])
        implies = "; ".join(why_phrases)
        why_short = f"your wording has {quoted} → {implies}" if quoted else implies

    quadrant = _quadrant_for(effort, model, breadth)
    confidence, runner_up, hidden = _confidence(
        quadrant, effort, model, breadth, any_signal, len(judgement), bool(domain_words)
    )
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
        why_short=why_short,
        confidence=confidence,
        runner_up=runner_up,
        hidden_knowledge_warning=hidden,
    )
