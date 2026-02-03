"""Manifest validation against JSON Schema."""

import json
from pathlib import Path

import jsonschema

# Path to the skill schema
SCHEMA_PATH = Path(__file__).parent.parent.parent / "spec" / "contracts" / "skill_schema.json"


def _load_schema() -> dict:
    """Load the skill JSON schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_manifest(manifest: dict) -> tuple[bool, list[str]]:
    """
    Validate a manifest against the skill schema and MVP constraints.

    Args:
        manifest: The manifest dictionary to validate.

    Returns:
        A tuple of (is_valid, list_of_errors).
        If valid, errors list is empty.
    """
    errors: list[str] = []

    # Load and validate against JSON Schema
    try:
        schema = _load_schema()
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
    except FileNotFoundError:
        errors.append(f"Schema file not found: {SCHEMA_PATH}")
    except json.JSONDecodeError as e:
        errors.append(f"Schema JSON decode error: {e}")

    # MVP constraints: network must be False, subprocess must be False
    permissions = manifest.get("permissions", {})

    if permissions.get("network") is True:
        errors.append("MVP constraint violation: network must be False")

    if permissions.get("subprocess") is True:
        errors.append("MVP constraint violation: subprocess must be False")

    return (len(errors) == 0, errors)
