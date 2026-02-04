"""Load production skills from the registry + skills_prod directory."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .models.skill import SkillManifest
from .registry import Registry
from .validators.manifest import validate_manifest


@dataclass
class LoadedSkill:
    """A loaded skill package with metadata and module."""

    name: str
    version: str
    path: Path
    manifest: SkillManifest
    module: ModuleType


class SkillLoader:
    """Load production skills based on the registry current_prod pointer."""

    def __init__(
        self,
        prod_path: Path | None = None,
        registry_path: Path | None = None,
        *,
        enforce_mvp_constraints: bool = True,
    ) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        self.prod_path = (prod_path or (repo_root / "skills_prod")).resolve()
        self.registry_path = (registry_path or (repo_root / "data" / "registry.json")).resolve()
        self.enforce_mvp_constraints = enforce_mvp_constraints
        self._registry = Registry(self.registry_path)
        self._cache: dict[tuple[str, str], LoadedSkill] = {}

    def _resolve_version(self, name: str, version: str | None) -> str:
        if version:
            return version
        entry = self._registry.get_entry(name)
        if entry is None or entry.current_prod is None:
            raise ValueError(f"No production version found for skill: {name}")
        return entry.current_prod

    def _skill_dir(self, name: str, version: str) -> Path:
        return self.prod_path / name / version

    def load_manifest(self, name: str, version: str | None = None) -> SkillManifest:
        """Load and validate a skill manifest."""
        resolved = self._resolve_version(name, version)
        skill_dir = self._skill_dir(name, resolved)
        manifest_path = skill_dir / "skill.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest: {manifest_path}")

        with open(manifest_path) as f:
            manifest_data = json.load(f)

        ok, errors = validate_manifest(
            manifest_data,
            enforce_mvp_constraints=self.enforce_mvp_constraints,
        )
        if not ok:
            raise ValueError(
                "Manifest validation failed: " + "; ".join(errors)
            )

        return SkillManifest.model_validate(manifest_data)

    def load_module(self, name: str, version: str | None = None) -> ModuleType:
        """Load a skill module from disk using importlib."""
        resolved = self._resolve_version(name, version)
        skill_dir = self._skill_dir(name, resolved)
        skill_file = skill_dir / "skill.py"
        if not skill_file.exists():
            raise FileNotFoundError(f"Missing skill code: {skill_file}")

        module_name = f"openclaw.skills.{name}.{resolved}"
        spec = importlib.util.spec_from_file_location(module_name, skill_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module spec for {skill_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def load(self, name: str, version: str | None = None) -> LoadedSkill:
        """Load a production skill (manifest + module), cached per version."""
        resolved = self._resolve_version(name, version)
        cache_key = (name, resolved)
        if cache_key in self._cache:
            return self._cache[cache_key]

        skill_dir = self._skill_dir(name, resolved)
        if not skill_dir.exists():
            raise FileNotFoundError(f"Missing skill directory: {skill_dir}")

        manifest = self.load_manifest(name, resolved)
        module = self.load_module(name, resolved)

        loaded = LoadedSkill(
            name=name,
            version=resolved,
            path=skill_dir,
            manifest=manifest,
            module=module,
        )
        self._cache[cache_key] = loaded
        return loaded

    def get_action(self, name: str, version: str | None = None):
        """Return the skill's action() callable."""
        loaded = self.load(name, version)
        action = getattr(loaded.module, "action", None)
        if action is None or not callable(action):
            raise AttributeError(f"Skill {name} has no callable action()")
        return action

    def get_verify(self, name: str, version: str | None = None):
        """Return the skill's verify() callable."""
        loaded = self.load(name, version)
        verify = getattr(loaded.module, "verify", None)
        if verify is None or not callable(verify):
            raise AttributeError(f"Skill {name} has no callable verify()")
        return verify
