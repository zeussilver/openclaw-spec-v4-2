"""Security integration tests for AST Gate and Sandbox.

Tests the full security pipeline:
1. AST Gate blocks dangerous code patterns
2. Sandbox catches runtime bypass attempts (when Docker available)
3. Combined flow from code check to sandbox verification
"""

from pathlib import Path

import pytest

from src.sandbox.runner import SandboxRunner
from src.security.ast_gate import ASTGate


class TestASTGateBypass:
    """Test that AST Gate blocks common bypass attempts."""

    def setup_method(self) -> None:
        """Initialize AST Gate for each test."""
        self.gate = ASTGate()

    def test_import_bypass_blocked(self) -> None:
        """__import__('os') should be rejected by AST gate."""
        code = '''
def action():
    os_module = __import__('os')
    return os_module.getcwd()
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__import__" in v for v in result.violations)

    def test_getattr_bypass_blocked(self) -> None:
        """getattr(x, '__import__') should be rejected by AST gate."""
        code = '''
def action():
    # Try to bypass via getattr
    builtins = getattr(__builtins__, 'eval')
    return builtins('1+1')
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("getattr" in v for v in result.violations)

    def test_globals_bypass_blocked(self) -> None:
        """globals()['__builtins__'] should be rejected by AST gate."""
        code = '''
def action():
    # Try to access builtins via globals
    g = globals()
    return g['__builtins__']['eval']('1+1')
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("globals" in v for v in result.violations)

    def test_subclasses_bypass_blocked(self) -> None:
        """__subclasses__() should be rejected by AST gate."""
        code = '''
def action():
    # Classic sandbox escape via subclasses
    for cls in ().__class__.__bases__[0].__subclasses__():
        if cls.__name__ == 'Popen':
            return cls(['id'])
'''
        result = self.gate.check(code)
        assert not result.passed
        # Should catch __subclasses__ attribute access
        assert any("__subclasses__" in v for v in result.violations)

    def test_bases_bypass_blocked(self) -> None:
        """__bases__ access should be rejected by AST gate."""
        code = '''
def action():
    return ().__class__.__bases__[0]
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__bases__" in v for v in result.violations)

    def test_mro_bypass_blocked(self) -> None:
        """__mro__ access should be rejected by AST gate."""
        code = '''
def action():
    return str.__mro__
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__mro__" in v for v in result.violations)

    def test_code_object_bypass_blocked(self) -> None:
        """__code__ access should be rejected by AST gate."""
        code = '''
def action():
    def inner():
        pass
    return inner.__code__
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__code__" in v for v in result.violations)

    def test_globals_attribute_bypass_blocked(self) -> None:
        """func.__globals__ access should be rejected by AST gate."""
        code = '''
def action():
    def inner():
        pass
    return inner.__globals__['__builtins__']
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__globals__" in v for v in result.violations)

    def test_closure_bypass_blocked(self) -> None:
        """func.__closure__ access should be rejected by AST gate."""
        code = '''
def action():
    x = 10
    def inner():
        return x
    return inner.__closure__
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("__closure__" in v for v in result.violations)

    def test_eval_blocked(self) -> None:
        """eval() should be rejected by AST gate."""
        code = '''
def action(expr: str):
    return eval(expr)
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_exec_blocked(self) -> None:
        """exec() should be rejected by AST gate."""
        code = '''
def action(code: str):
    exec(code)
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("exec" in v for v in result.violations)

    def test_compile_blocked(self) -> None:
        """compile() should be rejected by AST gate."""
        code = '''
def action(code: str):
    return compile(code, '<string>', 'exec')
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("compile" in v for v in result.violations)

    def test_open_blocked(self) -> None:
        """open() should be rejected by AST gate."""
        code = '''
def action(path: str):
    with open(path) as f:
        return f.read()
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("open" in v for v in result.violations)

    def test_path_traversal_blocked(self) -> None:
        """Path traversal patterns should be rejected by AST gate."""
        code = '''
def action():
    path = "../etc/passwd"
    return path
'''
        result = self.gate.check(code)
        assert not result.passed
        assert any("Suspicious pattern" in v for v in result.violations)


class TestSandboxBypass:
    """Test that Sandbox catches runtime bypass attempts when Docker is available."""

    def setup_method(self) -> None:
        """Initialize sandbox runner for each test."""
        self.runner = SandboxRunner()

    @pytest.fixture
    def sandbox_available(self) -> bool:
        """Check if Docker sandbox is available."""
        return self.runner.is_available()

    def test_systemexit_blocked(self, tmp_path: Path, docker_available: bool) -> None:
        """Code with `raise SystemExit(0)` should be caught by sandbox BaseException handler."""
        if not docker_available:
            pytest.skip("Docker sandbox not available")

        skill_dir = tmp_path / "systemexit_skill"
        skill_dir.mkdir()

        # Skill that tries to bypass with SystemExit(0)
        skill_code = '''"""Skill attempting SystemExit bypass."""

def action(text: str) -> str:
    return text.upper()

def verify() -> bool:
    # Try to exit with success code to bypass verification
    raise SystemExit(0)
'''
        (skill_dir / "skill.py").write_text(skill_code)

        passed, logs, metrics = self.runner.run(skill_dir)

        # Should fail because SystemExit is caught by BaseException handler
        assert not passed
        assert "SystemExit" in logs or "VERIFICATION_FAILED" in logs

    def test_keyboard_interrupt_blocked(
        self, tmp_path: Path, docker_available: bool
    ) -> None:
        """KeyboardInterrupt should be caught by sandbox BaseException handler."""
        if not docker_available:
            pytest.skip("Docker sandbox not available")

        skill_dir = tmp_path / "keyboard_interrupt_skill"
        skill_dir.mkdir()

        skill_code = '''"""Skill attempting KeyboardInterrupt bypass."""

def action(text: str) -> str:
    return text.upper()

def verify() -> bool:
    raise KeyboardInterrupt()
'''
        (skill_dir / "skill.py").write_text(skill_code)

        passed, logs, metrics = self.runner.run(skill_dir)

        assert not passed
        assert "KeyboardInterrupt" in logs or "VERIFICATION_FAILED" in logs

    def test_truthy_not_true_blocked(
        self, tmp_path: Path, docker_available: bool
    ) -> None:
        """verify() returning 1 (truthy but not True) should fail."""
        if not docker_available:
            pytest.skip("Docker sandbox not available")

        skill_dir = tmp_path / "truthy_skill"
        skill_dir.mkdir()

        skill_code = '''"""Skill returning truthy value instead of True."""

def action(text: str) -> str:
    return text.upper()

def verify() -> bool:
    # Return 1 which is truthy but not True
    return 1
'''
        (skill_dir / "skill.py").write_text(skill_code)

        passed, logs, metrics = self.runner.run(skill_dir)

        # Should fail because result is not exactly True
        assert not passed
        assert "VERIFICATION_FAILED" in logs


class TestASTThenSandboxFlow:
    """Test the combined flow: AST Gate check followed by Sandbox verification."""

    def test_safe_skill_passes_both(
        self, tmp_path: Path, docker_available: bool
    ) -> None:
        """A safe skill should pass AST Gate and (if Docker available) Sandbox."""
        gate = ASTGate()
        runner = SandboxRunner()

        # Safe skill code using only allowed imports
        skill_code = '''"""Safe text transformation skill."""

import json


def action(text: str, format: str = "upper") -> str:
    """Transform text to specified format."""
    if format == "upper":
        return text.upper()
    elif format == "lower":
        return text.lower()
    else:
        return text


def verify() -> bool:
    """Verify the skill works correctly."""
    result = action("hello", "upper")
    assert result == "HELLO", f"Expected HELLO, got {result}"
    return True
'''

        # Step 1: AST Gate check
        gate_result = gate.check(skill_code)
        assert gate_result.passed, f"AST Gate failed: {gate_result.violations}"

        # Step 2: Sandbox verification (if Docker available)
        if docker_available:
            skill_dir = tmp_path / "safe_skill"
            skill_dir.mkdir()
            (skill_dir / "skill.py").write_text(skill_code)

            passed, logs, metrics = runner.run(skill_dir)
            assert passed, f"Sandbox failed: {logs}"
            assert "VERIFICATION_SUCCESS" in logs

    def test_unsafe_skill_blocked_at_ast_gate(self) -> None:
        """An unsafe skill should be blocked at AST Gate before reaching Sandbox."""
        gate = ASTGate()

        # Unsafe skill code trying to import os
        skill_code = '''"""Unsafe skill attempting to import os."""

import os

def action(cmd: str) -> str:
    return os.popen(cmd).read()

def verify() -> bool:
    return True
'''

        # Should fail at AST Gate
        gate_result = gate.check(skill_code)
        assert not gate_result.passed
        assert any("os" in v for v in gate_result.violations)

    def test_chained_bypass_attempt_blocked(self) -> None:
        """Complex chained bypass attempts should be blocked."""
        gate = ASTGate()

        # Attempt to chain multiple techniques
        skill_code = '''"""Skill attempting chained bypass."""

def action():
    # Try to get builtins via multiple paths
    base = ().__class__.__bases__[0]
    for cls in base.__subclasses__():
        if 'warning' in cls.__name__.lower():
            # Try to access globals from a loaded class
            pass
    return "done"

def verify() -> bool:
    return True
'''

        gate_result = gate.check(skill_code)
        assert not gate_result.passed
        # Should catch both __bases__ and __subclasses__
        assert any("__bases__" in v for v in gate_result.violations)
        assert any("__subclasses__" in v for v in gate_result.violations)


class TestMultipleViolations:
    """Test that multiple violations are all reported."""

    def test_reports_all_violations(self) -> None:
        """AST Gate should report all violations, not just the first one."""
        gate = ASTGate()

        # Code with multiple violations
        code = '''
import os
import subprocess

def action():
    eval("1+1")
    exec("pass")
    x = getattr(obj, "attr")
    return globals()
'''

        result = gate.check(code)
        assert not result.passed
        # Should have multiple violations
        assert len(result.violations) >= 4

        # Check specific violations are present
        violation_text = " ".join(result.violations)
        assert "os" in violation_text
        assert "subprocess" in violation_text
        assert "eval" in violation_text
        assert "exec" in violation_text
