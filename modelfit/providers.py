"""
Provider layer.

Two dials live here:
  MODELS  : ordered by capability tier (edit to match what you have access to)
  EFFORT  : mapped to a thinking-token budget (Anthropic 'thinking' /
            OpenAI 'reasoning_effort' express the same idea)

Also here: an editable PRICING table (verify current numbers yourself; prices
change), a real Anthropic call, and a DETERMINISTIC mock so the harness runs
end-to-end with no API key and produces a stable, defensible sample report.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass

# Capability tier is just an ordinal used by the mock and for sorting.
MODELS: dict[str, int] = {
    "claude-haiku-4-5": 1,
    "claude-sonnet-5": 2,
    "claude-opus-4-8": 3,
    "claude-fable-5": 4,
}

# Effort dial -> thinking-token budget. 0 == thinking disabled.
EFFORT_BUDGETS: dict[str, int] = {
    "off": 0,
    "low": 2000,
    "high": 10000,
}

# $ per MILLION tokens (input, output). Thinking tokens are billed as output.
# >>> THESE ARE PLACEHOLDERS. Confirm current pricing before you trust the $ figures. <<<
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.80, 4.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-fable-5": (10.0, 50.0),
}


@dataclass
class Call:
    text: str
    in_tokens: int
    out_tokens: int
    latency_s: float


def cost_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    pin, pout = PRICING[model]
    return in_tokens / 1e6 * pin + out_tokens / 1e6 * pout


# --------------------------------------------------------------------------- #
# Real Anthropic call (used with --real). Requires: pip install anthropic
# and ANTHROPIC_API_KEY in the environment.
# --------------------------------------------------------------------------- #
def call_real(model: str, effort: str, prompt: str, max_tokens: int) -> Call:
    import anthropic  # imported lazily so mock mode needs no dependency

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Export it before running with --real.")
    client = anthropic.Anthropic(api_key=api_key)
    budget = EFFORT_BUDGETS[effort]
    kwargs: dict = {
        "model": model,
        "max_tokens": max(max_tokens, budget + 512),
        "messages": [{"role": "user", "content": prompt}],
    }
    if budget:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    t0 = time.time()
    resp = client.messages.create(**kwargs)
    latency = time.time() - t0

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return Call(text, resp.usage.input_tokens, resp.usage.output_tokens, latency)


# --------------------------------------------------------------------------- #
# Deterministic mock. Encodes the thesis so the sample report tells the story:
#   NEITHER -> everyone passes; cheapest config wins on cost-per-solved
#   EFFORT  -> pass rate driven by EFFORT, weakly by model
#   MODEL   -> pass rate driven by MODEL tier, weakly by effort
#   BOTH    -> only a strong model AT high effort is reliable
# It is fully deterministic (hash-thresholded), so reruns are identical.
# --------------------------------------------------------------------------- #
_EFFORT_ORD = {"off": 0, "low": 1, "high": 2}


def _stable_unit(*parts: str) -> float:
    h = hashlib.sha256("::".join(parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF  # in [0, 1)


def _pass_probability(quadrant: str, tier: int, effort: str) -> float:
    e = _EFFORT_ORD[effort]  # 0,1,2
    if quadrant == "NEITHER":
        return 0.99
    if quadrant == "EFFORT":
        base = {0: 0.15, 1: 0.60, 2: 0.92}[e]
        return min(0.98, base + 0.03 * (tier - 1))  # model barely helps
    if quadrant == "MODEL":
        base = {1: 0.15, 2: 0.50, 3: 0.85, 4: 0.95}[tier]
        return min(0.98, base + 0.04 * e)  # effort barely helps
    if quadrant == "BOTH":
        if tier >= 3 and e == 2:
            return 0.90
        if tier >= 3 and e == 1:
            return 0.45
        return 0.12
    return 0.5


def call_mock(
    model: str,
    effort: str,
    prompt: str,
    max_tokens: int,
    quadrant: str,
    task_id: str,
    trial: int = 0,
) -> tuple[Call, bool]:
    """Returns (Call, forced_pass). In mock mode we decide pass/fail here and
    hand a synthetic pass/fail straight to the runner (the verifier is bypassed
    because there's no real generation to check). `trial` varies the draw so
    repeated runs of the same cell estimate a reliability, not a coin flip."""
    tier = MODELS[model]
    prob = _pass_probability(quadrant, tier, effort)
    passed = _stable_unit(task_id, model, effort, str(trial)) < prob

    # Synthetic-but-plausible token usage: prompt in, answer + thinking out.
    in_tokens = 40 + len(prompt) // 4
    out_tokens = 120 + EFFORT_BUDGETS[effort]  # effort costs output tokens
    latency = 0.4 + EFFORT_BUDGETS[effort] / 4000 + tier * 0.15
    return Call("<<mock>>", in_tokens, out_tokens, latency), passed
