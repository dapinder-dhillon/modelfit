from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

MODELS: dict[str, int] = {
    "claude-haiku-4-5": 1,
    "claude-sonnet-5": 2,
    "claude-opus-4-8": 3,
    "claude-fable-5": 4,
}

THINKING_DISABLED_BUDGET = 0
EFFORT_BUDGETS: dict[str, int] = {
    "off": THINKING_DISABLED_BUDGET,
    "low": 2000,
    "high": 10000,
}

# PLACEHOLDER $ per million tokens (in, out): confirm before trusting any $ figure; prices change.
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

TOKENS_PER_MILLION = 1e6
THINKING_HEADROOM_TOKENS = 512
ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE = "ANTHROPIC_API_KEY"

CLAUDE_AGENT = "claude"
CODEX_AGENT = "codex"
DISABLE_ALL_TOOLS = ""
UNCONTROLLED_EFFORT = "n/a"
TIMEOUT_RETURN_CODE = -1
CLI_TIMEOUT_S = 300.0

# flags verified by hand against the real claude and codex CLIs; re-check when a CLI updates.
AGENTS: dict[str, list[str]] = {
    CLAUDE_AGENT: [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--tools",
        DISABLE_ALL_TOOLS,
    ],
    CODEX_AGENT: [
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

# claude -p --effort has no off/none level, so "off" can't be pinned there; codex accepts none.
_EFFORT_FLAGS: dict[str, dict[str, str]] = {
    CLAUDE_AGENT: {"low": "low", "high": "high"},
    CODEX_AGENT: {"off": "none", "low": "low", "high": "high"},
}

CODEX_ERROR_EVENT_TYPES = ("error", "turn.failed")
CODEX_ITEM_COMPLETED_EVENT_TYPE = "item.completed"
CODEX_AGENT_MESSAGE_ITEM_TYPES = ("agent_message", "assistant_message")

MOCK_TEXT = "<<mock>>"
MOCK_PROMPT_OVERHEAD_TOKENS = 40
CHARACTERS_PER_TOKEN = 4
MOCK_ANSWER_TOKENS = 120
MOCK_BASE_LATENCY_SECONDS = 0.4
MOCK_THINKING_TOKENS_PER_SECOND = 4000
MOCK_LATENCY_PER_TIER_SECONDS = 0.15
HASH_PART_SEPARATOR = "::"
HASH_PREFIX_LENGTH = 8
HEXADECIMAL_BASE = 16
MAX_HASH_PREFIX_VALUE = 0xFFFFFFFF

_EFFORT_ORD = {"off": 0, "low": 1, "high": 2}
NEITHER_PASS_PROBABILITY = 0.99
MAX_PASS_PROBABILITY = 0.98
UNKNOWN_QUADRANT_PASS_PROBABILITY = 0.5
EFFORT_QUADRANT_BASE_BY_EFFORT_RANK = {0: 0.15, 1: 0.60, 2: 0.92}
EFFORT_QUADRANT_BONUS_PER_TIER = 0.03
MODEL_QUADRANT_BASE_BY_TIER = {1: 0.15, 2: 0.50, 3: 0.85, 4: 0.95}
MODEL_QUADRANT_BONUS_PER_EFFORT_RANK = 0.04
BOTH_QUADRANT_STRONG_TIER = 3
HIGH_EFFORT_RANK = 2
LOW_EFFORT_RANK = 1
BOTH_QUADRANT_STRONG_HIGH_PASS_PROBABILITY = 0.90
BOTH_QUADRANT_STRONG_LOW_PASS_PROBABILITY = 0.45
BOTH_QUADRANT_OTHERWISE_PASS_PROBABILITY = 0.12


@dataclass
class Call:
    text: str
    in_tokens: int
    out_tokens: int
    latency_s: float
    cost_usd: float | None = None
    error: str | None = None


def cost_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    input_price, output_price = PRICING[model]
    return (
        in_tokens / TOKENS_PER_MILLION * input_price
        + out_tokens / TOKENS_PER_MILLION * output_price
    )


def call_real(model: str, effort: str, prompt: str, max_tokens: int) -> Call:
    import anthropic

    client = anthropic.Anthropic(api_key=_anthropic_api_key())
    request_arguments = _real_request_arguments(
        model=model, effort=effort, prompt=prompt, max_tokens=max_tokens
    )
    started_at = time.time()
    response = client.messages.create(**request_arguments)
    latency = time.time() - started_at
    text = "".join(
        content_block.text
        for content_block in response.content
        if getattr(content_block, "type", None) == "text"
    )
    return Call(
        text=text,
        in_tokens=response.usage.input_tokens,
        out_tokens=response.usage.output_tokens,
        latency_s=latency,
    )


# neither CLI exposes a token cap, so max_tokens is accepted for parity but not enforced.
def call_cli(
    agent: str,
    model: str,
    effort: str,
    prompt: str,
    max_tokens: int,
    timeout_s: float = CLI_TIMEOUT_S,
) -> tuple[Call, str]:
    _validate_agent(agent=agent)
    _validate_agent_installed(agent=agent)
    flag_value = _EFFORT_FLAGS.get(agent, dict()).get(effort)
    argv = _cli_argv(agent=agent, model=model, flag_value=flag_value, prompt=prompt)
    stdout, stderr, returncode, latency = _run_cli(argv=argv, timeout_s=timeout_s)
    call = _parse_cli_output(
        agent=agent, stdout=stdout, stderr=stderr, returncode=returncode, latency=latency
    )
    call = _with_placeholder_cost_if_only_tokens_reported(call=call, model=model)
    return call, _effective_effort(effort=effort, flag_value=flag_value)


def call_mock(
    model: str,
    effort: str,
    prompt: str,
    max_tokens: int,
    quadrant: str,
    task_id: str,
    trial: int = 0,
) -> tuple[Call, bool]:
    tier = MODELS[model]
    pass_probability = _pass_probability(quadrant=quadrant, tier=tier, effort=effort)
    passed = _stable_unit(task_id, model, effort, str(trial)) < pass_probability
    in_tokens = MOCK_PROMPT_OVERHEAD_TOKENS + len(prompt) // CHARACTERS_PER_TOKEN
    out_tokens = MOCK_ANSWER_TOKENS + EFFORT_BUDGETS[effort]
    latency = (
        MOCK_BASE_LATENCY_SECONDS
        + EFFORT_BUDGETS[effort] / MOCK_THINKING_TOKENS_PER_SECOND
        + tier * MOCK_LATENCY_PER_TIER_SECONDS
    )
    call = Call(text=MOCK_TEXT, in_tokens=in_tokens, out_tokens=out_tokens, latency_s=latency)
    return call, passed


def _anthropic_api_key() -> str:
    api_key = os.environ.get(ANTHROPIC_API_KEY_ENVIRONMENT_VARIABLE)
    if api_key is None or len(api_key) == 0:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Export it before running with --real.")
    return api_key


def _real_request_arguments(model: str, effort: str, prompt: str, max_tokens: int) -> dict:
    budget = EFFORT_BUDGETS[effort]
    request_arguments: dict = {
        "model": model,
        "max_tokens": max(max_tokens, budget + THINKING_HEADROOM_TOKENS),
        "messages": [{"role": "user", "content": prompt}],
    }
    if budget != THINKING_DISABLED_BUDGET:
        request_arguments["thinking"] = {"type": "enabled", "budget_tokens": budget}
    return request_arguments


def _validate_agent(agent: str) -> None:
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; choose from {list(AGENTS)}")


def _validate_agent_installed(agent: str) -> None:
    binary = AGENTS[agent][0]
    if shutil.which(binary) is None:
        raise RuntimeError(
            f"`{binary}` CLI not found — install it and log in, or use --real/--mock."
        )


def _effective_effort(effort: str, flag_value: str | None) -> str:
    if flag_value is not None:
        return effort
    else:
        return UNCONTROLLED_EFFORT


def _cli_argv(agent: str, model: str, flag_value: str | None, prompt: str) -> list[str]:
    if agent == CLAUDE_AGENT:
        return _claude_argv(model=model, flag_value=flag_value, prompt=prompt)
    else:
        return _codex_argv(model=model, flag_value=flag_value, prompt=prompt)


def _claude_argv(model: str, flag_value: str | None, prompt: str) -> list[str]:
    argv = list(AGENTS[CLAUDE_AGENT])
    argv += ["--model", model]
    if flag_value is not None:
        argv += ["--effort", flag_value]
    argv += [prompt]
    return argv


def _codex_argv(model: str, flag_value: str | None, prompt: str) -> list[str]:
    argv = list(AGENTS[CODEX_AGENT])
    argv += ["-m", model]
    if flag_value is not None:
        argv += ["-c", f"model_reasoning_effort={flag_value}"]
    argv += [prompt]
    return argv


def _run_cli(argv: list[str], timeout_s: float) -> tuple[str, str, int, float]:
    started_at = time.time()
    try:
        completed_process = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            stdin=subprocess.DEVNULL,
        )
        stdout = completed_process.stdout
        stderr = completed_process.stderr
        returncode = completed_process.returncode
    except subprocess.TimeoutExpired as timeout_error:
        stdout = _decode_timeout_output(chunk=timeout_error.stdout)
        stderr = (
            f"{_decode_timeout_output(chunk=timeout_error.stderr)}\n"
            f"[timed out after {timeout_s:.0f}s]"
        )
        returncode = TIMEOUT_RETURN_CODE
    latency = time.time() - started_at
    return stdout, stderr, returncode, latency


def _decode_timeout_output(chunk: bytes | str | None) -> str:
    if isinstance(chunk, bytes):
        return chunk.decode()
    if chunk is None:
        return ""
    return chunk


def _parse_cli_output(
    agent: str, stdout: str, stderr: str, returncode: int, latency: float
) -> Call:
    if agent == CLAUDE_AGENT:
        return _parse_claude_output(
            stdout=stdout, stderr=stderr, returncode=returncode, latency=latency
        )
    else:
        return _parse_codex_output(
            stdout=stdout, stderr=stderr, returncode=returncode, latency=latency
        )


def _with_placeholder_cost_if_only_tokens_reported(call: Call, model: str) -> Call:
    if _can_estimate_cost_from_tokens(call=call, model=model) is False:
        return call
    return Call(
        text=call.text,
        in_tokens=call.in_tokens,
        out_tokens=call.out_tokens,
        latency_s=call.latency_s,
        cost_usd=cost_usd(model=model, in_tokens=call.in_tokens, out_tokens=call.out_tokens),
        error=None,
    )


def _can_estimate_cost_from_tokens(call: Call, model: str) -> bool:
    if call.error is not None or call.cost_usd is not None:
        return False
    if call.in_tokens == 0 and call.out_tokens == 0:
        return False
    if model not in PRICING:
        return False
    return True


def _parse_claude_output(stdout: str, stderr: str, returncode: int, latency: float) -> Call:
    payload = _claude_payload(stdout=stdout)
    usage = _claude_usage(payload=payload)
    in_tokens = _token_count(usage=usage, key="input_tokens", default=0)
    out_tokens = _token_count(usage=usage, key="output_tokens", default=0)
    reported_cost = _reported_cost(cost=payload.get("total_cost_usd"))
    if _claude_failed(payload=payload, returncode=returncode) is True:
        error = _last_stderr_line(stderr=stderr, fallback=f"claude exited {returncode}")
        return Call(
            text="",
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            latency_s=latency,
            cost_usd=reported_cost,
            error=error,
        )
    return Call(
        text=str(payload.get("result", "")),
        in_tokens=in_tokens,
        out_tokens=out_tokens,
        latency_s=latency,
        cost_usd=reported_cost,
        error=None,
    )


def _claude_payload(stdout: str) -> dict[str, Any]:
    if len(stdout.strip()) == 0:
        return dict()
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return dict()
    if isinstance(parsed, dict):
        return parsed
    return dict()


def _claude_usage(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage")
    if isinstance(usage, dict):
        return usage
    return dict()


def _claude_failed(payload: dict[str, Any], returncode: int) -> bool:
    if returncode != 0:
        return True
    if bool(payload.get("is_error")) is True:
        return True
    return False


def _parse_codex_output(stdout: str, stderr: str, returncode: int, latency: float) -> Call:
    events = _codex_events(stdout=stdout)
    error_message = _codex_error_message(events=events)
    if returncode != 0 or error_message is not None:
        fallback = _last_stderr_line(stderr=stderr, fallback=f"codex exited {returncode}")
        return Call(
            text="",
            in_tokens=0,
            out_tokens=0,
            latency_s=latency,
            cost_usd=None,
            error=_codex_error_text(error_message=error_message, fallback=fallback),
        )
    text = _codex_text(events=events)
    in_tokens, out_tokens, reported_cost = _codex_usage(events=events)
    return Call(
        text=text,
        in_tokens=in_tokens,
        out_tokens=out_tokens,
        latency_s=latency,
        cost_usd=reported_cost,
        error=None,
    )


def _codex_events(stdout: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        event = _json_event_or_none(line=line.strip())
        if event is not None:
            events.append(event)
    return events


def _json_event_or_none(line: str) -> dict[str, Any] | None:
    if len(line) == 0:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(event, dict):
        return event
    return None


def _codex_error_message(events: list[dict[str, Any]]) -> Any:
    for event in events:
        if event.get("type") in CODEX_ERROR_EVENT_TYPES:
            return event.get("message")
    return None


def _codex_error_text(error_message: Any, fallback: str) -> str:
    if bool(error_message) is True:
        return str(error_message)
    return fallback


def _codex_text(events: list[dict[str, Any]]) -> str:
    text = ""
    for event in events:
        if event.get("type") == CODEX_ITEM_COMPLETED_EVENT_TYPE:
            item = event.get("item", dict())
            if _item_type(item=item) in CODEX_AGENT_MESSAGE_ITEM_TYPES:
                text = str(item.get("text", text))
    return text


def _item_type(item: Any) -> Any:
    if isinstance(item, dict):
        return item.get("type")
    return None


# codex's success-path usage event is documented but not verified live; the parse degrades.
def _codex_usage(events: list[dict[str, Any]]) -> tuple[int, int, float | None]:
    in_tokens = 0
    out_tokens = 0
    reported_cost: float | None = None
    for event in events:
        usage = event.get("usage")
        if isinstance(usage, dict):
            in_tokens = _token_count(usage=usage, key="input_tokens", default=in_tokens)
            out_tokens = _token_count(usage=usage, key="output_tokens", default=out_tokens)
            cost = _reported_cost(cost=usage.get("cost_usd"))
            if cost is not None:
                reported_cost = cost
    return in_tokens, out_tokens, reported_cost


def _token_count(usage: dict[str, Any], key: str, default: int) -> int:
    token_count = usage.get(key, default)
    if bool(token_count) is False:
        return default
    return int(token_count)


def _reported_cost(cost: Any) -> float | None:
    if isinstance(cost, int | float):
        return float(cost)
    return None


def _last_stderr_line(stderr: str | None, fallback: str) -> str:
    if stderr is None:
        return fallback
    non_empty_lines = [line for line in stderr.strip().splitlines() if len(line) > 0]
    if len(non_empty_lines) > 0:
        return non_empty_lines[-1]
    return fallback


def _stable_unit(*parts: str) -> float:
    digest = hashlib.sha256(HASH_PART_SEPARATOR.join(parts).encode()).hexdigest()
    return int(digest[:HASH_PREFIX_LENGTH], HEXADECIMAL_BASE) / MAX_HASH_PREFIX_VALUE


def _pass_probability(quadrant: str, tier: int, effort: str) -> float:
    effort_rank = _EFFORT_ORD[effort]
    if quadrant == "NEITHER":
        return NEITHER_PASS_PROBABILITY
    if quadrant == "EFFORT":
        return _effort_quadrant_pass_probability(tier=tier, effort_rank=effort_rank)
    if quadrant == "MODEL":
        return _model_quadrant_pass_probability(tier=tier, effort_rank=effort_rank)
    if quadrant == "BOTH":
        return _both_quadrant_pass_probability(tier=tier, effort_rank=effort_rank)
    return UNKNOWN_QUADRANT_PASS_PROBABILITY


def _effort_quadrant_pass_probability(tier: int, effort_rank: int) -> float:
    base = EFFORT_QUADRANT_BASE_BY_EFFORT_RANK[effort_rank]
    return min(MAX_PASS_PROBABILITY, base + EFFORT_QUADRANT_BONUS_PER_TIER * (tier - 1))


def _model_quadrant_pass_probability(tier: int, effort_rank: int) -> float:
    base = MODEL_QUADRANT_BASE_BY_TIER[tier]
    return min(MAX_PASS_PROBABILITY, base + MODEL_QUADRANT_BONUS_PER_EFFORT_RANK * effort_rank)


def _both_quadrant_pass_probability(tier: int, effort_rank: int) -> float:
    if tier >= BOTH_QUADRANT_STRONG_TIER and effort_rank == HIGH_EFFORT_RANK:
        return BOTH_QUADRANT_STRONG_HIGH_PASS_PROBABILITY
    if tier >= BOTH_QUADRANT_STRONG_TIER and effort_rank == LOW_EFFORT_RANK:
        return BOTH_QUADRANT_STRONG_LOW_PASS_PROBABILITY
    return BOTH_QUADRANT_OTHERWISE_PASS_PROBABILITY
