"""Skill manifest data models."""

from typing import Literal

from pydantic import BaseModel, Field


class Permission(BaseModel):
    """Skill permission declaration."""

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


class SkillManifest(BaseModel):
    """
    Skill metadata contract.

    Each skill must have a skill.json file conforming to this schema.
    """

    name: str = Field(..., pattern=r"^[a-z][a-z0-9_]{2,63}$")
    version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    description: str = Field(..., min_length=10, max_length=500)
    author: str = "auto-generated"
    created_at: str | None = None
    inputs_schema: dict
    outputs_schema: dict
    permissions: Permission
    dependencies: list[Dependency] = []
    tags: list[str] = []
    examples: list[Example] = []
