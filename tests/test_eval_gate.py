"""Tests for the evaluation gate module."""

import json
import tempfile
from pathlib import Path

import pytest

from src.eval.gate import EvalGate, EvalResult, GateReport


@pytest.fixture
def temp_eval_dir():
    """Create a temporary evaluation data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        eval_dir = Path(tmpdir)
        (eval_dir / "replay").mkdir()
        (eval_dir / "regression").mkdir()
        (eval_dir / "redteam").mkdir()
        yield eval_dir


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_skill(skill_dir: Path, code: str) -> Path:
    """Create a skill.py file with the given code."""
    skill_file = skill_dir / "skill.py"
    skill_file.write_text(code)
    return skill_dir


def create_case(eval_dir: Path, category: str, filename: str, case: dict) -> None:
    """Create a test case JSON file."""
    case_file = eval_dir / category / filename
    case_file.write_text(json.dumps(case))


class TestLoadCases:
    """Tests for EvalGate.load_cases method."""

    def test_load_cases_returns_filtered_cases(self, temp_eval_dir):
        """load_cases returns only cases matching the skill name."""
        create_case(
            temp_eval_dir,
            "replay",
            "test_001.json",
            {"id": "test_001", "skill": "text_echo", "input": {}},
        )
        create_case(
            temp_eval_dir,
            "replay",
            "test_002.json",
            {"id": "test_002", "skill": "other_skill", "input": {}},
        )
        create_case(
            temp_eval_dir,
            "replay",
            "test_003.json",
            {"id": "test_003", "skill": "text_echo", "input": {}},
        )

        gate = EvalGate(temp_eval_dir)
        cases = gate.load_cases("replay", "text_echo")

        assert len(cases) == 2
        assert all(c["skill"] == "text_echo" for c in cases)

    def test_load_cases_empty_for_nonexistent_category(self, temp_eval_dir):
        """load_cases returns empty list for nonexistent category."""
        gate = EvalGate(temp_eval_dir)
        cases = gate.load_cases("nonexistent", "text_echo")

        assert cases == []

    def test_load_cases_empty_for_no_matching_skill(self, temp_eval_dir):
        """load_cases returns empty list when no cases match skill."""
        create_case(
            temp_eval_dir,
            "replay",
            "test_001.json",
            {"id": "test_001", "skill": "other_skill", "input": {}},
        )

        gate = EvalGate(temp_eval_dir)
        cases = gate.load_cases("replay", "text_echo")

        assert cases == []

    def test_load_cases_ignores_hidden_files(self, temp_eval_dir):
        """load_cases ignores files starting with dot."""
        create_case(
            temp_eval_dir,
            "replay",
            ".gitkeep",
            {"id": "hidden", "skill": "text_echo", "input": {}},
        )
        create_case(
            temp_eval_dir,
            "replay",
            "test_001.json",
            {"id": "test_001", "skill": "text_echo", "input": {}},
        )

        gate = EvalGate(temp_eval_dir)
        cases = gate.load_cases("replay", "text_echo")

        assert len(cases) == 1
        assert cases[0]["id"] == "test_001"


class TestRunCase:
    """Tests for EvalGate.run_case method."""

    def test_run_case_exact_match_pass(self, temp_eval_dir, temp_skill_dir):
        """run_case passes when result exactly matches expected value."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    if format == "uppercase":
        return text.upper()
    return text
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "hello", "format": "uppercase"},
            "expected": {"type": "exact", "value": "HELLO"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is True
        assert result.actual_output == "HELLO"
        assert result.error is None

    def test_run_case_exact_match_fail(self, temp_eval_dir, temp_skill_dir):
        """run_case fails when result doesn't match expected value."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    return text.lower()
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "hello", "format": "uppercase"},
            "expected": {"type": "exact", "value": "HELLO"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is False
        assert result.actual_output == "hello"

    def test_run_case_contains_pass(self, temp_eval_dir, temp_skill_dir):
        """run_case passes when result contains expected substring."""
        create_skill(
            temp_skill_dir,
            """
def action(name):
    return f"Hello, {name}!"
""",
        )

        case = {
            "id": "test_001",
            "skill": "greeter",
            "input": {"name": "World"},
            "expected": {"type": "contains", "substring": "World"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is True

    def test_run_case_contains_fail(self, temp_eval_dir, temp_skill_dir):
        """run_case fails when result doesn't contain expected substring."""
        create_skill(
            temp_skill_dir,
            """
def action(name):
    return "Hello!"
""",
        )

        case = {
            "id": "test_001",
            "skill": "greeter",
            "input": {"name": "World"},
            "expected": {"type": "contains", "substring": "World"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is False

    def test_run_case_no_forbidden_patterns_pass(self, temp_eval_dir, temp_skill_dir):
        """run_case passes when result doesn't contain forbidden patterns."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    # Safe transformation that doesn't leak file contents
    return text.upper()
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "../../../etc/passwd", "format": "uppercase"},
            "expected": {
                "type": "no_forbidden_patterns",
                "forbidden": ["root:", "/etc/", "passwd"],
            },
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        # The output is "../../../ETC/PASSWD" which contains "passwd" (uppercase)
        # But "passwd" is lowercase in forbidden, so this should pass
        # Actually, "../../../ETC/PASSWD" does not contain "passwd" (case sensitive)
        assert result.passed is True

    def test_run_case_no_forbidden_patterns_fail(self, temp_eval_dir, temp_skill_dir):
        """run_case fails when result contains forbidden patterns."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    # Malicious skill that leaks file contents
    return "root:x:0:0:root:/root:/bin/bash"
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "../../../etc/passwd", "format": "uppercase"},
            "expected": {
                "type": "no_forbidden_patterns",
                "forbidden": ["root:", "/etc/"],
            },
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is False

    def test_run_case_timeout_or_error_pass_on_exception(
        self, temp_eval_dir, temp_skill_dir
    ):
        """run_case passes for timeout_or_error when skill raises exception."""
        create_skill(
            temp_skill_dir,
            """
def action(text):
    raise ValueError("Invalid input")
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "test"},
            "expected": {"type": "timeout_or_error", "max_duration_ms": 5000},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is True
        assert result.error is not None

    def test_run_case_skill_not_found(self, temp_eval_dir, temp_skill_dir):
        """run_case fails when skill file doesn't exist."""
        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "hello"},
            "expected": {"type": "exact", "value": "HELLO"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is False
        assert "not found" in result.error

    def test_run_case_no_action_function(self, temp_eval_dir, temp_skill_dir):
        """run_case fails when skill has no action() function."""
        create_skill(
            temp_skill_dir,
            """
def process(text):
    return text.upper()
""",
        )

        case = {
            "id": "test_001",
            "skill": "text_echo",
            "input": {"text": "hello"},
            "expected": {"type": "exact", "value": "HELLO"},
            "timeout_ms": 1000,
        }

        gate = EvalGate(temp_eval_dir)
        result = gate.run_case(case, temp_skill_dir)

        assert result.passed is False
        assert "action()" in result.error


class TestRunGate:
    """Tests for EvalGate.run_gate method."""

    def test_run_gate_all_pass(self, temp_eval_dir, temp_skill_dir):
        """run_gate passes when all cases pass and meets threshold."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    if format == "uppercase":
        return text.upper()
    elif format == "lowercase":
        return text.lower()
    return text
""",
        )

        create_case(
            temp_eval_dir,
            "replay",
            "test_001.json",
            {
                "id": "test_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )
        create_case(
            temp_eval_dir,
            "replay",
            "test_002.json",
            {
                "id": "test_002",
                "skill": "text_echo",
                "input": {"text": "WORLD", "format": "lowercase"},
                "expected": {"type": "exact", "value": "world"},
                "timeout_ms": 1000,
            },
        )

        gate = EvalGate(temp_eval_dir)
        report = gate.run_gate("replay", "text_echo", temp_skill_dir, threshold=1.0)

        assert report.gate_passed is True
        assert report.total == 2
        assert report.passed_count == 2
        assert report.failed_count == 0
        assert report.pass_rate == 1.0

    def test_run_gate_partial_fail(self, temp_eval_dir, temp_skill_dir):
        """run_gate fails when pass rate below threshold."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    return text.upper()  # Always uppercase, even for lowercase format
""",
        )

        create_case(
            temp_eval_dir,
            "replay",
            "test_001.json",
            {
                "id": "test_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )
        create_case(
            temp_eval_dir,
            "replay",
            "test_002.json",
            {
                "id": "test_002",
                "skill": "text_echo",
                "input": {"text": "WORLD", "format": "lowercase"},
                "expected": {"type": "exact", "value": "world"},
                "timeout_ms": 1000,
            },
        )

        gate = EvalGate(temp_eval_dir)
        report = gate.run_gate("replay", "text_echo", temp_skill_dir, threshold=1.0)

        assert report.gate_passed is False
        assert report.total == 2
        assert report.passed_count == 1
        assert report.failed_count == 1
        assert report.pass_rate == 0.5

    def test_run_gate_passes_with_lower_threshold(self, temp_eval_dir, temp_skill_dir):
        """run_gate passes when pass rate meets lower threshold."""
        create_skill(
            temp_skill_dir,
            """
def action(text, format):
    return text.upper()  # Always uppercase
""",
        )

        create_case(
            temp_eval_dir,
            "regression",
            "test_001.json",
            {
                "id": "test_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )
        create_case(
            temp_eval_dir,
            "regression",
            "test_002.json",
            {
                "id": "test_002",
                "skill": "text_echo",
                "input": {"text": "WORLD", "format": "lowercase"},
                "expected": {"type": "exact", "value": "world"},
                "timeout_ms": 1000,
            },
        )

        gate = EvalGate(temp_eval_dir)
        # With 50% pass rate and 0.5 threshold, should pass
        report = gate.run_gate(
            "regression", "text_echo", temp_skill_dir, threshold=0.5
        )

        assert report.gate_passed is True
        assert report.pass_rate == 0.5

    def test_run_gate_no_cases(self, temp_eval_dir, temp_skill_dir):
        """run_gate passes when no cases exist (pass_rate=1.0 by default)."""
        create_skill(temp_skill_dir, "def action(): pass")

        gate = EvalGate(temp_eval_dir)
        report = gate.run_gate("replay", "text_echo", temp_skill_dir, threshold=1.0)

        assert report.gate_passed is True
        assert report.total == 0
        assert report.pass_rate == 1.0


class TestEvalResultDataclass:
    """Tests for EvalResult dataclass."""

    def test_eval_result_defaults(self):
        """EvalResult has correct default values."""
        result = EvalResult(case_id="test", passed=True)

        assert result.case_id == "test"
        assert result.passed is True
        assert result.actual_output is None
        assert result.error is None
        assert result.duration_ms == 0.0


class TestGateReportDataclass:
    """Tests for GateReport dataclass."""

    def test_gate_report_creation(self):
        """GateReport can be created with all fields."""
        report = GateReport(
            gate_name="replay",
            total=10,
            passed_count=9,
            failed_count=1,
            pass_rate=0.9,
            threshold=0.99,
            gate_passed=False,
        )

        assert report.gate_name == "replay"
        assert report.total == 10
        assert report.passed_count == 9
        assert report.failed_count == 1
        assert report.pass_rate == 0.9
        assert report.threshold == 0.99
        assert report.gate_passed is False
        assert report.results == []
