"""Mock LLM provider for testing.

Returns predefined skill packages based on keyword matching in capability descriptions.
All generated code passes AST Gate (uses only allowed imports like json, re).
"""

from .base import LLMProvider, SkillPackage

# Trigger keywords for each canned skill
TEXT_ECHO_TRIGGERS = frozenset({"echo", "text", "uppercase", "convert", "lowercase", "case"})
FILENAME_TRIGGERS = frozenset({"filename", "normalize", "sanitize", "safe"})


# =============================================================================
# Canned Skill: text_echo
# =============================================================================
TEXT_ECHO_CODE = '''\
"""Text echo skill - transforms text to different formats."""

import json


def action(text: str, format: str = "upper") -> str:
    """Transform text to the specified format.

    Args:
        text: The input text to transform.
        format: The format to apply - "upper", "lower", or "title".

    Returns:
        The transformed text.
    """
    if format == "upper":
        return text.upper()
    elif format == "lower":
        return text.lower()
    elif format == "title":
        return text.title()
    else:
        return text


def verify() -> bool:
    """Verify the skill works correctly."""
    # Test uppercase
    assert action("hello", "upper") == "HELLO", "uppercase failed"
    # Test lowercase
    assert action("HELLO", "lower") == "hello", "lowercase failed"
    # Test title case
    assert action("hello world", "title") == "Hello World", "title failed"
    # Test default (upper)
    assert action("test") == "TEST", "default format failed"
    return True
'''

TEXT_ECHO_MANIFEST = {
    "name": "text_echo",
    "version": "1.0.0",
    "description": "Transforms text to different formats including uppercase, lowercase, and title case.",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The input text to transform"},
            "format": {
                "type": "string",
                "enum": ["upper", "lower", "title"],
                "default": "upper",
                "description": "The format to apply",
            },
        },
        "required": ["text"],
    },
    "outputs_schema": {"type": "string", "description": "The transformed text"},
    "permissions": {"filesystem": "none", "network": False, "subprocess": False},
    "dependencies": [],
}


# =============================================================================
# Canned Skill: safe_filename_normalize
# =============================================================================
FILENAME_CODE = '''\
"""Safe filename normalizer - sanitizes filenames for safe filesystem use."""

import re


def action(filename: str) -> str:
    """Normalize a filename to be safe for filesystem use.

    Removes or replaces characters that could cause issues:
    - Removes dot-dot sequences used in directory traversal
    - Replaces spaces with underscores
    - Removes special characters except dots, hyphens, underscores
    - Converts to lowercase
    - Limits length to 255 characters

    Args:
        filename: The input filename to normalize.

    Returns:
        A safe, normalized filename.
    """
    # Remove directory traversal attempts (dot-dot patterns)
    while ".." in filename:
        filename = filename.replace("..", "")

    # Remove path separators
    filename = filename.replace("/", "")
    filename = filename.replace(chr(92), "")  # backslash

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Keep only safe characters: alphanumeric, dots, hyphens, underscores
    filename = re.sub(r"[^a-zA-Z0-9._-]", "", filename)

    # Convert to lowercase
    filename = filename.lower()

    # Remove leading/trailing dots and underscores
    filename = filename.strip("._")

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    # Ensure non-empty result
    if not filename:
        filename = "unnamed"

    return filename


def verify() -> bool:
    """Verify the skill works correctly."""
    # Test basic normalization
    assert action("Hello World.txt") == "hello_world.txt", "basic failed"
    # Test dot-dot removal
    test_input = "." + "." + "/" + "." + "." + "/foo"
    assert action(test_input) == "foo", "dot-dot removal failed"
    # Test special characters
    assert action("file<>:name?.txt") == "filename.txt", "special chars failed"
    # Test empty result handling
    assert action("...") == "unnamed", "empty result failed"
    # Test length limit
    long_name = "a" * 300 + ".txt"
    assert len(action(long_name)) <= 255, "length limit failed"
    return True
'''

FILENAME_MANIFEST = {
    "name": "safe_filename_normalize",
    "version": "1.0.0",
    "description": "Normalizes filenames to be safe for filesystem use by removing dangerous characters and patterns.",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "The filename to normalize"}
        },
        "required": ["filename"],
    },
    "outputs_schema": {"type": "string", "description": "The normalized, safe filename"},
    "permissions": {"filesystem": "none", "network": False, "subprocess": False},
    "dependencies": [],
}


class MockLLM(LLMProvider):
    """Mock LLM provider that returns predefined skills based on keywords.

    Supports capabilities matching these keywords:
    - text_echo: "echo", "text", "uppercase", "convert", "lowercase", "case"
    - safe_filename_normalize: "filename", "normalize", "sanitize", "safe"

    Raises ValueError for unknown capabilities.
    """

    def generate_skill(self, capability: str, context: str = "") -> SkillPackage:
        """Generate a skill package from a capability description.

        Matches keywords in the capability string to return canned skills.

        Args:
            capability: Natural language description of the desired capability.
            context: Optional additional context (ignored by MockLLM).

        Returns:
            SkillPackage for the matched skill.

        Raises:
            ValueError: If no matching skill is found for the capability.
        """
        # Normalize capability for matching
        cap_lower = capability.lower()
        cap_words = set(cap_lower.split())

        # Check for text_echo triggers
        if cap_words & TEXT_ECHO_TRIGGERS:
            return SkillPackage(
                name="text_echo",
                code=TEXT_ECHO_CODE,
                manifest=TEXT_ECHO_MANIFEST.copy(),
                tests=[],
            )

        # Check for filename normalizer triggers
        if cap_words & FILENAME_TRIGGERS:
            return SkillPackage(
                name="safe_filename_normalize",
                code=FILENAME_CODE,
                manifest=FILENAME_MANIFEST.copy(),
                tests=[],
            )

        # No match found
        raise ValueError(
            f"MockLLM cannot generate skill for capability: {capability}. "
            f"Supported triggers: {TEXT_ECHO_TRIGGERS | FILENAME_TRIGGERS}"
        )
