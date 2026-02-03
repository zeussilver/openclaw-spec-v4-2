"""Tests for skill model validation."""

import pytest
from pydantic import ValidationError

from src.models.skill import Dependency, Example, Permission, SkillManifest


class TestPermission:
    """Tests for Permission model."""

    def test_default_permission(self):
        """Default permission has no access."""
        perm = Permission()
        assert perm.filesystem == "none"
        assert perm.network is False
        assert perm.subprocess is False

    def test_valid_filesystem_permissions(self):
        """All filesystem permission values are valid."""
        for fs in ["none", "read_workdir", "write_workdir"]:
            perm = Permission(filesystem=fs)
            assert perm.filesystem == fs

    def test_invalid_filesystem_permission(self):
        """Invalid filesystem permission raises error."""
        with pytest.raises(ValidationError):
            Permission(filesystem="read_all")


class TestSkillManifest:
    """Tests for SkillManifest model."""

    @pytest.fixture
    def valid_manifest_data(self):
        """Return valid manifest data."""
        return {
            "name": "text_echo",
            "version": "1.0.0",
            "description": "Echoes the input text back to the user",
            "inputs_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
            "outputs_schema": {"type": "string"},
            "permissions": {"filesystem": "none", "network": False, "subprocess": False},
        }

    def test_valid_manifest(self, valid_manifest_data):
        """Valid manifest passes validation."""
        manifest = SkillManifest(**valid_manifest_data)
        assert manifest.name == "text_echo"
        assert manifest.version == "1.0.0"
        assert manifest.author == "auto-generated"

    def test_invalid_name_starts_with_number(self, valid_manifest_data):
        """Name starting with number is invalid."""
        valid_manifest_data["name"] = "1text_echo"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)

    def test_invalid_name_too_short(self, valid_manifest_data):
        """Name too short (less than 3 chars) is invalid."""
        valid_manifest_data["name"] = "ab"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)

    def test_invalid_name_too_long(self, valid_manifest_data):
        """Name too long (more than 64 chars) is invalid."""
        valid_manifest_data["name"] = "a" * 65
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)

    def test_invalid_name_uppercase(self, valid_manifest_data):
        """Name with uppercase is invalid."""
        valid_manifest_data["name"] = "TextEcho"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)

    def test_invalid_name_with_dash(self, valid_manifest_data):
        """Name with dash is invalid (only underscores allowed)."""
        valid_manifest_data["name"] = "text-echo"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)

    def test_valid_name_with_underscore(self, valid_manifest_data):
        """Name with underscore is valid."""
        valid_manifest_data["name"] = "text_echo_v2"
        manifest = SkillManifest(**valid_manifest_data)
        assert manifest.name == "text_echo_v2"

    def test_valid_name_with_numbers(self, valid_manifest_data):
        """Name with numbers (not at start) is valid."""
        valid_manifest_data["name"] = "echo123"
        manifest = SkillManifest(**valid_manifest_data)
        assert manifest.name == "echo123"

    def test_invalid_version_format(self, valid_manifest_data):
        """Invalid version format is rejected."""
        valid_manifest_data["version"] = "1.0"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "version" in str(exc.value)

    def test_invalid_version_with_v_prefix(self, valid_manifest_data):
        """Version with v prefix is invalid."""
        valid_manifest_data["version"] = "v1.0.0"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "version" in str(exc.value)

    def test_valid_version_large_numbers(self, valid_manifest_data):
        """Version with large numbers is valid."""
        valid_manifest_data["version"] = "123.456.789"
        manifest = SkillManifest(**valid_manifest_data)
        assert manifest.version == "123.456.789"

    def test_description_too_short(self, valid_manifest_data):
        """Description shorter than 10 chars is invalid."""
        valid_manifest_data["description"] = "Too short"
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "description" in str(exc.value)

    def test_description_too_long(self, valid_manifest_data):
        """Description longer than 500 chars is invalid."""
        valid_manifest_data["description"] = "x" * 501
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "description" in str(exc.value)

    def test_missing_required_field(self, valid_manifest_data):
        """Missing required field raises error."""
        del valid_manifest_data["name"]
        with pytest.raises(ValidationError) as exc:
            SkillManifest(**valid_manifest_data)
        assert "name" in str(exc.value)


class TestDependency:
    """Tests for Dependency model."""

    def test_valid_dependency(self):
        """Valid dependency passes validation."""
        dep = Dependency(name="requests", version="2.28.0")
        assert dep.name == "requests"
        assert dep.version == "2.28.0"


class TestExample:
    """Tests for Example model."""

    def test_valid_example(self):
        """Valid example passes validation."""
        ex = Example(
            description="Echo hello",
            input={"text": "hello"},
            output="hello",
        )
        assert ex.description == "Echo hello"
        assert ex.input == {"text": "hello"}
        assert ex.output == "hello"

    def test_example_without_description(self):
        """Example without description is valid."""
        ex = Example(input={"text": "hello"}, output="hello")
        assert ex.description is None
