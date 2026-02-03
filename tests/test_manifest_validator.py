"""Tests for manifest validator."""

import pytest

from src.validators.manifest import validate_manifest


@pytest.fixture
def valid_manifest():
    """Return a valid manifest dictionary."""
    return {
        "name": "text_echo",
        "version": "1.0.0",
        "description": "Echoes the input text back to the user",
        "inputs_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "outputs_schema": {"type": "string"},
        "permissions": {"filesystem": "none", "network": False, "subprocess": False},
    }


class TestValidManifest:
    """Tests for valid manifest validation."""

    def test_valid_manifest_passes(self, valid_manifest):
        """Valid manifest passes validation."""
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is True
        assert errors == []

    def test_valid_manifest_with_optional_fields(self, valid_manifest):
        """Valid manifest with optional fields passes."""
        valid_manifest["author"] = "test_author"
        valid_manifest["tags"] = ["utility", "text"]
        valid_manifest["dependencies"] = [{"name": "pydantic", "version": "2.0.0"}]
        valid_manifest["examples"] = [
            {"input": {"text": "hello"}, "output": "hello"}
        ]

        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is True
        assert errors == []

    def test_valid_manifest_with_created_at(self, valid_manifest):
        """Valid manifest with created_at passes."""
        valid_manifest["created_at"] = "2024-01-01T00:00:00Z"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is True


class TestMissingRequiredFields:
    """Tests for missing required fields."""

    def test_missing_name(self, valid_manifest):
        """Missing name field fails validation."""
        del valid_manifest["name"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("name" in e.lower() for e in errors)

    def test_missing_version(self, valid_manifest):
        """Missing version field fails validation."""
        del valid_manifest["version"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("version" in e.lower() for e in errors)

    def test_missing_description(self, valid_manifest):
        """Missing description field fails validation."""
        del valid_manifest["description"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("description" in e.lower() for e in errors)

    def test_missing_inputs_schema(self, valid_manifest):
        """Missing inputs_schema field fails validation."""
        del valid_manifest["inputs_schema"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("inputs_schema" in e.lower() for e in errors)

    def test_missing_outputs_schema(self, valid_manifest):
        """Missing outputs_schema field fails validation."""
        del valid_manifest["outputs_schema"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("outputs_schema" in e.lower() for e in errors)

    def test_missing_permissions(self, valid_manifest):
        """Missing permissions field fails validation."""
        del valid_manifest["permissions"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("permissions" in e.lower() for e in errors)


class TestInvalidFieldFormats:
    """Tests for invalid field formats."""

    def test_invalid_name_format(self, valid_manifest):
        """Invalid name format fails validation."""
        valid_manifest["name"] = "Invalid-Name"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_invalid_version_format(self, valid_manifest):
        """Invalid version format fails validation."""
        valid_manifest["version"] = "1.0"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_description_too_short(self, valid_manifest):
        """Description shorter than 10 chars fails."""
        valid_manifest["description"] = "Too short"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_description_too_long(self, valid_manifest):
        """Description longer than 500 chars fails."""
        valid_manifest["description"] = "x" * 501
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False


class TestMVPConstraints:
    """Tests for MVP constraint violations."""

    def test_network_true_violates_mvp(self, valid_manifest):
        """Network=True violates MVP constraint."""
        valid_manifest["permissions"]["network"] = True
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("network" in e.lower() and "mvp" in e.lower() for e in errors)

    def test_subprocess_true_violates_mvp(self, valid_manifest):
        """Subprocess=True violates MVP constraint."""
        valid_manifest["permissions"]["subprocess"] = True
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert any("subprocess" in e.lower() and "mvp" in e.lower() for e in errors)

    def test_both_mvp_violations(self, valid_manifest):
        """Both network and subprocess True produces two errors."""
        valid_manifest["permissions"]["network"] = True
        valid_manifest["permissions"]["subprocess"] = True
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
        assert len(errors) >= 2


class TestPermissionsValidation:
    """Tests for permissions field validation."""

    def test_invalid_filesystem_value(self, valid_manifest):
        """Invalid filesystem value fails validation."""
        valid_manifest["permissions"]["filesystem"] = "read_all"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_valid_filesystem_read_workdir(self, valid_manifest):
        """Filesystem read_workdir is valid."""
        valid_manifest["permissions"]["filesystem"] = "read_workdir"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is True

    def test_valid_filesystem_write_workdir(self, valid_manifest):
        """Filesystem write_workdir is valid."""
        valid_manifest["permissions"]["filesystem"] = "write_workdir"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is True

    def test_missing_permission_field(self, valid_manifest):
        """Missing required permission field fails."""
        del valid_manifest["permissions"]["network"]
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False


class TestInputsOutputsSchema:
    """Tests for inputs_schema and outputs_schema validation."""

    def test_inputs_schema_requires_type_object(self, valid_manifest):
        """inputs_schema must have type: object."""
        valid_manifest["inputs_schema"] = {"properties": {}}
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_outputs_schema_requires_type(self, valid_manifest):
        """outputs_schema must have type field."""
        valid_manifest["outputs_schema"] = {}
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_outputs_schema_various_types(self, valid_manifest):
        """outputs_schema can have various types."""
        for output_type in ["string", "number", "boolean", "object", "array"]:
            valid_manifest["outputs_schema"] = {"type": output_type}
            is_valid, errors = validate_manifest(valid_manifest)
            assert is_valid is True, f"Failed for type: {output_type}"


class TestAdditionalProperties:
    """Tests for additionalProperties behavior."""

    def test_unknown_top_level_field_rejected(self, valid_manifest):
        """Unknown top-level field is rejected."""
        valid_manifest["unknown_field"] = "value"
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False

    def test_unknown_permission_field_rejected(self, valid_manifest):
        """Unknown permission field is rejected."""
        valid_manifest["permissions"]["unknown"] = True
        is_valid, errors = validate_manifest(valid_manifest)
        assert is_valid is False
