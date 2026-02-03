"""Skill manifest data models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Permission(BaseModel):
    """Skill permission declaration."""

    model_config = ConfigDict(extra="forbid")
    filesystem: Literal["none", "read_workdir", "write_workdir"] = "none"
    network: bool = False
    subprocess: bool = False


class Dependency(BaseModel):
    """Python package dependency."""

    name: str
    version: str


class Example(BaseModel):
    """Usage example for a skill."""

    description: str | None = None
    input: dict
    output: dict | str | int | float | bool | list | None


class InputSchema(BaseModel):
    """Schema for skill inputs (must be object)."""

    model_config = ConfigDict(extra="allow")
    type: Literal["object"]
    properties: dict
    required: list[str] | None = None


class OutputSchema(BaseModel):
    """Schema for skill outputs."""

    model_config = ConfigDict(extra="allow")
    type: str


class SkillManifest(BaseModel):
    """
    Skill metadata contract.

    Each skill must have a skill.json file conforming to this schema.
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., pattern=r"^[a-z][a-z0-9_]{2,63}$")
    version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    description: str = Field(..., min_length=10, max_length=500)
    author: str = "auto-generated"
    created_at: str | None = None
    inputs_schema: InputSchema
    outputs_schema: OutputSchema
    permissions: Permission
    dependencies: list[Dependency] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)
