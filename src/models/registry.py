"""Registry data models for skill version management."""

from datetime import datetime

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Results from validation gates."""

    ast_gate: dict | None = None
    sandbox: dict | None = None
    promote_gate: dict | None = None


class SkillVersion(BaseModel):
    """A specific version of a skill."""

    version: str
    code_hash: str
    manifest_hash: str
    created_at: datetime
    status: str  # staging | prod | disabled
    validation: ValidationResult = ValidationResult()
    promoted_at: datetime | None = None
    disabled_at: datetime | None = None
    disabled_reason: str | None = None


class SkillEntry(BaseModel):
    """Registry entry for a skill with all its versions."""

    name: str
    current_prod: str | None = None
    current_staging: str | None = None
    versions: dict[str, SkillVersion] = {}


class RegistryData(BaseModel):
    """Root registry data structure."""

    skills: dict[str, SkillEntry] = {}
    updated_at: datetime = datetime.now()
