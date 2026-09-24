"""
Deterministic verifiers. This is the heart of the whole idea: a run only counts
as "solved" if a machine can prove it, with no model-graded fuzziness.

Each verifier returns (passed: bool, detail: str).

NOTE ON SAFETY: verify_python_callable executes model-generated code. Here it runs
in a subprocess with a timeout, which is enough for a local experiment on models
YOU chose. For anything untrusted or CI, isolate properly (container / nsjail /
seccomp). Deterministic-first also means: don't trust generated code blindly.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

_FENCE = re.compile(r"```(?:[a-zA-Z0-9]+)?\s*(.*?)```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Pull the first fenced block if present, else return the text as-is."""
    m = _FENCE.search(text or "")
    return (m.group(1) if m else (text or "")).strip()


def _first_json(text: str) -> Any:
    """Best-effort: extract and parse the first JSON value in the text."""
    body = _strip_fences(text)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = body.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(body)):
            if body[i] == opener:
                depth += 1
            elif body[i] == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(body[start : i + 1])
    return json.loads(body)  # let it raise if truly not JSON


def verify_json_equals(output: str, fixture: dict) -> tuple[bool, str]:
    try:
        got = _first_json(output)
    except Exception as e:  # noqa: BLE001
        return False, f"not valid JSON: {e}"
    ok = got == fixture["expected"]
    return ok, "match" if ok else f"got {got!r}"


def verify_finding_set(output: str, fixture: dict) -> tuple[bool, str]:
    try:
        got = set(_first_json(output))
    except Exception as e:  # noqa: BLE001
        return False, f"not a JSON array: {e}"
    vocab = set(fixture["vocab"])
    required = set(fixture["required"])
    got &= vocab  # ignore anything outside the allowed vocabulary
    missing = required - got
    ok = not missing
    return ok, "all required findings present" if ok else f"missed {sorted(missing)}"


def verify_python_callable(output: str, fixture: dict) -> tuple[bool, str]:
    code = _strip_fences(output)
    tests = "\n".join(fixture["tests"])
    harness = textwrap.dedent(code) + "\n\n" + tests + "\nprint('__PASS__')\n"

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "candidate.py"
        f.write_text(harness)
        try:
            proc = subprocess.run(
                [sys.executable, str(f)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            return False, "timed out"
    if proc.returncode == 0 and "__PASS__" in proc.stdout:
        return True, "tests passed"
    err = (proc.stderr or proc.stdout or "").strip().splitlines()
    return False, err[-1] if err else "tests failed"


REGISTRY = {
    "verify_json_equals": verify_json_equals,
    "verify_finding_set": verify_finding_set,
    "verify_python_callable": verify_python_callable,
}


def verify(name: str, output: str, fixture: dict) -> tuple[bool, str]:
    return REGISTRY[name](output, fixture)
