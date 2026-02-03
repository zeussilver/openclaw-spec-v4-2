"""Exhaustive tests for AST Gate security analysis.

Test matrix from spec/acceptance.md section 3.1.
"""

import pytest

from src.security.ast_gate import ASTGate, GateResult


@pytest.fixture
def gate() -> ASTGate:
    """Create an ASTGate instance for testing."""
    return ASTGate()


# =============================================================================
# FORBIDDEN IMPORTS - Must Reject
# =============================================================================


class TestForbiddenImports:
    """Test that forbidden module imports are rejected."""

    def test_import_os(self, gate: ASTGate) -> None:
        """import os must be rejected."""
        result = gate.check("import os")
        assert not result.passed
        assert any("os" in v for v in result.violations)

    def test_import_subprocess(self, gate: ASTGate) -> None:
        """import subprocess must be rejected."""
        result = gate.check("import subprocess")
        assert not result.passed
        assert any("subprocess" in v for v in result.violations)

    def test_import_socket(self, gate: ASTGate) -> None:
        """import socket must be rejected."""
        result = gate.check("import socket")
        assert not result.passed
        assert any("socket" in v for v in result.violations)

    def test_import_shutil(self, gate: ASTGate) -> None:
        """import shutil must be rejected."""
        result = gate.check("import shutil")
        assert not result.passed
        assert any("shutil" in v for v in result.violations)

    def test_import_sys(self, gate: ASTGate) -> None:
        """import sys must be rejected."""
        result = gate.check("import sys")
        assert not result.passed
        assert any("sys" in v for v in result.violations)

    def test_from_os_import_path(self, gate: ASTGate) -> None:
        """from os import path must be rejected."""
        result = gate.check("from os import path")
        assert not result.passed
        assert any("os" in v for v in result.violations)

    def test_from_os_path_import_join(self, gate: ASTGate) -> None:
        """from os.path import join must be rejected."""
        result = gate.check("from os.path import join")
        assert not result.passed
        assert any("os" in v for v in result.violations)

    def test_import_os_path(self, gate: ASTGate) -> None:
        """import os.path must be rejected (top-level is os)."""
        result = gate.check("import os.path")
        assert not result.passed
        assert any("os" in v for v in result.violations)


# =============================================================================
# FORBIDDEN CALLS - Must Reject
# =============================================================================


class TestForbiddenCalls:
    """Test that forbidden function calls are rejected."""

    def test_dunder_import(self, gate: ASTGate) -> None:
        """__import__('os') must be rejected."""
        result = gate.check("__import__('os')")
        assert not result.passed
        assert any("__import__" in v for v in result.violations)

    def test_eval(self, gate: ASTGate) -> None:
        """eval('1+1') must be rejected."""
        result = gate.check("eval('1+1')")
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_exec(self, gate: ASTGate) -> None:
        """exec('pass') must be rejected."""
        result = gate.check("exec('pass')")
        assert not result.passed
        assert any("exec" in v for v in result.violations)

    def test_compile(self, gate: ASTGate) -> None:
        """compile('x=1','','exec') must be rejected."""
        result = gate.check("compile('x=1','','exec')")
        assert not result.passed
        assert any("compile" in v for v in result.violations)

    def test_open_read(self, gate: ASTGate) -> None:
        """open('/etc/passwd') must be rejected."""
        result = gate.check("open('/etc/passwd')")
        assert not result.passed
        assert any("open" in v for v in result.violations)

    def test_open_write(self, gate: ASTGate) -> None:
        """open('file.txt','w') must be rejected."""
        result = gate.check("open('file.txt','w')")
        assert not result.passed
        assert any("open" in v for v in result.violations)

    def test_input(self, gate: ASTGate) -> None:
        """input() must be rejected."""
        result = gate.check("input('Enter: ')")
        assert not result.passed
        assert any("input" in v for v in result.violations)

    def test_getattr(self, gate: ASTGate) -> None:
        """getattr(obj,'method') must be rejected."""
        result = gate.check("getattr(obj, 'method')")
        assert not result.passed
        assert any("getattr" in v for v in result.violations)

    def test_setattr(self, gate: ASTGate) -> None:
        """setattr(obj,'attr',val) must be rejected."""
        result = gate.check("setattr(obj, 'attr', val)")
        assert not result.passed
        assert any("setattr" in v for v in result.violations)

    def test_delattr(self, gate: ASTGate) -> None:
        """delattr(obj,'attr') must be rejected."""
        result = gate.check("delattr(obj, 'attr')")
        assert not result.passed
        assert any("delattr" in v for v in result.violations)

    def test_globals(self, gate: ASTGate) -> None:
        """globals() must be rejected."""
        result = gate.check("globals()")
        assert not result.passed
        assert any("globals" in v for v in result.violations)

    def test_locals(self, gate: ASTGate) -> None:
        """locals() must be rejected."""
        result = gate.check("locals()")
        assert not result.passed
        assert any("locals" in v for v in result.violations)

    def test_vars(self, gate: ASTGate) -> None:
        """vars() must be rejected."""
        result = gate.check("vars()")
        assert not result.passed
        assert any("vars" in v for v in result.violations)

    def test_breakpoint(self, gate: ASTGate) -> None:
        """breakpoint() must be rejected."""
        result = gate.check("breakpoint()")
        assert not result.passed
        assert any("breakpoint" in v for v in result.violations)

    def test_method_call_eval(self, gate: ASTGate) -> None:
        """obj.eval() as method call must be rejected."""
        result = gate.check("builtins.eval('1+1')")
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_method_call_exec(self, gate: ASTGate) -> None:
        """obj.exec() as method call must be rejected."""
        result = gate.check("builtins.exec('pass')")
        assert not result.passed
        assert any("exec" in v for v in result.violations)


# =============================================================================
# FORBIDDEN ATTRIBUTES - Must Reject
# =============================================================================


class TestForbiddenAttributes:
    """Test that forbidden attribute access is rejected."""

    def test_subclasses(self, gate: ASTGate) -> None:
        """x.__subclasses__() must be rejected."""
        result = gate.check("x.__subclasses__()")
        assert not result.passed
        assert any("__subclasses__" in v for v in result.violations)

    def test_func_globals(self, gate: ASTGate) -> None:
        """func.__globals__ must be rejected."""
        result = gate.check("func.__globals__")
        assert not result.passed
        assert any("__globals__" in v for v in result.violations)

    def test_func_code(self, gate: ASTGate) -> None:
        """func.__code__ must be rejected."""
        result = gate.check("func.__code__")
        assert not result.passed
        assert any("__code__" in v for v in result.violations)

    def test_bases(self, gate: ASTGate) -> None:
        """x.__bases__ must be rejected."""
        result = gate.check("x.__bases__")
        assert not result.passed
        assert any("__bases__" in v for v in result.violations)

    def test_mro(self, gate: ASTGate) -> None:
        """x.__mro__ must be rejected."""
        result = gate.check("x.__mro__")
        assert not result.passed
        assert any("__mro__" in v for v in result.violations)

    def test_builtins(self, gate: ASTGate) -> None:
        """x.__builtins__ must be rejected."""
        result = gate.check("x.__builtins__")
        assert not result.passed
        assert any("__builtins__" in v for v in result.violations)

    def test_closure(self, gate: ASTGate) -> None:
        """func.__closure__ must be rejected."""
        result = gate.check("func.__closure__")
        assert not result.passed
        assert any("__closure__" in v for v in result.violations)

    def test_loader(self, gate: ASTGate) -> None:
        """module.__loader__ must be rejected."""
        result = gate.check("module.__loader__")
        assert not result.passed
        assert any("__loader__" in v for v in result.violations)

    def test_spec(self, gate: ASTGate) -> None:
        """module.__spec__ must be rejected."""
        result = gate.check("module.__spec__")
        assert not result.passed
        assert any("__spec__" in v for v in result.violations)


# =============================================================================
# PATH TRAVERSAL PATTERNS - Must Reject
# =============================================================================


class TestPathTraversal:
    """Test that path traversal patterns are rejected."""

    def test_path_traversal_etc_passwd(self, gate: ASTGate) -> None:
        """String containing '../../../etc/passwd' must be rejected."""
        result = gate.check("path = '../../../etc/passwd'")
        assert not result.passed
        # Multiple patterns might match

    def test_path_traversal_etc_shadow(self, gate: ASTGate) -> None:
        """String containing '/etc/shadow' must be rejected."""
        result = gate.check("path = '/etc/shadow'")
        assert not result.passed
        assert any("/etc/" in v for v in result.violations)

    def test_path_traversal_proc_self(self, gate: ASTGate) -> None:
        """String containing '/proc/self/environ' must be rejected."""
        result = gate.check("path = '/proc/self/environ'")
        assert not result.passed
        assert any("/proc/" in v for v in result.violations)

    def test_path_traversal_sys(self, gate: ASTGate) -> None:
        """String containing '/sys/class' must be rejected."""
        result = gate.check("path = '/sys/class/net'")
        assert not result.passed
        assert any("/sys/" in v for v in result.violations)

    def test_path_traversal_home(self, gate: ASTGate) -> None:
        """String containing '~/' must be rejected."""
        result = gate.check("path = '~/.ssh/id_rsa'")
        assert not result.passed
        assert any("~/" in v for v in result.violations)

    def test_path_traversal_windows(self, gate: ASTGate) -> None:
        """String containing '..\\' must be rejected."""
        result = gate.check(r"path = '..\\..\\windows\\system32'")
        assert not result.passed


# =============================================================================
# CHAINED ATTACKS - Must Reject
# =============================================================================


class TestChainedAttacks:
    """Test that chained sandbox escape attempts are rejected."""

    def test_subclass_chain_attack(self, gate: ASTGate) -> None:
        """().__class__.__bases__[0].__subclasses__() must be rejected."""
        code = "().__class__.__bases__[0].__subclasses__()"
        result = gate.check(code)
        assert not result.passed
        # Should catch multiple violations: __bases__ and __subclasses__
        violations_str = " ".join(result.violations)
        assert "__bases__" in violations_str or "__subclasses__" in violations_str

    def test_func_globals_builtins(self, gate: ASTGate) -> None:
        """func.__globals__['__builtins__'] must be rejected."""
        code = "func.__globals__['__builtins__']"
        result = gate.check(code)
        assert not result.passed
        assert any("__globals__" in v for v in result.violations)


# =============================================================================
# ALLOWED IMPORTS - Must Pass
# =============================================================================


class TestAllowedImports:
    """Test that allowed module imports pass."""

    def test_import_json(self, gate: ASTGate) -> None:
        """import json must pass."""
        result = gate.check("import json")
        assert result.passed
        assert result.violations == []

    def test_import_re(self, gate: ASTGate) -> None:
        """import re must pass."""
        result = gate.check("import re")
        assert result.passed
        assert result.violations == []

    def test_import_pathlib(self, gate: ASTGate) -> None:
        """import pathlib must pass."""
        result = gate.check("import pathlib")
        assert result.passed
        assert result.violations == []

    def test_from_datetime_import(self, gate: ASTGate) -> None:
        """from datetime import datetime must pass."""
        result = gate.check("from datetime import datetime")
        assert result.passed
        assert result.violations == []

    def test_from_typing_import(self, gate: ASTGate) -> None:
        """from typing import List, Optional must pass."""
        result = gate.check("from typing import List, Optional")
        assert result.passed
        assert result.violations == []

    def test_from_collections_import(self, gate: ASTGate) -> None:
        """from collections import defaultdict must pass."""
        result = gate.check("from collections import defaultdict")
        assert result.passed
        assert result.violations == []

    def test_import_math(self, gate: ASTGate) -> None:
        """import math must pass."""
        result = gate.check("import math")
        assert result.passed
        assert result.violations == []

    def test_import_hashlib(self, gate: ASTGate) -> None:
        """import hashlib must pass."""
        result = gate.check("import hashlib")
        assert result.passed
        assert result.violations == []

    def test_import_functools(self, gate: ASTGate) -> None:
        """import functools must pass."""
        result = gate.check("import functools")
        assert result.passed
        assert result.violations == []

    def test_import_itertools(self, gate: ASTGate) -> None:
        """import itertools must pass."""
        result = gate.check("import itertools")
        assert result.passed
        assert result.violations == []

    def test_import_dataclasses(self, gate: ASTGate) -> None:
        """import dataclasses must pass."""
        result = gate.check("import dataclasses")
        assert result.passed
        assert result.violations == []

    def test_import_enum(self, gate: ASTGate) -> None:
        """import enum must pass."""
        result = gate.check("import enum")
        assert result.passed
        assert result.violations == []

    def test_import_base64(self, gate: ASTGate) -> None:
        """import base64 must pass."""
        result = gate.check("import base64")
        assert result.passed
        assert result.violations == []

    def test_import_urllib(self, gate: ASTGate) -> None:
        """import urllib must pass."""
        result = gate.check("import urllib")
        assert result.passed
        assert result.violations == []

    def test_import_csv(self, gate: ASTGate) -> None:
        """import csv must pass."""
        result = gate.check("import csv")
        assert result.passed
        assert result.violations == []

    def test_import_decimal(self, gate: ASTGate) -> None:
        """import decimal must pass."""
        result = gate.check("import decimal")
        assert result.passed
        assert result.violations == []

    def test_import_copy(self, gate: ASTGate) -> None:
        """import copy must pass."""
        result = gate.check("import copy")
        assert result.passed
        assert result.violations == []

    def test_import_abc(self, gate: ASTGate) -> None:
        """import abc must pass."""
        result = gate.check("import abc")
        assert result.passed
        assert result.violations == []


# =============================================================================
# COMPLETE SAFE SKILL - Must Pass
# =============================================================================


class TestSafeSkills:
    """Test that complete safe skills pass."""

    def test_complete_safe_skill(self, gate: ASTGate) -> None:
        """A complete safe skill must pass."""
        code = '''
import json

def action(text: str) -> str:
    """Transform text to uppercase and return as JSON."""
    return json.dumps({"result": text.upper()})

def verify() -> bool:
    """Verify the skill works correctly."""
    result = action("hello")
    expected = json.dumps({"result": "HELLO"})
    return result == expected
'''
        result = gate.check(code)
        assert result.passed
        assert result.violations == []

    def test_skill_with_multiple_safe_imports(self, gate: ASTGate) -> None:
        """Skill with multiple allowed imports must pass."""
        code = '''
import json
import re
from typing import Optional
from collections import defaultdict
from datetime import datetime

def action(data: dict) -> dict:
    """Process data with timestamp."""
    result = defaultdict(list)
    result["timestamp"] = datetime.now().isoformat()
    result["data"] = data
    return dict(result)

def verify() -> bool:
    return True
'''
        result = gate.check(code)
        assert result.passed
        assert result.violations == []

    def test_skill_with_math_operations(self, gate: ASTGate) -> None:
        """Skill with math operations must pass."""
        code = '''
import math
from decimal import Decimal

def action(value: float) -> dict:
    """Calculate mathematical properties."""
    return {
        "sqrt": math.sqrt(value),
        "ceil": math.ceil(value),
        "floor": math.floor(value),
        "precise": str(Decimal(str(value)))
    }

def verify() -> bool:
    result = action(2.5)
    return "sqrt" in result
'''
        result = gate.check(code)
        assert result.passed
        assert result.violations == []


# =============================================================================
# SYNTAX ERRORS - Must Fail with Error Message
# =============================================================================


class TestSyntaxErrors:
    """Test that syntax errors are caught and reported."""

    def test_syntax_error_missing_colon(self, gate: ASTGate) -> None:
        """Syntax error (missing colon) must be caught."""
        result = gate.check("def foo()")  # Missing colon
        assert not result.passed
        assert any("Syntax error" in v for v in result.violations)

    def test_syntax_error_invalid_token(self, gate: ASTGate) -> None:
        """Syntax error (invalid token) must be caught."""
        result = gate.check("x = @#$%")
        assert not result.passed
        assert any("Syntax error" in v for v in result.violations)

    def test_syntax_error_incomplete(self, gate: ASTGate) -> None:
        """Syntax error (incomplete statement) must be caught."""
        result = gate.check("if True")  # Missing colon and body
        assert not result.passed
        assert any("Syntax error" in v for v in result.violations)


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_code(self, gate: ASTGate) -> None:
        """Empty code should pass."""
        result = gate.check("")
        assert result.passed
        assert result.violations == []

    def test_only_comments(self, gate: ASTGate) -> None:
        """Code with only comments should pass."""
        result = gate.check("# This is a comment")
        assert result.passed
        assert result.violations == []

    def test_pass_statement(self, gate: ASTGate) -> None:
        """Single pass statement should pass."""
        result = gate.check("pass")
        assert result.passed
        assert result.violations == []

    def test_import_as_alias(self, gate: ASTGate) -> None:
        """Forbidden import with alias must still be rejected."""
        result = gate.check("import os as safe_os")
        assert not result.passed
        assert any("os" in v for v in result.violations)

    def test_from_import_as_alias(self, gate: ASTGate) -> None:
        """Forbidden from-import with alias must still be rejected."""
        result = gate.check("from subprocess import Popen as SafePopen")
        assert not result.passed
        assert any("subprocess" in v for v in result.violations)

    def test_multiple_violations(self, gate: ASTGate) -> None:
        """Code with multiple violations should report all."""
        code = """
import os
import subprocess
eval('1+1')
x.__globals__
"""
        result = gate.check(code)
        assert not result.passed
        # Should have at least 4 violations
        assert len(result.violations) >= 4

    def test_nested_forbidden_call(self, gate: ASTGate) -> None:
        """Nested forbidden call must be rejected."""
        result = gate.check("result = str(eval('1+1'))")
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_forbidden_in_function_def(self, gate: ASTGate) -> None:
        """Forbidden call inside function must be rejected."""
        code = """
def sneaky():
    return eval('os')
"""
        result = gate.check(code)
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_forbidden_in_class_def(self, gate: ASTGate) -> None:
        """Forbidden call inside class must be rejected."""
        code = """
class Sneaky:
    def method(self):
        return globals()
"""
        result = gate.check(code)
        assert not result.passed
        assert any("globals" in v for v in result.violations)

    def test_forbidden_in_lambda(self, gate: ASTGate) -> None:
        """Forbidden call inside lambda must be rejected."""
        result = gate.check("f = lambda: eval('1')")
        assert not result.passed
        assert any("eval" in v for v in result.violations)

    def test_gate_result_dataclass(self, gate: ASTGate) -> None:
        """GateResult should be a proper dataclass."""
        result = gate.check("x = 1")
        assert isinstance(result, GateResult)
        assert isinstance(result.passed, bool)
        assert isinstance(result.violations, list)
