"""Tests for Docker sandbox harness and runner.

Tests are skipped if Docker is not available.
"""
import tempfile
from pathlib import Path

import pytest

from src.sandbox.runner import SandboxRunner


def docker_available() -> bool:
    """Check if Docker is available for testing."""
    try:
        runner = SandboxRunner()
        return runner.is_available()
    except Exception:
        return False


# Skip all tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not docker_available(), reason="Docker not available or image not built"
)


@pytest.fixture
def runner() -> SandboxRunner:
    """Create a sandbox runner instance."""
    return SandboxRunner(timeout=30)


@pytest.fixture
def skill_dir():
    """Create a temporary directory for skill files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def write_skill(skill_dir: Path, code: str) -> Path:
    """Write a skill.py file to the skill directory."""
    skill_file = skill_dir / "skill.py"
    skill_file.write_text(code)
    return skill_dir


class TestVerifySuccess:
    """Test cases where verify() returns True."""

    def test_verify_returns_true(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() returning True should pass."""
        code = '''
def verify():
    return True

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is True
        assert "VERIFICATION_SUCCESS" in logs
        assert metrics["exit_code"] == 0
        assert "duration_ms" in metrics


class TestVerifyFalse:
    """Test cases where verify() returns False."""

    def test_verify_returns_false(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() returning False should fail."""
        code = '''
def verify():
    return False

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "False" in logs


class TestVerifyNone:
    """Test cases where verify() returns None."""

    def test_verify_returns_none(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() returning None should fail (not truthy check)."""
        code = '''
def verify():
    return None

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "None" in logs


class TestVerifyTruthyInt:
    """Test cases where verify() returns truthy integer."""

    def test_verify_returns_int_one(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() returning 1 should fail (strict is True check)."""
        code = '''
def verify():
    return 1

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        # Should show the actual returned value
        assert "1" in logs


class TestVerifyTruthyString:
    """Test cases where verify() returns truthy string."""

    def test_verify_returns_string(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() returning 'yes' should fail (strict is True check)."""
        code = '''
def verify():
    return "yes"

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "yes" in logs


class TestVerifyException:
    """Test cases where verify() raises an exception."""

    def test_verify_raises_exception(self, runner: SandboxRunner, skill_dir: Path):
        """Skill with verify() raising exception should fail."""
        code = '''
def verify():
    raise ValueError("Something went wrong")

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "ValueError" in logs


class TestSystemExitZero:
    """Test cases where skill raises SystemExit(0)."""

    def test_systemexit_zero_is_caught(self, runner: SandboxRunner, skill_dir: Path):
        """SystemExit(0) should be caught and treated as failure."""
        code = '''
def verify():
    raise SystemExit(0)

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "SystemExit" in logs


class TestSystemExitOne:
    """Test cases where skill raises SystemExit(1)."""

    def test_systemexit_one_is_caught(self, runner: SandboxRunner, skill_dir: Path):
        """SystemExit(1) should be caught and treated as failure."""
        code = '''
def verify():
    raise SystemExit(1)

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "SystemExit" in logs


class TestKeyboardInterrupt:
    """Test cases where skill raises KeyboardInterrupt."""

    def test_keyboard_interrupt_is_caught(self, runner: SandboxRunner, skill_dir: Path):
        """KeyboardInterrupt should be caught and treated as failure."""
        code = '''
def verify():
    raise KeyboardInterrupt()

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "KeyboardInterrupt" in logs


class TestTimeout:
    """Test cases for timeout handling."""

    def test_infinite_loop_times_out(self, skill_dir: Path):
        """Skill with infinite loop should timeout."""
        runner = SandboxRunner(timeout=5)  # Short timeout for test
        code = '''
def verify():
    while True:
        pass
    return True

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        # Either timeout flag or no VERIFICATION_SUCCESS
        assert "VERIFICATION_SUCCESS" not in logs


class TestMissingVerify:
    """Test cases where verify() function is missing."""

    def test_missing_verify_function(self, runner: SandboxRunner, skill_dir: Path):
        """Skill without verify() function should fail."""
        code = '''
def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "verify" in logs.lower()


class TestMissingAction:
    """Test cases where action() function is missing."""

    def test_missing_action_function(self, runner: SandboxRunner, skill_dir: Path):
        """Skill without action() function should fail."""
        code = '''
def verify():
    return True
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert passed is False
        assert "VERIFICATION_FAILED" in logs
        assert "action" in logs.lower()


class TestRunnerAvailability:
    """Test runner availability checks."""

    def test_is_available_returns_bool(self, runner: SandboxRunner):
        """is_available() should return a boolean."""
        result = runner.is_available()
        assert isinstance(result, bool)
        # If we got this far, Docker is available
        assert result is True


class TestMetrics:
    """Test that metrics are properly recorded."""

    def test_metrics_include_duration(self, runner: SandboxRunner, skill_dir: Path):
        """Metrics should include duration_ms."""
        code = '''
def verify():
    return True

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert "duration_ms" in metrics
        assert isinstance(metrics["duration_ms"], int)
        assert metrics["duration_ms"] >= 0

    def test_metrics_include_exit_code(self, runner: SandboxRunner, skill_dir: Path):
        """Metrics should include exit_code."""
        code = '''
def verify():
    return True

def action(inputs):
    return {"result": "ok"}
'''
        write_skill(skill_dir, code)
        passed, logs, metrics = runner.run(skill_dir)

        assert "exit_code" in metrics
        assert metrics["exit_code"] == 0
