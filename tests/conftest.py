"""Pytest fixtures for OpenClaw tests."""

import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from src.sandbox.runner import SandboxRunner


@pytest.fixture
def tmp_skill_dir(tmp_path: Path) -> Path:
    """Create a temp directory with a minimal skill.py and skill.json."""
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()

    # Minimal skill.py
    skill_code = '''"""Test skill for unit testing."""


def run(inputs: dict) -> dict:
    """Echo the input text."""
    return {"result": inputs.get("text", "")}


def verify() -> bool:
    """Verify the skill works correctly."""
    result = run({"text": "hello"})
    return result == {"result": "hello"}
'''
    (skill_dir / "skill.py").write_text(skill_code)

    # Minimal skill.json manifest
    manifest = {
        "name": "test_skill",
        "version": "1.0.0",
        "description": "A minimal test skill for unit testing purposes",
        "inputs_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "outputs_schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
        "permissions": {"filesystem": "none", "network": False, "subprocess": False},
        "dependencies": [],
    }
    (skill_dir / "skill.json").write_text(json.dumps(manifest, indent=2))

    return skill_dir


@pytest.fixture
def tmp_registry(tmp_path: Path) -> Path:
    """Create a temp registry.json path."""
    registry_path = tmp_path / "registry.json"
    # Initialize with empty registry structure
    registry_data = {"skills": {}, "updated_at": None}
    registry_path.write_text(json.dumps(registry_data, indent=2))
    return registry_path


@pytest.fixture
def tmp_queue(tmp_path: Path) -> Path:
    """Create a temp nightly_queue.json path."""
    queue_path = tmp_path / "nightly_queue.json"
    # Initialize with empty queue structure
    queue_data = {"items": [], "updated_at": None}
    queue_path.write_text(json.dumps(queue_data, indent=2))
    return queue_path


@pytest.fixture
def mock_queue(tmp_path: Path) -> Path:
    """Create a nightly_queue.json with 2 pending items for MockLLM."""
    queue_path = tmp_path / "nightly_queue.json"
    queue_data = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "capability": "convert text to uppercase",
                "first_seen": datetime.now().isoformat(),
                "occurrences": 2,
                "context": "[MISSING: convert text to uppercase]",
                "status": "pending",
            },
            {
                "id": str(uuid.uuid4()),
                "capability": "normalize filename removing special characters",
                "first_seen": datetime.now().isoformat(),
                "occurrences": 1,
                "context": "[MISSING: normalize filename removing special characters]",
                "status": "pending",
            },
        ],
        "updated_at": datetime.now().isoformat(),
    }
    queue_path.write_text(json.dumps(queue_data, indent=2))
    return queue_path


@pytest.fixture
def mock_registry(tmp_path: Path) -> Path:
    """Create a registry.json with one staged skill."""
    registry_path = tmp_path / "registry.json"
    registry_data = {
        "skills": {
            "text_echo": {
                "name": "text_echo",
                "current_prod": None,
                "current_staging": "1.0.0",
                "versions": {
                    "1.0.0": {
                        "version": "1.0.0",
                        "code_hash": "abc123",
                        "manifest_hash": "def456",
                        "created_at": datetime.now().isoformat(),
                        "status": "staging",
                        "validation": {
                            "ast_gate": {"passed": True, "violations": []},
                            "sandbox": {"passed": True, "skipped": False},
                            "promote_gate": None,
                        },
                        "promoted_at": None,
                        "disabled_at": None,
                        "disabled_reason": None,
                    }
                },
            }
        },
        "updated_at": datetime.now().isoformat(),
    }
    registry_path.write_text(json.dumps(registry_data, indent=2))
    return registry_path


@pytest.fixture
def mock_skill_dir(tmp_path: Path) -> Path:
    """Create a skill directory with valid skill.py and skill.json matching MockLLM output."""
    skill_dir = tmp_path / "skills_staging" / "text_echo" / "1.0.0"
    skill_dir.mkdir(parents=True)

    # skill.py matching MockLLM's text_echo
    skill_code = '''"""Text echo skill - transforms text to different formats."""

import json


def action(text: str, format: str = "upper") -> str:
    """Transform text to the specified format."""
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
    assert action("hello", "upper") == "HELLO", "uppercase failed"
    assert action("HELLO", "lower") == "hello", "lowercase failed"
    assert action("hello world", "title") == "Hello World", "title failed"
    assert action("test") == "TEST", "default format failed"
    return True
'''
    (skill_dir / "skill.py").write_text(skill_code)

    # skill.json manifest
    manifest = {
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
    (skill_dir / "skill.json").write_text(json.dumps(manifest, indent=2))

    return skill_dir


@pytest.fixture
def mock_eval_dir(tmp_path: Path) -> Path:
    """Create data/eval/ with minimal replay/regression/redteam cases for text_echo."""
    eval_dir = tmp_path / "eval"

    # Create replay cases
    replay_dir = eval_dir / "replay"
    replay_dir.mkdir(parents=True)
    replay_case = {
        "id": "replay-text-echo-001",
        "skill": "text_echo",
        "input": {"text": "hello", "format": "upper"},
        "expected": {"type": "exact", "value": "HELLO"},
        "timeout_ms": 5000,
    }
    (replay_dir / "text_echo_replay.json").write_text(json.dumps(replay_case, indent=2))

    # Create regression cases
    regression_dir = eval_dir / "regression"
    regression_dir.mkdir(parents=True)
    regression_case = {
        "id": "regression-text-echo-001",
        "skill": "text_echo",
        "input": {"text": "World", "format": "lower"},
        "expected": {"type": "exact", "value": "world"},
        "timeout_ms": 5000,
    }
    (regression_dir / "text_echo_regression.json").write_text(
        json.dumps(regression_case, indent=2)
    )

    # Create redteam cases
    redteam_dir = eval_dir / "redteam"
    redteam_dir.mkdir(parents=True)
    redteam_case = {
        "id": "redteam-text-echo-001",
        "skill": "text_echo",
        "input": {"text": "../etc/passwd", "format": "upper"},
        "expected": {
            "type": "no_forbidden_patterns",
            "forbidden": ["/etc/passwd", "/proc/", "/sys/"],
        },
        "timeout_ms": 5000,
    }
    (redteam_dir / "text_echo_redteam.json").write_text(
        json.dumps(redteam_case, indent=2)
    )

    return eval_dir


@pytest.fixture
def docker_available() -> bool:
    """Check if Docker daemon is running and sandbox image exists."""
    runner = SandboxRunner()
    return runner.is_available()
