"""Tests for Registry class."""

import json
from datetime import datetime

import pytest

from src.models.registry import RegistryData, ValidationResult
from src.registry import Registry, compute_hash


@pytest.fixture
def tmp_registry_path(tmp_path):
    """Return a temporary registry file path."""
    return tmp_path / "registry.json"


@pytest.fixture
def registry(tmp_registry_path):
    """Return a Registry instance with temporary path."""
    return Registry(tmp_registry_path)


@pytest.fixture
def sample_validation():
    """Return a sample validation result."""
    return ValidationResult(
        ast_gate={"passed": True, "violations": []},
        sandbox={"passed": True, "output": "OK"},
    )


class TestRegistryLoad:
    """Tests for Registry.load()."""

    def test_load_empty_when_file_missing(self, registry):
        """Load returns empty registry when file doesn't exist."""
        data = registry.load()
        assert isinstance(data, RegistryData)
        assert data.skills == {}

    def test_load_existing_file(self, registry, tmp_registry_path):
        """Load reads existing registry file."""
        existing_data = {
            "skills": {
                "test_skill": {
                    "name": "test_skill",
                    "current_prod": None,
                    "current_staging": "1.0.0",
                    "versions": {
                        "1.0.0": {
                            "version": "1.0.0",
                            "code_hash": "abc123",
                            "manifest_hash": "def456",
                            "created_at": "2024-01-01T00:00:00",
                            "status": "staging",
                            "validation": {},
                        }
                    },
                }
            },
            "updated_at": "2024-01-01T00:00:00",
        }
        tmp_registry_path.write_text(json.dumps(existing_data))

        data = registry.load()
        assert "test_skill" in data.skills
        assert data.skills["test_skill"].current_staging == "1.0.0"


class TestRegistrySave:
    """Tests for Registry.save()."""

    def test_save_creates_file(self, registry, tmp_registry_path):
        """Save creates the registry file."""
        data = RegistryData()
        registry.save(data)
        assert tmp_registry_path.exists()

    def test_save_with_indent(self, registry, tmp_registry_path):
        """Save uses indent=2 for JSON formatting."""
        data = RegistryData()
        registry.save(data)
        content = tmp_registry_path.read_text()
        # Check indentation exists
        assert "  " in content

    def test_save_roundtrip(self, registry, sample_validation):
        """Save and load produces equivalent data."""
        registry.add_staging("test_skill", "1.0.0", "hash1", "hash2", sample_validation)
        data = registry.load()
        assert "test_skill" in data.skills
        assert data.skills["test_skill"].versions["1.0.0"].code_hash == "hash1"


class TestRegistryAddStaging:
    """Tests for Registry.add_staging()."""

    def test_add_staging_new_skill(self, registry, sample_validation):
        """Add staging creates new skill entry."""
        version = registry.add_staging(
            "new_skill", "1.0.0", "code_hash", "manifest_hash", sample_validation
        )
        assert version.version == "1.0.0"
        assert version.status == "staging"
        assert version.code_hash == "code_hash"

        entry = registry.get_entry("new_skill")
        assert entry is not None
        assert entry.current_staging == "1.0.0"

    def test_add_staging_existing_skill(self, registry, sample_validation):
        """Add staging to existing skill adds new version."""
        registry.add_staging("skill", "1.0.0", "hash1", "hash2", sample_validation)
        registry.add_staging("skill", "2.0.0", "hash3", "hash4", sample_validation)

        entry = registry.get_entry("skill")
        assert "1.0.0" in entry.versions
        assert "2.0.0" in entry.versions
        assert entry.current_staging == "2.0.0"

    def test_add_staging_sets_created_at(self, registry, sample_validation):
        """Add staging sets created_at timestamp."""
        before = datetime.now()
        version = registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        after = datetime.now()
        assert before <= version.created_at <= after


class TestRegistryPromote:
    """Tests for Registry.promote()."""

    def test_promote_staging_to_prod(self, registry, sample_validation):
        """Promote moves staging version to prod."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        result = registry.promote("skill", "1.0.0")
        assert result is True

        entry = registry.get_entry("skill")
        assert entry.current_prod == "1.0.0"
        assert entry.versions["1.0.0"].status == "prod"
        assert entry.versions["1.0.0"].promoted_at is not None

    def test_promote_nonexistent_skill(self, registry):
        """Promote fails for nonexistent skill."""
        result = registry.promote("nonexistent", "1.0.0")
        assert result is False

    def test_promote_nonexistent_version(self, registry, sample_validation):
        """Promote fails for nonexistent version."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        result = registry.promote("skill", "2.0.0")
        assert result is False

    def test_promote_disables_old_prod(self, registry, sample_validation):
        """Promote disables previous prod version."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        registry.promote("skill", "1.0.0")
        registry.add_staging("skill", "2.0.0", "h3", "h4", sample_validation)
        registry.promote("skill", "2.0.0")

        entry = registry.get_entry("skill")
        assert entry.versions["1.0.0"].status == "disabled"
        assert entry.versions["1.0.0"].disabled_at is not None
        assert "2.0.0" in entry.versions["1.0.0"].disabled_reason

    def test_promote_clears_staging_pointer(self, registry, sample_validation):
        """Promote clears current_staging if same version."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        registry.promote("skill", "1.0.0")

        entry = registry.get_entry("skill")
        assert entry.current_staging is None


class TestRegistryRollback:
    """Tests for Registry.rollback()."""

    def test_rollback_to_previous_prod(self, registry, sample_validation):
        """Rollback restores previous prod version."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        registry.promote("skill", "1.0.0")
        registry.add_staging("skill", "2.0.0", "h3", "h4", sample_validation)
        registry.promote("skill", "2.0.0")

        result = registry.rollback("skill", "1.0.0")
        assert result is True

        entry = registry.get_entry("skill")
        assert entry.current_prod == "1.0.0"
        assert entry.versions["1.0.0"].status == "prod"
        assert entry.versions["2.0.0"].status == "disabled"

    def test_rollback_nonexistent_skill(self, registry):
        """Rollback fails for nonexistent skill."""
        result = registry.rollback("nonexistent", "1.0.0")
        assert result is False

    def test_rollback_nonexistent_version(self, registry, sample_validation):
        """Rollback fails for nonexistent version."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        result = registry.rollback("skill", "2.0.0")
        assert result is False

    def test_rollback_staging_never_promoted(self, registry, sample_validation):
        """Rollback fails for staging version never promoted."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        result = registry.rollback("skill", "1.0.0")
        assert result is False


class TestRegistryGetEntry:
    """Tests for Registry.get_entry()."""

    def test_get_entry_existing(self, registry, sample_validation):
        """Get entry returns existing skill entry."""
        registry.add_staging("skill", "1.0.0", "h1", "h2", sample_validation)
        entry = registry.get_entry("skill")
        assert entry is not None
        assert entry.name == "skill"

    def test_get_entry_nonexistent(self, registry):
        """Get entry returns None for nonexistent skill."""
        entry = registry.get_entry("nonexistent")
        assert entry is None


class TestRegistryListSkills:
    """Tests for Registry.list_skills()."""

    def test_list_skills_empty(self, registry):
        """List skills returns empty list for empty registry."""
        skills = registry.list_skills()
        assert skills == []

    def test_list_skills_multiple(self, registry, sample_validation):
        """List skills returns all skill names."""
        registry.add_staging("skill_a", "1.0.0", "h1", "h2", sample_validation)
        registry.add_staging("skill_b", "1.0.0", "h3", "h4", sample_validation)
        skills = registry.list_skills()
        assert set(skills) == {"skill_a", "skill_b"}


class TestComputeHash:
    """Tests for compute_hash function."""

    def test_compute_hash_deterministic(self):
        """Same content produces same hash."""
        content = "test content"
        hash1 = compute_hash(content)
        hash2 = compute_hash(content)
        assert hash1 == hash2

    def test_compute_hash_different_content(self):
        """Different content produces different hash."""
        hash1 = compute_hash("content 1")
        hash2 = compute_hash("content 2")
        assert hash1 != hash2

    def test_compute_hash_sha256_format(self):
        """Hash is 64 character hex string (SHA-256)."""
        h = compute_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
