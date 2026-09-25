from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

CODE_FENCE_PATTERN = re.compile(r"```(?:[a-zA-Z0-9]+)?\s*(.*?)```", re.DOTALL)
JSON_BRACKET_PAIRS = (("{", "}"), ("[", "]"))
NOT_FOUND = -1
EXPECTED_KEY = "expected"
VOCABULARY_KEY = "vocab"
REQUIRED_KEY = "required"
TESTS_KEY = "tests"
PASS_MARKER = "__PASS__"
CANDIDATE_FILE_NAME = "candidate.py"
SANDBOX_TIMEOUT_SECONDS = 10


def verify_json_equals(output: str, fixture: dict) -> tuple[bool, str]:
    try:
        parsed_output = _first_json(text=output)
    except Exception as error:
        return False, f"not valid JSON: {error}"
    return _json_equals_result(parsed_output=parsed_output, expected=fixture[EXPECTED_KEY])


def verify_finding_set(output: str, fixture: dict) -> tuple[bool, str]:
    try:
        reported_findings = set(_first_json(text=output))
    except Exception as error:
        return False, f"not a JSON array: {error}"
    vocabulary = set(fixture[VOCABULARY_KEY])
    required_findings = set(fixture[REQUIRED_KEY])
    in_vocabulary_findings = reported_findings & vocabulary
    return _finding_set_result(missing_findings=required_findings - in_vocabulary_findings)


def verify_python_callable(output: str, fixture: dict) -> tuple[bool, str]:
    harness = _python_test_harness(code=_strip_fences(text=output), tests=fixture[TESTS_KEY])
    try:
        completed_process = _run_in_subprocess(harness=harness)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    return _python_callable_result(completed_process=completed_process)


REGISTRY = {
    "verify_json_equals": verify_json_equals,
    "verify_finding_set": verify_finding_set,
    "verify_python_callable": verify_python_callable,
}


def verify(name: str, output: str, fixture: dict) -> tuple[bool, str]:
    return REGISTRY[name](output, fixture)


def _json_equals_result(parsed_output: Any, expected: Any) -> tuple[bool, str]:
    if parsed_output == expected:
        return True, "match"
    return False, f"got {parsed_output!r}"


def _finding_set_result(missing_findings: set[Any]) -> tuple[bool, str]:
    if len(missing_findings) == 0:
        return True, "all required findings present"
    return False, f"missed {sorted(missing_findings)}"


def _python_test_harness(code: str, tests: list[str]) -> str:
    return textwrap.dedent(code) + "\n\n" + "\n".join(tests) + f"\nprint('{PASS_MARKER}')\n"


# runs model-generated code: subprocess + timeout, not a sandbox; isolate it for untrusted use.
def _run_in_subprocess(harness: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temporary_directory:
        candidate_file = Path(temporary_directory) / CANDIDATE_FILE_NAME
        candidate_file.write_text(harness)
        return subprocess.run(
            [sys.executable, str(candidate_file)],
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT_SECONDS,
        )


def _python_callable_result(
    completed_process: subprocess.CompletedProcess[str],
) -> tuple[bool, str]:
    if completed_process.returncode == 0 and PASS_MARKER in completed_process.stdout:
        return True, "tests passed"
    return False, _last_output_line(completed_process=completed_process)


def _last_output_line(completed_process: subprocess.CompletedProcess[str]) -> str:
    output_lines = _process_output(completed_process=completed_process).strip().splitlines()
    if len(output_lines) > 0:
        return output_lines[-1]
    return "tests failed"


def _process_output(completed_process: subprocess.CompletedProcess[str]) -> str:
    if completed_process.stderr is not None and len(completed_process.stderr) > 0:
        return completed_process.stderr
    if completed_process.stdout is not None and len(completed_process.stdout) > 0:
        return completed_process.stdout
    return ""


def _first_json(text: str) -> Any:
    body = _strip_fences(text=text)
    for opener, closer in JSON_BRACKET_PAIRS:
        balanced_block = _first_balanced_block(body=body, opener=opener, closer=closer)
        if balanced_block is not None:
            return json.loads(balanced_block)
    return json.loads(body)


def _first_balanced_block(body: str, opener: str, closer: str) -> str | None:
    start = body.find(opener)
    if start == NOT_FOUND:
        return None
    depth = 0
    for index in range(start, len(body)):
        if body[index] == opener:
            depth += 1
        elif body[index] == closer:
            depth -= 1
            if depth == 0:
                return body[start : index + 1]
    return None


def _strip_fences(text: str) -> str:
    safe_text = _text_or_empty(text=text)
    fence_match = CODE_FENCE_PATTERN.search(safe_text)
    if fence_match is not None:
        return fence_match.group(1).strip()
    return safe_text.strip()


def _text_or_empty(text: str | None) -> str:
    if text is None:
        return ""
    return text
