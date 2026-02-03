"""Tests for the skill promotion module."""

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.models.registry import RegistryData, SkillEntry, SkillVersion, ValidationResult
from src.promote import promote_all, promote_skill
from src.registry import Registry


@pytest.fixture
def temp_dirs():
    """Create temporary directories for staging, prod, eval, and registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        staging = base / "staging"
        prod = base / "prod"
        eval_dir = base / "eval"
        registry_path = base / "registry.json"
        audit_log_path = base / "audit.log"

        staging.mkdir()
        prod.mkdir()
        eval_dir.mkdir()
        (eval_dir / "replay").mkdir()
        (eval_dir / "regression").mkdir()
        (eval_dir / "redteam").mkdir()

        yield {
            "staging": staging,
            "prod": prod,
            "eval_dir": eval_dir,
            "registry_path": registry_path,
            "audit_log_path": audit_log_path,
        }


def create_skill_in_staging(staging: Path, name: str, version: str, code: str) -> Path:
    """Create a skill directory in staging."""
    skill_dir = staging / name / version
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.py").write_text(code)
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": version,
                "description": f"Test skill {name}",
            }
        )
    )
    return skill_dir


def create_registry_with_staging(
    registry_path: Path, name: str, version: str
) -> Registry:
    """Create a registry with a skill in staging."""
    registry = Registry(registry_path)
    registry.add_staging(
        name=name,
        version=version,
        code_hash="abc123",
        manifest_hash="def456",
        validation=ValidationResult(),
    )
    return registry


def create_eval_case(eval_dir: Path, category: str, filename: str, case: dict) -> None:
    """Create an evaluation case file."""
    case_file = eval_dir / category / filename
    case_file.write_text(json.dumps(case))


class TestPromoteSkill:
    """Tests for promote_skill function."""

    def test_promote_success(self, temp_dirs):
        """promote_skill succeeds when all gates pass."""
        # Create skill that passes all tests
        create_skill_in_staging(
            temp_dirs["staging"],
            "text_echo",
            "1.0.0",
            """
def action(text, format):
    if format == "uppercase":
        return text.upper()
    elif format == "lowercase":
        return text.lower()
    elif format == "title":
        return text.title()
    return text
""",
        )

        # Create registry entry
        create_registry_with_staging(
            temp_dirs["registry_path"], "text_echo", "1.0.0"
        )

        # Create passing eval cases
        create_eval_case(
            temp_dirs["eval_dir"],
            "replay",
            "test_001.json",
            {
                "id": "replay_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )
        create_eval_case(
            temp_dirs["eval_dir"],
            "regression",
            "test_001.json",
            {
                "id": "regression_001",
                "skill": "text_echo",
                "input": {"text": "", "format": "uppercase"},
                "expected": {"type": "exact", "value": ""},
                "timeout_ms": 1000,
            },
        )
        create_eval_case(
            temp_dirs["eval_dir"],
            "redteam",
            "test_001.json",
            {
                "id": "redteam_001",
                "skill": "text_echo",
                "input": {"text": "../etc/passwd", "format": "uppercase"},
                "expected": {
                    "type": "no_forbidden_patterns",
                    "forbidden": ["root:", "/etc/passwd"],
                },
                "timeout_ms": 1000,
            },
        )

        # Promote
        result = promote_skill(
            "text_echo",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert result is True

        # Verify skill copied to prod
        prod_skill = temp_dirs["prod"] / "text_echo" / "1.0.0" / "skill.py"
        assert prod_skill.exists()

        # Verify registry updated
        registry = Registry(temp_dirs["registry_path"])
        entry = registry.get_entry("text_echo")
        assert entry.current_prod == "1.0.0"
        assert entry.current_staging is None

    def test_replay_fail_blocks_promotion(self, temp_dirs):
        """promote_skill fails when replay gate fails."""
        # Create skill that fails replay test
        create_skill_in_staging(
            temp_dirs["staging"],
            "text_echo",
            "1.0.0",
            """
def action(text, format):
    return text.lower()  # Always lowercase, fails uppercase test
""",
        )

        create_registry_with_staging(
            temp_dirs["registry_path"], "text_echo", "1.0.0"
        )

        # Create failing replay case
        create_eval_case(
            temp_dirs["eval_dir"],
            "replay",
            "test_001.json",
            {
                "id": "replay_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )

        result = promote_skill(
            "text_echo",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert result is False

        # Verify skill NOT copied to prod
        prod_skill = temp_dirs["prod"] / "text_echo" / "1.0.0" / "skill.py"
        assert not prod_skill.exists()

        # Verify registry NOT updated to prod
        registry = Registry(temp_dirs["registry_path"])
        entry = registry.get_entry("text_echo")
        assert entry.current_prod is None
        assert entry.current_staging == "1.0.0"

    def test_registry_updated_with_gate_results(self, temp_dirs):
        """promote_skill records gate results in registry validation."""
        create_skill_in_staging(
            temp_dirs["staging"],
            "text_echo",
            "1.0.0",
            """
def action(text, format):
    return text.upper()
""",
        )

        create_registry_with_staging(
            temp_dirs["registry_path"], "text_echo", "1.0.0"
        )

        create_eval_case(
            temp_dirs["eval_dir"],
            "replay",
            "test_001.json",
            {
                "id": "replay_001",
                "skill": "text_echo",
                "input": {"text": "hello", "format": "uppercase"},
                "expected": {"type": "exact", "value": "HELLO"},
                "timeout_ms": 1000,
            },
        )

        promote_skill(
            "text_echo",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        # Check registry has gate results
        registry = Registry(temp_dirs["registry_path"])
        data = registry.load()
        version = data.skills["text_echo"].versions["1.0.0"]

        assert version.validation.promote_gate is not None
        assert "replay" in version.validation.promote_gate
        assert version.validation.promote_gate["replay"]["gate_passed"] is True

    def test_audit_logged_on_success(self, temp_dirs):
        """promote_skill logs to audit on successful promotion."""
        create_skill_in_staging(
            temp_dirs["staging"],
            "text_echo",
            "1.0.0",
            """
def action(text, format):
    return text.upper()
""",
        )

        create_registry_with_staging(
            temp_dirs["registry_path"], "text_echo", "1.0.0"
        )

        promote_skill(
            "text_echo",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        # Check audit log
        audit_content = temp_dirs["audit_log_path"].read_text()
        assert "[PROMOTE]" in audit_content
        assert "skill=text_echo" in audit_content
        assert "version=1.0.0" in audit_content

    def test_no_staging_version_returns_false(self, temp_dirs):
        """promote_skill returns False when skill has no staging version."""
        # Create registry without staging
        registry = Registry(temp_dirs["registry_path"])
        data = RegistryData()
        data.skills["text_echo"] = SkillEntry(name="text_echo")
        registry.save(data)

        result = promote_skill(
            "text_echo",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert result is False

    def test_skill_not_in_registry_returns_false(self, temp_dirs):
        """promote_skill returns False when skill not in registry."""
        result = promote_skill(
            "nonexistent",
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert result is False


class TestPromoteAll:
    """Tests for promote_all function."""

    def test_promote_all_promotes_eligible_skills(self, temp_dirs):
        """promote_all promotes all skills with staging versions."""
        # Create two skills in staging
        create_skill_in_staging(
            temp_dirs["staging"],
            "skill_a",
            "1.0.0",
            "def action(): return 'a'",
        )
        create_skill_in_staging(
            temp_dirs["staging"],
            "skill_b",
            "1.0.0",
            "def action(): return 'b'",
        )

        # Create registry entries
        registry = Registry(temp_dirs["registry_path"])
        registry.add_staging("skill_a", "1.0.0", "h1", "h2", ValidationResult())
        registry.add_staging("skill_b", "1.0.0", "h3", "h4", ValidationResult())

        result = promote_all(
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert "skill_a" in result["promoted"]
        assert "skill_b" in result["promoted"]
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 0

    def test_promote_all_skips_no_staging(self, temp_dirs):
        """promote_all skips skills without staging versions."""
        # Create skill in prod only
        registry = Registry(temp_dirs["registry_path"])
        data = RegistryData()
        data.skills["old_skill"] = SkillEntry(
            name="old_skill",
            current_prod="0.9.0",
            versions={
                "0.9.0": SkillVersion(
                    version="0.9.0",
                    code_hash="x",
                    manifest_hash="y",
                    created_at=datetime.now(),
                    status="prod",
                )
            },
        )
        registry.save(data)

        result = promote_all(
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert "old_skill" in result["skipped"]
        assert len(result["promoted"]) == 0

    def test_promote_all_reports_failures(self, temp_dirs):
        """promote_all reports failed promotions."""
        # Create skill that will fail
        create_skill_in_staging(
            temp_dirs["staging"],
            "bad_skill",
            "1.0.0",
            "def action(): return 'wrong'",
        )

        registry = Registry(temp_dirs["registry_path"])
        registry.add_staging("bad_skill", "1.0.0", "h1", "h2", ValidationResult())

        # Create failing test case
        create_eval_case(
            temp_dirs["eval_dir"],
            "replay",
            "test_001.json",
            {
                "id": "replay_001",
                "skill": "bad_skill",
                "input": {},
                "expected": {"type": "exact", "value": "right"},
                "timeout_ms": 1000,
            },
        )

        result = promote_all(
            temp_dirs["staging"],
            temp_dirs["prod"],
            temp_dirs["registry_path"],
            temp_dirs["eval_dir"],
            temp_dirs["audit_log_path"],
        )

        assert "bad_skill" in result["failed"]
        assert len(result["promoted"]) == 0


class TestPromoteCLI:
    """Tests for promote CLI."""

    def test_cli_help(self):
        """CLI shows help message."""
        result = subprocess.run(
            [sys.executable, "-m", "src.promote", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "--staging" in result.stdout
        assert "--prod" in result.stdout
        assert "--registry" in result.stdout
        assert "--eval-dir" in result.stdout
        assert "--skill" in result.stdout
        assert "--audit-log" in result.stdout

    def test_cli_requires_arguments(self):
        """CLI requires staging, prod, registry, and eval-dir arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "src.promote"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower()
