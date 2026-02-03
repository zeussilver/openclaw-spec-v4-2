"""AST-based static security gate for validating LLM-generated code.

Three-phase check:
1. String pattern detection (path traversal, system directories)
2. AST parsing (catches syntax errors)
3. AST walking (imports, calls, attributes)
"""

import ast
import re
from dataclasses import dataclass, field

from .policy import (
    ALLOWED_TOP_LEVEL_MODULES,
    FORBIDDEN_ATTRIBUTES,
    FORBIDDEN_CALLS,
    SUSPICIOUS_PATTERNS,
)


@dataclass
class GateResult:
    """Result of AST Gate security check."""

    passed: bool
    violations: list[str] = field(default_factory=list)


class ASTGate:
    """Static security analyzer using AST inspection."""

    def check(self, code: str) -> GateResult:
        """
        Perform three-phase security check on code.

        Args:
            code: Python source code to analyze

        Returns:
            GateResult with passed status and list of violations
        """
        violations: list[str] = []

        # Phase 1: String pattern check
        violations.extend(self._check_strings(code))

        # Phase 2: AST parse
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return GateResult(passed=False, violations=[f"Syntax error: {e}"])

        # Phase 3: AST walk
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                violations.extend(self._check_import(node))
            elif isinstance(node, ast.ImportFrom):
                violations.extend(self._check_import_from(node))
            elif isinstance(node, ast.Call):
                violations.extend(self._check_call(node))
            elif isinstance(node, ast.Attribute):
                violations.extend(self._check_attribute(node))

        return GateResult(passed=len(violations) == 0, violations=violations)

    def _check_strings(self, code: str) -> list[str]:
        """Check for suspicious string patterns in code."""
        violations = []
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, code):
                violations.append(f"Suspicious pattern detected: {pattern}")
        return violations

    def _check_import(self, node: ast.Import) -> list[str]:
        """Check import statements (import x, import x.y)."""
        violations = []
        for alias in node.names:
            # Extract top-level module (e.g., "os" from "os.path")
            top_level = alias.name.split(".")[0]
            if top_level not in ALLOWED_TOP_LEVEL_MODULES:
                violations.append(f"Forbidden import: {alias.name}")
        return violations

    def _check_import_from(self, node: ast.ImportFrom) -> list[str]:
        """Check from-import statements (from x import y)."""
        violations = []
        if node.module:
            # Extract top-level module
            top_level = node.module.split(".")[0]
            if top_level not in ALLOWED_TOP_LEVEL_MODULES:
                violations.append(f"Forbidden import from: {node.module}")
        return violations

    def _check_call(self, node: ast.Call) -> list[str]:
        """Check function calls for forbidden calls."""
        violations = []

        # Check direct calls: func_name(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                violations.append(f"Forbidden call: {node.func.id}")

        # Check attribute calls: obj.func_name(...)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                violations.append(f"Forbidden call: {node.func.attr}")

        return violations

    def _check_attribute(self, node: ast.Attribute) -> list[str]:
        """Check attribute access for forbidden attributes."""
        violations = []
        if node.attr in FORBIDDEN_ATTRIBUTES:
            violations.append(f"Forbidden attribute access: {node.attr}")
        return violations
