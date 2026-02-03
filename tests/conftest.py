"""Pytest fixtures for OpenClaw tests."""

import json
import tempfile
from pathlib import Path

import pytest


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
