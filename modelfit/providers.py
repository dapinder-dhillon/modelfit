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
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

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
# The rows used by vendors.VENDORS were copied from each vendor's model docs on
# 2026-09-25 so the advise chart compares vendors on the same footing; the
# others are older and unchecked. Prices change -- the method is what lasts.
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-fable-5": (10.0, 50.0),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6-sol": (2.0, 10.0),
    "gpt-6-astra": (10.0, 50.0),
}


@dataclass
class Call:
    text: str
    in_tokens: int
    out_tokens: int
    latency_s: float
    cost_usd: float | None = None  # set only by call_cli, when the CLI reports it
    error: str | None = None  # set only by call_cli, when the process itself failed


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
# CLI mode: route a task through an already-authenticated agent CLI instead of
# the SDK. Auth then lives wherever that CLI already logged in -- nothing is
# stored by modelfit. This is the one place command templates live; fix them
# here when a CLI's flags change.
#
# Verified against the actual CLIs rather than assumed -- flags and output
# shapes drift between releases, so re-check these before trusting them blindly:
#   claude -p --output-format json  -> single JSON object: result, is_error,
#     total_cost_usd, usage.{input_tokens,output_tokens}. --model takes a full
#     model name. --effort accepts low|medium|high|xhigh|max -- there is NO
#     off/none level, so modelfit's "off" can't be pinned on this CLI.
#   codex exec --json               -> JSONL event stream; turn.failed/error
#     events carry a "message" on failure (confirmed against a live failure).
#     The success-path event shape (item.completed / turn.completed with a
#     usage block) matches Codex's documented protocol but has not been
#     exercised end-to-end against a live success response, so the usage
#     parse below degrades to "unknown" rather than assume a field name.
#     -c model_reasoning_effort=<level> accepts none|minimal|low|medium|high|xhigh
#     (per this CLI's own config validation error) -- "none" is a genuine
#     off-equivalent, unlike claude's --effort.
# --------------------------------------------------------------------------- #

AGENTS: dict[str, list[str]] = {
    "claude": [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--tools",
        "",  # disable all tools: a benchmark call is one completion, not an agent turn
    ],
    "codex": [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ask-for-approval",
        "never",
    ],
}

# effort dial (off/low/high) -> the flag value this agent actually accepts. A
# missing entry means that value cannot be pinned on that agent; call_cli then
# skips the flag rather than pass something the CLI would silently ignore, and
# reports the effort actually used as "n/a".
_EFFORT_FLAGS: dict[str, dict[str, str]] = {
    "claude": {"low": "low", "high": "high"},
    "codex": {"off": "none", "low": "low", "high": "high"},
}

CLI_TIMEOUT_S = 300.0


def _parse_claude_output(stdout: str, stderr: str, returncode: int, latency: float) -> Call:
    data: dict[str, Any] = {}
    if stdout.strip():
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            pass

    usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
    in_tokens = int(usage.get("input_tokens", 0) or 0)
    out_tokens = int(usage.get("output_tokens", 0) or 0)
    cost = data.get("total_cost_usd")
    cost_val = float(cost) if isinstance(cost, int | float) else None

    failed = returncode != 0 or bool(data.get("is_error"))
    if failed:
        tail = [line for line in (stderr or "").strip().splitlines() if line]
        error = tail[-1] if tail else f"claude exited {returncode}"
        return Call("", in_tokens, out_tokens, latency, cost_val, error)

    text = str(data.get("result", ""))
    return Call(text, in_tokens, out_tokens, latency, cost_val, None)


def _parse_codex_output(stdout: str, stderr: str, returncode: int, latency: float) -> Call:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue  # codex prints the odd plain-text status line to stdout too
        if isinstance(evt, dict):
            events.append(evt)

    error_msg = next(
        (e.get("message") for e in events if e.get("type") in ("error", "turn.failed")), None
    )
    failed = returncode != 0 or error_msg is not None
    if failed:
        tail = [line for line in (stderr or "").strip().splitlines() if line]
        fallback = tail[-1] if tail else f"codex exited {returncode}"
        error = str(error_msg) if error_msg else fallback
        return Call("", 0, 0, latency, None, error)

    text = ""
    for evt in events:
        if evt.get("type") == "item.completed":
            item = evt.get("item", {})
            item_type = item.get("type") if isinstance(item, dict) else None
            if item_type in ("agent_message", "assistant_message"):
                text = str(item.get("text", text))

    in_tokens = out_tokens = 0
    cost_val: float | None = None
    for evt in events:
        usage = evt.get("usage")
        if isinstance(usage, dict):
            in_tokens = int(usage.get("input_tokens", in_tokens) or in_tokens)
            out_tokens = int(usage.get("output_tokens", out_tokens) or out_tokens)
            cost = usage.get("cost_usd")
            if isinstance(cost, int | float):
                cost_val = float(cost)

    return Call(text, in_tokens, out_tokens, latency, cost_val, None)


def call_cli(
    agent: str,
    model: str,
    effort: str,
    prompt: str,
    max_tokens: int,
    timeout_s: float = CLI_TIMEOUT_S,
) -> tuple[Call, str]:
    """Run one task through an already-authenticated agent CLI (`claude -p` or
    `codex exec`), captured as a single completion. No API key is read or stored
    here -- auth lives wherever that CLI already logged in.

    Returns (Call, effective_effort). effective_effort is the value actually
    pinned on the CLI, or "n/a" when this agent has no way to control the
    requested level -- never a guess dressed up as a number.

    `max_tokens` is accepted for parity with call_real, but neither CLI exposes
    a token cap, so it is not enforced here.
    """
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; choose from {list(AGENTS)}")

    binary = AGENTS[agent][0]
    if shutil.which(binary) is None:
        raise RuntimeError(
            f"`{binary}` CLI not found — install it and log in, or use --real/--mock."
        )

    flag_value = _EFFORT_FLAGS.get(agent, {}).get(effort)
    # Keep modelfit's own off/low/high vocabulary in the report when we did
    # control it; the CLI's own flag spelling (e.g. codex's "none") is purely
    # an implementation detail of building argv, below.
    effective_effort = effort if flag_value is not None else "n/a"

    argv = list(AGENTS[agent])
    if agent == "claude":
        argv += ["--model", model]
        if flag_value is not None:
            argv += ["--effort", flag_value]
        argv += [prompt]
    else:  # codex
        argv += ["-m", model]
        if flag_value is not None:
            argv += ["-c", f"model_reasoning_effort={flag_value}"]
        argv += [prompt]

    t0 = time.time()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            stdin=subprocess.DEVNULL,
        )
        stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:

        def _decode(chunk: bytes | str | None) -> str:
            return chunk.decode() if isinstance(chunk, bytes) else (chunk or "")

        stdout = _decode(e.stdout)
        stderr = f"{_decode(e.stderr)}\n[timed out after {timeout_s:.0f}s]"
        returncode = -1
    latency = time.time() - t0

    if agent == "claude":
        call = _parse_claude_output(stdout, stderr, returncode, latency)
    else:
        call = _parse_codex_output(stdout, stderr, returncode, latency)

    # Honest fallback: if the CLI gave us token counts but no direct dollar
    # figure, estimate cost the same way --mock/--real do, PROVIDED we have a
    # placeholder price for this model. A model outside our PRICING table (e.g.
    # an older GPT id run via codex) has no knowable cost here -- leave it None
    # rather than guess or crash on a missing PRICING entry.
    if (
        call.error is None
        and call.cost_usd is None
        and (call.in_tokens or call.out_tokens)
        and model in PRICING
    ):
        call = Call(
            call.text,
            call.in_tokens,
            call.out_tokens,
            call.latency_s,
            cost_usd(model, call.in_tokens, call.out_tokens),
            None,
        )

    return call, effective_effort


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
