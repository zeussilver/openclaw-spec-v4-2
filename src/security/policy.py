"""Security policy constants for AST Gate.

These constants define the security rules for validating LLM-generated code.
Copied VERBATIM from spec/security.md section 3.
"""

# Allowed top-level modules (complete list from spec)
ALLOWED_TOP_LEVEL_MODULES = frozenset({
    # Data processing
    "json", "csv", "xml",
    # String and regex
    "re", "string", "textwrap",
    # Path (safe usage)
    "pathlib",
    # Time
    "datetime", "time", "calendar",
    # Types
    "typing", "types", "dataclasses", "enum",
    # Collections and iteration
    "collections", "itertools", "functools",
    # Math
    "math", "decimal", "fractions", "statistics", "random",
    # Encoding
    "hashlib", "base64", "binascii",
    # URL parsing (not urlopen)
    "urllib",
    # Utilities
    "copy", "pprint", "operator",
    # Context
    "contextlib",
    # ABC
    "abc",
})

# Forbidden function calls
FORBIDDEN_CALLS = frozenset({
    # Dynamic execution
    "__import__", "eval", "exec", "compile",
    # File operations
    "open", "input",
    # Reflection (can be used to bypass)
    "getattr", "setattr", "delattr",
    # Scope access
    "globals", "locals", "vars",
    # Debugging
    "breakpoint",
})

# Forbidden attribute access
FORBIDDEN_ATTRIBUTES = frozenset({
    # Type system attacks
    "__subclasses__", "__bases__", "__mro__",
    # Code objects
    "__globals__", "__code__", "__closure__",
    # Builtins
    "__builtins__", "__import__",
    # Module loading
    "__loader__", "__spec__",
})

# Suspicious string patterns (regex)
# Note: Forward slashes don't need escaping in Python regex
SUSPICIOUS_PATTERNS = [
    r'\.\./',            # Path traversal (Unix)
    r'\.\.\\',           # Path traversal (Windows)
    r'/etc/',            # System directory
    r'/proc/',           # proc filesystem
    r'/sys/',            # sys filesystem
    r'~/',               # User home directory
]
