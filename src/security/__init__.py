"""Security module for OpenClaw.

Provides AST-based static security analysis to validate LLM-generated code.
"""

from .ast_gate import ASTGate, GateResult
from .policy import (
    ALLOWED_TOP_LEVEL_MODULES,
    FORBIDDEN_ATTRIBUTES,
    FORBIDDEN_CALLS,
    SUSPICIOUS_PATTERNS,
)

__all__ = [
    "ASTGate",
    "GateResult",
    "ALLOWED_TOP_LEVEL_MODULES",
    "FORBIDDEN_CALLS",
    "FORBIDDEN_ATTRIBUTES",
    "SUSPICIOUS_PATTERNS",
]
