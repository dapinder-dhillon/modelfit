"""
Task set.

Each task is deliberately placed in one of four quadrants so the REPORT makes
the thesis visible in data:

    NEITHER : recall / boilerplate   -> cheap model, low effort wins on cost
    EFFORT  : self-contained logic   -> effort matters, model barely does
    MODEL   : breadth / judgement    -> model matters, effort barely does
    BOTH    : long multi-step change -> only big model + high effort is reliable

The tasks below are small on purpose. The intended use is to DELETE them and
drop in real tasks from your backlog, keeping the deterministic-verifier shape.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    quadrant: str  # NEITHER | EFFORT | MODEL | BOTH
    prompt: str  # what the model is asked to do
    verifier: str  # name of a function in verifiers.py
    fixture: dict[str, Any] = field(default_factory=dict)  # ground truth for the verifier
    max_tokens: int = 1500


# --- NEITHER: pure recall / format. Any decent model nails this. ---------------
T_TFVARS = Task(
    id="tfvars_to_json",
    quadrant="NEITHER",
    prompt=(
        "Convert these Terraform variable defaults into a single JSON object "
        "(the .tfvars.json equivalent). Return ONLY the JSON, no prose.\n\n"
        'region      = "eu-west-2"\n'
        "instance_count = 3\n"
        "enable_logging = true\n"
        'tags = { team = "platform", env = "prod" }\n'
    ),
    verifier="verify_json_equals",
    fixture={
        "expected": {
            "region": "eu-west-2",
            "instance_count": 3,
            "enable_logging": True,
            "tags": {"team": "platform", "env": "prod"},
        }
    },
)

# --- EFFORT: a self-contained logic bug. Needs working-out, not knowledge. ------
T_BACKOFF = Task(
    id="backoff_delays",
    quadrant="EFFORT",
    prompt=(
        "Implement a Python function `backoff_delays(attempts)` returning the list "
        "of sleep durations (seconds) BETWEEN attempts for exponential backoff "
        "starting at 1s and doubling. There is a sleep after every failed attempt "
        "EXCEPT the last (you don't wait after giving up). "
        "So backoff_delays(1) == [], backoff_delays(2) == [1], "
        "backoff_delays(4) == [1, 2, 4]. Return ONLY the function."
    ),
    verifier="verify_python_callable",
    fixture={
        "callable": "backoff_delays",
        "tests": [
            "assert backoff_delays(1) == []",
            "assert backoff_delays(2) == [1]",
            "assert backoff_delays(3) == [1, 2]",
            "assert backoff_delays(4) == [1, 2, 4]",
            "assert backoff_delays(5) == [1, 2, 4, 8]",
        ],
    },
)

T_SEMVER = Task(
    id="semver_compare",
    quadrant="EFFORT",
    prompt=(
        "Implement `semver_gt(a, b)` returning True if semantic version string a is "
        "strictly greater than b. Handle major.minor.patch numerically (so '1.10.0' "
        "> '1.9.0'). A version WITHOUT a pre-release ('1.0.0') is greater than the "
        "same version WITH one ('1.0.0-rc1'). Ignore build metadata after '+'. "
        "Return ONLY the function."
    ),
    verifier="verify_python_callable",
    fixture={
        "callable": "semver_gt",
        "tests": [
            "assert semver_gt('1.10.0', '1.9.0') is True",
            "assert semver_gt('1.0.0', '1.0.0-rc1') is True",
            "assert semver_gt('1.0.0-rc1', '1.0.0') is False",
            "assert semver_gt('2.0.0', '2.0.0') is False",
            "assert semver_gt('1.0.1+build9', '1.0.1') is False",
        ],
    },
)

# --- MODEL: breadth / judgement. Effort won't conjure knowledge it lacks. -------
T_IAM = Task(
    id="iam_findings",
    quadrant="MODEL",
    prompt=(
        "Review this IAM policy and return a JSON array of issue codes present, "
        "chosen ONLY from this exact set: "
        '["ADMIN_WILDCARD","RESOURCE_STAR","PRINCIPAL_STAR","PASSROLE_WILDCARD"]. '
        "Return ONLY the JSON array.\n\n"
        '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
        '"Principal":{"AWS":"*"},"Action":["iam:*","iam:PassRole"],'
        '"Resource":"*"}]}'
    ),
    verifier="verify_finding_set",
    fixture={
        # must catch all of these to pass
        "required": ["ADMIN_WILDCARD", "RESOURCE_STAR", "PRINCIPAL_STAR", "PASSROLE_WILDCARD"],
        "vocab": ["ADMIN_WILDCARD", "RESOURCE_STAR", "PRINCIPAL_STAR", "PASSROLE_WILDCARD"],
    },
)

# --- BOTH: multi-step change with several constraints at once. ------------------
T_REFACTOR = Task(
    id="idempotent_tagger",
    quadrant="BOTH",
    prompt=(
        "Rewrite `apply_tags(existing, new)` so that ALL of the following hold:\n"
        "1. It MERGES new tags into existing (does not replace the dict).\n"
        "2. It is idempotent: applying the same new tags twice == applying once.\n"
        "3. It NEVER mutates the caller's `existing` dict (returns a new dict).\n"
        "4. If a key exists in both, `new` wins.\n"
        "5. Keys are returned sorted.\n"
        "Return ONLY the function."
    ),
    verifier="verify_python_callable",
    fixture={
        "callable": "apply_tags",
        "tests": [
            "e = {'team': 'platform'}; out = apply_tags(e, {'env': 'prod'})",
            "assert out == {'env': 'prod', 'team': 'platform'}",
            "assert e == {'team': 'platform'}  # not mutated",
            "assert apply_tags(e, {'env':'prod'}) == "
            "apply_tags(apply_tags(e,{'env':'prod'}), {'env':'prod'})",
            "assert apply_tags({'a':'1'}, {'a':'2'}) == {'a':'2'}",
            "assert list(apply_tags({'z':'1'}, {'a':'2'}).keys()) == ['a','z']",
        ],
    },
)


ALL_TASKS: list[Task] = [T_TFVARS, T_BACKOFF, T_SEMVER, T_IAM, T_REFACTOR]

QUADRANTS = ["NEITHER", "EFFORT", "MODEL", "BOTH"]
