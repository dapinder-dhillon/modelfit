"""verifiers.py is the trust anchor of the whole tool: tested hardest."""

from __future__ import annotations

from modelfit import verifiers


class TestVerifyJsonEquals:
    def test_exact_match(self):
        ok, detail = verifiers.verify_json_equals('{"a": 1}', {"expected": {"a": 1}})
        assert ok
        assert detail == "match"

    def test_wrong_value(self):
        ok, detail = verifiers.verify_json_equals('{"a": 2}', {"expected": {"a": 1}})
        assert not ok
        assert "got" in detail

    def test_malformed_json(self):
        ok, detail = verifiers.verify_json_equals("not json at all", {"expected": {"a": 1}})
        assert not ok
        assert "not valid JSON" in detail

    def test_json_inside_fenced_block(self):
        text = '```json\n{"a": 1}\n```'
        ok, _ = verifiers.verify_json_equals(text, {"expected": {"a": 1}})
        assert ok

    def test_json_with_leading_prose(self):
        text = 'Sure, here is the JSON:\n{"a": 1}'
        ok, _ = verifiers.verify_json_equals(text, {"expected": {"a": 1}})
        assert ok


class TestVerifyFindingSet:
    FIXTURE = {
        "required": ["ADMIN_WILDCARD", "RESOURCE_STAR"],
        "vocab": ["ADMIN_WILDCARD", "RESOURCE_STAR", "PASSROLE_WILDCARD"],
    }

    def test_all_required_present(self):
        ok, detail = verifiers.verify_finding_set(
            '["ADMIN_WILDCARD", "RESOURCE_STAR"]', self.FIXTURE
        )
        assert ok
        assert "all required" in detail

    def test_missing_one(self):
        ok, detail = verifiers.verify_finding_set('["ADMIN_WILDCARD"]', self.FIXTURE)
        assert not ok
        assert "RESOURCE_STAR" in detail

    def test_extra_items_outside_vocab_ignored(self):
        text = '["ADMIN_WILDCARD", "RESOURCE_STAR", "NOT_IN_VOCAB"]'
        ok, _ = verifiers.verify_finding_set(text, self.FIXTURE)
        assert ok

    def test_malformed_array(self):
        ok, detail = verifiers.verify_finding_set("nope", self.FIXTURE)
        assert not ok
        assert "not a JSON array" in detail


class TestVerifyPythonCallable:
    def test_passing_code(self):
        code = "def add(a, b):\n    return a + b\n"
        fixture = {"callable": "add", "tests": ["assert add(1, 2) == 3"]}
        ok, detail = verifiers.verify_python_callable(code, fixture)
        assert ok
        assert detail == "tests passed"

    def test_failing_assertion(self):
        code = "def add(a, b):\n    return a - b\n"
        fixture = {"callable": "add", "tests": ["assert add(1, 2) == 3"]}
        ok, _ = verifiers.verify_python_callable(code, fixture)
        assert not ok

    def test_syntax_error(self):
        code = "def add(a, b)\n    return a + b\n"
        fixture = {"callable": "add", "tests": ["assert add(1, 2) == 3"]}
        ok, _ = verifiers.verify_python_callable(code, fixture)
        assert not ok

    def test_timeout_on_infinite_loop(self):
        code = "def add(a, b):\n    while True:\n        pass\n"
        fixture = {"callable": "add", "tests": ["assert add(1, 2) == 3"]}
        ok, detail = verifiers.verify_python_callable(code, fixture)
        assert not ok
        assert detail == "timed out"

    def test_code_wrapped_in_fences(self):
        code = "```python\ndef add(a, b):\n    return a + b\n```"
        fixture = {"callable": "add", "tests": ["assert add(1, 2) == 3"]}
        ok, _ = verifiers.verify_python_callable(code, fixture)
        assert ok


def test_registry_dispatch():
    ok, _ = verifiers.verify("verify_json_equals", '{"a": 1}', {"expected": {"a": 1}})
    assert ok
