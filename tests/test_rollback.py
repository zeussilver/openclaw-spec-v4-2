"""Tests for rollback functionality."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from src.registry import Registry
from src.rollback import rollback_skill


def create_test_registry(
    registry_path: Path,
    skill_name: str = "text_echo",
    versions: dict[str, dict] | None = None,
    current_prod: str | None = None,
    current_staging: str | None = None,
) -> None:
    """Helper to create a test registry file."""
    if versions is None:
        versions = {
            "0.9.0": {
                "version": "0.9.0",
                "code_hash": "hash_090",
                "manifest_hash": "manifest_090",
                "created_at": "2026-01-01T10:00:00",
                "status": "disabled",
                "promoted_at": "2026-01-01T12:00:00",
                "disabled_at": "2026-01-15T10:00:00",
                "disabled_reason": "Superseded by 1.0.0",
            },
            "1.0.0": {
                "version": "1.0.0",
                "code_hash": "hash_100",
                "manifest_hash": "manifest_100",
                "created_at": "2026-01-15T10:00:00",
                "status": "prod",
                "promoted_at": "2026-01-15T12:00:00",
            },
        }
        current_prod = current_prod or "1.0.0"

    data = {
        "skills": {
            skill_name: {
                "name": skill_name,
                "current_prod": current_prod,
                "current_staging": current_staging,
                "versions": versions,
            }
        },
        "updated_at": datetime.now().isoformat(),
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w") as f:
        json.dump(data, f, indent=2)


class TestRollbackSkill:
    """Test cases for rollback_skill function."""

    def test_successful_rollback(self, tmp_path: Path) -> None:
        """Test successful rollback from 1.0.0 to 0.9.0."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        result = rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        assert result is True

        # Verify registry was updated
        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "0.9.0"
        assert entry.versions["0.9.0"].status == "prod"
        assert entry.versions["1.0.0"].status == "disabled"

    def test_nonexistent_skill_raises_valueerror(self, tmp_path: Path) -> None:
        """Test that rollback raises ValueError for nonexistent skill."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        with pytest.raises(ValueError, match="Skill not found"):
            rollback_skill(
                skill_name="nonexistent_skill",
                target_version="0.9.0",
                registry_path=registry_path,
                audit_log_path=audit_path,
            )

    def test_nonexistent_version_raises_valueerror(self, tmp_path: Path) -> None:
        """Test that rollback raises ValueError for nonexistent version."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        with pytest.raises(ValueError, match="Version not found"):
            rollback_skill(
                skill_name="text_echo",
                target_version="2.0.0",
                registry_path=registry_path,
                audit_log_path=audit_path,
            )

    def test_cannot_rollback_to_unvalidated_staging(self, tmp_path: Path) -> None:
        """Test that rollback to never-promoted staging version fails."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        # Create registry with a staging version that was never promoted
        versions = {
            "1.0.0": {
                "version": "1.0.0",
                "code_hash": "hash_100",
                "manifest_hash": "manifest_100",
                "created_at": "2026-01-15T10:00:00",
                "status": "prod",
                "promoted_at": "2026-01-15T12:00:00",
            },
            "1.1.0": {
                "version": "1.1.0",
                "code_hash": "hash_110",
                "manifest_hash": "manifest_110",
                "created_at": "2026-01-20T10:00:00",
                "status": "staging",
                # No promoted_at - never promoted
            },
        }
        create_test_registry(
            registry_path,
            versions=versions,
            current_prod="1.0.0",
            current_staging="1.1.0",
        )

        with pytest.raises(ValueError, match="version was never promoted"):
            rollback_skill(
                skill_name="text_echo",
                target_version="1.1.0",
                registry_path=registry_path,
                audit_log_path=audit_path,
            )

    def test_disables_current_prod(self, tmp_path: Path) -> None:
        """Test that rollback disables the current prod version."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None

        # Old prod should be disabled
        old_prod = entry.versions["1.0.0"]
        assert old_prod.status == "disabled"
        assert old_prod.disabled_at is not None
        assert old_prod.disabled_reason == "Rollback to 0.9.0"

    def test_updates_current_prod_pointer(self, tmp_path: Path) -> None:
        """Test that rollback updates the current_prod pointer."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "0.9.0"

    def test_audit_logged(self, tmp_path: Path) -> None:
        """Test that rollback events are logged to audit file."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        assert audit_path.exists()
        content = audit_path.read_text()

        # Should have DISABLE and ROLLBACK events
        assert "[DISABLE]" in content
        assert "[ROLLBACK]" in content
        assert "skill=text_echo" in content
        assert "from=1.0.0" in content
        assert "to=0.9.0" in content

    def test_no_current_prod_case(self, tmp_path: Path) -> None:
        """Test rollback when there's no current prod version."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        # Create registry with a disabled version but no current prod
        versions = {
            "0.9.0": {
                "version": "0.9.0",
                "code_hash": "hash_090",
                "manifest_hash": "manifest_090",
                "created_at": "2026-01-01T10:00:00",
                "status": "disabled",
                "promoted_at": "2026-01-01T12:00:00",
                "disabled_at": "2026-01-15T10:00:00",
                "disabled_reason": "Manual disable",
            },
        }
        create_test_registry(
            registry_path,
            versions=versions,
            current_prod=None,
        )

        result = rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        assert result is True

        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "0.9.0"
        assert entry.versions["0.9.0"].status == "prod"

        # Check audit log - should have ROLLBACK but no DISABLE (no current prod to disable)
        content = audit_path.read_text()
        assert "[ROLLBACK]" in content
        assert "from=none" in content

    def test_rollback_to_same_version(self, tmp_path: Path) -> None:
        """Test rollback to current version (no-op but valid)."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path, current_prod="1.0.0")

        result = rollback_skill(
            skill_name="text_echo",
            target_version="1.0.0",
            registry_path=registry_path,
            audit_log_path=audit_path,
        )

        assert result is True

        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "1.0.0"
        # Should still be prod, not disabled (since target == current)
        assert entry.versions["1.0.0"].status == "prod"


class TestRollbackCLI:
    """Test cases for rollback CLI."""

    def test_cli_help(self) -> None:
        """Test that CLI --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "src.rollback", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--skill" in result.stdout
        assert "--to" in result.stdout
        assert "--registry" in result.stdout
        assert "--audit-log" in result.stdout

    def test_cli_successful_rollback(self, tmp_path: Path) -> None:
        """Test CLI successful rollback."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.rollback",
                "--skill",
                "text_echo",
                "--to",
                "0.9.0",
                "--registry",
                str(registry_path),
                "--audit-log",
                str(audit_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Successfully rolled back" in result.stdout

    def test_cli_nonexistent_skill(self, tmp_path: Path) -> None:
        """Test CLI with nonexistent skill."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.rollback",
                "--skill",
                "nonexistent",
                "--to",
                "0.9.0",
                "--registry",
                str(registry_path),
                "--audit-log",
                str(audit_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Skill not found" in result.stdout

    def test_cli_nonexistent_version(self, tmp_path: Path) -> None:
        """Test CLI with nonexistent version."""
        registry_path = tmp_path / "registry.json"
        audit_path = tmp_path / "audit.log"

        create_test_registry(registry_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.rollback",
                "--skill",
                "text_echo",
                "--to",
                "9.9.9",
                "--registry",
                str(registry_path),
                "--audit-log",
                str(audit_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Version not found" in result.stdout
